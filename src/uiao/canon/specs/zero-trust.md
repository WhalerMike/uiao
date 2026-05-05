---
document_id: UIAO_120
title: "UIAO Zero-Trust Integration Layer"
version: "1.2"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-05-05"
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

## Customer-Identity Surface (UIAO_120 v1.2)

The four pillars above describe Zero Trust over the **workforce-identity
surface** — federal employees and contractors authenticated via PIV /
Entra. Per ADR-055, UIAO recognizes a peer **customer-identity surface**
covering citizens, businesses, applicants, and beneficiaries who interact
with federal agencies mission-side.

The Identity pillar takes a Customer Identity Record (CIR) — defined in
UIAO_141 §2 with six required bindings — as a first-class evidence input
alongside the workforce inputs above. The CIR's **IAL / AAL / FAL**
(NIST SP 800-63) values are first-class evaluation inputs to Zero-Trust
decision envelopes; cached attributes drift-checked against their
authority of record per UIAO_141 §7.

| ZT pillar | Customer-surface evidence source | Decision surface | Enforcement point |
|---|---|---|---|
| Identity | Login.gov / ID.me FAL-2 assertion + authority-of-record attributes (SSA / IRS / USCIS / etc.) | Identity | Citizen-portal SAML/OIDC enforcement; reciprocity entitlement gate |
| Device | Customer browser/device posture (where in scope) | Telemetry | Step-up MFA; device attestation |
| Network | Citizen access path (IP geolocation, VPN, anomalous origin) | Addressing + Telemetry | WAF / API gateway controls |
| Data | Per-attribute disclosure scope (entitlement-bound) | Policy + Governance | Reciprocity entitlement enforcement; attribute-level redaction |

The same `EPL` policy language and adapter framework cover both surfaces;
the surfaces differ in their identity primitives (Application Identity
vs. Customer Identity Record) and their authority pattern (workforce =
PIV/Entra; customer = federation issuer + authority of record).
