"""
Palettes, colour variants ("couture modes"), and the cast of characters.

A `Palette` is a small named set of RGB colours that every widget reads from,
which is why switching character *or* variant instantly re-styles the entire
dashboard without touching widget code.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import art
from .color import (
    RGB,
    desaturate,
    grayscale,
    hsv,
    lighten,
    mix,
    rotate_toward,
    saturate,
)

VARIANTS = ["signature", "neon", "pastel", "ice", "sunset", "acid", "vhs", "mono"]


@dataclass
class Palette:
    name: str
    bg: RGB = (8, 6, 14)
    panel: RGB = (14, 11, 24)
    fg: RGB = (232, 226, 255)
    dim: RGB = (110, 104, 140)
    accents: list[RGB] = field(default_factory=list)
    hot: RGB = (255, 90, 170)
    cool: RGB = (90, 225, 255)
    warn: RGB = (255, 190, 90)
    good: RGB = (140, 255, 190)
    variant: str = "signature"

    # -- lookups -----------------------------------------------------------
    def cycle(self, i: int) -> RGB:
        if not self.accents:
            return self.fg
        return self.accents[i % len(self.accents)]

    def ramp(self, t: float) -> RGB:
        from .color import lerp_ramp

        stops = list(self.accents) or [self.fg]
        return lerp_ramp(stops + [stops[0]], t)

    def shade(self, t: float) -> RGB:
        """Very dark -> accent gradient, handy for backgrounds and heat maps."""
        base = mix(self.bg, self.cycle(0), 0.10)
        return mix(base, self.cycle(1) if len(self.accents) > 1 else self.hot, t)

    # -- variants ----------------------------------------------------------
    def with_variant(self, variant: str) -> "Palette":
        if variant == "signature":
            return self
        a = list(self.accents)
        bg, panel, fg, dim = self.bg, self.panel, self.fg, self.dim
        hot, cool, warn, good = self.hot, self.cool, self.warn, self.good

        if variant == "neon":
            a = [saturate(lighten(c, 0.05), 0.30) for c in a]
            hot, cool = saturate(lighten(hot, 0.1), 0.3), saturate(lighten(cool, 0.1), 0.3)
            bg = mix(bg, (0, 0, 0), 0.4)
            panel = mix(panel, (0, 0, 0), 0.35)
        elif variant == "pastel":
            a = [lighten(desaturate(c, 0.30), 0.28) for c in a]
            fg = lighten(fg, 0.1)
            dim = lighten(dim, 0.25)
            bg = lighten(bg, 0.10)
            panel = lighten(panel, 0.14)
            hot, cool = lighten(desaturate(hot, 0.25), 0.3), lighten(desaturate(cool, 0.25), 0.3)
        elif variant == "ice":
            a = [rotate_toward(lighten(c, 0.08), 0.56, 0.75) for c in a]
            bg = mix(bg, (4, 12, 28), 0.6)
            panel = mix(panel, (8, 20, 44), 0.6)
            hot, cool = rotate_toward(hot, 0.55, 0.7), rotate_toward(cool, 0.52, 0.5)
            dim = rotate_toward(dim, 0.58, 0.5)
        elif variant == "sunset":
            a = [rotate_toward(lighten(c, 0.05), 0.06, 0.8) for c in a]
            bg = mix(bg, (26, 8, 6), 0.6)
            panel = mix(panel, (36, 12, 10), 0.6)
            hot, cool = (255, 120, 70), (255, 190, 120)
            dim = rotate_toward(dim, 0.05, 0.6)
        elif variant == "acid":
            a = [rotate_toward(saturate(c, 0.35), 0.28, 0.85) for c in a]
            bg = mix(bg, (6, 18, 4), 0.6)
            panel = mix(panel, (10, 26, 6), 0.6)
            hot, cool = (200, 255, 80), (90, 255, 170)
        elif variant == "vhs":
            a = [rotate_toward(desaturate(lighten(c, 0.06), 0.12), 0.88, 0.85) for c in a]
            bg = mix(bg, (20, 6, 24), 0.6)
            panel = mix(panel, (30, 10, 36), 0.6)
            hot, cool = (255, 80, 190), (110, 200, 255)
            dim = rotate_toward(dim, 0.88, 0.5)
        elif variant == "mono":
            a = [grayscale(lighten(c, 0.10)) for c in a]
            bg, panel, dim = grayscale(bg), grayscale(panel), grayscale(dim)
            fg = (240, 240, 240)
            hot = cool = warn = good = (225, 225, 230)

        return Palette(
            name=self.name, bg=bg, panel=panel, fg=fg, dim=dim, accents=a,
            hot=hot, cool=cool, warn=warn, good=good, variant=variant,
        )


@dataclass
class Character:
    key: str
    name: str
    tagline: str
    mascot: str
    palette: Palette
    widgets: list[str]
    glyphs: str
    border: str = "round"
    ticker: list[str] = field(default_factory=list)
    # how twitchy the panes are (0..1) -> how often they reshuffle / glitch
    chaos: float = 0.5
    # key of the soundtrack this runner plays (see hollyweeb.music.STYLES)
    music: str = "synthwave"

    @property
    def art(self) -> list[str]:
        return art.MASCOTS.get(self.mascot, art.MASCOTS["neko"])


def _p(name, bg, panel, fg, accents, hot, cool, warn=(255, 190, 90), good=(140, 255, 190)) -> Palette:
    return Palette(name=name, bg=bg, panel=panel, fg=fg, accents=accents, hot=hot, cool=cool, warn=warn, good=good)


CHARACTERS: list[Character] = [
    Character(
        key="neko",
        name="NEON NEKO",
        tagline="catgirl sysadmin // nine lives, zero uptime",
        mascot="neko",
        palette=_p("neko", (11, 6, 22), (18, 11, 34), (240, 232, 255),
                   [(255, 84, 170), (110, 240, 255), (186, 140, 255), (255, 214, 235)],
                   (255, 84, 170), (110, 240, 255)),
        widgets=["kawaii_rain", "cat", "logstream", "matrix", "sparkles", "progress",
                  "packets", "spectrum", "hexdump", "clock", "vu", "glitch"],
        glyphs=art.HEARTS + art.SPARKLES + "ｱｲｳｴｵｶｷｸ",
        ticker=[
            "purring at 4.2 GHz",
            "headpats/sec: nominal",
            "sudo pets --all",
            "tail -f /dev/cuddles",
            "neko.exe is running",
        ],
        chaos=0.35,
        music="chiptune",
    ),
    Character(
        key="geisha",
        name="GLITCH GEISHA",
        tagline="tea ceremony at 240 baud // poison in the packet",
        mascot="geisha",
        palette=_p("geisha", (20, 6, 14), (32, 10, 22), (255, 238, 242),
                   [(255, 66, 96), (255, 183, 206), (255, 214, 102), (240, 240, 255)],
                   (255, 66, 96), (255, 183, 206)),
        widgets=["matrix", "katakana_rain", "glitch", "dna", "hexdump", "logstream",
                  "terrain", "sparkles", "netmap", "clock", "radar", "progress"],
        glyphs="✿❀✦ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ",
        border="double",
        ticker=[
            "folding paper cranes in /dev/null",
            "shamisen.vst loaded",
            "cherry blossoms: 3 packets lost",
            "おちゃをどうぞ // have a nice exploit",
        ],
        chaos=0.55,
        music="koto",
    ),
    Character(
        key="ronin",
        name="CHROME RONIN",
        tagline="no master, no firewall, only the blade",
        mascot="ronin",
        palette=_p("ronin", (6, 12, 20), (10, 20, 32), (226, 240, 255),
                   [(64, 230, 255), (150, 180, 210), (255, 74, 74), (255, 200, 80)],
                   (255, 74, 74), (64, 230, 255)),
        widgets=["nmap", "packets", "cube", "sysmon", "radar", "hexdump",
                  "matrix", "netmap", "terrain", "globe", "crypto", "wave"],
        glyphs=art.CYBER,
        border="heavy",
        ticker=[
            "steel sharpens on the shell",
            "target acquired: 10.0.0.0/8",
            "one cut, one connection",
            "honor is a zero-day",
        ],
        chaos=0.6,
        music="darkwave",
    ),
    Character(
        key="succubus",
        name="SYNTH SUCCUBUS",
        tagline="your bandwidth belongs to me now, darling",
        mascot="succubus",
        palette=_p("succubus", (14, 4, 22), (24, 8, 36), (248, 230, 255),
                   [(186, 66, 255), (255, 62, 200), (255, 122, 96), (222, 186, 255)],
                   (255, 62, 200), (186, 66, 255)),
        widgets=["spectrum", "wave", "glitch", "dna", "logstream", "heartbeat",
                  "sparkles", "matrix", "terrain", "vu", "crypto", "cube"],
        glyphs="♥❥✦✧ｱｲｳｴｵｶｷｸｹｺ",
        ticker=[
            "soul.dat uploaded... partially",
            "seducing the kernel",
            "latency: devastating",
            "you may call me root",
        ],
        chaos=0.7,
        music="synthwave",
    ),
    Character(
        key="idol",
        name="VAPOR IDOL",
        tagline="debut stage: mainframe // encore: forever",
        mascot="idol",
        palette=_p("idol", (20, 10, 32), (30, 16, 48), (255, 245, 255),
                   [(255, 140, 200), (140, 255, 220), (190, 170, 255), (255, 240, 170)],
                   (255, 140, 200), (140, 255, 220)),
        widgets=["vu", "spectrum", "sparkles", "kawaii_rain", "progress", "clock",
                  "wave", "cat", "logstream", "starfield", "glitch", "banner"],
        glyphs=art.CUTE,
        ticker=[
            "live in 3... 2... 1...",
            "fans: 1,048,576 and rising",
            "autotune enabled",
            "encore loop detected",
        ],
        chaos=0.3,
        music="citypop",
    ),
    Character(
        key="kitsune",
        name="DATA KITSUNE",
        tagline="nine tails, nine proxies, one truth",
        mascot="kitsune",
        palette=_p("kitsune", (22, 10, 8), (34, 16, 12), (255, 244, 236),
                   [(255, 140, 60), (170, 110, 255), (255, 245, 235), (255, 90, 60)],
                   (255, 140, 60), (170, 110, 255)),
        widgets=["radar", "netmap", "packets", "katakana_rain", "terrain", "globe",
                  "hexdump", "sparkles", "logstream", "nmap", "dna", "sysmon"],
        glyphs="✧✦ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿ◈◇",
        ticker=[
            "a trickster in every subnet",
            "illusion: 100% packet loss",
            "tails = ttl 9",
            "foxfire on the wire",
        ],
        chaos=0.5,
        music="taiko",
    ),
    Character(
        key="ramen",
        name="RAMEN RUNNER",
        tagline="hot broth, cold code, 3 a.m. delivery",
        mascot="ramen",
        palette=_p("ramen", (26, 12, 6), (38, 18, 10), (255, 248, 232),
                   [(255, 180, 70), (120, 220, 150), (255, 90, 70), (255, 240, 210)],
                   (255, 90, 70), (255, 180, 70)),
        widgets=["logstream", "progress", "sysmon", "cat", "kawaii_rain", "sparkles",
                  "clock", "packets", "vu", "hexdump", "terrain", "banner"],
        glyphs="*~oO0♥✦｡･ﾟ",
        ticker=[
            "order #3281: extra chashu",
            "noodles al dente in 0.4 ms",
            "steam: 92% CPU",
            "delivery drone en route",
        ],
        chaos=0.25,
        music="lofi",
    ),
    Character(
        key="corpo",
        name="CORPO SUIT",
        tagline="quarterly earnings: up // ethics: deprecated",
        mascot="corpo",
        palette=_p("corpo", (4, 14, 10), (8, 24, 16), (220, 255, 236),
                   [(90, 255, 140), (60, 220, 200), (190, 255, 90), (180, 200, 190)],
                   (190, 255, 90), (90, 255, 140)),
        widgets=["matrix", "crypto", "sysmon", "hexdump", "nmap", "packets",
                  "logstream", "netmap", "globe", "clock", "progress", "wave"],
        glyphs=art.CYBER,
        border="sharp",
        ticker=[
            "synergy detected on eth0",
            "rightsizing the mainframe",
            "promotion: /dev/null",
            "black ice, green numbers",
        ],
        chaos=0.45,
        music="techno",
    ),
    Character(
        key="android",
        name="ANDROID ANGEL",
        tagline="halo firmware 7.0 // bless this socket",
        mascot="android",
        palette=_p("android", (8, 10, 20), (14, 18, 34), (240, 244, 255),
                   [(255, 225, 140), (235, 240, 255), (120, 190, 255), (255, 160, 180)],
                   (255, 225, 140), (120, 190, 255)),
        widgets=["globe", "starfield", "wave", "sparkles", "clock", "dna",
                  "logstream", "progress", "hexdump", "terrain", "packets", "cube"],
        glyphs="✧✦⋆☆★ｱｲｳｴｵｶｷｸ",
        ticker=[
            "guardian daemon: online",
            "prayer packets: 0 dropped",
            "divine intervention scheduled",
            "ascending to /dev/tty1",
        ],
        chaos=0.35,
        music="ambient",
    ),
    Character(
        key="panda",
        name="PANDA PROTOCOL",
        tagline="bamboo firewall // bite-sized exploits",
        mascot="panda",
        palette=_p("panda", (12, 12, 16), (20, 20, 26), (245, 245, 250),
                   [(235, 240, 245), (130, 140, 160), (150, 230, 150), (255, 170, 200)],
                   (255, 170, 200), (150, 230, 150)),
        widgets=["cat", "kawaii_rain", "sparkles", "logstream", "hexdump", "progress",
                  "matrix", "vu", "clock", "packets", "glitch", "terrain"],
        glyphs=art.CUTE + "ｱｲｳ",
        ticker=[
            "snacking on /var/log",
            "rolling downhill at 9.6 Gbps",
            "bamboo: encrypted",
            "panda.exe stopped working (adorably)",
        ],
        chaos=0.3,
        music="trance",
    ),
]


CHARACTER_BY_KEY = {c.key: c for c in CHARACTERS}


def get_character(key: str) -> Character:
    if key in CHARACTER_BY_KEY:
        return CHARACTER_BY_KEY[key]
    low = key.lower().strip()
    for k, c in CHARACTER_BY_KEY.items():
        if low in (k, c.name.lower()) or low in c.name.lower():
            return c
    raise KeyError(key)
