from __future__ import annotations

from pathlib import Path
from typing import Protocol, Sequence

from .models import AudioDecision, Candidate, Verification, VisionResult


class SyncAdapter(Protocol):
    def discover(self, source_id: int, after_message_id: int) -> Sequence[Candidate]: ...


class VisionAdapter(Protocol):
    def validate(self, source_url: str, *, timeout_seconds: float) -> VisionResult: ...


class Materializer(Protocol):
    def download(self, candidate: Candidate, destination: Path) -> Path: ...


class AudioClassifier(Protocol):
    def classify(self, original: Path) -> AudioDecision: ...


class StudioAdapter(Protocol):
    def process(self, original: Path, result: Path, audio: AudioDecision) -> Path: ...


class HubAdapter(Protocol):
    def publish(self, result: Path, destination_id: int, topic_id: int) -> int: ...
    def verify(self, content_id: str, destination_id: int, topic_id: int) -> tuple[Verification, int | None, str]: ...
    def cleanup(self, content_id: str, workspace: Path) -> None: ...
