from pathlib import Path

from armoredcreator.collector import HistoricalCollector
from armoredcreator.config import Settings
from armoredcreator.db import Database
from armoredcreator.models import (AudioDecision, AudioKind, Candidate, DiscoveryPage,
                                   ItemState, SourceRoute, Verification, VisionResult, VisionStatus)
from armoredcreator.pipeline import Coordinator


class FakeSync:
    def __init__(self, page): self.page = page
    def discover(self, source_id, after_message_id): return self.page


class FakeVision:
    def __init__(self, result=None, error=None): self.result=result; self.error=error
    def validate(self, source_url, *, timeout_seconds):
        if self.error: raise self.error
        return self.result


class FakeMaterializer:
    def __init__(self): self.calls=0
    def download(self, candidate, destination):
        self.calls += 1
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"original")
        return destination


class FakeAudio:
    def classify(self, original):
        return AudioDecision(AudioKind.MUSIC_ONLY, .99, False, True, True)


class FakeStudio:
    def process(self, original, result, audio):
        assert not audio.use_rvc
        result.parent.mkdir(parents=True, exist_ok=True)
        result.write_bytes(b"result")
        return result


class FakeHub:
    def publish(self, result, destination_id, topic_id): return 42
    def verify(self, content_id, destination_id, topic_id):
        return Verification.CONFIRMED, 42, "verified"
    def cleanup(self, content_id, workspace): pass


def setup(tmp_path, vision):
    settings = Settings(root=tmp_path, database_path=tmp_path / "db.sqlite",
                        source_routes=(SourceRoute(-1, -2, 5),))
    db = Database(settings.database_path)
    materializer = FakeMaterializer()
    coordinator = Coordinator(settings, db, vision, materializer, FakeAudio(), FakeStudio(), FakeHub())
    return db, materializer, coordinator


def test_historical_scan_validates_without_downloading(tmp_path):
    db, materializer, coordinator = setup(
        tmp_path, FakeVision(VisionResult(VisionStatus.APPROVED, "https://s.example/aff", "approved")))
    candidate = Candidate(-1, 12, "https://example.invalid/p", "2026-01-01T00:00:00Z")
    collector = HistoricalCollector(FakeSync(DiscoveryPage((candidate,), 20, True)), coordinator, db)
    result = collector.scan_page(-1)
    assert result.newly_recorded == 1
    assert result.validated == 1
    assert result.mode == "LIVE"
    assert materializer.calls == 0
    assert db.get_item(candidate.content_id)["state"] == ItemState.READY.value
    assert db.get_checkpoint(-1)["last_message_id"] == 20


def test_historical_scan_does_not_advance_past_technical_failure(tmp_path):
    db, materializer, coordinator = setup(tmp_path, FakeVision(error=TimeoutError("offline")))
    candidate = Candidate(-1, 12, "https://example.invalid/p", "2026-01-01T00:00:00Z")
    collector = HistoricalCollector(FakeSync(DiscoveryPage((candidate,), 20, True)), coordinator, db)
    result = collector.scan_page(-1)
    assert result.blocked_at_message_id == 12
    assert result.mode == "CATCH_UP"
    assert db.get_checkpoint(-1) is None
    assert db.get_item(candidate.content_id)["state"] == ItemState.RECOVERY.value
    assert materializer.calls == 0
