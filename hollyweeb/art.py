"""
Bitmap lettering + kawaii mascot art.

`FONT5` is a hand-drawn 5x5 pixel font (all single-column glyphs so the grid
stays aligned on every terminal). `render_banner` scales it with spaces or
block glyphs and can paint it with a gradient.
"""

from __future__ import annotations

import math
import random

from .color import RGB, hsv, hue_shift, lerp_ramp, mix

# 5 rows tall, 5 columns wide per glyph, '#' = ink
FONT5: dict[str, list[str]] = {
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#### ", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "F": ["#####", "#    ", "#### ", "#    ", "#    "],
    "G": [" ####", "#    ", "#  ##", "#   #", " ####"],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "I": [" ### ", "  #  ", "  #  ", "  #  ", " ### "],
    "J": ["    #", "    #", "    #", "#   #", " ### "],
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "# ###", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
    "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    "0": [" ### ", "#  ##", "# # #", "##  #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "  ## ", " #   ", "#####"],
    "3": ["#### ", "    #", " ### ", "    #", "#### "],
    "4": ["#  # ", "#  # ", "#####", "   # ", "   # "],
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "],
    "7": ["#####", "   # ", "  #  ", " #   ", "#    "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    "9": [" ### ", "#   #", " ####", "    #", " ### "],
    " ": ["     ", "     ", "     ", "     ", "     "],
    "!": ["  #  ", "  #  ", "  #  ", "     ", "  #  "],
    "?": [" ### ", "#   #", "  ## ", "     ", "  #  "],
    ".": ["     ", "     ", "     ", "     ", "  #  "],
    ",": ["     ", "     ", "     ", "  #  ", " #   "],
    ":": ["     ", "  #  ", "     ", "  #  ", "     "],
    "-": ["     ", "     ", " ### ", "     ", "     "],
    "_": ["     ", "     ", "     ", "     ", "#####"],
    "+": ["     ", "  #  ", " ### ", "  #  ", "     "],
    "*": ["# # #", " ### ", "# # #", "     ", "     "],
    "/": ["    #", "   # ", "  #  ", " #   ", "#    "],
    "#": [" # # ", "#####", " # # ", "#####", " # # "],
    "@": [" ### ", "#  ##", "# # #", "#    ", " ### "],
    "<": ["   # ", "  #  ", " #   ", "  #  ", "   # "],
    ">": [" #   ", "  #  ", "   # ", "  #  ", " #   "],
    "(": ["  #  ", " #   ", " #   ", " #   ", "  #  "],
    ")": ["  #  ", "   # ", "   # ", "   # ", "  #  "],
    "[": [" ### ", " #   ", " #   ", " #   ", " ### "],
    "]": [" ### ", "   # ", "   # ", "   # ", " ### "],
}

FONT_H = 5
FONT_W = 5

# --------------------------------------------------------------------------
# header visual effects
# --------------------------------------------------------------------------

#: How the big HOLYWEEB wordmark is painted. `holo` is the default: it mixes the
#: runner's palette with complementary hues and an animated shine instead of
#: using one flat theme gradient.
HEADER_FX: list[str] = ["holo", "rainbow", "prism", "confetti", "vapor", "glitch", "theme"]


VAPOR_STOPS: list[RGB] = [(255, 128, 214), (126, 240, 255), (198, 164, 255), (255, 246, 196)]


def banner_color(mode: str, stops: list[RGB], cn: float, rn: float, t: float,
                 hot: RGB, cool: RGB, li: float = 0.0) -> RGB:
    """Colour of one banner cell.

    `cn`/`rn` run 0..1 across and down the logo, `li` runs 0..1 across its
    letters — that per-letter term is what makes the wordmark read as *mixed*
    colours instead of one smooth theme gradient.
    """
    stops = stops or [(255, 255, 255)]
    if mode == "theme":
        return lerp_ramp(stops, cn * 0.8 + rn * 0.2)
    if mode == "rainbow":
        return hsv((cn * 0.9 + t * 0.13) % 1.0, 0.88, 0.98 - rn * 0.08)
    if mode == "prism":
        base = hsv((li * 1.1 + rn * 0.06 + t * 0.10) % 1.0, 0.95, 0.99)
        return mix(base, stops[0], 0.12)
    if mode == "confetti":
        pool = list(stops) + [
            hue_shift(stops[0], 0.33),
            hue_shift(stops[-1], 0.55),
            hue_shift(stops[len(stops) // 2], 0.74),
            (255, 255, 255),
        ]
        rng = random.Random(int(t * 5.0) * 977 + int(cn * 53) * 131 + int(rn * 11))
        return mix(rng.choice(pool), (255, 255, 255), rng.random() * 0.35)
    if mode == "vapor":
        pos = (li * 0.5 + cn * 0.45 + math.sin(rn * 7.0) * 0.05 + t * 0.06) % 1.0
        return lerp_ramp(VAPOR_STOPS + [VAPOR_STOPS[0]], pos)
    if mode == "glitch":
        base = lerp_ramp(stops, cn * 0.8 + rn * 0.2)
        rng = random.Random(int(t * 9.0) * 131 + int(cn * 97) * 17 + int(rn * 5))
        roll = rng.random()
        if roll < 0.16:
            return hot
        if roll < 0.32:
            return cool
        return mix(base, hsv((li + t * 0.2) % 1.0, 0.8, 1.0), 0.35)
    # holo (default): theme + a complementary hue + a per-letter rainbow sweep
    theme = lerp_ramp(stops, cn * 0.8 + rn * 0.2)
    letter_hue = hsv((li * 0.8 + t * 0.18) % 1.0, 0.9, 1.0)
    other = hue_shift(theme, 0.42)
    k = 0.5 + 0.5 * math.sin(6.2831853 * (li * 2.4 - t * 0.35))
    mixed = mix(theme, other, k)
    mixed = mix(mixed, letter_hue, 0.55)
    return mix(mixed, hsv((cn * 0.9 + t * 0.22) % 1.0, 0.85, 1.0), 0.20)


def banner_stops(mode: str, stops: list[RGB], t: float, hot: RGB, cool: RGB,
                 n: int = 10) -> list[RGB]:
    """Sample the effect across the width — handy for gradient rules/underlines."""
    n = max(2, n)
    return [banner_color(mode, stops, i / (n - 1), 0.5, t, hot, cool, i / (n - 1)) for i in range(n)]


def draw_banner_fx(view, x: int, y: int, text: str, stops: list[RGB], t: float = 0.0,
                   mode: str = "holo", ink: str = "#", spacing: int = 1,
                   hot: RGB | None = None, cool: RGB | None = None,
                   shine: bool = True) -> int:
    """Draw the wordmark with a mixed-colour, animated effect. Returns its width."""
    from .canvas import BOLD

    stops = list(stops) or [(255, 255, 255)]
    hot = hot or (255, 70, 160)
    cool = cool or (90, 225, 255)
    rows = render_banner(text, spacing=spacing, ink=ink)
    width = banner_width(text, spacing)
    if width <= 0:
        return 0

    # chromatic aberration: a hot/cool ghost either side of the glyphs
    if mode in ("glitch", "prism"):
        ghost_a = mix(hot, stops[0], 0.3)
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch == " ":
                    continue
                view.put(x + c - 1, y + r, ch, ghost_a, None, 0)
                view.put(x + c + 1, y + r, ch, cool, None, 0)

    letters = max(1, len(text))
    stride = FONT_W + spacing
    sweep = ((t * 0.30) % 1.6) - 0.3
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch == " ":
                continue
            cn = c / max(1, width - 1)
            rn = r / max(1, FONT_H - 1)
            li = min(1.0, (c // stride) / max(1, letters - 1)) if letters > 1 else 0.0
            col = banner_color(mode, stops, cn, rn, t, hot, cool, li)
            if shine and mode not in ("glitch", "confetti"):
                d = cn - sweep
                gloss = math.exp(-(d * d) * 70.0)
                if gloss > 0.02:
                    col = mix(col, (255, 255, 255), min(0.9, gloss))
            view.put(x + c, y + r, ch, col, None, BOLD)
    return width


def render_banner(text: str, spacing: int = 1, ink: str = "#", blank: str = " ") -> list[str]:
    """Rasterise ``text`` into `FONT_H` rows using FONT5."""
    rows = [""] * FONT_H
    for idx, ch in enumerate(text.upper()):
        glyph = FONT5.get(ch, FONT5["?"])
        for r in range(FONT_H):
            rows[r] += glyph[r].replace("#", ink).replace(" ", blank)
        if idx != len(text) - 1:
            for r in range(FONT_H):
                rows[r] += " " * spacing
    return rows


def banner_width(text: str, spacing: int = 1) -> int:
    return max(0, len(text) * (FONT_W + spacing) - spacing)


def draw_banner(view, x: int, y: int, text: str, stops: list[RGB], spacing: int = 1,
                ink: str = "#", bold: bool = True, shadow: RGB | None = None) -> int:
    """Draw a gradient banner. Returns the width used."""
    rows = render_banner(text, spacing=spacing, ink=ink)
    width = banner_width(text, spacing)
    from .canvas import BOLD

    st = BOLD if bold else 0
    if shadow is not None:
        for r, line in enumerate(rows):
            view.text(x + 1, y + r + 1, line, shadow, None, 0)
    for r, line in enumerate(rows):
        for c, ch in enumerate(line):
            if ch != " ":
                col = lerp_ramp(stops, (c / max(1, width - 1)) * 0.8 + (r / 4) * 0.2)
                view.put(x + c, y + r, ch, col, None, st)
    return width


# --------------------------------------------------------------------------
# mascots (<= 9 rows, ~14 cols, all narrow glyphs)
# --------------------------------------------------------------------------

MASCOTS: dict[str, list[str]] = {
    "neko": [
        r"  /\_/\   ",
        r" ( o.o )  ",
        r"  > ^ <   ",
        r" /|   |\  ",
        r"  |___|   ",
    ],
    "kitsune": [
        r" /\   /\ ",
        r"(=^.^=)  ",
        r" /|   |\ ",
        r"  \___/  ",
        r"  ~~~~~  ",
    ],
    "geisha": [
        r"   .-.    ",
        r"  (o o)   ",
        r" /|=|=|\  ",
        r"   |_|    ",
        r"   / \    ",
    ],
    "ronin": [
        r"  .---.   ",
        r" /_____\  ",
        r" | o o |  ",
        r" |  ^  |  ",
        r"  \___/   ",
    ],
    "succubus": [
        r" \     /  ",
        r"  \   /   ",
        r"  (>.<)   ",
        r"  /|=|\   ",
        r"   / \    ",
    ],
    "idol": [
        r"    *     ",
        r"  (^o^)   ",
        r"  /|=|\   ",
        r"   / \    ",
        r"  ~ ~ ~   ",
    ],
    "ramen": [
        r" ,-----.  ",
        r"( ^o^  )  ",
        r" |=====|  ",
        r"  \___/   ",
        r"  ~ ~ ~   ",
    ],
    "corpo": [
        r" _______  ",
        r"| o   o | ",
        r"|   -   | ",
        r"|_______| ",
        r"   | |    ",
    ],
    "android": [
        r"  _____   ",
        r" | o o |  ",
        r" |  ~  |  ",
        r" |_____|  ",
        r"  /| |\   ",
    ],
    "panda": [
        r"  @   @   ",
        r" ( o.o )  ",
        r"  > ^ <   ",
        r" /|   |\  ",
        r"  |___|   ",
    ],
}

SPARKLES = "✦✧⋆✩✪✫✬✭✮✯✰⁂＊"

HEARTS = "♥♡❤❥❣"

KATAKANA = "ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ"

DIGITS = "01"

CYBER = "01ｦｧｨｩｪｫｬｭｮｯｰｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ╬╫╪┼▓▒░╱╲"

CUTE = "✿❀❁✾❃✽❋⋆˚･｡○●□■♡♥★☆"

BOXY = "▁▂▃▄▅▆▇█▉▊▋▌▍▎▏░▒▓"

BLOCKS = "█▓▒░"
