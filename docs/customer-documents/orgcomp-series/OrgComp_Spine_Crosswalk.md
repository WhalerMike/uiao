# AAN Spine-Derived Control Crosswalk

> **Generated file — do not hand-edit.** Produced by `render_crosswalk.py` from `orgcomp-compliance-spine.yml`. Regenerate when closures change; CI-gated by `orgcomp-authorities-drift.yml`.

## Coverage (stated honestly)

- This crosswalk is rendered from the **91 closure rows** the spine carries across **17 of 68 books**. It is the machine-derived slice of the series control crosswalk — **not** series-wide coverage. The hand-maintained master table in `Vol_0_Book_02_OrgComp_Control_Crosswalk.qmd` indexes the full 149 controls across all books; that superset is author-maintained until the spine back-fill reaches every book.
- It aggregates those closures into **53 distinct controls**. A control closed in several books lists each volume/book. As the spine is back-filled book by book, this table grows toward the full master automatically and cannot silently drift from the spine.

## Crosswalk

| Control | Title | Family | Where addressed (spine) | FedRAMP 20x KSI |
|---|---|---|---|---|
| AC-2 † | Account Management | AC | Vol I Bk 04, Vol VII Bk 02, Vol IX Bk 01, Vol IX Bk 03, Vol IX Bk 05 | KSI-IAM |
| AC-2(1) | Account Management | Automated System Account Management | AC | Vol I Bk 04, Vol IX Bk 05 | KSI-IAM |
| AC-2(3) | Account Management | Disable Accounts | AC | Vol IX Bk 05 | KSI-IAM |
| AC-2(4) | Account Management | Automated Audit Actions | AC | Vol IX Bk 05 | KSI-MLA |
| AC-3 | Access Enforcement | AC | Vol IX Bk 01, Vol IX Bk 05 | KSI-IAM |
| AC-4 | Information Flow Enforcement | AC | Vol I Bk 07, Vol IX Bk 05 | KSI-CNA, KSI-IAM |
| AC-5 | Separation of Duties | AC | Vol IX Bk 05 | KSI-IAM |
| AC-6 | Least Privilege | AC | Vol IX Bk 01, Vol IX Bk 03, Vol IX Bk 05 | KSI-IAM |
| AC-17 | Remote Access | AC | Vol I Bk 07 | KSI-CNA |
| AC-19 | Access Control for Mobile Devices | AC | Vol I Bk 07 | KSI-IAM |
| AC-20 | Use of External Systems | AC | Vol IX Bk 05 | KSI-IAM |
| AU-2 | Event Logging | AU | Vol VIII Bk 07, Vol IX Bk 04, Vol IX Bk 05 | KSI-MLA |
| AU-3 † | Content of Audit Records | AU | Vol III Bk 07 | KSI-MLA |
| AU-6 | Audit Record Review, Analysis, and Reporting | AU | Vol IX Bk 05 | KSI-MLA |
| AU-6(1) | Automated Process Integration | AU | Vol III Bk 07 | KSI-MLA |
| AU-12 | Audit Record Generation | AU | Vol III Bk 07 | KSI-MLA |
| AU-12(1) † | System-wide and Time-correlated Audit Trail | AU | Vol III Bk 07 | KSI-MLA |
| CA-2 | Control Assessments | CA | Vol VII Bk 04 | KSI-MLA |
| CA-3 | Information Exchange | CA | Vol IX Bk 05 | KSI-PIY |
| CA-5 | Plan of Action and Milestones | CA | Vol VII Bk 04 | KSI-MLA |
| CA-7 | Continuous Monitoring | CA | Vol III Bk 07, Vol VII Bk 02, Vol VII Bk 04, Vol IX Bk 05 | KSI-MLA |
| CM-2 | Baseline Configuration | CM | Vol III Bk 03, Vol IX Bk 02 | KSI-CMT |
| CM-3 | Configuration Change Control | CM | Vol VII Bk 01, Vol VIII Bk 07, Vol IX Bk 02, Vol IX Bk 04, Vol IX Bk 05 | KSI-CMT |
| CM-5 | Access Restrictions for Change | CM | Vol VIII Bk 07 | KSI-IAM |
| CM-6 | Configuration Settings | CM | Vol III Bk 03, Vol III Bk 04, Vol VII Bk 02, Vol VII Bk 03, Vol IX Bk 04 | KSI-CMT, KSI-SVC |
| CM-7 | Least Functionality | CM | Vol III Bk 04 | KSI-SVC |
| CM-8 † | System Component Inventory | CM | Vol III Bk 03, Vol VII Bk 01, Vol VIII Bk 06, Vol IX Bk 02, Vol IX Bk 05 | KSI-PIY |
| IA-2 | Identification and Authentication (Organizational Users) | IA | Vol IX Bk 05 | KSI-IAM |
| IA-3 † | Device Identification and Authentication | IA | Vol I Bk 07 | KSI-IAM |
| IA-4 † | Identifier Management | IA | Vol I Bk 04, Vol IX Bk 05 | KSI-IAM |
| IA-5 | Authenticator Management | IA | Vol IX Bk 01, Vol IX Bk 05 | KSI-IAM |
| IA-5(2) | Authenticator Management | Public Key-Based Authentication | IA | Vol IX Bk 03, Vol IX Bk 05 | KSI-IAM |
| PS-4 † | Personnel Termination | PS | Vol I Bk 04 | — |
| PS-5 † | Personnel Transfer | PS | Vol I Bk 04, Vol IX Bk 05 | KSI-IAM |
| RA-5 | Vulnerability Monitoring and Scanning | RA | Vol III Bk 03, Vol III Bk 04, Vol VII Bk 03 | KSI-MLA |
| SA-9 † | External System Services | SA | Vol IX Bk 05 | KSI-SCR |
| SA-9(2) | External System Services | Identification of Functions, Ports, Protocols, and Services | SA | Vol IX Bk 05 | KSI-SCR |
| SA-11 | Developer Testing and Evaluation | SA | Vol III Bk 04 | KSI-SVC |
| SC-7 | Boundary Protection | SC | Vol I Bk 07, Vol III Bk 04 | KSI-CNA |
| SC-7(8) | Route Traffic to Authenticated Proxy Servers | SC | Vol I Bk 07 | KSI-CNA |
| SC-8 † | Transmission Confidentiality and Integrity | SC | Vol I Bk 07 | KSI-CNA |
| SC-8(1) | Cryptographic Protection | SC | Vol I Bk 07 | KSI-CNA |
| SC-17 | Public Key Infrastructure Certificates | SC | Vol IX Bk 03, Vol IX Bk 05 | KSI-IAM |
| SC-20 † | Secure Name/Address Resolution Service (Authoritative Source) | SC | Vol I Bk 01, Vol VIII Bk 06 | KSI-CNA |
| SC-21 † | Secure Name/Address Resolution Service (Recursive or Caching Resolver) | SC | Vol I Bk 01 | KSI-CNA |
| SC-22 | Architecture and Provisioning for Name/Address Resolution Service | SC | Vol VIII Bk 06 | KSI-CNA |
| SI-2 † | Flaw Remediation | SI | Vol III Bk 03, Vol VII Bk 03 | KSI-MLA, KSI-SVC |
| SI-2(2) | Automated Flaw Remediation Status | SI | Vol III Bk 03 | KSI-MLA, KSI-SVC |
| SI-2(3) | Time to Remediate Flaws and Benchmarks for Corrective Actions | SI | Vol III Bk 03 | KSI-SVC |
| SI-3 | Malicious Code Protection | SI | Vol III Bk 04 | KSI-MLA |
| SI-4 | System Monitoring | SI | Vol I Bk 07 | KSI-MLA |
| SI-4(16) | Correlate Monitoring Information | SI | Vol III Bk 07 | KSI-MLA |
| SI-12 † | Information Management and Retention | SI | Vol I Bk 04, Vol IX Bk 05 | KSI-PIY |

*† = Closure-Necessity anchor (no alternate closure path; see the per-book alternate-path rebuttals in the authorities tables).*

## Control coverage by volume (spine)

Distinct controls the spine closes within each volume (a control closed in several volumes is counted in each).

| Volume | Distinct controls closed |
|---|---|
| Vol I | 17 |
| Vol III | 17 |
| Vol VII | 9 |
| Vol VIII | 6 |
| Vol IX | 26 |
| **Series total (distinct)** | **53** |

: Spine control coverage by volume {.striped}

## FedRAMP 20x KSI view (spine)

| FedRAMP 20x KSI | Controls mapped |
|---|---|
| **KSI-CMT** | CM-2, CM-3, CM-6 |
| **KSI-CNA** | AC-4, AC-17, SC-7, SC-7(8), SC-8, SC-8(1), SC-20, SC-21, SC-22 |
| **KSI-IAM** | AC-2, AC-2(1), AC-2(3), AC-3, AC-4, AC-5, AC-6, AC-19, AC-20, CM-5, IA-2, IA-3, IA-4, IA-5, IA-5(2), PS-5, SC-17 |
| **KSI-MLA** | AC-2(4), AU-2, AU-3, AU-6, AU-6(1), AU-12, AU-12(1), CA-2, CA-5, CA-7, RA-5, SI-2, SI-2(2), SI-3, SI-4, SI-4(16) |
| **KSI-PIY** | CA-3, CM-8, SI-12 |
| **KSI-SCR** | SA-9, SA-9(2) |
| **KSI-SVC** | CM-6, CM-7, SA-11, SI-2, SI-2(2), SI-2(3) |

: FedRAMP 20x Key Security Indicator → contributing controls (spine) {.striped}

## Closure-bearing books in this slice

| Book | Volume/Book | Title |
|---|---|---|
| book-01 | Vol I Bk 01 | Cloud Landing Zone, IPAM/DDI, FedRAMP |
| book-04 | Vol I Bk 04 | HRIT Identity & Org SSOT |
| book-net-enforce | Vol I Bk 07 | Network Enforcement Substrate (Cisco/Palo Alto/Juniper) |
| book-patch-sysmgmt | Vol III Bk 03 | Patch & Systems Management (multi-CSP SI-2/CM) |
| book-cloudnative-posture | Vol III Bk 04 | Cloud-Native Security Posture & Containers (CSPM/CNAPP, K8s) |
| book-evidence-fabric | Vol III Bk 07 | Multi-Cloud Evidence Fabric (telemetry → CDM → KSI) |
| book-sn-cmdb | Vol VII Bk 01 | CMDB Reconciliation & Asset Identity (reconciled to IPAM/DDI) |
| book-sn-m365 | Vol VII Bk 02 | M365 Federal Control Compliance Automation |
| book-sn-azure | Vol VII Bk 03 | Azure Federal Control Compliance Automation |
| book-sn-attestation | Vol VII Bk 04 | Control Attestation, Evidence & KSI |
| book-ddi-xplat | Vol VIII Bk 06 | Cross-Platform Operations & Multi-Cloud Governance |
| book-ddi-servicenow | Vol VIII Bk 07 | ServiceNow Orchestration — Governed Front Door for DDI |
| book-day2-helpdesk | Vol IX Bk 01 | Helpdesk & ITSM Catalog (Entra · M365 · Azure) |
| book-day2-landingzone | Vol IX Bk 02 | Landing Zone Front Door (catalog → IaC → CMDB) |
| book-day2-appreg | Vol IX Bk 03 | App Registration Governance (request · consent · secret/cert lifecycle) |
| book-day2-telephony | Vol IX Bk 04 | Teams Telephony Catalog & Teams SCuBA Drift |
| book-sn-saas | Vol IX Bk 05 | SaaS Integration Governance (the Entra app gallery as a governed SA-9 event) |
