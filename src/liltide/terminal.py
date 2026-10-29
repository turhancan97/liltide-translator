"""Terminal-only controls and captions; core session code does not import Rich."""

import os
import sys

from rich.live import Live
from rich.text import Text


class PauseControl:
    def __enter__(self):
        self.fd = None
        self.previous = None
        if sys.stdin.isatty() and os.name != "nt":
            import termios
            import tty
            self.fd = sys.stdin.fileno()
            self.previous = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)  # Keep Ctrl+C signal behavior.
        return self

    def __call__(self):
        if not sys.stdin.isatty():
            return None
        if os.name == "nt":
            import msvcrt
            if msvcrt.kbhit() and msvcrt.getwch().lower() == "p":
                return "pause"
        elif self.fd is not None:
            import select
            if select.select([self.fd], [], [], 0)[0] and os.read(self.fd, 1).lower() == b"p":
                return "pause"
        return None

    def __exit__(self, *args):
        if self.previous is not None:
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.previous)


def timestamp(ms):
    hours, remainder = divmod(max(0, ms), 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}.{millis:03}"


class CaptionRenderer:
    def __init__(self, console, view):
        self.console = console
        self.view = view
        self.live = None

    def __enter__(self):
        if self.console.is_terminal:
            self.live = Live(Text(""), console=self.console, refresh_per_second=10)
            self.live.start()
        return self

    def caption(self, event):
        label = "final" if event.final else "provisional"
        text = f"[{timestamp(event.start_ms)}] [{label}]\n"
        if self.view == "bilingual":
            text += f"PL: {event.polish}\n"
        text += f"EN: {event.english if event.english is not None else '[translation unavailable]'}"
        if event.final:
            if self.live:
                self.live.update(Text(""))
            self.console.print(Text(text))
        elif self.live:
            self.live.update(Text(text))

    def status(self, message):
        if self.live:
            self.live.update(Text(""))
        self.console.print(Text(message))

    def __exit__(self, *args):
        if self.live:
            self.live.update(Text(""))
            self.live.stop()
