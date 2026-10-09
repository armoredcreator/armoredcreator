from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class ItemState(StrEnum):
    RECEIVED = "RECEIVED"
    VISION = "VISION"
    WAITING_VISION = "WAITING_VISION"
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    PUBLISHING = "PUBLISHING"
    RECOVERY = "RECOVERY"
    PUBLISHED = "PUBLISHED"


class VisionStatus(StrEnum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


class Verification(StrEnum):
    CONFIRMED = "CONFIRMED"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class AudioKind(StrEnum):
    PT_BR_NARRATION = "PT_BR_NARRATION"
    FOREIGN_SPEECH = "FOREIGN_SPEECH"
    MUSIC_ONLY = "MUSIC_ONLY"
    NO_AUDIO = "NO_AUDIO"
    UNCERTAIN = "UNCERTAIN"


@dataclass(frozen=True)
class SourceRoute:
    source_id: int
    destination_id: int
    topic_id: int


@dataclass(frozen=True)
class Candidate:
    source_id: int
    message_id: int
    source_url: str
    received_at: str
    metadata_json: str = "{}"

    @property
    def content_id(self) -> str:
        return f"{self.source_id}_{self.message_id}"


@dataclass(frozen=True)
class VisionResult:
    status: VisionStatus
    affiliate_url: str | None
    reason: str


@dataclass(frozen=True)
class AudioDecision:
    kind: AudioKind
    confidence: float
    use_rvc: bool
    mute_original: bool
    apply_effect: bool


@dataclass(frozen=True)
class Workspace:
    root: Path
    original: Path
    working: Path
    result: Path
