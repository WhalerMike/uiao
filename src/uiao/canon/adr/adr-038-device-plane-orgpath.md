---
id: ADR-038
title: "Device-Plane OrgPath Provisioning — Graph + ARM Dual-Transport Adapter"
status: accepted
date: 2026-04-20
deciders:
  - governance-steward
  - identity-engineer
  - device-management-steward
supersedes: []
related_adrs:
  - ADR-034
  - ADR-035
  - ADR-036
  - ADR-037
canon_refs:
  - MOD_A_OrgPath_Codebook
  - MOD_C_Attribute_Mapping_Table
  - UIAO_007_OrgTree_Modernization_AD_to_EntraID
---

# ADR-038: Device-Plane OrgPath Provisioning — Graph + ARM Dual-Transport Adapter

## Status

Accepted

## Context

The session notes that kicked off this effort identify the **device
plane** as the "critical extension" of the OrgTree model:

> *"Identity as Root Namespace (Core Concept #3) applies to devices, not
> just users. Entra ID device objects can carry extension attributes just
> like user objects. An OrgPath-encoded device (`extensionAttribute1 =
> ORG-IT-INF-NET`) enables: Intune configuration profile targeting via
> the same dynamic group rules already built for users, Conditional
> Access device compliance policies scoped by OrgPath, consistent,
> auditable policy inheritance that mirrors what GPO-over-OU previously
> provided."*

Phases 0–3 closed the user-plane loop: codebook → collector → dynamic
groups → AUs + scoped roles. None of it touches device objects.

ADR-034 already established the three-plane device model (Identity /
Management / Workload), and the existing
`adapters/modernization/active-directory/disposition.py` classifier
already computes which plane each AD computer lands on. What was missing
is a **write surface**: nothing in the codebase knew how to turn
``ComputerDisposition.orgpath_plane = "extensionAttribute1"`` into a
Microsoft Graph PATCH, or ``"ARM-tag"`` into an ARM tag write, or how to
reconcile the two against canonical OrgPath values.

Three concrete gaps this ADR closes:

1. **Two transports, one decision tree.** Entra devices live behind
   Microsoft Graph; Arc servers live behind Azure Resource Manager.
   They are governed by the same OrgPath codebook (MOD_A) but speak
   different APIs with different authentication. An adapter that only
   does one of the two leaves half of the fleet ungoverned.
2. **Phantom drift on devices.** Without a machine-readable plane
   registry, a device with `extensionAttribute1 = "ORG-GHOST"` looks the
   same to the drift engine as a device with no OrgPath at all. MOD_A
   drift categories (Format / Value / Phantom) need a device-plane
   analogue.
3. **Where write mechanics live.** The existing disposition classifier
   has `orgpath_plane` strings but no declarative mapping from that
   string to a concrete HTTP method + endpoint template. Putting that
   mapping in code risks silent divergence between classifier and
   adapter; putting it in canon means a single governed source.

## Decision

1. Publish `src/uiao/canon/data/orgpath/device-planes.yaml` — a
   registry of device OrgPath storage planes. Every entry declares
   ``transport`` (microsoft-graph | azure-resource-manager),
   ``http_method``, ``endpoint_template``, ``body_template``,
   ``read_endpoint_template``, ``read_value_path``, and the set of
   AD dispositions that land on that plane. Phase 4 ships two planes
   (``extensionAttribute1``, ``ARM-tag``); ``app-tag`` is reserved for
   Phase 5 (workload identity).
2. Ship a JSON Schema at
   `src/uiao/schemas/orgpath/device-planes.schema.json` that pins the
   enum of plane names and the enum of dispositions so no loose values
   can be introduced without a canon change.
3. Provide a loader at
   `src/uiao/modernization/orgtree/device_planes.py` that additionally
   enforces:
   - **Disposition uniqueness** — no disposition is claimed by two
     planes (a device lands on exactly one).
   - **Disposition coverage** — every known disposition is either
     claimed by a plane *or* listed under `skip_dispositions` (DC, EOL).
     A new disposition added to `disposition.py` will fail the loader
     until the registry is updated — catches governance gaps at CI.
   - **ARM tag regex alignment** — the ARM plane's OrgPath value regex
     must equal the MOD_A codebook regex (`^ORG(-[A-Z0-9]{2,6}){0,4}$`).
     Prevents silent drift between the two canon files.
4. Introduce modernization adapter
   `uiao.adapters.entra_device_orgpath.EntraDeviceOrgPathAdapter` with
   three verbs (`plan` / `apply` / `reconcile`) that mirror the Phase 2
   and Phase 3 adapters. Input is a list of
   `DeviceOrgPathTarget` dataclasses — one per computer — produced
   upstream by running the AD survey + disposition classifier +
   `derive_orgpath_from_dn`.
5. Seven-op plan vocabulary covering both planes plus explicit skips:
   - `device-ext-create`, `device-ext-update` — Graph, auto-applied.
   - `arc-tag-create`, `arc-tag-update` — ARM, auto-applied.
   - `device-phantom-orgpath`, `arc-phantom-orgpath` — **never**
     auto-applied (MOD_C §Phantom rule; governance review).
   - `skip-no-plane` — the device's disposition is DC/EOL/unresolvable;
     recorded for auditability but no write attempted.
6. **Write path is deliberately minimal.** The adapter ships
   `plan()` and `apply(dry_run=True)` fully wired and offline-testable.
   `apply(dry_run=False)` calls a subclass hook (`_execute`) that raises
   by default, because the two transports require **two distinct
   credentials** (Graph scope vs ARM scope). Operators pick the
   credential story that fits their tenant; we refuse to hide that
   choice behind a convenience default.

## Consequences

**Positive**

- The device plane finally has a governed write surface. The session
  notes' "critical extension" is now a concrete adapter, not a plan.
- Plane mapping is declarative canon, not Python. When a new
  disposition or plane is added, three places change in lock-step
  (disposition.py enum, device-planes.yaml, JSON Schema enum) and the
  loader catches any mismatch.
- Phantom device drift is first-class. A device with a format-invalid
  or codebook-absent OrgPath produces a `*-phantom-orgpath` operation
  that never auto-remediates — exactly matching the user-plane phantom
  handling from ADR-035.
- Plan is fully offline-testable. Contract fixture injects synthetic
  Entra + Arc state as dicts; no network needed to verify drift
  detection on the full six-op matrix (ext create/update/phantom × ARM
  create/update/phantom).
- Unblocks Phase 5 (Intune + Arc policy targeting). Policy assignments
  will use the same canonical OrgPath values this adapter writes.

**Negative / deferred**

- **Workload identity (`app-tag` plane).** Reserved for Phase 5. When
  MANAGED-IDENTITY-CANDIDATE servers complete rebuild, their resulting
  service principals / MIs need OrgPath on Entra application `tags[]`;
  that adds a new disposition and a third plane entry.
- **Write-side dual credentials.** `_execute` raises by design;
  operators subclass and wire Graph / ARM tokens per their tenant.
  A future follow-up (Phase 4.5) can ship a canonical dual-token
  executor once the preferred credential story stabilises.
- **Tag-key collisions on ARM.** The adapter writes `tags.OrgPath`; a
  tenant already using the `OrgPath` key for a non-UIAO purpose would
  experience silent overwrites. MOD_C §ARM tag conventions claim the
  key, but production rollouts should scan for the key before switching
  `dry_run=False`.
- **Scope read-side.** `plan()` consumes pre-fetched device + Arc
  state. A future Phase 4.5 will wire Graph + ARM readers so
  `reconcile()` fetches tenant state itself.

## Alternatives considered

- **One adapter per plane.** Rejected. The governance story is one
  (OrgPath on every device); splitting the adapter would mean two
  plans, two reports, and two drift surfaces for operators to
  correlate. The dual-plane design keeps the human-visible artefact
  singular.
- **Store the body templates in Python.** Rejected. Templates embed
  API contracts (Graph version, ARM api-version, `isMemberManagement`
  flags); changing Microsoft's API shape should be a governed canon
  PR, not a code PR.

## Related work

- ADR-034 — Three-plane device model (Identity / Management / Workload).
  This ADR is the user-plane-equivalent for devices.
- ADR-035 — MOD_A OrgPath codebook. Device OrgPaths validate against
  the same codebook and regex.
- ADR-037 — MOD_D delegation matrix. When device AUs arrive (Phase 6+),
  their scoping will follow the same pattern.
