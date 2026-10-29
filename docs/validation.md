# Validation

## Documentation and asset checks

For this milestone, check local Markdown links/images resolve, planned CLI examples agree across guides, SVG XML parses, and logo variants render without clipping. Render each variant on its intended surface and inspect symbols at 24/32 px and wordmarks at 160 px. Calculate WCAG relative-luminance contrast for approved text/background pairs and retain the results below. Do not imply these checks validate application behavior.

### Results — 2026-10-28

Documentation/asset QA passed:

- All 40 local Markdown/image links in the initial guides resolved; final link validation also covers the added preview links.
- All 8 SVGs parsed as XML and contain accessible titles/descriptions, with no embedded raster images.
- Rendered all variants using `rsvg-convert`; visually inspected 24/32 px symbols and 160/360 px wordmarks on light/slate backgrounds. No clipping observed; 24 px symbols and 160 px wordmarks remain readable. [Rendered contact sheet](../assets/brand/preview.png).
- Reviewed CLI examples, free-only policy, planned/verified distinctions, and roadmap consistency. No application code, cloud resources, drivers, or live API requests were created.

Historical original-palette results below are superseded by the 2026-10-29 brand refresh. Contrast was calculated using WCAG sRGB linearization and relative luminance (ratios rounded to two decimals):

| Foreground | Background | Ratio | Normal text decision |
| --- | --- | --- | --- |
| Deep teal `#0F766E` | Light `#F8FAFC` | 5.23:1 | Approved |
| Bright teal `#2DD4BF` | Slate `#0F172A` | 9.59:1 | Approved |
| Slate `#0F172A` | Light `#F8FAFC` | 17.06:1 | Approved; reverse pairing also approved |
| Muted gray `#64748B` | Light `#F8FAFC` | 4.55:1 | Approved; avoid opacity reduction |
| Bright teal `#2DD4BF` | Light `#F8FAFC` | 1.78:1 | Not approved |
| Deep teal `#0F766E` | Slate `#0F172A` | 3.26:1 | Not approved for normal text |
| Muted gray `#64748B` | Slate `#0F172A` | 3.75:1 | Not approved for normal text |

Monochrome black on light and white on slate also exceed 4.5:1. Ratios apply to these exact opaque surfaces; recalculate for other combinations. Translation acceptance tests have not run. See capture results below for the limited macOS evidence; Windows/Linux and full system playback remain unverified.

## Capture implementation results — 2026-10-28

- Environment: macOS 27.0.1 / Darwin 27.0.0, arm64, Python 3.13.7. Tested Typer 0.27.3, Rich 14.3.4, SoundCard 0.4.6, NumPy 2.5.4.
- Editable installation and `liltide --version` passed. `python -m pytest -q`: **28 passed**. `python -m hatchling build -t wheel` produced a wheel; `python -m pip check` found no broken requirements. Build artifacts remain ignored under `dist/`.
- Tests use fake devices and synthetic sample arrays; no hardware/cloud required. Include exact-ID/source validation, Windows mono rejection, multichannel capture arguments, anti-phase signal levels, silence/clipping/non-finite samples, plain output, explicit rejection of future commands, generator closure on Ctrl+C, and a simulated stuck-reader cleanup test.
- `doctor` discovered zero inputs in the sandbox and four outside it. Native input access must be tested outside restricted environments. Device names/IDs are not retained in this record.
- Live level-only capture on a virtual macOS input passed. Generated a 2-second, 440 Hz stereo tone of amplitude 0.1 through the corresponding virtual output while the CLI ran for 4 seconds: observed approximately -23 dBFS RMS and -20 dBFS peak, digital silence before/after, and clean timed completion. No microphone input, raw recording files, or cloud calls used.
- Live testing exposed rejection of an oversized CoreAudio hardware buffer and silence-to-meter integer overflow. Fixed by leaving native buffer selection to the backend and clamping meter values before conversion. Successful live retest and regression tests recorded above.
- User follow-up: “yes it works” in response to the real-lecture capture/playback checklist. Record normal macOS lecture routing/playback as user-confirmed; no independent rerun, duration, or individual checklist results were provided.
- Not verified: physical microphones, Windows/Linux hardware, live Ctrl+C during stalled native capture, long sessions, translated captions, accuracy, or latency. No all-platform support claim follows from these macOS results.

## Translation PoC results — 2026-10-28

- Current full suite: **55 passed** with `python -m pytest -q`; wheel build and `pip check` passed. Same macOS arm64/Python 3.13.7 environment as capture; installed Azure Speech SDK 1.53.0 and SoXR 1.1.0.
- Offline tests cover split-vs-continuous PCM conversion at 16/44.1/48 kHz, clipping/non-finite handling, WAV format checks and pacing, Unicode/tick-to-millisecond event conversion, final deduplication, missing translations, plain/English-only rendering, file/live pause lifecycle, startup failure cleanup, and worker startup/drain timeouts.
- Fake SDK tests verify PCM format, Polish source and English target settings, provisional/final callbacks, authentication cancellation, and EOF draining. The actual SDK is imported locally, but constructors/recognition operations are replaced; no network requests occur.
- A full CLI session from synthetic WAV through a fake provider produced English captions without saving transcripts. F0 confirmation and credential preflight fail before capture/cloud use when absent. Raw capture/provider overflow tests produce explicit gap errors; no automatic paid fallback or reconnect exists.
- Only application queues are bounded: up to one second of raw capture plus up to one second of PCM awaiting SDK acceptance. SDK internal copies and network delivery are not measured by that limit.
- Live Azure authentication, quota response, translations, disconnect timing, long-session behavior, interactive terminal pause restoration on each OS, quality, and latency remain **unverified**. No credentials or Azure resource were inspected or provisioned, and no live test was invoked.

## Application test strategy (future)

Use deterministic fake audio sources/providers for normal-path and failure tests. Default tests must not require credentials or contact Azure. Explicitly invoked live tests require an operator-confirmed F0 resource and a short non-private recording. Never retry quota failures by changing tiers. Record OS, architecture, Python/dependency versions, device/backend, network conditions, test duration, and observed outcomes. Redact secrets and personal identifiers.

| Scenario | Required behavior/evidence |
| --- | --- |
| Device enumeration/selection | Correct source types; invalid/missing selection fails clearly; no silent microphone fallback |
| System audio on each OS | Reference clip captured while still audible; playback stop changes level; record actual routing |
| Microphone and WAV | Both use shared processing; WAV replay is paced, format/rate/channel handling checked |
| Silence | No fabricated finalized captions in a controlled silence fixture; no growing buffers |
| Provisional/final events | Provisional row replaced, finalized segments appear/export once and remain ordered |
| Unicode | Polish diacritics survive terminal and UTF-8 exports; include `Zażółć gęślą jaźń` in a synthetic fixture |
| Pause/resume | Capture/transmission stop, unfinished provisional text clears, completed text persists, fresh context resumes; file cursor pauses |
| Device removal | Actionable error; resources released; no indefinite retry or accidental source switch |
| Invalid credentials | Clear redacted error, no repeated authentication retry, no credential leakage |
| Quota exhausted | Session stops; no paid fallback/resource switch; already finalized text retained |
| Network interruption | Visible bounded retry; at most 2 seconds queued PCM; discarded audio reported as gaps; no unbounded backlog |
| Export opt-in | No default files/raw audio; text/JSONL only when requested, existing files refused, finalized segments flushed |
| Export write failure | Explicit failure and stopped session; no silent persistence loss |
| Ctrl+C / EOF | Bounded drain, clean resource release, final exports flushed, terminal restored; WAV ends cleanly |
| Non-interactive / no color | Readable finalized output and status without escape sequences; no dependence on keyboard controls |
| 30-minute lecture | No unbounded queues or growing delay; record resource trends, gap/retry counts, output completeness, and shutdown behavior |

## Quality and latency evaluation

Use a representative, consented or openly licensed Polish lecture recording with a human-reviewed reference transcript. Keep personal audio outside version control; record provenance/license, duration, content domain, and any preprocessing. Do not select only unusually easy phrases.

Report recognition word error rate with documented normalization and counts of substitutions/deletions/insertions. Separately review English meaning against the Polish source using a competent Polish/English reviewer, especially names, numbers, negation, terminology, and omissions. Record actual reviewed segments and errors without treating a transcript metric as translation quality. If no qualified reviewer is available, mark translation quality unresolved.

Annotate phrase-end times in the source recording. For paced replay, align the playback clock with a monotonic arrival timestamp for each finalized translation. Compute delay as final translation arrival minus the corresponding phrase end, and report sample count, median, p95, and maximum. Keep first provisional display latency separate. Include segmentation/alignment choices; do not subtract provider processing time or selectively remove slow segments.

**Target, not result:** median finalized translation delay at or below 5 seconds on the evaluation recording. If missed, report the measurements and address the issue before claiming the performance target is met. No numerical accuracy threshold is established yet; report measured recognition errors and reviewed translation limitations honestly.

## Release gate

Real system-audio capture and F0 provider smoke tests must be recorded for Windows, macOS, and Linux, alongside the fake-provider suite and the 30-minute test. A passing macOS run or mocked CI does not establish other-platform support. Record actual tested versions/architectures, unresolved limitations, and quality/latency evidence before calling v1 complete. Hardware access and reviewer availability are dependencies, not assumed completed work.


## User-reported live translation — 2026-10-28

After Azure key/resource setup guidance, the user reported: “IT works perfectly now.” Record the end-to-end macOS translation PoC as user-confirmed working. No independent live rerun was performed. Session duration, source content, input mode, pause/resume outcomes, timing measurements, and accuracy annotations were not supplied. F0 SKU/configuration has not been inspected by the agent. This report does not establish perfect accuracy, a latency benchmark, failure recovery, or Windows/Linux support.


## Brand refresh — 2026-10-29

User-selected colors: blue `#3a7eab`, red `#cf4832`, gray `#d1d3d4`. Supporting neutrals: ink `#17212b`, white `#ffffff`. This palette supersedes the original teal identity. Refreshed all 8 logo variants; added a README banner, palette tokens, and a brand board with explicitly labeled caption concepts. No terminal behavior or shipped GUI changed.

Rendered all SVGs using `rsvg-convert`. Visually inspected the banner and 1100×900 brand board for spacing/clipping and the logo contact sheet at 24/32 px symbols and 160/360 px wordmarks on white/ink backgrounds. All remained readable with no clipping. [Brand board preview](../assets/brand/brand-board.png) and [logo contact sheet](../assets/brand/preview.png).

WCAG sRGB contrast ratios, rounded to two decimals:

| Pair | Ratio | Use |
| --- | --- | --- |
| Ink / white | 16.29:1 | Normal text |
| Gray / ink | 10.85:1 | Normal text |
| Blue / white | 4.42:1 | Large text/meaningful graphics; not normal text |
| Red / white | 4.54:1 | Normal text, without opacity reduction |
| Blue / ink | 3.69:1 | Large text/meaningful graphics; not normal text |
| Red / ink | 3.59:1 | Large text/meaningful graphics; not normal text |
| Blue / gray | 2.94:1 | Decorative only |
| Red / gray | 3.02:1 | Meaningful graphics/large text only |
| Gray / white | 1.50:1 | Decorative only |

Small text in the delivered banner/board uses ink on white or gray on ink. States use explicit text labels. The gray separators are decorative; meaningful caption boundaries use blue on white/ink. These are asset/document checks, not new application-test or accessibility claims about the future GUI.


## Transcript exports — 2026-10-29

Current full suite: **75 passed** using `python -m pytest -q`; wheel build, `pip check`, CLI help, and `git diff --check` passed. Existing macOS arm64/Python 3.13.7 environment; no dependencies added and no live cloud request invoked.

New tests cover independent/both export flags, no default persistence, UTF-8 Polish text, escaped embedded newlines in JSONL, null translations, pre-close visibility, provisional exclusion, exclusive filenames, duplicate destinations, missing parents, partial-open rollback, and write/flush/fsync failures. Session tests cover final deduplication during EOF/shutdown, saved data through Ctrl+C and provider failure, pause/resume session/segment IDs, and source/provider cleanup on sink failures including final drain. Full fake-provider CLI tests verify English-only display still exports both languages and export preflight rejects existing files before cloud initialization.

An isolated child process wrote and synced a JSONL record, then used `os._exit(7)` without context cleanup; the completed record remained readable in the parent. This verifies abrupt-process-exit survival of completed writes, not power-loss/hardware guarantees or preservation of unfinished captions. Filesystem failures may leave an incomplete final record; paired formats are not transactional.

Live Azure export sessions, other-platform filesystem behavior, and 30-minute reliability remain unverified. Gap/reconnect records remain deferred; current exports contain finalized segment records only.


## User export inspection — 2026-10-29

Read the user-generated local text/JSONL pair without modifying it. Five finalized records matched exactly across formats, including text and start/end timestamps. JSONL parses cleanly with expected fields, one session ID, unique segment IDs, chronological/non-overlapping intervals, and no Unicode replacement characters. Both files end with a newline and are excluded by Git ignores.

One record has empty source and translation text (0–15 seconds). The provider callback currently tests dictionary truthiness rather than translation-content truthiness, allowing an empty translation value to produce a blank caption. This is a confirmed code-path issue to fix; exports faithfully preserved the supplied event. Four records contain speech text, including segments spanning 24.28 and 26.80 seconds. These durations do not measure end-to-end delay. Some source/translated sentences are disfluent, but no reference audio/transcript was supplied, so recognition accuracy and precise error attribution remain unresolved. No private transcript content or session/device identifiers are retained in this record.


## Export-review fixes — 2026-10-29

Current full suite: **95 passed**. Wheel build, dependency check, and whitespace check passed. Fixed the blank-event issue identified in user exports: fake Azure events with empty/whitespace values or absent translation maps produce no caption; defensive session/export filters also reject blanks before deduplication. Regression tests ensure a blank final cannot consume a segment ID before a meaningful result, source-only captions remain, and blank English values become unavailable/JSON `null`.

Optional `--segmentation-silence-ms` is validated at the CLI/config boundary and passed to the Azure property in fake-SDK tests, including values 300 and 5000; omission leaves the service setting unchanged. Full CLI tests verify option propagation. This tests configuration plumbing, not a measured translation segmentation improvement. No hard time slicing or content post-editing added. Original user text/JSONL files remain unchanged and ignored. Recognition accuracy, translation quality, and live latency still require reference audio and controlled review.


## Second user export inspection — 2026-10-29

Eight records matched exactly across UTF-8 text and JSONL, with valid schema, a single session, unique segment IDs, and chronological/non-overlapping timestamps. No blank or whitespace-only records. Durations: 21.92, 4.48, 0.96, 0.88, 2.88, 1.84, 3.56, and 4.60 seconds; median 3.22 seconds. First-phrase under-segmentation remains visible; later segments are shorter in this sample. Input and invocation are not controlled/matched to the previous run, so no causal claim about the optional threshold or latency improvement follows. Some idioms translate too literally; reference audio is still needed for recognition accuracy. Files were inspected without modification and remain excluded from Git; no transcript text or identifiers retained here.


## Recovery and gap records — 2026-10-29

Current full suite: **142 passed** with `python -m pytest -q`; wheel build, dependency check, and whitespace check passed. Same macOS arm64/Python 3.13.7 development environment; no live Azure call or network change made.

New tests use fake clocks/providers and fake SDK operations. Cover exact cumulative 1/2/4-second backoff, three retries per run including after successful reconnects, transient startup recovery, no retries for known auth/quota/access/unknown failures, fatal errors during retry, fresh live sources/PCM, retained WAV cursor without replay, context-specific segment IDs, queued-final delivery before failure, Ctrl+C/duration cancellation in backoff, pause-drain behavior, final-drain/source errors, and cleanup on persistence failures. SDK tests check disconnect/cancellation ordering so specific auth/quota errors take precedence; generic disconnect fallback and redacted native exceptions are covered. Structured failure payloads survive process serialization.

Gap exports are tested through both sinks and a full fake-provider CLI run: same export session across reconnect, finalized data retained, conservative/non-overlapping checkpoint and recovery intervals, synced checkpoint visible before retry wait, no credentials/caption text in gap records, and unchanged cloud config between attempts. Unknown errors never use heuristic error-text matching. Known fatal errors do not trigger retry or paid fallback.

These tests establish application control flow and persistence, not live SDK detection timing, real network recovery, measured missing-audio coverage, other-platform hardware behavior, or 30-minute stability. Gap times express possible missing/unfinalized audio, not exact downtime or translation latency. Manual live interruption steps are in the setup guide and require explicit operator invocation against confirmed F0.


## User-confirmed live recovery — 2026-10-29

The user confirmed completing the Wi-Fi interruption checklist: finalized caption, disconnect, visible reconnect status, restored network, resumed captions, and Ctrl+C shutdown. This is a user-operated macOS test, not an independent agent live run.

Read-only inspection of the corresponding local recovery exports found **3 segment records and 4 gap records**, one export session, and two successful recognizer-context prefixes. Captions occur after gap records. UTF-8 parsing, exact text/JSONL content/timestamp correspondence, expected event types, unique segment IDs, and nonnegative valid intervals passed. Gap reasons include `connection_failure` and `network_disconnect`. No files modified, private transcript text retained in project docs, or identifiers copied.

The artifacts support working export continuity and resumed caption output; they do not establish an exact retry count, exact network detection/downtime, complete audio coverage, measured translation latency/accuracy, other-platform behavior, or a 30-minute pass. Those checks remain separate.


## Caption arrival instrumentation — 2026-10-29

Current full suite: **157 passed** with `python -m pytest -q`; wheel build, dependency check, CLI help, and whitespace checks passed. Same development environment; no new dependencies or live Azure timing calls.

SDK callback tests now verify non-null timestamp capture. Deterministic tests separate callback entry, session handling, and later export/render cost; validate nearest-rank p95 and empty/partial samples; preserve/flag negative source-end estimates; distinguish handler-only and translated-caption coverage; guard against artificial negative dispatch from rounding; and verify provisional timing/deduplication plus shared session-clock continuity after a recovery/new context. Timing survives process serialization and is added to UTF-8 JSONL/text without exporting raw monotonic references. Full fake-provider CLI tests cover optional display and summaries on success or error; local-only meter rejects the option.

This verifies arithmetic and measurement plumbing, not live latency, source-clock alignment, capture timing, terminal paint time, translation accuracy, or 30-minute stability. Source-end delay remains an estimate affected by startup/buffering/pacing/resampling. Existing private exports have no new measurements and were not rewritten. A reference-aligned recording evaluation remains necessary for benchmark claims.


## User timing export inspection — 2026-10-29

The current user-generated timing file contains **one finalized caption**, with English, `provider_callback` timing, no gap/blank/duplicate records, valid UTF-8/JSONL and a newline-terminated complete record. Checked equations: arrival 30,783 ms minus mapped phrase end 28,551 ms = **2,232 ms estimated final delay**; handling 30,867 ms minus arrival = **84 ms local dispatch**; final arrival minus first observed provisional arrival 3,392 ms = **27,391 ms provisional-to-final**. Phrase duration is **27,120 ms**. All arithmetic matches the recorded fields; no negative estimate in this sample.

This supplies one live instrumented sample reported by the user, not independent source/audio alignment or a latency benchmark. Median/p95/max would all equal the single observation and provide no useful distribution evidence. The long phrase and provisional-to-final interval show that segmentation/stabilization still deserves evaluation. No transcript text/identifiers retained; the original export was not modified and remains excluded from Git.


## Additional timing comparison — 2026-10-29

Previous saved snapshot: one callback-timed final, estimated source-end delay 2,232 ms, local dispatch 84 ms, provisional-to-final 27,391 ms, phrase duration 27,120 ms. Current snapshot: four callback-timed finals, no gaps/blanks/duplicate IDs, one session and ordered/non-overlapping intervals. All timing equations match. Current estimated delay median/min/max: 1,226/1,023/1,545 ms; dispatch median/max: 37.5/57 ms; provisional-to-final median: 5,371.5 ms; phrase-duration median/max: 5,760/20,880 ms. With four observations, nearest-rank p95 equals the maximum.

The speech text and covered durations differ, and configuration/segmentation settings are not recorded in these exports. Therefore these are descriptive samples rather than a matched comparison or proof of improvement caused by the optional setting. First-phrase under-segmentation persists. Original files unchanged; no private transcript content or identifiers retained here.


## User-confirmed same-recording comparison — 2026-10-29

The user confirmed using the same recording. Current snapshots cover approximately 30.20 and 30.54 seconds, with 73 and 72 recognized source words and about 97.9% normalized token similarity. This similarity compares model outputs, not recognition accuracy. Small wording/coverage differences remain; one short phrase is absent from one output, requiring reference audio to attribute the difference. Every final has English; neither run contains gap/blank/duplicate-ID records; timing arithmetic passes.

| Metric | `exports1` (2 finals) | `exports` (4 finals) |
| --- | --- | --- |
| Median estimated source-end delay | 3,259 ms | 1,401.5 ms |
| Median first observed provisional-to-final | 14,349.5 ms | 6,141.5 ms |
| Median phrase length | 13,780 ms | 6,560 ms |
| Longest phrase | 13,920 ms | 8,520 ms |
| Median local dispatch | 51.5 ms | 48 ms |

The second run is descriptively more responsive in this pair. Settings are not recorded in the files, so file-to-setting attribution requires user confirmation. Single short runs, unequal segmentation and small source differences do not establish repeatable benchmark improvement or unchanged translation quality. No private files modified or transcript text/identifiers copied into project docs.


### Segmentation setting attribution

The user subsequently confirmed that `exports/timing-test.jsonl` used `--segmentation-silence-ms 300`. Its better timing estimates in the short same-recording comparison can therefore be associated with that run's configuration. The `exports1` setting is still not explicitly confirmed. This does not establish causality, repeatability, or an accuracy improvement; retain the current opt-in setting and verify the source-content difference before changing defaults.


## Deferred future validation — 2026-10-29

At the user's request, the following checks are deferred because they cannot perform them now. No dates or completion claims are assigned. Retain the procedures above for future execution, while allowing other authorized implementation work to continue:

- **30-minute long-session test:** Caption delay, memory use, pause/resume, exports, and one network interruption/recovery.
- **Reference-audio accuracy review:** A few minutes focused on missing words, numbers, and preservation of meaning.
- **Windows/Linux validation:** Installation/setup, system-audio capture, and audible playback, with actual environment details recorded.

These deferrals do not establish benchmark latency, accuracy, long-session reliability, or cross-platform release support. Resume the checks when the user authorizes/has capacity; do not repeatedly present them as immediate required tasks.

## Run-configuration metadata — 2026-10-29

Full suite: **173 passed** (`python -m pytest -q`); wheel build, dependency check, and whitespace check passed. New offline tests cover text/JSONL headers visible before captions, default versus requested 300 ms settings, shared session IDs, invalid metadata rejection, no files/sidecars without export flags, header-failure cleanup, and failure before capture/provider construction. Fake CLI runs cover system/microphone/file inputs with both settings and verify absence of credentials, region, device identifiers, and file paths. Recovery tests verify exactly one header across reconnects. Legacy standalone exporters remain headerless unless metadata is supplied; historical user files are unchanged.

These checks validate serialization/lifecycle and requested settings, not live Azure configuration application, platform capture, translation quality, or stability. No live cloud calls or private export edits were performed. Deferred long-session, reference accuracy, and Windows/Linux checks remain deferred.

## Stage-one desktop GUI — 2026-10-29

**183 offline tests passed**, including 10 optional offscreen GUI tests on the existing macOS arm64/Python 3.13.7 environment, using PySide6 6.12.0. Editable GUI installation, wheel build, dependency and whitespace checks passed. Empty-window screenshot rendered via Qt offscreen and visually inspected: readable labels, source/device row, F0 confirmation, Start/Stop, separate status/provisional text, and transcript area fit at 860×640. This checks layout, not real desktop theme/accessibility or audio.

GUI tests use synthetic devices/providers only. They check F0/missing-credential gates before startup; source filtering; event-loop responsiveness; duplicate Start prevention; Stop cleanup and final drain; retention across runs without disk files; close deferral; provisional coalescing and bounded final backlog; fatal errors; retry-wait cancellation; cancellation before startup and during provider startup; and retryable discovery errors without exposing raw diagnostics. Existing CLI pause/recovery tests still pass after adding a separate stop callback. GUI tests skip when PySide6 is absent.

No agent live capture or Azure calls were run. Opening/refreshing alone is not permission/routing/translation evidence. A short manually invoked GUI run remains unverified: confirm F0, choose routed input, start a non-private Polish source, observe bilingual captions, Stop, and close; verify audio remains audible and resources are released. Long-session, accuracy, and Windows/Linux checks remain user-deferred. GUI pause/resume/export controls and styling stages are not part of this milestone.

### User GUI confirmation — 2026-10-29

After receiving the GUI launch instructions, the user reported that it works well. This is user-reported confirmation on their macOS setup; individual capture/translation, Stop/close, playback, and duration results were not supplied. No independent agent live rerun followed. Deferred validation and other-platform evidence remain unchanged.
