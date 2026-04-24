---
document_id: UIAO_120
title: "UIAO Zero-Trust Integration Layer"
version: "1.1"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-17"
boundary: "GCC-Moderate"
---

# UIAO Zero-Trust Integration Layer

## Positioning in the reconciled layer model (ADR-030 §2)

The Zero-Trust / SASE enforcement boundary is implemented at the
**Overlay Fabric** layer of the Tier A four-layer model. The
four Zero-Trust pillars below source their evidence from the
Authority Plane (identity, device, network, data) and their
policy decisions route through the Control Plane before landing
as enforcement actions at the Overlay Fabric.

| ZT pillar | Evidence source (Authority Plane) | Decision surface (Tier B plane) | Enforcement point (Overlay Fabric) |
|---|---|---|---|
| Identity | Entra ID (MFA, Conditional Access, risk) | Identity | Conditional Access adapter |
| Device | Endpoint management / Defender | Identity + Telemetry | Compliance-gated access |
| Network | Named locations, VPN / private access logs | Addressing + Telemetry | SDN/SD-WAN segmentation |
| Data | DLP policies, sharing settings, sensitivity labels | Policy + Governance | DLP enforcement adapter |

The Tier A four-layer framing is the architectural prose model;
the Tier B six-plane decomposition (Identity, Addressing,
Overlay, Telemetry, Management, Governance) is the Control-Plane
decision-surface granularity that UIAO acts on. Both describe
the same substrate behavior.

## Pillars

1. **Identity**
   - Evidence from:
     - Azure AD (MFA, Conditional Access)
   - Controls:
     - IA-2, AC-17

2. **Device**
   - Evidence from:
     - Endpoint management / Defender
   - Controls:
     - CM, SI families (future adapters)

3. **Network**
   - Evidence from:
     - Conditional Access locations
     - VPN / private access logs
   - Controls:
     - SC-7

4. **Data**
   - Evidence from:
     - DLP policies
     - Sharing settings
   - Controls:
     - SC-28, AC-21

## Integration Pattern
- Zero-trust systems → Evidence Collectors → IR → Controls → OSCAL
- Enforcement:
  - EPL policies call:
    - Conditional Access adapter
    - DLP policy adapter
