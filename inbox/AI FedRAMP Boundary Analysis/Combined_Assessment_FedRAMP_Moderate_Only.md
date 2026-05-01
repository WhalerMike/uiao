# M365 GCC-Moderate Telemetry & Boundary Assessment

*Consolidated, normalized assessment — FedRAMP Moderate only.*

| Field | Value |
|---|---|
| Document title | M365 GCC-Moderate Telemetry & Boundary Assessment |
| Version | 1.0 (combined) |
| Status | DRAFT — combined synthesis |
| Classification | Controlled |
| Date | 2026-04-25 |
| Owner | Michael Stratton, Canon Steward |
| Authorization scope | **FedRAMP Moderate only** (M365 GCC-Moderate, .com commercial cloud) |
| Source AIs | Microsoft Copilot, Google Gemini, Grok, Perplexity (Mar 2026) + UIAO_INV_001 (Apr 24, 2026) |

---

## 0. Scope and Normalization Rules

This document combines four parallel AI analyses (Copilot, Gemini, Grok, Perplexity) of Microsoft 365 GCC-Moderate telemetry gaps with the operational investigation captured in **UIAO_INV_001 (Deep M365/Azure Dashboard Coverage Investigation, v1.0, 2026-04-24)**. It has been normalized to **FedRAMP Moderate only**.

### What "FedRAMP Moderate only" means in this document

1. **Target environment:** Microsoft 365 GCC-Moderate, which operates in the **.com** commercial cloud domain under a FedRAMP Moderate authorization boundary.
2. **Out of scope as an authorization target:** GCC-High, DoD, and any other FedRAMP High environment. References to those environments appear only where (a) Microsoft's own documentation enumerates them in a single line that names GCC-Moderate as well, or (b) they serve as a comparator that helps explain how FedRAMP Moderate behaves.
3. **Documentation purity rule (Perplexity scoping rule, retained):** *.us-domain documentation* and any GCC-High/DoD-specific page **must not** be applied to GCC-Moderate (.com) without separate justification. The .com boundary enforces telemetry constraints **more strictly** than the .us boundary, not less. Importing .us conclusions into .com is therefore an unsafe inference.
4. **AWS GovCloud is excluded** from the primary findings. AWS GovCloud is FedRAMP High + DoD SRG IL2/4/5 + ITAR — it is not a Moderate environment. The AWS material from the source folder is acknowledged in **Appendix C** as a comparator only.

### Methodology — the "false-negative" reverse-inference framework

The single most important methodological finding across all four AIs is that **absence of an explicit "not available in GCC-Moderate" statement is not evidence of availability.** Many telemetry-dependent capabilities are constrained by the FedRAMP Moderate authorization boundary itself, regardless of what any product page says.

The constraining controls are:

| NIST 800-53 control | Constraint applied to outbound telemetry |
|---|---|
| **SI-4** (Information System Monitoring) | Monitoring data must remain within the authorized boundary unless explicitly scoped and authorized for export. |
| **AU-2 / AU-3** (Audit Events / Content of Audit Records) | Audit content shipped off-boundary to commercial multi-tenant analytics may exceed authorized export scope. |
| **SC-7** (Boundary Protection) | Continuous, rich telemetry to multi-tenant analytics services is exactly the cross-boundary flow SC-7 forces agencies to constrain. |

**Reverse-inference rule:** If a feature requires telemetry to flow to Microsoft's commercial multi-tenant processing pipeline, and the FedRAMP Moderate boundary restricts that outbound flow under SI-4/AU-2/AU-3/SC-7, then the signal is **blocked or degraded by architecture** — even when no Microsoft product page explicitly says so. This document marks every such finding **"Inferred blocked by FedRAMP boundary architecture"** rather than asserting documented unavailability.

---

## 1. Executive Summary

**Position.** Microsoft 365 GCC-Moderate provides the same nominal product set as Microsoft 365 commercial, but the FedRAMP Moderate authorization boundary materially constrains the outbound telemetry that drives many of the platform's higher-order analytics. The result is a structural reduction in the **fidelity of signals available** for Zero Trust decisions, anomaly detection, insider-risk detection, and forensic reconstruction.

**Two confirmed-unavailable telemetry-driven capabilities** (with direct Microsoft documentation):

1. **Microsoft Adoption Score** — Microsoft's own page states the feature is *not available in GCC, GCC High, and DOD tenants*. The "GCC" item in that list is GCC-Moderate.
2. **Microsoft Informed Network Routing (INR)** — Microsoft's own page states INR *supports tenants in WW Commercial cloud but not the GCC Moderate, GCC High, DoD, Germany, or China clouds.*

**One disputed but partially-confirmed-unavailable capability:**

3. **Endpoint Analytics — Advanced Analytics tier (Intune)** — The Advanced Analytics overview page lists sovereign-cloud support as limited to GCC High and DoD only; GCC-Moderate is not listed. Whether base-tier Endpoint Analytics is available is not explicitly documented.

**Capabilities that have GCC-Moderate-specific connection guidance** (i.e., are supported, contrary to some AI conclusions):

4. **Teams Call Quality Dashboard (CQD)** — supported with GCC-specific docs; EUII retention is the operational constraint, not feature absence.
5. **Microsoft 365 Usage Analytics** — supported via the GCC-specific Power BI connector; only the Marketplace template app variant is missing.

**Five product areas with no explicit unavailability documentation but architecturally constrained outbound telemetry** (inferred blocked):

- **Entra ID** — Identity Protection ML risk scoring and cross-tenant analytics
- **Intune** — advanced compliance, app-protection, WUfB, and EPM analytics
- **M365 core apps** — Office "Optional" diagnostic data, Copilot/AI telemetry, sensitivity-label and DLP behavioral analytics
- **Continuous Access Evaluation (CAE)** — real-time sub-second revocation paths
- **Windows Update for Business reporting** — fleet-wide trend and regression telemetry

**Compliance posture.** Agencies operating in GCC-Moderate **can satisfy core logging requirements** (CISA BOD 25-01, OMB M-21-31 Tier 3) by exporting raw logs into Sentinel/Log Analytics, but reaching CISA ZTMM **Advanced** maturity in the Identity, Devices, Networks, Data, and Visibility & Analytics pillars **requires building agency-side analytics** — Microsoft's commercial ML pipelines cannot be inherited.

**The paradox.** Agencies may be **technically compliant with FedRAMP Moderate yet structurally less observable** than commercial enterprises that have full access to Microsoft's commercial telemetry stack. Closing this observability gap is an agency responsibility, not a Microsoft platform feature.

**Recommendation summary.** Execute the 60-day tactical remediation plan in Section 11. Track the gap closure through the UIAO Telemetry Completeness Scorecard. Pursue MAS 2026 boundary refinement as the strategic resolution path (Section 12).

---

## 2. Confirmed-Unavailable Capabilities (Direct Microsoft Documentation)

### 2.1 Microsoft Adoption Score

| Field | Value |
|---|---|
| Microsoft documentation | *Microsoft Adoption Score report overview — Microsoft 365 admin* |
| URL | `https://learn.microsoft.com/en-us/microsoft-365/admin/adoption/adoption-score?view=o365-worldwide` |
| Verbatim text | "This feature isn't available in GCC High, GCC, and DOD tenants." |
| Interpretation | "GCC" in this list = GCC-Moderate, per Microsoft's own naming. |

**Telemetry signals lost.** Adoption Score is the entry point for tenant-level **behavioral baselines** across People Experiences and Technology Experiences:

- **People Experiences** — Communication patterns (chat-vs-email frequency), Meetings participation, Content Collaboration (cloud links vs. physical attachments), Teamwork, Mobility (multi-platform usage)
- **Technology Experiences** — Microsoft 365 Apps health (update channel adoption, version telemetry over time), Network Connectivity scores to Microsoft 365, Endpoint readiness baselines

Specific telemetry fields named in the analyses: `AppCrashCount`, `BlueScreenCount` (Endpoint experience overlap), communication ratios such as `ChatCount / EmailCount`, attachment-vs-cloud-link frequency, multi-platform mobility flags.

### 2.2 Microsoft Informed Network Routing (INR)

| Field | Value |
|---|---|
| Microsoft documentation | *Microsoft 365 informed network routing* (commercial .com page) |
| Excerpt | INR "supports tenants in WW Commercial cloud but not the GCC Moderate, GCC High, DoD, Germany, or China clouds." |
| Status | **Confirmed unavailable in GCC-Moderate.** |

**Telemetry signals lost.** Real-time path-aware metrics — latency, jitter, packet loss between user locations and Microsoft front doors; per-ISP/peering path performance; continuous-feedback dynamic routing optimization. Without INR, agencies cannot use Microsoft's global telemetry to drive M365 path optimization; routing falls back to static or policy-based egress, third-party SD-WAN/SASE telemetry, or local NetFlow/SNMP/synthetic-probe monitoring.

---

## 3. Documentation-Limited Capabilities (Sovereign-Cloud Statement Excludes GCC-Moderate)

### 3.1 Endpoint Analytics — Advanced Analytics tier

| Field | Value |
|---|---|
| Microsoft documentation | *Advanced Analytics overview — Microsoft Intune* |
| URL | `https://learn.microsoft.com/en-us/intune/advanced-analytics/` |
| Sovereign-cloud support | "U.S. Government Community Cloud (GCC) High" and "U.S. Department of Defense (DoD)" |
| GCC-Moderate listing | **Not listed.** Inferred unavailable. |
| Supporting doc | *Microsoft Intune Government Service overview* — `https://learn.microsoft.com/en-us/intune/intune-service/fundamentals/intune-govt-service-description` (Advanced Analytics is listed only under GCC High and DoD support.) |

**Telemetry signals at risk** (Advanced Analytics tier):

- **Device performance:** startup/boot time (median total + core), Group Policy processing duration, desktop load time, top boot processes by CPU / path / publisher
- **Application reliability:** `AppCrashCount`, hang rates, stability trends per app
- **Stop-error restarts** and sensor diagnostics
- **Battery health**
- **Work-from-anywhere readiness** scoring
- **Device performance anomalies** — regressions after configuration / policy / OS changes
- **Resource performance:** `AverageProcessorUsage`, `TotalPhysicalMemory` spikes (the Gemini "grey-ware" signal — attacks that don't trigger EDR but do show up as performance outliers)

**Status note.** Whether the **base-tier Endpoint Analytics** (without "Advanced") is available in GCC-Moderate is not explicitly addressed. The Endpoint Analytics data-collection page states the feature is "available in all Intune locations in global Azure" but does not enumerate GCC-Moderate. Treat base-tier as **available in principle but unverified for GCC-Moderate**; treat the Advanced Analytics tier as **unavailable**.

---

## 4. Capabilities That Are Available in GCC-Moderate (Refuting Earlier AI Conclusions)

This section corrects analyses that incorrectly listed CQD and M365 Usage Analytics as unavailable.

### 4.1 Teams Call Quality Dashboard (CQD)

| Field | Value |
|---|---|
| Microsoft documentation | *Data and reports in CQD*, *Turn on and use Call Quality Dashboard* |
| URLs | `https://learn.microsoft.com/en-us/microsoftteams/cqd-data-and-reports`, `https://learn.microsoft.com/en-us/microsoftteams/turning-on-and-using-call-quality-dashboard` |
| Status | **Available.** Documentation does not exclude GCC-Moderate. |
| Operational constraint | EUII (End-User Identifiable Info: BSSID, public IP, subnet/building mapping) is **typically purged after 28 days** — a forensic-retention constraint, not a feature-absence constraint. |
| Modernization note | The legacy CQD portal has been deprecated; the GA pathway is **QER v5.0 Power BI templates** (M365 Admin announcement, October 2024) plus **Real-Time Analytics (RTA)** in the Teams admin center. |

The "forensic cliff" Gemini described — incidents discovered 45+ days after initial access find the EUII has been purged — applies even though CQD is technically available. This is an operational gap to mitigate via local long-term retention of CQD exports.

### 4.2 Microsoft 365 Usage Analytics

| Field | Value |
|---|---|
| Microsoft documentation | *Connect to GCC data with usage analytics* |
| URL | `https://learn.microsoft.com/en-us/microsoft-365/admin/usage-analytics/connect-to-gcc-data-with-usage-analytics?view=o365-worldwide` |
| Status | **Available** for GCC tenants via the Power BI connector. |
| Constraint | The Power BI **Marketplace template app** is not available; agencies download and connect the GCC-specific template manually. Some long-horizon historical pivoting (12+ months, joined to Entra ID department/location attributes via Graph API) is functionally limited. |

**Net.** Treat M365 Usage Analytics as **available with manual setup overhead**, not unavailable. Cross-product behavioral correlation pivots are reduced in fidelity but are recoverable via Sentinel + custom Power BI over Log Analytics.

---

## 5. Architecturally Constrained Services (Inferred Blocked, No Explicit Documentation)

These five product areas have no Microsoft documentation that explicitly addresses GCC-Moderate availability, but the FedRAMP Moderate boundary architecture (SI-4 / AU-2 / AU-3 / SC-7) blocks or degrades the outbound telemetry their commercial-cloud features depend on.

### 5.1 Entra ID — Identity Protection, sign-in analytics, cross-tenant collaboration

- **(A) Commercial telemetry signals required.** Per-sign-in evaluation data (device, location, client app, network, sign-in risk, session details); raw sign-in logs with success/failure, IP, user agent, MFA status, CA status; aggregated patterns (impossible travel, atypical client usage); Identity Protection risk detections (leaked credentials, atypical travel, anonymous IP, malware-linked IP, unfamiliar sign-in properties); user-risk and sign-in-risk scores and their evolution over time; B2B/B2B-direct-connect events; cross-tenant access settings evaluations.
- **(B) Constraining controls.** SI-4 (raw user-identifiable sign-in and risk telemetry export to commercial multi-tenant analytics conflicts with in-boundary monitoring requirement); AU-2/AU-3 (full-fidelity sign-in and risk events shipped off-boundary may exceed authorized audit export); SC-7 (continuous rich telemetry to multi-tenant analytics is exactly the cross-boundary flow SC-7 constrains).
- **(C) Documentation status.** No direct GCC-Moderate (.com) documentation confirms or denies availability. Entra government docs that exist are Azure Government (.us) — not applicable here under the scoping rule.
- **(D) Workarounds and fidelity loss.** Graph API export of sign-in and audit logs into Sentinel / Log Analytics; unified audit log + KQL queries; custom risk models built on local IP/location/device-ID/failure-pattern correlation. Fidelity lost: Microsoft's proprietary ML-driven risk scores (no continuously-tuned "atypical travel" or "unfamiliar sign-in properties" models), real-time cross-tenant correlation, vendor-supplied global threat-intelligence context. Detection-gap order of magnitude: commercial cloud ≈ minutes; GCC-Moderate ≈ hours to days.
- **(E) Compliance impact.** BOD 25-01 core logging is achievable if logs are exported and retained; the directive's "rapid detection and investigation" intent is harder to meet without local analytics. M-22-09 Identity pillar requires continuous identity-behavior monitoring and risk-based access — agencies must implement equivalent risk scoring to credibly claim **Advanced** maturity in the ZTMM Identity and Visibility & Analytics pillars; **Optimal** is difficult without equivalent continuous risk scoring.

### 5.2 Intune — compliance, app protection, Windows Update for Business reporting, Endpoint Privilege Management

- **(A) Commercial signals.** Detailed configuration state, health attestation, encryption status, OS version, jailbreak/root detection; continuous compliance evaluation results; app-launch events, app-protection enforcement outcomes (data-transfer blocked, copy/paste/save-as suppressed); WUfB per-device update state, patch success/failure, deferral status, safeguard holds, error codes/timing; EPM elevation requests/approvals/denials with process metadata (hash, path, publisher).
- **(B) Constraining controls.** SI-4 (continuous device monitoring + app-level behavior + elevation events are sensitive monitoring data); AU-2/AU-3 (policy enforcement and elevation attempts are audit records); SC-7 (telemetry paths constrained to "core management only," not full analytics).
- **(C) Documentation status.** No direct documentation. Public Intune docs describe data collection in the global Azure commercial environment without explicit GCC-Moderate addressing; Government-specific Intune docs are Azure Government (.us) and out of scope.
- **(D) Workarounds and fidelity loss.** Graph API exports into Log Analytics / Sentinel; built-in Intune reports where present (compliance status, basic update state); custom Power BI over exported device/compliance/update data. Fidelity lost: less granular and less frequent telemetry, limited behavioral context, reduced cross-correlation with identity and data events.
- **(E) Compliance impact.** BOD 25-01 met if device compliance and update events are logged centrally; loss of fine-grained telemetry reduces investigation speed and precision. M-22-09 Device pillar needs supplementation with OS-level logs to demonstrate posture; ZTMM Devices and Visibility & Analytics push toward **Initial / Advanced**, not Optimal.

### 5.3 M365 core apps — Office diagnostic data, Copilot/AI, sensitivity labels, DLP

- **(A) Commercial signals.** Office "Optional" diagnostic data (UX telemetry, feature usage, performance, crashes, add-in behavior, document interaction patterns at telemetry level); Copilot/AI prompt and response **metadata** (structure and usage, not necessarily content), interaction patterns, feedback signals; sensitivity-label application/removal events with locations and patterns by user/department/workload; DLP policy match conditions, content fingerprints, user actions, override/justification metadata, device/location/app context.
- **(B) Constraining controls.** SI-4 (Office and Copilot user-behavior telemetry exported to AI/analytics services must be tightly controlled); AU-2/AU-3 (DLP incidents and label events are audit records, content-sensitive); SC-7 (outbound client telemetry to external analytics endpoints constrained when it carries detailed behavioral/policy-match information).
- **(C) Documentation status.** Confirmed restricted: GCC privacy settings default Office diagnostic data to **"Required" only** — Optional diagnostic data is suppressed. Copilot and rich DLP analytics: no direct GCC-Moderate documentation; Purview docs mention government support generally but not at full analytics parity.
- **(D) Workarounds and fidelity loss.** Purview audit logs and DLP alerts exported via Graph / Management Activity API; custom label-usage reports from SharePoint/OneDrive/Exchange metadata + unified audit log; server-side logs (SharePoint access, Exchange message trace) instead of client-side telemetry. Fidelity lost: fine-grained Office client telemetry, Copilot usage patterns, behavioral DLP analytics (override behavior, near-misses, behavioral trends).
- **(E) Compliance impact.** BOD 25-01 met for centralized DLP and label-event logging; rich behavioral analytics for "rapid detection" weakened. M-22-09 Data pillar enforcement works but analytics-driven tuning is weaker; ZTMM Data + Visibility & Analytics typically **Advanced at best**.

### 5.4 Continuous Access Evaluation (CAE)

- **(A) Commercial signals.** Token issuance / refresh / revocation events; session state changes (revoked, invalidated); policy-relevant events (password changes, account disablement, device-compliance changes, location changes, high-risk detections); near-real-time event streams between Entra ID and resource services (Exchange, SharePoint, Teams).
- **(B) Constraining controls.** SI-4 (event streams are monitoring); AU-2/AU-3 (CAE-triggering events are audit events); SC-7 (cross-boundary signaling to non-GCC services constrained).
- **(C) Documentation status.** Inferred degraded. Basic CAE policy enforcement appears available with Entra ID licensing; the real-time signaling fidelity required for sub-minute revocation may be throttled by boundary inspection / proxies. CAE-capable client behavior is signaled in tokens via the `xms_cc` claim, which agencies can audit to confirm the path is at least negotiated.
- **(D) Workarounds and fidelity loss.** Short access-token lifetimes (60–90 min) to limit exposure without CAE; frequent re-authentication and CA re-evaluation; SIEM-triggered Graph API revocation scripts where possible. Fidelity lost: sub-second revocation; higher user friction; slower containment of compromised sessions.
- **(E) Compliance impact.** BOD 25-01 not directly mandating CAE but closely aligned with continuous-enforcement intent. M-22-09 Identity pillar emphasizes continuous verification and rapid revocation — without full CAE, agencies must compensate with shorter token lifetimes and strong monitoring; ZTMM Identity + Automation & Orchestration are difficult to push to Optimal.

### 5.5 Windows Update for Business reporting (depth and trend telemetry)

This area overlaps with §5.2 but is treated separately because it has its own asset-visibility consequence under BOD 25-01. Outbound flow to "Commercial Global Service" endpoints for WUfB telemetry is often blocked by boundary firewalls in agency environments. Agencies fall back to local GPO-based reporting or third-party inventory tools. Fidelity lost: real-time fleet-wide patch-compliance scoring; the "asset-visibility" requirement of BOD 25-01 is harder to satisfy.

---

## 6. Consolidated Telemetry-Gap Matrix

Each row is a specific telemetry field or metric. Source-dashboard, ZTMM mapping, and the four impact dimensions are normalized across the four AI analyses. Where unavailability cannot be confirmed from Microsoft documentation in the GCC-Moderate (.com) context, the row is marked **Inferred**.

| Missing signal | Source | Documented? | ZTMM pillar(s) | ZTMM level (if present) | Zero Trust impact | Anomaly detection | Insider risk | Forensics |
|---|---|---|---|---|---|---|---|---|
| Communication patterns (`ChatCount` vs `EmailCount`) | Adoption Score | **Yes** | Identity; Visibility & Analytics | Advanced | No "expected communication behavior" baseline for identity verification | No baseline for normal user-interaction volume | **Critical** — loss of "Digital Disengagement" / flight-risk signal | Low — usage volume rarely the smoking gun |
| Content collaboration (`PhysicalAttachments` vs `CloudLinks`) | Adoption Score | **Yes** | Data; Visibility & Analytics | Advanced | Inability to enforce/monitor cloud-only collaboration policies | **High** — regression to legacy methods to bypass DLP/scan unmonitored | **High** — users hoarding data via local copies | Moderate — harder to establish intent |
| Mobility (multi-platform usage patterns) | Adoption Score | **Yes** | Identity; Devices | Initial → Advanced | Cannot use "unusual platform" as account-takeover signal | Loss of platform-shift anomaly | Moderate — disengagement via specific workstation | Low |
| Meetings participation telemetry | Adoption Score | **Yes** | Visibility & Analytics | Advanced | Reduced behavioral context for risk scoring | No baseline for collaboration shifts | Lowers sensitivity to insider behavior changes | Missing participation data for activity reconstruction |
| Apps Health (update channel, version telemetry) | Adoption Score | **Yes** | Applications & Workloads; Visibility & Analytics | Advanced | Limits app/version posture as policy input | No outdated-app anomaly trends | Indirect | No version-change history correlated to incidents |
| Network connectivity scores (per location) | Adoption Score | **Yes** | Networks; Visibility & Analytics | Advanced → Optimal | Cannot distinguish real outages from path manipulation in access decisions | Hides localized connectivity drops indicating targeted disruption | Insiders degrading/rerouting traffic from specific sites harder to see | Reduced evidence of when/where network conditions shifted |
| Endpoint readiness baselines (tenant-wide) | Adoption Score | **Yes** | Visibility & Analytics | Advanced | No global posture view for ZT policy tuning | No tenant-wide deviation detection | Subtle group-level shifts harder to see | Weakens reconstruction of baseline drift |
| INR real-time path metrics (latency/jitter/packet-loss) | Microsoft INR | **Yes** | Networks; Visibility & Analytics | Advanced → Optimal | No "expected path" baseline for path-aware trust | **Infinite gap** — no native ability to detect BGP hijack, DNS manipulation, MITM | Insiders using unusual paths invisible | Cannot reconstruct routing during incident windows |
| Device boot performance / GP processing / desktop load | Endpoint Analytics — Advanced | Inferred (sovereign-list excludes Moderate) | Devices; Visibility & Analytics | Advanced → Optimal | Coarse compliance/AV posture only; degradations not risk inputs | Boot-time outliers as weak compromise signal lost | Tools/drivers destabilizing endpoints invisible | Cannot reconstruct device performance around incident |
| App reliability (`AppCrashCount`, hang rates, stability) | Endpoint Analytics — Advanced | Inferred | Devices; Applications & Workloads | Advanced → Optimal | Cannot use unstable apps as risk signal | Crash clusters indicating exploit attempts masked | Insiders testing unapproved tools obscured | Cannot correlate app instability with incidents |
| Resource performance (`AverageProcessorUsage`, memory spikes) | Endpoint Analytics — Advanced | Inferred | Devices | Advanced → Optimal | "Resource health" cannot drive dynamic access decisions | **High** — hidden miners, exfil tools bypassing AV go unnoticed | Unauthorized software by power users masked | Loss of CPU/RAM history to correlate with data egress |
| Stop-error restarts | Endpoint Analytics — Advanced | Inferred | Devices; Visibility & Analytics | Advanced → Optimal | Impairs real-time device-state verification | Loses automated restart-anomaly detection | N/A | Missing restart event correlation |
| Battery health / Work-from-anywhere readiness | Endpoint Analytics — Advanced | Inferred | Devices | Advanced | Reduced confidence in remote-endpoint trust | Less baseline for remote connectivity patterns | Unusual remote-only patterns obscured | Limited readiness-score history |
| Device performance anomalies (post-config/policy/OS regression) | Endpoint Analytics — Advanced | Inferred | Devices; Visibility & Analytics | Advanced → Optimal | Weakens continuous device-integrity verification | Core loss of automated regression detection | Targeted policy changes harming subsets of users masked | No anomaly-event timeline |
| Entra real-time risk scores / Identity Protection | Entra ID | Inferred blocked | Identity; Visibility & Analytics | Advanced → Optimal | Detection delay: minutes (commercial) → hours/days (GCC-M) | ML-driven impossible-travel, atypical-IP detection lost | Low-and-slow spraying invisible | Post-hoc only via log correlation |
| Cross-tenant access telemetry (B2B, Direct Connect) | Entra ID | Inferred blocked | Identity | Advanced | Less context for cross-tenant risk decisions | Cross-tenant anomaly correlation lost | External-collaboration insider patterns harder to see | Cross-tenant timeline reconstruction limited |
| Real-time CAE revocation paths (sub-second) | Entra ID + workloads | Inferred blocked | Identity; Automation & Orchestration | Optimal | Token-theft window 60–90 min vs. <15 min commercial | Mid-lifetime hijacks not auto-cut | Compromised sessions persist | Limited to token-expiry timeline |
| App-protection policy violation analytics | Intune | Inferred blocked | Devices; Applications & Workloads | Advanced | Snapshot compliance only; no real-time violation flag | Sideloaded / shadow apps invisible on BYOD | "Authorized but malicious" elevations masked | No app-protection telemetry for IR |
| WUfB deployment health trends / per-device error codes | Intune | Inferred blocked | Devices; Visibility & Analytics | Advanced | No real-time fleet patch posture for ZT | 7–14 day reporting lag | Patch state on specific devices opaque | Patch-window-aware forensics weakened |
| EPM elevation operational analytics (process metadata) | Intune | Inferred blocked | Devices; Identity; Visibility & Analytics | Advanced → Optimal | No elevation-as-risk input in CA | Anomalous elevations not "scored" centrally | Insider elevation patterns invisible | Elevation timeline reconstruction limited |
| Office "Optional" diagnostic data | M365 core | Confirmed restricted (defaults to Required) | Applications & Workloads; Devices | Advanced | Reduced client-side feature/use telemetry for trust | "Contextual glue" between apps lost | Lateral movement via Office/Teams cross-app navigation invisible | Cannot rewind client-side behavior |
| Copilot / AI prompt-response telemetry richness | M365 core | Inferred blocked | Applications & Workloads; Visibility & Analytics | Advanced | Limited AI-usage posture | Anomalous AI-usage patterns invisible | AI-mediated data hoarding harder to spot | Limited AI-interaction reconstruction |
| Sensitivity-label usage analytics | M365 core | Inferred blocked | Data; Visibility & Analytics | Advanced → Optimal | Label-state-aware policies coarser | Bulk label changes / mass decryption signals delayed | Insider label-stripping behavior less visible | Label-history forensic detail reduced |
| DLP behavioral richness (override, near-miss, fingerprint context) | M365 core | Inferred blocked | Data; Visibility & Analytics | Advanced → Optimal | Static DLP only; no behavior-aware policy | Intent-based detection absent | Override-pattern insider signal lost | Reduced DLP forensic context |
| Long-term EUII (BSSID, public IP, subnet/building) | Teams CQD | Available, retention-limited (28 days) | Networks | Advanced → Optimal | Trusted-location verification weakened for >28-day-old context | Limits delayed impossible-travel detection in Teams | Low | **Critical** forensic cliff at 28 days |
| Cross-product 12+ month historical pivots | M365 Usage Analytics | Available with reduced fidelity | Visibility & Analytics | Advanced | Shorter-window decisions only | "Low and slow" attacks across months hard to visualize | Long-term access-shift detection limited | Severely reduced retrospective breach analysis |

---

## 7. Cybersecurity Vulnerabilities — MITRE ATT&CK Mapping

Compensating-control honesty: every "compensating control" below assumes the agency has stood up the necessary local analytics. Without that investment, the gap is full.

### 7.1 Identity and session attacks (Entra ID)

| Attack pattern | MITRE TTP | Blocked / degraded signal | Detection gap | Compensating control |
|---|---|---|---|---|
| Credential stuffing / password spraying | T1110, T1078 | Identity Protection ML risk detections; aggregated sign-in anomaly models | Commercial: minutes. GCC-M: hours to days (periodic SIEM correlation) | CA + MFA + lockout + custom SIEM rules. No ML-driven low-and-slow spraying detection. |
| Token theft / session hijacking / Pass-the-Cookie | T1550.003, T1550.004, T1528 | Real-time sign-in risk changes; CAE event streams | Commercial: <15 min. GCC-M: up to full token lifetime (60–90 min) | Shorter token lifetimes; strict device compliance; SIEM-triggered Graph revocation. |
| Impossible travel / location anomalies | T1078, T1090 | Global impossible-travel models, cross-tenant telemetry | Commercial: minutes. GCC-M: hours to days, often missed | Custom geo-correlation in agency SIEM; many do not build this. |
| MFA fatigue / prompt bombing | T1621 | Behavioral risk models for abnormal MFA prompt frequency | Commercial: minutes (risk-based block). GCC-M: hours to days | FIDO2, number matching, user education. Volume-of-attempts not auto-flagged. |

### 7.2 Device and endpoint attacks (Intune)

| Attack pattern | MITRE TTP | Blocked signal | Detection gap | Compensating control |
|---|---|---|---|---|
| Privilege escalation (EPM bypass) | T1068 | EPM operational analytics; elevation behavioral telemetry | Commercial: real-time anomaly flagging. GCC-M: 48+ hours via compliance snapshots | Endpoint logs + SIEM correlation; no native equivalent. |
| Delayed-patch exploitation | T1190 / T1068 | WUfB deployment health trends; regression telemetry | Commercial: hours. GCC-M: 3–7 day gap (weekly manual reports) | Basic compliance reporting present; trend insights missing. |
| Malicious app sideloading (BYOD) | T1474, T1574.002 | App-protection policy violation analytics | Commercial: real-time. GCC-M: 24–48 hours | Periodic device checks; no real-time signal. |

### 7.3 Data movement (M365 core)

| Attack pattern | MITRE TTP | Blocked signal | Detection gap | Compensating control |
|---|---|---|---|---|
| Sensitivity-label-bypass exfiltration | T1048.003 | Label usage analytics; rich DLP behavioral context | Commercial: near-real-time. GCC-M: 24–72 hours, basic incident counts only | Static DLP regex rules; no intent-based detection. |
| Lateral movement via shared links (Teams/OneDrive) | T1021.006, T1534 | Office diagnostic telemetry (anomalous file-access patterns); label analytics | Commercial: minutes–hours. GCC-M: days | Manual audit-log/eDiscovery review; limited correlation. |
| Persistence via Office macros | T1547.009 | Office diagnostic / crash telemetry flagging anomalous macro execution | Commercial: hours. GCC-M: no equivalent; manual investigation 3–7 days | Manual Purview searches + endpoint telemetry outside M365. |
| Persistence via SharePoint OAuth / browser fingerprint | T1098.005 | Rich DLP context: client/browser fingerprint, API access details | Commercial: real-time. GCC-M: limited fingerprint telemetry | Static rules only; adversaries persist via "trusted" browsers. |
| Automated exfiltration | T1020 | Real-time risk-based DLP triggers | Commercial: minutes. GCC-M: 24+ hours processing latency | Static DLP; intent-aware detection absent. |

### 7.4 Network and session (INR + CAE)

| Attack pattern | MITRE TTP | Blocked signal | Detection gap | Compensating control |
|---|---|---|---|---|
| Adversary-in-the-middle / BGP hijack / DNS manipulation | T1557, T1565.002 | INR real-time path / latency / jitter telemetry | Commercial: sub-minute. GCC-M: not available | Third-party SD-WAN/SASE; external DNS monitoring. |
| Session persistence after network change | T1550.001 | CAE real-time revocation | Commercial: seconds–minutes. GCC-M: up to 60 min token lifetime | Shorter tokens; manual revocation; CA without continuous signals. |

### 7.5 Cross-cutting "sovereign blind spot" compound chains

Two attack chains become difficult to detect in GCC-Moderate without dedicated agency analytics:

**Chain A — T1190 → T1550.001 → T1048.003.** Initial access via delayed-patched Intune device + token theft (no CAE, no Entra Identity Protection real-time risk) + exfiltration via label-stripped OneDrive link (no rich DLP). Three blocked telemetries simultaneously. Commercial cloud detection: end-to-end <30 min. GCC-Moderate: days to weeks if no compensating analytics exist.

**Chain B — T1110.004 → T1068 → T1557.** Credential stuffing (no Entra risk) + privilege escalation on compromised device (no EPM analytics) + MITM via INR-blind routing. Commercial: minutes. GCC-Moderate: undetected until manual investigation.

**Gemini's "ghost compromise" framing — three-step concrete scenario:**
1. **Identity** — adversary uses residential proxy for sign-in; degraded global behavioral signals classify it as low risk.
2. **Device** — adversary uses BYOD with sideloaded grey-ware; advanced compliance telemetry blocked, device reports compliant.
3. **Data** — adversary performs low-and-slow exfiltration of sensitivity-labeled data; suppressed Office diagnostic telemetry hides the read-to-bulk-sync behavioral shift.
**Net.** A nation-state actor can exfiltrate substantial data over weeks without ever crossing a "high" severity threshold, because each individual action stays below the static-rule threshold inside GCC-Moderate.

---

## 8. CISA Zero Trust Maturity Model — Pillar-Level Impact

Pillar mapping below is per CISA ZTMM v2.0 (April 2023). All maturity ratings reflect the **achievable-without-additional-agency-analytics** baseline. Each pillar can typically be lifted one tier (toward Advanced or Optimal) by investing in agency-side Sentinel/Log Analytics + custom analytics over exported telemetry.

| Pillar | Achievable without agency analytics | Gating gap | Achievable with agency analytics | What "Optimal" requires |
|---|---|---|---|---|
| **Identity** | Initial | Real-time Identity Protection ML risk + CAE | Advanced | Continuous risk scoring equivalent to Microsoft commercial pipeline |
| **Devices** | Initial | Endpoint Analytics Advanced + Intune behavioral analytics | Advanced | Continuous performance/anomaly scoring with automated remediation |
| **Networks** | Initial | INR + CQD long-retention EUII | Advanced (with third-party SD-WAN/SASE) | Native M365-integrated dynamic optimization (not available; requires third-party) |
| **Applications & Workloads** | Initial → Advanced | Office Optional diagnostic + Copilot telemetry | Advanced | Behavior-aware app monitoring with predictive analytics |
| **Data** | Initial → Advanced | Adoption Score collaboration baselines + rich DLP behavioral context | Advanced | Behavior-aware DLP, adaptive policies, rich override-pattern analytics |
| **Visibility & Analytics** (cross-cutting) | Initial → Advanced | All of the above | Advanced | UEBA-class baselines plus historical correlation across pillars |
| **Automation & Orchestration** (cross-cutting) | Initial | Real-time CAE; automated risk-based response | Advanced | Event-driven automatic response, integrated across pillars |

**The structural ceiling.** Without agency-side analytics, the GCC-Moderate environment caps near **Initial** maturity in Identity, Devices, and Networks; reaching **Advanced** requires meaningful agency engineering investment; **Optimal** in any pillar requires either Microsoft platform changes (e.g., MAS 2026 boundary refinement) or substantial agency-built equivalents to Microsoft commercial ML pipelines.

---

## 9. Compliance Posture — BOD 25-01, M-22-09, M-21-31

| Mandate | Met by GCC-Moderate alone? | Gap | What closes the gap |
|---|---|---|---|
| **CISA BOD 25-01** (cloud secure configuration; logging and visibility) | Core logging requirements **met** if all available logs are exported to Sentinel/Log Analytics with appropriate retention. | Spirit of "rapid detection and investigation" requires analytics fidelity GCC-Moderate cannot natively provide. | Agency-built local analytics, custom KQL/SIEM rules, third-party UEBA. |
| **OMB M-22-09** (Federal Zero Trust Strategy) | Identity pillar continuous-monitoring intent **not met** without compensating analytics; Network pillar partially blocked by INR absence. | Identity (CAE/Identity Protection); Network (INR); Data (rich DLP behavioral context). | Equivalent agency risk scoring; third-party SASE/SD-WAN; behavior-aware DLP overlay. |
| **OMB M-21-31** (Tier 3 logging) | **Met** for Tier 1–3 if all categories (Entra non-interactive sign-ins, service-principal sign-ins, MailItemsAccessed, etc.) are enabled and routed. | Tier 3 advanced behavioral analytics interpretation — not unavailability of the underlying logs. | UIAO Telemetry Completeness Scorecard; quarterly verification per Section 11. |
| **NIST SP 800-207** (Zero Trust Architecture) | Architecture is consistent with the model, but PE/PA require continuous trust signals that GCC-Moderate constrains. | Continuous behavioral risk signals to feed the Policy Engine. | Build trust-algorithm overlay in agency SIEM. |

The unifying frame, used by all four AIs in different language: **An agency in GCC-Moderate can be technically compliant with FedRAMP yet structurally less observable than a commercial enterprise** until it builds its own observability stack on top of the FedRAMP boundary.

---

## 10. Operational Findings (UIAO_INV_001 — incorporated)

The following findings come from the UIAO Deep M365/Azure Dashboard Coverage Investigation (UIAO_INV_001 v1.0, 2026-04-24) and apply to the same GCC-Moderate boundary. They convert the architectural telemetry conclusions above into directly-actionable misconfigurations, scored on a 0–100 dashboard-completeness scale.

### 10.1 Symptoms catalog (deduplicated against Section 5 and Section 7)

| ID | Symptom | Severity | Root cause | Detection heuristic |
|---|---|---|---|---|
| SYM-001 | Invisible non-interactive / service-principal / managed-identity sign-in activity | **Critical** | Entra diagnostic settings do not enable `NonInteractiveUserSignInLogs`, `ServicePrincipalSignInLogs`, `ManagedIdentitySignInLogs` by default. | Query `AADNonInteractiveUserSignInLogs` in Sentinel — zero results with active SPNs/MIs = not collected. |
| SYM-002 | Exchange mailbox-access blind spot (`MailItemsAccessed`) | **Critical** | Pre-2025-Jan CISA Expanded Cloud Logs Playbook, only Audit Premium captured this; now in Standard but must be operationalized. | Query `OfficeActivity` for `Operation == "MailItemsAccessed"` over 7d — no results = gap. |
| SYM-003 | Teams media-relay blind spots; CQD/QER pipeline not in Sentinel | **High** | Teams call quality data flows through CQD/QER, not natively into Sentinel; PSTN and Direct Routing legs sparsely instrumented. | Attempt to query packet-loss/jitter/RTT in Sentinel — not present; only OfficeActivity Teams membership/messaging. |
| SYM-004 | Intune compliance-state lag | **High** | Diagnostic settings must be manually enabled; evaluation-cycle latency; aggressive DCR filtering of high-volume Win32 detection events removes security-relevant data. | Compare Intune admin-center reports to `IntuneDevices` table — stale or empty = misconfigured. |
| SYM-005 | Conditional Access evaluation-log incompleteness | **High** | CA evaluation depends on sign-in log completeness; Entra default 30-day retention without diagnostic settings loses historical CA evaluation. | `SigninLogs` filtered for `ConditionalAccessStatus == "notApplied"` to find scope misconfigurations. |
| SYM-006 | Sentinel correlation false-negatives from missing data sources | **Critical** | Analytic rules joining tables (e.g., `SigninLogs` ⋈ `DeviceEvents`) silently miss when a source is not configured. | Run Sentinel health diagnostics; check `Usage` table for unexpectedly low data volume. |
| SYM-007 | Power Platform activity opacity | **Medium** | Power Apps / Power Automate / Power BI activity flows through Purview unified audit, not a dedicated Sentinel connector; Dataverse Application Insights requires premium. | Search `OfficeActivity` for `OfficeWorkload in ("PowerApps","MicrosoftFlow","PowerBI")`. |
| SYM-008 | SharePoint search-query telemetry gap | **Medium** | `SearchQueryInitiatedSharePoint` previously Premium-only; now in Standard per CISA expansion but requires enablement. | Query for `SearchQueryInitiatedSharePoint` in `OfficeActivity`/Purview — zero events = not enabled. |
| SYM-009 | GCC feature-parity drift | **High** | Microsoft cloud feature availability documents many features as GA in Commercial but Preview or N/A in GCC; releases follow Commercial-first cadence. | Compare deployed GCC feature set against current Commercial feature list quarterly. |
| SYM-010 | Purview Audit retention cliff | **Critical** | Audit Standard retains 180 days max; Premium extends to 1 yr (10 yr add-on). E3/G3 licensing creates a forensic blind spot vs. APT dwell times. | Query audit log >180 days old; if absent on Standard, gap confirmed. |

### 10.2 Dashboard completeness scores (UIAO scoring methodology)

Score = (a) percentage of expected telemetry types available × (b) default-enabled × (c) Sentinel-integration path × (d) GCC parity confirmed.

| Product | Score | Primary remaining gap |
|---|---|---|
| Entra ID (P2) | 75 | NonInteractive, ServicePrincipal, ManagedIdentity logs not on by default |
| Exchange Online | 70 | `MailItemsAccessed` newly available in Standard, requires operationalization |
| SharePoint Online | 65 | `SearchQueryInitiatedSharePoint` requires enablement |
| Microsoft Teams | 55 | CQD/QER outside Sentinel; PSTN/Direct Routing telemetry incomplete |
| Microsoft Intune | 60 | Diagnostic settings manual; Win32-detection event volume forces aggressive filtering |
| Defender for Endpoint | 85 | Generally well-instrumented; some advanced tables may lag in GCC |
| Defender for Office 365 | 80 | Some Defender XDR connector data types may have limited GCC support |
| Defender for Identity | 80 | On-prem sensor required; hybrid gaps |
| Defender for Cloud Apps | 70 | `CloudAppEvents` requires Purview unified audit enabled |
| Purview Audit | 60 | Standard 180-day cliff; Premium needed for forensic-grade depth |
| Microsoft Sentinel | 75 | Platform audit requires `CloudAppEvents` via Defender XDR connector |
| Power Platform (Apps / Automate / BI) | 45 | No native Sentinel connectors; relies on Purview unified audit |
| Dynamics 365 | 40 | Heavy reliance on Application Insights; limited native security event coverage |
| Microsoft Stream | 25 | No native Sentinel connector |
| Windows Autopilot | 30 | No direct Sentinel connector; deployment telemetry siloed in Intune |

---

## 11. 60-Day Tactical Remediation Plan

This plan combines the UIAO_INV_001 priorities with the architectural telemetry mitigations from the four AI analyses. It is the operational realization of the conclusion that **GCC-Moderate compliance + observability requires agency engineering, not just license selection.**

### 11.1 Priority 1 — Foundation (Week 1–2)

| # | Action | Products | Effort | Risk if not addressed |
|---|---|---|---|---|
| 1 | **Enable all Entra ID diagnostic-settings log categories** — `NonInteractiveUserSignInLogs`, `ServicePrincipalSignInLogs`, `ManagedIdentitySignInLogs`, `RiskyUsers`, `UserRiskEvents`, `ProvisioningLogs`, `MicrosoftGraphActivityLogs`, `NetworkAccessTrafficLogs` to Sentinel Log Analytics. | Entra ID | 2–4 h | SYM-001 |
| 2 | **Operationalize CISA Expanded Cloud Logs** — enable and validate `MailItemsAccessed`, `MailItemsSent`, `SearchQueryInitiatedSharePoint`, `SearchQueryInitiatedExchange` in Purview Audit Standard; deploy Sentinel analytic rules per CISA playbook. | Exchange / SharePoint / Purview | 1–2 d | SYM-002, SYM-008 |
| 3 | **Configure Intune diagnostic settings** with DCRs filtering Win32-detection event volume while preserving security-relevant events. | Intune / Sentinel | 1 d | SYM-004 |
| 4 | **Validate via KQL** (Section 13.3) — record baseline scorecard. | Sentinel | 0.5 d | SYM-006 |

### 11.2 Priority 2 — Expansion (Week 3–4)

| # | Action | Products | Effort |
|---|---|---|---|
| 5 | Deploy Teams **QER v5.0** Power BI templates; establish baseline call-quality metrics + alerting thresholds; export EUII for long-term retention to circumvent the 28-day forensic cliff. | Teams | 2–3 d |
| 6 | Deploy **Conditional Access analytic rules** from the Microsoft Entra Sentinel content hub. | Entra / Sentinel | 0.5 d |
| 7 | Deploy Exchange Online and SharePoint Online **security solutions** from Sentinel content hub — RBAC delegation changes, transport-rule changes, VIP mailbox monitoring. | Exchange / SharePoint / Sentinel | 1–2 d |

### 11.3 Priority 3 — Depth (Week 5–6)

| # | Action |
|---|---|
| 8 | Power Platform monitoring via Purview unified audit — Sentinel rules for suspicious Power Automate flow creation and Power Apps data access. |
| 9 | Begin GCC feature-parity audit; document delta as governance risk-register entries. |

### 11.4 Priority 4 — Maturation (Week 7–8)

| # | Action |
|---|---|
| 10 | Build Sentinel **Telemetry Completeness Workbook** — data-freshness checks across all expected tables. |
| 11 | Dynamics 365 Application Insights prototype for security telemetry. |
| 12 | Establish quarterly **GCC Feature Parity Review** (NEW — Canon Steward approval required). |
| 13 | Establish monthly **Telemetry Completeness Scorecard** for continuous-ATO review (NEW — Canon Steward approval required). |

---

## 12. Boundary Modernization Path — TIC 3.0 and MAS 2026

**Position taken in this assessment.** The four AI sources disagree on whether later directives **authorize removing** FedRAMP boundaries. This document adopts the **reconciled view**:

> Modern mandates require telemetry that traditional FedRAMP authorization boundaries inhibit. This creates sustained pressure to modernize boundary implementation — for example, through scope refinement and boundary-shrinking approaches such as MAS 2026 — while maintaining a defined authorization boundary required for compliance under FISMA.

### 12.1 What the policy stack actually says

| Source | Effect on GCC-Moderate boundary |
|---|---|
| EO 14028 (2021) | Drives Zero Trust adoption; implicitly increases telemetry demand. |
| OMB M-21-31 | Requires Tier 3 logging — achievable inside the boundary if all categories are enabled. |
| OMB M-22-09 | Federal Zero Trust Strategy — drives Identity-pillar telemetry demand. |
| TIC 3.0 | Permits cloud-direct connectivity (vs. legacy MTIPS), enables SASE/ZTNA patterns inside the FedRAMP boundary. |
| EO 14117 (2024) | **Adds** restrictions on precise geolocation — *tightens*, does not loosen, boundary controls. |
| EO 14144 (Jan 2025) | Strengthens FedRAMP baselines (does not authorize boundary removal). |
| June 2025 EO | Modernizes FedRAMP, reduces process burden — does not authorize boundary removal. |
| **MAS 2026** | **Practical resolution.** Narrows boundary scope; allows more commercial-like functionality; explicitly excludes telemetry pipelines from the authorization boundary. The boundary itself remains. |

### 12.2 Operational implication for GCC-Moderate

MAS 2026 scope refinement is the realistic path to recovering some currently-blocked telemetry by **removing Microsoft's commercial telemetry pipelines from the agency's authorization scope** rather than blocking the data flow at the network boundary. This shifts the conversation from "can the data leave?" to "is the receiving service in scope of my ATO?"

### 12.3 Escalation channels for boundary-related issues

(These channels are GCC-High-scoped in the underlying source guides; the same mechanism applies to GCC-Moderate boundary issues.)

| Destination | Contact |
|---|---|
| FedRAMP PMO | `info@fedramp.gov`; ticket at `help.fedramp.gov` |
| Azure Government / Azure FedRAMP escalation | `AzFedDoc@microsoft.com` |
| Microsoft 365 GCC FedRAMP escalation | `O365FedRAMP@microsoft.com` |

Realistic timeline expectations: Day 0–1 acknowledgment; Week 1–2 MAS adoption-plan response; Week 3–6 SCN (Significant Change Notification) filing window for boundary-scope refinements.

---

## 13. Workarounds, Compensating Architectures, and Validation

### 13.1 Workarounds by area

| Constraint | Primary workaround | Fidelity loss |
|---|---|---|
| Entra Identity Protection ML scoring | Graph API → Sentinel + custom KQL risk rules | No proprietary continuously-tuned ML; less real-time; higher operational burden |
| Cross-tenant analytics | Manual cross-tenant log correlation in Sentinel | No vendor-supplied global threat intelligence context |
| Intune behavioral telemetry | Graph API exports + custom Power BI / Sentinel | Snapshot compliance only; no behavioral context |
| Office Optional diagnostic | Server-side audit (SharePoint access, message trace) | No client-side feature/use telemetry |
| Copilot/AI telemetry richness | Purview audit logs via Graph / Management Activity API | Basic incident counts only |
| INR routing optimization | Third-party SD-WAN / SASE | No native M365-integrated routing; agency-side detection of MITM/DNS manipulation only |
| CAE sub-second revocation | Short token lifetimes (60–90 min) + SIEM-triggered Graph revocation | Up to full token lifetime exposure window |
| CQD EUII 28-day retention | Scheduled CQD export to Log Analytics with extended retention | Operational overhead; storage cost |

### 13.2 Compensating architecture components (the agency-side stack)

To recover Advanced ZTMM maturity, an agency typically needs:

1. **Sentinel + Log Analytics workspace** with all M365/Entra/Intune diagnostic settings routed in.
2. **Defender XDR connector** for `CloudAppEvents`, `EmailEvents`, `DeviceEvents`, identity tables.
3. **Purview unified audit** ingestion for Power Platform and Office activity.
4. **Custom analytic rules** for the gaps the platform doesn't ML-score (impossible travel, MFA fatigue, low-and-slow spraying, behavioral DLP).
5. **Local risk-scoring overlay** that consumes the above to produce a continuous user-risk and device-risk signal feeding the Policy Engine.
6. **Third-party SD-WAN / SASE** for INR-equivalent path telemetry and MITM/DNS-manipulation detection.
7. **Long-term forensic store** (1+ year for general audit, 10 years for high-impact systems) to defeat the 28-day CQD EUII cliff and the 180-day Audit Standard cliff.

### 13.3 Validation KQL (executable in Sentinel Log Analytics)

```kusto
// 13.3.1 — Validate Entra ID diagnostic-setting completeness
union withsource=TableName SigninLogs, AADNonInteractiveUserSignInLogs,
  AADServicePrincipalSignInLogs, AADManagedIdentitySignInLogs, AuditLogs,
  AADProvisioningLogs, AADRiskyUsers, AADUserRiskEvents
| summarize RecordCount = count(), LastRecord = max(TimeGenerated) by TableName
| order by TableName asc

// 13.3.2 — Validate CISA Expanded Cloud Logs operationalization (MailItemsAccessed)
OfficeActivity
| where TimeGenerated > ago(7d)
| where Operation == "MailItemsAccessed"
| summarize Count = count(), FirstSeen = min(TimeGenerated), LastSeen = max(TimeGenerated)
| extend Status = iff(Count > 0, "Operational", "NOT DETECTED — Action Required")

// 13.3.3 — Validate Intune diagnostic-settings ingestion
IntuneOperationalLogs
| where TimeGenerated > ago(7d)
| summarize RecordCount = count(), LastRecord = max(TimeGenerated)
| extend Status = iff(RecordCount > 0, "Ingesting", "NOT DETECTED")

// 13.3.4 — Master telemetry health check (data volume by table over 24h)
Usage
| where TimeGenerated > ago(1d)
| summarize DataVolumeMB = sum(Quantity) by DataType
| order by DataVolumeMB desc

// 13.3.5 — CA evaluation completeness — flag policies with high "notApplied" volume
SigninLogs
| where TimeGenerated > ago(7d)
| where ConditionalAccessStatus == "notApplied"
| summarize NotAppliedCount = count() by ConditionalAccessPolicies = tostring(ConditionalAccessPolicies)
| order by NotAppliedCount desc
| take 20

// 13.3.6 — Power Platform activity in unified audit
OfficeActivity
| where TimeGenerated > ago(30d)
| where OfficeWorkload in ("PowerApps", "MicrosoftFlow", "PowerBI")
| summarize EventCount = count() by OfficeWorkload, Operation
| order by OfficeWorkload, EventCount desc

// 13.3.7 — Exchange security baseline (RBAC, transport rules, mailbox permissions)
OfficeActivity
| where TimeGenerated > ago(7d)
| where OfficeWorkload == "Exchange"
| where Operation in ("New-ManagementRoleAssignment","Set-TransportRule","Set-RemoteDomain","Add-MailboxPermission")
| project TimeGenerated, UserId, Operation, Parameters = tostring(Parameters)
```

---

## 14. Source Reconciliation — Where the Four AIs Disagreed

This section is preserved for transparency. The combined assessment above resolves each disagreement by adopting the **most documented, most conservative position**.

| Question | Copilot | Gemini | Grok | Perplexity | Resolved position |
|---|---|---|---|---|---|
| How many M365 dashboards are unavailable in GCC-Moderate? | 4 | 4 | 2 (Adoption Score, Endpoint Analytics Advanced) | 1 (Adoption Score only) | **2 confirmed unavailable** (Adoption Score + INR), **1 inferred unavailable** (Endpoint Analytics Advanced tier), CQD and Usage Analytics are **available with operational caveats**. |
| Is Teams CQD available in GCC-Moderate? | "Unavailable" | "Limited retention" | "Available" | "Available" | **Available**, with 28-day EUII retention as the operational constraint. |
| Is M365 Usage Analytics available? | "Unavailable" | "Limited / restricted" | "Available" | "Available" | **Available** via the GCC-specific connector; Marketplace template app is the only missing variant. |
| Is the reverse-inference framework (NIST SI-4/AU-2/AU-3/SC-7) valid? | Accepted | Accepted ("one-way filter") | Accepted | Accepted as **methodological** but requires explicit "Inferred" labeling rather than asserted unavailability | **Accepted with explicit "Inferred blocked by FedRAMP boundary architecture" labeling.** |
| Is INR explicitly unavailable? | Inferred | "Confirmed Unavailable" with Microsoft URL | "EXPLICIT CONFIRMATION OF UNAVAILABILITY" with verbatim quote | Available evidence supports unavailability | **Yes — confirmed unavailable** (verbatim Microsoft text). |
| Are agencies in BOD 25-01 / M-22-09 violation? | "Stuck at Initial maturity" | "M-22-09 Violation" | "Puts agencies out of compliance" | More nuanced — core requirements achievable with agency analytics; Optimal maturity not | **Achievable with agency-side analytics; not free out of the box.** |
| Should Prompt 5 (TTPs + hour-level detection gaps) be answered? | Answered with detailed table | Answered with "Telemetry Paradox" framing | Answered with quantitative gap estimates | **Refused** — no Microsoft/FedRAMP source publishes hour-level detection gaps | Provided in Section 7 with explicit acknowledgment that detection-gap orders-of-magnitude are AI synthesis, not vendor-published numbers. |

**Memorable framings to retain in agency communications:**
- "False negative" (Perplexity) — absence of "not available" language is not evidence of availability
- "Telemetry Paradox" (Gemini) — controls meant to protect government data create a shadow zone where advanced attack patterns thrive
- "Forensic cliff" (Gemini) — the 28-day CQD EUII purge and 180-day Audit Standard retention create incident-discovery dead zones
- "Digital Quit" / "Digital Disengagement" (Gemini) — the missing communication-volume baseline is a flight-risk insider indicator
- "Grey-ware" (Gemini) — attacks that evade EDR but show as performance outliers, invisible without Endpoint Analytics
- "Sovereign blind spot compound chain" (Gemini) — multiple gaps combining to enable undetectable nation-state-grade exfiltration
- "Ghost compromise" (Gemini) — the proxy + BYOD + low-and-slow exfiltration scenario

---

## 15. References

### Microsoft documentation (load-bearing for this assessment)

1. *Microsoft Adoption Score report overview — Microsoft 365 admin* — `https://learn.microsoft.com/en-us/microsoft-365/admin/adoption/adoption-score?view=o365-worldwide` — verbatim "not available in GCC High, GCC, and DOD tenants."
2. *Microsoft 365 informed network routing* — verbatim "supports tenants in WW Commercial cloud but not the GCC Moderate, GCC High, DoD, Germany, or China clouds."
3. *Advanced Analytics overview — Microsoft Intune* — `https://learn.microsoft.com/en-us/intune/advanced-analytics/`
4. *Microsoft Intune Government Service overview* — `https://learn.microsoft.com/en-us/intune/intune-service/fundamentals/intune-govt-service-description`
5. *Endpoint analytics data collection — Microsoft Intune* — `https://learn.microsoft.com/mem/intune/endpoint-analytics/data-collection`
6. *Connect to GCC data with usage analytics* — `https://learn.microsoft.com/en-us/microsoft-365/admin/usage-analytics/connect-to-gcc-data-with-usage-analytics?view=o365-worldwide`
7. *Data and reports in CQD* — `https://learn.microsoft.com/en-us/microsoftteams/cqd-data-and-reports`
8. *Turn on and use Call Quality Dashboard* — `https://learn.microsoft.com/en-us/microsoftteams/turning-on-and-using-call-quality-dashboard`
9. *Configure Microsoft Entra diagnostic settings for activity logs*
10. *Logs available for streaming from Microsoft Entra ID*
11. *Learn about auditing solutions in Microsoft Purview*
12. *Support for data types in Microsoft Sentinel across different clouds*
13. *Privacy controls — overview* (Office privacy / GCC defaults to Required diagnostic data) — `https://learn.microsoft.com/en-us/deployoffice/privacy/overview-privacy-controls`
14. *Cloud feature availability for commercial and US Government customers*

### Policy and framework references

15. CISA Zero Trust Maturity Model v2.0 (April 2023) — `https://www.cisa.gov/sites/default/files/2023-04/zero_trust_maturity_model_v2_508.pdf`
16. CISA BOD 25-01 (cloud secure configuration)
17. OMB M-22-09 (Federal Zero Trust Strategy)
18. OMB M-21-31 (Tier 3 logging)
19. NIST SP 800-53 — controls SI-4, AU-2, AU-3, SC-7
20. NIST SP 800-207 (Zero Trust Architecture)
21. EO 14028 (May 2021)
22. EO 14117 (2024) — precise-geolocation restrictions
23. EO 14144 (Jan 2025) — FedRAMP baseline strengthening
24. June 2025 EO — FedRAMP modernization
25. CISA — *Microsoft Expanded Cloud Logs Implementation Playbook*, January 15, 2025

### Operational and community references

26. Microsoft Community Hub — *Microsoft Sentinel Platform: Audit Logs and Where to Find Them* (Dec 2025)
27. Microsoft Community Hub — *How to Ingest Microsoft Intune Logs into Microsoft Sentinel* (Apr 2026)
28. Charbel Nemnom — *Monitor Microsoft Intune with Microsoft Sentinel* (Oct 2024)
29. MSEndpointMgr — *Fine-Tuning Azure Sentinel Log Ingestion for Intune Script Execution* (Dec 2024)
30. Kevin Kieller (LinkedIn) — *Teams Reporting: Evolving but still gaps* (Nov 2024)
31. M365 Admin — *Teams QER v5.0 GA announcement* (Oct 2024)
32. *Real-time telemetry to troubleshoot poor meeting quality* (Teams)
33. CloudBrothers — *Continuous Access Evaluation* (`xms_cc` claim detail)

### Source AI conversations (this assessment was synthesized from these)

34. Microsoft Copilot — full conversation thread, March 2026
35. Google Gemini — full conversation thread, March 2026
36. Grok — full conversation thread, March 2026
37. Perplexity — full conversation thread, March 2026
38. UIAO_INV_001 — *Deep M365/Azure Dashboard Coverage Investigation*, v1.0, 2026-04-24

---

## Appendix A — Glossary (selected)

| Abbreviation | Definition |
|---|---|
| ATO | Authorization to Operate |
| BEC | Business Email Compromise |
| BOD | Binding Operational Directive (CISA) |
| CA | Conditional Access |
| CAE | Continuous Access Evaluation |
| CQD | Call Quality Dashboard (Teams) |
| DCR | Data Collection Rule (Azure Monitor) |
| EPM | Endpoint Privilege Management (Intune) |
| EUII | End-User Identifiable Information |
| GCC | Government Community Cloud |
| INR | Informed Network Routing (M365) |
| KQL | Kusto Query Language |
| MAS | Microsoft Authorization Sponsor (boundary refinement program) |
| MFA | Multi-Factor Authentication |
| MITM | Man-in-the-Middle |
| QER | Quality of Experience Report (Power BI templates for Teams) |
| RTA | Real-Time Analytics (Teams admin center) |
| SCN | Significant Change Notification (FedRAMP) |
| SIEM | Security Information and Event Management |
| SOC | Security Operations Center |
| TIC | Trusted Internet Connection |
| TTP | Tactics, Techniques, and Procedures (MITRE ATT&CK) |
| UAL | Unified Audit Log (Purview) |
| UEBA | User and Entity Behavior Analytics |
| WUfB | Windows Update for Business |
| XDR | Extended Detection and Response |
| ZTMM | Zero Trust Maturity Model (CISA) |

## Appendix B — Excluded source material

The following items from the source folder are **out of scope** for this Moderate-only assessment and not incorporated into the body of this document:

| Source | Reason for exclusion |
|---|---|
| `AWS_FedRAMP/*` | AWS GovCloud is FedRAMP High + DoD SRG IL2/4/5 + ITAR — not a Moderate environment. Findings retained as comparator only. |
| `FedRAMP Realignment/Grok_FedRAMP Escalation Guide.docx` | Originally GCC-High-scoped. Mechanism preserved in Section 12.3 (escalation channels). |
| `FedRAMP Realignment/grok_report (18–25).pdf`, `Grok/grok_report (18–21).pdf`, `InTune/grok_report (18–28).pdf` | Raw chat exports redundant with the corresponding DOCX analyses. |
| `2026_03_18_Answer*.pdf` | AI conversation snapshots from March 2026 redundant with the four DOCX analyses. |
| `Perplesixy/Merge-Docs.ps1`, `New_Macro_Option Explicit.txt`, `Normal.txt`, `Word_CoPilot_Learn_Format_Paste.txt` | Word formatting macros; not analysis content. |
| `tosteve.docx` | Three-line prompt fragment, not an analysis. |
| `httpswhalermike.github.iouiao-core#.txt` | URL fragment. |

## Appendix C — AWS GovCloud comparator (informational)

AWS GovCloud is **FedRAMP High + DoD SRG IL2/4/5 + ITAR** — not a Moderate environment. The same architectural pattern observed in M365 GCC-Moderate (boundary blocks high-fidelity telemetry from leaving the authorized zone) appears in AWS GovCloud, which reinforces the conclusion that the M365 telemetry gap is a **CSP-architecture pattern, not a Microsoft-specific decision**.

Comparator points worth retaining:
- AWS Nitro System provides hardware-isolation guarantees that mirror, in different form, the SC-7 boundary protection M365 uses.
- Amazon Location Service is only available in `us-gov-west-1` (Cognito dependency); third-party providers transmit query parameters outside GovCloud.
- CloudTrail single-region trails miss global service events from outside `us-gov-west-1` — must convert to multi-region.
- FIPS endpoints (`iam.us-gov.api.aws`) prevent accidental routing through commercial gateways.
- No native VPC Peering / Transit Gateway Peering between GovCloud and commercial accounts.
- OpenTelemetry pipelines must be manually built with FIPS collectors and audit logging.

These observations are **reference only** for this Moderate-only assessment; they neither apply to M365 GCC-Moderate boundary scope nor are they citable for FedRAMP Moderate compliance arguments.

---

*Prepared under the UIAO NO-HALLUCINATION PROTOCOL. All findings derive from the sources enumerated in Section 15. Items marked "Inferred blocked by FedRAMP boundary architecture" are explicitly architecturally reasoned per NIST 800-53 SI-4 / AU-2 / AU-3 / SC-7 rather than asserted from product documentation.*
