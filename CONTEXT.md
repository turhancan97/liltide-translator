# Liltide project context

Last updated: 2026-10-29 (Europe/Prague).

## Current milestone

Milestone 3 reliability features and stages one through four of the optional Python GUI are implemented and offline-tested. Live macOS network-interruption recovery is user-confirmed and recovery-export integrity is checked; 30-minute, reference accuracy, and Windows/Linux validation are now user-deferred future work. Live macOS translation is user-confirmed; quantitative quality/latency validation remains open. Cross-platform capture/playback validation is still incomplete. The approved scope and durable rules are in [AGENTS.md](AGENTS.md); the milestone sequence is in the [roadmap](docs/roadmap.md).

## Completed

- Approved product direction, branding, CLI requirements, Azure F0-only policy, and documentation structure recorded in linked guides.
- SVG symbol and wordmark variants created for light, dark, and monochrome use.
- MIT license, third-party licensing notes, and ignores for local secrets and private artifacts added.
- Python packaging and `liltide` command implemented: `devices`, local `doctor`, `run --check-audio`, exact-ID source selection, RMS/peak meter, duration/sample-rate controls, and clean shutdown.
- Native capture isolated in a spawned process with bounded queues, stall timeouts, and forced cleanup fallback. Level-check mode remains local-only; translation explicitly enables Azure transmission. No raw audio recording; transcript output requires explicit export flags.
- 219 offline tests cover the capture/translation/recovery pipeline plus callback/handler timing, optional display/exit summaries, negative estimates, nullable fields, process serialization, and clock continuity across contexts.
- Azure Speech adapter (separate native worker), combined Polish recognition/English translation, timestamps, bilingual/English-only captions, paced PCM16 WAV input, and interactive pause/resume implemented.
- Cloud requires local environment credentials and explicit `--confirm-f0`; the agent has not accessed the account/resource or invoked live Azure calls. The user subsequently confirmed a working live session.

## Verification evidence

Documentation and asset QA passed: local links resolved; 8 SVGs parsed and rendered; small-size light/dark/monochrome previews visually inspected; intended text color pairs passed contrast checks. See [validation](docs/validation.md) for procedures, measurements, and the preview. Capture validation: editable install and wheel build passed; 28 tests passed; `pip check` passed. Host: macOS 27.0.1 (Darwin 27.0.0), arm64, Python 3.13.7; Typer 0.27.3, Rich 14.3.4, SoundCard 0.4.6, NumPy 2.5.4. Outside the sandbox, `doctor` discovered four inputs. A virtual-input test detected a synthetic 440 Hz tone at approximately -23 dBFS RMS / -20 dBFS peak, returned to digital silence, and completed a four-second run cleanly. No raw audio was saved or transmitted. The user subsequently reported that the requested real-lecture capture/playback check works. This is user-reported confirmation, not an independently observed rerun; individual check results and duration were not supplied. Physical microphone capture remains unverified. Translation validation: fake-provider/SDK tests pass; the user reports live translation works; quantitative quality/latency and comprehensive failure coverage remain unverified; a live interruption/recovery test is user-confirmed. Current full suite: 219 passed; wheel build and dependency checks pass. Added Azure Speech SDK 1.53.0 and SoXR 1.1.0 in the local environment.

## Capability status

| Capability | Status | Evidence |
| --- | --- | --- |
| Documentation and brand assets | Complete; documentation/asset QA passed | Repository files |
| Audio capture / device diagnostics | Implemented; macOS lecture check confirmed by user | Synthetic virtual-input smoke test plus user report |
| Azure transcription / translation | Implemented; live macOS session user-confirmed | Offline tests plus user report; no independent live rerun |
| WAV replay, resampling, pause/resume | Implemented; offline-tested | Session, source, PCM, and fake-provider tests |
| Text/JSONL exports | Implemented; user-generated files inspected | Matching text/JSONL captions/gaps, UTF-8/schema checked; no private content retained in docs |
| Automatic cloud recovery and gap records | Implemented; live macOS test user-confirmed | Recovery exports match, with captions after gaps and two successful recognizer contexts; exact retry/downtime timing unmeasured |
| Export run metadata | Implemented; offline-tested | Durable session headers, settings distinction, no identifier leakage, fail-fast cleanup; legacy files unchanged |
| Python GUI stages one through four | Implemented; offline-tested | Session controls/view/exports/timing plus themes, brand layout, caption size and keyboard controls; 46 GUI tests. Stages one/two user-confirmed on macOS; stage-three/four live additions unverified |
| Caption arrival instrumentation | Implemented; offline-tested | Callback/handler timestamps, dispatch and provisional-to-final intervals; source-end delay explicitly estimated |
| Accuracy and benchmark latency | Reference evaluation deferred by user | Live timing exports inspected; source-end delay remains estimated |

| Platform | Capture tested | Provider tested | Release support |
| --- | --- | --- | --- |
| Windows | No | No | Target only |
| macOS | Synthetic signal passed; lecture capture/playback user-confirmed; physical mic pending | Live session user-confirmed | macOS PoC only; full release gate open |
| Linux | No | No | Target only |

## Limitations and open verification

- Name provisionally adopted; package, domain, and trademark availability unconfirmed.
- Capture dependencies installed on macOS arm64/Python 3.13.7. Other OS/architectures, Python 3.11 compatibility, physical microphone permissions, and detailed/long-duration lecture validation still require testing. Azure SDK and SoXR are installed/tested locally; Optional PySide6 6.12.0 is installed locally; macOS GUI is reported working by the user; detailed live checks remain open.
- Sandbox discovery returned zero inputs; outside-sandbox discovery found four. Use a normal terminal for hardware checks. Initial live checks found a CoreAudio native-blocksize rejection and a silence-rendering overflow; both corrected and verified on retest.
- User reports the configured live session works. Resource SKU/region/credentials have not been inspected by the agent; F0 remains an operator-confirmed requirement, not an independently verified billing claim.
- Published free allowances are time-sensitive. Provider comparisons establish documented features, not measured Polish quality.
- No current documentation-work blocker. Hardware access for Windows/Linux validation is not established; track it before the cross-platform release gate.

## Next actions

1. GUI stages three/four are implemented and offline-tested. A short user-invoked check of exports/timing, themes, font size, and keyboard controls is available when convenient. Earlier confirmations cover stages one/two only. Floating captions are a possible later task requiring separate authorization.
2. Keep the future validation tasks below deferred until the user is ready; do not repeatedly request them as immediate next steps.
3. Preserve the current evidence limits: macOS PoC/recovery are user-confirmed; reference-aligned accuracy/latency, 30-minute stability, and Windows/Linux support are not established.

## Future validation — user-deferred

Deferred on 2026-10-29 because the user cannot perform these now; no planned execution date.

- **Long-session test:** Caption delay, memory use, pause/resume, exports, and one network interruption during a 30-minute session.
- **Accuracy review:** A few minutes against original audio, including missing words, numbers, and meaning.
- **Windows/Linux validation:** Installation/setup, capture, and playback on both systems with actual environment details recorded.

These tasks remain incomplete and are not blockers for other authorized development. The applicable release and quality claims still require validation. Detailed acceptance procedures remain in [validation](docs/validation.md) and [roadmap](docs/roadmap.md).

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

- 2026-10-29: User reported silence from BlackHole after headphone use. Read-only macOS audio diagnostics outside the sandbox showed output routed directly to Bluetooth headphones, BlackHole selected as default input, and an existing Multi-Output Device not selected for output. This identifies a playback-routing issue; no settings were changed or audio captured. Recommended verifying multi-output membership and selecting it for playback. No device-owner names or private identifiers retained. Fix/test outcome pending user confirmation.

- 2026-10-29: User confirmed the full Wi-Fi interruption/reconnect/resume/Ctrl+C checklist works. Inspected local recovery export pair read-only: 3 segment records, 4 gap records, one export session, 2 successful recognizer contexts, and captions after gaps. Text/JSONL match exactly; UTF-8, schema types, unique segment IDs and valid intervals pass. Gap reasons include connection_failure and network_disconnect. Exact retry count, downtime/detection timing, quality, and 30-minute stability are not established. No transcript content/identifiers copied into docs; no code changes, live agent cloud calls, commit, or push.

- 2026-10-29: User authorized caption arrival-time measurements. SDK callbacks now carry monotonic timestamps; session records relative arrival/handler times, local dispatch, first observed provisional-to-final interval, and explicitly estimated source-end delay. New segment exports add nullable timing fields and text arrival lines; gaps/old files unchanged. `--show-timing` opts into console details and median/nearest-rank p95/max summaries, including failure/Ctrl+C paths. Negative estimates retained/flagged; handler fallback never invents SDK latency. 157 offline tests, wheel build, dependency/whitespace checks passed. No live timing cloud call, private export modification, commit, or push.

- 2026-10-29: Read-only inspection of the user timing export found one valid nonblank final caption with English and provider_callback timing, no gaps/duplicates, and exact timing-equation consistency. Arrival 30.783 s, handling 30.867 s, mapped phrase end 28.551 s: estimated source-end delay 2.232 s and local dispatch 84 ms. Phrase duration 27.120 s; first observed provisional-to-final 27.391 s. This validates populated live timing fields for one sample, not a latency distribution, reference alignment, or 30-minute stability. Private file unchanged/ignored; no transcript content or identifiers copied into docs.

- 2026-10-29: Compared timing exports read-only: previous snapshot retained under export-1 has 1 final (2.232 s estimated source-end delay, 84 ms dispatch, 27.120 s phrase). Current exports snapshot has 4 callback-timed finals, no blanks/duplicates/gaps, matching timing equations and ordered valid intervals. Current medians: estimated source-end delay 1.226 s, dispatch 37.5 ms, provisional-to-final 5.3715 s, phrase length 5.760 s; longest phrase 20.880 s. Speech text and covered durations differ, and segmentation setting is not stored, so no controlled causal improvement or benchmark claim. Files unchanged; no transcript text/IDs copied into docs.

- 2026-10-29: User confirmed repeating the same recording; compared current exports1 versus exports timing files read-only. Coverage 30.20/30.54 s, 73/72 source words, normalized token similarity about 97.9% (not accuracy). Exports1: 2 finals, estimated-delay median 3.259 s, provisional-to-final median 14.3495 s, phrase median/max 13.780/13.920 s, dispatch median 51.5 ms. Exports: 4 finals, estimated-delay median 1.4015 s, provisional-to-final median 6.1415 s, phrase median/max 6.560/8.520 s, dispatch median 48 ms. Both have English for every final and no gaps/blanks/duplicate IDs; timing equations pass. Minor source wording/coverage differences remain, including a short phrase absent from the exports run. Settings-to-file mapping requested because not stored in exports; do not infer it from folder names. No private transcript content retained, files unchanged.

- 2026-10-29: User confirmed that the compared `exports/timing-test.jsonl` run used `--segmentation-silence-ms 300`. This attributes the more responsive current sample (4 finals; 1.4015 s median estimated delay; 6.1415 s provisional-to-final) to that configured run. The user has not explicitly confirmed the `exports1` setting; do not label it default yet. Keep service default unchanged pending repeated accuracy/coverage checks.

- 2026-10-29: User explicitly deferred the 30-minute stability test, reference-audio accuracy review, and Windows/Linux capture/setup validation because they cannot perform them now. Added future-work entries with no schedule; retained unverified status and release/quality evidence requirements. No tests run or marked complete.

- 2026-10-29: User authorized run-configuration export metadata. New CLI text/JSONL exports start with one durable session header recording app version, provider/languages, input type, and requested/default segmentation. Headers exclude credentials, region, file/device identifiers, and environment values; older exports are unchanged. Header failures close files and prevent capture/provider startup. 173 offline tests passed, including fake CLI cases for all three input types and default/300 ms settings, header visibility, no default persistence, failure cleanup, and reconnect continuity. Wheel build, dependency and whitespace checks passed. No live cloud calls, private export changes, commit, or push.

- 2026-10-29: User authorized committing and pushing pending caption timing instrumentation, export run metadata, and associated documentation/future-validation updates. Reviewed the selected source/tests/docs; 173 offline tests and whitespace checks passed. Private exports and local credentials remain excluded. No live cloud tests performed.

- 2026-10-29: User authorized stage one of the PySide6 GUI PoC. Added optional GUI extra/entry point, background device discovery/session worker, F0/environment gates, bilingual finalized/provisional display, bounded/coalesced UI delivery, and cooperative Stop/close/startup/reconnect cancellation using the shared session core. Installed PySide6 6.12.0 locally and updated third-party notices. 183 offline tests passed (10 GUI checks), editable install/wheel/dependency/whitespace checks passed; offscreen empty-window layout rendered and visually inspected. No live Azure/capture run, transcript persistence, private export modification, commit, or push. Pause/export/theme controls and live GUI validation remain open; deferred release checks are unchanged.

- 2026-10-29: User reported the GUI “works well” and authorized committing/pushing the stage-one implementation and documentation. Recorded macOS GUI operation as user-confirmed, without inferring individual checklist outcomes, session duration, release validation, or independent agent live tests. Private exports/credentials remain excluded.

- 2026-10-29: User authorized GUI stage two. Added Pause/Resume through the existing session pause path, structured lifecycle notifications/state label, duplicate-transition guards, and bilingual/English-only switching for history and provisional captions without restarting providers. Finalized text remains in memory across pause/resume/Stop. 189 offline tests passed (16 GUI tests), with resource release/no activity while paused, fresh contexts, final drain/history, paused Stop/close, view/missing translation/markup, fatal resume, and reconnect guards covered. Wheel/dependency/link/whitespace checks passed; synthetic bilingual/English paused layouts rendered and visually inspected. No live Azure/capture calls, private export edits, commit, or push. Stage-two live checks and later GUI stages remain open; deferred validation unchanged.

- 2026-10-29: User reported the stage-two GUI update “works well” and authorized committing/pushing it. Recorded macOS stage-two operation as user-confirmed without inferring individual checklist outcomes or duration. Reviewed source/tests/docs; private exports and credentials remain excluded. No independent agent live cloud test followed.

- 2026-10-29: User authorized GUI stage three. Added independent opt-in text/JSONL destinations with browse controls locked for the run, worker-owned durable exporter with metadata/finals/gaps, display-only timing toggle, and last-session received-caption/timing summaries through errors. Existing exporter/schema/calculations reused; no default files or summary sidecars. Fixed a Qt shutdown issue exposed by new widgets by replacing a window-retaining browse lambda with a bound slot. 203 offline tests passed (30 GUI tests), with independent/both exports, pause/recovery continuity, preflight/header/write failures, English-view bilingual persistence, no default saving, timing/negative/unavailable summaries, and browse selection/cancel covered. Wheel/dependency/link/whitespace checks passed; synthetic export/timing layout rendered and visually inspected at 900×800. No live cloud/capture calls, private export edits, commit, or push; stage-three live checks and later styling remain open. Deferred validation unchanged.

- 2026-10-29: User authorized committing/pushing GUI stage-three exports, timing display, last-session summaries, and associated tests/docs. Reviewed the selected source/tests/docs and exclusions; private exports and credentials remain excluded. This push request is not a live-test confirmation; stage-three live checks remain open.

- 2026-10-29: User authorized GUI branding/usability stage four. Added approved palette/original packaged symbol, System/Light/Dark window themes, grouped splitter/scrollable panes, 12–26 pt caption sizing (16 default), label buddies/Tab order, and guarded window shortcuts. Theme/font changes preserve worker/history/export configuration; no settings persistence or OS appearance changes. 209 offline tests passed (36 GUI checks), including simulated System notifications/manual override, appearance during fake translation, compact scrolling, keyboard Start/Pause/Stop/Tab, and normal-text/selection contrast. Synthetic light/dark 1100×820 and compact 760×600/26 pt renders visually inspected; wheel resources, dependency/link/whitespace checks passed. No live cloud/capture, private export edits, commit, or push. Real OS theme/accessibility and stages three/four live checks remain open; floating captions and deferred validation are unchanged.

- 2026-10-29: User reported clipped text when opening Theme/Caption size and other dropdowns. Replaced native combo-menu delegates with standard list views/delegates, synchronized popup fonts, sized menus to text/screen limits, padded rows, and widened compact Theme/Caption size controls. Initial offscreen native row geometry exceeded popup width; updated rows fit their viewports. 219 offline tests passed (46 GUI tests), including open-popup text/row bounds and mouse selection for all five selectors in both themes at 18 pt control font/compact width. Light/dark open menus rendered and visually inspected; build/dependency/whitespace checks passed. No cloud/capture call, private export edits, commit, or push. Actual desktop confirmation of the clipping fix remains open.

- 2026-10-29: User authorized committing/pushing pending stage-four branding/usability and dropdown clipping fixes, then implementing floating captions. Reviewed source/tests/docs and resource packaging; private exports/credentials remain excluded. Earlier “good thanks” acknowledges the fix, without supplying individual desktop checklist results. No new agent live audio/cloud test.
