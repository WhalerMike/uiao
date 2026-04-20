# FedRAMP Continuous Monitoring Playbook

## Provenance

| Field | Value |
|---|---|
| Document | FedRAMP Continuous Monitoring Playbook |
| Authority | FedRAMP Program Management Office (PMO), U.S. General Services Administration (GSA) |
| Retrieved | 2026-04-14 |
| Retrieved by | Michael Stratton (owner) |
| Local copy | `FedRAMP_Continuous_Monitoring_Playbook.pdf` |
| Upstream URL | https://www.fedramp.gov/resources/documents/Continuous_Monitoring_Playbook.pdf |
| License | U.S. Government work — public domain (17 U.S.C. § 105) |
| Verified against source | pending — see `uiao/ARCHITECTURE.md` §16.9 for UNSURE markers requiring verification |

## How UIAO uses this document

This playbook is the canonical authority for FedRAMP ConMon cadence and deliverable obligations inside the UIAO federal pair. It anchors the operational rhythm for every conformance adapter.

Primary references into this document:

- **§16.3 — ConMon deliverable cadence.** Monthly vulnerability scans, monthly POA&M updates, quarterly STIG compliance, annual 3PAO assessment — all cadences in `uiao/ARCHITECTURE.md` §16.3 derive from this playbook and require verification.
- **§16.6 — POA&M feed.** `conmon-aggregate.yml` produces the POA&M CSV per the playbook's expected submission format; column mapping must match the current FedRAMP POA&M template.
- **§16.7 — Significant Change Request (SCR) evidence pattern.** Pre/post conformance runs produce the evidence pair expected by the playbook's SCR process.

## Update policy

- **Monitoring cadence:** See `uiao/CONMON.md` §Reference Monitoring for the scheduled task pattern.
- **Replacement policy:** FedRAMP publishes playbook revisions periodically. New versions must be vetted by the `canon-steward` subagent, stored alongside this copy with a dated subdirectory (e.g. `fedramp-conmon-playbook/2026-revision-X/`), and diffed against this revision before canon updates are accepted.
- **Cross-references:** This playbook coordinates with but is subordinate to the FedRAMP Rev 5 security baseline and the current FedRAMP PMO guidance memos. Those references live alongside this one under `compliance/reference/`.

## File integrity

```
File: FedRAMP_Continuous_Monitoring_Playbook.pdf
Size: 909,986 bytes
```

SHA-256 checksum should be generated and committed alongside the PDF on first commit. Checksum file naming: `FedRAMP_Continuous_Monitoring_Playbook.pdf.sha256`.
