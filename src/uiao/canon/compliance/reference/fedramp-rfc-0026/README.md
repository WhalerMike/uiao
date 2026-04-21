# FedRAMP RFC-0026 — CA-7 Continuous Monitoring Expectations

## Provenance

| Field | Value |
|---|---|
| Document | FedRAMP RFC-0026 — CA-7 Continuous Monitoring Expectations |
| Authority | FedRAMP Program Management Office (PMO), U.S. General Services Administration (GSA) |
| Venue | `FedRAMP/community` GitHub discussions |
| Discussion URL | https://github.com/FedRAMP/community/discussions/130 |
| Retrieved | 2026-04-21 |
| Retrieved by | Michael Stratton (owner) |
| Comment period close | 2026-04-22 |
| Status at retrieval | RFC in active comment |
| License | U.S. Government work — public domain (17 U.S.C. § 105) |

Because RFC-0026 is an active GitHub discussion rather than a released
PDF, there is no binary artifact to check in here. The canon anchor is
the discussion URL above. If and when FedRAMP publishes a stable
release document (expected alongside the VDR / CCM Balance Improvement
Releases), it should land in this directory with a SHA-256 checksum
following the pattern in `../fedramp-conmon-playbook/`.

## Requirements summarized

| Requirement | Name | Pathway 1 (modernized) | Pathway 2 (traditional) |
|---|---|---|---|
| **RV5-CA07-VLN** | Vulnerability Reporting | Implement Vulnerability Detection and Response (VDR) Balance Improvement Release | Monthly OS / Database / Web App / Container / Service Configuration scans **and** monthly POA&M updates **and** annual Independent Assessor scans |
| **RV5-CA07-CCM** | Collaborative Continuous Monitoring | Implement Collaborative Continuous Monitoring Balance Improvement Release | Host monthly ConMon meetings open to all agency customers per the Rev5 ConMon Playbook |

## Effective dates

- **2026-06-30** — gradual adoption begins.
- **2026-12-31** — grace period ends.
- **2027-01-01** — enforcement begins (five-strike ladder; 12-month reset).

## How UIAO uses this reference

This RFC is the authority for UIAO's CA-7 pathway posture, recorded in:

- **ADR-043** — `src/uiao/canon/adr/adr-043-fedramp-rfc-0026-ca7-integration.md`
  — the decision to adopt Pathway 2 by default with a gated migration
  to Pathway 1.
- **UIAO_132** — `src/uiao/canon/specs/fedramp-rfc-0026-ca7-integration.md`
  — the operational mapping of every RFC deliverable to a UIAO adapter,
  workflow, and evidence artifact.
- **`canon/adapter-registry.yaml`** — CA-7-tagged conformance adapters
  carry an advisory `fedramp-rfc-0026` block (promoted to schema when
  the RFC ratifies).

## Update policy

- **Monitoring cadence:** When the RFC reaches a stable release state
  (ratification or explicit supersession), re-diff UIAO_132 against the
  released language and supersede ADR-043 with a successor if material
  changes are required.
- **Replacement policy:** Published release artifacts (PDFs or tagged
  repo releases) land in a dated subdirectory (e.g.
  `fedramp-rfc-0026/2027-release/`) with checksums.
- **Cross-references:** This RFC coordinates with — but does not
  replace — the FedRAMP Rev 5 security baseline and the FedRAMP ConMon
  Playbook. See `../fedramp-rev5/` and `../fedramp-conmon-playbook/`.

## Notable commenter positions

Summarized in UIAO_132 §6. The repo owner's comment on the
point-in-time SCuBA / BOD 25-01 gap is answered by the Drift Engine
(UIAO_110) per ADR-043 D6 and UIAO_132 §4.

Do not modify files in this folder directly — treat as vendor/reference.
