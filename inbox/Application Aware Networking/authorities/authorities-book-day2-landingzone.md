<!-- authorities:book-day2-landingzone — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-8 | System Component Inventory | Subnet/address allocation reconciled to the authoritative IPAM/DDI record (CM-8) at provisioning time — no landing zone stood up outside the naming plane | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 23-01 | Network | KSI-PIY | No |
| CM-3 | Configuration Change Control | Catalog approval → speculative Terraform plan → apply → validation gate → CMDB close as the CM-3 gate for landing-zone changes | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB Circular A-130 | Security / supply chain | KSI-CMT | No |
| CM-2 | Baseline Configuration | Landing-zone catalog request drives the change-controlled IaC pipeline (Terraform/Bicep) — deployed state equals reviewed source | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB Circular A-130 | Security / supply chain | KSI-CMT | No |

: Authorities Closed Here — Landing Zone Front Door (catalog → IaC → CMDB) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

