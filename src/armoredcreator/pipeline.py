from __future__ import annotations

from .config import Settings
from .contracts import AudioClassifier, HubAdapter, Materializer, StudioAdapter, VisionAdapter
from .db import Database
from .models import Candidate, ItemState, Verification, VisionStatus, Workspace


class Coordinator:
    """Single composition root. Vision validation and media work are separate phases."""

    def __init__(self, settings: Settings, db: Database, vision: VisionAdapter,
                 materializer: Materializer, audio_classifier: AudioClassifier,
                 studio: StudioAdapter, hub: HubAdapter):
        self.settings = settings
        self.db = db
        self.vision = vision
        self.materializer = materializer
        self.audio_classifier = audio_classifier
        self.studio = studio
        self.hub = hub
        self.routes = {route.source_id: route for route in settings.source_routes}

    def ingest(self, candidates: list[Candidate]) -> int:
        """Persist discovery only; ingestion does not download media."""
        return sum(1 for candidate in candidates if self.db.record_candidate(candidate))

    def validate_one(self, content_id: str) -> str:
        """Phase A: validate product/link and persist the outcome without downloading media."""
        item = self.db.get_item(content_id)
        if item is None:
            raise KeyError(content_id)
        if item["affiliate_url"]:
            self.db.transition(content_id, ItemState.READY,
                               detail={"vision": "reused_persisted_approval"})
            return ItemState.READY.value
        try:
            self.db.transition(content_id, ItemState.VISION)
            vision = self.vision.validate(item["source_url"],
                                          timeout_seconds=self.settings.vision_timeout_seconds)
        except Exception as exc:
            self.db.transition(content_id, ItemState.RECOVERY,
                               error=f"Falha técnica da Vision: {type(exc).__name__}: {exc}")
            return ItemState.RECOVERY.value
        if vision.status is VisionStatus.APPROVED and vision.affiliate_url:
            self.db.transition(content_id, ItemState.READY,
                               affiliate_url=vision.affiliate_url,
                               detail={"vision_status": vision.status.value, "reason": vision.reason})
            return ItemState.READY.value
        if vision.status is VisionStatus.APPROVED:
            self.db.transition(content_id, ItemState.RECOVERY,
                               error="Vision aprovou sem affiliate_url persistível",
                               detail={"reason": vision.reason})
            return ItemState.RECOVERY.value
        self.db.transition(content_id, ItemState.WAITING_VISION, error=vision.reason,
                           detail={"vision_status": vision.status.value})
        return ItemState.WAITING_VISION.value

    def process_one(self, content_id: str) -> str:
        item = self.db.get_item(content_id)
        if item is None:
            raise KeyError(content_id)
        route = self.routes.get(int(item["source_id"]))
        if route is None:
            self.db.transition(content_id, ItemState.RECOVERY,
                               error=f"Sem rota configurada para fonte {item['source_id']}")
            return ItemState.RECOVERY.value

        publication = self.db.get_publication(content_id)
        if publication:
            if publication["status"] == Verification.CONFIRMED.value:
                self.db.transition(content_id, ItemState.PUBLISHED,
                                   detail={"reason": "publication_already_confirmed"})
                self._cleanup_if_safe(content_id)
                return ItemState.PUBLISHED.value
            status, message_id, detail = self.hub.verify(
                content_id, route.destination_id, route.topic_id)
            self.db.update_publication(content_id, status, message_id=message_id, detail=detail)
            if status is Verification.CONFIRMED and message_id is not None:
                self.db.transition(content_id, ItemState.PUBLISHED,
                                   detail={"message_id": message_id, "reconciled": True})
                self._cleanup_if_safe(content_id)
                return ItemState.PUBLISHED.value
            if status is Verification.UNKNOWN:
                self.db.transition(content_id, ItemState.RECOVERY,
                                   error="Publicação UNKNOWN; reenvio automático bloqueado",
                                   detail={"verification": status.value, "detail": detail})
                return ItemState.RECOVERY.value
            self.db.transition(content_id, ItemState.RECOVERY,
                               error="Publicação comprovadamente ausente; reenvio requer decisão explícita",
                               detail={"verification": status.value, "detail": detail})
            return ItemState.RECOVERY.value

        if not item["affiliate_url"]:
            validation_state = self.validate_one(content_id)
            if validation_state != ItemState.READY.value:
                return validation_state
            item = self.db.get_item(content_id)

        workspace = self._workspace(content_id)
        try:
            # Vision approval is already persisted before any download.
            self.db.transition(content_id, ItemState.DOWNLOADING,
                               affiliate_url=item["affiliate_url"],
                               detail={"vision_approved": True})
            candidate = Candidate(int(item["source_id"]), int(item["message_id"]),
                                  item["source_url"], item["received_at"], item["metadata_json"])
            original = self.materializer.download(candidate, workspace.original)
            self.db.transition(content_id, ItemState.PROCESSING, original_path=str(original))
            audio = self.audio_classifier.classify(original)
            from .audio import decide_audio
            safe_audio = decide_audio(audio.kind, audio.confidence,
                                      pt_br_threshold=self.settings.audio_pt_br_threshold)
            result_path = self.studio.process(original, workspace.result, safe_audio)
            self.db.transition(content_id, ItemState.PUBLISHING, result_path=str(result_path))
            created = self.db.begin_publication(content_id, route.destination_id, route.topic_id)
            if not created:
                self.db.transition(content_id, ItemState.RECOVERY,
                                   error="Registro de publicação já existe; exige reconciliação")
                return ItemState.RECOVERY.value
            try:
                message_id = self.hub.publish(result_path, route.destination_id, route.topic_id)
            except Exception as exc:
                self.db.update_publication(content_id, Verification.UNKNOWN,
                                           detail=f"publish raised {type(exc).__name__}: {exc}")
                self.db.transition(content_id, ItemState.RECOVERY,
                                   error="Resultado do envio desconhecido; não republicar automaticamente")
                return ItemState.RECOVERY.value
            status, verified_id, detail = self.hub.verify(
                content_id, route.destination_id, route.topic_id)
            if status is Verification.CONFIRMED and verified_id is not None:
                self.db.update_publication(content_id, status, message_id=verified_id, detail=detail)
                self.db.transition(content_id, ItemState.PUBLISHED,
                                   detail={"message_id": verified_id, "verification": status.value})
                self._cleanup_if_safe(content_id)
                return ItemState.PUBLISHED.value
            self.db.update_publication(content_id, status,
                                       message_id=message_id if status is Verification.UNKNOWN else None,
                                       detail=detail)
            self.db.transition(content_id, ItemState.RECOVERY,
                               error=f"Publicação não confirmada: {status.value}",
                               detail={"detail": detail})
            return ItemState.RECOVERY.value
        except Exception as exc:
            current = self.db.get_item(content_id)
            if current and current["state"] != ItemState.PUBLISHED.value:
                self.db.transition(content_id, ItemState.RECOVERY,
                                   error=f"{type(exc).__name__}: {exc}")
            return ItemState.RECOVERY.value

    def _workspace(self, content_id: str) -> Workspace:
        root = (self.settings.root / "storage" / "videos" / content_id).resolve()
        root.mkdir(parents=True, exist_ok=True)
        return Workspace(root=root, original=root / f"{content_id}_finallinkoriginal.mp4",
                         working=root / f"{content_id}_working.mp4",
                         result=root / f"{content_id}_finaldomeulinknovo.mp4")

    def _cleanup_if_safe(self, content_id: str) -> None:
        item = self.db.get_item(content_id)
        publication = self.db.get_publication(content_id)
        if not item or item["state"] != ItemState.PUBLISHED.value or not publication:
            return
        if publication["status"] != Verification.CONFIRMED.value or not publication["message_id"]:
            return
        workspace = self.settings.root / "storage" / "videos" / content_id
        self.hub.cleanup(content_id, workspace)
