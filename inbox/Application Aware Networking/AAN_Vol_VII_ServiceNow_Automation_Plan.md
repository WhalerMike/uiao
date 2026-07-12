# AAN Volume VII Plan — ServiceNow Automation for Federal Control Compliance

> Status: DRAFT for author review · Surface: `inbox/` (not canon)
> Scope: new volume in `inbox/Application Aware Networking/` book series
> Companion to: `AAN_Series_Build_Plan.md`, `AAN_Series_Expansion_Plan_Substrate_Accreditation.md`
> Date Code: 2026-07-12 15:00 ET

## 1. Objective

Add **Volume VII — ServiceNow Automation for Federal Control Compliance (M365 &
Azure)** to the Federal Application-Aware Networking series: the **coordination
layer** that turns M365 and Azure control state into tracked ServiceNow work,
machine-readable evidence, and authorization-package input.

The volume operationalizes a decision the series already locked: Expansion Plan
§16 names **ServiceNow Gov Cloud** the "Workflow / CMDB / evidence coordination"
hub, FedRAMP-authorized, whose CMDB **reconciles to** the authoritative IPAM/DDI
asset identity (CM-8 join key) and never replaces it. Volume VII is where that
one-line positioning becomes worked doctrine + a deployable artifact.

## 2. Where It Sits

Volumes I–IV establish architecture (*what and why*); Volume V is training;
Volume VI carries deployable IaC/detection/evidence artifacts. **Volume VII sits
one plane further out than Volume VI: it does not deploy a control, it *operates*
one** — routing drift to an owner, gating change (CM-3), and rolling posture up
into continuous monitoring (CA-7). It depends on Vol I (naming-plane join key)
and Vol VI (the artifacts whose state it coordinates); it feeds Vol IV Book 06
(Authorization Package) and Vol VI Book 07 (Evidence & ConMon Pipeline).

## 3. Book Lineup

| Book | Title | Focus | Spine id |
|---|---|---|---|
| VII-00 | Volume Overview | Coordination doctrine; ServiceNow coordinates, does not actuate | `book-vol7-intro` |
| VII-01 | CMDB Reconciliation & Asset Identity | M365/Azure inventory → CMDB, reconciled to IPAM/DDI (CM-8, CM-3) | `book-sn-cmdb` |
| VII-02 | M365 Federal Control Compliance Automation | SCuBA/CA/Purview drift → Change/Incident/attestation (CM-6, AC-2, CA-7) | `book-sn-m365` |
| VII-03 | Azure Federal Control Compliance Automation | Azure Policy / Defender / Update Manager → tasks (CM-6, RA-5, SI-2) | `book-sn-azure` |
| VII-04 | Control Attestation, Evidence & KSI | IRM/GRC tests → OSCAL/KSI → ATO package (CA-2, CA-5, CA-7) | `book-sn-attestation` |
| VII-05 | The ServiceNow Compliance App | Scoped app, connectors, Flows, control map, ATF, update set | `book-sn-app` |

## 4. Doctrine Guardrails (carried from the series)

1. **Coordination, not actuation.** Actuation stays platform-native (Graph, Azure
   Policy, Update Manager); ServiceNow governs owner / SLA / approval / evidence.
   (Management-Plane Coordination Doctrine, Vol 0 Book 00.)
2. **CMDB reconciles to the naming plane; it does not become the SSOT.** IPAM/DDI
   and HRIT are truth planes; the CMDB and GRC workflow are enforcement/coordination
   planes. A CMDB that drifts from IPAM/DDI is a reconciliation defect.
3. **FedRAMP Moderate + Microsoft GCC Moderate only (this task).** Boundary is M365
   GCC (Moderate) + Moderate-targeted Azure; Graph/ARM resolve to the commercial
   endpoints that serve GCC Moderate (ADR-033). ServiceNow referred to as
   *FedRAMP-authorized*; never cite High in body text (authoring-spec §2). **Other
   CSPs (AWS/OCI/VMware) and higher boundaries (GCC High, DoD) are explicit
   follow-ups, out of scope now** — the coordination loop is built so they reconcile
   into the same ServiceNow queues later without reworking the M365/Azure core.
4. **In-boundary by construction.** MID Server inside the ATO boundary; least-privilege
   connector identities (read + scoped/logged/approved write, never standing admin).
5. **Everything as code, checked against the SSOT.** The app's control map is
   machine-readable data, a projection of `aan-compliance-spine.yml`, CI-checked
   against it — the same regen-and-diff discipline as `render_authorities_table.py`.
6. **Mechanism, not product — with a named coordinator.** ServiceNow is named because
   the coordination role is itself a named product decision (§16); substitution is
   preserved where a workflow/GRC platform is interchangeable.

## 5. Spine Integration (done in this pass)

- `volumes:` gains `vol-7` with its six book ids.
- `books:` gains the six `book-vol7-intro` … `book-sn-app` registry entries.
- `closures:` gains 11 coordination-closure rows across the four content books
  (overview and app carry no closures, matching Vol overview/impl-artifact books).
- Authorities partials regenerated (`--emit-dir authorities`); drift gate green
  (`--check authorities`). Each content book pastes its generated table inline
  under "Authorities Closed Here" (matches the partial byte-for-byte).

## 6. Follow-Ups (out of this pass)

1. **House-style figures (ADR-093).** This draft is text-and-table-first; the
   volume map + per-book loop diagrams are authored as committed SVG and rasterized
   in the PPTX→DOCX sync pass (authoring-spec §4).
2. **`.pptx` briefing decks** per book with full speaker notes (authoring-spec §3),
   then PPTX→DOCX figure write-back.
3. **Executive Summary series map + `es-fig-01`** updated to show Volume VII, and
   the datecoded distribution kit rebuilt to include the new volume.
4. **Scoped-app records.** Book VII-05 specifies the app; the actual `x_ssa_fed_compliance`
   record skeleton (generalizing `infoblox-ddi-book/servicenow-app/`) is a separate
   build once the control map and connector scopes are confirmed per tenant.
5. **Other CSPs & higher boundaries.** AWS/OCI/VMware coordination and GCC High / DoD
   endpoints are deferred by author direction (2026-07-12). They reconcile into the
   same queues later; no rework of the M365/Azure core is required to add them.
