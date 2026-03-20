# Management Stack — FedRAMP Control Definitions

> Auto-generated from `data/management-stack.yml` by the UDC Pipeline.

The Management Stack defines the two primary management-plane tools in the UIAO architecture — ServiceNow and Microsoft Intune — along with their FedRAMP authorization details and the specific NIST 800-53 Rev 5 controls each tool implements at the operational level. Every control mapping follows the same rigor applied to the Cisco and Infoblox pillars in the Vendor Stack: the product function named in each entry is the mechanism that satisfies the control requirement, and the evidence artifact identifies the specific log, API, or report an assessor would examine during a FedRAMP annual assessment.

---



## ServiceNow — ServiceNow GovCommunityCloud

Incident lifecycle management, change control, CMDB asset inventory, and continuous authorization support

### FedRAMP Authorization

| Attribute | Value |
|-----------|-------|
| Package Type | JAB P-ATO |
| Impact Level | High |
| FedRAMP 20x Class | Class C |
| Status | Authorized |
| Framework | NIST SP 800-53 Rev 5 |
| Authorization Source | Joint Authorization Board (JAB) |
| Controls Assessed | 421 |
| Last Annual Assessment | 2025-09-30 |
| Marketplace | [Link](https://marketplace.fedramp.gov/products/F1607067912) |
| Required Version | Xanadu (GovCommunityCloud) |

### NIST 800-53 Rev 5 Control Mappings


#### IR-4 — Incident Handling

Incident Management module state machine workflow (New > In Progress > Resolved > Closed) with mandatory categorization, priority assignment, and escalation rules

**Evidence Artifact:** incident table audit trail: sys_audit_list where tablename=incident

**API Endpoint:** `/api/now/table/incident`



#### IR-5 — Incident Monitoring

Performance Analytics incident dashboards with real-time MTTR/MTTI metrics, trend analysis, and SLA breach tracking against OLA definitions

**Evidence Artifact:** pa_dashboards where category=incident; sla_breach_log table

**API Endpoint:** `/api/now/stats/incident`



#### IR-6 — Incident Reporting

Notification rules engine (sysevent + cmn_notif_message) auto-generates incident reports to designated authorities; US-CERT reporting templates in GRC module

**Evidence Artifact:** cmn_notif_message audit log; scheduled report execution history

**API Endpoint:** `/api/now/table/sys_report`



#### IR-8 — Incident Response Plan

GRC Policy and Compliance Management stores the IRP as a controlled document with version history, annual review workflow, and stakeholder acknowledgment tracking

**Evidence Artifact:** sn_compliance_policy table where category=incident_response; document_revision history





#### CM-3 — Configuration Change Control

Change Management module enforces CAB approval workflow, risk assessment scoring (change_risk_score), collision detection, and mandatory back-out plan documentation

**Evidence Artifact:** change_request table audit trail; cab_meeting_agenda and approval history

**API Endpoint:** `/api/now/table/change_request`



#### CM-8 — System Component Inventory

CMDB maintains authoritative CI records; Discovery auto-populates hardware, software, and dependency relationships via agentless network scans

**Evidence Artifact:** cmdb_ci table with discovery_source=ServiceNow Discovery; cmdb_rel_ci relationship map

**API Endpoint:** `/api/now/table/cmdb_ci`



#### CA-7 — Continuous Monitoring

GRC Continuous Authorization and Monitoring module (com.sn_irm_cont_auth_monitor) tracks control implementation status against NIST 800-53 Rev 5 baseline, auto-generates POA&Ms from failed assessments

**Evidence Artifact:** sn_irm_cont_auth_monitor tables; poam table with auto-generated entries





#### SA-9 — External System Services

Vendor Risk Management module tracks third-party providers, stores vendor assessments, monitors SLA compliance, and links vendor CIs to CMDB service maps

**Evidence Artifact:** vendor_assessment table; sn_vdr_risk_assessment with linked cmdb_ci_service records







### Integration Bindings

| Target System | Mechanism | Control Supported |
|--------------|-----------|-------------------|
| Infoblox BloxOne DDI | CMDB Discovery imports IP allocation records via REST IntegrationHub spoke | CM-8 (CMDB completeness depends on Infoblox as IP source of truth) |
| CyberArk PAM | Privileged session events forwarded via MID Server syslog integration | IR-4 (privileged access anomalies auto-create P1 incidents) |
| Microsoft Sentinel | Bidirectional incident sync via Azure Logic App connector | IR-5 (correlated SIEM alerts enrich incident records) |
| Microsoft Intune | Device compliance status synced to CMDB via Graph API IntegrationHub spoke | CM-8 (managed device inventory reconciliation) |



---


## Microsoft — Microsoft Intune (M365 GCC High)

Endpoint configuration baseline enforcement, device compliance gating for Conditional Access, and hardware/software inventory for CMDB reconciliation

### FedRAMP Authorization

| Attribute | Value |
|-----------|-------|
| Package Type | Agency ATO |
| Impact Level | High |
| FedRAMP 20x Class | Class C |
| Status | Authorized |
| Framework | NIST SP 800-53 Rev 5 |
| Authorization Source | DoD / Agency ATO (FedRAMP High baseline) |
| Parent Package | Microsoft Office 365 GCC High |
| Marketplace | [Link](https://marketplace.fedramp.gov/products/FR1824057433) |
| Required Version | 2602 Service Release (March 2026) |

### NIST 800-53 Rev 5 Control Mappings


#### CM-2 — Baseline Configuration

Configuration Profiles define the approved baseline per device platform (Windows, iOS, macOS). Each profile specifies registry keys, MDM CSP settings, or plist values that enforce the organizational standard build.

**Evidence Artifact:** Intune > Devices > Configuration profiles > Per-profile compliance report; Graph API: GET /deviceManagement/deviceConfigurations/{id}/deviceStatuses




**Baseline Sources:**

- DISA STIG Windows 11 v1r6

- CIS Microsoft 365 Benchmark v3.1.0

- CISA SCuBA M365 Baseline (BOD 25-01)



#### CM-6 — Configuration Settings

Security Baselines deploy pre-built policy sets aligned to DISA STIGs and CIS Benchmarks. Settings Catalog provides granular per-CSP control over 5000+ individual Windows MDM policy settings.

**Evidence Artifact:** Intune > Endpoint security > Security baselines > Profile compliance status; Graph API: GET /deviceManagement/templates





#### CM-8 — System Component Inventory

Hardware inventory agent reports device make, model, serial number, OS version, installed applications, and TPM attestation status. Software inventory enumerates all discovered and managed applications per device.

**Evidence Artifact:** Intune > Devices > All devices > Hardware tab; Graph API: GET /deviceManagement/managedDevices/{id}?$select=hardwareInformation

**API Endpoint:** `https://graph.microsoft.com/v1.0/deviceManagement/managedDevices`



#### CM-7 — Least Functionality

App Protection Policies restrict which applications access corporate data. Enrollment Restrictions limit permitted device types and OS versions. AppLocker/WDAC policies deployed via Configuration Profiles block unauthorized executables.

**Evidence Artifact:** Intune > Apps > App protection policies > User report; Intune > Devices > Enrollment restrictions





#### IA-3 — Device Identification and Authentication

Autopilot device registration binds hardware hash (TPM 2.0 endorsement key + device serial) to Entra ID device object at enrollment. SCEP/PKCS certificate profiles issue machine certificates from agency PKI.

**Evidence Artifact:** Entra ID > Devices > Device list with join type=Autopilot; Intune > Configuration profiles > SCEP certificate deployment status





#### AC-19 — Access Control for Mobile Devices

Compliance Policies evaluate device posture (encryption, PIN, OS version, jailbreak detection, Defender risk score) and report status to Entra ID. Conditional Access consumes this signal to gate resource access.

**Evidence Artifact:** Intune > Devices > Compliance policies > Per-policy device status; Entra ID > Conditional Access > Grant controls = Require compliant device





#### SI-2 — Flaw Remediation

Windows Update for Business policies define update rings (Current/Deferred/Pilot) with deferral periods, deadline enforcement, and restart grace periods. Compliance tracked per ring with non-compliant device escalation.

**Evidence Artifact:** Intune > Devices > Windows updates > Update rings compliance; Graph API: GET /deviceManagement/windowsUpdateForBusinessConfigurations





#### SC-28 — Protection of Information at Rest

BitLocker encryption policy via Endpoint Protection profile requires TPM+PIN protector, XTS-AES-256, and automatic key escrow to Entra ID. FileVault enforced on macOS. Compliance policy marks unencrypted devices non-compliant.

**Evidence Artifact:** Intune > Configuration profiles > Endpoint protection > BitLocker status; Intune > Reports > Device encryption report







### Integration Bindings

| Target System | Mechanism | Control Supported |
|--------------|-----------|-------------------|
| Microsoft Entra ID | Compliance policy evaluation result is the primary signal consumed by Entra Conditional Access grant controls | AC-19 (device posture gates identity-based access decisions) |
| Microsoft Defender for Endpoint | MDE machine risk score feeds into Intune compliance policy as a device threat level condition | SI-2, IA-3 (compromised devices auto-quarantined via compliance failure) |
| ServiceNow CMDB | Graph API device inventory exported to ServiceNow CMDB via IntegrationHub spoke | CM-8 (Intune is MDM source of truth; ServiceNow CMDB is authoritative asset register) |
| Cisco SD-WAN | Device compliance status informs network access via Entra Conditional Access and Cisco ISE integration | AC-4 (non-compliant devices blocked from overlay network segments) |



---

