"""
The application: boot sequence, character select, and the live dashboard.

Screens
-------
boot    short holographic boot animation
select  pick your runner (mascot cards, live palette preview)
main    the actual hollywood-style wall of fake work
help    keybinding overlay on top of `main`
"""

from __future__ import annotations

import math
import random
import time

from . import art, music, pulse, widgets
from .canvas import BOLD, DIM, Canvas, View
from .color import Colorizer, darken, detect_mode, lerp_ramp, lighten, mix
from .layout import Rect, auto_pane_count, choose_cards, grid_rects
from .palettes import CHARACTERS, VARIANTS, Character, Palette
from .term import Terminal, strip_wide, term_size

BOOT_LINES = [
    ("mounting /dev/neon", "ok"),
    ("loading aesthetic drivers", "ok"),
    ("calibrating cuteness levels", "ok"),
    ("linking mascot daemon", "ok"),
    ("warming sparkle engine", "ok"),
    ("negotiating with the firewall", "warn"),
    ("decrypting vibes.key", "ok"),
    ("rendering 24/7 fashion", "ok"),
]


class Pane:
    """One window in the wall: a rect, a widget, and a lifetime."""

    __slots__ = ("rect", "widget", "widget_name", "color", "ttl", "age", "index")

    def __init__(self, rect: Rect, widget, widget_name: str, color, ttl: float, index: int):
        self.rect = rect
        self.widget = widget
        self.widget_name = widget_name
        self.color = color
        self.ttl = ttl
        self.age = 0.0
        self.index = index


class App:
    def __init__(self, args):
        self.args = args
        self.rng = random.Random(args.seed)
        self.mode = detect_mode(args.color)
        self.cz = Colorizer(self.mode)
        self.term = Terminal(use_alt_screen=not args.no_alt_screen)

        self.w, self.h = parse_size(getattr(args, "size", "") or "") or term_size()
        self.canvas = Canvas(self.w, self.h)
        self.prev: Canvas | None = None

        self.t = 0.0
        self.frame = 0
        self.running = True
        self.paused = False
        self.show_help = False
        self.glitch_fx = not args.no_glitch
        self.static = args.static
        self.auto = args.auto
        self.auto_at = 0.0
        self.auto_interval = args.auto_interval
        self.message = ""
        self.message_until = 0.0

        # cast
        self.char_index = 0
        if args.character:
            from .palettes import get_character

            try:
                self.char_index = CHARACTERS.index(get_character(args.character))
            except KeyError:
                self.char_index = 0
                self.message = f"unknown runner '{args.character}'"
                self.message_until = 4.0
        self.sel_index = self.char_index
        self.variant_index = 0
        if args.variant:
            try:
                self.variant_index = VARIANTS.index(args.variant)
            except ValueError:
                pass

        self.panes: list[Pane] = []
        self.pane_count_override = args.panes or 0
        self.fps = max(4, min(60, args.fps))
        self.typing = 0.0
        self.ticker_index = 0
        self.ticker_text = ""
        self.ticker_done_at = 0.0
        self.last_glitch = 0.0

        # header wordmark effect: mixed colours by default, not one flat theme
        fx = getattr(args, "header_fx", None) or "holo"
        self.header_fx = fx if fx in art.HEADER_FX else "holo"

        # soundtrack
        self.music = music.MusicPlayer(
            enabled=bool(getattr(args, "music", False)),
            style=getattr(args, "music_style", None) or CHARACTERS[self.char_index].music,
            volume=getattr(args, "music_volume", 0.7),
            seed=args.seed if getattr(args, "seed_given", False) else 0,
            path=getattr(args, "music_file", None),
            bpm=getattr(args, "music_bpm", None),
            bars=getattr(args, "music_bars", None),
            cache_dir=getattr(args, "music_cache_dir", None),
            dry_run=bool(getattr(args, "music_dry", False)),
        )
        self.music_override: str | None = getattr(args, "music_style", None)
        self.music_bars: list[float] = [0.0] * 4

        # pane re-roll cadence (seconds; 0 or --static = never) and music rotation
        self.reroll = max(0.0, float(getattr(args, "reroll", 3.0) or 0.0))
        self.music_rotate = _resolve_rotate(getattr(args, "music_rotate", "auto"), self.reroll)
        self.music_rotated_at = 0.0

        self.boot_t = 0.0
        self.boot_done = False
        self.screen = "main" if (args.character or args.no_boot) else "boot"
        if self.screen == "main":
            self._start_dashboard()
        self.duration = args.duration

    # ------------------------------------------------------------------
    # palette / character
    # ------------------------------------------------------------------
    @property
    def character(self) -> Character:
        return CHARACTERS[self.char_index]

    @property
    def palette(self) -> Palette:
        return self.character.palette.with_variant(VARIANTS[self.variant_index])

    def _start_dashboard(self) -> None:
        pal = self.palette
        self._fix_palette_for_mode(pal)
        n = self.pane_count_override or auto_pane_count(self.w, self.h)
        self._build_panes(n)
        self.ticker_index = 0
        self.ticker_text = ""
        self.typing = 0.0
        self._sync_music()

    # -- soundtrack --------------------------------------------------------
    def _music_style_for(self, index: int) -> str:
        if self.music_override:
            return self.music_override
        return CHARACTERS[max(0, min(len(CHARACTERS) - 1, index))].music

    def _sync_music(self) -> None:
        self.music.set_style(self._music_style_for(self.char_index))

    def _update_pulse(self) -> None:
        """Feed the shared beat clock so widgets can move in time."""
        if not self.music.playing:
            if pulse.active:
                pulse.reset()
                self.music_bars = [0.0] * 4
            return
        beat_phase, bar_phase = self.music.phase()
        level = max(0.0, 1.0 - beat_phase * 2.2)
        for i in range(4):
            target = abs(math.sin((beat_phase + i * 0.21) * math.pi)) * (0.45 + 0.55 * level)
            self.music_bars[i] += (target - self.music_bars[i]) * 0.4
        pulse.set_clock(True, self.music.style.bpm, beat_phase, bar_phase, level)

    def _music_indicator(self) -> str:
        if not self.music.enabled:
            return ""
        state = self.music.state
        if state == "error":
            return "♪ !"
        if state != "playing":
            return "♪ …"
        bars = "".join("▁▂▃▄▅▆▇█"[min(7, int(b * 8))] for b in self.music_bars)
        return f"♪ {self.music.style_key} {int(self.music.style.bpm)}bpm {bars}"

    def _fix_palette_for_mode(self, pal: Palette) -> None:
        """Monochrome terminals get no painted backgrounds (they'd look nasty)."""
        if self.mode in ("16", "none"):
            pal.bg = (0, 0, 0)
            pal.panel = (0, 0, 0)
            pal.dim = lighten(pal.dim, 0.35)

    def _widget_for(self, rect: Rect, avoid: str | None, used: set[str] | None = None) -> tuple[object, str]:
        pool = [n for n in self.character.widgets if n in widgets.REGISTRY] or ["sparkles"]
        iw = max(6, rect.w - 4)
        ih = max(3, rect.h - 2)

        def fits(name: str, pad: int = 0) -> bool:
            cls = widgets.REGISTRY[name]
            return cls.min_w <= iw + pad and cls.min_h <= ih

        usable = [n for n in pool if fits(n)]
        # small grids would otherwise recycle the same two widgets forever, so top
        # the pool up with other panes that physically fit
        if len(usable) < 8:
            usable += [n for n in widgets.FILLER_ORDER if n not in usable and fits(n)]
        if not usable:
            usable = [n for n in pool if fits(n, pad=8)] or ["sparkles"]
        choices = [n for n in usable if n != avoid] or usable
        if used:
            fresh = [n for n in choices if n not in used]
            if fresh:
                choices = fresh
        name = choices[self.rng.randrange(len(choices))]
        return widgets.make(name, self.rng, self.palette), name

    def _pane_ttl(self) -> float:
        """Seconds until this pane re-rolls, staggered so they don't all flip at once."""
        if self.reroll <= 0.0:
            return float("inf")
        spread = 0.15 + 0.35 * self.character.chaos
        return self.reroll * self.rng.uniform(1.0 - spread, 1.0 + spread)

    def _build_panes(self, count: int) -> None:
        count = max(1, min(24, count))
        area = Rect(0, self.header_h, self.w, max(1, self.h - self.header_h - self.footer_h))
        rects = grid_rects(count, area, min_w=16, min_h=5)
        old = {p.index: p for p in self.panes}
        panes: list[Pane] = []
        used: set[str] = set()
        for i, rect in enumerate(rects):
            pal = self.palette
            avoid = old[i].widget_name if i in old else None
            widget, name = self._widget_for(rect, avoid, used)
            used.add(name)
            color = pal.cycle(i * 2 + 1)
            panes.append(Pane(rect, widget, name, color, self._pane_ttl(), i))
        self.panes = panes

    def _reroll_panes(self) -> None:
        pal = self.palette
        used: set[str] = set()
        for p in self.panes:
            avoid = p.widget_name
            widget, name = self._widget_for(p.rect, avoid, used)
            used.add(name)
            p.widget, p.widget_name = widget, name
            p.age = 0.0
            p.ttl = self._pane_ttl()
            p.color = pal.cycle(p.index * 2 + 1)

    # ------------------------------------------------------------------
    # geometry helpers
    # ------------------------------------------------------------------
    @property
    def big_header(self) -> bool:
        return self.h >= 30

    @property
    def header_h(self) -> int:
        if self.big_header:
            return 8
        if self.h >= 18:
            return 3
        return 2

    @property
    def footer_h(self) -> int:
        return 1 if self.h >= 10 else 0

    # ------------------------------------------------------------------
    # main loop
    # ------------------------------------------------------------------
    def run(self) -> int:
        self.term.start()
        if self.music.enabled:
            self._sync_music()
            self.music.enable()
        start = time.perf_counter()
        last = start
        # force a resize check
        try:
            self._loop(start, last)
        except KeyboardInterrupt:
            pass
        except BrokenPipeError:
            pass
        finally:
            self.music.stop()
            self.term.stop()
        return 0

    def _loop(self, start: float, last: float) -> None:
        target = 1.0 / self.fps
        while self.running:
            now = time.perf_counter()
            dt = min(0.25, now - last)
            last = now
            self.t = now - start
            self.frame += 1

            if self.duration and self.t >= self.duration:
                break

            self._check_resize()
            for key in self.term.read_keys():
                self._on_key(key)
                if not self.running:
                    break
            if not self.running:
                break

            self._update(dt)
            self._draw()
            self.term.write(self.canvas.diff_to(self.prev, self.cz))
            self.term.flush()
            self.prev = self._snapshot()

            slack = target - (time.perf_counter() - now)
            if slack > 0:
                time.sleep(slack)

    def _snapshot(self) -> Canvas:
        snap = Canvas.__new__(Canvas)
        snap.w, snap.h = self.canvas.w, self.canvas.h
        snap.ch = list(self.canvas.ch)
        snap.fg = list(self.canvas.fg)
        snap.bg = list(self.canvas.bg)
        snap.st = list(self.canvas.st)
        return snap

    def _check_resize(self) -> None:
        w, h = term_size()
        if (w, h) != (self.w, self.h):
            self.w, self.h = w, h
            self.canvas = Canvas(w, h)
            self.prev = None
            if self.screen == "main":
                self._build_panes(self.pane_count_override or auto_pane_count(w, h))

    # ------------------------------------------------------------------
    # input
    # ------------------------------------------------------------------
    def _on_key(self, key: str) -> None:
        if self.screen == "boot":
            if key in ("q", "esc", "ctrl-c"):
                self.running = False
            else:
                self.boot_done = True
                self._finish_boot()
            return
        if self.screen == "select":
            self._on_key_select(key)
            return
        # main
        if self.show_help:
            if key in ("q", "esc", "?", "h", "enter", "space"):
                self.show_help = False
            elif key == "ctrl-c":
                self.running = False
            return
        if key in ("q", "esc", "ctrl-c", "ctrl-d"):
            self.running = False
        elif key in ("?", "h"):
            self.show_help = True
        elif key in (" ", "p"):
            self.paused = not self.paused
        elif key == "t":
            self.variant_index = (self.variant_index + 1) % len(VARIANTS)
            self._apply_palette()
            self._note(f"couture: {VARIANTS[self.variant_index]}")
        elif key == "T":
            self.variant_index = (self.variant_index - 1) % len(VARIANTS)
            self._apply_palette()
            self._note(f"couture: {VARIANTS[self.variant_index]}")
        elif key in ("+", "="):
            self.pane_count_override = min(24, len(self.panes) + 1)
            self._build_panes(self.pane_count_override)
            self._note(f"panes: {self.pane_count_override}")
        elif key == "-":
            self.pane_count_override = max(1, len(self.panes) - 1)
            self._build_panes(self.pane_count_override)
            self._note(f"panes: {self.pane_count_override}")
        elif key == "r":
            self._reroll_panes()
            self._note("panes re-rolled")
        elif key == "g":
            self.glitch_fx = not self.glitch_fx
            self._note(f"glitch fx {'on' if self.glitch_fx else 'off'}")
        elif key == "H":
            idx = (art.HEADER_FX.index(self.header_fx) + 1) % len(art.HEADER_FX)
            self.header_fx = art.HEADER_FX[idx]
            self._note(f"header fx: {self.header_fx}")
        elif key == "a":
            self.auto = not self.auto
            self.auto_at = self.t
            self._note(f"auto-cycle {'on' if self.auto else 'off'}")
        elif key == "s":
            self._screenshot()
        elif key == "f":
            if len(self.panes) > 1:
                self.pane_count_override = 1
            else:
                self.pane_count_override = 0
            self._build_panes(self.pane_count_override or auto_pane_count(self.w, self.h))
            self._note("focus mode" if self.pane_count_override else "grid mode")
        elif key == "m":
            on = self.music.toggle()
            self._note(self.music.status_text() if on else "music off")
        elif key == "M":
            keys = music.STYLE_KEYS
            idx = (keys.index(self.music.style_key) + 1) % len(keys)
            self.music_override = keys[idx]
            self.music.set_style(keys[idx], force=True)
            self._note(f"track: {self.music.style.name}")
        elif key in (",", "."):
            step = -0.1 if key == "," else 0.1
            vol = self.music.set_volume(round(self.music.volume + step, 2))
            self._note(f"volume {int(vol * 100)}%")
        elif key.isdigit():
            self._select_by_digit(key)
        elif key == "enter":
            self.screen = "select"
            self.sel_index = self.char_index
            self._note("")

    def _on_key_select(self, key: str) -> None:
        n = len(CHARACTERS)
        cols = self._select_cols()
        prev = self.sel_index
        if key in ("q", "esc", "ctrl-c", "ctrl-d"):
            self.running = False
        elif key in ("left", "h"):
            self.sel_index = (self.sel_index - 1) % n
        elif key in ("right", "l"):
            self.sel_index = (self.sel_index + 1) % n
        elif key in ("up", "k"):
            self.sel_index = (self.sel_index - cols) % n
        elif key in ("down", "j"):
            self.sel_index = (self.sel_index + cols) % n
        elif key in ("home",):
            self.sel_index = 0
        elif key in ("end",):
            self.sel_index = n - 1
        elif key == "enter":
            self.char_index = self.sel_index
            self._start_dashboard()
            self.screen = "main"
            self._note(f"runner: {self.character.name}")
        elif key in ("t", "T"):
            self.variant_index = (self.variant_index + 1) % len(VARIANTS)
            self._note(f"couture: {VARIANTS[self.variant_index]}")
        elif key == "m":
            on = self.music.toggle()
            self._note(self.music.status_text() if on else "music off")
        elif key in (",", "."):
            step = -0.1 if key == "," else 0.1
            vol = self.music.set_volume(round(self.music.volume + step, 2))
            self._note(f"volume {int(vol * 100)}%")
        elif key == "r":
            self.sel_index = self.rng.randrange(n)
            self.char_index = self.sel_index
            self._start_dashboard()
            self.screen = "main"
        elif key.isdigit():
            self._select_by_digit(key, start=True)
        if self.sel_index != prev:
            # audition that runner's tune while browsing the roster
            self.music.set_style(self._music_style_for(self.sel_index))

    def _select_by_digit(self, key: str, start: bool = False) -> None:
        idx = (int(key) - 1) % 10 if key != "0" else 9
        if idx < len(CHARACTERS):
            if start or self.screen == "main":
                self.char_index = idx
                self.sel_index = idx
                self._start_dashboard()
                if start:
                    self.screen = "main"
                self._note(f"runner: {self.character.name}")

    def _start_dashboard_preview(self) -> None:
        """Kept for API compatibility; the select screen is self-contained now."""
        self.char_index = self.sel_index

    def _apply_palette(self) -> None:
        pal = self.palette
        self._fix_palette_for_mode(pal)
        for p in self.panes:
            p.widget.pal = pal
            p.color = pal.cycle(p.index * 2 + 1)

    def _note(self, text: str, secs: float = 2.6) -> None:
        self.message = text
        self.message_until = self.t + secs

    def _screenshot(self) -> None:
        name = f"hollyweeb_{self.character.key}_{int(time.time())}.txt"
        try:
            with open(name, "w", encoding="utf-8") as fh:
                fh.write(self.canvas.to_text())
            self._note(f"saved {name}")
        except OSError as exc:  # pragma: no cover
            self._note(f"screenshot failed: {exc}")

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------
    def _update(self, dt: float) -> None:
        self.music.tick()
        self._update_pulse()
        if self.screen == "boot":
            self.boot_t += dt
            if self.boot_t >= 3.4:
                self.boot_done = True
            if self.boot_done:
                self._finish_boot()
            return
        if self.paused:
            return
        for p in self.panes:
            p.widget.update(dt, self.t)
            p.age += dt
            if not self.static and p.age > p.ttl:
                widget, name = self._widget_for(p.rect, p.widget_name)
                p.widget, p.widget_name = widget, name
                p.age = 0.0
                p.ttl = self._pane_ttl()
                p.color = self.palette.cycle(p.index * 2 + 1)
        # ticker typing
        ticker = self.character.ticker
        if ticker:
            full = strip_wide(ticker[self.ticker_index % len(ticker)])
            if self.typing < len(full):
                self.typing = min(len(full), self.typing + dt * 34)
            elif self.t - self.ticker_done_at > 2.6:
                self.ticker_done_at = self.t
                self.ticker_index += 1
                self.typing = 0.0
            self.ticker_text = full
        if self.auto and self.t - self.auto_at > self.auto_interval:
            self.auto_at = self.t
            self.char_index = (self.char_index + 1) % len(CHARACTERS)
            self.sel_index = self.char_index
            self._start_dashboard()
        # rotate the soundtrack on its own cadence
        if (self.music_rotate > 0 and self.screen == "main" and self.music.enabled
                and self.music.playing and self.t > 1.0):
            if self.music_rotated_at <= 0.0:
                self.music_rotated_at = self.t          # start the clock on first play
            elif self.t - self.music_rotated_at > self.music_rotate:
                self.music_rotated_at = self.t
                self.music.rotate()
                if not self.message:
                    self._note(f"track: {self.music.style.name}", 2.2)
        if self.message and self.t > self.message_until:
            self.message = ""

    def _finish_boot(self) -> None:
        if self.screen != "boot":
            return
        if self.args.character or self.args.no_boot:
            self.screen = "main"
            if not self.panes:
                self._start_dashboard()
        else:
            self.screen = "select"
            self.sel_index = self.char_index
            self._start_dashboard_preview()
            # preview is just for colour; force the real build on selection

    # ------------------------------------------------------------------
    # drawing
    # ------------------------------------------------------------------
    def _draw(self) -> None:
        if self.w < 34 or self.h < 10:
            self._draw_too_small()
            return
        if self.screen == "boot":
            self._draw_boot()
            return
        if self.screen == "select":
            self._draw_select()
            return
        self._draw_dashboard()
        if self.show_help:
            self._draw_help()

    def _view(self, x: int, y: int, w: int, h: int) -> View:
        return View(self.canvas, x, y, w, h)

    def _draw_too_small(self) -> None:
        self.canvas.clear(" ", None, None)
        v = self._view(0, 0, self.w, self.h)
        msg = ["terminal too small", f"{self.w}x{self.h} - need 34x10", "resize or press q"]
        for i, line in enumerate(msg):
            v.text(max(0, (self.w - len(line)) // 2), max(0, self.h // 2 - 1 + i), line,
                   self.palette.hot if i == 0 else self.palette.dim, None, BOLD if i == 0 else 0)

    # -- boot ----------------------------------------------------------
    def _draw_boot(self) -> None:
        pal = self.palette
        self.canvas.clear(" ", None, pal.bg)
        v = self._view(0, 0, self.w, self.h)
        bw = art.banner_width("HOLLYWEEB")
        bx = max(0, (self.w - bw) // 2)
        by = max(1, self.h // 4)
        art.draw_banner_fx(v, bx, by, "HOLLYWEEB", [pal.cycle(0), pal.cycle(1), pal.cycle(2)],
                           t=self.t, mode=self.header_fx, ink="█", hot=pal.hot, cool=pal.cool)
        sub = "a fashion-forward cyberpunk cuteness terminal multiplexer"
        v.text(max(0, (self.w - len(sub)) // 2), by + 6, sub, pal.dim)
        # boot log
        shown = int(self.boot_t / 3.4 * (len(BOOT_LINES) + 2))
        y = by + 8
        for i, (line, lvl) in enumerate(BOOT_LINES):
            if i >= shown or y >= self.h - 3:
                break
            col = {"ok": pal.good, "warn": pal.warn, "err": pal.hot}.get(lvl, pal.fg)
            v.text(max(2, self.w // 2 - 24), y, f"[ {lvl} ]", col, None, BOLD)
            v.text(max(2, self.w // 2 - 16), y, line, pal.fg)
            y += 1
        frac = min(1.0, self.boot_t / 3.4)
        bar_w = max(10, min(60, self.w - 8))
        bx2 = (self.w - bar_w) // 2
        by2 = self.h - 3
        filled = int(frac * bar_w)
        v.hline(bx2, by2, bar_w, "─", darken(pal.dim, 0.4))
        for x in range(bar_w):
            if x < filled:
                v.put(bx2 + x, by2, "█", lerp_ramp([pal.cycle(0), pal.cycle(1)], x / max(1, bar_w - 1)))
        v.text(bx2, by2 + 1, f"{int(frac * 100):3d}%  press any key to skip", pal.dim)
        for k in range(18):
            a = self.t * 1.4 + k * 0.7
            x = int(self.w / 2 + math.cos(a) * (self.w * 0.32))
            yy = int(self.h / 2 + math.sin(a * 1.3) * (self.h * 0.3))
            if v.get(x, yy) == " ":
                v.put(x, yy, "✦" if k % 3 else "✧", mix(pal.bg, pal.cycle(k % 4), 0.7), None, DIM)

    # -- dashboard -----------------------------------------------------
    def _draw_dashboard(self) -> None:
        pal = self.palette
        self.canvas.clear(" ", None, pal.bg)
        self._draw_header(pal)
        area = Rect(0, self.header_h, self.w, max(1, self.h - self.header_h - self.footer_h))
        for p in self.panes:
            self._draw_pane(p, pal)
        self._draw_footer(pal)
        if self.glitch_fx:
            self._apply_glitch(pal)

    def _draw_header(self, pal: Palette) -> None:
        v = self._view(0, 0, self.w, self.header_h)
        ch = self.character
        # animated mixed-colour rule under the header
        v.hgrad(0, self.header_h - 1, self.w,
                art.banner_stops(self.header_fx,
                                 [pal.cycle(0), pal.cycle(1), pal.cycle(2), pal.cycle(3)],
                                 self.t, pal.hot, pal.cool, n=14), "─")
        if self.header_h >= 6:
            bw = art.banner_width("HOLLYWEEB")
            art.draw_banner_fx(v, 1, 0, "HOLLYWEEB",
                               [pal.cycle(0), pal.cycle(1), pal.cycle(2), pal.cycle(3)],
                               t=self.t, mode=self.header_fx, ink="█",
                               hot=pal.hot, cool=pal.cool)
            # mascot + identity on the right when there is room, compact otherwise
            mw = max(0, len(ch.art[0]))
            if self.w >= bw + mw + 34:
                mx = self.w - mw - 30
                v.art(mx, 0, ch.art, [pal.cycle(0), pal.cycle(1), pal.cycle(2), pal.cycle(3)], bg=None)
                tx = mx + mw + 1
            else:
                tx = bw + 4
            v.text(tx, 0, ch.name, pal.cycle(0), None, BOLD)
            v.text(tx, 1, clip(ch.tagline, max(0, self.w - tx - 1)), pal.dim)
            self._draw_swatches(v, tx, 2, pal)
            v.text(tx, 3, f"couture: {VARIANTS[self.variant_index]}", pal.cycle(2))
            tick = self.ticker_text[: int(self.typing)]
            v.text(1, self.header_h - 3, "▌", pal.hot, None, BOLD)
            v.text(2, self.header_h - 3, clip(tick, self.w - 3), pal.fg)
            stats = f"{len(self.panes)} panes  {self.fps}fps  {self.mode}  {int(self.t // 60):02d}:{int(self.t % 60):02d}"
            v.text(max(0, self.w - len(stats) - 2), self.header_h - 2, stats, pal.dim)
            tune = self._music_indicator()
            if tune:
                mx = self.w - len(stats) - 4 - len(tune)
                if mx > 1:
                    v.text(mx, self.header_h - 2, tune, pal.cycle(2))
            if self.paused:
                v.text(1, self.header_h - 2, "PAUSED", pal.warn, None, BOLD)
        else:
            head = " HOLLYWEEB "
            v.text(1, 0, head, pal.cycle(1), None, BOLD)
            v.text(1 + len(head), 0, f"‹ {ch.name} ›", pal.cycle(0), None, BOLD)
            tick = self.ticker_text[: int(self.typing)]
            if self.header_h > 2:
                v.text(1, 1, clip(tick, self.w - 2), pal.dim)
            info = f"{len(self.panes)}p {self.fps}fps"
            if self.music.enabled:
                info = "♪ " + info
            v.text(max(0, self.w - len(info) - 1), 0, info, pal.dim)
            if self.paused:
                v.text(max(0, self.w - len(info) - 7), 0, "PAUSE", pal.warn, None, BOLD)

    def _draw_swatches(self, v: View, x: int, y: int, pal: Palette) -> None:
        for i, col in enumerate(pal.accents):
            v.text(x + i * 3, y, "██", col, None, BOLD)

    def _draw_pane(self, pane: Pane, pal: Palette) -> None:
        r = pane.rect
        if r.w < 4 or r.h < 3:
            return
        v = self._view(r.x, r.y, r.w, r.h)
        interior = mix(pal.panel, pal.bg, 0.35)
        if pane.index % 2:
            interior = mix(interior, pal.cycle(pane.index), 0.05)
        v.box(fg=darken(pane.color, 0.15), bg=interior, style=self.character.border,
              title=pane.widget.label, title_fg=pane.color)
        # pane number + live dot in the top-right of the border (if it fits)
        tag = f"{pane.index + 1:02d}"
        if r.w > len(pane.widget.label) + len(tag) + 10:
            v.text(r.w - len(tag) - 3, 0, tag, pal.dim)
            v.put(r.w - len(tag) - 5, 0, "●", pane.color, None, BOLD)
        inner = Rect(r.x + 2, r.y + 1, max(0, r.w - 4), max(0, r.h - 2))
        if inner.w < 2 or inner.h < 1:
            return
        wv = self._view(inner.x, inner.y, inner.w, inner.h)
        try:
            pane.widget.draw(wv)
        except Exception as exc:  # keep the wall alive even if one widget breaks
            wv.fill(0, 0, wv.w, wv.h, " ", None, None)
            wv.text(0, 0, "widget error", pal.hot, None, BOLD)
            wv.text(0, 1, clip(str(exc), wv.w), pal.dim)

    def _draw_footer(self, pal: Palette) -> None:
        if self.footer_h == 0:
            return
        y = self.h - 1
        v = self._view(0, y, self.w, 1)
        v.hline(0, 0, self.w, " ", None, mix(pal.bg, pal.cycle(1), 0.12))
        left = self.message or f"{self.character.name}  //  {VARIANTS[self.variant_index]}"
        col = pal.hot if self.message else pal.cycle(1)
        v.text(1, 0, clip(left, self.w - 2), col, None, BOLD)
        keys = "q quit · 1-0 runner · enter select · t couture · H header · +/- panes · r reroll · m music · ? help"
        if self.w > len(keys) + len(left) + 6:
            v.text(self.w - len(keys) - 2, 0, keys, pal.dim)

    def _apply_glitch(self, pal: Palette) -> None:
        """Occasional row-shift glitch bursts; intensity driven by character chaos."""
        if self.t - self.last_glitch < 0.35:
            return
        if self.rng.random() > 0.03 + 0.12 * self.character.chaos:
            return
        self.last_glitch = self.t
        cv = self.canvas
        for _ in range(self.rng.randint(1, 3)):
            y = self.rng.randrange(cv.h)
            dx = self.rng.choice([-4, -3, -2, -1, 1, 2, 3, 4])
            a, b = y * cv.w, (y + 1) * cv.w
            for arr in (cv.ch, cv.fg, cv.bg, cv.st):
                row = arr[a:b]
                arr[a:b] = row[-dx:] + row[:-dx]
            tint = pal.hot if self.rng.random() < 0.5 else pal.cool
            for x in range(cv.w):
                if self.rng.random() < 0.25:
                    cv.fg[a + x] = mix(cv.fg[a + x] or pal.fg, tint, 0.7)

    # -- character select ------------------------------------------------
    def _select_layout(self) -> tuple[str, int, int, int, int]:
        """Return (mode, cols, rows, card_w, card_h); mode is 'cards' or 'list'."""
        top = 6 if self.big_header else 1
        area_h = self.h - top - 1
        cards = choose_cards(len(CHARACTERS), self.w, area_h, min_w=16, min_h=7)
        if cards:
            cols, rows, cw, ch = cards
            return "cards", cols, rows, cw, ch
        return "list", 1, max(1, area_h), self.w, 1

    def _select_cols(self) -> int:
        mode, cols, _rows, _cw, _ch = self._select_layout()
        return cols if mode == "cards" else 1

    def _draw_select(self) -> None:
        mode, cols, rows, cw, chh = self._select_layout()
        sel_char = CHARACTERS[self.sel_index]
        pal = sel_char.palette.with_variant(VARIANTS[self.variant_index])
        self._fix_palette_for_mode(pal)
        self.canvas.clear(" ", pal.dim, pal.bg)
        v = self._view(0, 0, self.w, self.h)
        top = 6 if self.big_header else 1
        if top == 6:
            bw = art.banner_width("HOLLYWEEB")
            art.draw_banner_fx(v, max(0, (self.w - bw) // 2), 0, "HOLLYWEEB",
                               [pal.cycle(0), pal.cycle(1), pal.cycle(2)],
                               t=self.t, mode=self.header_fx, ink="█",
                               hot=pal.hot, cool=pal.cool)
            title = "S E L E C T   Y O U R   R U N N E R"
            v.text(max(0, (self.w - len(title)) // 2), 5, title, pal.cycle(3))
        else:
            title = "SELECT YOUR RUNNER"
            v.text(max(0, (self.w - len(title)) // 2), 0, title, pal.cycle(0), None, BOLD)
        v.hline(0, top - 1, self.w, "─", darken(pal.cycle(1), 0.4))
        if mode == "cards":
            self._draw_select_cards(cols, cw, chh, top, pal)
        else:
            self._draw_select_list(top, pal)
        couture = VARIANTS[self.variant_index]
        foot = f"←↑↓→ move · ENTER wear it · t couture ({couture}) · r random · q quit"
        v.text(max(0, (self.w - len(foot)) // 2), self.h - 1, clip(foot, self.w), pal.fg, None, BOLD)

    def _draw_select_cards(self, cols: int, cw: int, chh: int, top: int, pal: Palette) -> None:
        v = self._view(0, 0, self.w, self.h)
        for i, c in enumerate(CHARACTERS):
            col_i = i % cols
            row_i = i // cols
            x = col_i * cw
            y = top + row_i * chh
            w = cw - 1
            h = min(chh - 1, self.h - 1 - y)
            if w < 8 or h < 5:
                continue
            cpal = c.palette.with_variant(VARIANTS[self.variant_index])
            self._fix_palette_for_mode(cpal)
            card = self._view(x, y, w, h)
            sel = i == self.sel_index
            border = cpal.cycle(1) if sel else darken(cpal.cycle(2), 0.5)
            bg = mix(cpal.bg, cpal.panel, 0.45) if sel else cpal.bg
            card.box(fg=border, bg=bg, style=c.border if sel else "round",
                     title=f" {i + 1 if i < 9 else 0} ", title_fg=cpal.cycle(0))
            art_lines = c.art
            content_h = len(art_lines) + 3
            oy = max(1, (h - content_h) // 2)
            ax = max(1, (w - len(art_lines[0])) // 2)
            card.art(ax, oy, art_lines, [cpal.cycle(0), cpal.cycle(1), cpal.cycle(2), cpal.cycle(3)])
            name = c.name
            card.text(max(1, (w - len(name)) // 2), oy + len(art_lines), name,
                      cpal.cycle(0) if sel else cpal.fg, None, BOLD)
            tag = c.tagline
            if oy + len(art_lines) + 1 < h - 1:
                card.text(2, oy + len(art_lines) + 1, clip(tag, max(0, w - 4)), cpal.dim)
            sw_y = oy + len(art_lines) + 2
            if sw_y < h - 1:
                for k, col in enumerate(cpal.accents[: max(1, (w - 4) // 3)]):
                    card.text(2 + k * 3, sw_y, "██", col, None, BOLD)
            if sel:
                card.put(1, 1, "▶", cpal.cycle(3), None, BOLD)
                for k in range(10):
                    a = self.t * 2 + k * 0.8
                    sx = int(w / 2 + math.cos(a) * (w / 2 - 2))
                    sy = int(h / 2 + math.sin(a * 1.4) * (h / 2 - 2))
                    if card.get(sx, sy) == " ":
                        card.put(sx, sy, "✦" if k % 2 else "✧", cpal.cycle(k % 4), None, BOLD)

    def _draw_select_list(self, top: int, pal: Palette) -> None:
        v = self._view(0, 0, self.w, self.h)
        rows = self.h - top - 1
        n = len(CHARACTERS)
        start = max(0, min(n - rows, self.sel_index - rows // 2)) if n > rows else 0
        for k in range(rows):
            i = start + k
            if i >= n:
                break
            c = CHARACTERS[i]
            sel = i == self.sel_index
            cpal = c.palette.with_variant(VARIANTS[self.variant_index])
            y = top + k
            bg = mix(cpal.bg, cpal.panel, 0.55) if sel else None
            label = f" {i + 1 if i < 9 else 0}  {c.name:<16}{c.tagline}"
            v.text(1, y, clip(label, self.w - 2), cpal.cycle(0) if sel else cpal.fg, bg,
                   BOLD if sel else 0)
            if self.w > 60:
                for j, col in enumerate(cpal.accents):
                    v.text(self.w - 16 + j * 3, y, "██", col, bg, BOLD)
            if sel:
                v.text(0, y, "▶", cpal.cycle(3), bg, BOLD)

    # -- help ----------------------------------------------------------
    def _draw_help(self) -> None:
        pal = self.palette
        lines = [
            ("q / esc", "quit"),
            ("1 - 9 , 0", "switch runner instantly"),
            ("enter", "back to character select"),
            ("t / T", "cycle couture variant"),
            ("H", "cycle header effect (holo/rainbow/prism/vapor/glitch/theme)"),
            ("+ / -", "more / fewer panes"),
            ("r", "re-roll every pane"),
            ("space / p", "pause the simulation"),
            ("a", "auto-cycle runners"),
            ("g", "toggle glitch fx"),
            ("s", "save a plain-text screenshot"),
            ("m", "music on / off"),
            ("M", "next music style"),
            (", / .", "volume down / up"),
            ("f", "focus mode (one pane)"),
            ("? / h", "this help"),
        ]
        w = min(self.w - 4, max(46, max(len(a) + len(b) for a, b in lines) + 10))
        h = min(self.h - 2, len(lines) + 6)
        x = (self.w - w) // 2
        y = (self.h - h) // 2
        v = self._view(x, y, w, h)
        v.box(fg=pal.cycle(1), bg=mix(pal.bg, pal.panel, 0.4), style="double",
              title="CONTROLS", title_fg=pal.cycle(0))
        v.text(3, 1, f"{self.character.name} — {self.character.tagline}"[: w - 4], pal.fg)
        for i, (k, desc) in enumerate(lines):
            yy = 2 + i
            if yy >= h - 1:
                break
            v.text(3, yy, k.ljust(12), pal.cycle(i), None, BOLD)
            v.text(16, yy, desc, pal.fg)
        v.text(3, h - 2, "any key closes", pal.dim)


def clip(text: str, w: int) -> str:
    if w <= 0:
        return ""
    return text if len(text) <= w else text[: max(0, w - 1)] + "…"


def _resolve_rotate(value, reroll: float) -> float:
    """Turn `--music-rotate` into seconds: `auto` follows the re-roll cadence."""
    def auto() -> float:
        return reroll * 4.0 if reroll > 0 else 0.0

    if value is None:
        return auto()
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("auto", ""):
            return auto()
        if v in ("off", "never", "none", "no"):
            return 0.0
        try:
            return max(0.0, float(v))
        except ValueError:
            return auto()
    return max(0.0, float(value))


def parse_size(text: str) -> tuple[int, int] | None:
    if not text:
        return None
    try:
        w, h = text.lower().split("x")
        return (max(24, int(w)), max(10, int(h)))
    except Exception:
        return None


def run(args) -> int:
    return App(args).run()
