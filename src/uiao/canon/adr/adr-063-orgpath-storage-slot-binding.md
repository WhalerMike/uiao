---
id: ADR-063
title: "OrgPath Storage Slot — extensionAttribute1 Binding"
status: accepted
date: 2026-05-11
deciders:
  - governance-steward
  - identity-engineer
supersedes: []
related_adrs:
  - ADR-034
  - ADR-035
  - ADR-038
  - ADR-062
canon_refs:
  - UIAO_151_OrgPath_Codebook
  - UIAO_158_OrgPath_JSON_Schema
  - UIAO_163_Drift_Detection_Engine_Specification
---

# ADR-063: OrgPath Storage Slot — extensionAttribute1 Binding

## Status

Accepted

## Context

The OrgPath canon (UIAO_151) asserts in prose that the per-principal
OrgPath value is stored in Microsoft Entra ID's `extensionAttribute1`
on the user, device, and (where applicable) service-principal objects;
the Azure resource plane uses an ARM tag named `OrgPath`. Three
downstream ADRs already rely on this binding:

- ADR-034 (three-plane device model) declares
  `"OrgPath is written to extensionAttribute1"` for the client plane.
- ADR-035 (codebook binding) treats `extensionAttribute1` as the
  authoritative read-back target for `classify_identity_drift`.
- ADR-038 (device-plane OrgPath) hard-codes
  `ComputerDisposition.orgpath_plane = "extensionAttribute1"`.

The storage *slot* itself has never been ratified by its own ADR. The
binding is asserted in UIAO_151 line 44 and quietly assumed everywhere
else. Three concrete problems result:

1. **No documented rebind procedure.** Several tenants entering the
   modernization pipeline already use `extensionAttribute1` for an
   inherited purpose (most commonly HR cost-center sync from an
   on-prem identity manager). Operators have no canonical guidance on
   whether to migrate the existing value out, claim a different
   `extensionAttribute2..15` slot, or block the modernization until
   the prior tenant decision can be unwound. The default behavior
   today is silent overwrite, which destroys the prior tenant
   investment.

2. **No rationale on file for the slot choice.** Reviewers ask why
   `extensionAttribute1` specifically rather than `extensionAttribute2..15`,
   or a directory extension schema (`extension_<appId>_OrgPath`), or
   the `employeeOrgData`/`employeeHireDate` block, or
   `onPremisesExtensionAttribute1`. Without a documented rationale
   the binding is vulnerable to drift the next time a tenant asks for
   an exception.

3. **No drift class for slot-misalignment.** When a tenant's
   `extensionAttribute1` carries something other than an OrgPath
   (e.g., the inherited HR cost-center value), the drift engine
   classifies it as **Schema Drift** (regex fail) — which is
   technically true but operationally misleading: the value isn't
   malformed governance data, it is non-governance data living in the
   slot the canon claims. Operators want this distinguished so the
   remediation is "negotiate slot ownership," not "fix the value."

This ADR ratifies the binding, documents the rationale, defines a
rebind procedure for tenants where the slot is already occupied, and
opens a follow-up slot for a tighter drift sub-class.

## Decision

1. **Canonical slot binding.** The OrgPath value is stored in the
   following per-object-type slots, and these are the *only* canonical
   storage locations under M365 GCC-Moderate scope:

   | Principal | Storage |
   |-----------|---------|
   | User | `user.extensionAttribute1` |
   | Device (Entra-joined) | `device.extensionAttribute1` |
   | Service Principal (in-scope) | `servicePrincipal.extensionAttribute1` |
   | Azure resource | ARM tag named `OrgPath` |

2. **Why `extensionAttribute1` specifically.** The choice is recorded
   as canonical and not subject to per-tenant override:

   - **Tenant-universal.** `extensionAttribute1..15` exist on every
     Entra tenant out of the box (the `onPremisesExtensionAttributes`
     surface for hybrid and the writable `extensionAttribute1..15`
     surface for cloud-only). No tenant configuration is required
     before the slot can be claimed.
   - **Single-value, string-typed.** OrgPath is a single canonical
     string per principal; the `extensionAttribute*` slots match that
     shape exactly. Multi-value attributes (e.g., `proxyAddresses`)
     would force an ordering decision that the canon does not
     specify.
   - **First slot maximizes operator legibility.** Tenants
     consistently reserve the lowest-numbered extension attribute for
     "the most important governance field." Claiming
     `extensionAttribute1` matches Microsoft's own documentation
     convention and the implicit expectation operators bring from
     other directories.
   - **Not a directory extension schema.** A custom directory
     extension (`extension_<appId>_OrgPath`) would scope the attribute
     to a single application registration and complicate cross-tenant
     portability — out-of-scope per UIAO_171 Tenant Agnosticism.
   - **Not `employeeOrgData` or `employeeHireDate`.** These are
     authoritatively written by HR-driven inbound provisioning
     (UIAO_136 Spec 2) and cannot be safely overloaded with
     governance values without provoking provisioning-loop drift.
   - **Not `onPremisesExtensionAttribute1..15`.** Those are
     replicated *from* on-prem AD via Entra Connect and are
     read-only in the cloud — incompatible with cloud-only tenants
     and with the canon's HR-to-Entra-direct provisioning path.

3. **Rebind procedure for occupied tenants.** When the assessment
   phase (UIAO_156) discovers a non-empty, non-OrgPath value already
   present in `extensionAttribute1` for a non-trivial population of
   users (defined: ≥1% of in-scope users), the modernization program
   MUST follow this sequence before any OrgPath write occurs:

   1. Snapshot the current `extensionAttribute1` values to the
      Evidence Fabric with a `DRIFT-PROVENANCE` annotation. This
      preserves the prior-tenant investment for audit.
   2. Identify the inherited use (typical: cost-center sync, location
      code, mailbox-region tag). Document the prior owner in the
      governance steward log.
   3. Negotiate a target relocation slot — typically
      `extensionAttribute2` (cost-center) or
      `extensionAttribute3` (location) — and update the *upstream*
      provisioning configuration (HR adapter, mail-routing rule,
      etc.) to write the new slot.
   4. Run the upstream relocation in dry-run, verify population
      parity, then cut over. The cut-over commit lands in the same
      governance PR as the OrgPath-write enablement.
   5. Only after the relocation is verified do the OrgPath-write
      operations against `extensionAttribute1` proceed. The drift
      engine treats every write during the cutover window as a
      `DRIFT-PROVENANCE` event and records the source.

   Trivial occupancy (<1% of users, or only departed/tombstoned
   accounts) is handled by direct overwrite with a
   `DRIFT-PROVENANCE` annotation per write; no relocation is
   required.

4. **No tenant override of slot.** The slot is *not* a
   per-tenant-configurable knob. A tenant that cannot vacate
   `extensionAttribute1` cannot enter the modernization pipeline;
   that decision sits with the governance steward, not the deploying
   operator. Attempting to retarget the slot in code (e.g., by
   editing `orgpath_plane` in a `ComputerDisposition`) is a canon
   violation and fails CI under UIAO_172.

5. **New drift sub-class (deferred).** A future ADR will introduce
   `DRIFT-SCHEMA::slot-occupied` distinguishing "the value at
   `extensionAttribute1` is a well-formed but non-OrgPath string"
   from generic Schema Drift (regex fail). Until that ADR lands, the
   drift engine continues to classify these as Schema Drift and the
   remediation playbook (UIAO_167) routes them via the rebind
   procedure above.

## Consequences

**Positive**

- The binding now has a single ratified source; ADR-034, ADR-035, and
  ADR-038 no longer rest on prose assertion in UIAO_151.
- Operators have a documented procedure for the most common
  pre-modernization slot conflict, ending the
  "what do we do with the existing values?" stall in assessment.
- Audit-relevant prior-tenant data is preserved by the Evidence
  Fabric snapshot step rather than destroyed by silent overwrite.
- Justification for not choosing alternative slots is recorded, so
  the binding survives reviewer challenge without re-litigation.

**Negative / deferred**

- The 1%-of-users threshold is heuristic, not measured against
  real-world distributions yet. Field experience may move it.
- `DRIFT-SCHEMA::slot-occupied` is a follow-up commitment; without
  it, slot-occupancy events show up under generic Schema Drift and
  require the operator to read the `reason` field to triage.
- Tenants that *cannot* vacate `extensionAttribute1` (e.g., a
  vendor-managed sync writes it and the vendor refuses to retarget)
  are blocked from the modernization pipeline by design. This is
  intentional but operationally severe; an exception path may be
  warranted in a future ADR if the population is non-trivial.
- Service-principal OrgPath is declared in-scope here but the
  enforcement pipeline does not yet consume it; only users and
  devices are read by `classify_identity_drift` as of this writing.

## Related work

- ADR-034 introduced the three-plane device model; this ADR
  retroactively ratifies the slot it assumed.
- ADR-035 bound the codebook to executable canon; this ADR is the
  storage-side counterpart.
- ADR-038 wired the device plane to `extensionAttribute1`; this ADR
  generalizes that binding across all principal types.
- ADR-062 expanded OrgPath depth from 4 to 8 segments; that change
  did not touch the slot binding, but every depth-8 example written
  to a tenant still lands here.
