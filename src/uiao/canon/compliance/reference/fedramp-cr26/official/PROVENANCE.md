# PROVENANCE — FedRAMP Consolidated Rules for 2026 (Official)

## Source

| Field | Value |
|---|---|
| Repository | `FedRAMP/rules` |
| URL | https://github.com/FedRAMP/rules |
| File | `fedramp-consolidated-rules.json` |
| Raw URL | `https://raw.githubusercontent.com/FedRAMP/rules/main/fedramp-consolidated-rules.json` |
| Version | `2026.06.24.01` |
| Last updated | `2026-06-24` |
| Retrieved | `2026-07-01` |
| License | US Government work — public domain (17 U.S.C. § 105) |
| Authority | **Official** — published by the General Services Administration / FedRAMP PMO |

## File manifest

| File | SHA-256 | Size (bytes) |
|---|---|---|
| `fedramp-consolidated-rules.json` | `48d1fb4c1674c15f1a966f94c9f519b246af377d2ff51845083131ad99da8c60` | `568271` |

Verify: `sha256sum -c SHA256SUMS` from the `official/` directory.

## Document structure

The JSON contains four top-level sections:

| Section | Name | Count | Description |
|---|---|---|---|
| `FRD` | FedRAMP Definitions | 75 terms | Defined vocabulary for rules interpretation |
| `FRR` | FedRAMP Rules | 17 categories / 29 variants | Requirements across all/20x/rev5 paths |
| `KSI` | Key Security Indicators | 10 themes / 46 indicators | Continuous-validation evidence surface |
| `CTL` | Controls | 14 NIST families / 40+ controls | SP 800-53 rev5 control anchors |

## KSI themes

| Theme ID | Name | Indicators |
|---|---|---|
| KSI-CED | Cybersecurity Education | 1 |
| KSI-CMT | Change Management | 4 |
| KSI-CNA | Cloud Native Architecture | 8 |
| KSI-IAM | Identity and Access Management | 6 |
| KSI-INR | Incident Response | 3 |
| KSI-MLA | Monitoring, Logging, and Auditing | 5 |
| KSI-PIY | Policy and Inventory | 5 |
| KSI-RPL | Recovery Planning | 4 |
| KSI-SCR | Supply Chain Risk | 2 |
| KSI-SVC | Service Configuration | 8 |

**Total: 46 indicators**

## FRR rule categories

| Category | Name | Variants |
|---|---|---|
| AFC | Addressing FedRAMP Communication | all |
| AGU | Agency Use of FedRAMP Certified Cloud Services | all |
| CCM | Collaborative Continuous Monitoring | all |
| CDS | Certification Data Sharing | all, rev5 |
| CMU | Cryptographic Module Use | all |
| CPO | Certification Package Overview | all, 20x, rev5 |
| FRC | FedRAMP Certification | all, 20x, rev5 |
| IEC | Incident Evaluation and Communication | all |
| IVV | Independent Verification and Validation | all, 20x, rev5 |
| MAS | Minimum Assessment Scope | all |
| MKT | Marketplace Listing | all |
| REC | FedRAMP Recognition of Independent Assessment Services | all |
| SCG | Secure Configuration Guide | all |
| SCN | Significant Change Notification | all |
| SDR | Security Decision Record | all, 20x, rev5 |
| VDR | Vulnerability Detection and Response | all, 20x, rev5 |
| VER | Vulnerability Evaluation and Reporting | all, 20x, rev5 |

## Effective dates

| Action | Date |
|---|---|
| Optional adoption opens | 2026-07-04 |
| 20x Class B/C pipelines open | 2026-08-31 |
| Mandatory for all stakeholders | 2027-01-01 |
| No new Rev5 certifications accepted | 2027-06-11 |

## Relationship to Palladium snapshot

This official JSON is the **primary rules source** — plain text of requirements,
definitions, KSI statements, and control mappings in structured JSON.

The Palladium OSCAL snapshot at
`../snapshot/c31eb04c082d6d578a26a00de9a482707ab7a00c/` is a derived OSCAL
representation of an earlier Public Preview of this data. It remains in place for
OSCAL catalog/profile/mapping consumption per ADR-061 until superseded by an
official OSCAL publication from FedRAMP (see ADR-126 §D2).

## ADR governance

Authority posture, update discipline, and uiao consumption pattern are governed by
[ADR-126](../../../../adr/adr-126-fedramp-cr26-official-rules-adoption.md),
which fires ADR-061 re-evaluation trigger #1.

## How to refresh

When FedRAMP publishes a new version:

1. Download the new `fedramp-consolidated-rules.json` from
   `https://raw.githubusercontent.com/FedRAMP/rules/main/fedramp-consolidated-rules.json`.
2. Compute `sha256sum fedramp-consolidated-rules.json`.
3. Update `fedramp-consolidated-rules.json`, `SHA256SUMS`, and this file's
   version/date/hash fields in a single PR.
4. The prior file is replaced in-place (the version field in the JSON is the
   immutability identifier; there is no sibling-directory rotation for this
   official source — see ADR-126 §D2 for the rationale).
5. Run the `fedramp-cr26-catalog` conformance adapter (`uiao adapter-run
   fedramp-cr26-catalog`) to surface any `DRIFT-SCHEMA` or
   `DRIFT-PROVENANCE` findings caused by the update.
