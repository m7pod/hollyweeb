"""Pane geometry: turn an area + pane count into pretty rectangles."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Rect:
    x: int
    y: int
    w: int
    h: int

    @property
    def inner(self) -> "Rect":
        return Rect(self.x + 1, self.y + 1, max(0, self.w - 2), max(0, self.h - 2))


def choose_grid(n: int, width: int, height: int, min_w: int = 18, min_h: int = 6) -> tuple[int, int]:
    """Pick (cols, rows) minimising wasted space while keeping panes usable."""
    n = max(1, n)
    best = (1, n)
    best_score = float("inf")
    for cols in range(1, n + 1):
        rows = -(-n // cols)  # ceil
        cw = width / cols
        ch = height / rows
        # penalty: unusable cells, wasted area, extreme aspect ratios
        penalty = 0.0
        if cw < min_w:
            penalty += (min_w - cw) * 40
        if ch < min_h:
            penalty += (min_h - ch) * 60
        used = n / (cols * rows)
        penalty += (1.0 - used) * 300
        # panes look best a bit wider than tall (chars are ~2x taller than wide)
        ideal = 2.15
        ratio = cw / max(1.0, ch)
        penalty += abs(ratio - ideal) * 22
        if penalty < best_score:
            best_score = penalty
            best = (cols, rows)
    return best


def grid_rects(n: int, area: Rect, min_w: int = 18, min_h: int = 6) -> list[Rect]:
    """Split ``area`` into ``n`` near-equal panes, filling the space exactly."""
    cols, rows = choose_grid(n, area.w, area.h, min_w, min_h)
    rects: list[Rect] = []
    for i in range(n):
        c = i % cols
        r = i // cols
        x0 = area.x + (area.w * c) // cols
        x1 = area.x + (area.w * (c + 1)) // cols
        y0 = area.y + (area.h * r) // rows
        y1 = area.y + (area.h * (r + 1)) // rows
        rects.append(Rect(x0, y0, max(0, x1 - x0), max(0, y1 - y0)))
    return rects


def choose_cards(n: int, width: int, height: int, min_w: int = 16, min_h: int = 7,
                 ideal: float = 2.4) -> tuple[int, int, int, int] | None:
    """Best (cols, rows, card_w, card_h) for a character-card grid, or None."""
    best = None
    for cols in range(1, n + 1):
        rows = -(-n // cols)
        cw = width // cols
        ch = height // rows
        if cw < min_w or ch < min_h:
            continue
        score = abs(cw / max(1, ch) - ideal) + (cols * rows - n) * 0.6
        if best is None or score < best[0]:
            best = (score, cols, rows, cw, ch)
    if best is None:
        return None
    return best[1], best[2], best[3], best[4]


def auto_pane_count(width: int, height: int) -> int:
    """A sensible number of panes for the terminal size (hollywood-ish density)."""
    target_cell_w, target_cell_h = 34.0, 11.0
    cols = max(1, int(width // target_cell_w))
    rows = max(1, int(height // target_cell_h))
    n = cols * rows
    if width >= 200:
        n = max(n, 12)
    return max(1, min(20, n))
