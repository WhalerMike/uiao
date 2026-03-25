# UIAO-Core

**Unified Identity-Addressing-Overlay Architecture**  
Modernizing federal systems with machine-readable Zero Trust and FedRAMP compliance automation.

---

## End-to-End Demo

![UIAO generate-all demo](assets/demo.svg)

> Run `uiao generate-all` to transform your YAML canon into OSCAL JSON, Markdown docs, DOCX, PPTX, and a CycloneDX SBOM in a single command.

---

## Modernization Atlas

![Unified Zero Trust Architecture & Automation](assets/images/modernization-atlas-unified-zero-trust-architecture-and-automation.png)

![Mission Success](assets/images/modernization-atlas-mission-success.png)

### Core Identity Lifecycle
![Joiner / Mover / Leaver - Identity Core](assets/images/uiao-joiner-mover-leaver-identity-core.png)

### Legacy vs Modernized State
![Legacy vs Modernized Comparison](assets/images/uiao-core-legacy-vs-modernized-comparison.png)

---

## Key Architecture Views

![Unified Architecture Flow](assets/images/uiao-core-unified-architecture-flow.png)

![Mission-to-Tech Mapping](assets/images/uiao-core-mission-to-tech-mapping.png)

![Regional Scaling Model](assets/images/uiao-core-regional-scaling-model.png)

![O-Pillar INR Fabric - US View](assets/images/uiao-o-pillar-inr-fabric-us-map.png)

![Visibility & Telemetry](assets/images/modernization-atlas-visibility-and-telemetry-eyes-and-ears.png)

![Actionable Intelligence Dashboard](assets/images/modernization-atlas-actionable-intelligence-dashboard.png)

---

## FedRAMP / OSCAL Tool Comparison

| Capability | **uiao-core** | Compliance Trestle | GoComply | GovReady-Q | GSA fedramp-automation | Paramify | Xacta |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| OSCAL SSP generation | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OSCAL POA&M generation | ✅ | ✅ | ⚠️ partial | ✅ | ✅ | ✅ | ✅ |
| OSCAL Component Definition | ✅ | ✅ | ✅ | ⚠️ partial | ✅ | ⚠️ partial | ⚠️ partial |
| **Single YAML canon → OSCAL + PPTX** | ✅ **unique** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Leadership briefings (PPTX) auto-sync** | ✅ **unique** | ❌ | ❌ | ❌ | ❌ | ⚠️ manual | ❌ |
| FedRAMP Rev 5 baseline | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Continuous monitoring / telemetry | ✅ | ⚠️ partial | ❌ | ⚠️ partial | ❌ | ⚠️ partial | ✅ |
| Open-source | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| Zero-Trust architecture codified | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ partial |

> **uiao-core's unique value:** A single YAML canon simultaneously renders machine-readable OSCAL compliance artifacts *and* synchronized executive/leadership briefings (PPTX), keeping security documentation and leadership communications always in sync — no other tool in this space does both.

---

## Features

- Single source of truth YAML canon → OSCAL artifacts
- Vendor-neutral abstraction layer
- Automated SSP, POA&M and leadership briefings
- FedRAMP Rev 5 ready

## Quick Start

```powershell
git clone https://github.com/WhalerMike/uiao-core.git
cd uiao-core
```

Made for federal Zero Trust and compliance modernization

---

## Enhanced SSP Output

The `--enhanced` flag injects rich, Jinja2-rendered control narratives from
`data/control-library/*.yml` directly into the generated OSCAL SSP.

### Generate a rich SSP with control-library narratives

```bash
uiao generate-ssp --enhanced
```

This command merges the canon YAML, `data/parameters.yml`, and every
`data/control-library/<CONTROL-ID>.yml` file to produce an OSCAL SSP
where each control's `by-component` statement carries a fully rendered
narrative.

### Example rendered narrative (AC-3 — Access Enforcement)

```
UIAO Inc. enforces access control decisions in accordance with NIST SP 800-53
Rev 5 AC-3 through a layered Role-Based Access Control (RBAC) model evaluated
by the PolicyEnforcementPoint at every access request.

**RBAC Token Enforcement**
The IdentityProvider issues cryptographically signed tokens (JWT/SAML
assertions) that carry role assertions scoped to specific resource namespaces.
Every service validates these tokens on each request ...

**Infrastructure-Layer Access Enforcement**
...

**Just-in-Time Privileged Elevation**
Elevation requests are time-bounded to [TBD] hours and automatically revoked
at expiry ...
```

> Template variables that have no matching entry in `data/parameters.yml`
> render as `[TBD]`, making gaps immediately visible in the output.

### Adding a new control narrative to the library

1. Create `data/control-library/<CONTROL-ID>.yml` following the gold-standard
   template (`data/control-library/AT-2.yml`).
2. Ensure the file includes:
   - `control_id`, `title`, `status: implemented`
   - `implemented_by:` — simple string list of component names
   - `evidence:` — list of audit artefact slugs
   - `parameters:` — list of `{id, description, value}` objects using
     `"{{ parameters['param-id'] }}"` syntax
   - `narrative: |` — prose with at least 4 **Bold Section Headers** and
     Jinja2 variables (`{{ organization.name }}`, `{{ parameters['...'] }}`)
   - `related_controls:` — list of related control IDs with `# Title` comments
3. Re-run `uiao generate-ssp --enhanced` — the new narrative is picked up
   automatically with no code changes required.
