# Validation

## Documentation and asset checks

For this milestone, check local Markdown links/images resolve, planned CLI examples agree across guides, SVG XML parses, and logo variants render without clipping. Render each variant on its intended surface and inspect symbols at 24/32 px and wordmarks at 160 px. Calculate WCAG relative-luminance contrast for approved text/background pairs and retain the results below. Do not imply these checks validate application behavior.

### Results — 2026-10-28

Documentation/asset QA passed:

- All 40 local Markdown/image links in the initial guides resolved; final link validation also covers the added preview links.
- All 8 SVGs parsed as XML and contain accessible titles/descriptions, with no embedded raster images.
- Rendered all variants using `rsvg-convert`; visually inspected 24/32 px symbols and 160/360 px wordmarks on light/slate backgrounds. No clipping observed; 24 px symbols and 160 px wordmarks remain readable. [Rendered contact sheet](../assets/brand/preview.png).
- Reviewed CLI examples, free-only policy, planned/verified distinctions, and roadmap consistency. No application code, cloud resources, drivers, or live API requests were created.

Contrast was calculated using WCAG sRGB linearization and relative luminance (ratios rounded to two decimals):

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
