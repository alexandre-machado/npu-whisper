"""Tests for config validation."""
import pytest

from debora_whisper.dictation_engine import validate_config, DEFAULT_CONFIG


class TestConfigValidation:
    def test_valid_config_passes(self):
        config = DEFAULT_CONFIG.copy()
        validate_config(config)  # should not raise

    def test_invalid_device_raises(self):
        config = {**DEFAULT_CONFIG, "device": "TPU"}
        with pytest.raises(ValueError, match="device"):
            validate_config(config)

    def test_invalid_model_size_raises(self):
        config = {**DEFAULT_CONFIG, "model_size": "huge"}
        with pytest.raises(ValueError, match="model_size"):
            validate_config(config)

    def test_invalid_sample_rate_raises(self):
        config = {**DEFAULT_CONFIG, "sample_rate": "banana"}
        with pytest.raises(ValueError, match="sample_rate"):
            validate_config(config)

    def test_invalid_max_record_seconds_raises(self):
        config = {**DEFAULT_CONFIG, "max_record_seconds": -5}
        with pytest.raises(ValueError, match="max_record_seconds"):
            validate_config(config)

    @pytest.mark.parametrize("key", ["vad_end_silence_seconds", "vad_incomplete_silence_seconds"])
    @pytest.mark.parametrize("value", [None, True, "3", 0, -1, float("nan"), float("inf")])
    def test_invalid_vad_silence_raises(self, key, value):
        with pytest.raises(ValueError, match=key):
            validate_config({**DEFAULT_CONFIG, key: value})

    def test_existing_config_without_vad_keys_uses_defaults(self):
        config = {key: value for key, value in DEFAULT_CONFIG.items() if not key.startswith("vad_")}
        validate_config(config)


def test_continuous_startup_begins_in_dictation():
    from debora_whisper.dictation_engine import start_in_dictation
    config = {"continuous_listening": True, "voice_chat": True}
    assert start_in_dictation(config) is True  # still warm voice chat up
    assert config["voice_chat"] is False


def test_warm_voice_chat_loads_it_while_dictating():
    from unittest.mock import MagicMock, patch
    from debora_whisper.dictation_engine import DEFAULT_CONFIG, DictationApp
    app = DictationApp({**DEFAULT_CONFIG, "beep_on_start": False, "voice_chat": False})
    app.warm_voice_chat = True
    with patch.dict("sys.modules", {"keyboard": MagicMock()}),             patch.object(app, "_start_loader"),             patch.object(app, "_start_segment_consumer"),             patch.object(app, "_warm_up_voice_chat") as warm:
        app.start_background()
    warm.assert_called_once()


def test_startup_keeps_voice_chat_without_continuous_or_when_requested():
    from debora_whisper.dictation_engine import start_in_dictation
    config = {"continuous_listening": False, "voice_chat": True}
    assert start_in_dictation(config) is False
    assert config["voice_chat"] is True
    config = {"continuous_listening": True, "voice_chat": True}
    start_in_dictation(config, voice_chat_requested=True)
    assert config["voice_chat"] is True
