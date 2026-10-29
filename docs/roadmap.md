# Features and roadmap

Capture CLI and translation PoC implemented; macOS lecture capture/playback is user-confirmed. Live macOS translation is also user-confirmed; quantitative quality/latency and failure validation remain open. Reliability/exports and later milestones remain planned. Evidence lives in [CONTEXT.md](../CONTEXT.md).

| Milestone | Deliverables | Completion gate |
| --- | --- | --- |
| 0 — Identity and documentation | Guides, agent handoff, SVG variants, MIT license | Links, consistency, SVG rendering, and contrast reviewed |
| 1 — Capture CLI | Packaging, `devices`, local `doctor`, audio-level check; system/microphone capture and routing instructions | Local capture/playback smoke tests recorded per OS; no cloud needed |
| 2 — Translation PoC | Azure F0 continuous streaming, paced WAV input, bilingual/provisional captions, timestamps, English-only view, pause/resume, Ctrl+C | Representative recording evaluated; F0 setup and cloud-test invocation documented |
| 3 — Reliability and exports | Explicit text/JSONL export, bounded buffers/retries, gap notices, quota and credential handling | Automated fake-provider failure tests and 30-minute session test pass |
| 4 — Cross-platform v1 | Setup corrections, compatibility matrix, release instructions | Real system-audio and provider smoke tests on Windows, macOS, Linux; unresolved limits disclosed |
| 5 — Python GUI | PySide6 device controls, transcript panels, system theme/manual override, floating captions | Reuses validated core; UI workflow and accessibility checks completed |

## v1 feature checklist

- [x] Device enumeration/selection and actionable local diagnostics (capture permissions/routing need live validation).
- [ ] System audio capture on each target OS with original audio still audible.
- [x] Optional microphone capture path implemented; no silent fallback or mixing (hardware validation pending).
- [x] Paced PCM16 WAV input using the shared processing pipeline (offline tested).
- [x] Azure continuous Polish transcription and English translation adapter (fake SDK tested; live service unverified).
- [x] Provisional display updates and finalized-segment deduplication (offline tested).
- [x] Elapsed timestamps, bilingual default, English-only option (offline tested).
- [x] Pause/resume, clean termination, and explicit application buffer gap errors (offline tested; live cloud pending).
- [ ] Text and JSONL exports only when requested; no raw recording.
- [ ] Bounded retries/buffering, explicit quota/authentication errors.
- [x] Color-independent status and readable non-interactive output (offline tested).
- [ ] Free-only setup, privacy explanation, license notices, and verified platform matrix.

## Deferred

Offline inference, additional language pairs, SRT export, translated speech, speaker identification, meeting integrations, native applications, and packaged installers. No schedule or delivery date is promised. A roadmap entry does not authorize implementation of that milestone; use the user's current task scope.
