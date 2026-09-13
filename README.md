# HOLYWEEB — `hollyweeb`

[![CI](https://github.com/m7pod/hollyweeb/actions/workflows/ci.yml/badge.svg)](https://github.com/m7pod/hollyweeb/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-ff54aa.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776ab.svg)](pyproject.toml)
[![Platforms](https://img.shields.io/badge/platforms-linux%20%7C%20macos%20%7C%20windows-8a2be2.svg)](#cross-platform-notes)
[![Dependencies](https://img.shields.io/badge/dependencies-none-00c2a8.svg)](pyproject.toml)

A **fashion-forward, cyberpunk, aggressively cute** clone of
[`hollywood`](https://github.com/dustinkirkland/hollywood) that runs in a *single*
terminal window on **Linux, macOS and Windows** — no tmux, no byobu, no root, no
dependencies — with its own **procedurally synthesised soundtrack** and a cast of
runners to choose from.

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
* **synthesises its own soundtrack** — ten procedurally generated electronic
  styles (synthwave, chiptune, techno, city pop, ambient…), one per runner, in
  pure Python, and the visuals pulse in time with the beat,
* has an **animated mixed-colour wordmark** — the header runs the full hue wheel
  across its letters with a travelling gloss, instead of one flat theme gradient,
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
hollyweeb --no-music             # ...and no soundtrack
hollyweeb --auto                 # attract mode: cycles runners every 22s
hollyweeb --list                 # show runners, palettes, soundtracks, widgets
hollyweeb --duration 20          # exit after 20 seconds
```

Music plays by default — every runner has its own tune — see
[Background music](#background-music) for the ten styles and how to silence it.

### Keys

| Key | Action |
| --- | --- |
| `q` / `esc` | quit (during boot: skip) |
| `1`…`9`, `0` | switch runner instantly |
| `t` / `T` | cycle couture variant |
| `H` | cycle header effect |
| `+` / `-` | more / fewer panes |
| `r` | re-roll every pane |
| `space` / `p` | pause the simulation |
| `m` | music on / off |
| `M` | next music style |
| `,` / `.` | volume down / up |
| `a` | auto-cycle runners |
| `g` | toggle glitch fx |
| `s` | save a plain-text screenshot |
| `f` | focus mode (one big pane) |
| `enter` (in main) | back to character select |
| `?` / `h` | help overlay |

On the select screen: arrows / `hjkl` move, `enter` wears it, `t` previews
variants, `r` is random, digits jump straight in, `q` quits.

## The cast

| # | Runner | Vibe | Tune |
| - | ------ | ---- | ---- |
| 1 | **NEON NEKO** | catgirl sysadmin — nine lives, zero uptime | `chiptune` |
| 2 | **GLITCH GEISHA** | tea ceremony at 240 baud, poison in the packet | `koto` |
| 3 | **CHROME RONIN** | no master, no firewall, only the blade | `darkwave` |
| 4 | **SYNTH SUCCUBUS** | your bandwidth belongs to me now, darling | `synthwave` |
| 5 | **VAPOR IDOL** | debut stage: mainframe, encore: forever | `citypop` |
| 6 | **DATA KITSUNE** | nine tails, nine proxies, one truth | `taiko` |
| 7 | **RAMEN RUNNER** | hot broth, cold code, 3 a.m. delivery | `lofi` |
| 8 | **CORPO SUIT** | quarterly earnings up, ethics deprecated | `techno` |
| 9 | **ANDROID ANGEL** | halo firmware 7.0, bless this socket | `ambient` |
| 0 | **PANDA PROTOCOL** | bamboo firewall, bite-sized exploits | `trance` |

Each runner has a weighted widget pool, a glyph set for the rain panes, a
border style, a chaos level that drives how fast panes re-roll and glitch, and
its own soundtrack (see below).

### Header effects

The big `HOLLYWEEB` wordmark is not painted with one palette gradient — it runs
an animated colour effect across its letters, and so does the rule under the
header. Cycle them live with <kbd>H</kbd> or pick one up front:

```bash
hollyweeb --header-fx rainbow
```

| Effect | Look |
| ------ | ---- |
| `holo` *(default)* | each letter takes its own hue off the theme, mixed with a complementary tone and a travelling white gloss |
| `rainbow` | the full spectrum sweeping along the wordmark |
| `prism` | refracted hues with a hot/cool chromatic ghost either side of the glyphs |
| `confetti` | every cell picks a random pastel from a mixed pool, sparkling at 5 Hz |
| `vapor` | pink → cyan → lilac → cream pastel drift |
| `glitch` | datamoshed hues plus RGB-split edges |
| `theme` | the original single-palette gradient |

## Widgets (27)

`matrix` · `katakana_rain` · `kawaii_rain` · `sparkles` · `hexdump` · `packets` ·
`nmap` · `logstream` · `progress` · `spectrum` · `wave` · `vu` · `sysmon` ·
`cube` · `globe` · `starfield` · `terrain` · `dna` · `cat` · `heartbeat` ·
`glitch` · `clock` · `crypto` · `radar` · `netmap` · `banner` · `fires`

Panes are picked to fit the space available (small terminals fall back to a pool
of compact widgets), prefer not to repeat, and re-roll on a character-dependent
timer unless you pass `--static`.

## Background music

hollyweeb **plays a soundtrack by default** — one that is **synthesised on the
fly from wavetables**, so it stays zero-dependency and ships no audio files.
Each runner gets its own tune, so the music changes when you switch characters
(and you hear each one while browsing the select screen):

```bash
hollyweeb                               # Neon Neko, chiptune, 132 bpm
hollyweeb -c corpo                      # minimal techno at 128 bpm
hollyweeb --no-music                    # ...or run it completely silent
hollyweeb --music-style ambient         # ignore the runner, keep it calm
hollyweeb --music-bpm 90 --music-bars 8
hollyweeb --music-volume 0.4
```

Not a fan of surprise audio on every launch? Silence it for good:

```bash
export HOLLYWEEB_MUSIC=0                # Windows: setx HOLLYWEEB_MUSIC 0
```

Ten styles, each a small parameter set for the same engine (chord progression,
drum grid, bass/arp/pad/lead voices, filter, drive, sidechain, stereo width):

| Style | Feel |
| ----- | ---- |
| `synthwave` | neon arpeggios, gated pads, 4-on-the-floor |
| `chiptune` | 8-bit square leads, octave-bouncing bass |
| `koto` | hirajoshi pentatonic plucks, taiko-ish drums |
| `darkwave` | driving minor bass, cold pads |
| `citypop` | maj7 chords, bright organs, night-drive bass |
| `taiko` | percussive, pentatonic, ritualistic |
| `lofi` | swung, warm, deliberately dull filter |
| `techno` | minimal, rolling acid bass, offbeat open hats |
| `ambient` | beatless evolving pads |
| `trance` | rolling bass + supersaw pads at 138 bpm |

**The visuals listen too.** The synth publishes a beat clock, so the bongo cat
taps on the beat, VU meters and the spectrum kick on the kick drum, and the
`vitals` pane takes the track's BPM as its heart rate. The header shows the
track, tempo and a live equaliser: `♪ synthwave 104bpm ▄▆▅▃`.

**Playback** uses whatever your OS already has — nothing extra to install:

| Platform | Player |
| -------- | ------ |
| Windows | `winsound` (stdlib, gapless `SND_LOOP`) |
| macOS | `afplay` (built in) |
| Linux | first of `mpv`, `ffplay`, `paplay`, `aplay`, `sox play`, `vlc` |

**Your own music works too** — point it at a file, or a directory to shuffle
through (`.mp3`, `.ogg`, `.flac`, `.m4a`, `.opus`, `.wav`…):

```bash
hollyweeb --music-file ~/Music/cyberpunk/
```

Rendering happens on a worker thread (~1–3 s per track, while the boot animation
plays) and the result is cached under `%TEMP%/hollyweeb-music` (or `$TMPDIR`),
so every run after the first starts instantly; the cache self-prunes past 48 MB,
and `hollyweeb --clear-music-cache` wipes it.

Audio never gets in the way: `--shot`/`--selftest` never start it, `--no-music`
and `HOLLYWEEB_MUSIC=0` silence everything, and every audio failure is non-fatal
— you just get a `♪ !` in the header and the wall of fake work keeps scrolling.

## CLI reference

```
-c, --character NAME    runner to start with (see --list)
-p, --panes N           number of panes (0 = auto)
    --variant NAME      signature|neon|pastel|ice|sunset|acid|vhs|mono
    --header-fx NAME    holo|rainbow|prism|confetti|vapor|glitch|theme (default holo)
-f, --fps N             target frames per second (default 24)
    --color MODE        auto|truecolor|256|16|none
    --seed N            reproducible chaos
    --duration SECS     exit automatically
    --auto              start in auto-cycle mode
    --auto-interval S   seconds between auto switches (default 22)
    --static            never re-roll panes
    --no-glitch         disable glitch effects
    --no-boot           skip the boot animation
    --music             play the runner's soundtrack (default)
    --no-music          run silently
    --music-style NAME  synthwave|chiptune|koto|darkwave|citypop|taiko|lofi|techno|ambient|trance
    --music-volume 0..1 music level (default 0.7)
    --music-bpm N       override the tempo
    --music-bars N      loop length in bars
    --music-file PATH   play your own audio: a file, or a directory to shuffle
    --music-cache-dir D where rendered tracks are cached
    --clear-music-cache delete cached tracks and exit
    --no-alt-screen     draw in the normal buffer (keeps scrollback)
    --list              list runners + widgets, then exit
    --selftest          render every widget/variant headlessly, then exit
    --shot FILE         headless render to FILE (.ansi for raw escapes)
    --frames N          frames to simulate for --shot/--selftest
    --size WxH          virtual terminal size for --shot
    --screen main|select|boot   which screen --shot renders
```

Environment variables: `HOLLYWEEB_MUSIC=0` silences every invocation including
plain `hollyweeb`, `NO_COLOR=1` forces monochrome, and
`HOLLYWEEB_COLOR=truecolor|256|16|none` overrides colour detection.

## Cross-platform notes

| Platform | Notes |
| -------- | ----- |
| **Windows** | Works in Windows Terminal, VS Code, Alacritty, ConEmu, mintty/Git-Bash. `hollyweeb` enables `ENABLE_VIRTUAL_TERMINAL_PROCESSING` and UTF-8 (CP65001) itself; the legacy console host (conhost) gets 256 colours. Keys are read with `msvcrt`, arrows included. |
| **macOS** | Terminal.app, iTerm2, kitty, WezTerm, Ghostty. Truecolor is auto-detected from `COLORTERM`. |
| **Linux** | Any xterm-compatible terminal; also inside `tmux`/`screen` (it nests a full-screen app, so no `hollywood`-style pane multiplexing is required). `SIGWINCH` triggers re-layout. |
| **Anything ancient** | `--color 16`, `TERM=dumb`, or `NO_COLOR=1` all degrade gracefully. |

Audio needs no extra packages: `winsound` on Windows, `afplay` on macOS, and on
Linux whichever of `mpv`/`ffplay`/`paplay`/`aplay`/`sox`/`vlc` is installed. If
none is, the TUI keeps running silently and tells you in the header.

Because hollyweeb paints its own panes, it also works over SSH, in a
`docker run -it`, in GitHub Actions logs (`--color 256`), or piped to a file.

## Headless / CI

```bash
python -m hollyweeb --selftest                       # every widget x variant x size, plus the synth
python -m hollyweeb --list                           # runners, variants, soundtracks, widgets
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

Add a tune in `hollyweeb/music.py` — it's just another `_st(...)` entry in
`STYLES` (tempo, scale, chord progression, which voices play and how loud), and
any runner can point at it with `music="yourkey"`. Widgets that want to move
with the beat can read the shared clock:

```python
from . import pulse

if pulse.active:            # music is playing
    boost = pulse.level     # 1.0 on the kick, decaying
    phase = pulse.beat      # 0..1 within the current beat
    tempo = pulse.bpm
```

## How it works

* `canvas.py` — flat `(char, fg, bg, style)` cell grid + clipped sub-`View`s and
  a row-level diff that emits cursor moves only for changed runs.
* `music.py` — wavetable synth (kick/snare/hat/bass/arp/pad/lead + sidechain,
  filter, saturation, stereo delay), loop-safe rendering with wrapped note tails,
  an on-disk cache and a cross-platform player.
* `pulse.py` — the shared beat clock that lets widgets move with the music.
* `term.py` — raw mode, alt screen, resize detection, non-blocking key decoding
  (termios+select on POSIX, msvcrt on Windows), plus narrow-glyph filtering so
  the grid never desynchronises in terminals that render ambiguous-width
  characters differently.
* `color.py` — RGB maths (HSV shifts for variants) and truecolor/256/16 encoders.
* `widgets.py` — 27 self-contained animations; `layout.py` — pane/card grids;
  `app.py` — boot, select and dashboard screens, keybindings and glitch fx.

## License

MIT. Not affiliated with `hollywood`, Hollywood, or the concept of fame.
