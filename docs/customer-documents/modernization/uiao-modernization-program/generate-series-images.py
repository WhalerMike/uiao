#!/usr/bin/env python3
"""One-shot image generator for the UIAO Modernization Program series.

Generates the figure images referenced in chapters 00..07 via Google's
Gemini API (Nano Banana image model). Saves PNGs to ./images/ with slugs
that match each chapter's markdown reference exactly.

Usage:
    # Windows PowerShell:
    $env:GEMINI_API_KEY = "<your-key>"
    cd docs\\customer-documents\\modernization\\uiao-modernization-program
    python generate-series-images.py

    # macOS / Linux / bash:
    export GEMINI_API_KEY="<your-key>"
    cd docs/customer-documents/modernization/uiao-modernization-program
    python generate-series-images.py

Options:
    --dry-run     Report what would be generated; no API calls.
    --force       Regenerate even if the PNG already exists.
    --only SLUG   Generate only the single image matching SLUG.

Dependencies:
    pip install google-genai

Idempotent: an existing PNG is skipped unless --force is passed.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

MODEL = "gemini-2.5-flash-image"

STYLE_HEADER = "Style: clean, federal, McKinsey-grade editorial infographic. Flat vector with subtle depth; neutral slate + federal navy (#1F3A5F) accents; soft teal (#1A9E8F) and amber (#D4A017) highlights; white background; no gradients. No people, no Microsoft or vendor logos. Widescreen 16:9 aspect ratio (1440×810 nominal). Small readable sans-serif text labels on elements; monospace for canon identifiers (UIAO_NNN, DRIFT-*, MOD_*, DM_*, OrgPath values like ORG-FIN-AP). Government-appropriate; no marketing gloss. Show the GCC-Moderate boundary explicitly when the figure depicts tenants, services, or telemetry crossing it. Scene: "

IMAGES: list[tuple[str, str, str]] = [
    (
        "00-01-six-control-planes-interaction-model",
        "Six Control Planes Interaction Model",
        "A visual showing the six control planes arranged in a hub-and-spoke model with the Identity plane at the center. The five remaining planes --- Network, Addressing, Telemetry & Location, Security & Compliance, and Management --- are positioned radially around Identity. Bidirectional arrows connect each peripheral plane to Identity and to its adjacent planes, illustrating cross-plane data flows and dependency relationships. Each plane is labeled with its name and a one-line role summary.",
    ),
    (
        "00-02-modernization-phase-progression",
        "Modernization Phase Progression",
        "A horizontal timeline or swim-lane diagram showing Phases 0 through 4 arranged left to right in sequential order. Each phase is represented as a distinct block or lane with its name, focus area, and key deliverables listed beneath. Directional arrows between phases indicate incremental progression and dependency. The visual emphasizes that each phase delivers standalone value while building toward the complete architecture. Phase boundaries are clearly delineated with milestone markers.",
    ),
    (
        "02-01-diagram-showing-orgpath-architecture-with-user-aus-on-the-le",
        "Diagram showing OrgPath architecture with user AUs on the left, device correlation flow in the",
        "Diagram showing OrgPath architecture with user AUs on the left, device correlation flow in the center via Graph API/PowerShell automation, and device AUs on the right, with arrows showing the user-to-device assignment logic and scoped RBAC boundaries. The diagram should illustrate: (1) User objects grouped in AUs by department/location, (2) PowerShell correlation script querying Graph API to resolve each user's registered devices, (3) Device objects assigned to corresponding AUs, (4) Scoped RBAC roles (Helpdesk Admin, Intune Admin) bounded to AU scope for both users and devices.*",
    ),
    (
        "02-02-flowchart-showing-gpo-to-intune-conversion-pipeline-gpo-expo",
        "Flowchart showing GPO-to-Intune conversion pipeline: GPO Export (XML via Get-GPOReport) \u2192 Group",
        "Flowchart showing GPO-to-Intune conversion pipeline: GPO Export (XML via Get-GPOReport) \u2192 Group Policy Analytics Import (Intune Admin Center) \u2192 Compatibility Analysis (Supported / Not Supported / Deprecated) \u2192 Settings Catalog Migration (for supported settings) \u2192 Proactive Remediation Script Development (for unsupported but scriptable settings) \u2192 Deprecation Documentation (for obsolete settings) \u2192 Intune Policy Deployment (to pilot groups) \u2192 Coexistence Testing (MDM Wins Over GP validation) \u2192 Production Rollout \u2192 GPO Decommission (unlink, disable, archive). Each stage includes a gate checkpoint and owner assignment.*",
    ),
    (
        "02-03-diagram-showing-the-uiao-drift-detection-and-remediation-wor",
        "Diagram showing the UIAO Drift Detection and Remediation Workflow: Detection Sources (UTCM via",
        "Diagram showing the UIAO Drift Detection and Remediation Workflow: Detection Sources (UTCM via Microsoft Graph, ScubaGear via PowerShell, Azure Policy via Arc, Custom PowerShell Scripts) feeding into the UIAO Drift Engine. The Drift Engine classifies drift severity (Critical / High / Medium / Low), assigns to the responsible owner via OrgPath lookup, starts the SLA timer, and triggers remediation (automated remediation for eligible drifts; manual remediation with owner notification for complex drifts). After remediation, the detection source re-validates resolution. Upon validation, the drift record is closed and a full provenance record is written to canon/. Escalation paths branch from the SLA timer when remediation thresholds are exceeded.*",
    ),
    (
        "02-04-diagram-2-identity-synchronization-architecture-dimensions-6",
        "Diagram 2: Identity Synchronization Architecture** **Dimensions:** 6",
        'Left Side --- "On-Premises Active Directory":** Two domain controller server icons labeled "DC-01" and "DC-02" with a shared cylinder icon labeled "AD Database". Below the DCs, show a simplified OU tree with three levels. A callout shows a sample user object with attributes: sAMAccountName, UPN, distinguishedName, extensionAttribute1 (OrgPath).\\ \\ **Center-Left --- "Sync Engines" (two parallel paths):** Path 1 (top, colored blue #2b5797 with label "LEGACY"): A single server icon labeled "Entra Connect Sync Server v2.5.x" with a smaller server behind it labeled "Staging Server (passive)". An arrow labeled "30-min sync cycle" points right. Path 2 (bottom, colored green #2e7d32 with label "STRATEGIC"): Three small agent icons labeled "Cloud Sync Agent 1", "Agent 2", "Agent 3" deployed across different network segments. Arrows labeled "Near real-time" point right. A cloud icon above them labeled "Config stored in Entra ID" with dashed lines connecting to each agent. A curved arrow labeled "Auto-failover" connects the agents.\\ \\ **Center-Right --- "Microsoft Entra ID":** A large cloud-shaped container holding icons for: Users, Groups, Devices, Administrative Units, App Registrations. A highlighted callout shows the OrgPath attribute (extensionAttribute1) on a user object with the value "EAST/IT/Security/Analysts" and arrows pointing to a dynamic group and an AU.\\ \\ **Right Side --- "Downstream Services":** Four service boxes arranged vertically: (1) "Microsoft Intune" with device and policy icons, (2) "Conditional Access" with a shield and gate icon, (3) "Azure Arc" with a server and arc icon, (4) "Entra ID Governance" with access review and entitlement icons. Arrows from Entra ID feed into each',
    ),
    (
        "02-05-diagram-6-gcc-moderate-network-visibility-architecture-dimen",
        "Diagram 6: GCC-Moderate Network Visibility Architecture** **Dimensions:** 6",
        'Left Side --- "User Locations":** Three location icons arranged vertically: (1) "HQ Office" with a building icon and two sub-icons: "Enterprise Agent" (server) and "Endpoint Agents on Managed Devices" (laptops). (2) "Regional Office" with a smaller building icon and an Enterprise Agent server. (3) "Remote Workers" with a home icon and Endpoint Agent laptop icons. Arrows from each location point right toward the center.\\ \\ **Center --- "Network Paths":** A cloud-shaped area labeled "Internet / ISP / WAN" showing network path lines from user locations traversing through ISP nodes (labeled with example ASNs) and internet exchange points. The paths converge toward the right side. ThousandEyes synthetic test probes are shown as small radar icons along the paths.\\ \\ **Right Side --- "GCC-Moderate M365 Boundary":** A large dashed-border rectangle labeled "GCC-Moderate Microsoft 365 Service Boundary" containing service endpoint icons: "Exchange Online" (envelope), "SharePoint Online" (document), "Microsoft Teams" (Teams logo), "Entra ID" (identity shield). The dashed border indicates the compliance boundary.\\ \\ **Top-Right --- "ThousandEyes for Government Platform":** A cloud icon labeled "ThousandEyes for Government (FedRAMP Moderate --- AWS GovCloud)" with arrows coming from all Enterprise Agents and Endpoint Agents. Inside, show: "Path Visualization", "Synthetic Test Results", "Real User Metrics", "Alert Engine".\\ \\ **Bottom-Right --- "SIEM Integration":** A box labeled "UIAO SIEM/SOAR Platform" with an arrow from ThousandEyes labeled "Webhook Alerts + API Data Feed". A second arrow from the M365 boundary labeled "Entra Audit Logs + Defender Alerts" enters the SIEM.\\ \\',
    ),
    (
        "02-06-diagram-7-modernization-wave-dependency-and-timeline-dimensi",
        "Diagram 7: Modernization Wave Dependency and Timeline** **Dimensions:** 6",
        'Layout:** The horizontal axis represents time in weeks (0 to approximately 60 weeks). The vertical axis lists Wave 0 through Wave 7, each on its own swim lane. Each wave is represented as a horizontal bar with its name and duration shown inside.\\ \\ **Wave Bars and Colors:**\\ - Wave 0 "Foundation" (blue #2b5797): Starts at week 0, spans 4--6 weeks.\\ - Wave 1 "Identity Parity" (blue #2b5797): Starts after Wave 0, spans 6--8 weeks. Arrow from Wave 0 end \u2192 Wave 1 start.\\ - Wave 2 "Policy Translation" (orange #cc7a00): Starts after Wave 1, spans 8--10 weeks. Arrow from Wave 1 end \u2192 Wave 2 start.\\ - Wave 3 "Pilot Device Migration" (green #2e7d32): Starts after Wave 2, spans 4--6 weeks. Arrow from Wave 2 end \u2192 Wave 3 start.\\ - Wave 4 "Server Arc Enrollment" (green #2e7d32): Starts after Wave 1 (parallel with Wave 2), spans 4--6 weeks. Arrow from Wave 1 end \u2192 Wave 4 start. Note: Wave 4 runs in parallel with Waves 2--3.\\ - Wave 5 "Broad Device Migration" (green #2e7d32): Starts after Wave 3, spans 16--24 weeks. Arrow from Wave 3 end \u2192 Wave 5 start.\\ - Wave 6 "SCuBA Operationalization" (purple #6b21a8): Starts after Wave 0, extends through Wave 5 as a long bar. Arrow from Wave 0 end \u2192 Wave 6 start. A milestone marker at the Wave 5 end point labeled "Full Operationalization".\\ - Wave 7 "Legacy Decommission" (dark gray #4a4a4a): Starts after Wave 5, spans 8--12 weeks. Arrow from Wave 5 end \u2192 Wave 7 start.\\ \\ **Dependency Arrows:** Solid black arrows show sequential dependencies. Dashed arrows show the Wave 4 parallel path from Wave 1. A shaded vertical line at the Wave 3/Wave 5 boundary is labeled "Pilot Gate --- AO Approval Required".\\ \\ **Legend:** Bottom of diagram. Blue = Identity Waves. Orange =',
    ),
    (
        "03-01-governance-os-five-layer-architecture",
        "Governance OS Five-Layer Architecture",
        'Dimensions: 7.5 \u00d7 5.0 inches A vertically stacked five-layer architecture diagram with distinct color bands. Bottom layer (Layer 1, dark blue #1F4E79) labeled "Canonical Baseline Store" with a repository icon showing OSCAL/YAML files. Layer 2 (teal #2E75B6) labeled "Telemetry Ingestion Plane" with five inbound arrows from the left labeled "M365 API," "ScubaGear JSON/CSV," "Defender XDR," "Sentinel Logs," and "Intune Compliance." Layer 3 (amber #ED7D31) labeled "Drift Detection Engine" with a comparison scale icon and labels "Expected State" vs. "Actual State." Layer 4 (green #548235) labeled "Remediation Orchestration Engine" with workflow arrows and an SLA timer icon. Layer 5 (purple #7030A0) labeled "Provenance and Audit Layer" with a chain-link icon. Connecting arrows flow upward between each layer. A vertical sidebar on the right side spans all five layers labeled "Governance OS API Surface" with bidirectional arrows into each layer. The background is white. Each layer box has rounded corners and a subtle drop shadow.',
    ),
    (
        "03-02-governance-os-core-data-model-entity-relationship-diagram",
        "Governance OS Core Data Model --- Entity Relationship Diagram",
        'Dimensions: 7.5 \u00d7 4.5 inches An entity-relationship diagram on a white background with five entity boxes arranged in a flow pattern. CanonicalBaseline (dark blue #1F4E79 header) at top-left listing key attributes: document_id, title, version, status, owner, hash_sha256. DriftEvent (orange #ED7D31 header) at center listing key attributes: event_id, baseline_ref, workload, severity, detected_at, delta_summary. RemediationWorkflow (green #548235 header) at center-right listing key attributes: workflow_id, drift_event_ref, owner, status, sla_status, resolved_at. ProvenanceRecord (purple #7030A0 header) at bottom-right listing key attributes: record_id, artifact_ref, action_type, actor, timestamp, causal_chain_ref. TelemetryPayload (gray #A5A5A5 header) at bottom-left listing key attributes: payload_id, source_adapter, workload, timestamp, ingestion_status, validation_errors. Relationships shown as labeled lines: CanonicalBaseline \u2500\u25001:M\u2500\u2500\u25b6 DriftEvent labeled "generates"; DriftEvent \u2500\u25001:1\u2500\u2500\u25b6 RemediationWorkflow labeled "triggers"; RemediationWorkflow \u2500\u25001:M\u2500\u2500\u25b6 ProvenanceRecord labeled "produces"; TelemetryPayload \u2500\u2500M:1\u2500\u2500\u25b6 DriftEvent labeled "feeds"; ProvenanceRecord \u2500\u2500dashed line\u2500\u2500\u25b6 CanonicalBaseline labeled "traces provenance." Each entity box has a header bar with entity name and a body listing 5--6 key attributes.',
    ),
    (
        "03-03-microsoft-security-and-compliance-stack-integration-map",
        "Microsoft Security and Compliance Stack Integration Map",
        'Dimensions: 7.5 \u00d7 5.5 inches A hub-and-spoke diagram with white background. The UIAO Governance OS is at the center as a large hexagonal hub with dark blue fill (#1F4E79) and white text. Six spokes radiate outward to integration targets, each with a distinct icon and color: Microsoft Sentinel (top, shield icon, blue #2E75B6, labeled "SIEM/SOAR"), MDE (upper-right, laptop icon, orange #ED7D31, labeled "Endpoint Detection"), MDI (right, person-with-shield icon, teal #00B0F0, labeled "Identity Threat Detection"), MDO (lower-right, envelope icon, red #FF0000, labeled "Email/Collaboration Protection"), Intune (lower-left, device-management icon, green #548235, labeled "Endpoint Compliance"), Azure Arc (left, bridge/arc icon, gray #595959, labeled "Hybrid Projection"). Each spoke has two arrows: solid arrow inward labeled "Telemetry" and dashed arrow outward labeled "Remediation Commands." A dashed rounded-rectangle boundary line encircles the five M365-aligned services (Sentinel, MDE, MDI, MDO, Intune) labeled "GCC-Moderate Boundary --- M365 SaaS." Azure Arc sits OUTSIDE this boundary with an annotation: "Telemetry Projection Only --- Outside GCC-Moderate Boundary." At the bottom, a bar labeled "Microsoft Graph Security API" spans the width, showing it as the unified API layer.',
    ),
    (
        "03-04-uiao-scuba-integration-flow",
        "UIAO SCuBA Integration Flow",
        'Dimensions: 7.5 \u00d7 4.0 inches A left-to-right data flow diagram on white background. Far left: a rounded rectangle labeled "CISA ScubaGear" (teal border #2E75B6) containing three step icons arranged vertically: "1. PowerShell \u2192 M365 APIs," "2. OPA/Rego Evaluation," "3. Report Generation (HTML/JSON/CSV)." An output arrow labeled "JSON / CSV / HTML" flows right into a rectangle labeled "UIAO ScubaGear Adapter" (orange border #ED7D31) with sub-label "Normalize & Validate." From the adapter, a solid arrow flows right into "UIAO Telemetry Ingestion Plane" (blue box #2E75B6). From the ingestion plane, an upward arrow leads to "Drift Detection Engine" (amber box #ED7D31), which has a reference arrow pointing up to a cylinder icon labeled "Canonical Baseline Store" (dark blue #1F4E79). Drift results flow right from the detection engine into "DriftEvent Queue" (small orange rectangle) and then into "Remediation Orchestration" (green box #548235). A horizontal bar at the bottom spans the entire width labeled "Provenance Layer" (purple #7030A0), with dashed downward arrows from every major component feeding into it. In the lower-right corner, a callout box (light gray background) lists target engagement channels: "cisagov/ScubaGear GitHub Discussions; FedRAMP CWGs (Rev5 & 20x); FedRAMP RFCs; FSCAC/CISA Direct Engagement."',
    ),
    (
        "03-05-drift-detection-engine-processing-flow",
        "Drift Detection Engine Processing Flow",
        'Dimensions: 7.5 \u00d7 4.0 inches A horizontal swim-lane diagram with three lanes on white background. TOP LANE labeled "Telemetry Sources" (light blue background #D6E4F0) contains five source icons in a row: "M365 Management Activity API" (document icon), "ScubaGear Adapter" (gear icon), "Microsoft Sentinel" (shield icon), "Defender XDR (Graph Security API)" (shield-with-check icon), and "Intune Graph API" (device icon). Each has a downward arrow into the middle lane. MIDDLE LANE labeled "Drift Detection Engine" (light amber background #FDE9D9) shows a left-to-right pipeline: "Ingest & Normalize" (rounded rectangle) \u2192 arrow \u2192 "Compare Against Baselines" (rounded rectangle, with a reference arrow pointing upward to a cylinder icon labeled "Canonical Baselines" floating above the lane boundary in dark blue #1F4E79) \u2192 arrow \u2192 "Classify Severity (P0--P4)" (rounded rectangle with severity color bands) \u2192 arrow \u2192 "Generate DriftEvent" (rounded rectangle). BOTTOM LANE labeled "Output Routing" (light green background #E2EFDA) shows DriftEvent records splitting into two paths: left path arrow to "Remediation Queue" (green box) and right path arrow to "Provenance Layer" (purple bar #7030A0).',
    ),
    (
        "03-06-remediation-workflow-state-machine",
        "Remediation Workflow State Machine",
        'Dimensions: 7.5 \u00d7 3.5 inches A state machine diagram on white background with five states as rounded rectangles: "DriftEvent Detected" (start state, yellow fill #FFC000 with black text, leftmost), "Open" (orange fill #ED7D31 with white text), "In-Progress" (blue fill #2E75B6 with white text), "Resolved" (green fill #548235 with white text, rightmost), "Escalated" (red fill #C00000 with white text, below In-Progress). Transition arrows with labels: A start arrow points into "DriftEvent Detected" from the left. DriftEvent Detected \u2192 Open (labeled "Auto-assign owner from baseline"). Open \u2192 In-Progress (labeled "Owner acknowledges"). In-Progress \u2192 Resolved (labeled "Remediation confirmed & validated"). In-Progress \u2192 Escalated (labeled "SLA breached or approval denied"). Escalated \u2192 In-Progress (labeled "Escalation resolved, new owner assigned"). A dashed arrow from every state feeds downward into a horizontal bar labeled "Provenance Record" (purple #7030A0) at the bottom of the diagram.',
    ),
    (
        "03-07-provenance-chain-structure",
        "Provenance Chain Structure",
        'Dimensions: 7.5 \u00d7 3.0 inches A horizontal chain diagram on white background showing four linked ProvenanceRecord blocks arranged left to right, connected by solid arrows with small lock icons on each arrow representing cryptographic linkage. Block 1 (dark blue border #1F4E79): "Baseline Published" --- fields shown: record_id: PR-001, action_type: PUBLISH, actor: Canon Steward, timestamp: 2026-04-01T09:00:00Z, hash: abc1\\...23. Block 2 (orange border #ED7D31): "Drift Detected" --- fields: record_id: PR-002, action_type: DETECT, hash_before: abc1\\...23, hash_after: def4\\...56, causal_ref: PR-001. Block 3 (green border #548235): "Remediation Executed" --- fields: record_id: PR-003, action_type: REMEDIATE, hash_before: def4\\...56, hash_after: ghi7\\...89, causal_ref: PR-002. Block 4 (purple border #7030A0): "Resolution Confirmed" --- fields: record_id: PR-004, action_type: RESOLVE, hash_before: ghi7\\...89, hash_after: jkl0\\...12, causal_ref: PR-003. Each block is a rounded rectangle with the title in a colored header bar and fields listed below in monospace font.',
    ),
    (
        "03-08-cross-plane-telemetry-ingestion-architecture",
        "Cross-Plane Telemetry Ingestion Architecture",
        'Dimensions: 7.5 \u00d7 5.0 inches A left-to-right flow diagram on white background. LEFT SIDE: Five governance planes shown as vertical colored swim lanes stacked top to bottom: Identity Plane (blue #2E75B6 background, containing "Entra ID" and "MDI" icons with labels), Endpoint Plane (orange #ED7D31 background, containing "MDE" and "Intune" icons), Data Plane (purple #7030A0 background, containing "Purview" icon), Collaboration Plane (green #548235 background, containing "SharePoint" and "Teams" icons), Email Plane (red #C00000 background, containing "Exchange Online" and "MDO" icons). CENTER: A column of eight "Telemetry Adapter" boxes (gray #A5A5A5 fill, labeled ADP-001 through ADP-008) receives arrows from each source system. Each adapter box shows the adapter ID and source name. RIGHT SIDE: All adapter outputs converge via arrows into a large "Telemetry Ingestion Bus" (dark blue #1F4E79 horizontal bar spanning the full height). From the bus, a main right-pointing arrow flows into the "Drift Detection Engine" (amber #ED7D31 box). A secondary downward arrow from the bus leads to "Raw Telemetry Archive" (cylinder icon, gray #A5A5A5) labeled "Audit Retention --- 7 Years."',
    ),
    (
        "03-09-continuous-ato-evidence-generation-pipeline",
        "Continuous ATO Evidence Generation Pipeline",
        'Dimensions: 7.5 \u00d7 4.0 inches A pipeline diagram flowing left to right on white background. LEFT SIDE: Four UIAO source boxes stacked vertically with spacing: "Canonical Baselines" (dark blue fill #1F4E79, white text), "Drift Events" (orange fill #ED7D31, white text), "Remediation Workflows" (green fill #548235, white text), "Provenance Records" (purple fill #7030A0, white text). Each has a right-pointing arrow flowing into a central processing block labeled "OSCAL Generator" (gray box #A5A5A5 with a gear icon inside). RIGHT SIDE: Four OSCAL output boxes stacked vertically: "OSCAL Component Definitions" (dark blue border #1F4E79), "OSCAL Assessment Results" (orange border #ED7D31), "OSCAL POA&M Items" (green border #548235), "OSCAL Assessment Plans" (purple border #7030A0). These four outputs flow via converging arrows into a final box at the far right labeled "FedRAMP Authorization Package" (dark blue fill #1F4E79, white text, bold, large). A curved feedback arrow from the Authorization Package returns leftward along the bottom to "Canonical Baselines" labeled "Continuous Validation Loop." Across the top of the diagram, a banner reads "GCC-Moderate Boundary --- M365 SaaS Services" (blue background #4472C4, white text).',
    ),
    (
        "04-01-steady-state-architecture-showing-the-six-governance-os-laye",
        "Steady-state architecture showing the six Governance OS layers (Signal, Baseline, Drift Engine",
        "Steady-state architecture showing the six Governance OS layers (Signal, Baseline, Drift Engine, Remediation, Provenance, Governance OS API) integrated with the UIAO core layers (Identity/Entra ID, Addressing/InfoBlox DDI, Overlay/Catalyst SD-WAN + NSX, Telemetry/Sentinel + Splunk). Phase 3 optimization zones highlighted: cATO evidence output from Provenance Layer, tuned Drift Engine with calibrated severity thresholds, matured Remediation Layer with maturity model stages, SLA enforcement from Telemetry Layer, Dashboard optimization from Governance OS API, and Adapter interfaces for legacy/external integration. Closed-loop arrows: Detect \u2192 Capture \u2192 Correlate \u2192 Remediate \u2192 Report. External mandate inputs: OMB M-22-09, CISA ZTMM v2.0, NIST 800-53r5, FedRAMP Rev 5. GCC-Moderate boundary clearly delineated around M365 SaaS services. *PlantUML source to be rendered by diagram toolchain.*",
    ),
    (
        "04-02-optimized-drift-detection-flow-showing-five-drift-engines-id",
        "Optimized drift detection flow showing five drift engines (Identity/Sentinel, Device/Intune",
        "Optimized drift detection flow showing five drift engines (Identity/Sentinel, Device/Intune, Server/Arc, Policy/Sentinel, Baseline/Governance OS API) feeding into a Drift Aggregation Engine. Aggregation engine applies Phase 3 tuned thresholds and false-positive suppression rules. Output routes: (1) Suppressed --- logged to provenance with suppression reason, (2) Confirmed Low --- routed to auto-remediation, (3) Confirmed Medium --- routed to notify+auto, (4) Confirmed High --- routed to escalation+manual. All outputs feed Provenance Layer. Feedback loop from remediation outcomes back to threshold tuning engine. Weekly reconciliation report generated from Governance OS API. *PlantUML source to be rendered by diagram toolchain.*",
    ),
    (
        "04-03-sla-enforcement-closed-loop-sequence-1-telemetry-sources-cqd",
        "SLA enforcement closed-loop sequence: (1) Telemetry sources (CQD, MINR, SD-WAN, Sentinel, Intune",
        "SLA enforcement closed-loop sequence: (1) Telemetry sources (CQD, MINR, SD-WAN, Sentinel, Intune, InfoBlox) emit metrics to Conversation Schema normalization. (2) SLA Evaluation Engine compares normalized metrics against SLA thresholds (P3-T-004). (3) Threshold breach triggers: auto-capture (Riverbed AppResponse), ServiceNow incident creation, ThousandEyes external validation. (4) Remediation executed per severity (overlay re-path, identity health check, failover). (5) Post-remediation verification confirms SLA restored. (6) Evidence artifacts attached to ServiceNow ticket and Governance OS provenance. (7) Power BI SLA Dashboard updated with breach/resolution data. Feedback loop from resolution outcomes to threshold calibration. *PlantUML source to be rendered by diagram toolchain.*",
    ),
    (
        "04-04-multi-tier-dashboard-architecture-showing-data-flow-from-sou",
        "Multi-tier dashboard architecture showing data flow from source systems (Sentinel, Defender",
        "Multi-tier dashboard architecture showing data flow from source systems (Sentinel, Defender, Intune, Entra ID, SD-WAN, CQD, MINR, InfoBlox, Riverbed, ThousandEyes, ServiceNow, Governance OS API) through a Data Aggregation Layer (Sentinel workspace, Log Analytics) into Power BI Service (GCC-Moderate). Five dashboard instances (DASH-001 through DASH-005) with audience-specific data filtering, RBAC access controls, and privacy controls (pseudonymization for CDM/CLAW and citizen data). CDM/CLAW export stream with pseudonymization filter to CISA. Feedback arrows from dashboards to SLA Enforcement Engine and Drift Detection Optimization Engine. *PlantUML source to be rendered by diagram toolchain.*",
    ),
    (
        "05-01-multi-agent-governance-topology",
        "Multi-Agent Governance Topology",
        "A PlantUML component diagram depicting the cooperative multi-agent governance topology. Three agent swim lanes (Canon Steward, Drift Detector, Remediation Orchestrator) are arranged horizontally. The SSOT Repository is rendered as a central cylindrical data store connecting all three agents. Adapter endpoints appear as interface nodes on the right edge feeding telemetry into the Drift Detector. Message envelopes (structured JSON arrows) flow between agents: violation events from Canon Steward to Remediation Orchestrator, drift findings from Drift Detector to Remediation Orchestrator, and remediation confirmations from Remediation Orchestrator back to the SSOT. A Human Approver icon sits above the Orchestrator with a gated escalation arrow. Color scheme: Canon Steward in blue, Drift Detector in amber, Remediation Orchestrator in green, SSOT in gray.",
    ),
    (
        "05-02-drift-intelligence-engine-data-flow",
        "Drift Intelligence Engine Data Flow",
        "A PlantUML activity diagram showing the Drift Intelligence Engine's three input streams (adapter telemetry, evidence ledger history, SSOT commit metrics) converging into the engine's processing core. Inside the core, three processing stages are shown sequentially: data normalization, change-point detection, and trajectory projection. Two output arrows emerge: one labeled 'Priority Scan Targets' flowing to the Drift Detector, and one labeled 'Autonomy Calibration Scores' flowing to the Remediation Orchestrator. Each processing stage is annotated with its deterministic algorithm name. Confidence intervals are shown as range bars on the output arrows.",
    ),
    (
        "05-03-ssot-artifact-paths-and-agent-interactions",
        "SSOT Artifact Paths and Agent Interactions",
        "A reference table with columns: Artifact Path, Artifact Type, Writing Agent, Reading Agent(s), Schema Reference, and Retention Policy. Rows cover: canon/drift-events/ (Drift Detector writes, Orchestrator reads), canon/violations/ (Canon Steward writes, Orchestrator reads), canon/remediations/ (Orchestrator writes, all agents read), canon/evidence/ (all agents write, auditors read), canon/predictions/ (Drift Intelligence Engine writes, Detector and Orchestrator read), and canon/approvals/ (Human approvers write, Orchestrator reads). Each row includes the JSON schema file reference and the retention period in days.",
    ),
    (
        "05-04-adapter-doctrine-streaming-mode-integration",
        "Adapter Doctrine --- Streaming Mode Integration",
        "A PlantUML sequence diagram showing the interaction between an external service, its UIAO adapter, and the Drift Detector agent. The sequence begins with a configuration change event emitted by the external service. The adapter receives the event, translates it into the canonical telemetry schema, and pushes it to the Drift Detector via the SSOT drift-events path. The Drift Detector acknowledges receipt, processes the event against the current desired state, and --- if a deviation is found --- writes a drift finding to the SSOT. A parallel lane shows the adapter's health interface emitting periodic heartbeat events. Annotations on each message indicate the schema version and timestamp format.",
    ),
    (
        "05-05-coordination-epoch-sequence",
        "Coordination Epoch Sequence",
        "A PlantUML timing diagram showing three consecutive coordination epochs. Within each epoch, three sequential phases are color-coded: Canon Steward validation (blue), Drift Detector reconciliation (amber), Remediation Orchestrator action (green). Between epochs, a quiescent gap is shown in gray. Annotations mark the SSOT commit points at each phase transition. A failure scenario is shown in the third epoch where the Drift Detector fails, the epoch is marked incomplete, and a retry arrow loops back to the epoch start.",
    ),
    (
        "05-06-predictive-model-output-schema",
        "Predictive Model Output Schema",
        "A schema reference table with columns: Field Name, Data Type, Required, Description, and Example Value. Rows cover: surface_id (string, required), predicted_drift_type (enum, required), confidence_interval (float range, required), evidence_citations (array of UIAO_NNN references, required), predicted_impact (object with control_family and severity, required), recommended_action (string, optional), predicted_time_to_drift (ISO 8601 duration, required), and model_version (semver string, required). Example values demonstrate realistic data.",
    ),
    (
        "05-07-autonomous-remediation-decision-flow",
        "Autonomous Remediation Decision Flow",
        "A PlantUML flowchart depicting the Remediation Orchestrator's decision process upon receiving a drift finding. The flow begins with drift finding intake, proceeds to authority envelope lookup (decision diamond: authorized? yes/no), then to severity check (decision diamond: within autonomous threshold? yes/no), then to confidence score check (decision diamond: above minimum confidence? yes/no). If all checks pass, the flow proceeds to dry-run simulation, outcome comparison (decision diamond: matches prediction? yes/no), and actual execution. If any check fails or the outcome diverges, the flow routes to human escalation with context packaging. Terminal nodes show evidence ledger commits at each stage. Color: green for autonomous path, red for escalation path.",
    ),
    (
        "05-08-human-in-the-loop-control-architecture",
        "Human-in-the-Loop Control Architecture",
        "A PlantUML component diagram showing the relationship between automated agent pipelines and human control interfaces. The three agents are shown as process boxes in the center. Above them, the Approval Gate is depicted as a modal dialog component with input arrows from the Remediation Orchestrator and output arrows (approve/reject/modify) back to the Orchestrator. To the right, the Override Console is shown as a management interface with control arrows to each agent (suspend, modify, force-epoch, inject). Below the agents, the Evidence Ledger is shown as a persistent store receiving audit records from both the Approval Gate and the Override Console. Human operator icons are connected to both the Approval Gate and Override Console.",
    ),
    (
        "05-09-provenance-header-schema",
        "Provenance Header Schema",
        "A schema reference table with columns: Field Name, Data Type, Required, Description, and Validation Rule. Rows cover: agent_id (string, required, must match registered agent manifest), source_inputs (array of SSOT artifact paths, required, each must exist in the repository), processing_logic_ref (string, required, must reference a versioned runbook or algorithm), output_artifact_path (string, required, must conform to SSOT path conventions), timestamp (ISO 8601, required, must be within the current epoch window), parent_provenance_ids (array of provenance header IDs, optional, links to causal predecessors), and confidence_score (float 0-1, optional, populated for prediction artifacts).",
    ),
    (
        "05-10-control-maturity-evolution-model",
        "Control Maturity Evolution Model",
        "A PlantUML state diagram showing the five control maturity levels as states arranged left to right: Documented, Detected, Alerted, Assisted, Autonomous. Transition arrows between each pair of adjacent states are labeled with the required criteria: detection rule registered, alerting pipeline configured, predictive model and runbook registered, authority envelope authorized. A human approval icon sits above each transition arrow. Below the states, a timeline shows example maturity advancement for three controls (AC-2, SC-7, AU-6) progressing through levels at different rates. A dashed line marks the 'Phase 4 Enablement Threshold' at Level 4, indicating where multi-agent capabilities become active.",
    ),
    (
        "05-11-runbook-conformance-checklist",
        "Runbook Conformance Checklist",
        "A validation checklist table with columns: Requirement ID (RB-001 through RB-012), Requirement Description, Verification Method, and Conformance Status (Placeholder for implementor). Rows cover: precondition block present, action block uses declarative transitions, postcondition block present, rollback block present, parameters typed and schema-validated, idempotency verified by regression test, version controlled in canon/runbooks/, provenance header conforming, PowerShell module specification adherence, dry-run capability implemented, execution cap awareness, and evidence commit on completion.",
    ),
    (
        "05-12-phased-rollout-schedule",
        "Phased Rollout Schedule",
        "A Gantt-style table with columns: Wave, Duration, Agent Mode, Drift Intelligence Mode, Human Gate, and Exit Criteria. Three rows for Waves 1--3 with the durations, modes, and criteria described in the rollout plan narrative. A fourth row shows 'Steady State' beginning at Week 17 with all agents in full operational mode and continuous maturity assessment active.",
    ),
    (
        "06-01-canon-consolidation-workflow",
        "Canon Consolidation Workflow",
        "A three-stage flowchart depicting the Canon consolidation process. Stage 1 shows CII generation via canon/ directory scan. Stage 2 shows schema validation against metadata-schema.json with pass/fail branching. Stage 3 shows the deprecation workflow with superseded_by pointer assignment. Arrows flow left to right. Each stage is labeled with its deterministic inputs and outputs.",
    ),
    (
        "06-02-artifact-consolidation-status-matrix",
        "Artifact Consolidation Status Matrix",
        "A table listing all canonical artifacts from Phases 1--4 with columns for Document ID, Title, Phase of Origin, Current Status, Schema Compliance (Pass/Fail), Consolidation Action (Promote/Deprecate/Remediate), and Owner. Populated from the CII scan results. **MISSING:** Actual artifact inventory pending canon/ directory scan.",
    ),
    (
        "06-03-canonical-artifact-lifecycle-state-machine",
        "Canonical Artifact Lifecycle State Machine",
        "A state machine diagram showing four states (DRAFT, ACTIVE, DEPRECATED, ARCHIVED) with labeled transitions between them. Transition labels include the triggering event (schema validation pass, supersession, retention expiration) and the enforcement mechanism (CI pipeline, Canon Steward review). Self-loops on ACTIVE indicate periodic re-validation cycles.",
    ),
    (
        "06-04-baseline-versioning-and-branching-model",
        "Baseline Versioning and Branching Model",
        "A Git-style branching diagram showing the main branch as the authoritative baseline, a governance branch created for a major revision, concurrent CI enforcement on both branches, and the governance merge request workflow. Annotations indicate where Canon Steward approval, owner sign-off, and deprecation of the prior version occur.",
    ),
    (
        "06-05-evidence-archival-tiered-storage-model",
        "Evidence Archival Tiered Storage Model",
        "A three-tier storage diagram showing hot, warm, and cold storage layers with labeled retention windows (0--1 year, 1--3 years, 3+ years). Arrows indicate the flow of attestation bundles from active governance into archival tiers, with retrieval paths shown as reverse arrows. Each tier is annotated with its access latency and governance query capability.",
    ),
    (
        "06-06-evidence-retention-schedule",
        "Evidence Retention Schedule",
        "A table defining retention periods for each evidence category (assessment artifacts, drift detection logs, remediation records, SLA compliance reports, attestation packages, agent governance logs). Columns include Evidence Category, Retention Period, Storage Tier, Retrieval SLA, and Governing Policy Reference. **MISSING:** Specific retention periods pending agency policy confirmation.",
    ),
    (
        "06-07-extensibility-interface-architecture",
        "Extensibility Interface Architecture",
        "A layered architecture diagram showing the three extensibility layers (service, compliance, agent) stacked vertically. Each layer shows the registration workflow, validation gates, and CII integration point. Arrows from external sources (new services, new compliance regimes, new agents) enter through adapter contracts on the left and flow through validation into the canonical corpus on the right.",
    ),
    (
        "06-08-canonical-baseline-lifecycle-detail",
        "Canonical Baseline Lifecycle Detail",
        "A detailed lifecycle diagram expanding on P5_DIA_002, focused specifically on baselines. Shows DRAFT to ACTIVE to DEPRECATED to ARCHIVED with sub-states within ACTIVE (under monitoring, under remediation, under re-validation). Includes callouts for CI pipeline enforcement points, drift detection agent interactions, and SLA-governed remediation windows.",
    ),
    (
        "06-09-evidence-retrieval-interface-specification",
        "Evidence Retrieval Interface Specification",
        "A table defining the retrieval API endpoints, query parameters, response formats, access control requirements, and logging obligations. Columns include Endpoint, Method, Parameters, Response Format, Access Control, and Audit Logging. **MISSING:** Specific API endpoint paths pending Canonical API Specification alignment.",
    ),
    (
        "06-10-governance-lifecycle-management-feedback-loop",
        "Governance Lifecycle Management Feedback Loop",
        'A circular feedback loop diagram showing Review to Adaptation to Re-validation to Review. Each node is expanded to show its sub-activities (e.g., Review includes schema compliance rates, drift effectiveness, SLA adherence). Arrows between nodes are labeled with triggering conditions and outputs. A central label reads "Recursive Governance."',
    ),
    (
        "06-11-governance-branching-and-merge-workflow",
        "Governance Branching and Merge Workflow",
        "A Git-style branching diagram showing main as the authoritative branch, two concurrent governance branches (governance/UIAO_040-v2 and governance/UIAO_050-v2), CI enforcement pipelines running on each branch, and the governance merge request workflow including Canon Steward approval gates. Conflict resolution is shown as a mediation step when both branches touch shared dependents.",
    ),
    (
        "06-12-assessor-interface-capability-matrix",
        "Assessor Interface Capability Matrix",
        "A table listing each assessor interface capability (Baseline Query, Evidence Retrieval, Governance Posture Dashboard, Audit Trail Access) with columns for Capability, Access Level, Scope Restrictions, Authentication Method, and Logging Requirements. **MISSING:** Specific authentication method pending security architecture review.",
    ),
    (
        "06-13-continuous-ato-operational-cadence-schedule",
        "Continuous ATO Operational Cadence Schedule",
        "A table defining each cadence layer (Real-time, Daily, Monthly, Quarterly) with columns for Layer, Activities, Responsible Party, Inputs, Outputs, SLA/Deadline, and Escalation Path. Each row is populated with the specific operational activities described in this section.",
    ),
    (
        "06-14-four-layer-operational-cadence-architecture",
        "Four-Layer Operational Cadence Architecture",
        'A concentric ring diagram with four layers radiating outward from a center labeled "Continuous ATO." The innermost ring is Real-time (drift detection), the next is Daily (health checks), then Monthly (governance reviews), and the outermost is Quarterly (assessment readiness). Each ring is annotated with key activities and responsible parties.',
    ),
    (
        "06-15-migration-stage-dependency-matrix",
        "Migration Stage Dependency Matrix",
        "A table listing each migration stage (1--5) with columns for Stage, Name, Entry Criteria, Runbook Reference, Exit Criteria, Rollback Procedure, and Estimated Duration. Each row is populated with the specific details from this section. **MISSING:** Estimated durations pending operational capacity assessment.",
    ),
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--only", default="")
    args = p.parse_args()

    out_dir = Path(__file__).parent / "images"
    out_dir.mkdir(parents=True, exist_ok=True)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not args.dry_run and not api_key:
        print("ERROR: GEMINI_API_KEY not set", file=sys.stderr)
        return 2

    if not args.dry_run:
        try:
            from google import genai  # type: ignore
        except ImportError:
            print("ERROR: pip install google-genai", file=sys.stderr)
            return 3
        client = genai.Client(api_key=api_key)

    targets = IMAGES if not args.only else [t for t in IMAGES if t[0] == args.only]
    if not targets:
        print(f"No images match --only {args.only!r}", file=sys.stderr)
        return 1

    for slug, _caption, prompt in targets:
        out = out_dir / f"{slug}.png"
        if out.exists() and not args.force:
            print(f"SKIP  {slug}.png (exists)")
            continue
        full_prompt = STYLE_HEADER + prompt
        if args.dry_run:
            print(f"DRY   {slug}.png  ({len(full_prompt)} chars)")
            continue
        print(f"GEN   {slug}.png ...")
        resp = client.models.generate_content(
            model=MODEL,
            contents=[full_prompt],
        )
        for part in resp.candidates[0].content.parts:
            if part.inline_data and part.inline_data.data:
                out.write_bytes(part.inline_data.data)
                print(f"OK    {slug}.png")
                break
        else:
            print(f"WARN  {slug}.png — no image data returned", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
