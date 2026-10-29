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

    @classmethod
    def from_environment(cls, confirm_f0=False):
        if not confirm_f0:
            raise AudioError("Confirm the resource is Azure Speech F0 in Azure, then pass --confirm-f0. This flag cannot verify your billing tier.")
        key = os.environ.get("AZURE_SPEECH_KEY", "").strip()
        region = os.environ.get("AZURE_SPEECH_REGION", "").strip()
        if not key or not region:
            raise AudioError("Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION locally. Never share keys in chat or CLI flags.")
        if not re.fullmatch(r"[a-z][a-z0-9-]{1,63}", region):
            raise AudioError("AZURE_SPEECH_REGION must be a region identifier, not an endpoint URL.")
        return cls(key, region)


@dataclass(frozen=True)
class Caption:
    segment_id: str
    start_ms: int
    end_ms: int
    polish: str
    english: str | None
    final: bool


def caption_from_result(result, final):
    start = int(result.offset / 10000)
    duration = result.duration
    milliseconds = int(duration.total_seconds() * 1000) if hasattr(duration, "total_seconds") else int(duration / 10000)
    return Caption(str(result.offset), start, start + milliseconds,
                   result.text or "", result.translations.get("en"), final)


def cancellation_message(code):
    name = getattr(code, "name", str(code)).split(".")[-1]
    return {
        "AuthenticationFailure": "Azure authentication failed. Check the local key and matching resource region.",
        "Forbidden": "Azure access denied. Check resource access and F0 availability; do not upgrade automatically.",
        "TooManyRequests": "Azure quota or request limit reached. Session stopped; check the F0 resource. No paid fallback.",
        "ConnectionFailure": "Azure connection failed. Audio gap: session stopped; restart after checking your connection.",
        "ServiceTimeout": "Azure timed out. Audio gap: session stopped; no stale audio will be replayed.",
    }.get(name, "Azure canceled recognition. Check the resource and connection; quota exhaustion is not confirmed. Session stopped.")


def _azure_worker(config, incoming, events, errors, acknowledged):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    try:
        import azure.cognitiveservices.speech as sdk

        failed = threading.Event()
        ended = threading.Event()
        closing = threading.Event()
        def fail(message):
            failed.set()
            try:
                errors.put_nowait(message)
            except Full:
                pass
        def emit(item, required=True):
            try:
                events.put_nowait(item)
            except Full:
                if required:
                    fail("Caption event buffer overflow. Session stopped; output may be incomplete.")

        settings = sdk.translation.SpeechTranslationConfig(subscription=config.key, region=config.region)
        settings.speech_recognition_language = "pl-PL"
        settings.add_target_language("en")
        stream = sdk.audio.PushAudioInputStream(
            stream_format=sdk.audio.AudioStreamFormat(samples_per_second=16000, bits_per_sample=16, channels=1))
        audio = sdk.audio.AudioConfig(stream=stream)
        recognizer = sdk.translation.TranslationRecognizer(translation_config=settings, audio_config=audio)
        connection = sdk.Connection.from_recognizer(recognizer)
        def on_disconnect(event):
            if not closing.is_set():
                fail("Audio gap: Azure disconnected. Session stopped; restart after checking connectivity and resource access.")
        connection.disconnected.connect(on_disconnect)
        def on_result(event, final):
            try:
                result = event.result
                if result.reason == sdk.ResultReason.NoMatch:
                    return
                if result.text or result.translations:
                    emit(caption_from_result(result, final), required=final)
            except Exception:
                fail("Could not decode an Azure caption event; session stopped.")
        def on_cancel(event):
            if event.reason == sdk.CancellationReason.Error:
                fail(cancellation_message(event.error_code))
            ended.set()
        recognizer.recognizing.connect(lambda e: on_result(e, False))
        recognizer.recognized.connect(lambda e: on_result(e, True))
        recognizer.canceled.connect(on_cancel)
        recognizer.session_stopped.connect(lambda e: ended.set())
        recognizer.start_continuous_recognition_async().get()
        emit("ready")
        while not failed.is_set():
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
            errors.put_nowait("Azure SDK failed to initialize or stream. Check SDK compatibility, credentials, and region locally; native details were omitted.")
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
                if event == "ready":
                    self.ready = True
                    return
            time.sleep(.02)
        raise AudioError("Azure startup timed out. Check credentials, region, connectivity, and SDK compatibility.")

    def poll(self):
        try:
            raise AudioError(self.errors.get_nowait())
        except Empty:
            pass
        result = []
        while True:
            try:
                result.append(self.events.get_nowait())
            except Empty:
                break
        if self.started and not self.process.is_alive() and "stopped" not in result:
            try:
                message = self.errors.get(timeout=.1)
            except Empty:
                message = "Azure worker stopped unexpectedly. Session ended."
            raise AudioError(message)
        return result

    def write(self, pcm):
        if not pcm:
            return
        if self.sent - self.acknowledged.value + len(pcm) > 32000:
            raise AudioError("Audio gap: Azure input backlog exceeded one second. Session stopped.")
        try:
            self.incoming.put_nowait(pcm)
        except Full:
            raise AudioError("Audio gap: Azure input queue is full. Session stopped.")
        self.sent += len(pcm)

    def finish(self):
        """Yield final callbacks during a bounded drain, then always reap the worker."""
        try:
            if not self.started:
                return
            try:
                self.incoming.put_nowait(None)
            except Full:
                raise AudioError("Final audio could not drain; session output may be incomplete.")
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                events = self.poll()
                yield from (e for e in events if isinstance(e, Caption))
                if "stopped" in events:
                    return
                time.sleep(.02)
            raise AudioError("Azure finalization exceeded three seconds; unfinished captions may be missing.")
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
