"""
Tests for hollyweeb. Pure stdlib:  python -m unittest discover -s tests -v
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hollyweeb import art, widgets  # noqa: E402
from hollyweeb.canvas import Canvas, View  # noqa: E402
from hollyweeb.cli import build_parser  # noqa: E402
from hollyweeb.color import (  # noqa: E402
    Colorizer,
    MODE_16, MODE_256, MODE_NONE, MODE_TRUECOLOR,
    lerp_ramp, rgb_to_16, rgb_to_256,
)
from hollyweeb.layout import Rect, auto_pane_count, choose_cards, choose_grid, grid_rects  # noqa: E402
from hollyweeb.palettes import CHARACTERS, VARIANTS  # noqa: E402
from hollyweeb.term import char_width, decode_keys, narrow_only  # noqa: E402


def make_args(**kw) -> argparse.Namespace:
    args = build_parser().parse_args(["--no-boot"])
    for k, v in kw.items():
        setattr(args, k, v)
    return args


class TestColor(unittest.TestCase):
    def test_quantisation_ranges(self):
        for rgb in [(0, 0, 0), (255, 255, 255), (255, 0, 128), (12, 200, 45), (128, 128, 128)]:
            self.assertTrue(0 <= rgb_to_256(rgb) <= 255)
            self.assertTrue(0 <= rgb_to_16(rgb) <= 15)

    def test_colorizer_modes(self):
        c = (10, 200, 255)
        self.assertTrue(Colorizer(MODE_TRUECOLOR).code(c).startswith("\x1b[38;2;"))
        self.assertTrue(Colorizer(MODE_256).code(c).startswith("\x1b[38;5;"))
        self.assertTrue(Colorizer(MODE_16).code(c).startswith("\x1b[38;"))
        self.assertEqual(Colorizer(MODE_NONE).code(c), "")
        self.assertTrue(Colorizer(MODE_TRUECOLOR).code(c, bg=True).startswith("\x1b[48;2;"))

    def test_ramp_endpoints(self):
        stops = [(0, 0, 0), (255, 255, 255)]
        self.assertEqual(lerp_ramp(stops, 0.0), (0, 0, 0))
        self.assertEqual(lerp_ramp(stops, 1.0), (255, 255, 255))
        self.assertEqual(lerp_ramp([(1, 2, 3)], 0.5), (1, 2, 3))


class TestLayout(unittest.TestCase):
    def test_grids_cover_area(self):
        area = Rect(0, 0, 120, 40)
        for n in range(1, 21):
            rects = grid_rects(n, area, min_w=12, min_h=4)
            self.assertEqual(len(rects), n)
            for r in rects:
                self.assertGreater(r.w, 0)
                self.assertGreater(r.h, 0)
                self.assertLessEqual(r.x + r.w, area.w)
                self.assertLessEqual(r.y + r.h, area.h)

    def test_choose_grid_sane(self):
        cols, rows = choose_grid(6, 120, 40, min_w=10, min_h=4)
        self.assertGreaterEqual(cols * rows, 6)
        self.assertEqual(choose_grid(1, 80, 24), (1, 1))

    def test_choose_cards(self):
        got = choose_cards(10, 100, 28, min_w=16, min_h=7)
        self.assertIsNotNone(got)
        cols, rows, cw, ch = got
        self.assertGreaterEqual(cols * rows, 10)
        self.assertGreaterEqual(cw, 16)
        self.assertGreaterEqual(ch, 7)
        self.assertIsNone(choose_cards(10, 20, 4, min_w=16, min_h=7))

    def test_auto_panes(self):
        self.assertGreaterEqual(auto_pane_count(240, 60), 12)
        self.assertEqual(auto_pane_count(20, 5), 1)
        self.assertLessEqual(auto_pane_count(400, 100), 20)


class TestCanvas(unittest.TestCase):
    def test_clipping(self):
        cv = Canvas(4, 2)
        v = View(cv, 0, 0, 4, 2)
        v.put(-1, 0, "x")
        v.put(9, 9, "x")
        v.text(2, 0, "abcd")
        self.assertEqual(cv.get(2, 0), "a")
        self.assertEqual(cv.get(3, 0), "b")
        self.assertEqual(cv.to_text().count("\n"), 1)

    def test_diff_only_touches_changes(self):
        cv = Canvas(8, 2)
        cv.clear(" ", None, None)
        prev = Canvas(8, 2)
        prev.clear(" ", None, None)
        cz = Colorizer(MODE_TRUECOLOR)
        self.assertEqual(cv.diff_to(prev, cz), "")
        cv.put(3, 1, "Z", (255, 0, 0))
        out = cv.diff_to(prev, cz)
        self.assertIn("\x1b[2;4H", out)
        self.assertIn("Z", out)

    def test_art_helpers(self):
        cv = Canvas(40, 8)
        v = View(cv, 0, 0, 40, 8)
        v.box(fg=(255, 255, 255), title="hi")
        self.assertEqual(cv.get(0, 0), "╭")
        v.hgrad(1, 3, 10, [(0, 0, 0), (255, 255, 255)])
        self.assertNotEqual(cv.get(1, 3), " ")


class TestWidgets(unittest.TestCase):
    SIZES = [(10, 4), (20, 6), (40, 12)]

    def test_all_widgets_render(self):
        rng = random.Random(3)
        for cls in widgets.WIDGET_CLASSES:
            pal = CHARACTERS[0].palette
            for w, h in self.SIZES:
                cv = Canvas(w, h)
                view = View(cv, 0, 0, w, h)
                widget = cls(rng, pal)
                for f in range(10):
                    widget.update(1 / 24, f / 24)
                    cv.clear(" ", None, pal.bg)
                    widget.draw(view)
                self.assertTrue(any(ch != " " for ch in cv.ch), f"{cls.name} drew nothing at {w}x{h}")

    def test_all_widgets_all_variants(self):
        rng = random.Random(11)
        for cls in widgets.WIDGET_CLASSES:
            for variant in VARIANTS:
                pal = CHARACTERS[1].palette.with_variant(variant)
                cv = Canvas(24, 8)
                widget = cls(rng, pal)
                widget.update(1 / 24, 0.5)
                widget.draw(View(cv, 0, 0, 24, 8))

    def test_character_pools_are_valid(self):
        for c in CHARACTERS:
            self.assertTrue(c.widgets)
            for name in c.widgets:
                self.assertIn(name, widgets.REGISTRY, f"{c.key} -> {name}")
            self.assertGreaterEqual(len(c.art), 3)

    def test_registry_labels(self):
        labels = widgets.widget_labels()
        self.assertEqual(set(labels), set(widgets.REGISTRY))
        self.assertTrue(all(labels.values()))


class TestPalettes(unittest.TestCase):
    def test_variants_valid(self):
        for c in CHARACTERS:
            for variant in VARIANTS:
                pal = c.palette.with_variant(variant)
                for rgb in list(pal.accents) + [pal.bg, pal.panel, pal.fg, pal.dim, pal.hot, pal.cool]:
                    self.assertEqual(len(rgb), 3)
                    self.assertTrue(all(0 <= v <= 255 for v in rgb), f"{c.key}/{variant} -> {rgb}")
                self.assertGreaterEqual(len(pal.accents), 1)

    def test_unique_keys_names(self):
        keys = [c.key for c in CHARACTERS]
        names = [c.name for c in CHARACTERS]
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(len(set(names)), len(names))

    def test_ramp_and_shade(self):
        pal = CHARACTERS[0].palette
        for t in (0.0, 0.5, 1.0):
            self.assertEqual(len(pal.ramp(t)), 3)
            self.assertEqual(len(pal.shade(t)), 3)


class TestTerm(unittest.TestCase):
    def test_decode_arrows(self):
        self.assertEqual(decode_keys("\x1b[A"), ["up"])
        self.assertEqual(decode_keys("\x1b[B\x1b[C\x1b[D"), ["down", "right", "left"])
        self.assertEqual(decode_keys("\x1b[3~"), ["delete"])
        self.assertEqual(decode_keys("q"), ["q"])
        self.assertEqual(decode_keys(" "), ["space"])
        self.assertEqual(decode_keys("\r"), ["enter"])
        self.assertEqual(decode_keys("\x03"), ["ctrl-c"])
        self.assertEqual(decode_keys("\x1b"), ["esc"])

    def test_narrow_only(self):
        self.assertEqual(narrow_only("aｱ漢b"), "aｱb")
        self.assertEqual(char_width("a"), 1)
        self.assertEqual(char_width("漢"), 2)
        self.assertEqual(char_width("ｱ"), 1)

    def test_banner(self):
        rows = art.render_banner("A")
        self.assertEqual(len(rows), art.FONT_H)
        self.assertEqual(art.banner_width("AB"), 11)
        self.assertEqual(len(rows[0]), art.FONT_W)


class TestApp(unittest.TestCase):
    def _app(self, **kw):
        from hollyweeb.app import App

        args = make_args(size="96x28", character="neko", seed=5, fps=30, panes=6, **kw)
        return App(args)

    def test_headless_frames(self):
        app = self._app()
        app.screen = "main"
        app._start_dashboard()
        for i in range(30):
            app.t += 1 / 30
            app._update(1 / 30)
            app._draw()
        self.assertTrue(any(ch != " " for ch in app.canvas.ch))

    def test_keys_do_not_crash(self):
        app = self._app()
        app.screen = "main"
        app._start_dashboard()
        app._screenshot = lambda: None  # never touch the filesystem in tests
        keys = list("qwertyuiopasdfghjklzxcvbnm1234567890+-=/*?") + [
            "up", "down", "left", "right", "enter", "esc", "space", "tab",
        ]
        for key in keys:
            for screen in ("main", "select", "boot"):
                app.screen = screen
                app.running = True
                app._on_key(key)
                app._update(1 / 30)
                app._draw()
        # the app must be able to keep rendering afterwards
        app.screen = "main"
        app._draw()

    def test_every_character_and_variant_renders(self):
        app = self._app()
        for i in range(len(CHARACTERS)):
            for v in range(len(VARIANTS)):
                app.char_index = i
                app.variant_index = v
                app.screen = "main"
                app._start_dashboard()
                app.t += 0.5
                app._update(1 / 30)
                app._draw()
                self.assertTrue(any(ch != " " for ch in app.canvas.ch))

    def test_select_screen_both_modes(self):
        app = self._app()
        for size in ((60, 16), (100, 30), (140, 44)):
            app.w, app.h = size
            app.canvas = Canvas(*size)
            app.prev = None
            app.screen = "select"
            app._draw()
            mode = app._select_layout()[0]
            self.assertIn(mode, ("cards", "list"))
            self.assertTrue(any(ch != " " for ch in app.canvas.ch))

    def test_tiny_terminal_message(self):
        app = self._app()
        app.w, app.h = 20, 6
        app.canvas = Canvas(20, 6)
        app.screen = "main"
        app._draw()
        text = app.canvas.to_text()
        self.assertIn("small", text)

    def test_parse_size(self):
        from hollyweeb.app import parse_size

        self.assertEqual(parse_size("80x24"), (80, 24))
        self.assertIsNone(parse_size("nope"))
        self.assertIsNone(parse_size(""))


if __name__ == "__main__":
    unittest.main(verbosity=2)
