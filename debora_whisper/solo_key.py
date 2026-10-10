"""A key tapped on its own, such as Right Alt to switch voice chat."""
import time

# The keyboard package calls Right Alt "alt gr" on layouts that have AltGr
# (ABNT2, most of Europe) and "right alt" on the others.
ALIASES = {
    "right alt": ("right alt", "alt gr"),
    "alt gr": ("right alt", "alt gr"),
}


class SoloKeyTap:
    """Calls on_tap when `key` is pressed and released with no other key
    held or pressed in between, within max_seconds.

    The key is never suppressed, so AltGr+Q still types "/" and Ctrl+Alt
    shortcuts keep working; only a tap of the key alone counts. Feed it
    every event from ``keyboard.hook``.
    """

    def __init__(self, key: str, on_tap, max_seconds: float = 0.6,
                 clock=time.monotonic):
        key = key.strip().lower()
        self.names = frozenset(ALIASES.get(key, (key,)))
        self._on_tap = on_tap
        self.max_seconds = max_seconds
        self._clock = clock
        self._down_at = None
        self._spoiled = False
        # Other keys held, by scan code: a key's name can change between its
        # down and up events (AltGr+Q goes down as "/" and up as "q").
        self._held = set()

    def handle(self, event):
        name = (event.name or "").lower()
        if name in self.names:
            if event.event_type == "down":
                if self._down_at is None:  # auto-repeat keeps the first press
                    self._down_at = self._clock()
                    self._spoiled = bool(self._held)
            elif self._down_at is not None:
                solo = (not self._spoiled
                        and self._clock() - self._down_at <= self.max_seconds)
                self._down_at = None
                # Forget held keys: one whose up event the hook never saw
                # (Win+L, a UAC prompt) then blocks one tap, not all of them.
                # The cost is a second tap while still holding Ctrl.
                self._held.clear()
                if solo:
                    self._on_tap()
        elif event.event_type == "down":
            self._held.add(event.scan_code)
            self._spoiled = True
        else:
            self._held.discard(event.scan_code)
