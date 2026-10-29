# Intended platform setup

**Capture and translation PoC available.** Local capture and user-reported lecture routing work on this Mac. Translation has offline tests and a user-confirmed successful live macOS session; no independent agent cloud test has been run. Other-platform installation/capture remain unverified. No drivers, cloud resources, or credentials are supplied.

## Install and check locally

Python 3.11+ is required; the current local run uses Python 3.13.7. From the project directory:

```console
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
liltide devices
liltide doctor
liltide run --check-audio --source system --device DEVICE_ID --duration 10
```

Windows PowerShell: use `py -3 -m venv .venv`, then `.venv\Scripts\Activate.ps1`; the remaining commands are the same. Shell activation is optional: invoke `.venv/bin/liltide` directly on macOS/Linux, or `.venv\Scripts\liltide.exe` on Windows.

Select an exact ID from `devices`, quoted if necessary. Use `--source microphone` for microphone capture. Omit `--duration` for continuous checks; Ctrl+C releases capture. `--sample-rate` defaults to 48000 Hz. The meter reports RMS/peak dBFS plus SIGNAL, SILENCE/LOW, or CLIPPING; silence or a moving meter alone does not prove correct routing. Non-finite samples and unsupported devices fail explicitly. In a non-interactive terminal it prints approximately one update per second; interactive output refreshes in place. `NO_COLOR` or `TERM=dumb` disables colored/animated terminal presentation.

Run synthetic/offline tests with `python -m pytest -q`. Translation requires explicitly confirmed Azure F0 configuration as described below. WAV input, interactive pause/resume, and opt-in text/JSONL exports are implemented; bounded reconnect and gap records are also implemented; `doctor --cloud` is not.

If discovery returns zero devices inside a sandbox but succeeds in a normal terminal, test from that terminal. `doctor` does not verify recording permissions, and this project does not grant them automatically.

## Shared prerequisites

During the capture milestone, record OS version, architecture, Python version (3.11+), package versions, and native audio backend. Resolve supported SDK wheels and native dependencies before fixing a compatibility matrix. Use a project virtual environment. A GPU is not required by the planned cloud design.

First validate local audio routing using the implemented `devices`, `doctor`, and `run --check-audio` commands in the [technical specification](technical-spec.md). Play a non-private reference clip, confirm level activity, stop playback and check levels fall, and verify the original audio remains audible. Disconnect/reconnect the device and inspect diagnostics. No cloud transmission is needed for this phase.

## Windows: WASAPI loopback

1. Choose the playback endpoint carrying the lecture (for example, the current headphones).
2. Select that endpoint's loopback source in Liltide; a microphone is a separate source.
3. Keep the lecture playing through the normal endpoint; loopback should not require changing its output route.
4. Validate channel conversion and device switching, including Bluetooth behavior on the actual hardware.

[SoundCard](https://github.com/bastibe/SoundCard) uses WASAPI on Windows and documents capture/channel limitations. Do not assume single-channel device recording is safe; capture the necessary channels and downmix. OS/architecture compatibility remains untested here.

## Linux: monitor source

1. Use PulseAudio or PipeWire with its PulseAudio compatibility service enabled.
2. Route the lecture to the intended output sink and select its monitor as Liltide's source.
3. Keep the sink routed to headphones/speakers so the lecture remains audible.
4. Verify permissions, source visibility, rate conversion, and behavior when the default sink changes.

The chosen SoundCard backend uses PulseAudio; native ALSA-only setups are outside the initial approach. Refer to [SoundCard's backend documentation](https://github.com/bastibe/SoundCard). No distribution or audio-server combination has been tested by Liltide yet.

## macOS: virtual audio input

1. Manually install a virtual audio device, such as BlackHole, using its official instructions. Installation is separate from Liltide; no driver is bundled.
2. In Audio MIDI Setup, create a Multi-Output Device containing the virtual device and the headphones/speakers you want to hear. Follow the driver's clock/drift-correction guidance.
3. Route lecture/system playback to the Multi-Output Device.
4. Select the virtual device as Liltide's input, rather than selecting the physical microphone.
5. Grant the launching terminal/app the input permissions macOS requests. Verify capture and audible playback independently.
6. Restore the normal output device after testing if desired. Avoid routing captured audio back into its own input.

See [BlackHole's official repository and Multi-Output guidance](https://github.com/ExistentialAudio/BlackHole). Multi-output volume controls and Bluetooth behavior can differ from normal playback. SoundCard's current macOS backend does not provide the loopback path used on Windows; virtual routing is the initial workaround. Native system capture is deferred.

## Azure F0: translation PoC

1. Check current account eligibility, region availability, allowance, and restrictions using the [provider guide](providers.md).
2. Manually create or choose an Azure Speech resource with the **F0** SKU. If unavailable, stop and report the limitation; do not substitute S0 or use promotional paid-tier credit as approval.
3. Inspect the actual resource's pricing tier in Azure. Cloud billing configuration is the operator's responsibility; a key or a locally declared tier does not verify it.
4. Set `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` locally. Never put secrets in CLI flags, documentation, screenshots, or committed files. The SDK receives these through Liltide's configuration adapter.
5. Only explicitly invoke cloud diagnostics/tests after confirming F0. Use non-private audio. The CLI discloses transmission when a cloud session starts.
6. On quota exhaustion, stop. Do not upgrade, add a paid provider, or continue by switching resources automatically.

The user confirmed a successful live translation session after setup. The agent has not inspected the resource or run a cloud test. Resource provisioning is a separate manual step; never share the key in chat.

After creating an F0 Speech resource, open its Keys and Endpoint page to obtain the key and **region identifier** (for example `westeurope`, not an endpoint URL). Set them in the same terminal that runs Liltide. On macOS/Linux Bash or Zsh, enter the key through a hidden prompt so the value is not embedded in shell history:

```bash
export AZURE_SPEECH_REGION=westeurope
read -r -s AZURE_SPEECH_KEY
export AZURE_SPEECH_KEY
```

After the `read` command, paste the key and press Enter; nothing is echoed. Replace the example region with the actual resource region. In Windows PowerShell:

```powershell
$env:AZURE_SPEECH_REGION = "westeurope"
$env:AZURE_SPEECH_KEY = [System.Net.NetworkCredential]::new("", (Read-Host "Azure Speech key" -AsSecureString)).Password
```

Liltide reads environment variables, not `.env` files. It does not persist keys. Run explicitly:

```console
liltide run --source system --device DEVICE_ID --confirm-f0
liltide run --source microphone --device DEVICE_ID --confirm-f0
liltide run --source file --file lecture.wav --confirm-f0 --view english
```

Use a short non-private Polish clip first. The tier confirmation flag is an operator assertion, not an Azure billing check. Do not pass it for S0. `--duration 30` bounds session wall time after stream readiness, including pauses; initialization/shutdown add some time. Press `p` to pause/resume when stdin is an interactive terminal; capture and the recognizer are released during pause. WAV replay retains its cursor. Resumption creates fresh recognition context. Ctrl+C stops and attempts a bounded final drain.

Provisional text appears in place only in an interactive display; finalized captions are printed once with elapsed timestamps measured from session start (including connection setup). `--view english` omits Polish display but recognition still uses Polish. Plain/piped output contains finalized captions and status lines without cursor control. Classified transient Azure failures and provider-input backlog trigger bounded fresh-context recovery. Known auth/quota failures, unknown errors, source failures, and export errors stop the session. Read any final-drain warning: the last unfinished caption can be missing.

The cloud SDK has its own internal buffers and service behavior; application queue limits are not proof of network delivery or a guaranteed latency bound. `doctor` remains entirely local; `doctor --cloud` deliberately fails without contacting Azure.

## Tuning long finalized phrases

Blank/whitespace-only events are filtered out of captions and exports. If Polish text exists but English is missing/blank, keep the source and export English as JSON `null` (text: `[translation unavailable]`). Recognized text is not automatically rewritten to sound more fluent.

If final results combine too much speech, you can explicitly request a shorter pause threshold:

```console
liltide run --source system --device DEVICE_ID --confirm-f0 --segmentation-silence-ms 300
```

The accepted range is 100–5000 ms. This configures Azure's `Speech_SegmentationSilenceTimeoutMs`; it is a detected-silence threshold, **not** a maximum phrase duration or latency promise. Microsoft suggests 300 ms as one setting to try for long speech-recognition phrases, but its effects on this Polish-to-English translation path have not been measured. Translation-specific behavior can differ. Smaller values can split sentences and reduce translation context. Default: omit the flag to retain the service's existing settings. Local `--check-audio` rejects this cloud-only option. No fixed-length audio slicing, recognizer restarts, or automatic post-editing is used.

Compare the same non-private clip with and without the option, using new export filenames. Review meaning as well as segmentation; export start/end timestamps alone cannot measure actual callback arrival delay. Sources checked 2026-10-29: [Microsoft timeout guidance](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/how-to-recognize-speech#change-how-silence-is-handled) and [translation configuration API](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.translation.speechtranslationconfig?view=azure-python).

## File input and exports

Implemented file support is uncompressed PCM16 WAV, mono or stereo; rate conversion happens in the pipeline. Use synthetic or consented recordings kept outside version control. To retain finalized captions, explicitly request either or both formats. Create the parent folder first (`mkdir -p exports` on macOS/Linux; `New-Item -ItemType Directory -Force exports` in PowerShell):

```console
liltide run --source system --device DEVICE_ID --confirm-f0 --export-text exports/session.txt --export-jsonl exports/session.jsonl
liltide run --source file --file lecture.wav --confirm-f0 --export-jsonl exports/file-session.jsonl
```

- Export flags are independent; without them no transcript files are created. They cannot be combined with `--check-audio`.
- Files are created exclusively before capture/provider startup. Existing files, directories, or symlinks are refused, as is using the same path for both formats. Parent directories must already exist. Startup failure can leave new empty or header-only export files; inspect them and choose fresh names before retrying.
- Among caption events, only finalized segments are exported, once per segment. Text includes elapsed start/end timestamps and `PL`/`EN` labels. JSONL is UTF-8 with one JSON object per finalized segment; Polish diacritics are preserved, embedded newlines are escaped, and unavailable translation is `null`.
- `--view english` changes the terminal display only. Both exports always include Polish and English. No credentials, device metadata, status logs, provisional text, or raw audio are exported.
- Each segment is written, flushed, and synced using the operating system before display. Previously completed records remain readable after Ctrl+C, provider failure, or abrupt process termination. This is not a guarantee against filesystem/hardware failure or preservation of a caption that has not finalized yet.
- A write/flush/sync failure stops capture and the provider. The final record may be incomplete; retain complete JSONL lines before it. If both formats are enabled, one can contain a segment that the other failed to save. No rollback deletes previously saved speech.
- Pausing/resuming keeps the same export files and session ID. New recognizer contexts get distinct segment IDs; no prior transcript is reopened or appended in a later run.
- Current JSONL records use `type: "segment"`, `session_id`, `segment_id`, `start_ms`, `end_ms`, `source_language: "pl-PL"`, `target_language: "en"`, `source_text`, and `translation_text`. JSONL also includes session headers and gap records; readers must branch on `type` (`session`, `segment`, `gap`) rather than assuming every line contains caption text.

Exports persist until you delete them. Keep them outside version control: the project ignores `exports/`, `transcripts/`, and `*.jsonl`; arbitrary `.txt` paths are not automatically ignored. No raw audio files are recorded.


## Connection recovery and gap records

Recovery is automatic in translation mode. A run gets at most **three reconnect attempts total**, waiting **1, 2, and 4 seconds**. The budget is not reset by success or pause/resume. Only classified connection failures, service timeouts/unavailability, generic disconnects without a more specific cancellation, startup timeouts, and provider-input backlog are retryable. Known invalid credentials, denied access, quota/rate limits, bad requests, unknown SDK/service errors, device/source failures, and export failures stop without an automatic retry. Quota and concurrent-request rejection cannot always be distinguished; neither is retried. The same F0 configuration/credentials are reused; no provider/resource/tier switch occurs.

When a failure is detected, old capture and SDK workers are stopped and stale queues/resampler state discarded. Each attempt creates a new recognition context. Live capture restarts from current audio; missed speech is not replayed. WAV input keeps its consumed file cursor and pauses reading during recovery; consumed but unfinalized audio is not re-read. Already finalized captions remain in memory and in enabled exports. Queued final events are delivered before the provider failure. Native startup/drain timeouts still bound individual operations; `--duration` is checked during backoff, but a native initialization/shutdown operation can add time.

A `[gap]` notice describes an uncertainty interval from the current context's last finalized boundary (or its start if none finalized) through failure/recovery. It is not proof that every millisecond was lost: it includes possibly unfinalized audio and reconnect setup. A synced gap checkpoint is written before waiting; another record closes the remaining interval on recovery, retry exhaustion, Ctrl+C, or duration expiry. Adjacent records with the same reason can describe one outage. Immediate failures can produce zero-duration markers. Source failures and failed final drains also produce notices; a deliberately paused/stopped session does not reconnect automatically during finalization. A connection error while pausing leaves the session paused until `p` requests resume. Ctrl+C cancels backoff; keyboard pause is processed in the main session loop after connection startup/wait returns.

With exports enabled, text receives readable `[gap]` blocks and JSONL receives records with exactly:

```json
{"type":"gap","session_id":"example-session","start_ms":12500,"end_ms":15000,"reason":"connection_failure"}
```

Segment records retain their existing schema and share the same export `session_id` across reconnects. New context-prefixed `segment_id` values prevent collisions. Gap reasons are controlled codes (for example `connection_failure`, `network_disconnect`, `service_timeout`, `service_unavailable`, `startup_timeout`, `input_backlog`, `rate_or_quota_limit`, `authentication_failure`, `source_failure`), not raw SDK diagnostics or credentials. Gap writes use the same flush/sync/error handling as caption writes. A gap-export error stops recovery; previous records remain saved. No export flags still means no files.

### Brief manual recovery test (not yet performed by the agent)

1. In a normal terminal, confirm F0, keep the key local, and run with fresh filenames:

   ```console
   liltide run --source system --device DEVICE_ID --confirm-f0 --export-text exports/recovery-test.txt --export-jsonl exports/recovery-test.jsonl
   ```

2. Play a short non-private clip and wait for a finalized caption.
3. Temporarily disconnect your computer's network. Observe the gap/reconnect status; SDK detection can take time. Restore connectivity when the retry message appears.
4. Confirm captions resume, earlier captions remain, and both files include gap records with the same session ID. Ctrl+C should stop cleanly, including during backoff.
5. Record actual status/errors, retry count, and platform. Do not infer exact lost-audio coverage or latency from gap duration. Failure to resume needs investigation rather than upgrading the resource.

Offline fake-provider tests cover this behavior. The user confirmed a successful live macOS disconnect/reconnect/resume/shutdown test; inspected recovery exports also match. A 30-minute session and quantified detection/timing checks remain open. Azure error-code reference checked 2026-10-29: [CancellationErrorCode](https://learn.microsoft.com/en-us/python/api/azure-cognitiveservices-speech/azure.cognitiveservices.speech.cancellationerrorcode?view=azure-python).


## Caption arrival-time measurements

Use the existing F0 credentials and audio route. No additional service or dependency is needed:

```console
liltide run --source system --device DEVICE_ID --confirm-f0 --show-timing --export-jsonl exports/timing-test.jsonl --export-text exports/timing-test.txt
```

Choose fresh filenames and an existing parent directory. Timing is computed for every caption session. `--show-timing` controls terminal detail/summary only; requested exports include timing fields with or without the flag. No export flags means no timing files. `--check-audio` rejects `--show-timing`. Summary output appears after normal completion, Ctrl+C, or a session error once a session exists; it is console output rather than a separate saved summary record.

### Field meanings

Segment JSONL records retain their existing fields and add:

| Field | Definition |
| --- | --- |
| `arrival_ms` | Milliseconds since session start at SDK callback entry; handler time is used only when the provider supplies no callback timestamp |
| `handled_ms` | Milliseconds since session start when the session handles this event, before transcript flush/sync and rendering |
| `timing_source` | `provider_callback` or `session_handler`; `null` for a standalone untimed export |
| `dispatch_delay_ms` | Handler minus callback arrival; `null` without a callback timestamp |
| `first_provisional_arrival_ms` | Earliest callback arrival among meaningful provisional events observed for this segment/context, or `null` |
| `provisional_to_final_ms` | Final callback arrival minus the first observed provisional callback arrival, or `null` when either is unavailable |
| `estimated_final_delay_ms` | Final callback arrival minus session-mapped provider `end_ms`; `null` without a provider callback timestamp |

Timestamps are session-relative, rounded to milliseconds, and continue across pause/reconnect. New recognition contexts reset unfinished provisional observations. Repeated final events do not create extra timing samples. Gap records keep their existing schema and are excluded from caption summaries. Older exports lack these fields; readers should treat absent/`null` values as unavailable. Raw absolute monotonic timestamps stay internal and are not exported. Text files add an `Arrival:` line per timed final caption. `--view english` still changes display only, not export languages/timing.

### What these numbers establish

SDK callbacks are stamped before event decoding/IPC. `dispatch_delay_ms` measures local dispatch/handling delay, including polling and other session work; it is not network latency. Neither callback nor handler time measures when pixels became visible: disk sync, console output, and terminal refresh happen afterward. First observed provisional-to-final time measures stabilization after an available partial result; dropped/unobserved partial callbacks are not reconstructed.

**The final source-end delay is an estimate.** Provider audio offsets are mapped using each recognition context’s readiness time; capture startup/buffering, resampling, replay pacing/drift, and provider segmentation affect audio-to-clock alignment. WAV results use the same session mapping and are not an annotated reference benchmark. Negative estimates are kept, not clamped to zero; they flag alignment issues or overly early audio delivery for review. Do not interpret segment duration as latency, a small local dispatch time as fast translation, or a handler-only fallback as a measured SDK arrival.

The terminal summary reports final captions received, how many contain English, SDK-timed versus handler-only counts, and sample count/median/nearest-rank p95/max for available estimates, local dispatch, and provisional-to-final intervals. Estimates include source-only final captions when English is unavailable, so inspect `translation_text` when evaluating translated output specifically. No samples yields an explicit unavailable result. Negative estimates remain in aggregates and produce a warning. With few samples, p95 often equals the maximum. Summary counts are received events, not a guarantee that every event was displayed or persisted if an export failed.

For the next test, play a short non-private Polish clip, stop with Ctrl+C, and inspect these fields plus the terminal summary. Then use a representative reference recording with annotated phrase ends and a controlled playback clock to evaluate actual end-to-end translation delay. No new live cloud timing measurement has been run by the agent. Clock reference checked 2026-10-29: [Python monotonic clock](https://docs.python.org/3/library/time.html#time.monotonic).

## Run configuration metadata

New CLI exports start with one session header, written and flushed/synced before audio-source or provider startup. Text exports have a readable `[session]` block. JSONL exports begin with this structure (the session ID varies):

```json
{"type":"session","session_id":"example","schema_version":1,"app_version":"0.1.0.dev0","provider":"azure_speech","source_language":"pl-PL","target_language":"en","input_type":"system","segmentation_silence_ms":300,"segmentation_mode":"explicit_request"}
```

`input_type` is `system`, `microphone`, or `file`. With no segmentation override, `segmentation_silence_ms` is `null` and `segmentation_mode` is `service_default`; this does not assume a numerical Azure default. With `--segmentation-silence-ms 300`, the fields are `300` and `explicit_request`. These describe requested settings, not proof of service behavior or identical cloud models across runs.

The header shares `session_id` with all subsequent segments/gaps and is not repeated on pause/resume or reconnect. A header alone means export initialization succeeded, not that capture or translation succeeded. Header-write failures close opened files and prevent source/provider startup. Without export flags, metadata remains in memory and no files or sidecars are created.

Metadata is an explicit allowlist: no credentials, environment values, Azure region, device names/IDs, file paths, or wall-clock identifiers are included. Caption records still contain speech. Older files remain unchanged and may lack a header; readers should treat their settings as unknown rather than infer them from folder names. Standalone exporter callers may omit metadata for compatibility. New JSONL readers must handle `session`, `segment`, and `gap` separately.

## Desktop GUI PoC

GUI stages one through four are implemented with optional PySide6; it does not replace the CLI. Installation and offscreen fake-provider tests passed locally on macOS arm64/Python 3.13.7 with PySide6 6.12.0. The user subsequently reported that the GUI works well on their macOS setup; individual live checklist results and duration were not supplied. Desktop accessibility and Windows/Linux remain unverified.

1. Activate your existing virtual environment and run `python -m pip install -e ".[gui]"`.
2. Set the same local `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION` environment variables used by the CLI. Launch from that terminal with `liltide-gui` or `python -m liltide.gui` so the process inherits them. The GUI does not load `.env` files automatically.
3. Click **Refresh devices**, choose **System audio** or **Microphone**, then select the input. On macOS all routed inputs are shown for either type; explicitly choose BlackHole/your virtual device for system audio. Keep the existing multi-output playback routing so you can hear the source. Discovery is not a routing/permission check.
4. Verify your Azure resource is F0, check the F0 confirmation box, then click **Start translation**. This sends selected audio to Azure. The checkbox is your assertion, not a billing-tier check. There is no paid fallback.
5. Finalized Polish/English captions accumulate in the text area; provisional text is separate and labeled. **Stop** requests cleanup and drains remaining finalized captions. Closing an active window waits for cleanup too. Startup/drain/native shutdown can take several seconds; the UI does not force-terminate a session thread.

Opening the window and refreshing devices do not record audio or contact Azure. No audio files or settings are saved by the GUI; transcript files are saved only when explicitly enabled before Start. Prior finalized text remains visible across starts until the window closes; there is no disk recovery. GUI controls currently use the service-default segmentation setting. Use the CLI for WAV input and segmentation tuning; optional exports and timing summaries are also available in the GUI. System/Light/Dark themes, brand styling, and caption sizing are available; floating captions are also available.

The GUI runs discovery and session coordination off the UI thread, reusing the existing capture and provider subprocesses. Stop also cancels reconnect waits. It coalesces provisional updates and bounds pending final-caption delivery to 256 events; overflow stops translation visibly rather than growing a hidden queue. Previously displayed captions remain. Final transcript history stays in memory and can grow with session length, as in the CLI; the deferred long-session memory check is still needed. Device discovery/native operations may delay closing until their own return/timeout.

Offline GUI checks: `QT_QPA_PLATFORM=offscreen python -m pytest tests/test_gui.py -q` on macOS/Linux; in PowerShell set `$env:QT_QPA_PLATFORM="offscreen"` before running pytest. Without the GUI extra, GUI tests skip; CLI tests still run.

### GUI pause/resume, display, and states

- **Pause** is enabled only while Running. It requests a graceful final-result drain and releases live capture/provider resources. During **Pausing**, cleanup is still in progress; wait for **Paused** before assuming transmission has stopped. Unfinished provisional text and resampler tail are discarded. Finalized captions stay visible.
- **Resume** is enabled only when Paused. It creates fresh capture/recognizer contexts and continues the same in-memory session history; speech during the pause is not replayed. The existing retry budget and F0-only policy are unchanged.
- During Connecting, Pausing, Reconnecting, and Stopping, the pause toggle is disabled to prevent queued duplicate transitions. **Stop** works while paused or reconnecting; closing also waits for cleanup. Fatal resume errors show **Error** and retain finalized text.
- **Polish + English / English only** changes existing finalized text and current/future provisional captions immediately, including after Stop or across runs in the same window. It does not reconnect or change the Polish source/English translation configuration. Missing English remains `[translation unavailable]`; switching back restores the retained Polish text. This view preference is not persisted to disk.
- A separate, color-independent state label shows Ready, Discovering, Connecting, Running, Pausing, Paused, Reconnecting, Stopping, Stopped, or Error, with explanatory text below it. Native startup/drain timeouts can delay transitions; a requested pause is not yet a completed pause.

Stage-two behavior is offline-tested with fake providers and offscreen widgets. After receiving the stage-two update, the user reported that it works well on macOS; individual pause/resume/view-switch checklist results and duration were not supplied. No agent live cloud run was performed for this addition.

### GUI exports and timing

Before **Start translation**, check **Save text**, **Save JSONL**, or both and type or browse to new filenames in an existing parent folder. Unchecked formats are ignored even if their fields contain paths. Export controls are locked during the run, including while paused. They remain configured in this window after Stop, so choose fresh filenames before starting another run; files are never overwritten or appended. Browse only selects a destination and does not save anything yet. It uses Qt's widget file dialog, with actual exclusive creation enforced by the exporter at Start.

Exports save the new run, not captions from earlier runs still visible in the window. Both languages are included even in English-only view. The worker uses the CLI's durable exporter: session header, finalized segments with timing fields, and gap records use the same schemas and flush/sync behavior. Provisional text is excluded. One export session/header spans pause/resume and reconnects. Header/preflight failure prevents capture/provider startup. Source startup failure can leave a header-only file. Persistence errors stop the session; previously completed records remain, but a last record can be incomplete and paired files can differ. Consult [export details](#file-input-and-exports) and keep transcripts outside version control.

**Show caption timing and session timing summary** is a display-only toggle that can change at any time, without reconnecting. It adds arrival/provenance and explicitly estimated final-caption delay to existing/new finalized captions, plus arrival details for provisional text. It does not enable saving or change exported timing fields. Delay is not verified benchmark latency; source alignment and pacing can affect it, and dispatch excludes later disk sync/display work. See [timing definitions](#caption-arrival-time-measurements).

After Stop, normal completion, or failure, the summary shows the last run's received final-caption count and how many contain English. Enable the timing toggle to show SDK versus handler-only counts and sample count/median/nearest-rank p95/max for estimated final-caption delay, callback-to-handler delay, and first-provisional-to-final interval. Unavailable samples are labeled; negative estimates remain and trigger a warning. Summary counts are received events, not proof of successful persistence or display of every record. Worker failures before a session starts produce zero samples; a Start rejected by the window before worker creation leaves the prior summary unchanged. A new run replaces the previous summary; prior transcript text remains visible. The summary is not written as a separate export record/file.

Stage-three exports/timing are offline-tested with synthetic speech and fake providers, including failures/recovery and clean Qt shutdown. Live GUI checks of these additions remain open; earlier user confirmations cover stages one/two. No new agent cloud test was run.

### GUI appearance and keyboard controls

The header offers **Theme → System / Light / Dark**. System is the default; it follows Qt's reported OS color scheme and updates on its notification. If no color scheme is reported, the application palette supplies a light/dark fallback. Light/Dark overrides apply to this window and its widgets, not the OS appearance setting. Returning to System uses the currently reported scheme. Preferences are not saved after closing the window.

**Caption size** offers 12, 14, 16 (default), 18, 22, and 26 pt using the system sans-serif font. It changes both finalized/provisional captions without reformatting caption data or reconnecting. The original symbol and approved blue/red/gray palette appear with ink/white supporting surfaces. Blue/red are graphic accents; normal text uses higher-contrast neutral pairs. Every session state and caption status remains labeled in words.

Audio setup and optional exports sit in the left pane; session controls, captions, and session details sit in the right pane. Drag the divider to resize; each pane can scroll when the window is constrained, and finalized captions also have their own scroll area. At large caption sizes, scroll to read longer text. The layout was checked offscreen at 1100×820 and 760×600, not against every display scaling setting.

Tab/Shift+Tab navigate controls, with associated labels and visible focus. Start uses `Ctrl+Return`, Pause/Resume uses `Ctrl+Space`, and Stop uses `Ctrl+.` in Qt key-sequence notation; native platform representations appear in button tooltips. Shortcuts are window-scoped, respect disabled controls, and cannot bypass F0 or session guards. Standard text selection/copy remains available; provisional and summary labels are selectable too. Actual desktop keyboard mapping and screen-reader behavior remain unverified.

Theme/font/view changes work during running/paused/stopped sessions, preserving captions, worker identity, export destinations, and F0 settings. Appearance controls do not save files or invoke cloud services. Stages one/two have earlier macOS user confirmations; the new layout/theme/keyboard behavior is offline-tested only. Persisted preferences and platform release validation remain later work; floating-caption behavior is described below.

### Floating captions

Click **Floating captions** in the main header to show a movable/resizable secondary window. Click the button again or close the secondary window to hide it. It is optional and initially hidden. Opening it does not start capture, contact Azure, or enable exports; start translation through the main window as usual.

The floating view shows the latest **Finalized** caption, separate **Provisional** text, and the current session state. The main window retains the full history. New sessions clear old floating captions; Pause/Stop keep the last finalized caption and clear unfinished provisional text after cleanup. While hidden, the view tracks the latest result so reopening is current. Long text remains readable through the text areas' scrollbars.

**View** and **Caption size** controls work in either window and synchronize in both directions. The floating window inherits the main theme, including System updates. These presentation changes do not restart processing or alter export content. Text is selectable and preserves literal markup/Polish Unicode. Use the main window for Start/Pause/Resume/Stop and exports. Closing the floating view does not stop translation; closing the main window still requests session cleanup, then hides the floating window too. Floating geometry/settings are not saved to disk.

Qt is asked to keep this tool window on top and keep it visible while the app is inactive on macOS. Actual stacking depends on the OS/window manager; offscreen tests verify flags and interaction, not desktop stacking or fullscreen/Spaces behavior. Those live checks remain open, along with the earlier unverified stage-three/four additions. No agent audio/cloud test was run for this feature.
