# Liltide

![Liltide — live captions across languages](assets/brand/liltide-banner.svg)

**Live captions across languages.**

Liltide is an open-source Python tool for following computer audio with a live Polish transcript and English translation. It targets Windows, macOS, and Linux, starting with a terminal interface and later a Python GUI.

**Status: translation PoC implemented, offline-tested, and user-confirmed working live on macOS.** Local capture works on this Mac, including user-confirmed lecture playback routing. Windows/Linux capture, translation quality, and latency remain unverified.

## Try the local capture CLI

```console
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
liltide --help
liltide devices
liltide doctor
liltide run --check-audio --source system --device DEVICE_ID --duration 10
```

On Windows PowerShell, create the environment with `py -3 -m venv .venv` and activate with `.venv\Scripts\Activate.ps1`. Copy an exact device ID from `devices`; quote it if needed. For a microphone use `--source microphone`. Omit `--duration` to run until Ctrl+C. The meter only shows levels; it does not save or transmit audio. macOS system audio needs a manually routed virtual input. See [setup](docs/setup.md).

Run offline tests with `python -m pytest -q`. Tests use synthetic audio/fake devices; they do not open capture devices or require cloud credentials.

## Try translated captions

Configure your own Azure Speech **F0** resource and local environment variables using the [Azure setup instructions](docs/setup.md#azure-f0-translation-poc). Then explicitly enable cloud transmission:

```console
liltide run --source system --device DEVICE_ID --confirm-f0
liltide run --source file --file lecture.wav --confirm-f0 --view english
```

`--confirm-f0` asserts you checked the resource tier; Liltide cannot verify it or enforce account-wide billing. Press `p` to pause/resume in an interactive terminal; Ctrl+C stops. Plain/piped output shows finalized captions only. No transcript files are saved unless requested. Classified temporary connection failures trigger up to three fresh-context retries per run (1, 2, 4 seconds). Known authentication/quota errors stop immediately; no paid fallback is used.

## Save finalized captions

Create an export directory, then opt into either or both formats:

```console
mkdir -p exports
liltide run --source system --device DEVICE_ID --confirm-f0 --export-text exports/session.txt --export-jsonl exports/session.jsonl
```

PowerShell users can create the folder with `New-Item -ItemType Directory -Force exports`. Choose fresh filenames for each run: existing files are never overwritten. Both formats contain Polish and English, regardless of the terminal's `--view`. Provisional captions are excluded. Every finalized segment is flushed and synced before display, so completed writes survive a process interruption. Exports may contain private speech; the `exports/` folder is ignored by Git. See [export details](docs/setup.md#file-input-and-exports).

New CLI exports automatically begin with run settings: app version, language pair, input type, and requested segmentation silence. JSONL uses a `type: "session"` header; text uses a `[session]` block. No extra flag is needed. Device identifiers, filenames, and credentials are excluded. See [run metadata](docs/setup.md#run-configuration-metadata).

Connection interruptions appear as `[gap]` notices and, when export is enabled, `type: "gap"` JSONL records. Capture stops during recovery; stale audio is discarded. Saved captions remain in the same files/session. Gap intervals conservatively include audio that may be missing or unfinalized, and may be split into adjacent checkpoint/recovery records. See [recovery behavior and test steps](docs/setup.md#connection-recovery-and-gap-records).

## Inspect caption timing

```console
liltide run --source system --device DEVICE_ID --confirm-f0 --show-timing --export-jsonl exports/timing-test.jsonl
```

Use a new filename. `--show-timing` displays arrival details and a count/median/p95/max summary on exit, including Ctrl+C or a session error. New segment exports contain callback-arrival, handler, local dispatch, and first-provisional-to-final timing fields. The source-end delay is explicitly an **estimate**, affected by capture startup, source pacing, and offset alignment; it is not a verified translation-latency benchmark. Negative estimates are retained and flagged. See [measurement definitions](docs/setup.md#caption-arrival-time-measurements).

## Intended first release

- Select system audio or a microphone, or replay a WAV file.
- View timestamped Polish and English captions, including clearly marked provisional text.
- Pause/resume and optionally export finalized segments as text or JSONL.
- Use your own Azure Speech **F0** resource, with no automatic paid fallback.

Lectures are the initial priority. Spoken output, speaker identification, SRT subtitles, offline processing, and additional language pairs are later possibilities. No Liltide account or hosted backend is planned.

## Documentation

| Guide | Purpose |
| --- | --- |
| [Branding](docs/branding.md) | Name, voice, colors, typography, and logo usage |
| [Technical specification](docs/technical-spec.md) | Architecture, CLI contract, audio flow, and failure handling |
| [Features and roadmap](docs/roadmap.md) | Scope, milestones, and completion gates |
| [Platform setup](docs/setup.md) | Installation, audio routing, and F0 configuration |
| [Validation](docs/validation.md) | Documentation checks and future application acceptance tests |
| [Provider comparison](docs/providers.md) | Dated comparison and Azure F0 rationale |
| [Third-party licensing](docs/third-party.md) | Dependency and driver licensing boundaries |
| [Agent guidance](AGENTS.md) | Durable instructions for future AI contributors |
| [Project context](CONTEXT.md) | Current progress, evidence, limitations, and next actions |

## Privacy and cost defaults

Cloud mode transmits selected audio to Azure while running. No raw audio or transcript is saved locally by default; text/JSONL exports require explicit flags. Provider-side retention is governed by the provider, not by Liltide's local saving settings.

Only Azure F0 is approved initially. Free allowances are limited; see the [provider policy](docs/providers.md). An application estimate cannot enforce your Azure account's billing tier or account-wide consumption.

## Contributing and license

Read [AGENTS.md](AGENTS.md) and [CONTEXT.md](CONTEXT.md) before making changes. The translation PoC is implemented with offline tests. Caption callback timing is now recorded; reference-aligned accuracy/latency, longer-session reliability, and Windows/Linux validation are deferred future work; opt-in exports, bounded reconnect, and gap records are implemented and offline-tested; live macOS recovery is user-confirmed; measured timing and longer-session validation remain open.

Original project code, documentation, and brand assets are covered by the [MIT License](LICENSE). Third-party software retains its own terms. Liltide is a provisional name; package, domain, and trademark availability are not established.

## Desktop GUI PoC

The GUI provides source/device selection, Start/Stop, Pause/Resume, bilingual or English-only captions, optional text/JSONL exports, and timing details/session summaries. Install the optional GUI dependency in your activated virtual environment:

```console
python -m pip install -e ".[gui]"
liltide-gui
```

Alternatively: `python -m liltide.gui`. Launch from the same terminal where you set `AZURE_SPEECH_KEY` and `AZURE_SPEECH_REGION`; credentials are never entered or saved in the window. Refresh devices, choose your input, confirm that your resource is F0, then click Start translation. Opening the window or refreshing devices makes no cloud calls. See [GUI setup and limitations](docs/setup.md#desktop-gui-poc).

This is an offline-tested desktop PoC; the user reports that it works well on their macOS setup. Detailed live checklist outcomes were not supplied. Pause/resume and display switching are offline-tested and reported working by the user on macOS; individual checklist results and duration were not supplied. GUI exports and timing controls are implemented/offline-tested; live checks of these new additions remain open. Theme override and floating captions are later stages. Existing CLI features remain available.

Use **Pause** to release capture/cloud processing while retaining finalized captions; wait for **Paused**, then **Resume** to start fresh context. Change **Polish + English / English only** at any time to reformat existing and incoming captions without restarting translation.

Before Start, optionally check **Save text** and/or **Save JSONL**, then choose new filenames in an existing folder. Exports include both languages regardless of display. **Show caption timing** adds arrival details and clearly estimated delay; the last-session summary appears after Stop or failure. With exports unchecked, no files are saved.
