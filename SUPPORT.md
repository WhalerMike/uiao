# Getting Help

UIAO is a pre-1.0 project. Support channels are intentionally limited and asynchronous.

## Decide where to ask

| Situation | Channel |
|---|---|
| **Security vulnerability** | [Private advisory](https://github.com/WhalerMike/uiao/security/advisories/new) — do NOT open a public issue. See [`SECURITY.md`](SECURITY.md). |
| **Reproducible bug** | [Bug report](https://github.com/WhalerMike/uiao/issues/new?template=bug-report.yml) — uses the structured form. |
| **Canon change proposal** | [Canon change request](https://github.com/WhalerMike/uiao/issues/new?template=canon-change-request.yml) — UIAO_NNN / ADR-NNN form. |
| **Adapter promotion request** | [Adapter activation](https://github.com/WhalerMike/uiao/issues/new?template=adapter-activation.yml) — checklist form. |
| **Governance drift** | [Governance drift](https://github.com/WhalerMike/uiao/issues/new?template=governance-drift.yml) — 5-class taxonomy form. |
| **Open-ended question / design discussion** | [GitHub Discussions](https://github.com/WhalerMike/uiao/discussions) |
| **Contributing** | Read [`CONTRIBUTING.md`](CONTRIBUTING.md) first — it covers setup, commit convention, canon protocol, and adapter activation. |

## What's a good question

Questions that get answered quickly include:

- **Version / commit SHA.** `git rev-parse HEAD` or the release tag. The substrate evolves fast; "on main" is not specific enough.
- **Actual vs expected behavior.** Error messages, stack traces, `uiao substrate walk` output.
- **Minimal reproduction.** The fewer steps, the faster the triage.
- **What you've already tried.** Saves reviewers from suggesting the thing you already did.

The issue templates are designed to prompt for all of this.

## What's not in scope for support

- **Running UIAO as a service** — UIAO is a substrate / library, not a hosted product. You self-host.
- **Agency-specific FedRAMP ATO work** — UIAO generates OSCAL artifacts and compliance scaffolding; the ATO process requires your agency's AO + a 3PAO. Those humans, not this repo, drive it.
- **General compliance questions** — if the question is "what does NIST SP 800-53 control AC-2 require?", the answer isn't in this repo. See the authority documents referenced in `core/CONMON.md`.

## Response expectations

- **Security issues:** 3 business days for acknowledgement, 7 for triage. See [`SECURITY.md`](SECURITY.md).
- **Other issues:** best effort, asynchronous. No SLA.

## Self-service

Before filing, consider:

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — setup, workflow, adapter activation
- [`CLAUDE.md`](CLAUDE.md) — substrate-level agent entry point
- [`CHANGELOG.md`](CHANGELOG.md) — "what changed recently"
- [`docs/docs/glossary.qmd`](docs/docs/glossary.qmd) — canonical vocabulary
- `uiao substrate walk` — validates your clone is intact
- `make help` (or `make` with no args) — lists common developer tasks
