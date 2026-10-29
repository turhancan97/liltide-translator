# Technical specification

Status: capture and translation PoC implemented with offline tests. Live Azure behavior, quality, and latency are unverified. Exports, automatic retries/reconnect, and cloud diagnostics remain future requirements.

## Scope and baseline

Personal use first; lectures before interactive meetings. v1 supports Polish (`pl-PL`) to English (`en`) text only, on Windows, macOS, and Linux. No Liltide account, hosted backend, telemetry, speaker identification, meeting bot, or translated audio. Future language support must be configurable, but only this pair is accepted/tested in v1.

Use Python 3.11+, standard `pyproject.toml` packaging and a `src/liltide` layout. Baseline dependencies: Typer, Rich, SoundCard, NumPy, a dedicated resampler (initial candidate: python-soxr), and Azure's Python Speech SDK. Use pytest and fake providers for application tests. Resolve compatible versions and native dependencies during the capture milestone; do not publish guessed minimum OS/architecture support. Future GUI: PySide6, added separately.

## Architecture and data flow

```text
System audio / microphone / paced WAV replay
  → capture adapter → channel conversion + resampling
  → bounded PCM stream → provider adapter
  → provisional/finalized segment events → session coordinator
  → terminal renderer + explicitly enabled exporters
```

- **Audio sources:** Enumerate selectable sources and their type. Windows uses WASAPI loopback; Linux uses a PulseAudio-compatible monitor, including PipeWire's PulseAudio compatibility service; macOS uses a separately configured virtual audio input. Microphones are an alternative source, never silently selected when system capture fails.
- **Audio format:** Read all required device channels, mix to mono without clipping, resample with a stateful dedicated resampler, and encode little-endian signed 16-bit PCM at 16 kHz. Handle non-finite samples explicitly. Avoid requesting a single capture channel on Windows without validating SoundCard's documented channel limitation.
- **WAV input:** Initially accept uncompressed PCM16 mono/stereo WAV at common sample rates including 16, 44.1, and 48 kHz, converting as needed. Reject unsupported encodings with an actionable message. Replay at real-time pace through the same stream; no compressed codecs or accelerated batch path initially.
- **Provider:** One Azure continuous translation recognizer produces Polish text and English translations. Keep a provider interface that can emit both; do not force a separate translation API. Use provider segmentation/endpointing first. Transport blocks are not independent transcription requests; preserve streaming context. Client-side voice-activity gating is deferred unless measurements justify it.
- **Session:** Own capture, provider lifetime, monotonic elapsed time, event ordering, pause/reconnect, and finalization. Capture callbacks must not block on rendering or network calls. Keep GUI/terminal dependencies out of the core.
- **Events:** Normalize provisional segments, finalized segments, status/errors, and audio gaps. Associate provisional updates with a stable segment identifier; replace the active provisional row rather than appending duplicates. Emit each finalized segment once. Finalized text is immutable within a session.

## Planned CLI contract

The full interface below includes future commands. For executable capture commands and installation, see [setup](setup.md).

```console
liltide devices
liltide doctor
liltide doctor --cloud
liltide run --source system --device DEVICE_ID --confirm-f0
liltide run --source microphone --device DEVICE_ID --confirm-f0
liltide run --source file --file lecture.wav --confirm-f0
liltide run --source system --device DEVICE_ID --confirm-f0 --view english
liltide run --source system --device DEVICE_ID --confirm-f0 --export-text session.txt --export-jsonl session.jsonl
```

`devices` lists IDs, names, source type, and channel count. Native sample rates are not exposed consistently; the capture meter requests 48 kHz by default. Device IDs are used as returned; do not claim they remain stable across reboots. `doctor` performs local, non-recording, non-network checks by default; `--cloud` explicitly opts into a minimal F0 connectivity check, which can consume allowance. A local audio-level check will use `run --check-audio --source ... --device ...`, capture without transmission or saving, and exit on Ctrl+C. The meter also accepts `--duration SECONDS` (0.1–3600 seconds after the first level update) and `--sample-rate HZ` (8000–192000; actual device support must be checked). For the meter, a separate spawned reader process sends only level summaries through a one-item queue in level-check mode; the parent bounds first-frame wait to 15 seconds and subsequent stalls to 8 seconds, then requests shutdown and terminates a stuck reader if needed.

PoC behavior: `doctor --cloud` and export options are not implemented. Translation requires `--confirm-f0` plus local credentials before capture/network activity. WAV replay, pause/resume, and speech-format resampling are implemented. Live PCM uses up to ten 100 ms blocks in the capture queue; the Azure worker queue allows ten chunks and at most 32,000 bytes not yet accepted by the SDK. Combined application PCM queues are bounded to at most two seconds. SDK acceptance is not network acknowledgement; internal SDK buffering remains outside this application limit. Native disconnect, cancellation, or application overflow stops the session; automatic retry/reconnect is deferred to milestone 3. macOS inputs are labeled “routed input” rather than guessed as microphones or loopbacks. The operator must select the correct virtual input for system audio. Mono Windows endpoints are rejected due to SoundCard's documented limitation. The meter measures pre-downmix channel energy so anti-phase stereo does not conceal activity.

`run` defaults to `--source system` and `--view bilingual`; require `--device` for live input and `--file` for file input. Reject conflicting source/file/device flags. No automatic microphone fallback. Only Polish-to-English is accepted initially. `--check-audio` is incompatible with cloud/export options. Credentials come from environment variables `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`, never command-line arguments. Map these to the SDK configuration; never print the key.

In an interactive translation session, `p` toggles pause/resume; Ctrl+C stops gracefully. Reuse the same session actions in the later GUI. Non-interactive sessions have no keyboard pause controls and append finalized captions/status text without cursor control. Bilingual mode shows `PL` and `EN` labels; provisional captions carry `[provisional]`, finalized captions carry `[final]`, and timestamps use elapsed `HH:MM:SS.mmm` from capture start. Session time continues across pauses and gaps.

`--export-text PATH` and `--export-jsonl PATH` are independent opt-ins. Refuse to overwrite existing files; report an error before capturing. Without these options, no transcript files or raw recordings are created. Write finalized segments incrementally and flush after each segment; exclude provisional text from exports. Do not dump transcripts in debug logs. No automatic recovery file in v1; explicit exports are the disk recovery mechanism.

JSONL records contain `type`, `session_id`, `segment_id` for segment records, `start_ms`, `end_ms`, `source_language`, `target_language`, `source_text`, and `translation_text`. Use UTF-8, session-relative audio times, and `null` for genuinely unavailable text; never invent missing translations. Gap records use `type: "gap"`, start/end times, and a reason. Plain text includes readable gap notices and language labels. Never include credentials, raw PCM, or personal device metadata in exports.

## Lifecycle and failures

Initial states: idle → connecting → running; running can enter paused or reconnecting, then return to running; any state can stop or fail. Show status transitions in words. Pause stops capture and the provider stream, preserves finalized text, and discards unfinished provisional text. File replay also pauses its cursor. Resume creates a new provider context. Stop requests a bounded provider drain (up to 3 seconds), flushes enabled exports, releases resources, and restores terminal settings.

The following reconnect/export behavior is the reliability milestone target, not fully implemented in the PoC. Use at most 2 seconds of queued PCM. On overflow or network loss, discard stale queued audio, record an audio gap, and reconnect with fresh context rather than building latency. Retry transient failures up to three times with waits of 1, 2, and 4 seconds; stop after exhaustion. Do not retry invalid credentials, confirmed quota exhaustion, unsupported input, or removed devices indefinitely. An ambiguous service cancellation must be reported honestly, not automatically labeled a quota error. Stop on export write failure so promised persistence does not silently fail. Keep finalized text visible during recovery.

## Free-only and privacy policy

Azure F0 is the only approved initial cloud tier; no paid fallback, automatic provisioning, or tier upgrade. Follow the [provider policy](providers.md) for account setup and allowance limits. SDK data-plane credentials alone do not prove the resource's billing tier. Require the operator to pass `--confirm-f0` before enabling cloud use; configuration intent and local usage estimates are not a billing guarantee. Quota rejection ends the session with an explanation.

Capture is limited to the selected device while running; no microphone mixing, background capture, hidden uploads, or telemetry. Live system capture may include unrelated application sounds; source selection is not application isolation. No raw audio recording. Cloud provider handling remains subject to its own terms. User-selected text exports persist until the user removes them. Application logs contain operational events only, with secrets and caption content excluded.

## Completion criteria

See [validation](validation.md) for behavior and failure tests. Initial performance target: median finalized translation within 5 seconds of phrase end on a representative Polish recording; report actual values and tail latency. No accuracy, delay, or platform support claim is established by this specification.


## Implementation sources checked

Reviewed 2026-10-28: [Azure translation recognizer API](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.translation.translationrecognizer?view=azure-python), [PCM stream requirements](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-use-audio-input-streams), and [SoXR streaming API](https://python-soxr.readthedocs.io/en/latest/soxr.html). Installed Azure SDK 1.53.0 source confirms translation cancellation fields and recognition offsets/durations in 100 ns ticks. These checks validate API usage, not live cloud accuracy or access.
