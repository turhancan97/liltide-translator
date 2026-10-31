# Technical specification

Status: capture/translation, opt-in exports, bounded recovery, timing, and GUI stages one through four are implemented with offline tests. Live macOS CLI translation/recovery are user-confirmed; the GUI is also user-confirmed as working on macOS, with detailed checklist results unrecorded. Reference-aligned quality/latency and cross-platform release validation remain open. Cloud diagnostics are unimplemented.

## Scope and baseline

Personal use first; lectures before interactive meetings. v1 supports Polish (`pl-PL`) to English (`en`) text only, on Windows, macOS, and Linux. No Liltide account, hosted backend, telemetry, speaker identification, meeting bot, or translated audio. Future language support must be configurable, but only this pair is accepted/tested in v1.

Use Python 3.11+, standard `pyproject.toml` packaging and a `src/liltide` layout. Baseline dependencies: Typer, Rich, SoundCard, NumPy, a dedicated resampler (initial candidate: python-soxr), and Azure's Python Speech SDK. Use pytest and fake providers for application tests. Resolve compatible versions and native dependencies during the capture milestone; do not publish guessed minimum OS/architecture support. Stage-one GUI: optional PySide6 extra, sharing the same processing core.

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

PoC behavior: `doctor --cloud` is not implemented. Export options are implemented as explicit opt-ins. Translation requires `--confirm-f0` plus local credentials before capture/network activity. WAV replay, pause/resume, and speech-format resampling are implemented. Live PCM uses up to ten 100 ms blocks in the capture queue; the Azure worker queue allows ten chunks and at most 32,000 bytes not yet accepted by the SDK. Combined application PCM queues are bounded to at most two seconds. SDK acceptance is not network acknowledgement; internal SDK buffering remains outside this application limit. Classified transient provider failures and input backlog enter bounded fresh-context recovery; fatal/unknown provider errors and capture failures stop. macOS inputs are labeled “routed input” rather than guessed as microphones or loopbacks. The operator must select the correct virtual input for system audio. Mono Windows endpoints are rejected due to SoundCard's documented limitation. The meter measures pre-downmix channel energy so anti-phase stereo does not conceal activity.

`run` defaults to `--source system` and `--view bilingual`; require `--device` for live input and `--file` for file input. Reject conflicting source/file/device flags. No automatic microphone fallback. Only Polish-to-English is accepted initially. `--check-audio` is incompatible with cloud/export options. Credentials come from environment variables `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`, never command-line arguments. Map these to the SDK configuration; never print the key.

In an interactive translation session, `p` toggles pause/resume; Ctrl+C stops gracefully. Reuse the same session actions in the later GUI. Non-interactive sessions have no keyboard pause controls and append finalized captions/status text without cursor control. Bilingual mode shows `PL` and `EN` labels; provisional captions carry `[provisional]`, finalized captions carry `[final]`, and timestamps use elapsed `HH:MM:SS.mmm` from session start, including connection setup. Session time continues across pauses and gaps.

`--export-text PATH` and `--export-jsonl PATH` are independent opt-ins. Refuse to overwrite existing files; report an error before capturing. Without these options, no transcript files or raw recordings are created. Write finalized segments incrementally and flush plus `fsync` each destination after each segment, before display; exclude provisional text from exports. Do not dump transcripts in debug logs. No implicit recovery file; explicit exports are the disk persistence mechanism.

JSONL records contain `type`, `session_id`, `segment_id` for segment records, `start_ms`, `end_ms`, `source_language`, `target_language`, `source_text`, and `translation_text`. Use UTF-8, session-relative audio times, and `null` for genuinely unavailable text; never invent missing translations. Text exports include readable language labels and start/end timestamps. Gap records use `type: "gap"`, `session_id`, `start_ms`, `end_ms`, and a controlled `reason` code; text receives `[gap]` blocks. JSONL readers must dispatch by `type`. Checkpoints and closure records can be adjacent intervals for the same interruption. Never include credentials, raw PCM, or personal device metadata in exports.

## macOS cross-process input identity

Device listing still displays the numeric SoundCard ID for CLI selection. Discovery also reads CoreAudio's persistent DeviceUID into private session memory; the GUI retains that identity from discovery through validation, capture spawn, pause/resume, and reconnect. CLI live preflight binds its supplied exact numeric ID to a UID; direct/local capture binds before spawning. The child resolves an exact, unique UID against its own current inputs, allowing numeric-ID reassignment without name/default matching. A reused numeric ID belonging to a different UID cannot replace the selected identity. Missing, ambiguous, or unreadable identities fail closed; source/capture failures remain non-retryable.

The read-only macOS helper loads system CoreAudio/CoreFoundation lazily and releases each returned CFString. It adds no dependency and is not loaded for Windows/Linux endpoints. Other platforms retain exact SoundCard endpoint IDs; hardware validation remains open. Identity objects hide IDs/UIDs from their representation and never enter metadata/exports. Error diagnostics distinguish parent validation from child lookup and expose only input counts, identity outcome, and whether the prior numeric ID is present. Lookup performs one bounded enumeration pass, with no retry loop or identifier log. It does not impose a new timeout on native property calls; existing capture-child startup bounds still apply, while parent/native discovery can still block.

These changes address the demonstrated identity-change mechanism, not a proven cause of the historical intermittent failure. The subsequent SEC-01 repair also requires explicit initial GUI input selection and clears lost/ambiguous selections after Refresh, retaining a macOS device by exact UID rather than its prior numeric ID. See [security review](security-review.md).

## Lifecycle and failures

Initial states: idle → connecting → running; running can enter paused or reconnecting, then return to running; any state can stop or fail. Show status transitions in words. Pause stops capture and the provider stream, preserves finalized text, and discards unfinished provisional text. File replay also pauses its cursor. Resume creates a new provider context. Stop requests a bounded provider drain (up to 3 seconds), flushes enabled exports, releases resources, and restores terminal settings.

Implemented recovery behavior (offline-tested; live validation pending): Use at most 2 seconds of queued PCM. On overflow or network loss, discard stale queued audio, record an audio gap, and reconnect with fresh context rather than building latency. Retry only structured transient failures up to three times per run with waits of 1, 2, and 4 seconds; stop after exhaustion. Success/pause does not reset the budget. Do not retry invalid credentials, confirmed quota exhaustion, unsupported input, or removed devices indefinitely. An ambiguous service cancellation must be reported honestly, not automatically labeled a quota error. Stop on export write failure so promised persistence does not silently fail. Keep finalized text visible during recovery.

## Free-only and privacy policy

Azure F0 is the only approved initial cloud tier; no paid fallback, automatic provisioning, or tier upgrade. Follow the [provider policy](providers.md) for account setup and allowance limits. SDK data-plane credentials alone do not prove the resource's billing tier. Require the operator to pass `--confirm-f0` before enabling cloud use; configuration intent and local usage estimates are not a billing guarantee. Quota rejection ends the session with an explanation.

Capture is limited to the selected device while running; no microphone mixing, background capture, hidden uploads, or telemetry. Live system capture may include unrelated application sounds; source selection is not application isolation. No raw audio recording. Cloud provider handling remains subject to its own terms. User-selected text exports persist until the user removes them. Application logs contain operational events only, with secrets and caption content excluded.

## Completion criteria

See [validation](validation.md) for behavior and failure tests. Initial performance target: median finalized translation within 5 seconds of phrase end on a representative Polish recording; report actual values and tail latency. No accuracy, delay, or platform support claim is established by this specification.


## Implementation sources checked

Reviewed 2026-10-28: [Azure translation recognizer API](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.translation.translationrecognizer?view=azure-python), [PCM stream requirements](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-use-audio-input-streams), and [SoXR streaming API](https://python-soxr.readthedocs.io/en/latest/soxr.html). Installed Azure SDK 1.53.0 source confirms translation cancellation fields and recognition offsets/durations in 100 ns ticks. These checks validate API usage, not live cloud accuracy or access.


## Export lifecycle

The exporter is a session sink independent of terminal rendering. The session deduplicates final events and assigns context-prefixed segment IDs before invoking it; provisional events never reach the persistence callback. One run uses one export session ID across pause/resume, with UTF-8 text and JSONL files opened through exclusive creation before audio/cloud startup. Missing parent directories fail preflight; no implicit directory creation or overwrite/append mode is offered.

Exports always include both languages independently of display view. Files use owner read/write permissions on POSIX; Windows access also depends on the directory ACL. Writes flush and `fsync` each segment. Default behavior remains no persistence. On an export error, abort capture/provider processing; do not erase saved data or silently continue. A failed final record can be partial, and two output formats are independent rather than an atomic transaction. Abrupt-process-exit survival is tested; power loss/storage guarantees depend on the filesystem and hardware. Source/cloud startup failures can leave empty explicitly requested export files.


## Blank-event filtering and optional segmentation tuning

The Azure adapter tests actual Polish/English text content rather than dictionary truthiness. Blank or whitespace-only events never reach the caption sink; the session and exporter also reject them defensively. This happens before finalized-ID deduplication, so a blank event cannot suppress a later meaningful result at the same offset. Missing/blank English values normalize to `None`/JSON `null`; valid source-only or translation-only captions remain supported. Existing private exports are not rewritten.

`--segmentation-silence-ms` optionally passes an integer from 100–5000 to the Azure translation config property `Speech_SegmentationSilenceTimeoutMs`. Default `None` leaves service behavior unchanged. The SDK property setting is covered by fake-SDK and CLI tests; its actual translation-service effect, latency benefit, and quality trade-offs require live evaluation. This is not a hard phrase-duration cap. See [setup tuning guidance](setup.md#tuning-long-finalized-phrases). No recognition/translation content is post-edited without reference evidence.


## Recovery implementation boundaries

Provider failures carry structured reason/retryability across the process boundary. Native cancellation codes determine retry policy; no text matching of SDK errors. A disconnect gets a short 200 ms window for a more specific cancellation (especially auth/quota) before generic network recovery. Unknown/native exceptions remain nonretryable. Final events already queued are delivered before the failure; stale provisional updates are discarded.

On recovery, close live capture, abort the old provider, clear queues/resampler state, retain finalized history/export files, and checkpoint an uncertainty gap before backoff. Use new contexts on retries, sharing only the unchanged cloud configuration and finalized history. WAV replay retains its cursor without replaying consumed unconfirmed chunks. Record remaining gap time on successful activation or termination. Export callbacks are outside transient-provider classification: persistence errors stop and are never retried. Gaps may include unfinalized speech before detected failure, are not exact network downtime measurements, and can be zero-duration for immediate errors. Ordinary pause intervals are not marked as network loss. During intentional EOF/stop drain, report failure/gap rather than restarting capture.

Session timestamps now start at `run()` (connection setup included). `--duration` remains measured from first stream readiness, including subsequent pauses/recovery waits. Lifecycle/source cleanup is guaranteed through outer `finally` blocks in tested failure paths. Live SDK detection timing and other-platform behavior remain to be verified; see [manual recovery steps](setup.md#brief-manual-recovery-test-not-yet-performed-by-the-agent).


## Arrival measurement implementation

The SDK worker stamps each meaningful caption callback with `time.monotonic()` at entry, before decoding or IPC. `Caption` carries this internal timestamp across the existing process boundary. The session maps it to milliseconds since `run()` started, records handler time before export/render, computes local dispatch delay, and tracks the earliest observed meaningful provisional callback per context/segment. Final timing is deduplicated with the final caption and unfinished provisional history is reset on activation. Providers without callback stamps get an explicit handler-only fallback; callback-derived delays remain unavailable.

Segment JSONL adds `arrival_ms`, `handled_ms`, `timing_source`, `dispatch_delay_ms`, `first_provisional_arrival_ms`, `provisional_to_final_ms`, and `estimated_final_delay_ms`. Defaults are `null` for untimed standalone exports. Existing fields and gap schema remain unchanged; no raw monotonic reference or system wall-clock time is persisted. Text includes an arrival/estimated-delay line. `--show-timing` opts into console details and end-of-session statistics, not additional storage. Median/p95/max use available final samples; p95 is nearest rank. Negative estimates are preserved and flagged; received events (including source-only captions or a final whose persistence subsequently failed) are counted explicitly.

`estimated_final_delay_ms = arrival_ms - end_ms` uses the existing session-mapped provider audio timeline. It includes alignment uncertainty and is not a verified source-end/display latency. No capture timestamp propagation or reference-audio annotation was added. Source startup, buffering, source pacing/drift, resampling, and segmentation can affect the estimate. Local dispatch excludes later disk sync/render time. Refer to [setup measurement definitions](setup.md#caption-arrival-time-measurements) before interpreting values. Python 3.11+ monotonic clocks share a reference across local processes, including macOS; worker/parent clock differences are covered with deterministic tests, not inferred from live benchmarks.

## Export run metadata

The CLI constructs an allowlisted `RunMetadata` value from validated input type and requested segmentation setting, then passes it to `TranscriptExports`. No environment introspection is used. Enabled destinations receive one durable session header before source/provider creation, using the same session ID for all caption and gap records across recovery. Header-write errors close destinations and prevent startup. No enabled destinations means no persistence. Standalone exporter callers can omit metadata for compatibility.

The versioned session record (`schema_version: 1`) contains app version, provider identifier, language pair, input type, requested segmentation silence, and explicit/default mode. It does not change segment/gap schemas or rewrite old exports. Null silence means no override requested, not a known numerical backend default. Settings are requests, not proof of backend behavior. Filenames, device identifiers, credentials, environment values, region, and wall-clock timestamps are excluded. Readers dispatch on record type and tolerate legacy headerless files. See [field definitions and example](setup.md#run-configuration-metadata).

## Stage-one GUI architecture

`liltide-gui` / `python -m liltide.gui` lazily loads Qt, leaving CLI installations independent of the optional GUI extra. The main thread owns widgets; QThread workers handle device discovery and the unchanged translation/capture/provider pipeline. A thread-safe stop event is passed as `TranslationSession.should_stop`; session polling, activation boundaries, and reconnect backoff check it without consuming terminal pause commands. Existing graceful final drain and native cleanup remain in effect.

A 40 ms UI timer drains a bounded 256-event final-caption queue; one locked provisional/status slot coalesces intermediate updates. Overflow raises an actionable error and stops the session. Final captions are plain text (including literal markup characters); provisional and status widgets use explicit text labeling. Source/device selection, F0 confirmation, Start/Stop, Pause/Resume, explicit session states, and bilingual/English-only display are included. GUI exports and timing/session-summary controls are included; audio-file input remains unavailable in the GUI. Optional segmentation tuning is now available as described below. The separately authorized local macOS app adds Keychain setup and allowlisted preferences as described below. Finished workers are joined before release, and closing is deferred until all workers finish. Optional dependency terms are recorded in [third-party notices](third-party.md).

## GUI stage two

The core exposes an optional `on_state` callback for lifecycle notifications; the CLI retains its existing status/control path. The GUI receives structured state names rather than inferring state from explanatory messages. A coalesced pause Event is consumed by the existing session control callback; only Running/Paused accept toggles, and a pending request immediately disables further toggles. Stop retains priority. Core pause drains finals, closes live capture/provider resources, discards unfinished context, and keeps history; resume creates new contexts using the same config and retry budget. Resume failures use the existing typed recovery/fatal policy.

The window retains caption objects and session separators in memory independently of presentation. View changes re-render history and the latest provisional caption, preserving source text and missing-translation markers. They do not mutate caption data, session config, exports, or workers. Provisional labels and final text preserve literal markup characters. History remains unbounded as before; the deferred long-session memory/performance check still applies. Explicit state and detail text distinguish pending transitions from completed pause/stop.

## GUI stage three

The window validates explicit export toggles/paths before constructing its worker; the worker opens a single `TranscriptExports` context with allowlisted `RunMetadata` before device selection/capture/provider startup. It wires `on_finalized` and `on_gap` directly to that sink, so writes complete before a finalized caption reaches the UI queue. Existing exclusive creation, per-record flush/fsync, failure cleanup, and cross-context session identity apply without a new export schema. Unchecked exports produce no files. Export options are frozen for the worker lifetime; only the new session is saved.

The worker captures `session.timing_summary()` in a `finally` block, including fatal/export-error paths; pre-session failures expose the existing empty-summary shape. After joining the worker, the UI retains that last-session summary and renders it according to the timing checkbox. Counts describe received final events, including one whose persistence failed. No summary sidecar, aggregate JSONL event, or default storage is introduced. Caption timing display uses already measured event fields and does not affect provider configuration or sink output. View/timing toggles re-render in-memory history and provisional text only.

Browse uses the documented [Qt file-selection API](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QFileDialog.html) (checked 2026-10-29); widget-dialog selection does not imply permission to overwrite. The exporter still refuses existing destinations. Browse callbacks use bound slots without a window-retaining lambda; offscreen tests include successful process exit after widget/thread cleanup.

## GUI stage four

`gui_theme.py` defines window-local palettes/styles using the approved brand colors and neutral supporting colors. System mode reads `QStyleHints.colorScheme` (unknown falls back to the application palette) and listens to `colorSchemeChanged`; manual modes use the same styles without changing OS or application-global appearance. Stage four introduced no settings persistence; the separately authorized local macOS app now adds allowlisted persistence as described below. The approach uses [Qt style-hint notifications](https://doc.qt.io/qtforpython-6/PySide6/QtGui/QStyleHints.html), checked 2026-10-29; notification behavior is simulated in tests, not independently verified by changing the real OS theme.

The header loads an unchanged copy of the approved waveform symbol from `liltide/resources/symbol.svg`; keep it synchronized with `assets/brand/liltide-symbol-light.svg`. A small original MIT checkmark SVG makes selection visible in both themes. Resources ship inside the Python wheel; no repository-relative runtime paths or downloaded assets are required. Qt SVG support is supplied by the existing optional PySide6 dependency.

A horizontal splitter separates scrollable setup/export groups from the reader/session pane. Caption sizing changes widget fonts only. Explicit Tab order, label buddies, accessible names, selectable text, window-scoped shortcuts, focus borders, and labeled states preserve keyboard/status access. These controls use existing guards and do not touch workers, credentials, session metadata, or exports. The GUI history/memory and deferred validation limits remain unchanged. Floating captions are outside this stage.

Selectors use a shared `Dropdown` with per-widget list delegates, matching popup/control fonts, and content-sized, screen-bounded menus. Row padding is explicit; unusually long entries can scroll horizontally without eliding. This avoids native menu-gutter metrics conflicting with styled popup widths. Theme/Caption size controls reserve enough space for their labels and arrows. Qt supports custom combo views/delegates through its [model/view API](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QComboBox.html) (checked 2026-10-29).

## Floating caption view

`FloatingCaptions` is a parent-owned Qt tool window with `WindowStaysOnTopHint`, `WA_MacAlwaysShowToolWindow`, and quit-on-close disabled. It owns no processing or exports. Main-thread caption draining supplies the latest final; the existing UI timer supplies coalesced provisional/state updates. It stores only one final and one provisional observation, without duplicating full history. New runs reset that view, while pause/stop preserve the last finalized text. Closing the floating window hides it and updates the main toggle; main-window shutdown hides it after session cleanup.

Signal-blocked synchronization routes its language/font controls through the existing main controls; themes apply to both windows. Hidden views still receive latest data, so reopening neither replays history nor creates a worker. Final/provisional text uses read-only plain-text widgets and clear labels. The documented [Qt window flags](https://doc.qt.io/qtforpython-6/PySide6/QtCore/Qt.html) (checked 2026-10-29) describe requests to the window manager, not independently verified cross-platform/fullscreen behavior. No transparency, click-through overlay, persisted geometry, or new cloud behavior is introduced.

On macOS Cocoa, each floating-window show also configures the borrowed NSWindow through a lazy, typed Objective-C bridge using system libobjc. It requests `canJoinAllSpaces` and `fullScreenAuxiliary`; macOS 13+ also uses Apple's [`canJoinAllApplications`](https://developer.apple.com/documentation/appkit/nswindow/collectionbehavior-swift.struct/canjoinallapplications) behavior for eligible floating windows over other apps' fullscreen Spaces. Conflicting move-to-active/fullscreen-primary/fullscreen-none flags are removed; on 13+ mutually exclusive primary/auxiliary Stage Manager flags are removed. Unrelated behavior bits are preserved. Methods run on the GUI thread via the production show event, retain no native handles, read settings back, and reapply on reopening. No global activation policy, focus policy, window level, screen preference, or dependency change is introduced. Non-Cocoa/other platforms keep their existing Qt behavior without loading libobjc. Failure preserves the window and displays a fullscreen-visibility limitation in its footer. Native policy readback passed locally on macOS 27.0.1 arm64; actual Chrome fullscreen visibility still requires the post-fix retest.

## Untrusted text presentation

Terminal captions, provisional text, status/errors, device listing, and human-readable export fields use shared visible escaping for C0/C1 controls (including ESC, CR/backspace, and embedded LF/tab) and Unicode line/paragraph separators. Layout newlines are added by the application after field escaping. This prevents terminal controls and forged field lines while retaining ordinary Polish Unicode. JSONL preserves original decoded values, using JSON C0 escaping plus C1/separator escaping; text and JSONL can therefore differ in their visible representation of control characters. Existing exports are not rewritten.

## Local macOS app

The separately authorized local bundle reuses the same Qt GUI and session core. [Build/setup instructions](macos-app.md) define its launch and storage behavior. PyInstaller's windowed onedir bundle includes Python, Qt, audio conversion/capture modules, Azure SDK native libraries, and packaged resources. The dedicated entry calls `multiprocessing.freeze_support()` before importing GUI modules; the offline bundle diagnostic verifies actual spawn dispatch and SDK/audio imports without running live workers. The app includes an input-permission description and local ad-hoc signature; it has no updater, Developer ID signature or notarization.

The macOS GUI injects `MacCredentials` and `Preferences`; other platforms and directly constructed test windows retain the environment-only/default-isolated behavior. `CloudConfig.from_values` centralizes locale-independent validation; F0 confirmation remains required per launch and is never saved. The macOS credential adapter uses the explicit `keyring.backends.macOS.Keyring` backend only. A single Keychain record holds the matching key/region, written only by the masked setup dialog. No saved key is rendered, logged, added to exports, or copied to environment variables. Any present environment credential selects the entire environment configuration; incomplete environment configuration fails rather than mixing accounts. Keychain/backend failures produce generic errors with no plaintext fallback or raw exception details.

Qt settings persist only theme, source type, language view and supported caption size. Input persistence requires opting into Remember and a successful Start validation; it stores source type and private persistent UID, without a name/numeric fallback. A single initial discovery may restore only a unique UID in the matching source type; missing/ambiguous matches stay unselected. Subsequent Refresh uses the existing in-memory identity checks. Unchecking Remember removes the saved UID. F0 consent, timing toggle, export paths/toggles, audio and text history are excluded. Opening the app performs no automatic discovery/capture/provider request. Settings/backend failure coverage uses temporary settings and fake Keychain backends; actual operator Keychain permissions and packaged live capture remain separate validation.

## GUI segmentation control — 2026-10-31

The user authorized exposing the existing optional silence threshold in the app. An unchecked Custom phrase pause checkbox maps to `None`; enabling it uses a bounded 100–5000 ms spinbox, initially 300 ms. Both environment and Keychain configuration paths pass the value through the existing validator. The immutable worker config carries it through pause/resume and recovery, while the UI controls remain disabled until worker cleanup. The existing `RunMetadata` records either service-default or explicit-request mode in enabled exports. No schema, provider policy, session slicing, automatic saving, or default service setting changes are introduced. The choice is local to the current window and is excluded from persistent preferences.
