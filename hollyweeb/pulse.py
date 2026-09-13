"""
A tiny shared beat clock.

`App` refreshes this every frame from the music player, and widgets that feel
rhythmic (bongo cat, VU meters, spectrum, vitals) read it so the visuals lock to
the soundtrack. When music is off, `active` is False and widgets fall back to
their own internal clocks — so nothing depends on audio being available.
"""

from __future__ import annotations

active = False
bpm = 0.0
beat = 0.0      # 0..1 within the current beat
bar = 0.0       # 0..1 within the current bar
level = 0.0     # fake loudness 0..1, follows the kick


def set_clock(active_: bool, bpm_: float = 0.0, beat_: float = 0.0,
              bar_: float = 0.0, level_: float = 0.0) -> None:
    global active, bpm, beat, bar, level
    active = bool(active_)
    bpm = float(bpm_)
    beat = float(beat_)
    bar = float(bar_)
    level = float(level_)


def reset() -> None:
    set_clock(False)
