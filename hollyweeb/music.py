"""
Procedural electronic background music — synthesised in pure Python.

No audio libraries, no bundled assets, no ffmpeg required (though it will use it
if you have it): the soundtrack is generated from wavetables with the stdlib
`wave` module and handed to a player the OS already ships:

    Windows   winsound.PlaySound(SND_ASYNC | SND_LOOP)   (gapless, built in)
    macOS     afplay
    Linux     mpv / ffplay / paplay / aplay / sox play / cvlc   (first one found)

Each runner has its own tune (`Character.music`), so switching characters
switches the music. Rendering happens on a worker thread and the result is
cached in the temp directory, so the TUI never blocks and repeat runs are
instant.

Everything here is deterministic: same (style, tempo, seed) -> same samples.
"""

from __future__ import annotations

import array
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import wave
from dataclasses import dataclass, field

IS_WINDOWS = os.name == "nt"
IS_MAC = sys.platform == "darwin"

MUSIC_VERSION = 2          # bump to invalidate the render cache
SR = 22050                 # sample rate (mono synthesis, stereo output)
TSIZE = 1024               # wavetable size
TMASK = TSIZE - 1
NOISE_SIZE = 1 << 16
NOISE_MASK = NOISE_SIZE - 1


# --------------------------------------------------------------------------
# wavetables
# --------------------------------------------------------------------------


def _table(fn) -> array.array:
    return array.array("f", (fn(i / TSIZE) for i in range(TSIZE)))


SINE = _table(lambda x: math.sin(2 * math.pi * x))
SAW = _table(lambda x: 2.0 * x - 1.0)
TRI = _table(lambda x: 4.0 * abs(x - 0.5) - 1.0)
SQUARE = _table(lambda x: 1.0 if x < 0.5 else -1.0)
PULSE = _table(lambda x: 1.0 if x < 0.25 else -1.0)
ORGAN = _table(lambda x: 0.6 * math.sin(2 * math.pi * x) + 0.3 * math.sin(4 * math.pi * x) + 0.1 * math.sin(6 * math.pi * x))

TABLES = {"sine": SINE, "saw": SAW, "tri": TRI, "square": SQUARE, "pulse": PULSE, "organ": ORGAN}

_NOISE = array.array("f", (random.Random(0xC0FFEE).uniform(-1.0, 1.0) for _ in range(NOISE_SIZE)))

SCALES: dict[str, tuple[int, ...]] = {
    "minor": (0, 2, 3, 5, 7, 8, 10),
    "dorian": (0, 2, 3, 5, 7, 9, 10),
    "phrygian": (0, 1, 3, 5, 7, 8, 10),
    "major": (0, 2, 4, 5, 7, 9, 11),
    "lydian": (0, 2, 4, 6, 7, 9, 11),
    "pent_min": (0, 3, 5, 7, 10),
    "pent_maj": (0, 2, 4, 7, 9),
    "hirajoshi": (0, 2, 3, 7, 8),
}


def midi_to_freq(m: float) -> float:
    return 440.0 * (2.0 ** ((m - 69.0) / 12.0))


def degree(scale: tuple[int, ...], d: int) -> int:
    """Scale degree (may be negative or > len) -> semitones from the root."""
    n = len(scale)
    oct_, idx = divmod(d, n)
    return scale[idx] + 12 * oct_


# --------------------------------------------------------------------------
# styles
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Style:
    key: str
    name: str
    bpm: float = 100.0
    bars: int = 4
    root: int = 45                 # MIDI tonic (45 = A2)
    scale: str = "minor"
    prog: tuple[int, ...] = (0, 5, 2, 6)
    chord_ext: int = 0             # add the 7th degree to chords
    swing: float = 0.0             # delay the off-16ths by this fraction
    kick: bool = True
    snare: bool = True
    hat: str = "16"                # off | 8 | 16 | offbeat
    bass: str = "8"                # off | 8 | 16 | rolling
    bass_wave: str = "saw"
    bass_decay: float = 6.0
    arp: str = "up"                # off | up | down | updown
    arp_wave: str = "square"
    arp_oct: int = 1
    arp_rate: str = "16"           # 16 | 8
    arp_decay: float = 11.0
    pad: bool = True
    pad_wave: str = "saw"
    pad_level: float = 0.34
    pad_attack: float = 0.35
    pad_oct: int = 0
    lead: str = "sparse"           # off | sparse | melody
    lead_wave: str = "tri"
    lead_oct: int = 1
    cutoff: float = 0.55           # 0..1 -> 250 Hz .. 14 kHz
    drive: float = 0.25
    sidechain: float = 0.35
    width: float = 0.6


def _st(key: str, name: str, **kw) -> Style:
    return Style(key=key, name=name, **kw)


STYLES: dict[str, Style] = {
    s.key: s
    for s in (
        _st("chiptune", "Chiptune Bounce", bpm=132, scale="major", prog=(0, 4, 5, 3),
            hat="16", bass="8", bass_wave="pulse", arp="updown", arp_wave="pulse", arp_oct=2,
            pad=False, lead="melody", lead_wave="pulse", cutoff=0.85, drive=0.10,
            sidechain=0.15, width=0.30),
        _st("koto", "Koto Circuitry", bpm=84, scale="hirajoshi", prog=(0, 3, 1, 4),
            hat="8", kick=True, snare=True, bass="8", bass_wave="tri", bass_decay=4.0,
            arp="up", arp_wave="tri", arp_oct=1, arp_rate="8", arp_decay=7.0,
            pad=True, pad_wave="sine", pad_level=0.26, pad_attack=0.5,
            lead="sparse", lead_wave="tri", cutoff=0.62, drive=0.12, sidechain=0.22, width=0.45),
        _st("darkwave", "Darkwave Drive", bpm=92, scale="minor", prog=(0, 5, 6, 4),
            hat="8", bass="rolling", bass_wave="saw", bass_decay=7.0,
            arp="off", pad_wave="saw", pad_level=0.40, pad_attack=0.45,
            lead="sparse", lead_wave="saw", cutoff=0.45, drive=0.35, sidechain=0.40, width=0.70),
        _st("synthwave", "Neon Synthwave", bpm=104, scale="minor", prog=(0, 5, 2, 6),
            hat="16", bass="16", bass_wave="saw", arp="updown", arp_wave="saw", arp_oct=2,
            pad_wave="saw", pad_level=0.38, pad_attack=0.5,
            lead="melody", lead_wave="square", cutoff=0.60, drive=0.30, sidechain=0.45, width=0.80),
        _st("citypop", "City Pop Nights", bpm=108, scale="major", prog=(0, 3, 5, 4), chord_ext=1,
            hat="16", bass="8", bass_wave="tri", bass_decay=5.0,
            arp="up", arp_wave="square", arp_oct=2, arp_rate="16",
            pad_wave="organ", pad_level=0.30, pad_attack=0.4,
            lead="melody", lead_wave="organ", cutoff=0.72, drive=0.15, sidechain=0.25, width=0.60),
        _st("taiko", "Taiko Protocol", bpm=96, scale="pent_min", prog=(0, 0, 3, 4),
            hat="8", kick=True, snare=True, bass="8", bass_wave="tri", bass_decay=4.5,
            arp="up", arp_wave="tri", arp_oct=2, arp_rate="16", arp_decay=9.0,
            pad=False, lead="sparse", lead_wave="tri", cutoff=0.60, drive=0.22,
            sidechain=0.30, width=0.50),
        _st("lofi", "Lo-Fi Ramen", bpm=78, scale="dorian", prog=(0, 3, 5, 4), chord_ext=1,
            swing=0.25, hat="16", bass="8", bass_wave="tri", bass_decay=4.0,
            arp="off", pad_wave="organ", pad_level=0.34, pad_attack=0.6,
            lead="sparse", lead_wave="tri", cutoff=0.34, drive=0.16, sidechain=0.20, width=0.50),
        _st("techno", "Minimal Techno", bpm=128, scale="phrygian", prog=(0, 0, 5, 6),
            hat="offbeat", bass="rolling", bass_wave="saw", bass_decay=9.0,
            arp="off", pad=False, lead="off", cutoff=0.50, drive=0.42,
            sidechain=0.50, width=0.30),
        _st("ambient", "Halo Ambient", bpm=68, scale="lydian", prog=(0, 4, 2, 5), chord_ext=1,
            hat="off", kick=False, snare=False, bass="off",
            arp="off", pad_wave="saw", pad_level=0.50, pad_attack=1.2, pad_oct=1,
            lead="sparse", lead_wave="sine", cutoff=0.40, drive=0.08, sidechain=0.0, width=0.90),
        _st("trance", "Bamboo Trance", bpm=138, scale="minor", prog=(0, 5, 2, 6),
            hat="offbeat", bass="rolling", bass_wave="saw", bass_decay=9.0,
            arp="updown", arp_wave="saw", arp_oct=2, arp_decay=12.0,
            pad_wave="saw", pad_level=0.36, pad_attack=0.4,
            lead="melody", lead_wave="square", cutoff=0.64, drive=0.30, sidechain=0.50, width=0.85),
    )
}

STYLE_KEYS = list(STYLES)


def style_names() -> list[tuple[str, str, float]]:
    return [(s.key, s.name, s.bpm) for s in STYLES.values()]


# --------------------------------------------------------------------------
# voice synthesis (all mono float buffers)
# --------------------------------------------------------------------------


def _osc(buf: array.array, start: int, n: int, inc: float, table: array.array,
         amp: float, decay: float, sr: int) -> None:
    """Decaying oscillator note."""
    if n <= 0 or amp <= 0.0:
        return
    end = start + n
    if end > len(buf):
        end = len(buf)
    if start >= end:
        return
    dm = math.exp(-decay / sr)
    e = amp
    ph = 0.0
    i = start
    mask = TMASK
    while i < end:
        buf[i] += table[int(ph) & mask] * e
        ph += inc
        e *= dm
        i += 1


def _pad_note(start: int, n: int, inc: float, table: array.array, amp: float,
              sr: int, attack: float, release: float, detune: float = 0.005) -> array.array:
    """Sustained detuned note rendered into its own buffer (can wrap the loop)."""
    out = array.array("f", [0.0]) * max(1, n)
    if n <= 0 or amp <= 0.0:
        return out
    a_n = max(1, min(n // 2, int(attack * sr)))
    r_n = max(1, min(n // 2, int(release * sr)))
    a_step = 1.0 / a_n
    r_step = 1.0 / r_n
    det = (1.0, 1.0 + detune, 1.0 - detune * 0.8)
    i0, i1, i2 = (inc * d for d in det)
    p0 = p1 = p2 = 0.0
    amp3 = amp / 3.0
    mask = TMASK
    sustain_end = n - r_n
    for i in range(n):
        s = table[int(p0) & mask] + table[int(p1) & mask] + table[int(p2) & mask]
        p0 += i0
        p1 += i1
        p2 += i2
        if i < a_n:
            g = i * a_step
        elif i >= sustain_end:
            g = (n - i) * r_step
        else:
            g = 1.0
        out[i] = s * amp3 * g
    return out


def _add_wrapped(dst: array.array, src: array.array, start: int, loop_len: int) -> None:
    """Mix `src` into `dst` at `start`, wrapping around `loop_len` (seamless loop)."""
    n = len(src)
    i = start % loop_len
    k = 0
    while k < n:
        take = min(n - k, loop_len - i)
        for j in range(take):
            dst[i + j] += src[k + j]
        k += take
        i = 0


def _kick(buf: array.array, start: int, amp: float, sr: int,
          f0: float = 165.0, f1: float = 48.0, sweep: float = 34.0, decay: float = 7.5) -> None:
    n = int(0.34 * sr)
    end = min(len(buf), start + n)
    if start >= end:
        return
    inc = f0 * TSIZE / sr
    target = f1 * TSIZE / sr
    fm = math.exp(-sweep / sr)
    dm = math.exp(-decay / sr)
    e = amp
    ph = 0.0
    mask = TMASK
    for i in range(start, end):
        buf[i] += SINE[int(ph) & mask] * e
        ph += inc
        inc = target + (inc - target) * fm
        e *= dm


def _snare(buf: array.array, start: int, amp: float, sr: int, decay: float = 26.0) -> None:
    n = int(0.22 * sr)
    end = min(len(buf), start + n)
    if start >= end:
        return
    dm = math.exp(-decay / sr)
    e = amp
    phase = 0.0
    inc = 190.0 * TSIZE / sr
    idx = 0.0
    prev = 0.0
    mask = TMASK
    for i in range(start, end):
        s = _NOISE[int(idx) & NOISE_MASK]
        hp = (s - prev) * 0.5
        prev = s
        body = SINE[int(phase) & mask] * 0.30
        phase += inc
        buf[i] += (hp * 0.85 + body) * e
        e *= dm
        idx += 1.0


def _hat(buf: array.array, start: int, amp: float, sr: int, decay: float = 90.0) -> None:
    n = int(min(0.18, 6.0 / decay) * sr) + 8
    end = min(len(buf), start + n)
    if start >= end:
        return
    dm = math.exp(-decay / sr)
    e = amp
    idx = 0.0
    prev = 0.0
    for i in range(start, end):
        s = _NOISE[int(idx) & NOISE_MASK]
        hp = s - prev
        prev = s
        buf[i] += hp * e
        e *= dm
        idx += 1.0


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def _arp_seq(midis: list[int], kind: str, octaves: int) -> list[int]:
    base: list[int] = []
    for o in range(max(1, octaves)):
        base += [m + 12 * o for m in midis]
    if kind == "down":
        return list(reversed(base))
    if kind == "updown":
        return base + list(reversed(base))[1:-1]
    return base


def render_pcm(style: Style, sr: int = SR, seed: int = 0, volume: float = 1.0) -> array.array:
    """Synthesise `style` into interleaved stereo signed 16-bit samples."""
    scale = SCALES[style.scale]
    rng = random.Random((seed * 2654435761) ^ 0x5EED)
    beat = 60.0 / float(style.bpm)
    step = beat / 4.0
    n_bar = int(round(beat * 4.0 * sr))
    total = n_bar * style.bars
    # Render into a slightly padded buffer so notes near the loop point are not
    # truncated; the overflow is then folded back into the head of the loop,
    # which is what makes the loop click-free.
    pad = int(0.75 * sr)
    mono = array.array("f", [0.0]) * (total + pad)

    def at(s: int, b: int) -> int:
        swing = style.swing * step * sr * 0.5 if s % 2 else 0.0
        return b * n_bar + int(round(s * step * sr + swing))

    for b in range(style.bars):
        t0 = b * n_bar
        deg = style.prog[b % len(style.prog)]
        chord = [deg, deg + 2, deg + 4]
        if style.chord_ext:
            chord.append(deg + 6)
        midis = [style.root + degree(scale, d) for d in chord]

        # ---------------------------------------------------------- drums
        last = b == style.bars - 1
        for s in range(16):
            pos = at(s, b)
            if style.kick and (s in (0, 4, 8, 12) or (last and s == 14)):
                _kick(mono, pos, 0.90 if s in (0, 8) else 0.72, sr,
                      f1=52.0 if s in (0, 8) else 46.0)
            if style.snare and s in (4, 12):
                _snare(mono, pos, 0.42, sr)
            if s == 15 and last:
                _snare(mono, pos, 0.30, sr, decay=34.0)
            if style.hat == "16":
                _hat(mono, pos, 0.085 if s % 4 == 0 else 0.05, sr, decay=110.0 if s % 4 else 80.0)
            elif style.hat == "8" and s % 2 == 0:
                _hat(mono, pos, 0.07 if s % 4 == 0 else 0.045, sr, decay=95.0)
            elif style.hat == "offbeat" and s % 4 == 2:
                _hat(mono, pos, 0.075, sr, decay=26.0)

        # ----------------------------------------------------------- bass
        if style.bass != "off":
            wave = TABLES[style.bass_wave]
            step_every = 1 if style.bass in ("16", "rolling") else 2
            for s in range(0, 16, step_every):
                if style.bass == "8":
                    m, dur, amp = (midis[0] if s % 8 != 4 else midis[2]), step * 1.7, 0.32
                elif style.bass == "16":
                    m, dur, amp = midis[0] + (12 if s % 2 else 0), step * 0.95, 0.30
                else:  # rolling
                    m = midis[(s // 2) % 3] + (12 if s % 4 == 3 else 0)
                    dur, amp = step * 0.9, 0.28
                _osc(mono, at(s, b), int(dur * sr), midi_to_freq(m - 12) * TSIZE / sr,
                     wave, amp, style.bass_decay, sr)

        # ------------------------------------------------------------ arp
        if style.arp != "off":
            seq = _arp_seq(midis, style.arp, style.arp_oct)
            wave = TABLES[style.arp_wave]
            every = 1 if style.arp_rate == "16" else 2
            k = 0
            for s in range(0, 16, every):
                m = seq[k % len(seq)]
                k += 1
                _osc(mono, at(s, b), int(step * sr * 1.5), midi_to_freq(m + 12) * TSIZE / sr,
                     wave, 0.15, style.arp_decay, sr)

        # ------------------------------------------------------------ pad
        if style.pad:
            wave = TABLES[style.pad_wave]
            amp = style.pad_level / max(1, len(midis))
            for m in midis:
                note = _pad_note(0, n_bar, midi_to_freq(m + 12 * style.pad_oct) * TSIZE / sr,
                                 wave, amp, sr, style.pad_attack, 0.35)
                _add_wrapped(mono, note, t0, total)

        # ----------------------------------------------------------- lead
        if style.lead == "melody":
            wave = TABLES[style.lead_wave]
            cur = len(scale)                     # start around the octave
            top = len(scale) * 2
            for s in range(0, 16, 2):
                cur = max(0, min(top, cur + rng.choice((-2, -1, -1, 0, 1, 1, 2))))
                m = style.root + degree(scale, cur) + 12 * style.lead_oct
                _osc(mono, at(s, b), int(step * sr * 1.9), midi_to_freq(m) * TSIZE / sr,
                     wave, 0.17, 5.0, sr)
        elif style.lead == "sparse":
            wave = TABLES[style.lead_wave]
            for _ in range(2):
                if rng.random() < 0.7:
                    s = rng.randrange(0, 14)
                    d = rng.choice(chord)
                    m = style.root + degree(scale, d) + 12 * style.lead_oct
                    _osc(mono, at(s, b), int(step * sr * 3.2), midi_to_freq(m) * TSIZE / sr,
                         wave, 0.15, 3.2, sr)

    # ------------------------------------------------ wrap + fold the tail
    for i in range(pad):
        mono[i] += mono[total + i]
    del mono[total:]

    # ------------------------------------------------------------ effects
    # sidechain: duck the whole mix on every kick (that classic pumping)
    if style.sidechain > 0.0 and style.kick:
        beat_n = max(1, int(round(beat * sr)))
        duck = array.array("f", [0.0]) * beat_n
        g = 1.0 - style.sidechain
        recover = 1.0 - math.exp(-1.0 / (0.14 * sr))
        for i in range(beat_n):
            duck[i] = g
            g += (1.0 - g) * recover
        for start in range(0, total, beat_n):
            n = min(beat_n, total - start)
            for k in range(n):
                mono[start + k] *= duck[k]

    # gently low-pass the mix so bleeps never get painful
    fc = 250.0 * (14000.0 / 250.0) ** max(0.0, min(1.0, style.cutoff))
    a = 1.0 - math.exp(-2.0 * math.pi * fc / sr)
    lp = 0.0
    for i in range(total):
        lp += a * (mono[i] - lp)
        mono[i] = lp

    # saturation
    if style.drive > 0.0:
        d = 1.0 + style.drive * 6.0
        for i in range(total):
            x = mono[i] * d
            mono[i] = x / (1.0 + abs(x))

    peak = 0.0
    for x in mono:
        ax = x if x >= 0.0 else -x
        if ax > peak:
            peak = ax
    norm = (0.88 / peak) if peak > 1e-6 else 0.0

    # stereo: L = mono, R = mono blended with a ~12 ms delayed copy
    delay = int(sr * 0.012 * max(0.0, min(1.0, style.width)))
    w = max(0.0, min(1.0, style.width)) * 0.5
    out = array.array("h", bytes(4 * total))
    for i in range(total):
        s = mono[i] * norm * volume
        if delay:
            j = i - delay
            if j < 0:
                j += total
            r = s * (1.0 - w) + mono[j] * norm * volume * w
        else:
            r = s
        li = int(s * 32767.0)
        ri = int(r * 32767.0)
        out[2 * i] = 32767 if li > 32767 else (-32768 if li < -32768 else li)
        out[2 * i + 1] = 32767 if ri > 32767 else (-32768 if ri < -32768 else ri)
    return out


def write_wav(path: str, pcm: array.array, sr: int = SR) -> None:
    """Write interleaved stereo 16-bit samples to `path` (atomically)."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    tmp = path + ".part"
    with wave.open(tmp, "wb") as fh:
        fh.setnchannels(2)
        fh.setsampwidth(2)
        fh.setframerate(sr)
        fh.writeframes(pcm.tobytes())
    os.replace(tmp, path)


def render_to_wav(style: Style, path: str, sr: int = SR, seed: int = 0, volume: float = 1.0) -> None:
    write_wav(path, render_pcm(style, sr=sr, seed=seed, volume=volume), sr)


def loop_seconds(style: Style, bars: int | None = None) -> float:
    return (bars or style.bars) * 4.0 * 60.0 / style.bpm


# --------------------------------------------------------------------------
# playback
# --------------------------------------------------------------------------

AUDIO_EXT = (".wav", ".mp3", ".ogg", ".flac", ".m4a", ".opus", ".aac", ".wma")


def find_backend() -> str | None:
    """First usable OS-native player, or None."""
    if IS_WINDOWS:
        try:
            import winsound  # noqa: F401
            return "winsound"
        except Exception:
            pass
    if IS_MAC and shutil.which("afplay"):
        return "afplay"
    for name in ("mpv", "ffplay", "paplay", "aplay", "play", "cvlc"):
        if shutil.which(name):
            return name
    return None


def _build_command(backend: str, path: str, volume: float, loop: bool) -> list[str]:
    vol = max(0.0, min(1.0, volume))
    if backend == "mpv":
        cmd = ["mpv", "--no-video", "--really-quiet", "--audio-display=no", f"--volume={int(vol * 130)}"]
        if loop:
            cmd.append("--loop-file=inf")
        return cmd + [path]
    if backend == "ffplay":
        cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", "-volume", str(int(vol * 100))]
        if loop:
            cmd += ["-loop", "0"]
        return cmd + [path]
    if backend == "afplay":
        return ["afplay", "-v", f"{vol:.2f}", path]
    if backend == "paplay":
        return ["paplay", path]
    if backend == "aplay":
        return ["aplay", "-q", path]
    if backend == "play":
        return ["play", "-q", path]
    if backend == "cvlc":
        cmd = ["cvlc", "--intf", "dummy", "--play-and-exit", "--quiet"]
        if loop:
            cmd.append("--loop")
        return cmd + [path]
    return [path]


_GAPLESS = {"winsound", "mpv", "cvlc"}


class MusicPlayer:
    """Non-blocking soundtrack: renders on a worker thread, plays via the OS.

    States: ``off`` -> ``synth`` -> ``playing`` (or ``error``/``nobackend``).
    """

    def __init__(self, enabled: bool = False, style: str = "synthwave", volume: float = 0.7,
                 sr: int = SR, seed: int = 0, path: str | None = None,
                 bpm: float | None = None, bars: int | None = None,
                 cache_dir: str | None = None, dry_run: bool = False):
        self.enabled = bool(enabled)
        self.sr = sr
        self.seed = seed
        self.volume = max(0.0, min(1.0, volume))
        self.user_path = path
        self.dry_run = dry_run
        self.bpm_override = bpm
        self.bars_override = bars
        self.cache_dir = cache_dir or os.path.join(tempfile.gettempdir(), "hollyweeb-music")

        self._style_key = style if style in STYLES else STYLE_KEYS[0]
        self._state = "off"
        self._detail = ""
        self._file: str | None = None
        self._proc: subprocess.Popen | None = None
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._lock = threading.RLock()
        self._started_at = 0.0
        self._loop_len = 0.0
        self._volume_dirty = 0.0
        self._backend = find_backend() if not dry_run else "dry"

    # -- state -------------------------------------------------------------
    @property
    def style_key(self) -> str:
        return self._style_key

    @property
    def style(self) -> Style:
        s = STYLES[self._style_key]
        if self.bpm_override or self.bars_override:
            s = Style(**{**s.__dict__,
                         "bpm": self.bpm_override or s.bpm,
                         "bars": self.bars_override or s.bars})
        return s

    @property
    def state(self) -> str:
        return self._state

    @property
    def detail(self) -> str:
        return self._detail

    @property
    def backend(self) -> str | None:
        return self._backend

    @property
    def playing(self) -> bool:
        return self._state == "playing"

    def phase(self) -> tuple[float, float]:
        """(beat phase 0..1, bar phase 0..1) of the current loop."""
        if self._state != "playing" or self._loop_len <= 0:
            return (0.0, 0.0)
        t = time.monotonic() - self._started_at
        beat = 60.0 / self.style.bpm
        b = (t % beat) / beat
        bar = (t % (beat * 4.0)) / (beat * 4.0)
        return (b, bar)

    # -- control -----------------------------------------------------------
    def toggle(self) -> bool:
        if self.enabled:
            self.disable()
        else:
            self.enable()
        return self.enabled

    def enable(self) -> None:
        self.enabled = True
        self._restart()

    def disable(self) -> None:
        self.enabled = False
        self._teardown()
        self._state = "off"
        self._detail = ""

    def set_style(self, key: str, force: bool = False) -> None:
        if key not in STYLES or (key == self._style_key and not force):
            return
        self._style_key = key
        if self.enabled:
            self._restart()

    def set_volume(self, volume: float) -> float:
        """Set the level; the re-render happens once the level settles (see tick())."""
        self.volume = max(0.0, min(1.0, volume))
        if self.enabled:
            self._volume_dirty = time.monotonic()
        return self.volume

    def tick(self) -> None:
        """Called from the app loop: applies a debounced volume change."""
        if self._volume_dirty and time.monotonic() - self._volume_dirty > 0.6:
            self._volume_dirty = 0.0
            if self.enabled:
                self._restart()

    # -- internals ---------------------------------------------------------
    def _teardown(self) -> None:
        self._stop.set()
        proc = self._proc
        self._proc = None
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        if self._backend == "winsound":
            try:
                import winsound

                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        thread = self._thread
        self._thread = None
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2.0)
        self._proc = None

    def _restart(self) -> None:
        self._teardown()
        self._stop = threading.Event()
        self._state = "synth"
        self._detail = self.style.name
        self._thread = threading.Thread(target=self._worker, name="hollyweeb-music", daemon=True)
        self._thread.start()

    def _cache_path(self) -> str:
        style = self.style
        name = (f"hollyweeb-v{MUSIC_VERSION}-{style.key}-{style.bpm:g}bpm-{style.bars}bar-"
                f"{self.sr}-{self.seed}-{int(self.volume * 100)}.wav")
        return os.path.join(self.cache_dir, name)

    def _pick_user_file(self) -> str | None:
        path = self.user_path
        if not path:
            return None
        if os.path.isdir(path):
            try:
                files = sorted(
                    os.path.join(path, f) for f in os.listdir(path)
                    if f.lower().endswith(AUDIO_EXT)
                )
            except OSError:
                files = []
            if not files:
                return None
            return random.choice(files)
        return path if os.path.exists(path) else None

    def _worker(self) -> None:
        """Render (or fetch from cache) then play, restarting for gapless loops."""
        try:
            if self._backend is None:
                self._state = "error"
                self._detail = "no audio player found"
                return
            if self.dry_run:
                # test/stub mode: report playing without rendering or playing
                self._state = "playing"
                self._detail = "dry-run"
                self._loop_len = loop_seconds(self.style)
                self._started_at = time.monotonic()
                self._stop.wait(3600)
                return
            first = True
            while not self._stop.is_set():
                if self.user_path:
                    track = self._pick_user_file()
                    if track is None:
                        self._state = "error"
                        self._detail = "music file not found"
                        return
                    loop = True
                else:
                    track = self._cache_path()
                    if not os.path.exists(track):
                        self._state = "synth"
                        self._detail = self.style.name
                        os.makedirs(self.cache_dir, exist_ok=True)
                        prune_cache(cache_dir=self.cache_dir)
                        render_to_wav(self.style, track, sr=self.sr, seed=self.seed, volume=self.volume)
                        if self._stop.is_set():
                            return
                    loop = True
                if self._stop.is_set():
                    return
                self._loop_len = loop_seconds(self.style)
                self._play(track, loop)
                first = False
                if self._stop.is_set():
                    return
                if self._backend in _GAPLESS:
                    # native looping: just idle until told to stop
                    self._stop.wait(3600)
                    return
                # otherwise wait for the track to finish, then play it again
                while not self._stop.is_set():
                    proc = self._proc
                    if proc is not None and proc.poll() is not None:
                        break
                    if self._stop.wait(0.2):
                        return
        except Exception as exc:  # never take the TUI down for audio
            self._state = "error"
            self._detail = f"{type(exc).__name__}: {exc}"

    def _play(self, path: str, loop: bool) -> None:
        self._proc = None
        if self.dry_run:
            self._state = "playing"
            self._detail = os.path.basename(path)
            self._started_at = time.monotonic()
            return
        if self._backend == "winsound":
            import winsound

            flags = winsound.SND_FILENAME | winsound.SND_ASYNC
            if loop:
                flags |= winsound.SND_LOOP
            winsound.PlaySound(path, flags)
        else:
            cmd = _build_command(self._backend, path, self.volume, loop)
            kwargs: dict = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if IS_WINDOWS:
                kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
            self._proc = subprocess.Popen(cmd, **kwargs)
        self._started_at = time.monotonic()
        self._state = "playing"
        self._detail = os.path.basename(path)

    def stop(self) -> None:
        self._teardown()
        if self.enabled:
            self._state = "off"

    # -- info --------------------------------------------------------------
    def status_text(self) -> str:
        if not self.enabled:
            return "music off"
        if self._state == "synth":
            return f"♪ synthesising {self.style.name}…"
        if self._state == "playing":
            return f"♪ {self.style.name} · {int(self.style.bpm)} bpm"
        if self._state == "error":
            return f"♪ {self._detail}" if self._detail else "♪ error"
        return "♪ off"


def cache_size(cache_dir: str | None = None) -> int:
    """Bytes used by the render cache."""
    d = cache_dir or os.path.join(tempfile.gettempdir(), "hollyweeb-music")
    total = 0
    try:
        for f in os.listdir(d):
            total += os.path.getsize(os.path.join(d, f))
    except OSError:
        pass
    return total


def prune_cache(limit_bytes: int = 48 * 1024 * 1024, cache_dir: str | None = None) -> int:
    """Drop the oldest cached tracks once the cache grows past `limit_bytes`."""
    d = cache_dir or os.path.join(tempfile.gettempdir(), "hollyweeb-music")
    try:
        files = [(os.path.getmtime(os.path.join(d, f)), os.path.getsize(os.path.join(d, f)),
                  os.path.join(d, f))
                 for f in os.listdir(d) if f.endswith(".wav")]
    except OSError:
        return 0
    total = sum(size for _, size, _ in files)
    if total <= limit_bytes:
        return 0
    removed = 0
    for _mtime, size, path in sorted(files):
        try:
            os.remove(path)
            removed += 1
            total -= size
        except OSError:
            pass
        if total <= limit_bytes * 0.6:
            break
    return removed


def clear_cache(cache_dir: str | None = None) -> int:
    d = cache_dir or os.path.join(tempfile.gettempdir(), "hollyweeb-music")
    n = 0
    try:
        for f in os.listdir(d):
            if f.endswith((".wav", ".part")):
                os.remove(os.path.join(d, f))
                n += 1
    except OSError:
        pass
    return n
