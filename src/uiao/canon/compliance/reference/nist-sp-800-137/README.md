# NIST SP 800-137 — Information Security Continuous Monitoring (ISCM) for Federal Information Systems and Organizations

## Provenance

| Field | Value |
|---|---|
| Document | NIST Special Publication 800-137 |
| Title | Information Security Continuous Monitoring (ISCM) for Federal Information Systems and Organizations |
| Authority | National Institute of Standards and Technology (NIST) |
| Retrieved | 2026-04-14 |
| Retrieved by | Michael Stratton (owner) |
| Local copy | `NIST.SP.800-137.pdf` |
| Upstream URL | https://nvlpubs.nist.gov/nistpubs/legacy/sp/nistspecialpublication800-137.pdf |
| License | U.S. Government work — public domain (17 U.S.C. § 105) |
| Verified against source | pending — see `uiao-core/ARCHITECTURE.md` §16.9 for UNSURE markers requiring verification |

## How UIAO uses this document

This publication is the canonical authority for the UIAO Information Security Continuous Monitoring (ISCM) program, implemented via the Conformance Adapter class (see `uiao-core/ARCHITECTURE.md` §3.5 and §16).

Primary references into this document:

- **§16.2 — ISCM lifecycle mapping.** Six-step lifecycle (Define → Establish → Implement → Analyze/Report → Respond → Review/Update) anchors adapter-registry lifecycle and CI workflow design.
- **§15.2 — ISCM capability matrix.** Capability categories (Configuration Management, Vulnerability Management, Patch Management, Event Management, Asset Management, Network Management, Malware Detection, Information Management, License Management, Software Assurance) drive conformance adapter roadmap.
- **§16.5 — Conformance adapter roadmap.** ScubaGear satisfies Configuration Management (M365 control plane) and IAM capabilities; additional adapters (`vuln-scan`, `patch-state`, `stig-compliance`) are slot-reserved to close the capability gap.

## Update policy

- **Monitoring cadence:** See `uiao-core/CONMON.md` §Reference Monitoring for the scheduled task pattern.
- **Replacement policy:** Superseding revisions (if NIST issues SP 800-137A, Rev 1, etc.) must be vetted by the `canon-steward` subagent, stored alongside this copy with a new subdirectory, and diffed against this revision before canon updates are accepted.
- **Never delete:** Historical revisions are retained for audit traceability.

## File integrity

```
File: NIST.SP.800-137.pdf
Size: 986,916 bytes
```

SHA-256 checksum should be generated and committed alongside the PDF on first commit. Checksum file naming: `NIST.SP.800-137.pdf.sha256`.
