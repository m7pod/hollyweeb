# HOLYWEEB — `hollyweeb`

[![CI](https://github.com/m7pod/hollyweeb/actions/workflows/ci.yml/badge.svg)](https://github.com/m7pod/hollyweeb/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-ff54aa.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776ab.svg)](pyproject.toml)
[![Platforms](https://img.shields.io/badge/platforms-linux%20%7C%20macos%20%7C%20windows-8a2be2.svg)](#cross-platform-notes)
[![Dependencies](https://img.shields.io/badge/dependencies-none-00c2a8.svg)](pyproject.toml)

A **fashion-forward, cyberpunk, aggressively cute** clone of
[`hollywood`](https://github.com/dustinkirkland/hollywood) that runs in a *single*
terminal window on **Linux, macOS and Windows** — no tmux, no byobu, no root, no
dependencies.

```text
 █   █  ███  █     █     █   █ █   █ █████ █████ ████        \     /   SYNTH SUCCUBUS
 █   █ █   █ █     █      █ █  █   █ █     █     █   █        \   /    your bandwidth belongs to me now
 █████ █   █ █     █       █   █ █ █ ████  ████  ████         (>.<)    ██ ██ ██ ██
 █   █ █   █ █     █       █   ██ ██ █     █     █   █        /|=|\    couture: neon
 █   █  ███  █████ █████   █   █   █ █████ █████ ████          / \      4 panes  24fps  00:08
────────────────────────────────────────────────────────────────────────────────────────────
╭─ vitals ────────●─01──╮╭─ matrix rain ───●─02──╮╭─ wireframe ─────●─03──╮╭─ wave field ────●─04──╮
│ ♥ 121 bpm  spo2 98%   ││   ｽﾊﾗ░  ﾈ  ｬ  ﾓ      ││        •─────•        ││ ░░░▒▒▒▓▓▓███▓▓▒▒░░░ │
│      ╱╲               ││   ﾓ╪ ｷﾄ ╬  ﾂ  ｳﾀ      ││      ╱         ╲      ││ ░░░░▒▒▒▓▓▓███▓▒▒░░░ │
│ ────╯  ╰──╮           ││   ﾚ0 ｾﾋ ╱  ﾉ  ｺﾇ      ││    •             •    ││ ░░░░░▒▒▒▓▓▓▓▓▒▒░░░ │
│            ╰────♥     ││   ┼ｫｸﾅﾒ ｩ  ﾐ  ﾁﾎ      ││      ╲         ╱      ││ ░░░░░░▒▒▒▓▓▓▓▒▒░░░ │
╰───────────────────────╯╰──────────────────────╯╰──────────────────────╯╰──────────────────────╯
```

## Why it exists

`hollywood` spawns a wall of `cat`, `hexdump`, `nmap`-ish noise in many terminal
split panes. It needs a Linux tty-multiplexer stack (`byobu`, `tmux`, `apg`,
`caca-utils`…) so Windows and macOS users are out of luck, and it looks like a
1998 basement.

**hollyweeb** is a from-scratch, dependency-free, double-buffered TUI that:

* renders the *entire* pane wall itself (one terminal window, no tmux),
* is a **character-selectable** aesthetic: 10 runners, each with their own
  mascot, palette, ticker, glyph set and widget pool,
* has **8 "couture" colour variants** (neon, pastel, ice, sunset, acid, vhs, mono…)
  you can cycle live,
* detects and degrades truecolor → 256 → 16 → plain, so it looks good in
  Windows Terminal, iTerm2, kitty, foot, xterm, screen, tmux and serial consoles,
* stays under ~30 fps of pure-Python simulation using a diffed cell canvas.

## Install

Install once and you get a **`hollyweeb` command** — Python 3.9+ and any terminal,
nothing else (no pip packages, no tmux, no ncurses).

```bash
# straight from GitHub
pip install "git+https://github.com/m7pod/hollyweeb.git"

# or from a clone (add -e for an editable install while hacking on it)
git clone https://github.com/m7pod/hollyweeb && cd hollyweeb
pip install .
```

**Helper installers** (use `pipx`/`uv` when available, else `pip --user`):

```bash
./install.sh                   # Linux / macOS
```

```powershell
.\install.ps1                   # Windows
```

Then, from anywhere:

```bash
hollyweeb                      # boot animation, then character select
hollyweeb -c neko              # straight to Neon Neko
```

**Prefer no install at all?** Run it straight from a checkout — same CLI, same
behaviour, just without the `hollyweeb` command on your PATH:

```bash
python run.py                  # Linux / macOS / Windows
python -m hollyweeb            # equivalent, from inside the checkout
```

## Use

```bash
hollyweeb                        # boot animation, then character select
hollyweeb -c neko                # straight to Neon Neko
hollyweeb -c ronin --panes 12 --fps 30
hollyweeb -c idol --variant pastel
hollyweeb --auto                 # attract mode: cycles runners every 22s
hollyweeb --list                 # show runners, palettes, widgets
hollyweeb --duration 20          # exit after 20 seconds
```

### Keys

| Key | Action |
| --- | --- |
| `q` / `esc` | quit (during boot: skip) |
| `1`…`9`, `0` | switch runner instantly |
| `t` / `T` | cycle couture variant |
| `+` / `-` | more / fewer panes |
| `r` | re-roll every pane |
| `space` / `p` | pause the simulation |
| `a` | auto-cycle runners |
| `g` | toggle glitch fx |
| `s` | save a plain-text screenshot |
| `m` | solo mode (one big pane) |
| `enter` (in main) | back to character select |
| `?` / `h` | help overlay |

On the select screen: arrows / `hjkl` move, `enter` wears it, `t` previews
variants, `r` is random, digits jump straight in, `q` quits.

## The cast

| # | Runner | Vibe |
| - | ------ | ---- |
| 1 | **NEON NEKO** | catgirl sysadmin — nine lives, zero uptime |
| 2 | **GLITCH GEISHA** | tea ceremony at 240 baud, poison in the packet |
| 3 | **CHROME RONIN** | no master, no firewall, only the blade |
| 4 | **SYNTH SUCCUBUS** | your bandwidth belongs to me now, darling |
| 5 | **VAPOR IDOL** | debut stage: mainframe, encore: forever |
| 6 | **DATA KITSUNE** | nine tails, nine proxies, one truth |
| 7 | **RAMEN RUNNER** | hot broth, cold code, 3 a.m. delivery |
| 8 | **CORPO SUIT** | quarterly earnings up, ethics deprecated |
| 9 | **ANDROID ANGEL** | halo firmware 7.0, bless this socket |
| 0 | **PANDA PROTOCOL** | bamboo firewall, bite-sized exploits |

Each runner has a weighted widget pool, a glyph set for the rain panes, a
border style and a chaos level that drives how fast panes re-roll and glitch.

## Widgets (27)

`matrix` · `katakana_rain` · `kawaii_rain` · `sparkles` · `hexdump` · `packets` ·
`nmap` · `logstream` · `progress` · `spectrum` · `wave` · `vu` · `sysmon` ·
`cube` · `globe` · `starfield` · `terrain` · `dna` · `cat` · `heartbeat` ·
`glitch` · `clock` · `crypto` · `radar` · `netmap` · `banner` · `fires`

Panes are picked to fit the space available (small terminals fall back to a pool
of compact widgets), prefer not to repeat, and re-roll on a character-dependent
timer unless you pass `--static`.

## CLI reference

```
-c, --character NAME    runner to start with (see --list)
-p, --panes N           number of panes (0 = auto)
    --variant NAME      signature|neon|pastel|ice|sunset|acid|vhs|mono
-f, --fps N             target frames per second (default 24)
    --color MODE        auto|truecolor|256|16|none
    --seed N            reproducible chaos
    --duration SECS     exit automatically
    --auto              start in auto-cycle mode
    --auto-interval S   seconds between auto switches (default 22)
    --static            never re-roll panes
    --no-glitch         disable glitch effects
    --no-boot           skip the boot animation
    --no-alt-screen     draw in the normal buffer (keeps scrollback)
    --list              list runners + widgets, then exit
    --selftest          render every widget/variant headlessly, then exit
    --shot FILE         headless render to FILE (.ansi for raw escapes)
    --frames N          frames to simulate for --shot/--selftest
    --size WxH          virtual terminal size for --shot
    --screen main|select|boot   which screen --shot renders
```

## Cross-platform notes

| Platform | Notes |
| -------- | ----- |
| **Windows** | Works in Windows Terminal, VS Code, Alacritty, ConEmu, mintty/Git-Bash. `hollyweeb` enables `ENABLE_VIRTUAL_TERMINAL_PROCESSING` and UTF-8 (CP65001) itself; the legacy console host (conhost) gets 256 colours. Keys are read with `msvcrt`, arrows included. |
| **macOS** | Terminal.app, iTerm2, kitty, WezTerm, Ghostty. Truecolor is auto-detected from `COLORTERM`. |
| **Linux** | Any xterm-compatible terminal; also inside `tmux`/`screen` (it nests a full-screen app, so no `hollywood`-style pane multiplexing is required). `SIGWINCH` triggers re-layout. |
| **Anything ancient** | `--color 16`, `TERM=dumb`, or `NO_COLOR=1` all degrade gracefully. |

Because hollyweeb paints its own panes, it also works over SSH, in a
`docker run -it`, in GitHub Actions logs (`--color 256`), or piped to a file.

## Headless / CI

```bash
python -m hollyweeb --selftest                       # every widget × variant × size
python -m hollyweeb --shot banner.txt --size 140x42 --frames 120 -c geisha
python -m hollyweeb --shot banner.ansi --size 140x42 --frames 120 -c neko
python -m unittest discover -s tests -v
```

`--shot` renders the real app (layout, borders, header, ticker) without a tty,
which makes it easy to grab screenshots for docs.

## Extending

Add a widget in `hollyweeb/widgets.py`:

```python
class MyPane(Widget):
    name = "mypane"          # registry key
    label = "my pane"        # border title
    min_w, min_h = 12, 4

    def update(self, dt, t):
        super().update(dt, t)      # keeps self.t / self.dt fresh
        ...

    def draw(self, view):
        view.text(0, 0, "hello", self.pal.cycle(0))
```

…then append the class to `WIDGET_CLASSES`. Add a character in
`hollyweeb/palettes.py` (mascot art lives in `hollyweeb/art.py`) and reference
your widget names in its `widgets=[...]` pool. Both are picked up by the
select screen, `--list` and the test-suite automatically.

## How it works

* `canvas.py` — flat `(char, fg, bg, style)` cell grid + clipped sub-`View`s and
  a row-level diff that emits cursor moves only for changed runs.
* `term.py` — raw mode, alt screen, resize detection, non-blocking key decoding
  (termios+select on POSIX, msvcrt on Windows), plus narrow-glyph filtering so
  the grid never desynchronises in terminals that render ambiguous-width
  characters differently.
* `color.py` — RGB maths (HSV shifts for variants) and truecolor/256/16 encoders.
* `widgets.py` — 27 self-contained animations; `layout.py` — pane/card grids;
  `app.py` — boot, select and dashboard screens, keybindings and glitch fx.

## License

MIT. Not affiliated with `hollywood`, Hollywood, or the concept of fame.
