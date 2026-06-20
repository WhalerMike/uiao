---
document_id: UIAO_188
title: "UIAO Personnel Security Program"
version: "1.0"
status: Current
owner: Michael Stratton
created_at: "2026-06-05"
updated_at: "2026-06-19"
publish_to_site: true
publication_style: include
---

# UIAO Personnel Security Program

> **Status: Current — authoritative template.** Agency-responsibility program template that closes the **PS (Personnel Security)** family — one of the four families Chapter 23 names as uncovered. The SSP ([UIAO_185](UIAO_185_System_Security_Plan_Template.md) §4) declares PS as an agency-responsibility program; this document is that program template. Covers `PS-1` through `PS-9`. Bracketed `[PLACEHOLDER]` fields are completed per authorizing agency. Tracked in [UIAO_184](UIAO_184_Gap_Closure_Register.md) (Workstream A).

## Purpose

Establish personnel-security controls governing how individuals are positioned, screened, and managed across the access lifecycle for a UIAO Governance OS deployment, satisfying `PS-1` through `PS-9` of NIST SP 800-53 Rev 5.

## §1 — Policy and procedures (`PS-1`)

The authorizing agency maintains a personnel-security policy reviewed at least annually. `[AGENCY POLICY REF]` is the governing instrument; this program is its UIAO-specific implementation.

## §2 — Position risk designation and screening (`PS-2`, `PS-3`)

- Each position with system access is assigned a risk designation (`[LOW/MODERATE/HIGH]`) per `PS-2`.
- Personnel are screened commensurate with the risk designation before access is granted, and re-screened at `[REINVESTIGATION INTERVAL]` per `PS-3`.

## §3 — Termination and transfer (`PS-4`, `PS-5`)

- **Termination (`PS-4`):** on separation, access is revoked within `[N]` hours; credentials disabled; the identity lifecycle state is set to OFFBOARDING/SUSPENDED. The drift engine flags any residual `accountEnabled=true` for a terminated identity as a `DRIFT-IDENTITY` lifecycle inconsistency.
- **Transfer (`PS-5`):** on role change, access is re-evaluated against the new position's risk designation and OrgPath; entitlements not justified by the new role are removed.

## §4 — Access agreements (`PS-6`)

Personnel sign access agreements (acceptable use, NDA as applicable, rules of behavior) before access and re-acknowledge at `[FREQUENCY]`. Records are retained as assessment evidence.

## §5 — External personnel (`PS-7`)

Third-party/contractor personnel are subject to equivalent screening and access-agreement requirements; the responsible provider and security requirements are documented per `PS-7`, consistent with the SR (Supply Chain Risk Management) program.

## §6 — Sanctions (`PS-8`) and position descriptions (`PS-9`)

- **Sanctions (`PS-8`):** a formal sanctions process applies to personnel failing to comply with security policies; invocation is coordinated with `[AGENCY HR / LEGAL]`.
- **Position descriptions (`PS-9`):** security responsibilities are documented in position descriptions.

## §7 — Gap linkage

Until the agency formally adopts this program, PS-family controls remain a **gap** recorded in the POA&M (`CA-5`). On adoption, the PS family moves from agency-responsibility-planned to satisfied in the SSP §3 disposition.

## References

- [UIAO_185](UIAO_185_System_Security_Plan_Template.md) — SSP (`PS` disposition, §4)
- [UIAO_187](UIAO_187_Security_Awareness_and_Training_Program.md) — Security Awareness & Training Program (paired AT family)
- [UIAO_184](UIAO_184_Gap_Closure_Register.md) — gap-closure register (Workstream A)
- [`compliance-mapping.qmd`](../../../docs/customer-documents/compliance/controls-testing/compliance-mapping.qmd) — `PS` gap analysis
