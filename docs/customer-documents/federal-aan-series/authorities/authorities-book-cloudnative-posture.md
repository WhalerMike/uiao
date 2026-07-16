<!-- authorities:book-cloudnative-posture — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| CM-7 | Least Functionality | Container hardening + Kubernetes admission control (deny non-compliant workloads) | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Security / supply chain | KSI-SVC | No |
| SC-7 | Boundary Protection | Cloud network-exposure and attack-path analysis (CNAPP) — internet-reachable workloads flagged | FedRAMP Moderate | NIST SP 800-53 Rev 5; NIST SP 800-207 | Network | KSI-CNA | No |
| CM-6 | Configuration Settings | Cloud resource misconfiguration detection across CSPs (CSPM) — Defender for Cloud (Moderate default); Prisma Cloud/Wiz (High) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA SCuBA | Security / supply chain | KSI-CMT, KSI-SVC | No |
| RA-5 | Vulnerability Monitoring and Scanning | Agentless cloud-workload + container-image vulnerability scanning (CNAPP/CWPP) | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 22-01 | Security / supply chain | KSI-MLA | No |
| SA-11 | Developer Testing and Evaluation | Shift-left IaC and container-image scanning in CI (CNAPP code security) | FedRAMP Moderate | NIST SP 800-53 Rev 5; NIST SP 800-218 | Security / supply chain | KSI-SVC | No |
| SI-3 | Malicious Code Protection | Container / workload runtime threat detection | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Security / supply chain | KSI-MLA | No |

: Authorities Closed Here — Cloud-Native Security Posture & Containers (CSPM/CNAPP, K8s) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}
