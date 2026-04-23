# E1 Design Memo — Connect.gov POA&M Submission Automation

**Roadmap entry:** [`docs/docs/uiao-rfc-0026-roadmap.md`](uiao-rfc-0026-roadmap.md) § E1
**Canon ref:** UIAO_132 Open Item O1; ADR-043 N3
**Status:** **DRAFT — review-only, no implementation yet**
**Date:** 2026-04-23
**Target delivery:** 2026-10-31 (60-day buffer before 2027-01-01 enforcement)

---

## Why this memo exists

The roadmap's T1.1 is *"Confirm Connect.gov upload API (REST vs SFTP; auth scheme; endpoint)"*. Until that confirmation lands, UIAO can't write implementation code that won't need to be rewritten. This memo enumerates the three plausible backend shapes, names the decision points, and proposes a default path if confirmation does not arrive before the enforcement-clock buffer closes.

When the backend is confirmed, this memo's "Recommended path" section becomes the implementation spec and the remaining branches are struck out. No code in `src/uiao/` or `.github/workflows/` changes as a result of approving this memo.

---

## Goal

Automate the monthly POA&M upload to Connect.gov so that after 2027-01-01 UIAO never relies on an operator to manually transfer an artifact. UIAO_132 §2.3 names this as the only remaining manual step in the Pathway-2 fan-out.

**Definition of done:**

1. The evidence bundle produced by `conmon-aggregate.yml` lands at the Connect.gov destination within ≤24 hours of being generated.
2. A receipt (server-returned or system-captured) is written to `evidence/submissions/<yyyy-mm>/connect-gov-receipt.json`, signed into the same HMAC chain as the rest of the evidence pack.
3. A submission failure opens a `conmon-cure`-labelled issue within 72 hours (matching the UIAO_132 §2.2 critical-finding SLA).
4. A dry-run mode lets us exercise the workflow against a sandbox before the enforcement clock starts.

---

## Known knowns

| Fact | Source |
|---|---|
| Monthly POA&M upload is required under RFC-0026 RV5-CA07-VLN Pathway-2 | ADR-043 D2 |
| `conmon-aggregate.yml` already produces `exports/conmon/conmon-poam.csv` + summary JSON | `.github/workflows/conmon-aggregate.yml` |
| The POA&M CSV shape is a subset of the FedRAMP POA&M template with TODO columns | `scripts/conmon/aggregate.py` docstring |
| Enforcement strike 1 is eligible 2027-01-01 | RFC-0026, FedRAMP community #130 |
| UIAO's operator today runs the upload manually (UIAO_132 O1) | UIAO_132 |

## Known unknowns

These are the items that block code and that this memo cannot resolve without you:

1. **Transport.** Is Connect.gov's ingest surface a REST API, an SFTP endpoint, a web portal with per-CSP folders, or a combination? The public FedRAMP site shows the portal UI but has not been specific about programmatic ingest for the community at the time of this memo.
2. **Authentication.** API-key, OIDC/OAuth2, mTLS client cert, PIV-CAC, or portal-session cookies? Each has different secret-management implications for GitHub Actions.
3. **Bundle shape.** Does Connect.gov expect individual CSV files per artifact, a zip bundle, an OSCAL JSON drop, or all of the above? Order of upload (POA&M first vs SSP first vs parallel)?
4. **Sandbox.** Is there a Connect.gov test/staging environment UIAO can exercise against pre-enforcement? Without one, the first real upload risks being the first successful dress rehearsal on 2027-01-31.
5. **Receipt shape.** Does Connect.gov return a signed receipt, a submission ID, an email, or just an HTTP 200? The evidence chain shape depends on this answer.
6. **Retry semantics.** What does Connect.gov consider a duplicate? Is idempotent re-upload supported via a client-provided key, or must UIAO track submission state locally to avoid double-counts?

---

## Three candidate backend shapes

### Option A — REST API with bearer token

**Hypothetical shape.** `POST /v1/csps/{csp-id}/submissions` with a bearer token minted from an OIDC federation between GitHub Actions and Connect.gov, carrying a multipart upload of the OSCAL bundle + POA&M CSV.

**Pros.** Cleanest integration. GitHub's `permissions: id-token: write` enables OIDC without stored secrets. Receipt is a synchronous HTTP response.

**Cons.** Depends on Connect.gov actually exposing such an API — unconfirmed. Requires a Connect.gov-side OIDC trust anchor that may not exist.

**UIAO-side changes.**
- New `scripts/conmon/connect_gov_submit.py` with a REST client
- New workflow `.github/workflows/conmon-submit-poam.yml` triggered by the conmon-aggregate completion
- New secret (or OIDC claim mapping) in repo config
- Receipt: `evidence/submissions/<yyyy-mm>/connect-gov-receipt.json` contains the full HTTP response body + headers

### Option B — SFTP drop

**Hypothetical shape.** UIAO's GitHub Actions runner uploads via SFTP to `sftp://submissions.connect.gov/{csp-id}/<yyyy-mm>/` using an agency-provisioned SSH key.

**Pros.** Simple, battle-tested, matches how many federal upload workflows actually work today.

**Cons.** No synchronous receipt — UIAO has to treat successful `put` as the receipt. Secret-sprawl risk (SSH private key in GitHub secret storage).

**UIAO-side changes.**
- New `scripts/conmon/connect_gov_submit.py` wrapping `paramiko` or a similar SFTP client
- Same new workflow as Option A, different body
- New `CONNECT_GOV_SSH_KEY` secret + known-hosts pin
- Receipt: synthesized JSON with server-fingerprint, upload timestamps, and sha256 of uploaded bundle

### Option C — Portal-only with manual operator step (graceful degradation)

**Hypothetical shape.** Connect.gov only exposes a web portal. UIAO generates a signed, timestamped, hash-manifest "submission bundle" under `exports/conmon/submission-bundle/<yyyy-mm>/`, and the monthly workflow:
1. Emits the bundle
2. Posts a governance issue titled *"Manual Connect.gov upload required for `<yyyy-mm>`"*, linking to the artifact, with an SLA of 24 hours
3. Expects an operator to paste the Connect.gov submission ID back into the issue as a receipt
4. A follow-up workflow watches for the receipt, writes `connect-gov-receipt.json`, and closes the issue

**Pros.** Works *today* regardless of upstream API posture. Creates an auditable paper trail even when the human loop is required. Zero dependency on unconfirmed Connect.gov ingest.

**Cons.** Doesn't fully close UIAO_132 O1 — there's still a manual step. The SLA risk is "operator forgets to paste the receipt ID".

**UIAO-side changes.**
- New `scripts/conmon/submission_bundle.py` that produces a zipped, hash-manifested bundle of the month's POA&M + summary JSON + signed manifest
- Extension to `conmon-aggregate.yml` that opens the operator-task issue and attaches the bundle URL
- New `scripts/conmon/receipt_intake.py` that parses the operator's reply and writes the receipt file
- Receipt: `evidence/submissions/<yyyy-mm>/connect-gov-receipt.json` with the Connect.gov submission ID pasted by the operator + a timestamp of when the receipt was confirmed
- SLA check in a weekly workflow that escalates if a month's receipt is still missing after 5 business days

---

## Recommended path if mechanics do not arrive by 2026-09-01

**Build Option C now; upgrade to A or B when mechanics arrive.**

Rationale:
- Option C is *always valuable* even if the final answer is REST or SFTP — the submission-bundle artifact and signed hash manifest are useful in every world.
- Option C can be built with zero Connect.gov-side assumptions.
- When mechanics arrive, only the "upload" step needs to swap from "operator task" to "REST/SFTP call". The bundle, the hash manifest, and the receipt-ingestion logic all remain.
- Shipping Option C by the 2026-10-31 target means we start the enforcement clock with *a worse version of the right thing* rather than *the right version of nothing*.

---

## Task breakdown (revised from roadmap)

| Roadmap task | Blocked on user input | Can start now (Option C preamble) |
|---|---|---|
| T1.1 Confirm upload API | ✅ Yes — user action | — |
| T1.2 Build `conmon-submit-poam` workflow | Partial — final transport swap is blocked; the scaffold + bundle generation are not | Scaffold + trigger wiring |
| T1.3 Receipt verification + `connect-gov-receipt.json` | Partial — receipt shape depends on transport | Write the receipt-file schema + signing + HMAC chain now |
| T1.4 Failure-path 72h SLA issue | ❌ Not blocked | Build on the existing `conmon-sla-issues.json` pattern |
| T1.5 Dry-run mode | Partial — requires sandbox endpoint in A/B; no-op in C | Dry-run mode in C means "generate bundle but skip issue creation" |
| T1.6 Close UIAO_132 §2.3 O1 | ❌ Canon edit; needs transport-confirmed implementation first | Will follow |

**Net new work that can start without Connect.gov confirmation:**
- Submission-bundle generator + hash manifest + signing
- Receipt-file schema (JSON) + HMAC signing pattern
- Failure-path SLA issue template (identical to existing `conmon-cure` shape)

When mechanics arrive, the remaining work is the transport swap (< 1 day for REST, ~ 1 day for SFTP, ~ 0 for portal-only) plus sandbox dry-run validation.

---

## Open questions for the user

1. **Can you get a maintainer-level Connect.gov account** and confirm which of A / B / C best matches the current ingest surface? If yes, say so and I'll pause this memo.
2. **Is there an agency stakeholder** (your ConMon PM or ISSO) who has uploaded to Connect.gov in the last 6 months and can describe their path by example?
3. **Preference on Option C scope** if we have to fall back to it: do you want the workflow to *also* auto-email the operator (requires SMTP secret + PII-free audit trail), or leave notification at the GitHub-issue layer only?
4. **Security posture for secrets:** is GitHub Actions' native secret store acceptable for a Connect.gov credential, or does your tenant require HashiCorp Vault / Azure Key Vault / ACME integration?

Answer any of these inline in the PR review comments and I'll lock the memo into an implementation plan.
