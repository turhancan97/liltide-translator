# Working on Liltide

## Start here

Read [CONTEXT.md](CONTEXT.md) for current progress, then the relevant authoritative guide:

- [Technical specification](docs/technical-spec.md): processing, CLI, privacy, and failure behavior.
- [Branding](docs/branding.md): identity and asset usage.
- [Roadmap](docs/roadmap.md): approved scope and milestone gates.
- [Setup](docs/setup.md), [providers](docs/providers.md), and [validation](docs/validation.md): environment, free-only operation, and evidence.

## Approved direction

Liltide is a personal-use-first, open-source Python CLI for Polish-to-English captions from computer audio. Lectures take priority. Target Windows, macOS, and Linux; a PySide6 GUI follows a validated CLI. Native apps, offline inference, and additional languages are deferred.

Keep Python 3.11+, a `src` package layout, Typer/Rich, SoundCard, NumPy with a dedicated resampler, and the Azure Speech SDK as the baseline. Keep capture, session coordination, providers, presentation, and exports separate. Permit a combined transcription/translation provider.

Use the Liltide name, approved blue `#3a7eab`, red `#cf4832`, and gray `#d1d3d4` palette, system typography, accessible status labels, and factual writing. The package and command identifier is `liltide`, subject to eventual availability checks.

## Authorization and scope

- Ask before substantive changes to approved product scope, branding, architecture, provider policy, or licensing. Explain the concrete proposed change. Do not seek repeated approval for routine fixes or implementation choices within approved decisions.
- Initial cloud operation is **Azure Speech F0 only**. Never provision paid resources, upgrade tiers, add paid fallbacks, or run billable tests under implied authorization. Live tests must be explicitly invoked against a user-configured F0 resource.
- The user authorized milestone 1 and then milestone 2: the capture CLI, Azure streaming adapter, WAV replay, bilingual captions, and pause/resume. The user subsequently authorized opt-in finalized text/JSONL exports as the first part of milestone 3. The user also authorized bounded connection recovery/gap records and caption arrival-time instrumentation, and export run-configuration metadata. Keep metadata allowlisted; never reflect credentials, environment values, device/file identifiers, or region into headers. Distinguish callback/handler measurements from estimated source-end delay; never present estimates as benchmark latency. Retry only structured transient failures within the run-wide three-attempt limit; known authentication/quota errors never trigger retries or paid fallback. Live cloud tests still require explicit invocation against operator-confirmed F0; do not run them merely because implementation is authorized. Do not interpret planned commands or unchecked roadmap tasks as implemented features or authorization to implement later milestones.
- On 2026-10-29 the user authorized stage one of the PySide6 GUI PoC: device/source selection, Start/Stop, and bilingual provisional/final captions reusing the session core. Optional GUI dependency only; F0 confirmation and environment credentials remain mandatory. Do not infer authorization for later GUI stages from this task. Deferred release validation remains open.
- The user subsequently authorized GUI stage two: pause/resume, bilingual/English-only display switching, and explicit session states. Reuse core pause semantics (resource release, fresh context, finalized-text retention); view changes affect presentation only. Later export/styling stages still require a separately authorized task.
- The user subsequently authorized GUI stage three: optional text/JSONL destinations, a timing display toggle, and last-session caption/timing summaries. Reuse the durable exporter and timing calculations; keep exports opt-in and independent of view/timing toggles. Preserve session metadata/gaps and fail before capture/provider startup on invalid destinations. Styling remains a later task.
- The user subsequently authorized GUI stage four branding/usability: approved palette and original symbol, System/Light/Dark themes, grouped layout, caption sizing, and keyboard navigation. Keep appearance changes independent of session/provider/export state and local to the window; no persisted settings or OS appearance changes. Floating captions remain a separate later task. Packaged brand symbol must match the authoritative asset in `assets/brand/`.
- The user subsequently authorized floating captions after pushing the pending branding/dropdown fixes. Treat the floating window as a presentation-only view of the same session: no second capture/provider, no implicit exports, close hides it, main-window shutdown still waits for cleanup. Synchronize language/font/theme controls and keep finalized/provisional labels explicit.
- Do not publish the repository, register names, or contact third parties without explicit authorization.
- On 2026-10-29, the user authorized identifier-safe parent/child diagnostics and exact macOS persistent-device identity resolution after investigation. Retain the selected UID in memory across capture contexts; fail closed on missing/ambiguous/unreadable identity, without name/default fallback or identifier exports/logs. This does not resume the separately deferred SEC-01 GUI Refresh selection repair or other security work.
- The user subsequently authorized [automated GitHub checks](docs/ci.md): offline tests/builds, dependency advisories, committed secrets, and local documentation links. Keep Actions permissions read-only, actions pinned to full SHAs, scanner downloads checksum-verified, and checkout credentials unpersisted. No cloud credentials, audio capture, deployment, or publishing in CI. Do not add scanner suppressions to hide findings; report hosted jobs as unverified until actually run. Branch protection/settings changes require a separate request.
- The user subsequently authorized main protection and hosted-evidence/badge documentation. Main now requires pull requests, an up-to-date branch, and all five [required GitHub Actions checks](docs/ci.md#required-checks-on-main), enforced for administrators; force pushes/deletion are disabled and approval-review count is zero. Use feature branches and PRs for future publication; do not push directly to main or disable/bypass protections. Preserve exact required job names; further protection-policy changes require user authorization.

## Evidence and privacy

- Distinguish planned, implemented, and verified behavior. Never infer Windows/Linux support from a macOS run or source inspection. Record OS, architecture, runtime, and test details for platform claims.
- Use fake providers for automated application tests. Add meaningful tests for behavior and failure boundaries; do not add tests merely mirroring implementation.
- Do not commit credentials, `.env` values, personal recordings, transcripts, exports, or identifying diagnostic logs. Use synthetic/redacted fixtures. Ignore rules are a guardrail, not a security guarantee.
- No raw audio or transcript saving by default. No hidden telemetry. Preserve finalized text in memory on recoverable failures; disk persistence remains explicit.
- External pricing and SDK claims need official sources and a verification date. Local usage estimates cannot guarantee free-only billing.

## Deferred validation

On 2026-10-29, the user deferred the long-session test (delay, memory, pause/resume, exports, one network interruption), reference-audio accuracy review (missing words, numbers, meaning), and Windows/Linux setup/capture validation because they cannot perform them now. Track these as future work in the roadmap/context. Do not repeatedly ask the user to perform them or initiate them without later authorization. Continue other authorized development; do not mark the deferred checks as passed or claim the corresponding release/quality evidence exists.

## Handoff

On 2026-10-29, the user initially deferred security work, then explicitly resumed SEC-01/02/03 repairs and installer upgrades. Preserve explicit initial device selection and clear lost/ambiguous selections; match persistent identities when retaining macOS selections. Escape untrusted controls at terminal/text boundaries, preserve decoded JSONL data, and keep installer/advisory checks current. Track repair evidence and remaining hardening in the [security follow-up](docs/roadmap.md#security-follow-up) and [review](docs/security-review.md). Additional hardening suggestions remain future work; completing these repairs does not establish comprehensive security.

After each meaningful development task, update [CONTEXT.md](CONTEXT.md) with completed work, actual verification, limitations/blockers, and next steps. Keep it concise; link to specifications instead of copying them. Update authoritative guides when behavior changes. Do not mark planned tests as passed or replace missing measurements with targets.
