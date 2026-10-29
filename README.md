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

`--confirm-f0` asserts you checked the resource tier; Liltide cannot verify it or enforce account-wide billing. Press `p` to pause/resume in an interactive terminal; Ctrl+C stops. Plain/piped output shows finalized captions only. No transcript files are saved. Temporary cloud failures currently stop the session; reconnect and exports are a later milestone.

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

Cloud mode transmits selected audio to Azure while running. No raw audio or transcript is saved locally by default; exports are not implemented yet. Provider-side retention is governed by the provider, not by Liltide's local saving settings.

Only Azure F0 is approved initially. Free allowances are limited; see the [provider policy](docs/providers.md). An application estimate cannot enforce your Azure account's billing tier or account-wide consumption.

## Contributing and license

Read [AGENTS.md](AGENTS.md) and [CONTEXT.md](CONTEXT.md) before making changes. The translation PoC is implemented with offline tests. Next record measured quality/latency and validate reliability; exports and reconnect remain future work.

Original project code, documentation, and brand assets are covered by the [MIT License](LICENSE). Third-party software retains its own terms. Liltide is a provisional name; package, domain, and trademark availability are not established.
