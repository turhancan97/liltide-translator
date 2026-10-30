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

## GUI stage two — 2026-10-29

**189 offline tests passed**, including 16 optional offscreen GUI tests in the same macOS/Python/PySide6 environment. Wheel, dependency, local-link, and whitespace checks passed. Synthetic paused bilingual and English-only windows rendered and visually inspected at 860×640: Pause/Resume, view selector, explicit state/detail labels, and captions fit without clipping. No private transcript content was used.

New/extended GUI checks verify pause final drain and resource release, no read/poll activity while paused, fresh contexts on resume with one retained session/history, disabled repeated transitions, Stop/close while paused without reopening resources, view switching before/during/after sessions without reconnect, source-text restoration, literal markup, unavailable English, fatal resume cleanup/error state, and reconnect pause guards. Existing CLI pause/recovery tests still pass with the optional structured lifecycle callback. No live Azure/capture call was run; earlier user GUI confirmation covers stage one, not these new controls. Long-session/accuracy/Windows/Linux checks remain deferred.

### User stage-two confirmation — 2026-10-29

After receiving the Pause/Resume, English-only view, and explicit-state update, the user reported it works well and authorized a push. Record stage-two GUI operation on macOS as user-confirmed; no individual checklist outcomes, measurements, or session duration were supplied. No independent agent live rerun followed; deferred release validation is unchanged.

## GUI stage three — 2026-10-29

**203 offline tests passed**, including 30 optional offscreen GUI tests on the existing macOS/Python/PySide6 environment. Wheel build, dependency, local-link, and whitespace checks passed. Rendered a synthetic 900×800 window with export selectors, timing details, and last-session statistics; visually inspected readable controls and unclipped caption/summary areas. No private text was used.

New GUI integration tests cover independent/both destinations, flushed records visible before Stop, one metadata header/session across pause/reconnect, gap persistence, bilingual output despite English-only view, controls locked during runs, existing/duplicate/missing-parent/blank destinations, header cleanup before source/provider construction, failed final writes preserving completed records, received-versus-persisted counts, timing re-rendering without restart, negative estimates, zero/unavailable samples, browse selection/cancel, and no files from unchecked paths/timing alone. Existing core exporter durability/recovery tests continue to pass. An initial shutdown crash after passing widget tests exposed a retaining browse lambda; switching to a bound slot removed the retained-window cycle and subsequent GUI/full-suite processes exited successfully.

No agent live cloud/audio test was run. Stage-three live GUI exports/timing remain unverified, and earlier macOS user confirmations cover stages one/two. Long-session, reference accuracy, and Windows/Linux validation remain user-deferred. Styling/theme controls are not implemented here.

## GUI branding/usability — 2026-10-29

**209 offline tests passed**, including 36 optional offscreen GUI tests on the existing macOS arm64/Python 3.13.7/PySide6 6.12.0 environment. Wheel build and packaged-resource checks, dependency, local-link, and whitespace checks passed. Original symbol bytes in the wheel match the authoritative approved SVG; the original utility checkmark is packaged too.

Added fake-session checks show that theme/font changes preserve worker identity, history, and enabled export configuration; simulated system theme notifications update System mode while manual mode remains stable. Compact-window tests exercise setup scrolling and readable transcript area. Keyboard tests activate guarded Start, Pause, and Stop, confirm duplicate Start does not create another worker, and exercise Tab order. Text/selection palettes meet 4.5:1 in both themes. WCAG formula measurements: ink/white **16.29:1**, ink/gray **10.85:1**, blue/white **4.42:1**, blue/ink **3.69:1**, red/white **4.54:1**, red/ink **3.59:1**. Blue/red are meaningful graphic accents (3:1 requirement), not small text on those surfaces.

Rendered actual synthetic windows for Liltide 0.1.0.dev0 via Qt offscreen on macOS: light/dark at 1100×820, compact dark at 760×600 with 26 pt captions, plus checked/unchecked controls. Visually inspected symbol, neutral body text, accent/focus boundaries, explicit checkmarks, distinct groupings, caption wrapping, scroll access, and summary layout. Fixed dark native checkbox boundaries by packaging a neutral checkmark and explicit contrasting indicator surfaces. These are rendering/interaction checks, not a full accessibility certification. Real desktop scaling, screen readers, native shortcut mapping, and OS appearance notifications remain unverified. No live audio/cloud test or private transcript use; previous user confirmations cover stages one/two. Long-session/accuracy/Windows/Linux validation remains deferred.

## Dropdown clipping correction — 2026-10-29

After the user reported clipped open-menu text, offscreen inspection found native menu row rectangles of 160 px inside a 77 px Theme popup (and similar mismatches in other selectors). This identifies inconsistent native/styled geometry; exact desktop clipping was not independently reproduced. All five selectors now use standard list delegates with synchronized fonts, content-sized/screen-bounded popup widths, padded rows, and horizontal scrolling for exceptionally long content. Theme and Caption size closed controls also have wider minimum sizes.

**219 offline tests passed**, including 46 GUI tests. New cases open each selector in light/dark modes at compact window width and 18 pt control font, check that text/padded rows fit their viewports, and select entries with mouse events; Caption size changes still reach the reader. Rendered and inspected Theme/Caption size open menus in both themes using synthetic content. Wheel/dependency/whitespace checks passed. No audio/cloud calls or private data used. Real desktop confirmation remains open.

## Floating captions — 2026-10-29

**225 offline tests passed**, including 52 optional offscreen GUI tests in the existing environment. Wheel, dependency, local-link, and whitespace checks passed. New fake-session tests cover opt-in visibility/window flags without creating files or processing; shared captions/state; language/font/theme synchronization without a second provider; hiding while processing continues; reopening with the latest result; pause/stop retention and new-run reset; main-close resource cleanup; Unicode, literal markup, unavailable English, and latest-only display.

Rendered and visually inspected synthetic 720×380 floating windows in light/dark modes and a compact 480×280 window with 26 pt text: explicit Finalized/Provisional labels, neutral readable surfaces, synchronized controls, and scrollable caption areas. Qt flags for stay-on-top and macOS inactive visibility were inspected/tested, but actual OS stacking, lecture-app interaction, fullscreen/Spaces, and other platforms remain unverified. Closing only the floating window does not stop translation. No audio/cloud call or private transcript use; deferred long-session, reference accuracy, and Windows/Linux checks remain unchanged.

## Agent-operated synthetic macOS GUI smoke test — 2026-10-29

User explicitly requested the short live check, launched the configured GUI, and reconfirmed F0. No credentials were exposed/read and no Azure resource/settings were inspected or changed. Host/runtime match the existing macOS arm64/Python 3.13.7/PySide6 environment. Generated a 17.3 s Polish WAV locally with installed Zosia voice using only synthetic text, then played directly into the selected BlackHole endpoint. No private recording, microphone, or system routing change. The generated test clip is not an application audio recording; artifacts remain outside version control.

Initial preflight correctly rejected a missing export parent directory; created the directory. Two subsequent attempts failed in capture with **Device ID not found**. Each produced a valid matching text/JSONL header and source-failure gap, zero finalized captions, and an Error/zero-sample summary. Fresh-process and Qt-thread/spawn discovery diagnostics found the virtual endpoint with matching IDs; the diagnostic did not reproduce the running app's failure. Refresh alone did not help. User fully restarted the GUI; the next attempt succeeded. Cause remains unresolved, and no capture-code fix is claimed.

Observed with native UI controls: bilingual live provisional/final text, floating-window switch to English-only and 26 pt mirrored in the main window, closing floating while the main session continued, pause reaching Resume, resume followed by another translated caption, and Stop reaching Stopped. Successful exports contain **one session header, two finalized bilingual records, two distinct recognizer contexts, zero gaps**, and no duplicate/blank segments. UTF-8, exact text/JSONL correspondence, timing equations, and session identity checks pass. The GUI summary matches recomputed counts/statistics: two finals/two English/two SDK callback-timed; estimated-delay median **1706.5 ms**, p95/max **1779 ms**, individual values **1779/1634 ms**; dispatch median **26.5 ms**, p95/max **47 ms**; provisional-to-final median **16753.5 ms**, p95/max **16795 ms**. These are two synthetic samples and estimated source alignment, not benchmark latency or an accuracy result. Native process inspection after Stop found **zero capture/provider spawn children**.

A temporary blank browser tab was created/closed for a foreground-app attempt, but the foreground browser changed during the check; actual cross-app stacking was not reliably verified. Fullscreen/Spaces, audible playback, OS theme switching, screen readers, 30-minute stability, reference accuracy, and Windows/Linux remain open/deferred as previously recorded. The test is a partial desktop smoke pass with an unresolved initial source failure, not a cross-platform release gate. Only documentation changed; no new automated suite was needed for this evidence update.

## Device-ID failure investigation — 2026-10-29

User requested diagnosis first. Confirmed code path: [GUI preflight](../src/liltide/gui_window.py) selects the device in the parent; [capture worker](../src/liltide/capture.py) selects it again in a spawned process, before opening a recorder. [Exact selection](../src/liltide/audio.py) raises the observed error when no current input matches the numeric string ID. The prior failures produced `source_failure` gaps, placing failure after parent preflight, in source processing. The immediate error is not an Azure credential/quota or recorder sample-rate error; whether permissions/topology changed the child enumeration is not established.

The installed SoundCard 0.4.6 [CoreAudio implementation](https://raw.githubusercontent.com/bastibe/SoundCard/0.4.6/soundcard/coreaudio.py) enumerates AudioObjectIDs and exposes that numeric ID. Liltide transports its string form across processes; it does not carry or re-resolve the selected device's persistent UID. Refresh constructs a new backend but uses the same process/imported native library, so it is not equivalent to a full restart. Apple's installed AudioHardwareBase.h documents [DeviceUID](https://developer.apple.com/documentation/coreaudio/kaudiodevicepropertydeviceuid) as persistent across boots; AudioHardware.h describes rebuilding client state after [service reset](https://developer.apple.com/documentation/coreaudio/kaudiohardwarepropertyservicerestarted). These mechanisms make stale identity/state plausible but do not prove a reset or ID change occurred in the original incident. SoundCard's installed enumeration path does not show a Python device-list cache; stale native state must not be described as a confirmed Python caching bug.

A temporary read-only diagnostic compared an initial Qt discovery-thread snapshot, separate validation-thread snapshots in the same process, and six spawned children. Each round found four inputs; the selected virtual device's numeric ID and persistent UID matched in all comparisons, and every child exited cleanly. No recorder, playback, Azure SDK/provider, permissions/routing changes, or device identifiers were logged. Thus a deterministic spawn/thread/ID-conversion defect was not reproduced. The original failed process is gone, and its export schema intentionally excludes device identifiers/snapshots; exact mismatch versus missing-device enumeration cannot be reconstructed from those artifacts.

Leading hypothesis is intermittent inconsistent CoreAudio identity/enumeration state between the long-lived GUI and a fresh child, consistent with restart resolving the prior run. Recommended next implementation is identifier-safe parent/child diagnostics and exact persistent-UID resolution inside the child; do not silently select by name/default or assert that this design gap proves the historical cause. No application-code change, cloud/audio test, new automated suite, commit, or push was performed in this diagnostic task.

## Security review — 2026-10-29

See the [security review](security-review.md) for source scope, scanner versions/results, synthetic device-selection and terminal-output reproductions, advisory prerequisites, and open repair acceptance criteria. The original findings were open at review time; see the subsequent security-fixes entry for repair evidence. Zero Bandit results do not establish security. This review used no audio/cloud calls and does not complete the deferred platform/release checks.

## Device-ID follow-up investigation — 2026-10-29

The user resumed investigation of the intermittent capture-child failure; security repairs remain deferred. A temporary read-only probe used a Qt discovery thread for its parent snapshot and nine fresh spawned children (three rounds with input-first, output-first, and default-input/output-first initialization). Outside the sandbox, the parent and every child saw four inputs, identical persistent-UID sets, and zero numeric-ID changes for matching UIDs. All children completed. The sandbox saw zero inputs, so that restricted run is not evidence of device health. Only aggregate counts/comparison results were printed; no device names, numeric IDs, UIDs, credentials, or audio were saved. No recorder, playback, routing change, service reset, or Azure call was made.

This further weakens a deterministic fresh-process/initialization-order explanation. It does not recreate the original long-lived failing process or establish that its state was stale. Device disappearance, ID reassignment, and inconsistent native enumeration remain candidate mechanisms; the historical trigger remains unresolved.

Added two synthetic boundary tests in [test_capture.py](../tests/test_capture.py): parent enumeration/preflight succeeds, then child enumeration either contains no device or contains the same synthetic name/UID under a different numeric ID. Both reproduce `Device ID not found`, emit no audio blocks, and open no recorder. The second case demonstrates that the current numeric-ID-only boundary cannot use a stable identity to recognize a renumbered device; it does not show that renumbering happened in the original run. **16 targeted capture/audio tests passed**. Production code was not changed, and the full suite was not rerun.

Additional source tracing explains why a cloud connection can appear successful before this local failure: `LiveSource` creates a lazy capture generator; `TranslationSession._activate()` starts the provider before the first `source.read()` starts the capture child. Thus provider readiness or a subsequent `source_failure` gap does not imply Azure caused the lookup error. No live provider was invoked to establish this source-level ordering.

The next useful implementation is a privacy-safe, bounded diagnostic at the actual failing boundary: distinguish parent preflight from child lookup, compare enumeration counts and exact selected identity presence, and distinguish an absent persistent UID from a UID whose numeric ID changed. Keep identities in memory and publish aggregate outcomes only. A subsequent exact persistent-UID resolution change should fail on missing/ambiguous identity and retain no name/default fallback. Those production changes are proposed, not implemented by this investigation. Continue treating a full app restart as a workaround observed in the earlier run, not a proven repair; after Refresh, explicitly verify the selected virtual device because SEC-01 remains open.

## Persistent-device identity implementation — 2026-10-29

After the investigation, the user authorized its recommended diagnostics and persistent-identity changes. macOS discovery now reads DeviceUID through a small read-only system-library helper. GUI selection carries that identity into parent validation and each spawned capture context; CLI preflight and direct/local capture bind the supplied numeric selection before spawn. Exact UID resolution accepts a changed numeric ID, rejects an ID reused by a different device, and stops on missing/ambiguous/unreadable identity. No name/default fallback, service restart, driver installation, or routing change was introduced. Windows/Linux retain exact endpoint selection and remain hardware-unverified.

Failures now identify parent validation versus capture-child selection. Identity failures include only input count, whether the old numeric ID is present, and missing/ambiguous/unavailable outcome; identifiers and native exception details are excluded from the displayed diagnostics. IDs/UIDs stay in private session state, are hidden from identity representations, and are not added to allowlisted exports. CoreFoundation strings are released on decode success/failure. Native property calls have no new timeout; capture-child startup remains bounded by the existing parent loop, while parent discovery/preflight can still block in native code.

**244 offline tests passed**, including 53 GUI tests. New coverage includes identity serialization, renumbering with an old numeric ID reused by another device, missing/duplicate/unreadable UID rejection, non-macOS endpoint behavior, native property/decode/empty-string failures and CFString ownership, pre-spawn level-check binding, GUI identity retention across pause/resume, and CLI export omission of persistent identities. Earlier synthetic numeric-only failure tests remain as evidence of the original boundary condition. Wheel build, packaged helper/symbol checks, dependency consistency, local links/anchors, and whitespace checks passed.

A read-only macOS arm64/Python 3.13.7 check used the new production backend/helper: parent discovery found four inputs; a fresh child resolved all four exact identities and all four references whose numeric IDs were deliberately replaced with a synthetic stale value. Only counts were printed. This simulates stale references without changing OS devices; it is not a reproduction of the historical trigger or proof of capture/translation behavior. No recorder, playback, microphone access, Azure call, or private export edit occurred. No new live capture/translation smoke test was run. Deferred SEC-01 GUI Refresh selection repair and the other security findings remain open. No commit or push in this implementation task.

## Security fixes — 2026-10-29

The user reported the preceding persistent-identity update works well (general user confirmation; detailed checklist results unspecified), then explicitly resumed SEC-01/02/03 repairs. **257 offline tests passed**, including 58 GUI tests. New security coverage verifies explicit initial selection; no worker creation when Refresh loses a virtual input and leaves a microphone, an empty list, a reused numeric ID, or duplicate UIDs; identity-preserving refresh/reordering; C0/C1/ESC/OSC/CSI and line-break spoofing at final/provisional/status/device/text-export boundaries; unchanged ordinary Polish Unicode; and lossless JSONL decoding with escaped controls. All payloads were synthetic, captured in memory or temporary files; no interactive terminal payload was emitted.

Project-local pip was upgraded from 25.2 to 26.2.2. pip-audit 2.10.1 returned zero advisory rows across 37 distribution records, with editable Liltide skipped. This resolves the six previously reported pip advisories in this environment only. Bandit 1.9.4 returned zero findings/errors on production source. These scanners do not establish comprehensive security or native-library coverage. No runtime dependencies were upgraded.

Wheel build, packaged identity/safety helpers and brand resource checks, dependency consistency, local documentation links/anchors, and whitespace checks passed. No live audio/cloud call, private export rewrite, commit, or push. The user has not yet confirmed the subsequent security UI changes on their desktop. Remaining hardening suggestions stay in the roadmap; deferred long-session, accuracy, and Windows/Linux checks remain open.

## Automated checks — 2026-10-29

The user authorized [GitHub checks](ci.md). Workflow syntax passed actionlint 1.7.12 with verified upstream release digest; official action commit pins were resolved from their releases. Gitleaks 8.30.1 was likewise checksum-verified: a redacted full-history scan covered 12 existing commits with zero matches; a separate temporary repository containing a generated synthetic credential returned detection status 1 without exposing the credential, despite local allowlist/inline-suppression attempts. Changed/untracked project files were also scanned locally with no matches at scan time. Private exports and ignored environments were excluded. This is detection evidence, not proof of no secrets.

**259 offline tests passed on macOS/Python 3.13**, including two new document-checker boundary tests for reference/image links, encoded spaces, duplicate/self heading fragments, fenced examples, missing targets/anchors and repository escapes. Source/wheel builds, packaged wheel CLI help, dependency consistency, strict isolated pip-audit, actionlint, repository documentation links, and whitespace checks passed locally. These results do not establish Ubuntu or Python 3.11 execution. The first GitHub-hosted push/PR run remains pending; no workflow badge or cross-platform release claim was added.

The workflow requires no Azure/repository secrets, uses fake providers/offscreen GUI, grants read-only contents access, disables persisted checkout credentials, and uploads no artifacts or findings. No deployment, branch-protection change, schedule, remote commit/push, or live audio/cloud call in this task. Dependency advisories are checked when workflows run, not continuously. External links and arbitrary HTML anchors are outside the documentation checker scope.

## Light and dark README banners — 2026-10-29

Added matching 1100×320 [light](../assets/brand/liltide-banner-light.svg) and [dark](../assets/brand/liltide-banner-dark.svg) designs using the original waveform and approved palette; the original banner filename is an identical light fallback. README uses documented picture/media selection with an accessible alt description. Rendered both SVGs at 1100 and 550 px widths using librsvg; 550 px light/dark previews were visually inspected for clipping, wordmark/tagline legibility and graphic separation. Secondary small labels are supplementary; README body text and alt text provide the meaning independently. Temporary rendered previews are not committed.

Both new variants and fallback passed XML, approved-color, title/description, and matching-layout checks. Picture source paths/media ordering and fallback alt text were checked separately because the Markdown checker intentionally ignores raw HTML. Measured text contrast: ink/white 16.29:1; gray/ink 10.85:1. Waveform graphic contrast: blue/white 4.42:1, blue/ink 3.69:1, red/white 4.54:1, red/ink 3.59:1; all exceed 3:1 for the meaningful graphics. Thin gray outlines are decorative. No small blue/red text is used. Local documentation links and whitespace checks passed; no application change or full-suite rerun for this asset-only task. Actual GitHub rendering/theme switching remains unverified; other Markdown viewers may use only the light fallback.

## Hosted CI and main protection — 2026-10-29

Independently read GitHub run/job/check metadata for [first run 40953616220](https://github.com/turhancan97/liltide-translator/actions/runs/40953616220) at `501841f` and [latest verified run 40955144466](https://github.com/turhancan97/liltide-translator/actions/runs/40955144466) at `717c843`. Both completed successfully across all five jobs. Latest log summaries confirm **259 tests passed on Ubuntu 24.04/Python 3.11 and 259 on Python 3.13**, both source/wheel build and installed-wheel CLI steps succeeded, 12 Markdown files had zero link failures, pip-audit reported no known advisories, and Gitleaks scanned 14 commits with no matches. These are offline Linux test/build results, not system capture/playback, native macOS identity behavior, or live translation validation. Earlier entries marked hosted execution pending describe the pre-publication state; this entry supersedes that limitation for these commits only.

User then authorized main protection. Confirmed repository is public/personal with admin access, existing protection absent, and no inherited rulesets. Applied branch protection and independently fetched it afterward: required PR object present, approval count 0, strict/up-to-date checks enabled, admin enforcement enabled, force pushes/deletion disabled. Five exact check contexts are tied to GitHub Actions app ID 15368; see [required names](ci.md#required-checks-on-main). Personal repositories reject organization-only bypass-user/team fields; the corrected request omits them. No protection bypass or rejected push was attempted as a test, and no CI/repository secrets were inspected.

README now links the live `checks.yml` badge restricted to `branch=main&event=push`; endpoint download parsed as valid SVG. Its displayed state is dynamic, not a fixed passing guarantee. Local documentation links/anchors and whitespace checks passed. No application change/full-suite rerun for these documentation/settings changes, no live audio/cloud call, and no commit/push of the local docs branch during this task. Deferred validation and broader security limits remain open.

## Native macOS desktop check — 2026-10-29

User authorized a short desktop check on macOS 27.0.1 arm64/Python 3.13.7, production snapshot `eaad42c`. Two temporary harness runs instantiated the production main/floating windows and session coordinator with synthetic devices/captions and fake sources/providers. Real audio-backend/provider constructors were replaced with fail-fast guards, and any nonempty transcript export path was rejected. These are native presentation/control checks, not live audio/translation validation. UI actions used desktop automation; temporary read-only Qt state snapshots contained only fixture settings, focus/key diagnostics, counters and own-window exposure state. No private speech/device/credential data was used or copied into these docs.

| Check | Observed result | Limit |
| --- | --- | --- |
| Appearance | System mode initially rendered dark; manual Light and Dark worked; 26 pt floating text and controls remained readable in inspected native window captures | No OS appearance preference change or notification test |
| Shared presentation | English-only/26 pt changes from floating propagated to main; caption/provisional text, hide/reopen retention and theme propagation worked without extra source/provider creation | Synthetic captions only |
| Keyboard controls | Focused main Start, Pause/Resume, Stop and popup arrow/Return actions changed expected state; Tab moved between caption fields | Complete Tab traversal, screen readers and physical global-hotkey interception not established |
| Normal-window exposure | After a physical click activated blank Chrome, Qt reported Liltide inactive, main unexposed and floating exposed | Own-window native exposure signal; per-app screenshots exclude other windows and do not directly prove full composite ordering |
| Native fullscreen | With Chrome fullscreen, main and floating both became unexposed while floating remained logically visible; exiting fullscreen restored floating exposure | **Reproduced limitation; no fullscreen fix implemented** |
| Cleanup | First run closed/released 1/1 fake source/provider; second run 2/2 after pause/resume, with no remaining worker; both harness processes exited 0 | No native capture/provider child processes were started |

The initial automation input for the Stop punctuation key produced a different character under the host keyboard layout; sending the actual period activated Stop. This was an input-mapping issue, not evidence of an application shortcut defect. Some accessibility snapshots did not expose dropdown popup contents, so selection was verified by the resulting control values/read-only fixture state. No application behavior change was made on that basis.

The browser was restored out of fullscreen, the agent-created blank tab was closed, and the originally selected project tab restored. No OS keyboard/theme settings, permissions or audio routing changed. Arbitrary non-fullscreen Spaces, other applications, multiple displays and full accessibility remain open. Native fullscreen entry/exit tests a particular Space transition, not all Spaces support. Recommended follow-up is to define and implement supported fullscreen/Spaces floating-window behavior, then repeat the same guarded comparison. Local docs/whitespace checks passed; no full suite rerun for this documentation-only task and no commit/push.
