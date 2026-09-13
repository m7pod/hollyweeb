"""
Bitmap lettering + kawaii mascot art.

`FONT5` is a hand-drawn 5x5 pixel font (all single-column glyphs so the grid
stays aligned on every terminal). `render_banner` scales it with spaces or
block glyphs and can paint it with a gradient.
"""

from __future__ import annotations

from .color import RGB, lerp_ramp

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
