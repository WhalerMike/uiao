<!-- authorities:book-ddi-servicenow — generated from orgcomp-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-5 | Access Restrictions for Change | Separation-of-duties gate in the catalog approval flow (requester ≠ approver) over DDI changes | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Identity | KSI-IAM | No |
| AU-2 | Event Logging | Immutable request/approval/apply/validation audit trail emitted from the ServiceNow closed loop into the evidence contract | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-26-14 | Telemetry | KSI-MLA | No |
| CM-3 | Configuration Change Control | Service Catalog → Flow Designer approval/SoD → Terraform apply → validation gate → CMDB close: DDI provisioning gated by an approved, audited change record | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB Circular A-130 | Security / supply chain | KSI-CMT | No |

: Authorities Closed Here — ServiceNow Orchestration — Governed Front Door for DDI († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}
