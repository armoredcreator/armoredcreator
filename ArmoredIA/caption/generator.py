from __future__ import annotations

import os
import uuid
from typing import Any

from .selector import CaptionCandidateEvaluation, CaptionGenerationError, CaptionSelector
from ..providers.gemini import GeminiProvider


class CaptionGenerator:
    """One provider batch, deterministic local policy/ranking, durable evidence."""

    def __init__(self, provider=None, selector: CaptionSelector | None = None):
        self.provider = provider or GeminiProvider()
        self.selector = selector or CaptionSelector()

    def generate(self, context: dict[str, Any]) -> str:
        caption, _batch_id, _evaluations = self.generate_with_evidence(context)
        return caption

    def generate_with_evidence(
        self, context: dict[str, Any]
    ) -> tuple[str, str, tuple[CaptionCandidateEvaluation, ...]]:
        batch_id = uuid.uuid4().hex
        limit = max(1, min(10, int(os.getenv("ARMORED_IA_MAX_CANDIDATES", "10"))))
        product_name = str((context or {}).get("productName") or "")
        candidates = self.provider.generate_candidates("caption", context or {}, limit)
        evaluations = self.selector.evaluate(
            list(candidates or []),
            product_name=product_name,
            product_context=context or {},
        )
        try:
            selection, marked = self.selector.choose(evaluations)
        except CaptionGenerationError as exc:
            exc.batch_id = batch_id
            exc.evaluations = evaluations
            raise
        return selection.caption, batch_id, marked
