import pytest

from armoredcreator.db import Database
from armoredcreator.models import Candidate, ItemState


def candidate(source, message):
    return Candidate(source, message, "https://example.invalid", "2026-01-01T00:00:00+00:00")


def test_candidate_is_idempotent_and_checkpoint_never_moves_back(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    assert db.record_candidate(candidate(1, 10))
    assert not db.record_candidate(candidate(1, 10))
    db.set_checkpoint(1, 10)
    db.set_checkpoint(1, 20)
    with pytest.raises(ValueError):
        db.set_checkpoint(1, 19)


def test_only_one_media_item_can_be_active(tmp_path):
    db = Database(tmp_path / "db.sqlite")
    first = candidate(1, 1)
    second = candidate(1, 2)
    db.record_candidate(first)
    db.record_candidate(second)
    db.transition(first.content_id, ItemState.DOWNLOADING)
    with pytest.raises(Exception):
        db.transition(second.content_id, ItemState.DOWNLOADING)
    assert db.get_item(second.content_id)["state"] == ItemState.RECEIVED.value
