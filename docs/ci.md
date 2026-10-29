# Automated repository checks

The [Checks workflow](../.github/workflows/checks.yml) runs on pushes, pull requests, and manual dispatch. It needs no Azure credentials, audio hardware, repository secrets, or Gitleaks license key. GitHub-hosted execution is unverified until the workflow is pushed and its first run completes.

| Check | What it verifies | What it does not establish |
| --- | --- | --- |
| Offline tests and build, Python 3.11/3.13 on Ubuntu 24.04 | Synthetic/fake-provider suite including offscreen GUI, dependency consistency, source distribution/wheel build, installed-wheel CLI help | Linux capture/playback, other OS support, actual Azure operation, or translation quality |
| Dependency advisories | Newly resolved application/dev/GUI distributions in an isolated Python 3.13 environment, including pip | Native bundled libraries or every Python/OS dependency resolution |
| Committed secrets | Gitleaks built-in rules over full available Git history plus checked-out HEAD; failures are redacted | Complete secret detection, uncommitted private files, or credential revocation |
| Local documentation links | Markdown file/image/reference targets and Markdown heading fragments, including duplicate headings | External URL availability, arbitrary HTML links/IDs, or perfect GitHub rendering equivalence |

Tests use synthetic providers and cleared Azure environment values. Installation and advisory queries use the network; the application tests do not intentionally open devices or contact Azure. A GUI import/offscreen preflight fails the job if PySide6 cannot load, rather than silently accepting skipped GUI tests. No artifacts, transcripts, scanner reports, or releases are uploaded.

## Workflow security and maintenance

The workflow uses `pull_request`, not `pull_request_target`, read-only `contents` permission, no persisted checkout credentials, timeouts, and per-ref cancellation. Official checkout/setup-python actions are pinned to full commit SHAs. Fork pull requests do not require project secrets; these jobs do not deploy or publish anything. Passing jobs do not make checks mandatory for merging: maintainers can configure branch protection/rulesets separately after the first successful hosted run.

Gitleaks CLI 8.30.1 is downloaded from its official release and verified against a pinned SHA-256 digest before extraction. A temporary explicit config extends its built-in rules; repository config/ignore files and inline `gitleaks:allow` comments cannot suppress this scan. The scan includes `--all HEAD` so synthetic pull-request merge commits and their ancestry are covered. It uses no findings baseline or credentials allowlist. Investigate failures with redacted output; do not commit real credentials to reproduce a finding. If a real credential is discovered, removing the text alone does not revoke it.

The advisory job freezes the exact installed application-environment distributions, excluding only the local Liltide project, then runs pip-audit 2.10.1 in a separate tools environment with strict collection handling. `--no-deps --disable-pip` audits that complete installed snapshot without resolving or installing another dependency tree. pip remains included. The snapshot is an audit input, not a committed reproducibility lock; other unknown/unauditable distributions are not silently ignored. It fails on known advisories or audit errors. It does not automatically upgrade dependencies or ignore findings. A new advisory can fail a later run even when application source is unchanged; there is no scheduled scan in this workflow.

Tool pins verified on 2026-10-29: checkout v7.0.1, setup-python v7.1.0, pip 26.2.2, Gitleaks 8.30.1, pip-audit 2.10.1, Markdown-it-py 4.2.0, and Hatchling 1.33.0. Actions/tools are pinned; runtime dependencies still resolve within the project ranges. A tested dependency lock/constraints snapshot remains future hardening. Review upstream release notes/advisories when updating pins, verify digests/SHAs, and rerun these checks. Primary references: [checkout](https://github.com/actions/checkout), [setup-python](https://github.com/actions/setup-python), [Gitleaks](https://github.com/gitleaks/gitleaks), and [pip-audit](https://github.com/pypa/pip-audit).

## Local verification

```console
python -m pip install -e ".[dev,gui]"
QT_QPA_PLATFORM=offscreen python -m pytest -q
python scripts/check_docs.py
python -m hatchling build
```

Install Hatchling separately to run the last command (`python -m pip install "hatchling==1.33.0"`). On Windows set `QT_QPA_PLATFORM` using your shell's environment syntax. The document checker reads tracked and unignored new Markdown files, skips fenced examples, rejects links escaping the repository, and never requests external URLs. GitHub-style Markdown heading fragments are supported; HTML anchors require a future extension.

For workflow syntax, the local review uses checksum-verified actionlint 1.7.12. For secrets/advisories, use the workflow's pinned scanner versions and flags. Keep scanners/tools separate from the application environment when auditing dependencies; never paste scanner output containing credentials into issues or commits.
