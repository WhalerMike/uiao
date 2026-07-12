# ServiceNow Day-2 Operations — Helpdesk / ITSM Catalog (Lane C scaffold)

> Status: DRAFT scaffold · Surface: `inbox/` (not canon) · Tracks issue #1139
> Scope: **FedRAMP Moderate + Microsoft GCC Moderate** only. Date Code: 2026-07-12 15:00 ET

This is the starting scaffold for the day-2 **helpdesk / ITSM catalog** — the common
Entra / M365 / Azure operator tasks — from `inbox/Federal_Compliance_Automation_Roadmap.md`
(§3, Lane C). It reuses the Vol VII coordination discipline: **ServiceNow governs
who/when/approval/evidence; Microsoft Graph actuates through the in-boundary MID Server.**

## What's here

| File | Role |
|---|---|
| [`helpdesk-control-map.json`](./helpdesk-control-map.json) | The machine-readable catalog → (control, task type, approval, KSI, slot) binding. A projection of `aan-compliance-spine.yml`, meant to be CI-checked against it (same regen-and-diff pattern as `render_authorities_table.py`). |

## The pattern (inherited from Vol VII Book 05)

Every catalog item is a governed request, not a portal click:

1. **Request** — typed catalog item against the reconciled identity CI.
2. **Approve** — the gate the control requires (manager, identity, security approver — see the map).
3. **Actuate** — Microsoft Graph **through the in-boundary MID Server**; **never standing
   tenant admin** (scoped, logged, individually-approved write only).
4. **Evidence** — every action a change/approval record (CM-3 / AU-2), reconciled to the
   IPAM/DDI-keyed CMDB (CM-8), feeding Vol VII Book 04 attestation.

## Catalog items (v0)

Ten items across the joiner/mover/leaver, credential, and access-request families —
each mapped to its NIST control and KSI in `helpdesk-control-map.json`. The
Conditional-Access exception item **reuses the Vol VII Book 02 pattern** (mandatory
break-glass exclusion + expiry + access review) rather than re-inventing it.

## Next steps (issue #1139)

1. Promote this scaffold into a full **Volume IX — ServiceNow Day-2 Operations** book
   (Lanes C helpdesk, D landing-zone front door, E app-registration governance, plus the
   §4 telephony catalog), registered in the compliance spine as `vol-9`.
2. Author the scoped-app records (Flows + catalog items + ATF) mirroring
   `infoblox-ddi-book/servicenow-app/`, extended for the helpdesk families.
3. Wire the control-map CI check so the catalog cannot drift from the spine.

## References

- `inbox/Federal_Compliance_Automation_Roadmap.md` (§3 Lane C, §5 crosswalk)
- `inbox/Application Aware Networking/Vol_VII_Book_05_FedAAN_ServiceNow_Compliance_App.qmd`
- `infoblox-ddi-book/servicenow-app/` (scoped-app exemplar)
- `inbox/Application Aware Networking/aan-compliance-spine.yml`
