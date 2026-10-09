from __future__ import annotations

import json
from pathlib import Path

from .config import Settings
from .contracts import AudioClassifier, HubAdapter, Materializer, StudioAdapter, VisionAdapter
from .db import Database
from .models import Candidate, ItemState, Verification, VisionStatus, Workspace


class Coordinator:
    """Single composition root. One media item is advanced at a time."""

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

    def process_one(self, content_id: str) -> str:
        item = self.db.get_item(content_id)
        if item is None:
            raise KeyError(content_id)
        route = self.routes.get(int(item["source_id"]))
        if route is None:
            self.db.transition(content_id, ItemState.RECOVERY,
                               error=f"Sem rota configurada para fonte {item['source_id']}")
            return ItemState.RECOVERY.value

        # Resolve prior ambiguous external publication before any possible resend.
        publication = self.db.get_publication(content_id)
        if publication:
            if publication["status"] == Verification.CONFIRMED.value:
                self.db.transition(content_id, ItemState.PUBLISHED,
                                   detail={"reason": "publication_already_confirmed"})
                return ItemState.PUBLISHED.value
            status, message_id, detail = self.hub.verify(
                content_id, route.destination_id, route.topic_id)
            self.db.update_publication(content_id, status, message_id=message_id, detail=detail)
            if status is Verification.CONFIRMED:
                self.db.transition(content_id, ItemState.PUBLISHED,
                                   detail={"message_id": message_id, "reconciled": True})
                self._cleanup_if_safe(content_id)
                return ItemState.PUBLISHED.value
            if status is Verification.UNKNOWN:
                self.db.transition(content_id, ItemState.RECOVERY,
                                   error="Publicação UNKNOWN; reenvio automático bloqueado",
                                   detail={"verification": status.value, "detail": detail})
                return ItemState.RECOVERY.value
            # ABSENT is safe only after the adapter has established sufficient evidence.
            # The adapter contract, not a failed first search, must make that determination.
            self.db.transition(content_id, ItemState.RECOVERY,
                               error="Publicação comprovadamente ausente; requer nova execução explícita",
                               detail={"verification": status.value, "detail": detail})
            return ItemState.RECOVERY.value

        try:
            self.db.transition(content_id, ItemState.VISION)
            vision = self.vision.validate(item["source_url"],
                                          timeout_seconds=self.settings.vision_timeout_seconds)
        except Exception as exc:
            self.db.transition(content_id, ItemState.RECOVERY,
                               error=f"Falha técnica da Vision: {type(exc).__name__}: {exc}")
            return ItemState.RECOVERY.value

        if vision.status is not VisionStatus.APPROVED or not vision.affiliate_url:
            state = ItemState.WAITING_VISION if vision.status is not VisionStatus.APPROVED else ItemState.RECOVERY
            self.db.transition(content_id, state, error=vision.reason,
                               detail={"vision_status": vision.status.value})
            return state.value

        workspace = self._workspace(content_id)
        try:
            # Approval is durable before materialization begins.
            self.db.transition(content_id, ItemState.DOWNLOADING,
                               affiliate_url=vision.affiliate_url,
                               detail={"vision_approved": True})
            original = self.materializer.download(
                Candidate(int(item["source_id"]), int(item["message_id"]), item["source_url"],
                          item["received_at"], item["metadata_json"]), workspace.original)
            self.db.transition(content_id, ItemState.PROCESSING,
                               original_path=str(original))
            audio = self.audio_classifier.classify(original)
            # Defense in depth: Studio must not be able to call RVC for any other class.
            from .audio import decide_audio
            safe_audio = decide_audio(audio.kind, audio.confidence,
                                      pt_br_threshold=self.settings.audio_pt_br_threshold)
            result_path = self.studio.process(original, workspace.result, safe_audio)
            self.db.transition(content_id, ItemState.PUBLISHING, result_path=str(result_path))
            created = self.db.begin_publication(content_id, route.destination_id, route.topic_id)
            if not created:
                # Never send a second time when the durable publication record exists.
                self.db.transition(content_id, ItemState.RECOVERY,
                                   error="Registro de publicação já existe; exige reconciliação")
                return ItemState.RECOVERY.value
            try:
                message_id = self.hub.publish(result_path, route.destination_id, route.topic_id)
            except Exception as exc:
                # The send may have reached Telegram even if the client raised.
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
