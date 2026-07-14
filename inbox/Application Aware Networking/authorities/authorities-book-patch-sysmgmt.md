<!-- authorities:book-patch-sysmgmt — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-8 † | System Component Inventory | IPAM-keyed asset identity as the join key correlating all native-stack inventories (naming-plane necessity) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 23-01 | Network | KSI-PIY | No |
| RA-5 | Vulnerability Monitoring and Scanning | Assessment handoff FROM Book 11 (scan measures the gap; this book actuates remediation) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 22-01 | Endpoint | KSI-MLA | No |
| CM-2 | Baseline Configuration | Desired-state config baseline per platform (Azure Machine Config, SSM State Manager, Aria, Ansible) | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB Circular A-130 | Endpoint | KSI-CMT | No |
| CM-6 | Configuration Settings | Drift detection + reconciliation against the baseline; drift record to the evidence contract | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA SCuBA | Endpoint | KSI-CMT | No |
| SI-2 † | Flaw Remediation | Platform-native patch orchestration per CSP × OS (Intune/Arc, SSM, OS Mgmt Hub/Ksplice, vLCM, Satellite/Ansible) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 26-04; EO 14028 | Endpoint | KSI-SVC, KSI-MLA | No |
| SI-2(2) | Automated Flaw Remediation Status | Machine-readable remediation-status record emitted by each native stack into the unified evidence contract | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA CDM | Endpoint | KSI-SVC, KSI-MLA | No |
| SI-2(3) | Time to Remediate Flaws and Benchmarks for Corrective Actions | Remediation-SLA class per asset, keyed to KEV/exposure (BOD 26-04 four-variable model) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 22-01; CISA BOD 26-04 | Endpoint | KSI-SVC | No |

: Authorities Closed Here — Patch & Systems Management (multi-CSP SI-2/CM) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

**Closure-Necessity — alternate-path rebuttals (†).** For each necessity anchor, the strongest alternative a reviewer might propose and the specific reason it fails to close the control:

- **CM-8** — Strongest alternative: "The ServiceNow CMDB is the authoritative inventory." Fails CM-8 because a CMDB is a discovery-populated projection that must reconcile to an authoritative address/name identity to dedupe across clouds; you cannot inventory what you cannot enumerate, and only the IPAM/DDI naming plane enumerates every host by construction. The CMDB reconciles to it, it does not replace it.
- **SI-2** — Strongest alternative: "A single cross-platform scanner or patch console covers every OS." Fails SI-2 because a scanner detects but does not remediate, and cross-platform consoles still delegate the actual install to each platform native mechanism (Intune/Arc, SSM, vLCM, Ksplice); no remediation path bypasses the per-CSP-by-OS orchestrator.

