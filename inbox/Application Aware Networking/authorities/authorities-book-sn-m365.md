<!-- authorities:book-sn-m365 — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| AC-2 | Account Management | Joiner/mover/leaver and Conditional-Access exception requests raised, approved, and access-reviewed as ServiceNow tasks over the Entra estate | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-22-09 | Identity | KSI-IAM | No |
| CA-7 | Continuous Monitoring | M365 control-test results (Graph, SCuBA, Purview) ingested as attestation tasks feeding the KSI evidence pipeline | FedRAMP Moderate | NIST SP 800-53 Rev 5; NIST SP 800-137; FedRAMP 20x KSIs | Telemetry | KSI-MLA | No |
| CM-6 | Configuration Settings | SCuBA / secure-baseline drift on the M365 SaaS surface raised as a ServiceNow Incident/Change task and tracked to closure (actuation stays platform-native) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA SCuBA; CISA BOD 25-01 | Security / supply chain | KSI-CMT, KSI-SVC | No |

: Authorities Closed Here — M365 Federal Control Compliance Automation († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

