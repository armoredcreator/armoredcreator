from armoredcreator.collector import HistoricalCollector
from armoredcreator.models import Candidate, DiscoveryPage, ItemState, VisionResult, VisionStatus
from test_pipeline import FakeAudio, FakeHub, FakeMaterializer, FakeStudio, FakeVision
from armoredcreator.config import Settings
from armoredcreator.db import Database
from armoredcreator.models import SourceRoute
from armoredcreator.pipeline import Coordinator


class FakeSync:
    def __init__(self, page): self.page = page
    def discover(self, source_id, after_message_id): return self.page


def test_historical_scan_validates_without_downloading(tmp_path):
    settings = Settings(root=tmp_path, database_path=tmp_path / "db.sqlite",
                        source_routes=(SourceRoute(-1, -2, 5),))
    db = Database(settings.database_path)
    candidate = Candidate(-1, 12, "https://example.invalid/p", "2026-01-01T00:00:00Z")
    materializer = FakeMaterializer()
    coordinator = Coordinator(settings, db,
        FakeVision(VisionResult(VisionStatus.APPROVED, "https://s.example/aff", "approved")),
        materializer, FakeAudio(), FakeStudio(), FakeHub())
    collector = HistoricalCollector(FakeSync(DiscoveryPage((candidate,), 20, True)), coordinator, db)
    result = collector.scan_page(-1)
    assert result.newly_recorded == 1
    assert result.validated == 1
    assert result.mode == "LIVE"
    assert materializer.calls == 0
    assert db.get_item(candidate.content_id)["state"] == ItemState.READY.value
    assert db.get_checkpoint(-1)["last_message_id"] == 20


def test_historical_scan_does_not_advance_past_technical_failure(tmp_path):
    settings = Settings(root=tmp_path, database_path=tmp_path / "db.sqlite",
                        source_routes=(SourceRoute(-1, -2, 5),))
    db = Database(settings.database_path)
    candidate = Candidate(-1, 12, "https://example.invalid/p", "2026-01-01T00:00:00Z")
    class BrokenVision:
        def validate(self, source_url, *, timeout_seconds): raise TimeoutError("offline")
    coordinator = Coordinator(settings, db, BrokenVision(), FakeMaterializer(),
                              FakeAudio(), FakeStudio(), FakeHub())
    collector = HistoricalCollector(FakeSync(DiscoveryPage((candidate,), 20, True)), coordinator, db)
    result = collector.scan_page(-1)
    assert result.blocked_at_message_id == 12
    assert result.mode == "CATCH_UP"
    assert db.get_checkpoint(-1) is None
    assert db.get_item(candidate.content_id)["state"] == ItemState.RECOVERY.value
