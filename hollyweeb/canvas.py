"""
A tiny double-buffered character canvas with clipped sub-views.

The whole app is drawn into one `Canvas`, diffed against the previous frame,
and flushed as cursor-positioning escape sequences. That is what makes a
20-pane, 30 fps, truecolor dashboard possible from pure Python in one terminal
window on any OS.
"""

from __future__ import annotations

from .color import RGB
from .term import RESET

# style bits
BOLD = 1
DIM = 2
ITALIC = 4
UNDERLINE = 8

STYLE_ON = {
    BOLD: "\x1b[1m",
    DIM: "\x1b[2m",
    ITALIC: "\x1b[3m",
    UNDERLINE: "\x1b[4m",
}

# Turn styles off without clobbering the current fg/bg colour (RESET would).
STYLE_OFF = "\x1b[22m\x1b[23m\x1b[24m"


class Canvas:
    """Flat, mutable grid of (char, fg, bg, style) cells."""

    __slots__ = ("w", "h", "ch", "fg", "bg", "st")

    def __init__(self, w: int, h: int):
        self.w = max(1, w)
        self.h = max(1, h)
        n = self.w * self.h
        self.ch = [" "] * n
        self.fg: list[RGB | None] = [None] * n
        self.bg: list[RGB | None] = [None] * n
        self.st = [0] * n

    # -- basics ------------------------------------------------------------
    def clear(self, ch: str = " ", fg: RGB | None = None, bg: RGB | None = None, st: int = 0) -> None:
        n = self.w * self.h
        self.ch = [ch] * n
        self.fg = [fg] * n
        self.bg = [bg] * n
        self.st = [st] * n

    def put(self, x: int, y: int, ch: str = " ", fg: RGB | None = None, bg: RGB | None = None, st: int = 0) -> None:
        if not ch:
            return
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            self.ch[i] = ch[0]
            self.fg[i] = fg
            self.bg[i] = bg
            self.st[i] = st

    def get(self, x: int, y: int) -> str:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.ch[y * self.w + x]
        return " "

    # -- diffing -----------------------------------------------------------
    def diff_to(self, prev: "Canvas | None", cz) -> str:
        """Return escape sequences that morph ``prev`` into ``self``."""
        out: list[str] = []
        w, h = self.w, self.h
        for y in range(h):
            base = y * w
            x = 0
            while x < w:
                i = base + x
                if prev is not None and (
                    prev.ch[i] == self.ch[i]
                    and prev.fg[i] == self.fg[i]
                    and prev.bg[i] == self.bg[i]
                    and prev.st[i] == self.st[i]
                ):
                    x += 1
                    continue
                start = x
                while x < w:
                    j = base + x
                    same = (
                        prev is not None
                        and prev.ch[j] == self.ch[j]
                        and prev.fg[j] == self.fg[j]
                        and prev.bg[j] == self.bg[j]
                        and prev.st[j] == self.st[j]
                    )
                    if same:
                        break
                    x += 1
                out.append(f"\x1b[{y + 1};{start + 1}H")
                cur_fg: RGB | None = object()  # type: ignore[assignment]
                cur_bg: RGB | None = object()  # type: ignore[assignment]
                cur_st = -1
                buf: list[str] = []
                for k in range(start, x):
                    j = base + k
                    fg, bg, st = self.fg[j], self.bg[j], self.st[j]
                    if fg != cur_fg:
                        buf.append(cz.code(fg, False) if fg is not None else "\x1b[39m")
                        cur_fg = fg
                    if bg != cur_bg:
                        buf.append(cz.code(bg, True) if bg is not None else "\x1b[49m")
                        cur_bg = bg
                    if st != cur_st:
                        if st == 0:
                            buf.append(STYLE_OFF)
                        else:
                            if cur_st:
                                buf.append(STYLE_OFF)
                            buf.append(STYLE_ON.get(st, ""))
                        cur_st = st
                    buf.append(self.ch[j])
                out.append("".join(buf))
                out.append(RESET)
        return "".join(out)

    def to_text(self) -> str:
        return "\n".join("".join(self.ch[y * self.w : (y + 1) * self.w]) for y in range(self.h))


class View:
    """A clipped window into a Canvas; widgets only ever touch a View."""

    __slots__ = ("cv", "x0", "y0", "w", "h", "transparent")

    def __init__(self, cv: Canvas, x0: int, y0: int, w: int, h: int, transparent: bool = True):
        self.cv = cv
        self.x0 = x0
        self.y0 = y0
        self.w = max(0, w)
        self.h = max(0, h)
        self.transparent = transparent

    def sub(self, x: int, y: int, w: int, h: int) -> "View":
        return View(self.cv, self.x0 + x, self.y0 + y, w, h, self.transparent)

    # -- primitives --------------------------------------------------------
    def put(self, x: int, y: int, ch: str = " ", fg: RGB | None = None, bg: RGB | None = None, st: int = 0) -> None:
        if not ch:
            return
        if 0 <= x < self.w and 0 <= y < self.h:
            self.cv.put(self.x0 + x, self.y0 + y, ch[0], fg, bg, st)

    def get(self, x: int, y: int) -> str:
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.cv.get(self.x0 + x, self.y0 + y)
        return " "

    def text(self, x: int, y: int, s: str, fg: RGB | None = None, bg: RGB | None = None, st: int = 0) -> None:
        if y < 0 or y >= self.h:
            return
        for k, ch in enumerate(s):
            if ch == " " and self.transparent:
                if bg is None:
                    continue
            self.put(x + k, y, ch, fg, bg, st)

    def fill(self, x: int, y: int, w: int, h: int, ch: str = " ", fg: RGB | None = None, bg: RGB | None = None, st: int = 0) -> None:
        for yy in range(max(0, y), min(self.h, y + h)):
            for xx in range(max(0, x), min(self.w, x + w)):
                self.put(xx, yy, ch, fg, bg, st)

    def hline(self, x: int, y: int, w: int, ch: str = "─", fg: RGB | None = None, bg: RGB | None = None, st: int = 0) -> None:
        for xx in range(x, x + w):
            self.put(xx, y, ch, fg, bg, st)

    def vline(self, x: int, y: int, h: int, ch: str = "│", fg: RGB | None = None, bg: RGB | None = None, st: int = 0) -> None:
        for yy in range(y, y + h):
            self.put(x, yy, ch, fg, bg, st)

    def box(self, fg: RGB | None = None, bg: RGB | None = None, style: str = "round", title: str = "",
            title_fg: RGB | None = None, st: int = 0) -> None:
        self.fill(0, 0, self.w, self.h, " ", None, bg)
        if self.w < 2 or self.h < 2:
            return
        sets = {
            "round": ("╭", "╮", "╰", "╯", "─", "│"),
            "sharp": ("┌", "┐", "└", "┘", "─", "│"),
            "double": ("╔", "╗", "╚", "╝", "═", "║"),
            "heavy": ("┏", "┓", "┗", "┛", "━", "┃"),
            "dots": ("·", "·", "·", "·", "·", "·"),
        }
        tl, tr, bl, br, hz, vt = sets.get(style, sets["round"])
        self.hline(1, 0, self.w - 2, hz, fg, bg, st)
        self.hline(1, self.h - 1, self.w - 2, hz, fg, bg, st)
        self.vline(0, 1, self.h - 2, vt, fg, bg, st)
        self.vline(self.w - 1, 1, self.h - 2, vt, fg, bg, st)
        self.put(0, 0, tl, fg, bg, st)
        self.put(self.w - 1, 0, tr, fg, bg, st)
        self.put(0, self.h - 1, bl, fg, bg, st)
        self.put(self.w - 1, self.h - 1, br, fg, bg, st)
        if title and self.w > 6:
            label = " " + title[: max(0, self.w - 6)] + " "
            self.text(2, 0, label, title_fg or fg, bg, BOLD)

    # -- composite helpers -------------------------------------------------
    def vgrad(self, x: int, y: int, w: int, h: int, stops: list[RGB], ch: str = "█", bg: RGB | None = None) -> None:
        from .color import lerp_ramp

        if h <= 0:
            return
        for i in range(h):
            t = i / max(1, h - 1)
            c = lerp_ramp(stops, t)
            self.hline(x, y + i, w, ch, c, bg)

    def hgrad(self, x: int, y: int, w: int, stops: list[RGB], ch: str = "█", bg: RGB | None = None) -> None:
        from .color import lerp_ramp

        for i in range(w):
            self.put(x + i, y, ch, lerp_ramp(stops, i / max(1, w - 1)), bg)

    def art(self, x: int, y: int, lines: list[str], stops: list[RGB] | None = None, fg: RGB | None = None,
            bg: RGB | None = None, st: int = 0) -> None:
        from .color import lerp_ramp

        for i, line in enumerate(lines):
            c = lerp_ramp(stops, i / max(1, len(lines) - 1)) if stops else fg
            self.text(x, y + i, line, c, bg, st)
