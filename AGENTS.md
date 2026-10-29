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
- Do not publish the repository, register names, or contact third parties without explicit authorization.

## Evidence and privacy

- Distinguish planned, implemented, and verified behavior. Never infer Windows/Linux support from a macOS run or source inspection. Record OS, architecture, runtime, and test details for platform claims.
- Use fake providers for automated application tests. Add meaningful tests for behavior and failure boundaries; do not add tests merely mirroring implementation.
- Do not commit credentials, `.env` values, personal recordings, transcripts, exports, or identifying diagnostic logs. Use synthetic/redacted fixtures. Ignore rules are a guardrail, not a security guarantee.
- No raw audio or transcript saving by default. No hidden telemetry. Preserve finalized text in memory on recoverable failures; disk persistence remains explicit.
- External pricing and SDK claims need official sources and a verification date. Local usage estimates cannot guarantee free-only billing.

## Deferred validation

On 2026-10-29, the user deferred the long-session test (delay, memory, pause/resume, exports, one network interruption), reference-audio accuracy review (missing words, numbers, meaning), and Windows/Linux setup/capture validation because they cannot perform them now. Track these as future work in the roadmap/context. Do not repeatedly ask the user to perform them or initiate them without later authorization. Continue other authorized development; do not mark the deferred checks as passed or claim the corresponding release/quality evidence exists.

## Handoff

After each meaningful development task, update [CONTEXT.md](CONTEXT.md) with completed work, actual verification, limitations/blockers, and next steps. Keep it concise; link to specifications instead of copying them. Update authoritative guides when behavior changes. Do not mark planned tests as passed or replace missing measurements with targets.
