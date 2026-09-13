"""
Terminal plumbing: raw mode, alternate screen, resize detection, and a
cross-platform non-blocking key reader.

POSIX  -> termios + select
Windows-> msvcrt + ctypes (Virtual Terminal Processing, UTF-8 code page)
"""

from __future__ import annotations

import os
import shutil
import sys
import unicodedata

IS_WINDOWS = os.name == "nt"

# --------------------------------------------------------------------------
# ANSI constants
# --------------------------------------------------------------------------

ESC = "\x1b"
CSI = ESC + "["
ALT_SCREEN_ON = CSI + "?1049h"
ALT_SCREEN_OFF = CSI + "?1049l"
CURSOR_HIDE = CSI + "?25l"
CURSOR_SHOW = CSI + "?25h"
CLEAR = CSI + "2J"
HOME = CSI + "H"
RESET = CSI + "0m"
WRAP_OFF = CSI + "?7l"
WRAP_ON = CSI + "?7h"
MOUSE_OFF = CSI + "?1000l"
BRACKET_PASTE_OFF = CSI + "?2004l"


# --------------------------------------------------------------------------
# windows niceties
# --------------------------------------------------------------------------


def enable_windows_vt() -> bool:
    """Turn on ANSI escape support + UTF-8 for the current Windows console."""
    if not IS_WINDOWS:
        return True
    try:
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.windll.kernel32
        ok = False
        for handle_id in (-11, -12):  # STD_OUTPUT_HANDLE, STD_ERROR_HANDLE
            h = k32.GetStdHandle(handle_id)
            if h in (0, -1, None):
                continue
            mode = wintypes.DWORD()
            if not k32.GetConsoleMode(h, ctypes.byref(mode)):
                continue
            # ENABLE_VIRTUAL_TERMINAL_PROCESSING | DISABLE_NEWLINE_AUTO_RETURN
            k32.SetConsoleMode(h, mode.value | 0x0004 | 0x0008)
            ok = True
        k32.SetConsoleOutputCP(65001)
        k32.SetConsoleCP(65001)
        return ok
    except Exception:
        return False


def _reconfigure_utf8() -> None:
    for stream in (sys.stdout, sys.stderr, sys.stdin):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def prepare_console() -> None:
    """Idempotent console prep: UTF-8 streams + Windows VT."""
    _reconfigure_utf8()
    if IS_WINDOWS:
        enable_windows_vt()


# --------------------------------------------------------------------------
# size
# --------------------------------------------------------------------------


def term_size(fallback: tuple[int, int] = (110, 32)) -> tuple[int, int]:
    """(columns, rows) with a sane fallback when there is no controlling tty."""
    for src in (
        lambda: os.get_terminal_size(),
        lambda: shutil.get_terminal_size(fallback),
    ):
        try:
            s = src()
            if s.columns > 0 and s.lines > 0:
                return (int(s.columns), int(s.lines))
        except Exception:
            continue
    return fallback


def setup_signals(callback) -> None:
    """Call ``callback`` on terminal resize (POSIX only; Windows is polled)."""
    if IS_WINDOWS:
        return
    try:
        import signal

        signal.signal(signal.SIGWINCH, lambda *_: callback())
    except Exception:
        pass


# --------------------------------------------------------------------------
# writing
# --------------------------------------------------------------------------


class Terminal:
    """Owns raw mode / alt screen so the app never leaves a broken tty behind."""

    def __init__(self, stream=None, stdin=None, use_alt_screen: bool = True):
        self.out = stream or sys.stdout
        self.inp = stdin or sys.stdin
        self.use_alt_screen = use_alt_screen
        self._raw = False
        self._saved = None
        self._fd = None
        self._win_in_mode = None

    # -- lifecycle ---------------------------------------------------------
    def start(self) -> None:
        prepare_console()
        if self.use_alt_screen:
            self.write(ALT_SCREEN_ON)
        self.write(WRAP_OFF + MOUSE_OFF + BRACKET_PASTE_OFF + CURSOR_HIDE + CLEAR + HOME)
        self.flush()
        self._enter_raw()

    def stop(self) -> None:
        self._leave_raw()
        self.write(RESET + WRAP_ON + CURSOR_SHOW)
        if self.use_alt_screen:
            self.write(ALT_SCREEN_OFF)
        self.flush()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *exc):
        self.stop()
        return False

    # -- output ------------------------------------------------------------
    def write(self, s: str) -> None:
        try:
            self.out.write(s)
        except (ValueError, OSError):  # closed pipe
            pass

    def flush(self) -> None:
        try:
            self.out.flush()
        except (ValueError, OSError):
            pass

    # -- raw mode ----------------------------------------------------------
    def _enter_raw(self) -> None:
        if self._raw:
            return
        try:
            self._fd = self.inp.fileno()
        except Exception:
            self._fd = None  # not a real tty (piped input) -> no keys, fine
        if IS_WINDOWS:
            self._enter_raw_windows()
        elif self._fd is not None:
            try:
                import termios
                import tty

                self._saved = termios.tcgetattr(self._fd)
                new = termios.tcgetattr(self._fd)
                new[3] &= ~(termios.ECHO | termios.ICANON | termios.ISIG)
                new[6][termios.VMIN] = 0
                new[6][termios.VTIME] = 0
                termios.tcsetattr(self._fd, termios.TCSADRAIN, new)
                # keep OPOST so "\n" still behaves; we use explicit cursor moves
                del tty
            except Exception:
                self._saved = None
        self._raw = True

    def _enter_raw_windows(self) -> None:
        """Turn off line buffering, echo and Ctrl-C processing for the console."""
        try:
            import ctypes
            from ctypes import wintypes

            k32 = ctypes.windll.kernel32
            handle = k32.GetStdHandle(-10)  # STD_INPUT_HANDLE
            if handle in (0, -1, None):
                return
            mode = wintypes.DWORD()
            if not k32.GetConsoleMode(handle, ctypes.byref(mode)):
                return  # stdin is a pipe, not a console: nothing to do
            self._win_in_mode = mode.value
            ENABLE_PROCESSED_INPUT, ENABLE_LINE_INPUT, ENABLE_ECHO_INPUT = 0x0001, 0x0002, 0x0004
            k32.SetConsoleMode(handle, mode.value & ~(ENABLE_PROCESSED_INPUT | ENABLE_LINE_INPUT | ENABLE_ECHO_INPUT))
        except Exception:
            self._win_in_mode = None

    def _leave_raw_windows(self) -> None:
        if self._win_in_mode is None:
            return
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleMode(ctypes.windll.kernel32.GetStdHandle(-10), self._win_in_mode)
        except Exception:
            pass
        self._win_in_mode = None

    def _leave_raw(self) -> None:
        if not self._raw:
            return
        if IS_WINDOWS:
            self._leave_raw_windows()
        elif self._fd is not None and self._saved is not None:
            try:
                import termios

                termios.tcsetattr(self._fd, termios.TCSADRAIN, self._saved)
            except Exception:
                pass
        self._raw = False

    # -- input -------------------------------------------------------------
    def read_keys(self) -> list[str]:
        """Non-blocking. Returns a list of logical key names."""
        if IS_WINDOWS:
            return self._read_keys_windows()
        return self._read_keys_posix()

    def _read_keys_posix(self) -> list[str]:
        if self._fd is None:
            return []
        out: list[str] = []
        try:
            import select

            while True:
                r, _, _ = select.select([self._fd], [], [], 0)
                if not r:
                    break
                data = os.read(self._fd, 64)
                if not data:
                    break
                out.extend(decode_keys(data.decode("utf-8", "replace")))
        except Exception:
            return out
        return out

    def _read_keys_windows(self) -> list[str]:
        out: list[str] = []
        try:
            import msvcrt
        except Exception:
            return out
        try:
            while msvcrt.kbhit():
                ch = msvcrt.getwch()
                if ch in ("\x00", "\xe0"):  # special key prefix
                    code = msvcrt.getwch()
                    out.append({"H": "up", "P": "down", "K": "left", "M": "right"}.get(code, "unknown"))
                else:
                    out.extend(decode_keys(ch))
        except Exception:
            return out
        return out


# --------------------------------------------------------------------------
# key decoding
# --------------------------------------------------------------------------

_CSI_KEYS = {
    "A": "up", "B": "down", "C": "right", "D": "left",
    "H": "home", "F": "end", "Z": "shift-tab",
    "1~": "home", "2~": "insert", "3~": "delete",
    "4~": "end", "5~": "pageup", "6~": "pagedown",
}

_CTRL = {
    "\x03": "ctrl-c", "\x04": "ctrl-d", "\x1a": "ctrl-z",
    "\x0c": "ctrl-l", "\x17": "ctrl-w", "\x0e": "ctrl-n", "\x10": "ctrl-p",
}

_SPECIAL = {
    "\r": "enter", "\n": "enter", "\t": "tab",
    "\x7f": "backspace", "\x08": "backspace", "\x1b": "esc", " ": "space",
}


def decode_keys(buf: str) -> list[str]:
    """Decode a raw byte-chunk into logical key names (handles ANSI arrows)."""
    keys: list[str] = []
    i = 0
    n = len(buf)
    while i < n:
        ch = buf[i]
        if ch == "\x1b":
            # try CSI / SS3 sequence
            if i + 1 < n and buf[i + 1] in "[O":
                j = i + 2
                param = ""
                while j < n and (buf[j].isdigit() or buf[j] in ";?"):
                    param += buf[j]
                    j += 1
                if j < n:
                    final = buf[j]
                    token = param + final
                    key = _CSI_KEYS.get(token) or _CSI_KEYS.get(final)
                    keys.append(key or "unknown")
                    i = j + 1
                    continue
                keys.append("esc")
                i += 1
                continue
            keys.append("esc")
            i += 1
            continue
        mapped = _SPECIAL.get(ch) or _CTRL.get(ch)
        if mapped:
            keys.append(mapped)
        elif ch.isprintable():
            keys.append(ch)
        i += 1
    return keys


# --------------------------------------------------------------------------
# unicode safety
# --------------------------------------------------------------------------


def char_width(ch: str) -> int:
    if not ch:
        return 0
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def narrow_only(chars: str) -> str:
    """Filter a charset down to single-column glyphs (keeps our grid aligned)."""
    return "".join(c for c in chars if char_width(c) == 1)


def strip_wide(text: str) -> str:
    return "".join(c for c in text if char_width(c) <= 1)
