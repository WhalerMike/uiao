<!-- authorities:book-ddi-xplat — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-8 | System Component Inventory | IPAM as the authoritative multi-cloud address/subnet inventory (CM-8 join key) reconciled across per-CSP discovery adapters | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 23-01 | Network | KSI-PIY | No |
| SC-20 | Secure Name/Address Resolution (Authoritative) | One authoritative Infoblox DDI naming plane spanning Azure/AWS/GCP/OCI/VMware, per-cloud discovery adapters reconciling to it | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA TIC 3.0 | Network | KSI-CNA | No |
| SC-22 | Architecture / Provisioning for Name/Address Resolution | HA/anycast DDI service architecture with fault-tolerant resolution across cloud boundaries | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Network | KSI-CNA | No |

: Authorities Closed Here — Cross-Platform Operations & Multi-Cloud Governance († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

