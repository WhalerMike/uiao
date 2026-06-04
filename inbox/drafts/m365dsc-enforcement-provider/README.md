# M365 config-as-code enforcement provider — draft

Draft ADR proposing the incorporation of **Microsoft 365 config-as-code**
(Microsoft365DSC today; Graph Tenant Configuration Management APIs tomorrow) into
UIAO as a **governed enforcement provider** — the actuation counterpart to the
read adapters (`entra`/`intune`/`m365`) and the ScubaGear / Zero Trust Assessment
evidence producers.

- [`adr-m365-config-as-code-enforcement.DRAFT.md`](adr-m365-config-as-code-enforcement.DRAFT.md)
  — the draft ADR. Subordinate to ADR-092 (Active Governance); maps M365DSC's
  modes onto the L0–L4 actuation ladder; per-control-plane-slot decomposition;
  L0–L2 now, L3 gated behind the actuator-security design, L4 prohibited for
  high-blast classes.

**Status:** DRAFT — not promoted. To promote: assign the next free ADR number
against `main`, move to `src/uiao/canon/adr/`, set `publish_to_site: true`, and
seed the per-slot enforcement-adapter work (identity first).

**Why it matters:** closes the assess→reconcile loop — ZT/SCuBA findings (L1) →
remediation playbook (L2 advise) → config-as-code reconcile (L3 gated) — and
makes the active surface accreditable rung-by-rung.
