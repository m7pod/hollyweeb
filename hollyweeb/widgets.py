"""
The pane widgets: the fake-work going on inside every window.

Every widget is a tiny self-contained animation that can be drawn into any
rectangular `View`. Widgets are chosen per character from a weighted pool, so
a Catgirl's dashboard feels nothing like the Corpo Suit's.

Contract:
    w = Widget(rng, palette)
    w.update(dt, t)     # advance simulation
    w.draw(view)        # paint into a clipped view
"""

from __future__ import annotations

import math
import random

from . import art
from .canvas import BOLD, DIM, View
from .color import RGB, darken, lerp_ramp, lighten, mix
from .term import narrow_only

# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------

SPARK_CHARS = " ▁▂▃▄▅▆▇█"
BLOCKS = " ░▒▓█"
LINE_CHARS = {0: "─", 1: "╱", -1: "╲"}
HEAT = [" ", "·", "░", "▒", "▓", "█"]

PROTOCOLS = ["TCP", "UDP", "TLS1.3", "QUIC", "SSH", "HTTP/3", "WS", "DNS", "ICMP"]
SERVICES = {
    22: "ssh", 53: "domain", 80: "http", 443: "https", 3000: "node", 3306: "mysql",
    5432: "postgres", 6379: "redis", 8080: "http-alt", 8443: "https-alt", 9000: "minio",
    1337: "leet", 4000: "gemini", 25565: "minecraft", 6969: "gopherhole",
}
CUTE_TASKS = [
    "reticulating splines", "grooming the packets", "petting the daemon",
    "brewing matcha for the kernel", "polishing chrome horns", "tuning the neon",
    "counting sparkles", "herding photons", "brushing the mainframe",
    "restocking the snack vault", "tuning the shamisen", "warming the ramen",
    "braiding the fiber optic", "feeding the mascot", "debugging feelings",
]
LOG_OK = ["ok", "done", "linked", "purring", "synced", "cute", "based"]
LOG_WARN = ["slow", "retry", "wobble", "hot", "stale", "leaky"]
LOG_ERR = ["boom", "404", "panic", "yikes", "glitch", "oops"]
LOG_LOVE = ["<3", "nya", "hai~", "uwu", "daisuki", "kiss"]


def pick(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]


def draw_line(v: View, x0: int, y0: int, x1: int, y1: int, fg: RGB, bg: RGB | None = None, st: int = 0) -> None:
    """Bresenham-ish line with box-drawing characters."""
    x0, y0, x1, y1 = int(x0), int(y0), int(x1), int(y1)
    if x1 == x0 and y1 == y0:
        v.put(x0, y0, "·", fg, bg, st)
        return
    if abs(x1 - x0) >= abs(y1 - y0):
        if x1 < x0:
            x0, y0, x1, y1 = x1, y1, x0, y0
        dx = x1 - x0
        slope = (y1 - y0) / dx if dx else 0.0
        ch = LINE_CHARS.get(0 if abs(slope) < 0.35 else (1 if slope < 0 else -1), "─")
        y = y0
        for x in range(x0, x1 + 1):
            v.put(x, int(round(y)), ch, fg, bg, st)
            y += slope
    else:
        if y1 < y0:
            x0, y0, x1, y1 = x1, y1, x0, y0
        dy = y1 - y0
        slope = (x1 - x0) / dy if dy else 0.0
        x = x0
        for y in range(y0, y1 + 1):
            v.put(int(round(x)), y, "│", fg, bg, st)
            x += slope


def sparkline(values: list[float], width: int, lo: float = 0.0, hi: float = 1.0) -> str:
    if not values:
        return ""
    out = []
    span = max(1e-6, hi - lo)
    for val in values[-width:]:
        k = (val - lo) / span
        k = 0.0 if k < 0 else 1.0 if k > 1 else k
        out.append(SPARK_CHARS[int(k * (len(SPARK_CHARS) - 1))])
    return "".join(out)


def clip_text(s: str, w: int) -> str:
    if w <= 0:
        return ""
    return s if len(s) <= w else s[: max(0, w - 1)] + "…"


# --------------------------------------------------------------------------
# base
# --------------------------------------------------------------------------


class Widget:
    name = "widget"
    label = "widget"
    tags: tuple[str, ...] = ()
    min_w = 12
    min_h = 4

    def __init__(self, rng: random.Random, pal):
        self.rng = rng
        self.pal = pal
        self.t = 0.0
        self.dt = 1 / 30
        self._w = 0
        self._h = 0

    def update(self, dt: float, t: float) -> None:
        self.dt = dt
        self.t = t

    def draw(self, v: View) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def bg(self, v: View, alpha: float = 1.0) -> None:
        v.fill(0, 0, v.w, v.h, " ", None, None)


# --------------------------------------------------------------------------
# rain family
# --------------------------------------------------------------------------


class Rain(Widget):
    name = "matrix"
    label = "matrix rain"
    min_w = 7
    min_h = 4

    glyphs = art.CYBER
    flicker = 8.0
    speed = (7.0, 26.0)
    tail = (5, 9)
    head_boost = 0.85

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.cols: list[list[float]] = []
        self._gw = -1
        self._gh = -1

    def _ensure(self, w: int, h: int) -> None:
        if (w, h) == (self._gw, self._gh) and len(self.cols) == w:
            return
        self._gw, self._gh = w, h
        cols = []
        for _ in range(w):
            cols.append([
                self.rng.uniform(-h, h),                       # head y
                self.rng.uniform(*self.speed),                 # speed
                self.rng.randint(*self.tail),                  # tail length
                self.rng.random(),                             # phase
            ])
        self.cols = cols

    def update(self, dt, t):
        super().update(dt, t)
        h = max(1, self._gh)
        for c in self.cols:
            c[0] += c[1] * dt
            if c[0] - c[2] > h:
                c[0] = self.rng.uniform(-6, 0)
                c[1] = self.rng.uniform(*self.speed)
                c[2] = self.rng.randint(*self.tail)

    def draw(self, v):
        self._ensure(v.w, v.h)
        pal = self.pal
        glyphs = self.glyphs
        n = len(glyphs)
        dark = mix(pal.bg, pal.panel, 0.6)
        tick = int(self.t * self.flicker)
        for x, c in enumerate(self.cols):
            head, _spd, length, _ph = c
            base = pal.cycle(x * 3 + 1)
            tip = lighten(base, self.head_boost)
            hy = int(head)
            for k in range(length):
                y = hy - k
                if not (0 <= y < v.h):
                    continue
                f = 1.0 - k / max(1, length)
                f = max(0.30, f * f)
                col = mix(dark, base, f)
                ch = glyphs[(x * 13 + y * 7 + tick) % n]
                if k == 0:
                    v.put(x, y, ch, tip, None, BOLD)
                else:
                    v.put(x, y, ch, col, None, DIM if f < 0.35 else 0)


class KatakanaRain(Rain):
    name = "katakana_rain"
    label = "kana drizzle"
    glyphs = narrow_only("ｱｲｳｴｵｶｷｸｹｺｻｼｽｾｿﾀﾁﾂﾃﾄﾅﾆﾇﾈﾉﾊﾋﾌﾍﾎﾏﾐﾑﾒﾓﾔﾕﾖﾗﾘﾙﾚﾛﾜﾝ◇◈✦")
    flicker = 4.0
    speed = (5.0, 16.0)
    tail = (7, 14)
    head_boost = 1.0


class KawaiiRain(Rain):
    name = "kawaii_rain"
    label = "kawaii rain"
    glyphs = narrow_only(art.HEARTS + art.SPARKLES + "｡･ﾟ*")
    flicker = 3.0
    speed = (3.0, 11.0)
    tail = (2, 5)

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.extra: list[list[float]] = []

    def draw(self, v):
        super().draw(v)
        # drifting sparkle dust on top
        pal = self.pal
        if len(self.extra) != v.w:
            self.extra = [[self.rng.uniform(0, v.h), self.rng.uniform(1, 4), self.rng.random()] for _ in range(v.w)]
        tick = int(self.t * 3)
        for x, e in enumerate(self.extra):
            y = (e[0] + self.rng.uniform(-0.4, 0.4)) % max(1.0, v.h)
            if (x * 7 + tick) % 11 == 0:
                v.put(x, int(y), pick(self.rng, "✦✧⋆･｡"), lighten(pal.cycle(x), 0.5), None, DIM)


# --------------------------------------------------------------------------
# sparkle field
# --------------------------------------------------------------------------


class Sparkles(Widget):
    name = "sparkles"
    label = "sparkle field"
    min_w = 7
    min_h = 3

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.stars: list[list[float]] = []
        self._w = self._h = -1

    def _ensure(self, w, h):
        if (w, h) == (self._w, self._h):
            return
        self._w, self._h = w, h
        count = max(4, (w * h) // 14)
        self.stars = [[self.rng.randrange(w), self.rng.randrange(h), self.rng.uniform(0, 6.28),
                       self.rng.uniform(0.8, 2.4)] for _ in range(count)]

    def draw(self, v):
        self._ensure(v.w, v.h)
        pal = self.pal
        chars = "✦✧⋆·+*✩"
        for sx, sy, ph, spd in self.stars:
            b = 0.5 + 0.5 * math.sin(self.t * spd + ph)
            col = mix(pal.panel, pal.cycle(int(sx + sy)), b)
            ch = chars[int(b * (len(chars) - 1))]
            v.put(int(sx), int(sy), ch, col, None, BOLD if b > 0.8 else 0)


# --------------------------------------------------------------------------
# classic hacker panes
# --------------------------------------------------------------------------


class HexDump(Widget):
    name = "hexdump"
    label = "hex dump"
    min_w = 15
    min_h = 5

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.offset = rng.randrange(0, 0xFFFF0)
        self.rows: list[tuple[int, bytes]] = []
        self.scroll = 0.0
        self.speed = rng.uniform(6, 18)
        self.buf = bytes(rng.randrange(256) for _ in range(4096))
        self.bp = 0

    def _next_row(self):
        if self.bp + 16 > len(self.buf):
            self.bp = 0
            self.buf = bytes(self.rng.randrange(256) for _ in range(4096))
        data = self.buf[self.bp:self.bp + 16]
        self.bp += 16
        self.rows.append((self.offset, data))
        self.offset += 16

    def update(self, dt, t):
        super().update(dt, t)
        self.scroll += self.speed * dt
        while self.scroll >= 1:
            self.scroll -= 1
            self._next_row()
        if len(self.rows) > 400:
            del self.rows[:200]

    def draw(self, v):
        pal = self.pal
        addr_col = pal.dim
        hex_col = pal.cycle(1)
        asc_col = pal.fg
        need = max(1, v.h)
        while len(self.rows) < need + 2:
            self._next_row()
        rows = self.rows[-need:]
        xs = 9 if v.w < 30 else 10
        max_bytes = max(3, min(16, (v.w - xs - 2) // 3))
        ascii_x = xs + max_bytes * 3 + 1
        show_ascii = v.w >= ascii_x + max_bytes
        for i, (off, data) in enumerate(rows):
            y = i
            v.text(0, y, f"{off:08x}", addr_col)
            for j, byte in enumerate(data[:max_bytes]):
                col = hex_col
                if byte in (0, 255):
                    col = pal.hot
                elif 32 <= byte < 127:
                    col = pal.cool
                v.text(xs + j * 3, y, f"{byte:02x}", col)
            if show_ascii:
                s = "".join(chr(b) if 32 <= b < 127 else "·" for b in data[:max_bytes])
                v.text(ascii_x, y, s, asc_col)


class Packets(Widget):
    name = "packets"
    label = "packet stream"
    min_w = 16
    min_h = 4

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.lines: list[tuple[str, RGB]] = []
        self.acc = 0.0
        self.rate = rng.uniform(9, 32)
        self.src = [f"10.{rng.randrange(4)}.{rng.randrange(256)}.{rng.randrange(256)}" for _ in range(4)]
        self.dst = [f"172.16.{rng.randrange(256)}.{rng.randrange(256)}" for _ in range(3)]

    def _make(self) -> tuple[str, RGB]:
        rng = self.rng
        pal = self.pal
        proto = pick(rng, PROTOCOLS)
        s = pick(rng, self.src)
        d = pick(rng, self.dst)
        sp = rng.choice([443, 80, 22, 53, 8080, 1337])
        dp = rng.randrange(1024, 65535)
        length = rng.randrange(40, 1480)
        flags = pick(rng, ["[P.]", "[S]", "[.]", "[F.]", "[R.]", "[PSH,ACK]"])
        t = f"{self.t % 100:09.6f}"
        line = f"{t} {proto:<6} {s}.{sp} > {d}.{dp}: Flags {flags} seq {rng.randrange(1 << 32)} win {rng.randrange(64, 65535)} len {length}"
        col = pal.cycle(1) if proto in ("TCP", "TLS1.3") else pal.cycle(0)
        if "R." in flags:
            col = pal.hot
        elif proto == "ICMP":
            col = pal.warn
        return line, col

    def update(self, dt, t):
        super().update(dt, t)
        self.acc += self.rate * dt
        while self.acc >= 1:
            self.acc -= 1
            self.lines.append(self._make())
        if len(self.lines) > 300:
            del self.lines[:150]

    def draw(self, v):
        pal = self.pal
        while len(self.lines) < v.h + 1:
            self.lines.append(self._make())
        for i, (line, col) in enumerate(self.lines[-v.h:]):
            v.text(0, i, clip_text(line, v.w), col)
        if v.w > 4:
            v.put(v.w - 1, v.h - 1, "▌", pal.cycle(2), None, BOLD)


class Nmap(Widget):
    name = "nmap"
    label = "port sweep"
    min_w = 14
    min_h = 5

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.targets = [f"10.0.{rng.randrange(8)}.{rng.randrange(2, 254)}" for _ in range(3)]
        self.reset()

    def reset(self):
        rng = self.rng
        self.host = pick(rng, self.targets)
        self.ports = sorted(rng.sample(list(SERVICES), k=min(len(SERVICES), rng.randint(6, 11))))
        self.idx = 0
        self.delay = 0.0
        self.done = False
        self.findings: list[tuple[int, str, bool]] = []
        self.start = self.t

    def update(self, dt, t):
        super().update(dt, t)
        self.delay -= dt
        if self.delay <= 0:
            if self.idx < len(self.ports):
                port = self.ports[self.idx]
                self.idx += 1
                open_ = self.rng.random() < 0.7
                self.findings.append((port, SERVICES.get(port, "unknown"), open_))
                self.delay = self.rng.uniform(0.05, 0.4)
            else:
                self.delay = self.rng.uniform(2.5, 5.0)
                if self.delay < 2.6:
                    self.reset()

    def draw(self, v):
        pal = self.pal
        head = [
            f"Starting Nmap 7.9{self.rng.randrange(10)} ( https://nmap.org )",
            f"Nmap scan report for {self.host}",
            "Host is up (0.00% packet loss).",
            "PORT      STATE  SERVICE",
        ]
        y = 0
        for i, line in enumerate(head):
            if y >= v.h:
                return
            col = pal.dim if i == 0 else pal.fg
            v.text(0, y, clip_text(line, v.w), col)
            y += 1
        for port, svc, open_ in self.findings:
            if y >= v.h:
                break
            state = "open  " if open_ else "closed"
            col = pal.good if open_ else pal.dim
            v.text(0, y, f"{port}/tcp".ljust(10), pal.cycle(1))
            v.text(10, y, state, col, None, BOLD if open_ else 0)
            v.text(17, y, svc, pal.fg)
            y += 1
        if self.idx >= len(self.ports) and y < v.h:
            v.text(0, y, "Nmap done: 1 IP address (1 host up) scanned", pal.warn)


class LogStream(Widget):
    name = "logstream"
    label = "log stream"
    min_w = 13
    min_h = 4

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.lines: list[tuple[str, RGB]] = []
        self.acc = 0.0
        self.rate = rng.uniform(2.0, 6.0)
        self.levels = ["INFO", "OK", "WARN", "LOVE", "ERR"]

    def _make(self):
        rng, pal = self.rng, self.pal
        lvl = pick(rng, ["INFO", "INFO", "OK", "OK", "LOVE", "WARN", "ERR"])
        svc = pick(rng, ["neko-core", "holly", "daemon", "kernel", "ui", "net", "glow", "mascot"])
        if lvl == "OK":
            msg = pick(rng, LOG_OK) + f" ({rng.randrange(1, 900)}ms)"
            col = pal.good
        elif lvl == "WARN":
            msg = pick(rng, LOG_WARN) + f" [{rng.randrange(1, 99)}%]"
            col = pal.warn
        elif lvl == "ERR":
            msg = pick(rng, LOG_ERR) + f" @0x{rng.randrange(1 << 24):06x}"
            col = pal.hot
        elif lvl == "LOVE":
            msg = pick(rng, LOG_LOVE)
            col = pal.cycle(2)
        else:
            msg = pick(rng, CUTE_TASKS)
            col = pal.dim
        ts = f"{int(self.t // 60):02d}:{int(self.t % 60):02d}.{int((self.t * 10) % 10)}"
        return f"{ts} [{lvl:<4}] {svc:<9} {msg}", col

    def update(self, dt, t):
        super().update(dt, t)
        self.acc += self.rate * dt
        while self.acc >= 1:
            self.acc -= 1
            self.lines.append(self._make())
        if len(self.lines) > 200:
            del self.lines[:100]

    def draw(self, v):
        pal = self.pal
        while len(self.lines) < v.h:
            self.lines.append(self._make())
        for i, (line, col) in enumerate(self.lines[-v.h:]):
            v.text(0, i, clip_text(line, v.w), col)


# --------------------------------------------------------------------------
# graphs and meters
# --------------------------------------------------------------------------


class Progress(Widget):
    name = "progress"
    label = "task queue"
    min_w = 12
    min_h = 4

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.tasks: list[dict] = []

    def _new_task(self, done=0.0):
        rng = self.rng
        return {
            "name": pick(self.rng, CUTE_TASKS),
            "p": done,
            "speed": rng.uniform(0.05, 0.35),
            "color": self.pal.cycle(rng.randrange(4)),
        }

    def update(self, dt, t):
        super().update(dt, t)
        while len(self.tasks) < 6:
            self.tasks.append(self._new_task(self.rng.random() * 0.6))
        for task in self.tasks:
            task["p"] += task["speed"] * dt * (1.0 + 1.5 * math.sin(self.t + task["speed"] * 40) * 0.2)
        done = [x for x in self.tasks if x["p"] >= 1.0]
        for d in done:
            self.tasks.remove(d)
            self.tasks.append(self._new_task(0.0))

    def draw(self, v):
        pal = self.pal
        rows = max(1, v.h // 2)
        for i, task in enumerate(self.tasks[:rows]):
            y = i * 2
            if y >= v.h:
                break
            pct = min(1.0, task["p"])
            label = clip_text(task["name"], max(4, v.w - 6))
            v.text(0, y, label, pal.fg)
            v.text(max(0, v.w - 5), y, f"{int(pct * 100):3d}%", task["color"])
            bw = max(3, v.w)
            filled = int(pct * bw)
            for x in range(bw):
                ch = "█" if x < filled else "░"
                t = x / max(1, bw - 1)
                col = lerp_ramp([task["color"], pal.cycle(1)], t) if x < filled else darken(pal.dim, 0.45)
                v.put(x, y + 1, ch, col)


class Spectrum(Widget):
    name = "spectrum"
    label = "spectrum"
    min_w = 10
    min_h = 5

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.bars: list[float] = []
        self.peaks: list[float] = []
        self.vel: list[float] = []
        self.phase = rng.uniform(0, 6.28)

    def _ensure(self, w):
        if len(self.bars) != w:
            self.bars = [0.2] * w
            self.vel = [0.0] * w
            self.peaks = [0.2] * w

    def update(self, dt, t):
        super().update(dt, t)
        for i in range(len(self.bars)):
            x = i / max(1, len(self.bars) - 1)
            env = math.exp(-((x - 0.25) ** 2) * 5) * 0.8 + math.exp(-((x - 0.7) ** 2) * 7) * 0.7
            target = abs(math.sin(self.t * (1.2 + x * 5.5) + self.phase + x * 9)) * env
            target += self.rng.uniform(0, 0.18) * (1 - x)
            target = min(1.0, target + 0.05)
            self.vel[i] += (target - self.bars[i]) * 12 * dt
            self.vel[i] *= 0.86
            self.bars[i] = max(0.02, min(1.0, self.bars[i] + self.vel[i]))
            self.peaks[i] = max(self.peaks[i] - dt * 0.35, self.bars[i])

    def draw(self, v):
        self._ensure(v.w)
        pal = self.pal
        stops = [pal.cycle(0), pal.cycle(2), pal.cool, pal.fg]
        for x in range(v.w):
            hgt = int(self.bars[x] * v.h)
            for y in range(hgt):
                t = y / max(1, v.h - 1)
                col = lerp_ramp(stops, 1.0 - t)
                v.put(x, v.h - 1 - y, "█", col)
            py = v.h - 1 - int(self.peaks[x] * v.h)
            if 0 <= py < v.h:
                v.put(x, py, "▔", pal.hot, None, BOLD)


class Wave(Widget):
    name = "wave"
    label = "oscilloscope"
    min_w = 12
    min_h = 4

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.phase = rng.uniform(0, 6.28)
        self.freq = rng.uniform(0.15, 0.35)
        self.traces = rng.randint(2, 3)

    def _val(self, x, k):
        x = x * self.freq
        s = math.sin(x * 2 + self.t * (1.4 + k * 0.5) + self.phase)
        s += 0.45 * math.sin(x * 5.1 - self.t * 2.2 + k)
        s += 0.2 * math.sin(x * 11.0 + self.t * 3.7)
        return s / 1.65

    def draw(self, v):
        pal = self.pal
        mid = v.h / 2 - 0.5 if v.h > 2 else 0
        v.hline(0, int(mid), v.w, "┄", darken(pal.dim, 0.45))
        for k in range(self.traces):
            col = pal.cycle(k)
            prev = None
            for x in range(v.w):
                val = self._val(x, k)
                y = mid - val * (v.h / 2 - 1) * (0.9 - k * 0.18)
                yi = int(round(y))
                if prev is not None:
                    draw_line(v, x - 1, prev, x, yi, col, None, BOLD if k == 0 else 0)
                prev = yi
        if v.h > 2:
            v.text(0, v.h - 1, f"{self.freq * 100:.1f}kHz  {self.traces}ch", pal.dim)


class Vu(Widget):
    name = "vu"
    label = "vu meters"
    min_w = 9
    min_h = 4

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.levels = [0.5, 0.5]
        self.peak = [0.5, 0.5]
        self.labels = ["L", "R"]

    def update(self, dt, t):
        super().update(dt, t)
        for i in range(2):
            base = 0.55 + 0.4 * math.sin(self.t * (1.1 + i * 0.4) + i * 2)
            base = abs(base) + self.rng.uniform(0, 0.22)
            target = min(1.0, base)
            self.levels[i] += (target - self.levels[i]) * min(1.0, 9 * dt)
            self.peak[i] = max(self.peak[i] - dt * 0.4, self.levels[i])

    def draw(self, v):
        pal = self.pal
        cols = min(2, max(1, v.w // 6))
        for i in range(cols):
            bx = i * (v.w // cols)
            bw = max(3, v.w // cols - 2)
            lvl = self.levels[i % 2]
            v.text(bx, 0, self.labels[i % 2], pal.cycle(i), None, BOLD)
            segs = max(3, (v.h - 2) * 3)
            for s in range(segs):
                y = v.h - 1 - s
                if y <= 0:
                    break
                t = s / max(1, segs - 1)
                on = t <= lvl
                col = pal.good if t < 0.6 else pal.warn if t < 0.85 else pal.hot
                v.text(bx + 1, y, "██"[:bw], col if on else darken(pal.dim, 0.5))
            py = int((1.0 - self.peak[i % 2]) * (v.h - 2))
            v.text(bx + 1, max(1, py), "▀", pal.fg)


class SysMon(Widget):
    name = "sysmon"
    label = "system monitor"
    min_w = 12
    min_h = 5

    metrics = [("CPU", 0), ("GPU", 1), ("MEM", 2), ("NET", 3)]

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.hist: dict[str, list[float]] = {m: [rng.random() for _ in range(120)] for m, _ in self.metrics}
        self.val: dict[str, float] = {m: self.hist[m][-1] for m, _ in self.metrics}

    def update(self, dt, t):
        super().update(dt, t)
        for name, k in self.metrics:
            target = 0.5 + 0.45 * math.sin(self.t * (0.4 + k * 0.17) + k * 1.9) + self.rng.uniform(-0.06, 0.15)
            self.val[name] = max(0.03, min(1.0, self.val[name] + (target - self.val[name]) * min(1.0, 3 * dt)))
            self.hist[name].append(self.val[name])
            if len(self.hist[name]) > 200:
                del self.hist[name][:100]

    def draw(self, v):
        pal = self.pal
        rows = max(1, v.h // 3)
        used = 0
        for name, k in self.metrics[: max(1, min(len(self.metrics), rows))]:
            y = used * 3
            if y + 2 >= v.h:
                break
            val = self.val[name]
            col = pal.good if val < 0.6 else pal.warn if val < 0.85 else pal.hot
            v.text(0, y, f"{name}", pal.cycle(k), None, BOLD)
            v.text(4, y, f"{val * 100:5.1f}%", col)
            gauge_w = max(4, v.w - 12)
            filled = int(val * gauge_w)
            for x in range(min(gauge_w, v.w - 12)):
                v.put(11 + x, y, "▮" if x < filled else "▯", col if x < filled else darken(pal.dim, 0.5))
            line = sparkline(self.hist[name], v.w, 0.0, 1.0)
            v.text(0, y + 1, line, col)
            used += 1
        if v.h - used * 3 >= 1:
            v.text(0, v.h - 1, f"load {self.val['CPU'] * 8:.2f} {self.val['MEM'] * 8:.2f} {self.val['NET'] * 8:.2f}",
                   pal.dim)


# --------------------------------------------------------------------------
# geometry / 3d
# --------------------------------------------------------------------------


class Cube(Widget):
    name = "cube"
    label = "wireframe"
    min_w = 9
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.rx = rng.uniform(0, 6.28)
        self.ry = rng.uniform(0, 6.28)
        self.speed = rng.uniform(0.5, 1.2)
        self.kind = rng.choice(["cube", "octa", "pyramid"])
        self.verts, self.edges = self._shape(self.kind)

    @staticmethod
    def _shape(kind):
        if kind == "octa":
            v = [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]
            e = [(0, 2), (0, 3), (0, 4), (0, 5), (1, 2), (1, 3), (1, 4), (1, 5), (2, 4), (2, 5), (3, 4), (3, 5)]
            return v, e
        if kind == "pyramid":
            v = [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1), (0, 1, 0)]
            e = [(0, 1), (1, 2), (2, 3), (3, 0), (0, 4), (1, 4), (2, 4), (3, 4)]
            return v, e
        v = [(x, y, z) for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)]
        idx = {p: i for i, p in enumerate(v)}
        e = []
        for i, p in enumerate(v):
            for d in range(3):
                q = list(p)
                q[d] *= -1
                j = idx.get(tuple(q))
                if j is not None and j > i:
                    e.append((i, j))
        return v, e

    def _project(self, v3, w, h):
        x, y, z = v3
        scale = min(w, h * 2) * 0.26
        return (w / 2 + x * scale, h / 2 + y * scale * 0.5, z)

    def draw(self, v):
        pal = self.pal
        self.rx += self.dt * self.speed * 0.7
        self.ry += self.dt * self.speed
        cx, sx = math.cos(self.rx), math.sin(self.rx)
        cy, sy = math.cos(self.ry), math.sin(self.ry)
        pts = []
        for x, y, z in self.verts:
            y, z = y * cx - z * sx, y * sx + z * cx
            x, z = x * cy + z * sy, -x * sy + z * cy
            pts.append(self._project((x, y, z), v.w, v.h))
        for i, j in self.edges:
            x0, y0, z0 = pts[i]
            x1, y1, z1 = pts[j]
            depth = (z0 + z1) / 2
            t = (depth + 1.6) / 3.2
            col = mix(darken(pal.cycle(1), 0.55), pal.cycle(0), 1 - t)
            draw_line(v, round(x0), round(y0), round(x1), round(y1), col, None, BOLD if depth > 0.5 else 0)
        for x, y, _z in pts:
            v.put(round(x), round(y), "•", pal.fg, None, BOLD)


class Globe(Widget):
    name = "globe"
    label = "geo globe"
    min_w = 10
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.lon = rng.uniform(0, 6.28)
        self.speed = rng.uniform(0.25, 0.6)
        self.points = []
        for lat_d in range(-80, 81, 10):
            for lon_d in range(-180, 180, 10):
                if rng.random() < 0.42:  # skinny out the cloud into continents-ish
                    self.points.append((math.radians(lat_d), math.radians(lon_d), rng.random()))
        self.links = [(rng.randrange(len(self.points)), rng.randrange(len(self.points))) for _ in range(4)]

    def draw(self, v):
        pal = self.pal
        self.lon += self.dt * self.speed
        R = min(v.w / 2.1, v.h * 0.52)
        cx, cy = v.w / 2, v.h / 2
        cl, sl = math.cos(self.lon), math.sin(self.lon)
        # glow rings
        for i in range(0, 3):
            rr = R * (1.12 + i * 0.07)
            dots = max(8, int(rr * 5))
            for k in range(dots):
                a = k / dots * 6.2832 + self.t * 0.3 * (1 if i % 2 else -1)
                x, y = cx + math.cos(a) * rr, cy + math.sin(a) * rr * 0.5
                v.put(int(x), int(y), "·", darken(pal.dim, 0.35))
        pts = []
        for lat, lng, _seed in self.points:
            l2 = lng + self.lon
            x = math.cos(lat) * math.cos(l2)
            y = math.sin(lat)
            z = math.cos(lat) * math.sin(l2)
            pts.append((lat, x, y, z))
        for lat, x, y, z in pts:
            if z < -0.15:
                continue
            depth = (z + 1) / 2
            px = cx + x * R
            py = cy - y * R * 0.55
            ch = "●" if z > 0.6 else "•" if z > 0.1 else "·"
            col = mix(darken(pal.cycle(1), 0.5), pal.cycle(0), depth)
            v.put(int(px), int(py), ch, col, None, BOLD if z > 0.75 else 0)
        for a, b in self.links:
            la, xa, ya, za = pts[a]
            lb, xb, yb, zb = pts[b]
            if za <= 0 or zb <= 0:
                continue
            draw_line(v, round(cx + xa * R), round(cy - ya * R * 0.55),
                      round(cx + xb * R), round(cy - yb * R * 0.55), pal.hot, None, DIM)


class Starfield(Widget):
    name = "starfield"
    label = "warp field"
    min_w = 9
    min_h = 5

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.stars = [[rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.05, 1.0)] for _ in range(140)]
        self.speed = rng.uniform(0.35, 0.9)

    def update(self, dt, t):
        super().update(dt, t)
        for s in self.stars:
            s[2] -= self.speed * dt * (0.6 + s[2])
            if s[2] <= 0.02:
                s[0], s[1], s[2] = self.rng.uniform(-1, 1), self.rng.uniform(-1, 1), 1.0

    def draw(self, v):
        pal = self.pal
        cx, cy = v.w / 2, v.h / 2
        for x, y, z in self.stars:
            px = cx + x / z * (v.w / 2.4)
            py = cy + y / z * (v.h / 2.4) * 0.55
            if 0 <= px < v.w and 0 <= py < v.h:
                b = min(1.0, (1 - z) * 1.4)
                col = mix(pal.panel, pal.fg, b)
                ch = "·" if z > 0.6 else "•" if z > 0.3 else "●"
                v.put(int(px), int(py), ch, col, None, BOLD if z < 0.35 else 0)


class Terrain(Widget):
    name = "terrain"
    label = "wave field"
    min_w = 10
    min_h = 5

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.phase = rng.uniform(0, 6.28)
        self.speed = rng.uniform(0.6, 1.5)
        self.kind = rng.choice(["ridges", "grid", "plasma"])

    def draw(self, v):
        pal = self.pal
        rows = max(2, v.h)
        if self.kind == "plasma":
            for y in range(v.h):
                for x in range(v.w):
                    val = (math.sin(x * 0.28 + self.t * self.speed)
                           + math.sin(y * 0.5 - self.t * self.speed * 1.3)
                           + math.sin((x + y) * 0.18 + self.t * 0.7))
                    k = (val + 3) / 6
                    v.put(x, y, BLOCKS[int(k * (len(BLOCKS) - 1))],
                          mix(pal.bg, pal.cycle(0), k), None)
            return
        if self.kind == "grid":
            for i in range(rows):
                depth = (i + 1) / rows
                yy = int((v.h - 1) - i * 0.85)
                if yy < 0:
                    break
                amp = (v.h * 0.16) * depth
                col = mix(pal.cycle(2), pal.cycle(0), depth)
                for x in range(v.w):
                    ph = x * 0.35 / (0.6 + depth * 2) + self.t * (1.6 - depth) + i * 0.9
                    val = math.sin(ph) * amp + math.sin(ph * 2.3 + 1.4) * amp * 0.4
                    v.put(x, int(yy + val), "─" if depth > 0.5 else "·", col, None, 0)
            return
        # ridges: stacked sine mountains
        for i in range(rows):
            depth = 1.0 - i / rows            # 1 = near, 0 = far
            yy = int(v.h - 1 - i * 0.8)
            if yy < 0:
                break
            amp = (v.h * 0.22) * (1.0 - depth) + 1.0
            col = mix(pal.cycle(1), pal.cycle(0), depth)
            ch = "▁▂▃▄▅▆▇█"[min(7, max(0, int(depth * 8)))]
            for x in range(v.w):
                ph = x * 0.22 + self.t * self.speed * (0.5 + depth)
                val = math.sin(ph) * amp + math.sin(ph * 2.7 + self.phase) * amp * 0.35
                v.put(x, int(yy - val * 0.25), ch, col)


class DNA(Widget):
    name = "dna"
    label = "helix"
    min_w = 10
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.phase = rng.uniform(0, 6.28)
        self.speed = rng.uniform(1.0, 2.2)
        self.pairs = "ATCG"

    def draw(self, v):
        pal = self.pal
        cy = v.h / 2 - 0.5
        amp = max(1.0, v.h / 2 - 1)
        for x in range(v.w):
            a = x * 0.34 + self.t * self.speed + self.phase
            y1 = cy + math.sin(a) * amp
            y2 = cy - math.sin(a) * amp
            depth = math.cos(a)
            c1 = mix(darken(pal.cycle(1), 0.45), pal.cycle(0), (depth + 1) / 2)
            c2 = mix(darken(pal.cycle(3), 0.45), pal.cycle(2), (1 - depth) / 2)
            v.put(x, int(round(y1)), "●", c1, None, BOLD if depth > 0.3 else 0)
            v.put(x, int(round(y2)), "●", c2, None, BOLD if depth < -0.3 else 0)
            if x % 3 == 0:
                lo, hi = sorted((int(round(y1)), int(round(y2))))
                v.vline(x, lo + 1, max(0, hi - lo - 1), "│", darken(pal.dim, 0.3))
                if hi - lo > 2:
                    v.put(x, (lo + hi) // 2, self.pairs[(x // 3 + int(self.t)) % 4], pal.fg)


# --------------------------------------------------------------------------
# cute
# --------------------------------------------------------------------------


class Cat(Widget):
    name = "cat"
    label = "bongo cat"
    min_w = 11
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.tap = 0.0
        self.beat = rng.uniform(2.4, 4.2)
        self.notes: list[list[float]] = []
        self.blink = 0.0
        self.next_blink = rng.uniform(2, 5)
        self.meow = 0.0

    def update(self, dt, t):
        super().update(dt, t)
        self.tap += dt
        self.blink -= dt
        self.meow = max(0.0, self.meow - dt)
        if self.blink < -0.12:
            if self.rng.random() < 0.01 or self.next_blink <= 0:
                self.next_blink = self.rng.uniform(2.5, 7)
                self.blink = 0.12
            else:
                self.next_blink -= dt
        if self.rng.random() < 0.05:
            self.notes.append([self.rng.uniform(0, 0.8), self.rng.uniform(0.1, 0.9), 1.0])
        for n in self.notes:
            n[1] -= dt * 0.35
            n[2] -= dt * 0.6
        self.notes = [n for n in self.notes if n[2] > 0]
        if self.rng.random() < 0.02:
            self.meow = 0.9

    def draw(self, v):
        pal = self.pal
        w, h = v.w, v.h
        # drum pad
        pad_y = h - 2
        beat_phase = (self.tap * self.beat) % 1.0
        press = 1 if beat_phase < 0.25 else 0
        pad_col = pal.cycle(1 if press else 2)
        v.hline(1, pad_y, max(1, w - 2), "═", darken(pal.dim, 0.2))
        v.text(1, pad_y - 1, "▄" * max(1, w - 2), None if not press else pad_col)
        for i in range(1, max(2, w - 2)):
            v.put(i, pad_y - 1, "▄", pad_col if press else darken(pad_col, 0.55))
        # sparkle notes
        for nx, ny, life in self.notes:
            v.put(1 + int(nx * (w - 3)), max(0, int((1 - ny) * (h - 3))), pick(self.rng, "♪♫♩✦"),
                  mix(pal.panel, pal.cycle(3), life), None, BOLD)
        # cat sprite
        art_lines = [
            r"  /\_/\  ",
            r" ( o.o ) ",
            r"  > ^ <  ",
            r" /|   |\ ",
        ]
        if self.blink > 0 and self.blink > -0.12:
            art_lines[1] = r" ( -.- ) "
        sx = max(0, (w - 9) // 2)
        sy = max(0, (h - 8) // 2)
        v.art(sx, sy, art_lines, [pal.cycle(0), pal.cycle(1), pal.cool], bg=None)
        # paws
        paw = "⌒" if press else "‿"
        v.put(sx + 1, sy + 4, paw, pal.cycle(1), None, BOLD)
        v.put(sx + 7, sy + 4, paw, pal.cycle(1), None, BOLD)
        if self.meow > 0:
            v.text(sx + 9, sy + 1, "nya!", mix(pal.bg, pal.hot, min(1.0, self.meow * 1.4)), None, BOLD)
        v.text(0, h - 1, f"bpm {int(self.beat * 60):3d}  combo {int(self.tap * self.beat)}",
               pal.dim)


class Heartbeat(Widget):
    name = "heartbeat"
    label = "vitals"
    min_w = 12
    min_h = 5

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.bpm = rng.randint(62, 128)
        self.phase = 0.0
        self.buf: list[float] = [0.0] * 400
        self.beat_flash = 0.0

    def update(self, dt, t):
        super().update(dt, t)
        step = self.bpm / 60.0 * dt
        self.phase = (self.phase + step) % 1.0
        val = 0.0
        p = self.phase
        if 0.06 < p < 0.10:
            val = math.sin((p - 0.06) / 0.04 * math.pi) * 0.35
        elif 0.10 <= p < 0.16:
            val = -0.25
        elif 0.16 <= p < 0.20:
            val = math.sin((p - 0.16) / 0.04 * math.pi) * 1.0
        elif 0.20 <= p < 0.26:
            val = math.sin((p - 0.20) / 0.06 * math.pi) * 0.30
        val += self.rng.uniform(-0.015, 0.015)
        self.beat_flash = max(0.0, self.beat_flash - dt * 3)
        if 0.16 < p < 0.19:
            self.beat_flash = 1.0
        self.buf.append(val)
        if len(self.buf) > 2000:
            del self.buf[:1000]

    def draw(self, v):
        pal = self.pal
        mid = v.h / 2
        v.hline(0, int(mid), v.w, "┄", darken(pal.dim, 0.5))
        data = self.buf[-(v.w):]
        col = mix(darken(pal.hot, 0.4), pal.hot, max(0.25, self.beat_flash))
        prev = None
        for x, val in enumerate(data):
            y = mid - val * (v.h / 2 - 1.2)
            yi = int(round(y))
            if prev is not None:
                draw_line(v, x - 1, prev, x, yi, col, None, BOLD)
            prev = yi
        beat = "♥" if self.beat_flash > 0.3 else "♡"
        v.text(0, 0, f"{beat} {self.bpm:3d} bpm", mix(pal.panel, pal.hot, 0.3 + self.beat_flash * 0.7), None, BOLD)
        if v.w > 30:
            v.text(v.w - 12, 0, f"spo2 {self.rng.randrange(96, 100)}%", pal.cool)
        if v.h > 2:
            v.text(0, v.h - 1, "sinus rhythm // cute but unstable", pal.dim)


# --------------------------------------------------------------------------
# text-y panes
# --------------------------------------------------------------------------


class Glitch(Widget):
    name = "glitch"
    label = "glitch text"
    min_w = 12
    min_h = 4

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.lines: list[str] = []
        self.next = 0.0
        self.corpus = [
            "WAKE UP, NETRUNNER",
            "THE CITY DREAMS IN NEON",
            "YOUR SOUL IS A PAYLOAD",
            "SYSTEM: ADORABLE",
            "BREACH THE FIREWALL OF HEAVEN",
            "KISS ME, I'M COMPILED",
            "01001000 01001001",
            "CUTE OVERRIDE ENGAGED",
        ]

    def update(self, dt, t):
        super().update(dt, t)
        self.next -= dt
        if self.next <= 0:
            self.next = self.rng.uniform(0.12, 0.5)
            if self.rng.random() < 0.6 or not self.lines:
                self.lines.append(self.rng.choice(self.corpus))
            else:
                self.lines.append("".join(self.rng.choice("▓▒░#@$%&*+=?!/\\01") for _ in range(self.rng.randrange(6, 24))))
            if len(self.lines) > 40:
                del self.lines[:20]

    def draw(self, v):
        pal = self.pal
        while len(self.lines) < v.h:
            self.lines.append(self.rng.choice(self.corpus))
        for i, line in enumerate(self.lines[-v.h:]):
            text = line
            jitter = self.rng.random() < 0.25
            col = pal.cycle(i) if jitter else pal.fg
            x = 0
            if jitter:
                x = self.rng.randrange(0, 3)
                # chromatic aberration
                v.text(x, i, clip_text(text, v.w - x - 1), pal.hot, None, DIM)
            for k, ch in enumerate(text[: max(0, v.w - x)]):
                c = col
                if jitter and self.rng.random() < 0.12:
                    ch = self.rng.choice("▓▒░#@$%&*")
                    c = pal.cool
                v.put(x + k, i, ch, c, None, BOLD if jitter else 0)


class Clock(Widget):
    name = "clock"
    label = "chrono"
    min_w = 12
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.quotes = [
            "neon never sleeps", "chrome & cherry blossom", "the night is a network",
            "stay cute, stay encrypted", "future nostalgia", "wired for affection",
        ]
        self.q = rng.choice(self.quotes)
        self.q_at = 0.0

    def draw(self, v):
        pal = self.pal
        import time as _time

        lt = _time.localtime()
        hh, mm, ss = lt.tm_hour, lt.tm_min, lt.tm_sec
        stamp = ""
        for cand in (f"{hh:02d}{mm:02d}", f"{mm:02d}"):
            if art.banner_width(cand) <= v.w - 2:
                stamp = cand
                break
        if not stamp:
            v.text(0, 0, f"{hh:02d}:{mm:02d}:{ss:02d}", pal.cycle(1), None, BOLD)
            stamp = ""
        rows = art.render_banner(stamp, spacing=1) if stamp else []
        bw = art.banner_width(stamp) if stamp else 0
        ox = max(0, (v.w - bw) // 2)
        oy = max(0, (v.h - 6) // 2)
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch != " ":
                    col = lerp_ramp([pal.cycle(0), pal.cycle(1), pal.cycle(2)], c / max(1, bw - 1))
                    from .canvas import BOLD as _B

                    v.put(ox + c, oy + r, ch, col, None, _B)
        if stamp and ox + bw + 2 < v.w:
            v.text(ox + bw + 1, oy + 2, f"{ss:02d}", pal.hot, None, BOLD)
        date = f"{lt.tm_year}-{lt.tm_mon:02d}-{lt.tm_mday:02d}"
        v.text(0, v.h - 2, f"{date}  tz{_time.strftime('%z') or '+0000'}", pal.dim)
        if self.t - self.q_at > 8:
            self.q_at = self.t
            self.q = self.rng.choice(self.quotes)
        v.text(0, v.h - 1, f'"{self.q}"', pal.cycle(3))


class Crypto(Widget):
    name = "crypto"
    label = "chain ticker"
    min_w = 15
    min_h = 5

    coins = ["NEON", "KITTY", "ZAIBATSU", "SAKURA", "GLITCH", "CHROME", "MOCHI", "UWU"]

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.rows = []
        for name in self.rng.sample(self.coins, k=min(6, len(self.coins))):
            base = self.rng.uniform(0.02, 4200)
            self.rows.append({"n": name, "p": base, "hist": [base * (1 + self.rng.uniform(-0.02, 0.02)) for _ in range(40)]})
        self.hash_lines: list[str] = []
        self.acc = 0.0

    def update(self, dt, t):
        super().update(dt, t)
        for row in self.rows:
            drift = self.rng.uniform(-0.03, 0.032) + math.sin(self.t * 0.7 + len(row["n"])) * 0.004
            row["p"] = max(0.0001, row["p"] * (1 + drift))
            row["hist"].append(row["p"])
            if len(row["hist"]) > 120:
                del row["hist"][:60]
        self.acc += dt * 6
        while self.acc >= 1:
            self.acc -= 1
            self.hash_lines.append("0x" + "".join(self.rng.choice("0123456789abcdef") for _ in range(24)))
        if len(self.hash_lines) > 60:
            del self.hash_lines[:30]

    def draw(self, v):
        pal = self.pal
        y = 0
        for i, row in enumerate(self.rows):
            if y >= v.h - 2:
                break
            hist = row["hist"]
            chg = (hist[-1] - hist[0]) / max(1e-9, hist[0]) * 100
            col = pal.good if chg >= 0 else pal.hot
            arrow = "▲" if chg >= 0 else "▼"
            v.text(0, y, f"{row['n']:<9}", pal.cycle(i))
            v.text(9, y, f"{row['p']:>10.2f}", pal.fg)
            v.text(20, y, f"{arrow}{abs(chg):5.2f}%", col)
            if v.w > 28:
                spark = sparkline(hist, min(18, v.w - 28), min(hist), max(hist))
                v.text(28, y, spark, col)
            y += 1
        if y < v.h:
            v.hline(0, y, v.w, "┄", darken(pal.dim, 0.4))
            y += 1
        for line in self.hash_lines[-(v.h - y):] if v.h > y else []:
            v.text(0, y, clip_text(line, v.w), darken(pal.cycle(2), 0.25))
            y += 1


class Radar(Widget):
    name = "radar"
    label = "radar"
    min_w = 12
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.angle = 0.0
        self.speed = rng.uniform(1.2, 2.4)
        self.blips = []

    def update(self, dt, t):
        super().update(dt, t)
        self.angle = (self.angle + self.speed * dt) % 6.2832
        if self.rng.random() < dt * 0.9:
            self.blips.append([self.rng.uniform(0.15, 1.0), self.rng.uniform(0, 6.2832), 1.0])
        for b in self.blips:
            b[2] -= dt * 0.22
        self.blips = [b for b in self.blips if b[2] > 0]

    def draw(self, v):
        pal = self.pal
        cx, cy = v.w / 2, v.h / 2
        R = min(v.w / 2 - 1, (v.h / 2 - 1) * 2.0)
        if R < 2:
            return
        for ring in (0.35, 0.65, 1.0):
            rr = R * ring
            steps = max(10, int(rr * 6))
            for k in range(steps):
                a = k / steps * 6.2832
                v.put(int(cx + math.cos(a) * rr), int(cy + math.sin(a) * rr * 0.5), "·",
                      darken(pal.cycle(1), 0.25 if ring < 1 else 0.05))
        draw_line(v, int(cx), int(cy - R * 0.5), int(cx), int(cy + R * 0.5), darken(pal.dim, 0.35))
        draw_line(v, int(cx - R), int(cy), int(cx + R), int(cy), darken(pal.dim, 0.35))
        # sweep
        for k in range(14):
            a = self.angle - k * 0.06
            rr = R * (0.25 + 0.75 * (1 - k / 14))
            x = cx + math.cos(a) * rr
            y = cy + math.sin(a) * rr * 0.5
            v.put(int(x), int(y), "▒" if k < 3 else "░", mix(pal.panel, pal.cycle(0), 1 - k / 14), None, BOLD if k < 3 else 0)
        for r, a, life in self.blips:
            x = cx + math.cos(a) * R * r
            y = cy + math.sin(a) * R * r * 0.5
            col = mix(pal.panel, pal.hot, life)
            v.put(int(x), int(y), "◉" if life > 0.6 else "○", col, None, BOLD if life > 0.6 else 0)
        v.text(0, v.h - 1, f"{len(self.blips)} contacts", pal.dim)


class NetMap(Widget):
    name = "netmap"
    label = "network map"
    min_w = 13
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.nodes = []
        self.edges = []
        self.packets = []
        self._w = self._h = -1

    def _ensure(self, w, h):
        if (w, h) == (self._w, self._h):
            return
        self._w, self._h = w, h
        rng = self.rng
        n = max(5, min(11, (w * h) // 22))
        self.nodes = [{
            "x": rng.uniform(2, max(3, w - 3)),
            "y": rng.uniform(1, max(2, h - 2)),
            "ip": f"10.0.{rng.randrange(6)}.{rng.randrange(2, 250)}",
            "hub": i == 0,
        } for i in range(n)]
        self.edges = [(i, rng.randrange(n)) for i in range(1, n)]
        self.packets = [[e, self.rng.random(), self.rng.uniform(0.3, 1.1)] for e in self.edges for _ in range(1)]

    def update(self, dt, t):
        super().update(dt, t)
        for p in self.packets:
            p[1] += dt * p[2]
            if p[1] >= 1.0:
                p[1] = 0.0
                p[2] = self.rng.uniform(0.3, 1.2)

    def draw(self, v):
        self._ensure(v.w, v.h)
        pal = self.pal
        for a, b in self.edges:
            na, nb = self.nodes[a], self.nodes[b]
            draw_line(v, int(na["x"]), int(na["y"]), int(nb["x"]), int(nb["y"]), darken(pal.cycle(1), 0.15))
        for edge, prog, _spd in self.packets:
            a, b = edge
            na, nb = self.nodes[a], self.nodes[b]
            x = na["x"] + (nb["x"] - na["x"]) * prog
            y = na["y"] + (nb["y"] - na["y"]) * prog
            v.put(int(x), int(y), "•", pal.hot, None, BOLD)
        for i, n in enumerate(self.nodes):
            col = pal.cycle(0) if n["hub"] else pal.cycle(i + 1)
            n["x"] = max(2.0, min(v.w - 3.0, n["x"]))
            n["y"] = max(1.0, min(v.h - 2.0, n["y"]))
            v.put(int(n["x"]), int(n["y"]), "◍" if n["hub"] else "○", col, None, BOLD)
            if v.h > 8:
                v.text(int(n["x"]) - 3, int(n["y"]) + 1, n["ip"][:7], darken(col, 0.35))
        v.text(0, v.h - 1, f"{len(self.nodes)} nodes / {len(self.packets)} flows", pal.dim)


class BannerPane(Widget):
    name = "banner"
    label = "identity"
    min_w = 12
    min_h = 6

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.word = pal.name.upper().replace(" ", "")
        self.next = 0.0
        self.words = [self.word, "HOLLYWEEB", "NEON", "CUTE", "CYBER", "NYA~"]

    def update(self, dt, t):
        super().update(dt, t)
        self.next -= dt
        if self.next <= 0:
            self.next = 4.5
            self.word = self.rng.choice(self.words)

    def draw(self, v):
        pal = self.pal
        text = self.word[: max(1, (v.w + 1) // 6)]
        rows = art.render_banner(text, spacing=0)
        bw = art.banner_width(text, spacing=0)
        ox = max(0, (v.w - bw) // 2)
        oy = max(0, (v.h - 5) // 2)
        stops = [pal.cycle(0), pal.cycle(1), pal.cycle(2), pal.cycle(3)]
        for r, line in enumerate(rows):
            for c, ch in enumerate(line):
                if ch != " " and ox + c < v.w:
                    col = lerp_ramp(stops, (c / max(1, bw - 1) + r * 0.12) % 1.0)
                    v.put(ox + c, oy + r, ch, col, None, BOLD)
        # orbiting sparkles
        for k in range(6):
            a = self.t * (0.8 + k * 0.05) + k
            x = int(v.w / 2 + math.cos(a) * (v.w / 2 - 1))
            y = int(v.h / 2 + math.sin(a * 1.3) * (v.h / 2 - 1))
            v.put(x, y, pick(self.rng, "✦✧⋆"), pal.fg, None, DIM)


class Fire(Widget):
    name = "fires"
    label = "doom fire"
    min_w = 8
    min_h = 4

    def __init__(self, rng, pal):
        super().__init__(rng, pal)
        self.heat: list[int] = []
        self.acc = 0.0
        self._w = self._h = -1

    def _ensure(self, w, h):
        if (w, h) == (self._w, self._h):
            return
        self._w, self._h = w, h
        self.heat = [0] * (w * h)
        for x in range(w):
            self.heat[(h - 1) * w + x] = 255

    def update(self, dt, t):
        super().update(dt, t)
        self.acc += dt
        if self.acc < 1 / 24:
            return
        self.acc = 0.0
        w, h = self._w, self._h
        if w < 1 or h < 2:
            return
        for y in range(h - 1):
            for x in range(w):
                src = (y + 1) * w + x
                decay = self.rng.randrange(0, 12)
                left = self.rng.randrange(0, 3) - 1
                dst = y * w + ((x + left) % w)
                v = self.heat[src] - decay
                self.heat[dst] = v if v > 0 else 0
        for x in range(w):
            self.heat[(h - 1) * w + x] = 255

    def draw(self, v):
        self._ensure(v.w, v.h)
        pal = self.pal
        stops = [pal.bg, pal.cycle(0), pal.hot, pal.warn, pal.fg]
        for y in range(v.h):
            for x in range(v.w):
                v_int = self.heat[y * v.w + x]
                if v_int < 12:
                    continue
                t = v_int / 255
                v.put(x, y, HEAT[min(5, int(t * 5.2))], lerp_ramp(stops, t))


# --------------------------------------------------------------------------
# registry
# --------------------------------------------------------------------------

WIDGET_CLASSES = [
    Rain, KatakanaRain, KawaiiRain, Sparkles, HexDump, Packets, Nmap, LogStream,
    Progress, Spectrum, Wave, Vu, SysMon, Cube, Globe, Starfield, Terrain, DNA,
    Cat, Heartbeat, Glitch, Clock, Crypto, Radar, NetMap, BannerPane, Fire,
]

REGISTRY: dict[str, type[Widget]] = {cls.name: cls for cls in WIDGET_CLASSES}

# Panes that fit into almost any character's aesthetic; used to top up variety in
# dense grids without breaking the character's identity.
FILLER_ORDER: list[str] = [
    "sparkles", "matrix", "kawaii_rain", "starfield", "terrain", "wave", "dna",
    "vu", "progress", "logstream", "glitch", "sysmon", "packets", "hexdump",
    "radar", "globe", "cube", "netmap", "crypto", "clock", "spectrum", "cat",
    "katakana_rain", "heartbeat", "nmap", "banner", "fires",
]


def make(name: str, rng: random.Random, pal) -> Widget:
    cls = REGISTRY.get(name)
    if cls is None:
        cls = Sparkles
    return cls(rng, pal)


def widget_labels() -> dict[str, str]:
    return {cls.name: cls.label for cls in WIDGET_CLASSES}
