<!-- authorities:book-sn-aws — generated from orgcomp-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-6 | Configuration Settings | AWS Config / Security Hub CSPM findings raised as ServiceNow remediation tasks; Config-native remediation actuates, ServiceNow tracks to closure | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA SCuBA | Security / supply chain | KSI-CMT | No |
| RA-5 | Vulnerability Monitoring and Scanning | Security Hub CSPM / GuardDuty / Inspector findings on AWS workloads flow to ServiceNow Vulnerability Response as prioritized remediation tasks | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 26-04 | Security / supply chain | KSI-MLA | No |
| SI-2 | Flaw Remediation | AWS Systems Manager Patch Manager patch results reconciled into ServiceNow Change/Incident with SLA-class tasks keyed to KEV/exposure (actuation platform-native) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 26-04 | Endpoint | KSI-SVC, KSI-MLA | No |

: Authorities Closed Here — AWS Federal Control Compliance Automation († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}
