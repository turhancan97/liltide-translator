# Liltide project context

Last updated: 2026-10-29 (Europe/Prague).

## Current milestone

Milestone 2: translation PoC implemented and offline-tested; live macOS translation is user-confirmed; quantitative quality/latency validation remains open. Cross-platform capture/playback validation is still incomplete. The approved scope and durable rules are in [AGENTS.md](AGENTS.md); the milestone sequence is in the [roadmap](docs/roadmap.md).

## Completed

- Approved product direction, branding, CLI requirements, Azure F0-only policy, and documentation structure recorded in linked guides.
- SVG symbol and wordmark variants created for light, dark, and monochrome use.
- MIT license, third-party licensing notes, and ignores for local secrets and private artifacts added.
- Python packaging and `liltide` command implemented: `devices`, local `doctor`, `run --check-audio`, exact-ID source selection, RMS/peak meter, duration/sample-rate controls, and clean shutdown.
- Native capture isolated in a spawned process with bounded queues, stall timeouts, and forced cleanup fallback. Level-check mode remains local-only; translation explicitly enables Azure transmission. No persistent audio/transcript output.
- 55 offline tests cover capture, stateful SoXR normalization, WAV pacing, fake Azure callbacks, F0/credential preflight, captions, pause/resume, cleanup, queue limits, and startup/drain timeouts.
- Azure Speech adapter (separate native worker), combined Polish recognition/English translation, timestamps, bilingual/English-only captions, paced PCM16 WAV input, and interactive pause/resume implemented.
- Cloud requires local environment credentials and explicit `--confirm-f0`; the agent has not accessed the account/resource or invoked live Azure calls. The user subsequently confirmed a working live session.

## Verification evidence

Documentation and asset QA passed: local links resolved; 8 SVGs parsed and rendered; small-size light/dark/monochrome previews visually inspected; intended text color pairs passed contrast checks. See [validation](docs/validation.md) for procedures, measurements, and the preview. Capture validation: editable install and wheel build passed; 28 tests passed; `pip check` passed. Host: macOS 27.0.1 (Darwin 27.0.0), arm64, Python 3.13.7; Typer 0.27.3, Rich 14.3.4, SoundCard 0.4.6, NumPy 2.5.4. Outside the sandbox, `doctor` discovered four inputs. A virtual-input test detected a synthetic 440 Hz tone at approximately -23 dBFS RMS / -20 dBFS peak, returned to digital silence, and completed a four-second run cleanly. No raw audio was saved or transmitted. The user subsequently reported that the requested real-lecture capture/playback check works. This is user-reported confirmation, not an independently observed rerun; individual check results and duration were not supplied. Physical microphone capture remains unverified. Translation validation: fake-provider/SDK tests pass; the user reports live translation works; quantitative quality, latency, and failure behavior remain unverified. Current full suite: 55 passed; wheel build and dependency checks pass. Added Azure Speech SDK 1.53.0 and SoXR 1.1.0 in the local environment.

## Capability status

| Capability | Status | Evidence |
| --- | --- | --- |
| Documentation and brand assets | Complete; documentation/asset QA passed | Repository files |
| Audio capture / device diagnostics | Implemented; macOS lecture check confirmed by user | Synthetic virtual-input smoke test plus user report |
| Azure transcription / translation | Implemented; live macOS session user-confirmed | Offline tests plus user report; no independent live rerun |
| WAV replay, resampling, pause/resume | Implemented; offline-tested | Session, source, PCM, and fake-provider tests |
| Exports and automatic cloud recovery | Planned | Fail-fast PoC only; no exports/reconnect yet |
| Python GUI | Deferred | Roadmap only |
| Accuracy and latency | Unmeasured | No recordings evaluated |

| Platform | Capture tested | Provider tested | Release support |
| --- | --- | --- | --- |
| Windows | No | No | Target only |
| macOS | Synthetic signal passed; lecture capture/playback user-confirmed; physical mic pending | Live session user-confirmed | macOS PoC only; full release gate open |
| Linux | No | No | Target only |

## Limitations and open verification

- Name provisionally adopted; package, domain, and trademark availability unconfirmed.
- Capture dependencies installed on macOS arm64/Python 3.13.7. Other OS/architectures, Python 3.11 compatibility, physical microphone permissions, and detailed/long-duration lecture validation still require testing. Azure SDK and SoXR are installed/tested locally; GUI dependency is not installed.
- Sandbox discovery returned zero inputs; outside-sandbox discovery found four. Use a normal terminal for hardware checks. Initial live checks found a CoreAudio native-blocksize rejection and a silence-rendering overflow; both corrected and verified on retest.
- User reports the configured live session works. Resource SKU/region/credentials have not been inspected by the agent; F0 remains an operator-confirmed requirement, not an independently verified billing claim.
- Published free allowances are time-sensitive. Provider comparisons establish documented features, not measured Polish quality.
- No current documentation-work blocker. Hardware access for Windows/Linux validation is not established; track it before the cross-platform release gate.

## Next actions

1. Live macOS translation is user-confirmed. Next planned coding milestone: reliability and opt-in exports; await authorization before starting it.
2. Run Windows/Linux capture smoke tests and record actual versions/architectures; do not mark milestone 1's all-platform gate complete until these pass.
3. Record session duration and reviewed quality/latency before marking the full milestone 2 validation gate complete. Exports, automatic reconnect/retries, and long-session reliability remain milestone 3.

## Progress log

- 2026-10-28: User approved Liltide branding/documentation plan, Azure F0 only, CLI before Python GUI, and cross-platform validation before v1. Created documentation and original SVG assets; local-link, SVG, visual, and contrast checks passed. No application, drivers, or cloud resources created.

- 2026-10-28: User authorized capture CLI implementation. Added packaging, local commands, bounded level-only capture, and tests; 28 tests/build/dependency checks passed. macOS virtual capture detected a synthetic tone and silence; no cloud calls, driver installs, or private recordings. Cross-platform routing gate remains open.

- 2026-10-28: User replied “yes it works” to the real-lecture capture/playback checklist. Recorded macOS lecture capture/playback as user-confirmed; duration and individual checklist outcomes not supplied. Windows/Linux and cloud validation remain open.

- 2026-10-28: User authorized the translation PoC. Implemented Azure worker, SoXR PCM normalization, WAV pacing, bilingual captions, and pause/resume. 55 offline tests, wheel build, and dependency checks passed. No live cloud call or resource provisioning; awaiting operator-configured F0 validation.

- 2026-10-28: After Azure key/setup guidance, user reported “IT works perfectly now.” Recorded the live macOS translation path as user-confirmed. No independent cloud run, quantitative measurements, failure testing, or resource-tier inspection followed.

- 2026-10-29: User requested local Git tracking. Initialized repository on `main`; existing author identity is configured. Checked candidate files and ignore rules: credentials, recordings, exports, virtual environment, caches, and build artifacts are excluded. No remote configured or publication performed.
