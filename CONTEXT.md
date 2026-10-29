# Liltide project context

Last updated: 2026-10-29 (Europe/Prague).

## Current milestone

Milestone 3: exports, bounded recovery, and gap records implemented and offline-tested. Live network-interruption and 30-minute validation remain open. Live macOS translation is user-confirmed; quantitative quality/latency validation remains open. Cross-platform capture/playback validation is still incomplete. The approved scope and durable rules are in [AGENTS.md](AGENTS.md); the milestone sequence is in the [roadmap](docs/roadmap.md).

## Completed

- Approved product direction, branding, CLI requirements, Azure F0-only policy, and documentation structure recorded in linked guides.
- SVG symbol and wordmark variants created for light, dark, and monochrome use.
- MIT license, third-party licensing notes, and ignores for local secrets and private artifacts added.
- Python packaging and `liltide` command implemented: `devices`, local `doctor`, `run --check-audio`, exact-ID source selection, RMS/peak meter, duration/sample-rate controls, and clean shutdown.
- Native capture isolated in a spawned process with bounded queues, stall timeouts, and forced cleanup fallback. Level-check mode remains local-only; translation explicitly enables Azure transmission. No raw audio recording; transcript output requires explicit export flags.
- 142 offline tests cover capture/translation, exports, blank filtering, segmentation configuration, structured failure policy, bounded backoff, fresh audio/context recovery, and gap persistence/cleanup.
- Azure Speech adapter (separate native worker), combined Polish recognition/English translation, timestamps, bilingual/English-only captions, paced PCM16 WAV input, and interactive pause/resume implemented.
- Cloud requires local environment credentials and explicit `--confirm-f0`; the agent has not accessed the account/resource or invoked live Azure calls. The user subsequently confirmed a working live session.

## Verification evidence

Documentation and asset QA passed: local links resolved; 8 SVGs parsed and rendered; small-size light/dark/monochrome previews visually inspected; intended text color pairs passed contrast checks. See [validation](docs/validation.md) for procedures, measurements, and the preview. Capture validation: editable install and wheel build passed; 28 tests passed; `pip check` passed. Host: macOS 27.0.1 (Darwin 27.0.0), arm64, Python 3.13.7; Typer 0.27.3, Rich 14.3.4, SoundCard 0.4.6, NumPy 2.5.4. Outside the sandbox, `doctor` discovered four inputs. A virtual-input test detected a synthetic 440 Hz tone at approximately -23 dBFS RMS / -20 dBFS peak, returned to digital silence, and completed a four-second run cleanly. No raw audio was saved or transmitted. The user subsequently reported that the requested real-lecture capture/playback check works. This is user-reported confirmation, not an independently observed rerun; individual check results and duration were not supplied. Physical microphone capture remains unverified. Translation validation: fake-provider/SDK tests pass; the user reports live translation works; quantitative quality, latency, and failure behavior remain unverified. Current full suite: 142 passed; wheel build and dependency checks pass. Added Azure Speech SDK 1.53.0 and SoXR 1.1.0 in the local environment.

## Capability status

| Capability | Status | Evidence |
| --- | --- | --- |
| Documentation and brand assets | Complete; documentation/asset QA passed | Repository files |
| Audio capture / device diagnostics | Implemented; macOS lecture check confirmed by user | Synthetic virtual-input smoke test plus user report |
| Azure transcription / translation | Implemented; live macOS session user-confirmed | Offline tests plus user report; no independent live rerun |
| WAV replay, resampling, pause/resume | Implemented; offline-tested | Session, source, PCM, and fake-provider tests |
| Text/JSONL exports | Implemented; offline-tested | Per-final-segment flush/fsync, opt-in only; interruption and failure tests pass |
| Automatic cloud recovery and gap records | Implemented; offline-tested | Three retries/run at 1/2/4 seconds; known fatal failures stop; live recovery unverified |
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

1. Manually validate recovery in an explicitly invoked F0 session using fresh filenames and the brief interruption steps in docs/setup.md. No live cloud calls or network changes were run for this implementation.
2. Run Windows/Linux capture smoke tests and record actual versions/architectures; do not mark milestone 1's all-platform gate complete until these pass.
3. Record session duration and reviewed quality/latency before marking the full milestone 2 validation gate complete. Exports and bounded recovery are implemented; live interruption and long-session validation remain milestone 3 work.

## Progress log

- 2026-10-28: User approved Liltide branding/documentation plan, Azure F0 only, CLI before Python GUI, and cross-platform validation before v1. Created documentation and original SVG assets; local-link, SVG, visual, and contrast checks passed. No application, drivers, or cloud resources created.

- 2026-10-28: User authorized capture CLI implementation. Added packaging, local commands, bounded level-only capture, and tests; 28 tests/build/dependency checks passed. macOS virtual capture detected a synthetic tone and silence; no cloud calls, driver installs, or private recordings. Cross-platform routing gate remains open.

- 2026-10-28: User replied “yes it works” to the real-lecture capture/playback checklist. Recorded macOS lecture capture/playback as user-confirmed; duration and individual checklist outcomes not supplied. Windows/Linux and cloud validation remain open.

- 2026-10-28: User authorized the translation PoC. Implemented Azure worker, SoXR PCM normalization, WAV pacing, bilingual captions, and pause/resume. 55 offline tests, wheel build, and dependency checks passed. No live cloud call or resource provisioning; awaiting operator-configured F0 validation.

- 2026-10-28: After Azure key/setup guidance, user reported “IT works perfectly now.” Recorded the live macOS translation path as user-confirmed. No independent cloud run, quantitative measurements, failure testing, or resource-tier inspection followed.

- 2026-10-29: User requested local Git tracking. Initialized repository on `main`; existing author identity is configured. Checked candidate files and ignore rules: credentials, recordings, exports, virtual environment, caches, and build artifacts are excluded. No remote configured or publication performed.

- 2026-10-29: User published the project and requested GitHub metadata updates. Remote: https://github.com/turhancan97/liltide-translator. Set and verified the description and ten topics (Python/CLI, speech recognition/translation, system audio, captions, Polish/English). No source push performed in this task.

- 2026-10-29: User approved replacement brand colors #3a7eab, #cf4832, #d1d3d4. Refreshed light/dark and monochrome logos, README banner, palette tokens, and clearly labeled light/dark caption concepts. Rendered SVGs and visually checked large/small variants; documented contrast restrictions. Prior teal palette is superseded. No app behavior changes or remote push.

- 2026-10-29: User approved committing and pushing the branding refresh to the configured GitHub remote. Reviewed branding/docs/assets only; local link, SVG, contrast, render, and whitespace checks passed.

- 2026-10-29: User authorized opt-in finalized text/JSONL exports. Added exclusive UTF-8 files, a presentation-independent export sink, flush/fsync per segment, no default files, and fail-fast persistence errors. 75 offline tests, wheel build, dependency checks, CLI help, and whitespace checks passed. Abrupt child-process exit preserved a completed JSONL record. No live cloud call, source commit, or push in this task.

- 2026-10-29: Reviewed user-generated local text/JSONL exports without modifying them. Five records (four nonempty) matched exactly across formats; UTF-8, schema, unique segment IDs, and ordered/non-overlapping timestamps passed. One empty finalized record at 0–15 seconds exposed the provider guard accepting a nonempty translation dictionary with empty values (provider.py on_result). Two speech segments span 24.28 and 26.80 seconds; latency cannot be measured from export timestamps alone. Audio reference and qualified review are still needed for transcription/translation accuracy. Export files remain ignored; no transcript text or personal identifiers copied into project docs. Subsequently fixed blank-event filtering; see the next progress entry.

- 2026-10-29: User requested fixes after export review. Filtered blank/whitespace events at provider, session (before ID deduplication), and export boundaries; blank English normalizes to unavailable while preserving meaningful source-only captions. Added optional `--segmentation-silence-ms` (100–5000, default service behavior) for a controlled long-phrase experiment, not a guaranteed latency fix. 95 offline tests, wheel build, dependency and whitespace checks passed. No live cloud comparison, private export changes, transcript post-editing, commit, or push.

- 2026-10-29: Reviewed a second user-generated export pair without modification. Eight records, zero blank records; exact text/JSONL match, valid UTF-8/schema, one session, unique segment IDs, and chronological/non-overlapping timestamps. First segment spans 21.92 seconds; remaining seven span 0.88–4.60 seconds (overall median 3.22 seconds). Blank-event issue is absent in this sample. Different input/unknown invocation prevents attributing shorter segments to the tuning flag; durations are not latency measurements. Some idiomatic translation remains overly literal. No private transcript content copied into docs; files remain ignored.

- 2026-10-29: User authorized connection recovery and gap records. Added structured Azure failures, queued-final preservation, run-wide three-retry budget (1/2/4 seconds), fresh live/SDK contexts, conservative gap checkpoints/closures in terminal and both export formats, file-cursor retention, and fatal/persistence failure stops. 142 offline tests, wheel build, dependency/whitespace checks passed. No live cloud/network test, private export changes, commit, or push; live SDK behavior and 30-minute validation remain open.

- 2026-10-29: User approved committing and pushing the pending finalized exports, blank-event fix, optional segmentation tuning, bounded recovery, gap records, and associated tests/docs. Private exports remain ignored; latest verification is 142 passing offline tests plus build/dependency checks.
