<!-- authorities:book-sn-cmdb — generated from orgcomp-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-8 | System Component Inventory | ServiceNow CMDB populated by Discovery/Service Graph connectors and reconciled to the authoritative IPAM/DDI asset identity (CM-8 join key); DDI stays the SSOT, the CMDB is the workflow projection | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 23-01 | Network | KSI-PIY | No |
| CM-3 | Configuration Change Control | Change Management as the CM-3 gate: every compliance-affecting change to M365/Azure carries an approved, reviewable change record before actuation | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB Circular A-130 | Security / supply chain | KSI-CMT | No |

: Authorities Closed Here — CMDB Reconciliation & Asset Identity (reconciled to IPAM/DDI) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}
