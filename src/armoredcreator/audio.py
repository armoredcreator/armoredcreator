from __future__ import annotations

from .models import AudioDecision, AudioKind


def decide_audio(kind: AudioKind, confidence: float, *, pt_br_threshold: float = 0.85) -> AudioDecision:
    """Fail closed: RVC is allowed only for confidently identified PT-BR narration."""
    confidence = max(0.0, min(1.0, float(confidence)))
    use_rvc = kind is AudioKind.PT_BR_NARRATION and confidence >= pt_br_threshold
    return AudioDecision(
        kind=kind,
        confidence=confidence,
        use_rvc=use_rvc,
        mute_original=not use_rvc,
        apply_effect=not use_rvc,
    )
