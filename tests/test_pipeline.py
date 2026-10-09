from pathlib import Path

from armoredcreator.config import Settings
from armoredcreator.db import Database
from armoredcreator.models import (AudioDecision, AudioKind, Candidate, ItemState,
                                   SourceRoute, Verification, VisionResult, VisionStatus)
from armoredcreator.pipeline import Coordinator


class FakeVision:
    def __init__(self, result): self.result = result
    def validate(self, source_url, *, timeout_seconds): return self.result


class FakeMaterializer:
    def __init__(self): self.calls = 0
    def download(self, candidate, destination):
        self.calls += 1
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"original")
        return destination


class FakeAudio:
    def classify(self, original):
        return AudioDecision(AudioKind.MUSIC_ONLY, 0.99, False, True, True)


class FakeStudio:
    def process(self, original, result, audio):
        assert audio.use_rvc is False
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_bytes(b"result")
        return result


class FakeHub:
    def __init__(self, status=Verification.CONFIRMED): self.status=status; self.publishes=0; self.cleanups=0
    def publish(self, result, destination_id, topic_id): self.publishes += 1; return 42
    def verify(self, content_id, destination_id, topic_id):
        return self.status, (42 if self.status is Verification.CONFIRMED else None), "fake verification"
    def cleanup(self, content_id, workspace): self.cleanups += 1


def make(tmp_path, vision_result, hub_status=Verification.CONFIRMED):
    settings = Settings(root=tmp_path, database_path=tmp_path / "db.sqlite",
                        source_routes=(SourceRoute(-1001, -2001, 7),))
    db = Database(settings.database_path)
    materializer = FakeMaterializer()
    hub = FakeHub(hub_status)
    coordinator = Coordinator(settings, db, FakeVision(vision_result), materializer,
                              FakeAudio(), FakeStudio(), hub)
    candidate = Candidate(-1001, 10, "https://s.example/item", "2026-01-01T00:00:00+00:00")
    assert coordinator.ingest([candidate]) == 1
    return coordinator, db, materializer, hub, candidate


def test_vision_rejected_never_downloads(tmp_path):
    c, db, materializer, hub, item = make(
        tmp_path, VisionResult(VisionStatus.REJECTED, None, "product unavailable"))
    assert c.process_one(item.content_id) == ItemState.WAITING_VISION.value
    assert materializer.calls == 0
    assert db.get_item(item.content_id)["state"] == ItemState.WAITING_VISION.value
    assert hub.publishes == 0


def test_vision_technical_error_is_recoverable_without_download(tmp_path):
    class BrokenVision:
        def validate(self, source_url, *, timeout_seconds): raise TimeoutError("vision timeout")
    c, db, materializer, hub, item = make(
        tmp_path, VisionResult(VisionStatus.REJECTED, None, "unused"))
    c.vision = BrokenVision()
    assert c.process_one(item.content_id) == ItemState.RECOVERY.value
    assert materializer.calls == 0
    assert hub.publishes == 0


def test_confirmed_publication_then_cleanup(tmp_path):
    c, db, materializer, hub, item = make(
        tmp_path, VisionResult(VisionStatus.APPROVED, "https://s.example/affiliate", "exact product"))
    assert c.process_one(item.content_id) == ItemState.PUBLISHED.value
    assert materializer.calls == 1
    assert hub.publishes == 1
    assert hub.cleanups == 1
    assert db.get_item(item.content_id)["state"] == ItemState.PUBLISHED.value
    assert db.get_publication(item.content_id)["status"] == Verification.CONFIRMED.value


def test_unknown_publication_is_not_resent(tmp_path):
    c, db, materializer, hub, item = make(
        tmp_path, VisionResult(VisionStatus.APPROVED, "https://s.example/affiliate", "exact product"),
        Verification.UNKNOWN)
    assert c.process_one(item.content_id) == ItemState.RECOVERY.value
    assert hub.publishes == 1
    assert hub.cleanups == 0
    assert c.process_one(item.content_id) == ItemState.RECOVERY.value
    assert hub.publishes == 1


def test_duplicate_discovery_is_idempotent(tmp_path):
    c, db, materializer, hub, item = make(
        tmp_path, VisionResult(VisionStatus.REJECTED, None, "unavailable"))
    assert c.ingest([item]) == 0
    assert materializer.calls == 0
