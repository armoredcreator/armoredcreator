from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Callable

from .models import Item, PublicationCheck, State
from .services import (
    PublicationUnknownError,
    VisionUnresolvedError,
)


class Pipeline:
    """Durable, conservative pipeline for one content item at a time.

    This implementation intentionally delegates Telegram/Shopee, Studio/RVC and
    publication transport to adapters. SQLite state transitions are the restart
    boundary; an unknown publication outcome is never automatically resent.
    """

    def __init__(self, db, storage, vision, studio, publisher, ia=None):
        self.db = db
        self.storage = storage
        self.vision = vision
        self.studio = studio
        self.publisher = publisher
        self.ia = ia
        self.log = logging.getLogger(__name__)
        self._shutdown_checker: Callable[[], bool] = lambda: False

    def set_shutdown_checker(self, checker: Callable[[], bool]) -> None:
        self._shutdown_checker = checker

    def _check_shutdown(self) -> None:
        if self._shutdown_checker():
            raise InterruptedError("shutdown requested; item remains recoverable")

    def run(self, item_id: str, *, stop_after_vision: bool = False) -> None:
        item = self.db.get(str(item_id))
        if item.state == State.PUBLISHED:
            self.cleanup(item_id)
            return

        # Reconcile any earlier external side effect before creating another one.
        publication = self.db.publication(item_id)
        if publication is not None:
            check = self.publisher.check_publication(item)
            if check == PublicationCheck.CONFIRMED:
                message_id = str(publication["published_message_id"] or "")
                if not message_id:
                    self.db.transition(item_id, State.RECOVERY, "confirmed-publication-without-message-id")
                    return
                self.db.publication_confirmed(item_id, message_id)
                self.db.transition(item_id, State.PUBLISHED, "publication-reconciled-confirmed")
                self.cleanup(item_id)
                return
            if check == PublicationCheck.UNKNOWN:
                self.db.transition(item_id, State.RECOVERY, "publication-UNKNOWN; automatic resend forbidden")
                return
            # ABSENT is not permission to resend from this path. Recovery owns
            # the explicit decision after sufficient external evidence.
            self.db.transition(item_id, State.RECOVERY, "publication-ABSENT; explicit recovery required")
            return

        try:
            self._check_shutdown()
            item = self.db.get(item_id)
            if not item.affiliate_url:
                self.db.transition(item_id, State.VISION, "vision-start")
                try:
                    vision_result = self.vision.identify(item)
                except VisionUnresolvedError as exc:
                    self.db.mark_vision_waiting(item_id, str(exc))
                    return
                affiliate_url = str(getattr(vision_result, "affiliate_url", "") or "").strip()
                if not affiliate_url:
                    self.db.mark_vision_waiting(item_id, "Vision V1 não resolveu produto/link exato")
                    return
                self.db.set_vision(
                    item_id,
                    str(getattr(vision_result, "affiliate_name", "") or ""),
                    affiliate_url,
                    getattr(vision_result, "affiliate_urls", ()) or (),
                    getattr(vision_result, "publication_caption", None),
                    getattr(vision_result, "ia_context", None),
                )
                self.db.transition(item_id, State.RECEIVED, "vision-approved-durable")
                item = self.db.get(item_id)

            # Stage 2 can stop here: approval is durable, no video has been downloaded.
            if stop_after_vision:
                return

            self._check_shutdown()
            item = self.db.get(item_id)
            original = Path(item.original_path)
            if not original.is_file() or original.stat().st_size <= 0:
                raise FileNotFoundError(
                    f"ORIGINAL imutável ausente/vazio para {item.content_id}; Sync deve materializar após Vision"
                )

            if self._caption_enabled() and self.ia is not None and item.ia_context:
                self.db.transition(item_id, State.IA, "caption-start")
                try:
                    caption, batch_id, evaluations = self.ia.generate_caption_with_evidence(item.ia_context)
                except Exception as exc:
                    batch_id = getattr(exc, "batch_id", None)
                    evaluations = getattr(exc, "evaluations", ())
                    if batch_id and evaluations:
                        self.db.record_caption_candidates(item_id, batch_id, evaluations)
                    raise
                self.db.record_caption_candidates(item_id, batch_id, evaluations)
                self.db.set_caption(item_id, caption)
                item = self.db.get(item_id)

            self._check_shutdown()
            self.db.transition(item_id, State.STUDIO, "studio-start")
            studio_result = self.studio.process(item)
            if studio_result.working_path is not None:
                self.db.set_working(item_id, studio_result.working_path)
            self.db.set_result(item_id, studio_result.result_path)
            item = self.db.get(item_id)

            self._check_shutdown()
            self.db.transition(item_id, State.PUBLISHING, "hub-publish-start")
            publish_once = getattr(self.publisher, "publish_once", None)
            try:
                if callable(publish_once):
                    result = publish_once(item)
                else:
                    self.db.publication_started(item_id)
                    result = self.publisher.publish(item)
            except PublicationUnknownError as exc:
                self.db.transition(item_id, State.RECOVERY, f"publication-UNKNOWN: {exc}")
                return
            except Exception as exc:
                # A transport exception may occur after Telegram accepted the upload.
                try:
                    check = self.publisher.check_publication(self.db.get(item_id))
                except Exception:
                    check = PublicationCheck.UNKNOWN
                if check == PublicationCheck.CONFIRMED:
                    record = self.db.publication(item_id)
                    message_id = str(record["published_message_id"] or "") if record else ""
                    if message_id:
                        self.db.publication_confirmed(item_id, message_id)
                        self.db.transition(item_id, State.PUBLISHED,
                                           f"send raised but external reconciliation CONFIRMED {message_id}")
                        self.cleanup(item_id)
                        return
                reason = (
                    f"publication outcome UNKNOWN after {type(exc).__name__}: {exc}"
                    if check != PublicationCheck.ABSENT
                    else f"publish failed with confirmed ABSENT; explicit recovery required: {exc}"
                )
                self.db.transition(item_id, State.RECOVERY, reason)
                return

            message_id = str(getattr(result, "message_id", "") or "").strip()
            confirmed = bool(getattr(result, "confirmed", False)) and bool(message_id)
            if confirmed:
                self.db.publication_confirmed(item_id, message_id)
                self.db.transition(item_id, State.PUBLISHED, f"CONFIRMED message_id={message_id}")
                self.cleanup(item_id)
                return

            try:
                check = self.publisher.check_publication(self.db.get(item_id))
            except Exception:
                check = PublicationCheck.UNKNOWN
            if check == PublicationCheck.CONFIRMED and message_id:
                self.db.publication_confirmed(item_id, message_id)
                self.db.transition(item_id, State.PUBLISHED, f"reconciled CONFIRMED message_id={message_id}")
                self.cleanup(item_id)
                return
            self.db.transition(item_id, State.RECOVERY, f"publication not confirmed: {check.value}")
        except InterruptedError as exc:
            self.db.record_retryable_error(item_id, str(exc))
        except Exception as exc:
            self.log.exception("Pipeline item %s failed", item_id)
            try:
                self.db.transition(item_id, State.RECOVERY, f"{type(exc).__name__}: {exc}")
            except Exception:
                self.db.record_retryable_error(item_id, f"{type(exc).__name__}: {exc}")
            raise

    @staticmethod
    def _caption_enabled() -> bool:
        return (os.getenv("ARMORED_IA_ENABLED", "1") == "1"
                and os.getenv("ARMORED_IA_CAPTION_ENABLED", "1") == "1")

    def cleanup(self, item_id: str) -> None:
        item = self.db.get(item_id)
        if item.state != State.PUBLISHED:
            return
        publication = self.db.publication(item_id)
        confirmed = bool(publication and publication["confirmed"] and publication["published_message_id"])
        if not confirmed:
            try:
                check = self.publisher.check_publication(item)
            except Exception:
                return
            if check != PublicationCheck.CONFIRMED:
                return
            message_id = str(publication["published_message_id"] or "") if publication else ""
            if not message_id:
                return
            self.db.publication_confirmed(item_id, message_id)
        # ORIGINAL is immutable recovery evidence; only derived files are removed.
        for value in (item.working_path, item.result_path):
            if value:
                path = Path(value)
                try:
                    if path.is_file() and path != Path(item.original_path):
                        path.unlink()
                except OSError:
                    self.log.warning("Could not clean derived artifact %s", path, exc_info=True)
        self.db.mark_cleanup_completed(item_id)
