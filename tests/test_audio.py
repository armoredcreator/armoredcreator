from armoredcreator.audio import decide_audio
from armoredcreator.models import AudioKind


def test_only_confident_pt_br_narration_uses_rvc():
    allowed = decide_audio(AudioKind.PT_BR_NARRATION, 0.95)
    assert allowed.use_rvc is True
    assert allowed.mute_original is False
    assert allowed.apply_effect is False

    for kind in (AudioKind.FOREIGN_SPEECH, AudioKind.MUSIC_ONLY, AudioKind.NO_AUDIO, AudioKind.UNCERTAIN):
        decision = decide_audio(kind, 0.99)
        assert decision.use_rvc is False
        assert decision.mute_original is True
        assert decision.apply_effect is True


def test_low_confidence_portuguese_does_not_use_rvc():
    decision = decide_audio(AudioKind.PT_BR_NARRATION, 0.5)
    assert not decision.use_rvc
    assert decision.mute_original
    assert decision.apply_effect
