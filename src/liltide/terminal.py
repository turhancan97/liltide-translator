"""Terminal-only controls and captions; core session code does not import Rich."""

import os
import sys

from rich.live import Live
from rich.text import Text
from liltide.formatting import timestamp
from liltide.text_safety import safe_text


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


class CaptionRenderer:
    def __init__(self, console, view, show_timing=False):
        self.console = console
        self.view = view
        self.live = None
        self.show_timing = show_timing

    def __enter__(self):
        if self.console.is_terminal:
            self.live = Live(Text(""), console=self.console, refresh_per_second=10)
            self.live.start()
        return self

    def caption(self, event):
        label = "final" if event.final else "provisional"
        text = f"[{timestamp(event.start_ms)}] [{label}]\n"
        if self.view == "bilingual":
            text += f"PL: {safe_text(event.polish)}\n"
        text += f"EN: {safe_text(event.english) if event.english is not None else '[translation unavailable]'}"
        if self.show_timing and event.arrival_ms is not None:
            text += f"\nArrived {timestamp(event.arrival_ms)} ({safe_text(str(event.timing_source))})"
            if event.final and event.estimated_final_delay_ms is not None:
                text += f" | estimated final delay {event.estimated_final_delay_ms:+d} ms"
        if event.final:
            if self.live:
                self.live.update(Text(""))
            self.console.print(Text(text))
        elif self.live:
            self.live.update(Text(text))

    def status(self, message):
        if self.live:
            self.live.update(Text(""))
        self.console.print(Text(safe_text(message)))

    def timing_summary(self, summary):
        self.status(f"Timing: {summary['final_captions']} final captions received; {summary['translated_final_captions']} with English; {summary['provider_callback_captions']} SDK callback-timed; {summary['handler_only_captions']} handler-only.")
        for key, label in (("estimated_final_delay", "Estimated final-caption delay (not benchmark latency)"),
                           ("dispatch_delay", "SDK callback to session handler"),
                           ("provisional_to_final", "First observed provisional to final callback")):
            stats = summary[key]
            if not stats['count']:
                self.status(f"{label}: no samples.")
            else:
                self.status(f"{label}: n={stats['count']}, median={stats['median_ms']:g} ms, p95={stats['p95_ms']:g} ms, max={stats['max_ms']:g} ms.")
        if summary['negative_estimates']:
            self.status(f"Warning: {summary['negative_estimates']} negative delay estimates retained; source-clock alignment needs review.")

    def __exit__(self, *args):
        if self.live:
            self.live.update(Text(""))
            self.live.stop()
