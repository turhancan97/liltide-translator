# Security review — 2026-10-29

Reviewed application snapshot: `4ee1b595f8d5566bc67c7ae686332b56ff6d72ad`.
Status: the initial findings below describe the reviewed snapshot. The user initially deferred repairs, then resumed them on 2026-10-29. SEC-01/02/03 are now remediated in the working tree/local environment with the verification below; additional hardening remains [future work](roadmap.md#security-follow-up). The initial review itself changed no application code/environment.

## Repair verification — 2026-10-29

- **SEC-01:** GUI requires an explicit first input choice. Refresh clears a lost selection and prevents worker creation until the user chooses again. Stored persistent UID, rather than numeric ID alone, retains the same macOS device through refresh/reordering/reassignment. Synthetic GUI tests cover a microphone remaining, empty lists, numeric-ID reuse, and identity-preserving renumbering. No microphone was opened for these tests.
- **SEC-02:** Only the project's local virtual-environment pip was upgraded, from 25.2 to 26.2.2. pip-audit 2.10.1 rescanned 37 distribution records, skipped editable Liltide, and reported zero advisory rows. This closes the six installer findings for this scanned environment; it does not upgrade other users or comprehensively scan native bundled libraries. See patched [pip release information](https://pip.pypa.io/en/stable/news/).
- **SEC-03:** C0/C1 controls and embedded field line separators are rendered visibly in terminal captions (provisional/final), status/errors, device listing and text exports. App-generated layout newlines remain. JSONL escapes C1/separators in addition to standard JSON C0 escaping, preserving decoded original values and normal Polish UTF-8. Synthetic ESC/OSC/CSI, CR/backspace, NUL/DEL, tabs, line-break spoofing, and Unicode tests use memory buffers/temporary files, never interactive terminal payloads. Existing private exports are not rewritten.

The full offline suite and documentation/build verification are recorded in [validation](validation.md#security-fixes--2026-10-29). Bandit 1.9.4 rescanned production source with zero findings/errors. These repairs are not a security certification. No live capture/cloud test was run in this repair task; other platform, Git-history, native-library, and account-configuration limits still apply.

## Scope and evidence

Reviewed audio selection, subprocess boundaries, credentials, WAV input, captions, GUI presentation, and exports on the existing macOS arm64/Python 3.13.7 development environment. Used synthetic data and fake workers only: no recording, playback, live Azure request, or account inspection.

| Check | Result | Limits |
| --- | --- | --- |
| Bandit 1.9.4, recursive `src/liltide` scan | Zero findings/errors; 1,957 source lines scanned | Does not establish absence of vulnerabilities |
| pip-audit 2.10.1, installed `.venv` packages | 37 dependency records, including skipped editable Liltide; six distinct advisories affecting pip 25.2 | Scanner emitted 12 advisory rows, paired duplicates by advisory/aliases; native bundled libraries are not comprehensively covered |
| Synthetic GUI device-loss probe | Lost virtual selection silently replaced by remaining microphone; Start accepted it | Fake worker; no microphone capture or transmission performed |
| Synthetic terminal/export probe | Raw ESC characters survived Rich rendering and plain-text export | Output captured in memory; no terminal control sequence executed |
| Tracked working-tree secret heuristics | No matches across 58 tracked paths | Limited private-key, GitHub-token, AWS-ID and Azure-key assignment patterns; not full entropy detection, history scanning, or proof that no secrets exist |

Scanners were installed into an isolated temporary environment, not the project environment. Dependency metadata was queried against public advisory data; source code and private exports were not uploaded. The existing 225-test result predates this audit; the full application suite was not rerun for this documentation-only task.

## Original findings, in recommended repair order

### SEC-01: lost GUI input selection can silently select a microphone

**Priority: fix first. Impact: unintended audio disclosure. Assessment: medium privacy risk; reproduced selection/start behavior, not demonstrated remote exploitation.**

In [gui_window.py](../src/liltide/gui_window.py), `populate_devices()` (lines 416–425 in the reviewed snapshot) clears the combo box and inserts devices. If the previous ID has disappeared, Qt selects the first new item automatically. `start_session()` (427–456) accepts that replacement. On macOS, both virtual inputs and physical microphones are listed as `routed input`; [audio.py](../src/liltide/audio.py) cannot distinguish them using its current metadata.

Offline reproduction: populate a synthetic microphone and virtual input; explicitly select the virtual input; remove it from the available list; repopulate. The selected ID becomes the microphone while the source selector remains “System audio.” With synthetic credentials and a fake worker, Start passes the replacement microphone ID to the worker without explicit reselection.

If a real device disappears or enumeration changes, a user intending to translate computer audio could therefore start microphone capture and send ambient conversation to Azure. Device loss/reordering is enough to trigger the privacy hazard; no attacker control of device metadata was demonstrated. This is separate from the earlier intermittent CoreAudio ID failure, whose cause remains unconfirmed.

**Repair:** preserve the previous exact selection when present. When it disappears, clear the selection, show an explicit device-loss message, and require deliberate selection before Start. Do not substitute a name, default device, or first input. Consider requiring deliberate initial selection as well. On macOS, explain that the user must select the configured virtual device.

**Acceptance:** fake GUI tests must cover lost virtual input with a microphone remaining, reordered lists with the original ID still present, and an empty list. Lost selection must prevent worker creation until deliberate reselection. No real audio or cloud call is needed.

### SEC-02: installed package installer has known advisories

**Priority: update tooling before further installations. Impact: installation/download integrity; prerequisites vary by advisory.**

The local `.venv` contains pip 25.2. The six unique advisories below were matched by the scanner and checked against the Python Packaging Authority advisory database on 2026-10-29. They affect the installer; they are not evidence that listening to audio exploits Liltide.

| Advisory | Relevant condition | Fixed pip version |
| --- | --- | --- |
| [CVE-2025-8869](https://github.com/pypa/advisory-database/blob/main/vulns/pip/PYSEC-2026-1795.yaml) | Fallback tar extraction on Python without PEP 706 support; the reviewed Python 3.13 interpreter avoids this fallback | 25.3, with the advisory's Python-version caveat |
| [CVE-2026-1703](https://github.com/pypa/advisory-database/blob/main/vulns/pip/PYSEC-2026-1796.yaml) | Crafted wheel paths can escape the installation directory within constrained prefixes | 26.0 |
| [CVE-2026-3219](https://github.com/pypa/advisory-database/blob/main/vulns/pip/PYSEC-2026-2875.yaml) | Ambiguous concatenated tar/ZIP archives | 26.1 |
| [CVE-2026-6357](https://github.com/pypa/advisory-database/blob/main/vulns/pip/PYSEC-2026-2876.yaml) | Deferred self-update imports after installing untrusted modules | 26.1 |
| [CVE-2026-8643](https://github.com/pypa/advisory-database/blob/main/vulns/pip/PYSEC-2026-196.yaml) | Unsanitized script entry-point paths during installation | 26.1.2 |
| [CVE-2026-13346](https://github.com/pypa/advisory-database/blob/main/vulns/pip/PYSEC-2026-3721.yaml) | Doubly encoded URLs from a malicious package index | 26.2 |

**Repair:** upgrade pip in development/bootstrap environments to a current patched release, then rerun the audit. Version 26.2.2 is listed in the [official pip changelog](https://pip.pypa.io/en/stable/news/) on the review date. This was not installed into the project environment during the audit. Keep package sources trusted; upgrades do not make arbitrary package installation safe. pip is not a Liltide runtime dependency, so adding it to application dependencies would not solve this finding.

**Acceptance:** verify the environment's pip version, rerun pip-audit against that environment, and assess any remaining advisories by prerequisites. Repeat on release/build environments; this scan only covers the installed development snapshot.

### SEC-03: terminal control characters are not neutralized

**Priority: harden output. Assessment: low, conditional injection risk.**

[terminal.py](../src/liltide/terminal.py), `CaptionRenderer.caption()` (55–70), wraps caption strings in Rich `Text`. This prevents Rich markup interpretation but does not remove ESC sequences. [exports.py](../src/liltide/exports.py), `TranscriptExports.caption()` (70–98), also writes caption text directly into plain-text files. Device/status output should be included in the repair review.

A synthetic caption containing an OSC-style ESC sequence retained its raw ESC bytes in both an in-memory terminal rendering and a temporary text export. JSONL serialization escapes control characters in the file. Depending on terminal capabilities, malicious terminal controls can manipulate displayed output or terminal features when emitted directly or when a text file is printed with `cat`.

Exploitation requires an attacker-controlled string to reach these sinks. The audit did not establish that normal Azure recognition can produce such characters, that OS device names preserve them, or that any shell command or clipboard operation can be triggered in the user's environment. This is not a demonstrated remote code execution finding.

**Repair:** use a shared, tested output sanitizer at terminal and plain-text presentation boundaries. Render dangerous C0/C1 controls and ANSI/OSC initiators visibly, preserving ordinary Unicode Polish text and intentional formatting. Keep JSONL a properly escaped structured format; consider line-break spoofing in human-readable exports as part of the same repair.

**Acceptance:** tests with synthetic ESC/OSC/CSI, carriage-return, backspace, embedded line breaks, and Polish Unicode must verify safe terminal/text bytes and readable captions. Run these tests using memory buffers, never an interactive terminal payload.

## Additional hardening opportunities

These are follow-up improvements, not demonstrated exploits:

- Automated dependency and committed-secret checks now [pass in hosted CI](ci.md), with required PR/check protection on `main`. A documented private reporting route and tested constraints/lock snapshot remain future work. Broad dependency ranges alone are not a vulnerability.
- Document subprocess isolation accurately: spawned capture/provider processes are crash isolation, not an OS security sandbox. Review inherited environment variables so capture-only workers receive no unnecessary credentials.
- Consider a deliberate retention limit for in-memory session/history data. Audio queues are bounded, but finalized text and GUI history can grow during prolonged use. No remotely exploitable memory-exhaustion attack was demonstrated.
- Validate Windows export ACLs and native dependency security separately. POSIX mode `0600` was observed locally; it does not establish Windows confidentiality.

## Controls checked and remaining limits

Export creation uses exclusive creation (`O_EXCL`), rejects existing files/symlinks, and creates owner-only files on this POSIX host; the probe observed mode `0600`. JSONL uses JSON serialization rather than string concatenation. GUI transcript rendering uses plain-text widgets. The reviewed production paths do not execute caption strings through a shell or evaluate them as Python. These controls reduce particular risks; they do not certify the application as secure.

This was source review, advisory matching, and focused offline reproduction, not an independent penetration test. Git history, operating-system permissions, cloud-account configuration, all native SDK/Qt components, future dependency resolutions, and Windows/Linux execution were not comprehensively audited. No critical/high remote compromise path was confirmed within this scope. Recheck the report after repairs and dependency changes.

## Public exposure recheck — 2026-10-30

Audited the public repository at main commit `9c9df4d` after PR #8 merged. No credentials or private audio/transcript artifacts were found in the checked surfaces. This is scan evidence, not a guarantee against every secret format or a check of the Azure account itself.

- Fresh public Git mirror: 31 reachable commits, main/remaining advertised branch and all eight PR-head refs. Gitleaks 8.30.1 scanned all history with default rules, complete redaction, no repository allowlists/inline suppression; zero findings. The independent local all-ref history scan also returned zero. Scanner archive SHA-256 was verified against the official release digest and the executable matched the verified archive.
- All 83 historical file paths checked: no exports, recordings, transcript files, `.env` credentials, private-key files or generated app/environment directories were committed. An independent scan of historical text blobs found zero standalone Azure-style 32-hex candidates. This pattern check is supplemental, not a complete definition of Azure credentials.
- All 26 available public workflow log archives downloaded and scanned: 858 log files. Public issue/PR bodies, issue comments, review comments, commit comments, review records for all eight PRs and commit messages were also scanned. Combined public text: 7,140,534 bytes; zero Gitleaks findings. Three currently published PNG brand assets were visually inspected and contained brand/concept artwork rather than credentials or private session screenshots.
- GitHub secret-scanning API returned no alerts; latest main hosted secret scan passed. No release assets or Actions artifacts were present; Pages/discussions were disabled and no wiki repository was found. These statements describe the observed repository state on this date.
- **Privacy finding:** a personal Gmail address is publicly present in Git author/committer metadata. Its value is deliberately omitted here. GitHub's no-reply author address can be used for future commits if desired; that does not remove already published author metadata. No author-email configuration or public-history rewrite was performed.

Public content was downloaded only to an isolated temporary audit folder. No Azure keys were retrieved from Keychain, no raw credentials were printed, and no capture/cloud session, resource change, credential rotation or repository-setting change was performed. Local evidence updates are not a public publication step.
