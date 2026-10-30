"""Azure adapter behind a bounded process boundary; no automatic cloud invocation."""

from dataclasses import dataclass, field
import multiprocessing as mp
import os
from queue import Empty, Full
import re
import signal
import threading
import time

from liltide.audio import AudioError


@dataclass(frozen=True)
class CloudConfig:
    key: str = field(repr=False)
    region: str
    segmentation_silence_ms: int | None = None

    @classmethod
    def from_environment(cls, confirm_f0=False, segmentation_silence_ms=None):
        if not confirm_f0:
            raise AudioError("Confirm the resource is Azure Speech F0 in Azure, then pass --confirm-f0. This flag cannot verify your billing tier.")
        key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
        region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
        return cls.from_values(key, region, confirm_f0, segmentation_silence_ms)

    @classmethod
    def from_values(cls, key, region, confirm_f0=False, segmentation_silence_ms=None):
        if not confirm_f0:
            raise AudioError("Confirm the resource is Azure Speech F0 in Azure, then pass --confirm-f0.")
        key, region = key.strip(), region.strip()
        if not key or not region:
            raise AudioError("Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION locally. Never share keys in chat or CLI flags.")
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", region):
            raise AudioError("AZURE_SPEECH_REGION must be a region identifier, not an endpoint URL.")
        if segmentation_silence_ms is not None and not 100 <= segmentation_silence_ms <= 5000:
            raise AudioError("Segmentation silence must be between 100 and 5000 milliseconds.")
        return cls(key, region, segmentation_silence_ms)


@dataclass(frozen=True)
class Caption:
    segment_id: str
    start_ms: int
    end_ms: int
    polish: str
    english: str | None
    final: bool
    callback_monotonic: float | None = field(default=None, repr=False)
    arrival_ms: int | None = None
    handled_ms: int | None = None
    timing_source: str | None = None
    dispatch_delay_ms: int | None = None
    first_provisional_arrival_ms: int | None = None
    provisional_to_final_ms: int | None = None
    estimated_final_delay_ms: int | None = None

    @property
    def has_content(self):
        return bool(self.polish.strip() or (self.english or "").strip())


class ProviderError(AudioError):
    def __init__(self, message, *, reason="provider_failure", retryable=False):
        super().__init__(message)
        self.reason = reason
        self.retryable = retryable


@dataclass(frozen=True)
class ProviderFailure:
    message: str
    reason: str
    retryable: bool = False

    def exception(self):
        return ProviderError(self.message, reason=self.reason, retryable=self.retryable)


def caption_from_result(result, final, callback_monotonic=None):
    start = int(result.offset / 10000)
    duration = result.duration
    milliseconds = int(duration.total_seconds() * 1000) if hasattr(duration, "total_seconds") else int(duration / 10000)
    english = (result.translations or {}).get("en")
    if english is not None and not english.strip():
        english = None
    return Caption(str(result.offset), start, start + milliseconds,
                   result.text or "", english, final, callback_monotonic=callback_monotonic)


def cancellation_message(code):
    name = getattr(code, "name", str(code)).split(".")[-1]
    return {
        "AuthenticationFailure": "Azure authentication failed. Check the local key and matching resource region.",
        "Forbidden": "Azure access denied. Check resource access and F0 availability; do not upgrade automatically.",
        "TooManyRequests": "Azure quota or request limit reached. Session stopped; check the F0 resource. No paid fallback.",
        "ConnectionFailure": "Azure connection failed.",
        "ServiceTimeout": "Azure timed out.",
        "ServiceUnavailable": "Azure is temporarily unavailable.",
    }.get(name, "Azure canceled recognition. Check the resource and connection; quota exhaustion is not confirmed. Session stopped.")


def cancellation_failure(code):
    name = getattr(code, "name", str(code)).split(".")[-1]
    reasons = {"ConnectionFailure": "connection_failure", "ServiceTimeout": "service_timeout",
               "ServiceUnavailable": "service_unavailable", "AuthenticationFailure": "authentication_failure",
               "Forbidden": "access_denied", "TooManyRequests": "rate_or_quota_limit", "BadRequest": "bad_request"}
    return ProviderFailure(cancellation_message(code), reasons.get(name, "unknown_cancellation"),
                           name in {"ConnectionFailure", "ServiceTimeout", "ServiceUnavailable"})


def _azure_worker(config, incoming, events, errors, acknowledged):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        import azure.cognitiveservices.speech as sdk

        failed = threading.Event()
        ended = threading.Event()
        closing = threading.Event()
        disconnected = threading.Event()
        def fail(message, reason="sdk_failure", retryable=False):
            failed.set()
            try:
                errors.put_nowait(ProviderFailure(message, reason, retryable))
            except Full:
                pass
        def emit(item, required=True):
            try:
                events.put_nowait(item)
            except Full:
                if required:
                    fail("Caption event buffer overflow. Session stopped; output may be incomplete.", "caption_overflow")

        settings = sdk.translation.SpeechTranslationConfig(subscription=config.key, region=config.region)
        settings.speech_recognition_language = "pl-PL"
        settings.add_target_language("en")
        if config.segmentation_silence_ms is not None:
            settings.set_property(sdk.PropertyId.Speech_SegmentationSilenceTimeoutMs,
                                  str(config.segmentation_silence_ms))
        stream = sdk.audio.PushAudioInputStream(
            stream_format=sdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1))
        audio = sdk.audio.AudioConfig(stream=stream)
        recognizer = sdk.translation.TranslationRecognizer(translation_config=settings, audio_config=audio)
        connection = sdk.Connection.from_recognizer(recognizer)
        def on_disconnect(event):
            if not closing.is_set():
                disconnected.set()
        connection.disconnected.connect(on_disconnect)
        def on_result(event, final):
            arrived = time.monotonic()  # SDK callback entry, before decoding and IPC.
            try:
                result = event.result
                if result.reason == sdk.ResultReason.NoMatch:
                    return
                caption = caption_from_result(result, final, arrived)
                if caption.has_content:
                    emit(caption, required=final)
            except Exception:
                fail("Could not decode an Azure caption event; session stopped.")
        def on_cancel(event):
            if event.reason == sdk.CancellationReason.Error:
                failure = cancellation_failure(event.error_code)
                fail(failure.message, failure.reason, failure.retryable)
            ended.set()
        recognizer.recognizing.connect(lambda e: on_result(e, False))
        recognizer.recognized.connect(lambda e: on_result(e, True))
        recognizer.canceled.connect(on_cancel)
        recognizer.session_stopped.connect(lambda e: ended.set())
        recognizer.start_continuous_recognition_async().get()
        emit("ready")
        while not failed.is_set():
            if disconnected.is_set():
                # Prefer a specific cancellation (especially auth/quota) over the
                # generic disconnect signal; never classify by native error text.
                if not failed.wait(.2):
                    fail("Azure connection disconnected.", "network_disconnect", True)
                break
            try:
                chunk = incoming.get(timeout=.05)
            except Empty:
                if ended.is_set():
                    fail("Azure ended the session unexpectedly. Audio gap: restart the session.")
                    break
                continue
            if chunk is None:
                closing.set()
                stream.close()
                ended.wait(2.5)  # Parent enforces a three-second total shutdown budget.
                recognizer.stop_continuous_recognition_async().get()
                emit("stopped")
                break
            stream.write(chunk)
            with acknowledged.get_lock():
                acknowledged.value += len(chunk)
    except Exception:
        # Native error strings may contain subscription/endpoint information.
        try:
            errors.put_nowait(ProviderFailure("Azure SDK failed to initialize or stream. Check SDK compatibility, credentials, and region locally; native details were omitted.", "sdk_failure"))
        except Full:
            pass


class AzureProvider:
    """Process isolation bounds native SDK startup/write/stop stalls."""

    def __init__(self, config):
        ctx = mp.get_context("spawn")
        self.incoming = ctx.Queue(maxsize=10)
        self.events = ctx.Queue(maxsize=128)
        self.errors = ctx.Queue(maxsize=1)
        self.acknowledged = ctx.Value("q", 0)
        self.process = ctx.Process(target=_azure_worker,
            args=(config, self.incoming, self.events, self.errors, self.acknowledged), daemon=True)
        self.sent = 0
        self.ready = False
        self.started = False

    def start(self):
        self.process.start()
        self.started = True
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            for event in self.poll():
                if isinstance(event, ProviderFailure):
                    raise event.exception()
                if event == "ready":
                    self.ready = True
                    return
            time.sleep(.02)
        raise ProviderError("Azure startup timed out. Check credentials, region, connectivity, and SDK compatibility.",
                            reason="startup_timeout", retryable=True)

    def poll(self):
        result = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except Empty:
                break
        try:
            failure = self.errors.get_nowait()
        except Empty:
            failure = None
        if failure is None and self.started and not self.process.is_alive() and "stopped" not in result:
            try:
                failure = self.errors.get(timeout=.1)
            except Empty:
                failure = ProviderFailure("Azure worker stopped unexpectedly. Session ended.", "worker_exit")
        if failure is not None:
            # Deliver completed captions before reporting the failure. Drop stale
            # provisional updates and never feed another audio block afterward.
            return [e for e in result if isinstance(e, Caption) and e.final] + [failure]
        return result

    def write(self, pcm):
        if not pcm:
            return
        if self.sent - self.acknowledged.value + len(pcm) > 32000:
            raise ProviderError("Audio gap: Azure input backlog exceeded one second.", reason="input_backlog", retryable=True)
        try:
            self.incoming.put_nowait(pcm)
        except Full:
            raise ProviderError("Audio gap: Azure input queue is full.", reason="input_backlog", retryable=True)
        self.sent += len(pcm)

    def finish(self):
        """Yield final callbacks during a bounded drain, then always reap the worker."""
        try:
            if not self.started:
                return
            try:
                self.incoming.put_nowait(None)
            except Full:
                raise ProviderError("Final audio could not drain; session output may be incomplete.", reason="finalization_failure")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                events = self.poll()
                for event in events:
                    if isinstance(event, ProviderFailure):
                        raise event.exception()
                    if isinstance(event, Caption):
                        yield event
                if "stopped" in events:
                    return
                time.sleep(.02)
            raise ProviderError("Azure finalization exceeded three seconds; unfinished captions may be missing.", reason="finalization_timeout")
        finally:
            self.abort()

    def abort(self):
        if self.started:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=1)
            self.started = False
        for queue in (self.incoming, self.events, self.errors):
            queue.close()
            queue.cancel_join_thread()
