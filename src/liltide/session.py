"""Provider-independent streaming session and pause/resume lifecycle."""

from dataclasses import replace
import time
from uuid import uuid4

from liltide.pcm import PCMEncoder
from liltide.provider import Caption


class TranslationSession:
    def __init__(self, source_factory, provider_factory, on_caption, on_status,
                 control=lambda: None, *, file_input=False, duration=None):
        self.source_factory = source_factory
        self.provider_factory = provider_factory
        self.on_caption = on_caption
        self.on_status = on_status
        self.control = control
        self.file_input = file_input
        self.duration = duration
        self.source = self.provider = None
        self.finalized = []  # Memory-only, retained through pause/recovery.
        self.seen = set()
        self.started = None

    def _emit(self, event):
        if not isinstance(event, Caption):
            return
        event = replace(event, segment_id=f"{self.epoch}:{event.segment_id}",
                        start_ms=event.start_ms + self.base_ms, end_ms=event.end_ms + self.base_ms)
        if event.segment_id in self.seen:
            return
        if event.final:
            self.seen.add(event.segment_id)
            self.finalized.append(event)
        self.on_caption(event)

    def _activate(self):
        if self.source is None:
            self.source = self.source_factory()
        self.encoder = PCMEncoder(self.source.rate)
        self.encoder_finished = False
        self.epoch = uuid4().hex
        self.base_ms = 0 if self.started is None else int((time.monotonic() - self.started) * 1000)
        self.on_status("Connecting to Azure Speech (operator-confirmed F0)…")
        self.provider = self.provider_factory()
        self.provider.start()
        if self.started is None:
            self.started = time.monotonic()
        self.base_ms = int((time.monotonic() - self.started) * 1000)
        self.source.resume()
        self.on_status("Running: selected audio is sent to Azure; no local recording. Press p to pause/resume in an interactive terminal; Ctrl+C stops.")

    def _deactivate(self, *, graceful, flush=False):
        try:
            if self.source and not self.file_input:
                self.source.close()
                self.source = None
            if self.provider:
                if graceful:
                    if flush and not self.encoder_finished:
                        self.provider.write(self.encoder.flush())
                        self.encoder_finished = True
                    for event in self.provider.finish():
                        if isinstance(event, Caption) and event.final:
                            self._emit(event)
                else:
                    self.provider.abort()
        finally:
            if self.provider:
                self.provider.abort()
                self.provider = None

    def run(self):
        failed = False
        try:
            self._activate()
            paused = False
            while True:
                if self.duration is not None and time.monotonic() - self.started >= self.duration:
                    break
                if self.control() == "pause":
                    if paused:
                        self._activate()
                    else:
                        self._deactivate(graceful=True)
                        self.on_status("Paused: capture/transmission stopped; unfinished provisional text and resampler tail discarded. Press p to resume.")
                    paused = not paused
                if paused:
                    time.sleep(.02)
                    continue
                for event in self.provider.poll():
                    self._emit(event)
                try:
                    samples = self.source.read()
                except StopIteration:
                    self.provider.write(self.encoder.flush())
                    self.encoder_finished = True
                    break
                if samples is not None:
                    self.provider.write(self.encoder.encode(samples))
                else:
                    time.sleep(.01)
        except KeyboardInterrupt:
            self.on_status("Stopping…")
        except Exception:
            failed = True
            self.on_status("Session failed; previously finalized captions remain visible. Audio after failure is not buffered for replay.")
            raise
        finally:
            try:
                self._deactivate(graceful=not failed, flush=not failed)
            finally:
                if self.source:
                    self.source.close()
                    self.source = None
        self.on_status("Stopped. Capture and cloud resources released.")
