# Capability Dispositions

Capabilities are grouped by disposition. Per-signal detail is in
[`canon/data/gcc-moderate-telemetry-gaps.yaml`](../../../data/gcc-moderate-telemetry-gaps.yaml);
this file carries the per-capability narrative the data file does not.

## Confirmed unavailable (Microsoft documentation)

### Microsoft Adoption Score

- **Source:** [Adoption Score report overview](https://learn.microsoft.com/en-us/microsoft-365/admin/adoption/adoption-score?view=o365-worldwide)
- **Verbatim:** "This feature isn't available in GCC High, GCC, and DOD tenants." ("GCC" in this list = GCC-Moderate per Microsoft's own naming.)
- **Telemetry lost:** People Experiences (communication ratios, meetings, content collaboration, teamwork, mobility) and Technology Experiences (M365 Apps health, network connectivity scores, endpoint readiness baselines). Specific fields named: `AppCrashCount`, `BlueScreenCount`, `ChatCount` / `EmailCount`, attachment-vs-cloud-link frequency, multi-platform mobility flags.
- **Gap matrix rows:** `communication-patterns-chat-vs-email`, `content-collaboration-attachments-vs-cloudlinks`, `mobility-multiplatform-usage`, `meetings-participation`, `apps-health-version-channel`, `network-connectivity-scores-per-location`, `endpoint-readiness-baselines-tenant-wide`.

### Microsoft Informed Network Routing (INR)

- **Source:** Microsoft 365 informed network routing (commercial .com page).
- **Verbatim:** INR "supports tenants in WW Commercial cloud but not the GCC Moderate, GCC High, DoD, Germany, or China clouds."
- **Telemetry lost:** Real-time path-aware metrics — latency, jitter, packet loss between user locations and Microsoft front doors; per-ISP and per-peering path performance; continuous-feedback dynamic routing optimization.
- **Fallback:** Static or policy-based egress; third-party SD-WAN or SASE telemetry; local NetFlow / SNMP / synthetic-probe monitoring.
- **Gap matrix row:** `inr-realtime-path-metrics`.
- **Existing finding:** [`docs/findings/fedramp-gcc-moderate-informed-network-routing.md`](../../../../../docs/findings/fedramp-gcc-moderate-informed-network-routing.md).

## Documentation-limited (sovereign-cloud statement excludes GCC-Moderate)

### Endpoint Analytics — Advanced Analytics tier

- **Source:** [Advanced Analytics overview — Microsoft Intune](https://learn.microsoft.com/en-us/intune/advanced-analytics/).
- **Sovereign-cloud support:** GCC High and DoD only. GCC-Moderate not listed.
- **Disposition:** Inferred unavailable in GCC-Moderate.
- **Telemetry lost:** Boot/GP/desktop-load times, app reliability (`AppCrashCount`, hang rates, stability trends), stop-error restarts, battery health, work-from-anywhere readiness, device performance regressions, resource performance (`AverageProcessorUsage`, memory spikes — the "grey-ware" signal).
- **Base-tier note:** Whether base-tier Endpoint Analytics is available in GCC-Moderate is not explicitly addressed. Treat base-tier as available in principle but unverified.
- **Gap matrix rows:** `device-boot-performance`, `app-reliability-crashcount-hangrate`, `resource-performance-cpu-memory`, `stop-error-restarts`, `battery-health-wfa-readiness`, `device-performance-anomalies-regression`.

## Available with operational caveats

This section corrects analyses that incorrectly listed CQD and M365
Usage Analytics as unavailable.

### Teams Call Quality Dashboard (CQD)

- **Sources:** [Data and reports in CQD](https://learn.microsoft.com/en-us/microsoftteams/cqd-data-and-reports), [Turn on and use Call Quality Dashboard](https://learn.microsoft.com/en-us/microsoftteams/turning-on-and-using-call-quality-dashboard).
- **Status:** Available. Documentation does not exclude GCC-Moderate.
- **Operational constraint:** EUII (BSSID, public IP, subnet/building mapping) is typically purged after **28 days** — a forensic-retention constraint, not a feature-absence constraint.
- **Modernization note:** The legacy CQD portal has been deprecated; the GA pathway is QER v5.0 Power BI templates plus Real-Time Analytics (RTA) in the Teams admin center.
- **Gap matrix row:** `cqd-euii-long-term`.

### Microsoft 365 Usage Analytics

- **Source:** [Connect to GCC data with usage analytics](https://learn.microsoft.com/en-us/microsoft-365/admin/usage-analytics/connect-to-gcc-data-with-usage-analytics?view=o365-worldwide).
- **Status:** Available for GCC tenants via the Power BI connector. Marketplace template app is not available; agencies use the GCC-specific template manually.
- **Constraint:** Long-horizon historical pivoting (12+ months, joined to Entra attributes via Graph) is functionally limited.
- **Gap matrix row:** `m365-usage-analytics-historical-pivots`.

## Architecturally constrained (inferred blocked, no explicit documentation)

Five product areas where no Microsoft documentation explicitly addresses
GCC-Moderate availability, but the FedRAMP Moderate boundary
architecture (SI-4 / AU-2 / AU-3 / SC-7) blocks or degrades the
outbound telemetry their commercial-cloud features depend on.

### Entra ID — Identity Protection, sign-in analytics, cross-tenant collaboration

- **Telemetry required:** Per-sign-in evaluation data (device, location, client app, network, sign-in risk, session detail); raw sign-in logs; aggregated patterns (impossible travel, atypical client usage); Identity Protection risk detections (leaked credentials, atypical travel, anonymous IP, malware-linked IP, unfamiliar sign-in properties); user-risk and sign-in-risk evolution; B2B and Direct Connect events; cross-tenant access settings.
- **Constraining controls:** SI-4, AU-2, AU-3, SC-7.
- **Workarounds:** Graph API export of sign-in and audit logs into Sentinel / Log Analytics; unified audit log + KQL; custom risk models on local IP, location, device-ID, failure-pattern correlation.
- **Fidelity lost:** Microsoft's proprietary continuously-tuned ML risk scores; real-time cross-tenant correlation; vendor-supplied global threat intelligence.
- **Detection-gap order of magnitude:** Commercial ≈ minutes; GCC-Moderate ≈ hours to days.
- **Compliance impact:** BOD 25-01 core logging achievable; "rapid detection and investigation" intent harder. M-22-09 Identity pillar requires equivalent risk scoring for credible Advanced ZTMM claim.
- **Gap matrix rows:** `entra-identity-protection-realtime-risk`, `cross-tenant-access-telemetry`.

### Intune — compliance, app protection, WUfB reporting, EPM

- **Telemetry required:** Detailed configuration state, health attestation, encryption status, OS version, jailbreak/root detection; continuous compliance evaluation; app-launch and app-protection enforcement events; WUfB per-device update state, patch success/failure, deferral, safeguard holds, error codes, timing; EPM elevation requests, approvals, denials with process metadata (hash, path, publisher).
- **Constraining controls:** SI-4, AU-2, AU-3, SC-7.
- **Workarounds:** Graph API exports → Log Analytics / Sentinel; built-in Intune reports where present; custom Power BI over exported device/compliance/update data.
- **Fidelity lost:** Less granular and frequent telemetry; limited behavioral context; reduced cross-correlation with identity and data events.
- **Compliance impact:** BOD 25-01 met if device compliance and update events are logged centrally. ZTMM Devices and V&A push toward Initial-Advanced, not Optimal.
- **Gap matrix rows:** `app-protection-policy-violation-analytics`, `wufb-deployment-health-trends`, `epm-elevation-operational-analytics`.

### M365 core apps — Office diagnostic, Copilot/AI, sensitivity labels, DLP

- **Telemetry required:** Office "Optional" diagnostic data (UX telemetry, feature usage, performance, crashes, add-in behavior, document interaction at telemetry level); Copilot prompt-and-response metadata (structure and usage), interaction patterns, feedback signals; sensitivity-label application/removal events with locations and patterns; DLP policy match conditions, content fingerprints, user actions, override or justification metadata, device/location/app context.
- **Constraining controls:** SI-4, AU-2, AU-3.
- **Confirmed restriction:** GCC privacy settings default Office diagnostic data to **Required only**; Optional is suppressed.
- **Workarounds:** Purview audit logs and DLP alerts via Graph or Management Activity API; custom label-usage reports from SharePoint, OneDrive, Exchange metadata + UAL; server-side logs (SharePoint access, Exchange message trace) instead of client-side telemetry.
- **Fidelity lost:** Fine-grained Office client telemetry, Copilot usage patterns, behavioral DLP analytics (override, near-miss, behavioral trends).
- **Compliance impact:** BOD 25-01 met for centralized DLP and label-event logging. ZTMM Data + V&A typically Advanced at best.
- **Gap matrix rows:** `office-optional-diagnostic-data`, `copilot-ai-prompt-response-telemetry`, `sensitivity-label-usage-analytics`, `dlp-behavioral-richness`.

### Continuous Access Evaluation (CAE)

- **Telemetry required:** Token issuance, refresh, revocation events; session state changes; policy-relevant events (password changes, account disablement, device-compliance changes, location changes, high-risk detections); near-real-time event streams between Entra ID and resource services (Exchange, SharePoint, Teams).
- **Constraining controls:** SI-4, AU-2, AU-3, SC-7.
- **Disposition:** Inferred degraded. Basic CAE policy enforcement appears available with Entra licensing; sub-minute revocation fidelity may be throttled by boundary inspection or proxies. The `xms_cc` claim on issued tokens confirms whether the CAE path is at least negotiated.
- **Workarounds:** Short access-token lifetimes (60–90 minutes); frequent re-authentication and CA re-evaluation; SIEM-triggered Graph API revocation scripts.
- **Fidelity lost:** Sub-second revocation; higher user friction; slower containment of compromised sessions.
- **Compliance impact:** M-22-09 Identity pillar emphasizes continuous verification and rapid revocation — without full CAE, agencies must compensate with shorter token lifetimes and strong monitoring. ZTMM Identity + Automation & Orchestration difficult to push to Optimal.
- **Gap matrix row:** `cae-realtime-revocation-paths`.

### Windows Update for Business reporting

This area overlaps with Intune above but is separately load-bearing
under BOD 25-01's asset-visibility requirement. Outbound flow to
"Commercial Global Service" endpoints for WUfB telemetry is often
blocked by boundary firewalls; agencies fall back to local GPO-based
reporting or third-party inventory. Real-time fleet-wide
patch-compliance scoring is the load-bearing loss.

- **Gap matrix row:** `wufb-deployment-health-trends`.
