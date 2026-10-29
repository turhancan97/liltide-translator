# Features and roadmap

Capture CLI and translation PoC implemented; macOS lecture capture/playback is user-confirmed. Live macOS translation is also user-confirmed; caption-arrival instrumentation is implemented/offline-tested; reference-aligned quality/latency and comprehensive failure validation remain open. Opt-in text/JSONL exports are implemented and offline-tested; bounded recovery and gap records are also implemented/offline-tested; live macOS recovery is user-confirmed; long-session/accuracy and Windows/Linux validation are explicitly deferred by the user; later milestones remain open. Evidence lives in [CONTEXT.md](../CONTEXT.md).

| Milestone | Deliverables | Completion gate |
| --- | --- | --- |
| 0 — Identity and documentation | Guides, agent handoff, SVG variants, MIT license | Links, consistency, SVG rendering, and contrast reviewed |
| 1 — Capture CLI | Packaging, `devices`, local `doctor`, audio-level check; system/microphone capture and routing instructions | Local capture/playback smoke tests recorded per OS; no cloud needed |
| 2 — Translation PoC | Azure F0 continuous streaming, paced WAV input, bilingual/provisional captions, timestamps, English-only view, pause/resume, Ctrl+C | Live macOS PoC user-confirmed; reference accuracy review deferred |
| 3 — Reliability and exports | Explicit text/JSONL export, bounded buffers/retries, gap notices, quota and credential handling | Automated fake-provider failure tests; 30-minute session validation deferred |
| 4 — Cross-platform v1 | Setup corrections, compatibility matrix, release instructions | Windows/Linux tests deferred; real capture/provider evidence required before cross-platform release claims |
| 5 — Python GUI (stages one through four implemented; offline-tested) | PySide6 device controls, transcript panels, system theme/manual override, floating captions | Reuses validated core; UI workflow and accessibility checks completed |

## v1 feature checklist

- [x] Device enumeration/selection and actionable local diagnostics (capture permissions/routing need live validation).
- [ ] System audio capture on each target OS with original audio still audible.
- [x] Optional microphone capture path implemented; no silent fallback or mixing (hardware validation pending).
- [x] Paced PCM16 WAV input using the shared processing pipeline (offline tested).
- [x] Azure continuous Polish transcription and English translation adapter (fake SDK tested; live service unverified).
- [x] Provisional display updates and finalized-segment deduplication (offline tested).
- [x] Elapsed timestamps, bilingual default, English-only option (offline tested).
- [x] Pause/resume, clean termination, and explicit application buffer gap errors (offline tested; live cloud pending).
- [x] Text and JSONL exports only when requested; per-final-segment flush/sync and interruption tests pass; no raw recording.
- [x] Automatic run-settings headers in opt-in exports; distinguish service default from requested segmentation (offline tested).
- [x] Bounded retries/buffering and structured quota/authentication errors (offline tests; live macOS recovery user-confirmed).
- [x] Color-independent status and readable non-interactive output (offline tested).
- [ ] Free-only setup, privacy explanation, license notices, and verified platform matrix.

## Future validation — deferred by the user

Deferred on 2026-10-29 because the user cannot perform these tasks right now. No schedule is assigned. Continue other authorized development without treating these as immediate user tasks; resume them when the user is ready. They remain unverified, and the applicable release/quality claims still require their evidence.

- [ ] **Long-session test:** Run a 30-minute lecture session; check caption delay, memory use, pause/resume, transcript exports, and one network interruption/recovery.
- [ ] **Accuracy review:** Compare a few minutes against the original audio/reference transcript, focusing on missing words, numbers, and preservation of meaning in the English translation.
- [ ] **Windows/Linux validation:** Test installation, audio-source selection, system capture, and audible playback on both platforms; record actual OS/runtime/backend versions and setup limitations.

## Deferred

Offline inference, additional language pairs, SRT export, translated speech, speaker identification, meeting integrations, native applications, and packaged installers. No schedule or delivery date is promised. A roadmap entry does not authorize implementation of that milestone; use the user's current task scope.

## GUI PoC stages

- [x] Stage 1: optional PySide6 window, source/device selection, F0-gated Start/Stop, bilingual provisional/final captions; fake-provider/offscreen checks passed. The user reports that the GUI works well on macOS; detailed live checklist outcomes remain unrecorded.
- [x] Stage 2: pause/resume, English-only display (including existing history), and explicit session states; offline-tested and user-confirmed working on macOS; individual checklist results unspecified.
- [x] Stage 3: optional text/JSONL destinations, caption timing toggle, and last-session summaries; offline-tested and brief synthetic macOS GUI check passed.
- [x] Stage 4: approved brand styling, System/Light/Dark themes, grouped/resizable layout, caption sizing, and keyboard controls; offline-tested/visually inspected.
- [x] Floating caption view: optional shared-session window, latest final/provisional text, synchronized language/font/theme; offline-tested, with live caption/language/font checks on macOS. Actual OS stacking remains open.
- [ ] Real desktop stacking/fullscreen, accessibility, and OS theme checks; remain unverified.

The user authorized GUI stages one through four before the deferred release checks are complete. This does not declare the CLI or GUI cross-platform release-ready. Later GUI stages need a separately authorized task.
