"""
Color math + terminal color encoding.

Everything is kept as plain RGB tuples internally and only turned into escape
sequences at the very end, which is what lets one codebase render truecolor on
Windows Terminal, 256 colors on an old xterm, and 16 colors inside a serial
console.
"""

from __future__ import annotations

import colorsys
import os
import sys

RGB = tuple[int, int, int]

# --------------------------------------------------------------------------
# color maths
# --------------------------------------------------------------------------


def clamp(v: float, lo: float = 0.0, hi: float = 255.0) -> int:
    return int(lo if v < lo else hi if v > hi else v)


def hsv(h: float, s: float, v: float) -> RGB:
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return (clamp(r * 255), clamp(g * 255), clamp(b * 255))


def to_hsv(c: RGB) -> tuple[float, float, float]:
    r, g, b = (x / 255.0 for x in c)
    return colorsys.rgb_to_hsv(r, g, b)


def mix(a: RGB, b: RGB, t: float) -> RGB:
    t = max(0.0, min(1.0, t))
    return (clamp(a[0] + (b[0] - a[0]) * t), clamp(a[1] + (b[1] - a[1]) * t), clamp(a[2] + (b[2] - a[2]) * t))


def lighten(c: RGB, t: float) -> RGB:
    return mix(c, (255, 255, 255), t)


def darken(c: RGB, t: float) -> RGB:
    return mix(c, (0, 0, 0), t)


def saturate(c: RGB, t: float) -> RGB:
    h, s, v = to_hsv(c)
    return hsv(h, min(1.0, s + t), v)


def desaturate(c: RGB, t: float) -> RGB:
    return saturate(c, -t)


def hue_shift(c: RGB, delta: float) -> RGB:
    h, s, v = to_hsv(c)
    return hsv(h + delta, s, v)


def rotate_toward(c: RGB, target_hue: float, t: float) -> RGB:
    h, s, v = to_hsv(c)
    # shortest way around the hue wheel
    d = (target_hue - h + 0.5) % 1.0 - 0.5
    return hsv(h + d * t, s, v)


def lerp_ramp(stops: list[RGB], t: float) -> RGB:
    """Sample a gradient defined by ``stops`` (n >= 1) at position t in [0,1]."""
    if not stops:
        return (255, 255, 255)
    if len(stops) == 1:
        return stops[0]
    t = max(0.0, min(1.0, t))
    pos = t * (len(stops) - 1)
    i = int(pos)
    if i >= len(stops) - 1:
        return stops[-1]
    return mix(stops[i], stops[i + 1], pos - i)


def grayscale(c: RGB) -> RGB:
    y = clamp(0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2])
    return (y, y, y)


# --------------------------------------------------------------------------
# encoding
# --------------------------------------------------------------------------

MODE_TRUECOLOR = "truecolor"
MODE_256 = "256"
MODE_16 = "16"
MODE_NONE = "none"

_CUBE = [0, 95, 135, 175, 215, 255]
_BASIC16 = [
    (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
    (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
    (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
    (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
]


def rgb_to_256(c: RGB) -> int:
    r, g, b = c
    if abs(r - g) < 12 and abs(g - b) < 12 and abs(r - b) < 12:
        if r < 8:
            return 16
        if r > 248:
            return 231
        return 232 + int((r - 8) / 247 * 24)
    ri = min(range(6), key=lambda i: abs(_CUBE[i] - r))
    gi = min(range(6), key=lambda i: abs(_CUBE[i] - g))
    bi = min(range(6), key=lambda i: abs(_CUBE[i] - b))
    return 16 + 36 * ri + 6 * gi + bi


def rgb_to_16(c: RGB) -> int:
    best, bd = 0, 1 << 30
    for i, b in enumerate(_BASIC16):
        d = (c[0] - b[0]) ** 2 + (c[1] - b[1]) ** 2 + (c[2] - b[2]) ** 2
        if d < bd:
            best, bd = i, d
    return best


class Colorizer:
    """Turns RGB into the shortest escape sequence the terminal understands."""

    def __init__(self, mode: str = MODE_TRUECOLOR):
        self.mode = mode
        self._cache: dict[tuple[bool, RGB], str] = {}

    def code(self, c: RGB, bg: bool = False) -> str:
        if self.mode == MODE_NONE:
            return ""
        key = (bg, c)
        hit = self._cache.get(key)
        if hit is not None:
            return hit
        base = 48 if bg else 38
        if self.mode == MODE_TRUECOLOR:
            out = f"\x1b[{base};2;{c[0]};{c[1]};{c[2]}m"
        elif self.mode == MODE_256:
            out = f"\x1b[{base};5;{rgb_to_256(c)}m"
        else:
            out = f"\x1b[{base};{rgb_to_16(c)}m"
        self._cache[key] = out
        return out


def detect_mode(explicit: str | None = None, stream=None) -> str:
    """Pick the best color mode available, honouring NO_COLOR / dumb terminals."""
    stream = stream or sys.stdout
    if explicit and explicit != "auto":
        return explicit
    if os.environ.get("NO_COLOR"):
        return MODE_NONE
    if os.environ.get("HOLLYWEEB_COLOR"):
        return os.environ["HOLLYWEEB_COLOR"]
    if os.environ.get("TERM", "").lower() in ("dumb", ""):
        if os.name != "nt":
            return MODE_16
    try:
        if not stream.isatty():
            return MODE_256  # piped: still pretty in logs/pagers
    except Exception:
        pass
    if os.name == "nt":
        # Windows Terminal / ConEmu / ANSICON / mintty all advertise one of these
        if os.environ.get("WT_SESSION") or os.environ.get("ConEmuANSI") == "ON":
            return MODE_TRUECOLOR
        if os.environ.get("TERM", "").lower().startswith(("xterm", "screen", "tmux", "cygwin", "msys")):
            return MODE_TRUECOLOR
        if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
            return MODE_TRUECOLOR
        return MODE_256
    ct = os.environ.get("COLORTERM", "").lower()
    term = os.environ.get("TERM", "").lower()
    if ct in ("truecolor", "24bit") or "truecolor" in term or "direct" in term:
        return MODE_TRUECOLOR
    if "256color" in term or "kitty" in term or "alacritty" in term or "wezterm" in term:
        return MODE_256
    return MODE_16
