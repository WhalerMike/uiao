---
title: "Day-2 Kit — Live Validation Program RunBook"
subtitle: "ServiceNow PDI · Active Directory Lab · Microsoft 365 Tenant"
date: "Authored 2026-07-30 · repo commit 84bdb28ca · shipped in later kit builds unchanged"
---

# Executive summary

Five rounds of code-reading and mock-harness execution converged on the same
conclusion: every remaining open item in the Day-2 Automation Kit — the
`ecc_queue` insert ACL, the AD delegation itself, the SER-4 per-tenant Graph
scope wiring, the two `verify()` test-mode design questions, whether the
Terraform secrets-in-state exposure is reachable — is not a "read the code
harder" problem. Each requires either real infrastructure or a decision only
a human can make. No further round of AI-reviews-AI would find or fix any of
them.

This RunBook is the next step: three self-contained validation tracks, each
closing a gap the mock-harness/adversarial-review cycle could not, in the
order they should be run.

| Track | Closes | Needs |
|---|---|---|
| 1. ServiceNow PDI | Real platform ACL behavior, real ATF Test Runner execution, the `ecc_queue` insert-ACL review | A free, self-service PDI signup (~30 min) |
| 2. Active Directory Lab | Real AD write behavior, real delegated-rights enforcement, real filter/attribute-injection resistance | A local Hyper-V VM — no cloud account |
| 3. Microsoft 365 Tenant | SER-4: whether the compliance gate's Graph scope check actually reads a real tenant correctly | A free M365 Developer Program signup |

**What changed in the repo to make these runnable**, all committed at
`84bdb28ca` on `main`:

- Corrected doc/code drift: `CURRENT-STATE-START-HERE.md` and
  `CURRENT-STATE-SCRIPTS.md` still warned "do not point this at a live
  directory yet" for three defects that commit `7d2423c74` had already fixed —
  the warning was one commit stale. The ATF `README.md` documented 12 of the
  17 specs that exist on disk; now documents all 17.
- Implemented the SER-4 Graph scope read in `ComplianceGate._checkWriteScope`,
  which was previously a bare `TODO` unconditionally returning `'unverified'` —
  now reads `appRoleAssignments` / `oauth2PermissionGrants`, fails closed
  throughout, and ships with two new ATF specs proving the read-only/
  write-shaped verdicts against fixture data. **In the sibling `x_fed_compliance`
  scoped app, which this kit does not ship** — the change is real but is not
  verifiable from anything in this archive. It is listed because Track 3 (M365
  tenant) exercises it; if you are running only Tracks 1 and 2, it does not
  apply to you.
- Authored `lab/New-Day2AdLab.ps1` — a local Hyper-V lab-domain provisioner
  with no cloud-account dependency. It ships in this archive at
  `servicenow-day2/lab/`, one canonical copy; earlier builds also carried a
  byte-identical duplicate under `RunBook/`, which has been removed.

Each track below states, up front, what it proves and — just as
importantly — what it still does not prove. None of this is a substitute for
a real ATO. It substitutes for "an AI read the code and believes it's
correct."
