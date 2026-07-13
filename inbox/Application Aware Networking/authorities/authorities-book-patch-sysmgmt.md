<!-- authorities:book-patch-sysmgmt — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-8 † | System Component Inventory | IPAM-keyed asset identity as the join key correlating all native-stack inventories (naming-plane necessity) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 23-01 | Network | KSI-PIY | No |
| RA-5 | Vulnerability Monitoring and Scanning | Assessment handoff FROM Book 11 (scan measures the gap; this book actuates remediation) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 22-01 | Endpoint | KSI-MLA | No |
| CM-2 | Baseline Configuration | Desired-state config baseline per platform (Azure Machine Config, SSM State Manager, Aria, Ansible) | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB Circular A-130 | Endpoint | KSI-CMT | No |
| CM-6 | Configuration Settings | Drift detection + reconciliation against the baseline; drift record to the evidence contract | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA SCuBA | Endpoint | KSI-CMT | No |
| SI-2 † | Flaw Remediation | Platform-native patch orchestration per CSP × OS (Intune/Arc, SSM, OS Mgmt Hub/Ksplice, vLCM, Satellite/Ansible) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 26-04; EO 14028 | Endpoint | KSI-SVC, KSI-MLA | No |
| SI-2(2) | Automated Flaw Remediation Status | Machine-readable remediation-status record emitted by each native stack into the unified evidence contract | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA CDM | Endpoint | KSI-SVC, KSI-MLA | No |
| SI-2(3) | Time to Remediate / Benchmarks | Remediation-SLA class per asset, keyed to KEV/exposure (BOD 26-04 four-variable model) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 22-01; CISA BOD 26-04 | Endpoint | KSI-SVC | No |

: Authorities Closed Here — Patch & Systems Management (multi-CSP SI-2/CM) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

