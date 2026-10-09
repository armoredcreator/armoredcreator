from __future__ import annotations

from dataclasses import dataclass

from .contracts import SyncAdapter
from .db import Database
from .models import DiscoveryPage, ItemState
from .pipeline import Coordinator


@dataclass(frozen=True)
class ScanResult:
    discovered: int
    newly_recorded: int
    validated: int
    waiting_vision: int
    blocked_at_message_id: int | None
    checkpoint: int
    mode: str


class HistoricalCollector:
    """Phase A: discover and validate links without downloading any media."""

    def __init__(self, sync: SyncAdapter, coordinator: Coordinator, db: Database):
        self.sync = sync
        self.coordinator = coordinator
        self.db = db

    def scan_page(self, source_id: int) -> ScanResult:
        saved = self.db.get_checkpoint(source_id)
        after = int(saved["last_message_id"]) if saved else 0
        page: DiscoveryPage = self.sync.discover(source_id, after)
        candidates = sorted(page.candidates, key=lambda c: c.message_id)
        newly_recorded = self.coordinator.ingest(list(candidates))
        validated = 0
        waiting = 0
        safe_checkpoint = after
        blocked: int | None = None

        for candidate in candidates:
            if candidate.message_id <= after:
                continue
            item = self.db.get_item(candidate.content_id)
            if item is None:
                blocked = candidate.message_id
                break
            publication = self.db.get_publication(candidate.content_id)
            if publication:
                if publication["status"] != "CONFIRMED" or not publication["message_id"]:
                    blocked = candidate.message_id
                    break
                if item["state"] != ItemState.PUBLISHED.value:
                    self.db.transition(candidate.content_id, ItemState.PUBLISHED,
                                       detail={"reconciled_from_persisted_confirmation": True})
                outcome = ItemState.PUBLISHED.value
            else:
                state = item["state"]
                if state in (ItemState.READY.value, ItemState.WAITING_VISION.value,
                             ItemState.PUBLISHED.value):
                    outcome = state
                else:
                    outcome = self.coordinator.validate_one(candidate.content_id)
                    validated += 1
            if outcome == ItemState.WAITING_VISION.value:
                waiting += 1
            if outcome not in (ItemState.READY.value, ItemState.WAITING_VISION.value,
                               ItemState.PUBLISHED.value):
                blocked = candidate.message_id
                break
            safe_checkpoint = candidate.message_id
            self.db.set_checkpoint(source_id, safe_checkpoint, "CATCH_UP")

        if blocked is None and page.history_exhausted:
            # Only mark LIVE when every candidate in the scanned range is safely classified
            # and no unresolved technical item remains for this source.
            blockers = self.db.items_for_source(source_id, (
                ItemState.RECEIVED.value, ItemState.VISION.value, ItemState.RECOVERY.value,
                ItemState.DOWNLOADING.value, ItemState.PROCESSING.value, ItemState.PUBLISHING.value,
            ))
            if not blockers:
                safe_checkpoint = max(safe_checkpoint, int(page.high_watermark))
                self.db.set_checkpoint(source_id, safe_checkpoint, "LIVE")
                mode = "LIVE"
            else:
                mode = "CATCH_UP"
        else:
            mode = "CATCH_UP"

        return ScanResult(len(candidates), newly_recorded, validated, waiting,
                          blocked, safe_checkpoint, mode)
