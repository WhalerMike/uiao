UIAO Compliance Mapping Matrix

**Document ID:** UIAO_CMM_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

1\. Overview

+-------------------------------------------------------------------------------------------------------+
| **Canon Rule**                                                                                        |
|                                                                                                       |
| GCC Moderate applies to M365 SaaS services only. This is a public repository.                         |
+-------------------------------------------------------------------------------------------------------+

This matrix maps UIAO pipeline capabilities to NIST 800-53 controls under the FedRAMP Moderate baseline and CISA BOD 25-01 requirements. It identifies which controls are automated, which require supplemental evidence, and which remain manual.

2\. Coverage Summary

2.1 FedRAMP Moderate Baseline

  ------------------------------------------------------------------
  **Category**                          **Count**   **Percentage**
  ------------------------------------- ----------- ----------------
  Automated (pipeline-evaluated)        78          24%

  Supplemental (pipeline-assisted)      42          13%

  Manual (human-assessed)               205         63%

  **Total FedRAMP Moderate Controls**   **325**     **100%**
  ------------------------------------------------------------------

2.2 BOD 25-01

  ---------------------------------------------------------------
  **Category**                       **Count**   **Percentage**
  ---------------------------------- ----------- ----------------
  Automated                          9           82%

  Supplemental                       2           18%

  **Total BOD 25-01 Requirements**   **11**      **100%**
  ---------------------------------------------------------------

3\. NIST 800-53 Control Family Breakdown

3.1 Coverage by Family

  ------------------------------------------------------------------------------------------
  **Family**   **Name**                     **Total**   **Auto**   **Suppl.**   **Manual**
  ------------ ---------------------------- ----------- ---------- ------------ ------------
  AC           Access Control               25          12         5            8

  AT           Awareness & Training         5           0          0            5

  AU           Audit & Accountability       16          8          3            5

  CA           Assessment & Authorization   9           3          2            4

  CM           Configuration Management     11          9          1            1

  CP           Contingency Planning         13          0          2            11

  IA           Identification & Auth        12          10         1            1

  IR           Incident Response            10          0          3            7

  MA           Maintenance                  6           0          1            5

  MP           Media Protection             8           0          1            7

  PE           Physical & Environmental     20          0          0            20

  PL           Planning                     4           0          1            3

  PS           Personnel Security           8           0          0            8

  RA           Risk Assessment              6           2          2            2

  SA           System & Services Acq.       22          0          4            18

  SC           System & Comm. Protection    44          15         8            21

  SI           System & Info Integrity      16          10         3            3

  PM           Program Management           16          0          3            13

  SR           Supply Chain Risk Mgmt       74          9          2            63
  ------------------------------------------------------------------------------------------

3.2 Automated Coverage Visualization

Family \| Automated Coverage \-\-\-\-\-\-\--\|\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-\-- AC 25 \| ████████████░░░░░░░░░░░░░ 48% AT 5 \| 0% AU 16 \| ████████████░░░░░░░░░░░░░ 50% CA 9 \| ████████░░░░░░░░░░░░░░░░░ 33% CM 11 \| ████████████████████████░ 82% CP 13 \| 0% IA 12 \| ████████████████████████░ 83% IR 10 \| 0% MA 6 \| 0% MP 8 \| 0% PE 20 \| 0% PL 4 \| 0% PS 8 \| 0% RA 6 \| ████████░░░░░░░░░░░░░░░░░ 33% SA 22 \| 0% SC 44 \| ████████░░░░░░░░░░░░░░░░░ 34% SI 16 \| ████████████████░░░░░░░░░ 63% PM 16 \| 0% SR 74 \| ███░░░░░░░░░░░░░░░░░░░░░░ 12%

4\. Detailed Automated Control Tables

4.1 Access Control (AC) --- 12 Automated

  -------------------------------------------------------------------------------------------------------------------------
  **Control**   **Title**                 **M365 Product**   **ScubaGear Rule(s)**        **KSI ID**    **Evidence Type**
  ------------- ------------------------- ------------------ ---------------------------- ------------- -------------------
  AC-2          Account Management        AAD                MS.AAD.2.1v1, MS.AAD.2.3v1   KSI-AC-002    Configuration

  AC-2(1)       Automated Management      AAD                MS.AAD.2.1v1                 KSI-AC-002a   Configuration

  AC-3          Access Enforcement        AAD, SPO           MS.AAD.3.1v1, MS.SPO.2.1v1   KSI-AC-003    Configuration

  AC-4          Information Flow          EXO                MS.EXO.1.1v1, MS.EXO.2.1v1   KSI-AC-004    Configuration

  AC-6          Least Privilege           AAD                MS.AAD.7.1v1, MS.AAD.7.4v1   KSI-AC-006    Configuration

  AC-6(1)       Authorize Access          AAD                MS.AAD.7.1v1                 KSI-AC-006a   Configuration

  AC-6(5)       Privileged Accounts       AAD                MS.AAD.7.4v1                 KSI-AC-006e   Configuration

  AC-7          Unsuccessful Logon        AAD                MS.AAD.3.2v1                 KSI-AC-007    Configuration

  AC-8          System Use Notification   AAD                MS.AAD.8.1v1                 KSI-AC-008    Configuration

  AC-11         Session Lock              AAD                MS.AAD.3.3v1                 KSI-AC-011    Configuration

  AC-17         Remote Access             AAD                MS.AAD.4.1v1                 KSI-AC-017    Configuration

  AC-17(2)      Crypto Protection         AAD                MS.AAD.1.1v1                 KSI-AC-017b   Configuration
  -------------------------------------------------------------------------------------------------------------------------

4.2 Configuration Management (CM) --- 9 Automated

  ------------------------------------------------------------------------------------------------------------------------------
  **Control**   **Title**                    **M365 Product**   **ScubaGear Rule(s)**          **KSI ID**    **Evidence Type**
  ------------- ---------------------------- ------------------ ------------------------------ ------------- -------------------
  CM-2          Baseline Configuration       All                Multiple                       KSI-CM-002    Configuration

  CM-2(2)       Automation Support           All                Pipeline-validated             KSI-CM-002b   Configuration

  CM-6          Configuration Settings       All                All product rules              KSI-CM-006    Configuration

  CM-6(1)       Automated Management         All                Pipeline-validated             KSI-CM-006a   Configuration

  CM-7          Least Functionality          EXO, SPO           MS.EXO.4.1v1, MS.SPO.3.1v1     KSI-CM-007    Configuration

  CM-7(1)       Periodic Review              All                Nightly assessment             KSI-CM-007a   Configuration

  CM-8          System Component Inventory   Defender           MS.DEF.1.1v1                   KSI-CM-008    Configuration

  CM-8(3)       Automated Detection          Defender           MS.DEF.1.2v1                   KSI-CM-008c   Configuration

  CM-11         User-Installed Software      Teams, PBI         MS.TEAMS.5.1v1, MS.PBI.1.1v1   KSI-CM-011    Configuration
  ------------------------------------------------------------------------------------------------------------------------------

4.3 System & Communications Protection (SC) --- 15 Automated

  ------------------------------------------------------------------------------------------------------------------------------
  **Control**   **Title**                      **M365 Product**   **ScubaGear Rule(s)**        **KSI ID**    **Evidence Type**
  ------------- ------------------------------ ------------------ ---------------------------- ------------- -------------------
  SC-5          DoS Protection                 Defender           MS.DEF.2.1v1                 KSI-SC-005    Configuration

  SC-7          Boundary Protection            EXO, AAD           MS.EXO.1.1v1, MS.AAD.4.1v1   KSI-SC-007    Configuration

  SC-7(5)       Deny by Default                AAD                MS.AAD.4.2v1                 KSI-SC-007e   Configuration

  SC-8          Transmission Confidentiality   EXO                MS.EXO.5.1v1                 KSI-SC-008    Configuration

  SC-8(1)       Crypto Protection              EXO                MS.EXO.5.2v1                 KSI-SC-008a   Configuration

  SC-12         Crypto Key Management          AAD                MS.AAD.5.1v1                 KSI-SC-012    Configuration

  SC-13         Cryptographic Protection       AAD, EXO           MS.AAD.5.1v1, MS.EXO.5.1v1   KSI-SC-013    Configuration

  SC-18         Mobile Code                    Teams              MS.TEAMS.5.1v1               KSI-SC-018    Configuration

  SC-20         Secure Name Resolution         Defender           MS.DEF.3.1v1                 KSI-SC-020    Configuration

  SC-23         Session Authenticity           AAD                MS.AAD.3.3v1                 KSI-SC-023    Configuration

  SC-28         Protection at Rest             SPO                MS.SPO.4.1v1                 KSI-SC-028    Configuration

  SC-28(1)      Crypto Protection              SPO                MS.SPO.4.2v1                 KSI-SC-028a   Configuration

  SC-35         External Malicious Code        Defender           MS.DEF.4.1v1                 KSI-SC-035    Configuration

  SC-39         Process Isolation              Teams              MS.TEAMS.6.1v1               KSI-SC-039    Configuration

  SC-44         Detonation Chambers            Defender           MS.DEF.5.1v1                 KSI-SC-044    Configuration
  ------------------------------------------------------------------------------------------------------------------------------

4.4 Identification & Authentication (IA) --- 10 Automated

  -------------------------------------------------------------------------------------------------------------------
  **Control**   **Title**                **M365 Product**   **ScubaGear Rule(s)**   **KSI ID**    **Evidence Type**
  ------------- ------------------------ ------------------ ----------------------- ------------- -------------------
  IA-2          Identification & Auth    AAD                MS.AAD.1.1v1            KSI-IA-002    Configuration

  IA-2(1)       MFA to Privileged        AAD                MS.AAD.3.1v1            KSI-IA-002a   Configuration

  IA-2(2)       MFA to Non-Privileged    AAD                MS.AAD.3.2v1            KSI-IA-002b   Configuration

  IA-2(6)       Access to Privileged     AAD                MS.AAD.1.1v1            KSI-IA-002f   Configuration

  IA-2(8)       Replay Resistant         AAD                MS.AAD.3.4v1            KSI-IA-002h   Configuration

  IA-5          Authenticator Mgmt       AAD                MS.AAD.6.1v1            KSI-IA-005    Configuration

  IA-5(1)       Password-Based           AAD                MS.AAD.6.2v1            KSI-IA-005a   Configuration

  IA-5(2)       PKI-Based                AAD                MS.AAD.5.1v1            KSI-IA-005b   Configuration

  IA-6          Authenticator Feedback   AAD                MS.AAD.6.3v1            KSI-IA-006    Configuration

  IA-8          Non-Org Users            AAD                MS.AAD.4.3v1            KSI-IA-008    Configuration
  -------------------------------------------------------------------------------------------------------------------

4.5 System & Information Integrity (SI) --- 10 Automated

  ---------------------------------------------------------------------------------------------------------------------------
  **Control**   **Title**                   **M365 Product**   **ScubaGear Rule(s)**        **KSI ID**    **Evidence Type**
  ------------- --------------------------- ------------------ ---------------------------- ------------- -------------------
  SI-2          Flaw Remediation            Defender           MS.DEF.1.3v1                 KSI-SI-002    Configuration

  SI-2(2)       Automated Remediation       Defender           MS.DEF.1.4v1                 KSI-SI-002b   Configuration

  SI-3          Malicious Code Protection   Defender           MS.DEF.4.1v1, MS.DEF.4.2v1   KSI-SI-003    Configuration

  SI-3(1)       Central Management          Defender           MS.DEF.4.3v1                 KSI-SI-003a   Configuration

  SI-4          System Monitoring           Defender           MS.DEF.6.1v1                 KSI-SI-004    Configuration

  SI-4(2)       Automated Analysis          Defender           MS.DEF.6.2v1                 KSI-SI-004b   Configuration

  SI-4(5)       System Alerts               Defender           MS.DEF.6.3v1                 KSI-SI-004e   Configuration

  SI-5          Security Alerts             Defender           MS.DEF.7.1v1                 KSI-SI-005    Configuration

  SI-7          Software Integrity          Pipeline           Hash validation              KSI-SI-007    Integrity

  SI-16         Memory Protection           Defender           MS.DEF.8.1v1                 KSI-SI-016    Configuration
  ---------------------------------------------------------------------------------------------------------------------------

4.6 Audit & Accountability (AU) --- 8 Automated

  --------------------------------------------------------------------------------------------------------------------------
  **Control**   **Title**                  **M365 Product**   **ScubaGear Rule(s)**        **KSI ID**    **Evidence Type**
  ------------- -------------------------- ------------------ ---------------------------- ------------- -------------------
  AU-2          Event Logging              AAD, EXO           MS.AAD.9.1v1, MS.EXO.6.1v1   KSI-AU-002    Configuration

  AU-3          Content of Audit Records   AAD                MS.AAD.9.2v1                 KSI-AU-003    Configuration

  AU-6          Audit Record Review        Defender           MS.DEF.6.1v1                 KSI-AU-006    Configuration

  AU-6(1)       Automated Review           Defender           MS.DEF.6.2v1                 KSI-AU-006a   Configuration

  AU-7          Audit Record Reduction     AAD                MS.AAD.9.3v1                 KSI-AU-007    Configuration

  AU-8          Time Stamps                Pipeline           Provenance metadata          KSI-AU-008    Integrity

  AU-11         Audit Record Retention     AAD                MS.AAD.9.4v1                 KSI-AU-011    Configuration

  AU-12         Audit Record Generation    AAD, EXO           MS.AAD.9.1v1, MS.EXO.6.2v1   KSI-AU-012    Configuration
  --------------------------------------------------------------------------------------------------------------------------

5\. BOD 25-01 Mapping

5.1 BOD 25-01 Requirements

  -------------------------------------------------------------------------------------------------------------------------------------
  **BOD Requirement**                   **M365 Product**   **ScubaGear Coverage**       **Pipeline Coverage**            **Status**
  ------------------------------------- ------------------ ---------------------------- -------------------------------- --------------
  Implement MFA for all users           AAD                MS.AAD.3.1v1, MS.AAD.3.2v1   Plane 2 KSI evaluation           Automated

  Disable legacy authentication         AAD                MS.AAD.1.1v1                 Plane 2 KSI evaluation           Automated

  Block external email forwarding       EXO                MS.EXO.1.1v1                 Plane 2 KSI evaluation           Automated

  Enable unified audit logging          AAD, EXO           MS.AAD.9.1v1, MS.EXO.6.1v1   Plane 2 KSI evaluation           Automated

  Restrict admin consent                AAD                MS.AAD.7.4v1                 Plane 2 KSI evaluation           Automated

  Enable anti-phishing policies         Defender           MS.DEF.4.1v1                 Plane 2 KSI evaluation           Automated

  Configure safe attachments            Defender           MS.DEF.5.1v1                 Plane 2 KSI evaluation           Automated

  Enable safe links                     Defender           MS.DEF.5.2v1                 Plane 2 KSI evaluation           Automated

  Restrict anonymous meeting join       Teams              MS.TEAMS.3.1v1               Plane 2 KSI evaluation           Automated

  Implement data loss prevention        Purview            Partial                      Supplemental evidence required   Supplemental

  Review and restrict app permissions   AAD                Partial                      Supplemental evidence required   Supplemental
  -------------------------------------------------------------------------------------------------------------------------------------

5.2 BOD 25-01 Coverage Diagram

\@startuml skinparam componentStyle rectangle package \"Fully Automated (9/11)\" { \[MFA for all users\] as R1 \[Disable legacy auth\] as R2 \[Block external forwarding\] as R3 \[Unified audit logging\] as R4 \[Restrict admin consent\] as R5 \[Anti-phishing policies\] as R6 \[Safe attachments\] as R7 \[Safe links\] as R8 \[Restrict anonymous meetings\] as R9 } package \"Supplemental (2/11)\" { \[Data loss prevention\] as R10 \[App permission review\] as R11 } \[ScubaGear\] \--\> R1 \[ScubaGear\] \--\> R2 \[ScubaGear\] \--\> R3 \[ScubaGear\] \--\> R4 \[ScubaGear\] \--\> R5 \[ScubaGear\] \--\> R6 \[ScubaGear\] \--\> R7 \[ScubaGear\] \--\> R8 \[ScubaGear\] \--\> R9 \[Manual Evidence\] \--\> R10 \[Manual Evidence\] \--\> R11 \@enduml

6\. OSCAL Artifact Mapping

6.1 Pipeline Output to OSCAL Artifact

  ----------------------------------------------------------------------------------------------------------------------
  **Pipeline Output**        **OSCAL Artifact**   **OSCAL Model**                 **Content**
  -------------------------- -------------------- ------------------------------- --------------------------------------
  KSI evaluation (passing)   SSP                  system-security-plan            Control implementation statements

  KSI evaluation (failing)   POA&M                plan-of-action-and-milestones   Open findings with remediation plans

  Evidence bundle            SAR                  assessment-results              Assessment observations and findings

  SSP narrative              SSP                  system-security-plan            Narrative control descriptions

  Lineage traces             SAR                  assessment-results              Evidence provenance chain

  Coverage export            SSP                  system-security-plan            Control coverage matrix
  ----------------------------------------------------------------------------------------------------------------------

6.2 Evidence Chain Tracing

ScubaGear JSON (source) │ ├── Plane 1: ScubaResults.json → NormalizedClaim\[\] │ └── claim_id: scuba.exo.MS.EXO.1.1v1 │ └── provenance.source: scubagear-v5.4 │ └── provenance.collected_at: 2026-04-11T02:00:00Z │ ├── Plane 2: NormalizedClaim → KSI EvaluationResult │ └── control: AC-4 │ └── result: fail │ └── evidence_type: configuration │ ├── Plane 3: EvaluationResult → EvidenceBundle │ └── bundle_id: EVD-2026-04-11-001 │ └── signature: HMAC-SHA256(\...) │ └── stable_hash: SHA-256(\...) │ └── Plane 4: EvidenceBundle → OSCAL Artifacts ├── oscal-ssp.json (AC-4 implementation) ├── oscal-poam.json (AC-4 finding) └── oscal-sar.json (AC-4 observation)

7\. ConMon Activity Mapping

7.1 Continuous Monitoring Activities

  ---------------------------------------------------------------------------------------
  **Activity**               **Pipeline Support**                  **Automation Level**
  -------------------------- ------------------------------------- ----------------------
  Configuration assessment   SCuBA nightly scan + KSI evaluation   Fully automated

  Vulnerability scanning     Defender adapter (supplemental)       Semi-automated

  POA&M management           Governance module + OSCAL POA&M       Fully automated

  Change detection           Diff engine + drift detection         Fully automated

  Evidence freshness         Freshness grading engine              Fully automated

  Compliance reporting       Coverage export + dashboard           Fully automated

  Incident response          Governance event engine (planned)     Planned

  Access review              AAD adapter findings                  Semi-automated
  ---------------------------------------------------------------------------------------

7.2 ConMon Cadence

  ----------------------------------------------------------------------------------------
  **Frequency**   **Activity**                       **Pipeline Component**
  --------------- ---------------------------------- -------------------------------------
  Nightly         SCuBA assessment + full pipeline   scuba-nightly.yml

  Nightly         Drift detection                    drift-detection.yml

  Daily           Evidence freshness check           Operator runbook §1

  Weekly          POA&M review + coverage trend      Operator runbook §2

  Monthly         ATO package generation             Operator runbook §3

  Monthly         Evidence retention review          Retention policy config

  Quarterly       Key rotation                       Deployment guide §9

  Quarterly       Control library update             Canon update procedure

  Annually        Full ATO reassessment              Complete pipeline + manual controls
  ----------------------------------------------------------------------------------------

8\. Gap Closure Roadmap

8.1 Planned Automated Coverage Expansion

  -----------------------------------------------------------------------------------------
  **Phase**   **Version**   **Target Date**   **New Controls**        **Cumulative Auto**
  ----------- ------------- ----------------- ----------------------- ---------------------
  Current     v2.0.0        2026-04-11        ---                     78 (24%)

  Phase 1     v2.1.0        2026-05-01        +12 (IR, RA families)   90 (28%)

  Phase 2     v2.2.0        2026-06-01        +15 (SA, CP partial)    105 (32%)

  Phase 3     v3.0.0        2026-08-01        +20 (new adapters)      125 (38%)

  Phase 4     v3.1.0        2026-10-01        +15 (PM, SR partial)    140 (43%)
  -----------------------------------------------------------------------------------------

8.2 Controls That Cannot Be Automated

  ------------------------------------------------------------------------------------
  **Family**         **Count**   **Reason**
  ------------------ ----------- -----------------------------------------------------
  PE (Physical)      20          Requires physical inspection; no API access

  PS (Personnel)     8           HR process controls; not technology-assessable

  AT (Training)      5           Training completion requires LMS integration

  CP (Contingency)   11          Disaster recovery testing requires manual execution

  MA (Maintenance)   5           Physical maintenance controls
  ------------------------------------------------------------------------------------

Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
