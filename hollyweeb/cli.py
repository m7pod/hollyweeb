"""Command line interface: `hollyweeb` and `python -m hollyweeb`."""

from __future__ import annotations

import argparse
import random
import sys

from . import __version__, art, widgets
from .canvas import Canvas, View
from .color import MODE_TRUECOLOR, detect_mode
from .palettes import CHARACTERS, VARIANTS
from .term import prepare_console


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hollyweeb",
        description="A fashion-forward, cyberpunk, aggressively cute clone of `hollywood`.",
        epilog="examples:\n"
               "  hollyweeb                      # boot, then pick a runner\n"
               "  hollyweeb -c neko              # straight to Neon Neko\n"
               "  hollyweeb -c ronin --panes 12 --fps 30\n"
               "  hollyweeb --variant pastel -c idol\n"
               "  hollyweeb --list\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-c", "--character", metavar="NAME", help="runner to start with (see --list)")
    p.add_argument("-p", "--panes", type=int, default=0, metavar="N", help="number of panes (0 = auto)")
    p.add_argument("--variant", metavar="NAME", help="couture variant: " + ", ".join(VARIANTS))
    p.add_argument("-f", "--fps", type=int, default=24, help="target frames per second (default 24)")
    p.add_argument("--color", default="auto", choices=["auto", "truecolor", "256", "16", "none"],
                   help="force a colour mode (default: auto-detect)")
    p.add_argument("--seed", type=int, default=None, help="random seed for reproducible chaos")
    p.add_argument("--duration", type=float, default=0.0, metavar="SECS",
                   help="exit automatically after SECS seconds")
    p.add_argument("--auto", action="store_true", help="start in auto-cycle mode")
    p.add_argument("--auto-interval", type=float, default=22.0, metavar="SECS",
                   help="seconds between auto character switches")
    p.add_argument("--static", action="store_true", help="never re-roll panes")
    p.add_argument("--no-glitch", action="store_true", help="disable glitch effects")
    p.add_argument("--no-boot", action="store_true", help="skip the boot animation")
    p.add_argument("--no-alt-screen", action="store_true",
                   help="draw in the normal screen buffer (keeps scrollback)")
    p.add_argument("--list", action="store_true", help="list runners, palettes and widgets, then exit")
    p.add_argument("--selftest", action="store_true", help="render every widget/character headlessly, then exit")
    p.add_argument("--shot", metavar="FILE",
                   help="headless: render frames and write a frame to FILE (.ansi for raw escape output)")
    p.add_argument("--frames", type=int, default=60, help="frames to simulate for --shot/--selftest")
    p.add_argument("--size", metavar="WxH", default="120x36", help="virtual terminal size for --shot")
    p.add_argument("--screen", default="main", choices=["main", "select", "boot"],
                   help="which screen to render for --shot")
    p.add_argument("-V", "--version", action="version", version=f"hollyweeb {__version__}")
    return p


def parse_size(text: str) -> tuple[int, int] | None:
    if not text:
        return None
    try:
        w, h = text.lower().split("x")
        return (max(20, int(w)), max(8, int(h)))
    except Exception:
        return None


# --------------------------------------------------------------------------
# informational commands
# --------------------------------------------------------------------------


def cmd_list() -> int:
    prepare_console()
    cz = detect_mode("auto")
    print(f"hollyweeb {__version__}  (colour: {cz})\n")
    print("RUNNERS")
    for i, c in enumerate(CHARACTERS):
        key = str(i + 1) if i < 9 else "0"
        print(f"  [{key}] {c.name:<16} {c.tagline}")
        swatch = "".join(f"\x1b[48;2;{r};{g};{b}m  " for r, g, b in c.palette.accents[:4])
        print(f"       {swatch}\x1b[0m  widgets: {', '.join(c.widgets[:6])}…")
    print("\nCOUTURE VARIANTS")
    print("  " + ", ".join(VARIANTS))
    print("\nWIDGETS")
    labels = widgets.widget_labels()
    for name in sorted(labels):
        print(f"  {name:<16} {labels[name]}")
    print("\nKEYS: q quit · 1-0 runner · t couture · +/- panes · r reroll · space pause · "
          "a auto · g glitch · s shot · ? help")
    return 0


def cmd_selftest(frames: int) -> int:
    """Headless smoke test: every widget x every palette variant x several sizes."""
    rng = random.Random(7)
    failures = 0
    sizes = [(14, 5), (28, 8), (48, 14), (8, 3)]
    for cls in widgets.WIDGET_CLASSES:
        for variant in VARIANTS:
            pal = CHARACTERS[0].palette.with_variant(variant)
            for (w, h) in sizes:
                cv = Canvas(w, h)
                view = View(cv, 0, 0, w, h)
                try:
                    wdg = cls(rng, pal)
                    for f in range(frames):
                        wdg.update(1 / 24, f / 24)
                        cv.clear(" ", None, pal.bg)
                        wdg.draw(view)
                except Exception as exc:  # noqa: BLE001
                    failures += 1
                    print(f"FAIL {cls.name:<16} {variant:<10} {w}x{h}: {type(exc).__name__}: {exc}")
    for c in CHARACTERS:
        for variant in VARIANTS:
            pal = c.palette.with_variant(variant)
            for name in c.widgets:
                if name not in widgets.REGISTRY:
                    failures += 1
                    print(f"FAIL {c.key}: widget '{name}' is not registered")
    print(f"selftest: {len(widgets.WIDGET_CLASSES)} widgets x {len(VARIANTS)} variants x {len(sizes)} sizes"
          f" -> {'OK' if not failures else str(failures) + ' FAILURES'}")
    return 1 if failures else 0


def cmd_shot(args) -> int:
    """Headless render to a file (great for CI, docs, or a quick look)."""
    from .app import App

    size = parse_size(args.size) or (120, 36)
    args_no_tty = argparse.Namespace(**vars(args))
    args_no_tty.character = args.character or "neko"
    args_no_tty.no_boot = args.screen != "boot"
    args_no_tty.size = f"{size[0]}x{size[1]}"
    app = App(args_no_tty)
    app.w, app.h = size
    app.canvas = Canvas(size[0], size[1])
    app.prev = None
    app.screen = args.screen
    if args.screen in ("main", "select"):
        app._start_dashboard()
    dt = 1 / 24
    for _ in range(max(1, args.frames)):
        app.t += dt
        app.frame += 1
        app._update(dt)
        app._draw()
    if args.shot.endswith(".ansi"):
        from .color import Colorizer

        data = app.canvas.diff_to(None, Colorizer(MODE_TRUECOLOR))
    else:
        data = app.canvas.to_text()
    with open(args.shot, "w", encoding="utf-8") as fh:
        fh.write(data if data.endswith("\n") else data + "\n")
    print(f"wrote {args.shot} ({size[0]}x{size[1]}, {args.frames} frames, screen={args.screen})")
    return 0


# --------------------------------------------------------------------------
# entry point
# --------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.list:
        return cmd_list()
    if args.selftest:
        return cmd_selftest(args.frames)
    if args.shot:
        return cmd_shot(args)
    if args.seed is None:
        args.seed = random.randrange(1 << 30)
    from .app import run

    try:
        return run(args)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
