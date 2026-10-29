"""Provider-independent streaming session and pause/resume lifecycle."""

from dataclasses import replace
import time
from uuid import uuid4

from liltide.audio import AudioError
from liltide.events import Gap
from liltide.formatting import timestamp
from liltide.pcm import PCMEncoder
from liltide.provider import Caption, ProviderError, ProviderFailure
from liltide.timing import timing_summary


class TranslationSession:
    def __init__(self, source_factory, provider_factory, on_caption, on_status,
                 control=lambda: None, *, file_input=False, duration=None, on_finalized=None, on_gap=None):
        self.source_factory = source_factory
        self.provider_factory = provider_factory
        self.on_caption = on_caption
        self.on_status = on_status
        self.control = control
        self.file_input = file_input
        self.duration = duration
        self.on_finalized = on_finalized
        self.on_gap = on_gap
        self.source = self.provider = None
        self.finalized = []  # Retained in memory; persistence is a separate opt-in sink.
        self.seen = set()
        self.started = None
        self.ready_at = None
        self.base_ms = 0
        self.last_final_end_ms = 0
        self.retries = 0
        self.pending_gap = None
        self.gaps = []
        self.first_provisionals = {}

    def timing_summary(self):
        return timing_summary(self.finalized)

    def _elapsed_ms(self):
        return 0 if self.started is None else max(0, int((time.monotonic() - self.started) * 1000))

    def _expired(self):
        return (self.duration is not None and self.ready_at is not None and
                time.monotonic() - self.ready_at >= self.duration)

    def _begin_gap(self, reason):
        if self.pending_gap is None:
            # The last committed caption is the conservative confirmation boundary.
            # Include unfinalized audio already sent before detecting the failure.
            self.pending_gap = (max(self.base_ms, self.last_final_end_ms), reason)

    def _close_gap(self, end_ms=None):
        if self.pending_gap is None:
            return
        start, reason = self.pending_gap
        self.pending_gap = None  # Do not retry a failed persistence callback.
        event = Gap(start, max(start, self._elapsed_ms() if end_ms is None else end_ms), reason)
        if (event.start_ms == event.end_ms and self.gaps and
                self.gaps[-1].end_ms == start and self.gaps[-1].reason == reason):
            return  # The initial checkpoint already represents this instant.
        self.gaps.append(event)
        if self.on_gap:
            self.on_gap(event)
        self.on_status(f"Audio gap [{timestamp(event.start_ms)} --> {timestamp(event.end_ms)}]: {reason}. Audio may be missing or unfinalized.")

    def _checkpoint_gap(self):
        if self.pending_gap is not None:
            reason = self.pending_gap[1]
            self._close_gap()  # Persist the detected uncertainty before any retry wait.
            self.pending_gap = (self.gaps[-1].end_ms, reason)

    def _emit(self, event):
        if not isinstance(event, Caption) or not event.has_content:
            return
        event = replace(event, segment_id=f"{self.epoch}:{event.segment_id}",
                        start_ms=event.start_ms + self.base_ms, end_ms=event.end_ms + self.base_ms)
        if event.segment_id in self.seen:
            return
        handled = round((time.monotonic() - self.started) * 1000)  # Before export/fsync/rendering.
        callback_timed = event.callback_monotonic is not None
        arrival = round((event.callback_monotonic - self.started) * 1000) if callback_timed else handled
        if not event.final and callback_timed:
            self.first_provisionals[event.segment_id] = min(self.first_provisionals.get(event.segment_id, arrival), arrival)
        first = self.first_provisionals.get(event.segment_id)
        event = replace(event, arrival_ms=arrival, handled_ms=handled,
                        timing_source="provider_callback" if callback_timed else "session_handler",
                        dispatch_delay_ms=handled - arrival if callback_timed else None,
                        first_provisional_arrival_ms=first,
                        provisional_to_final_ms=arrival - first if event.final and callback_timed and first is not None else None,
                        estimated_final_delay_ms=arrival - event.end_ms if event.final and callback_timed else None)
        if event.final:
            self.first_provisionals.pop(event.segment_id, None)
            self.seen.add(event.segment_id)
            self.finalized.append(event)
            self.last_final_end_ms = max(self.last_final_end_ms, event.end_ms)
            if self.on_finalized:
                self.on_finalized(event)
        self.on_caption(event)

    def _activate(self):
        if self.source is None:
            self.source = self.source_factory()
        self.encoder = PCMEncoder(self.source.rate)
        self.encoder_finished = False
        self.epoch = uuid4().hex
        self.first_provisionals.clear()  # Unfinished provisional observations do not cross contexts.
        self.base_ms = self._elapsed_ms()
        self.on_status("Connecting to Azure Speech (operator-confirmed F0)…")
        self.provider = self.provider_factory()
        self.provider.start()
        if self.ready_at is None:
            self.ready_at = time.monotonic()
        self.base_ms = max(self._elapsed_ms(), self.last_final_end_ms)
        self.source.resume()
        self._close_gap(self.base_ms)
        self.on_status("Running: selected audio is sent to Azure; no raw-audio recording. Press p to pause/resume in an interactive terminal; Ctrl+C stops.")

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

    def _recover(self, error):
        self._begin_gap(error.reason)
        self._deactivate(graceful=False)  # Discard old source/SDK queues and resampler state.
        self._checkpoint_gap()
        delays = (1, 2, 4)
        while error.retryable and self.retries < len(delays):
            delay = delays[self.retries]
            self.on_status(f"{error} Reconnecting {self.retries + 1}/3 in {delay} seconds. Capture stopped; Ctrl+C cancels.")
            deadline = time.monotonic() + delay
            while time.monotonic() < deadline:
                if self._expired():
                    self._close_gap()
                    self.on_status("Session duration reached during recovery.")
                    return False
                time.sleep(min(.05, max(0, deadline - time.monotonic())))
            if self._expired():
                self._close_gap()
                return False
            self.retries += 1  # Run-wide budget, never reset by successful reconnection/pause.
            try:
                self._activate()
            except ProviderError as next_error:
                error = next_error
                self._deactivate(graceful=False)
                continue
            return True
        self._close_gap()
        if not error.retryable:
            raise error
        raise ProviderError(f"Reconnect limit reached (3 retries per run). {error}", reason=error.reason)

    def run(self):
        failed = False
        self.started = time.monotonic()
        try:
            active = True
            try:
                self._activate()
            except ProviderError as error:
                active = self._recover(error)
            paused = False
            while active:
                if self._expired():
                    break
                try:
                    if self.control() == "pause":
                        if paused:
                            paused = False
                            self._activate()
                        else:
                            paused = True
                            self._deactivate(graceful=True)
                            self.on_status("Paused: capture/transmission stopped; unfinished provisional text and resampler tail discarded. Press p to resume.")
                    if paused:
                        time.sleep(.02)
                        continue
                    for event in self.provider.poll():
                        if isinstance(event, ProviderFailure):
                            raise event.exception()
                        self._emit(event)
                    try:
                        samples = self.source.read()
                    except StopIteration:
                        self.provider.write(self.encoder.flush())
                        self.encoder_finished = True
                        break
                    except AudioError:
                        self._begin_gap("source_failure")
                        raise
                    if samples is not None:
                        self.provider.write(self.encoder.encode(samples))
                    else:
                        time.sleep(.01)
                except ProviderError as error:
                    if paused:
                        self._begin_gap(error.reason)
                        self._deactivate(graceful=False)
                        self._close_gap()
                        if not error.retryable:
                            raise
                        self.on_status("Paused after provider interruption. Press p to resume with a fresh connection.")
                    elif not self._recover(error):
                        break
        except KeyboardInterrupt:
            self.on_status("Stopping…")
        except Exception:
            failed = True
            self.on_status("Session failed; previously finalized captions remain visible. Audio after failure is not buffered for replay.")
            raise
        finally:
            try:
                try:
                    self._deactivate(graceful=not failed, flush=not failed)
                except ProviderError as error:
                    self._begin_gap(error.reason)
                    raise  # Do not reconnect during a deliberate stop/EOF drain.
            finally:
                try:
                    self._close_gap()
                finally:
                    if self.source:
                        self.source.close()
                        self.source = None
        self.on_status("Stopped. Capture and cloud resources released.")
