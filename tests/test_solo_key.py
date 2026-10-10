"""Right Alt tapped alone switches voice chat; AltGr combos keep typing."""
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from debora_whisper.dictation_engine import DEFAULT_CONFIG, DictationApp, validate_config
from debora_whisper.solo_key import SoloKeyTap


class Clock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


# Scan codes for the event names used below.
CODES = {"right alt": 56, "alt gr": 541, "ctrl": 29, "q": 16, "/": 16, "windows": 91}


def _tap(key="right alt"):
    clock, taps = Clock(), []
    tap = SoloKeyTap(key, lambda: taps.append(clock.now), clock=clock)

    def send(name, kind, after=0.0):
        clock.now += after
        tap.handle(SimpleNamespace(name=name, event_type=kind, scan_code=CODES[name]))
    return send, taps


@pytest.mark.parametrize("name", ["right alt", "alt gr"])
def test_tap_alone_fires_for_both_layout_names(name):
    send, taps = _tap()
    send(name, "down")
    send(name, "up", after=0.1)
    assert len(taps) == 1


def test_altgr_combo_does_not_fire():
    send, taps = _tap()
    send("alt gr", "down")
    send("q", "down", after=0.05)
    send("q", "up", after=0.05)
    send("alt gr", "up", after=0.05)
    assert taps == []


def test_key_held_before_does_not_fire():
    send, taps = _tap()
    send("ctrl", "down")
    send("right alt", "down", after=0.1)
    send("right alt", "up", after=0.1)
    assert taps == []


def test_released_key_no_longer_blocks():
    send, taps = _tap()
    send("ctrl", "down")
    send("ctrl", "up", after=0.1)
    send("right alt", "down", after=0.1)
    send("right alt", "up", after=0.1)
    assert len(taps) == 1


def test_long_held_modifier_still_blocks():
    send, taps = _tap()
    send("ctrl", "down")
    send("right alt", "down", after=5)
    send("right alt", "up", after=0.1)
    assert taps == []


def test_key_name_changing_between_down_and_up_does_not_stick():
    send, taps = _tap()
    send("alt gr", "down")
    send("/", "down", after=0.05)  # AltGr+Q
    send("alt gr", "up", after=0.05)
    send("q", "up", after=0.05)    # same key, named without AltGr
    send("alt gr", "down", after=0.1)
    send("alt gr", "up", after=0.1)
    assert len(taps) == 1


def test_missed_key_up_blocks_only_one_tap():
    send, taps = _tap()
    send("windows", "down")  # its up event lost behind the lock screen
    send("right alt", "down", after=0.1)
    send("right alt", "up", after=0.1)
    assert taps == []
    send("right alt", "down", after=0.1)
    send("right alt", "up", after=0.1)
    assert len(taps) == 1


def test_long_hold_does_not_fire_and_autorepeat_keeps_first_press():
    send, taps = _tap()
    send("right alt", "down")
    for _ in range(10):
        send("right alt", "down", after=0.1)  # auto-repeat
    send("right alt", "up", after=0.1)
    assert taps == []


def test_up_without_down_is_ignored():
    send, taps = _tap()
    send("right alt", "up")
    assert taps == []


def test_engine_hotkey_calls_app_callback():
    app = DictationApp({**DEFAULT_CONFIG, "beep_on_start": False})
    app.on_voice_chat_toggle = MagicMock()
    keyboard = MagicMock()
    app._register_voice_chat_hotkey(keyboard)
    handler = keyboard.hook.call_args.args[0]
    handler(SimpleNamespace(name="alt gr", event_type="down", scan_code=541))
    handler(SimpleNamespace(name="alt gr", event_type="up", scan_code=541))
    app.on_voice_chat_toggle.assert_called_once()


def test_engine_hotkey_disabled_when_empty():
    app = DictationApp({**DEFAULT_CONFIG, "beep_on_start": False,
                        "voice_chat_hotkey": ""})
    keyboard = MagicMock()
    app._register_voice_chat_hotkey(keyboard)
    keyboard.hook.assert_not_called()


def test_engine_hotkey_without_app_switches_engine():
    app = DictationApp({**DEFAULT_CONFIG, "beep_on_start": False, "voice_chat": False})
    with patch.object(app, "set_voice_chat") as set_voice_chat:
        app._on_voice_chat_hotkey()
        for _ in range(200):
            if set_voice_chat.called:
                break
            time.sleep(0.005)
    set_voice_chat.assert_called_once_with(True)


def test_config_rejects_non_string_hotkey():
    with pytest.raises(ValueError, match="voice_chat_hotkey"):
        validate_config({**DEFAULT_CONFIG, "voice_chat_hotkey": 1})
