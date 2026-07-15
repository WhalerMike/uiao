# `x_ssa_day2_ops` — ServiceNow Day-2 Operations scoped app

> Status: DRAFT importable skeleton · Surface: `inbox/` (not canon) · Tracks issue #1139
> Scope: **FedRAMP Moderate + Microsoft GCC Moderate** only. Date Code: 2026-07-12 15:00 ET

The importable scoped app for the day-2 **helpdesk / landing-zone / app-reg / telephony**
catalog — the common Entra / M365 / Azure operator tasks (`inbox/Federal_Compliance_Automation_Roadmap.md`
§3–§4). It generalizes the DDI ServiceNow app (`infoblox-ddi-book/servicenow-app/`) from
provisioning to day-2 operations, with the Vol VII coordination discipline: **ServiceNow
governs who/when/approval/evidence; Microsoft Graph actuates through the in-boundary MID Server.**

## What's here

| Path | Record / artifact | Role |
|---|---|---|
| [`script-includes/EntraHelpdeskClient.js`](./script-includes/EntraHelpdeskClient.js) | `sys_script_include` | MID-routed Graph client — JML, password/MFA reset, group/license, guest invite |
| [`script-includes/EntraHelpdeskGate.js`](./script-includes/EntraHelpdeskGate.js) | `sys_script_include` | Pre-flight safety (SoD/least-privilege) + post-action verify gate |
| [`flow/flow-blueprint.md`](./flow/flow-blueprint.md) | Flow Designer blueprint | The "Governed Day-2 Request" flow + access-review / leaver-completion flows |
| [`helpdesk-control-map.json`](./helpdesk-control-map.json) | app data (CI-checked) | Helpdesk catalog → (control, task type, approval, KSI, slot) — projection of `aan-compliance-spine.yml` |
| [`landingzone-control-map.json`](./landingzone-control-map.json) | app data | Lane D landing-zone front-door bindings (CM-2/3/8) |
| [`appreg-control-map.json`](./appreg-control-map.json) | app data | Lane E app-registration lifecycle bindings (AC-2/IA-5(2)/SC-17/AC-6) |
| [`telephony-control-map.json`](./telephony-control-map.json) | app data | §4 Teams telephony + SCuBA-drift bindings (CM-3/CM-6/AU-2) |
| [`saas-control-map.json`](./saas-control-map.json) | app data | Lane F SaaS integration governance bindings (Vol VII Book 06) |
| [`atf/README.md`](./atf/README.md) | ATF test spec | Happy-path + negative (self-approve, standing-privilege, unreconciled) via `test_mode` |
| [`update-set/README.md`](./update-set/README.md) | update set | How the app assembles into one importable XML |

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

## Status — promoted to Volume IX

This scaffold is now the data layer of **Volume IX — ServiceNow Day-2 Operations**
(registered in `aan-compliance-spine.yml` as `vol-9`):

- `Vol_IX_Book_00_FedAAN_Day2_Operations_Overview.qmd` — the day-2 coordination discipline
- `Vol_IX_Book_01_FedAAN_Helpdesk_ITSM_Catalog.qmd` — the ten catalog items this map binds
- `Vol_IX_Book_02_FedAAN_Landing_Zone_Front_Door.qmd` — Lane D
- `Vol_IX_Book_03_FedAAN_App_Registration_Governance.qmd` — Lane E (issue #1140)
- `Vol_IX_Book_04_FedAAN_Teams_Telephony_Catalog.qmd` — §4 (issue #1141)

## Remaining steps (issue #1139)

1. ~~Author the scoped-app records (Script Includes, Flows, ATF) mirroring the DDI app.~~ **Done** (this skeleton).
2. ~~Add per-lane control maps (landing-zone, app-reg, telephony).~~ **Done.**
3. Export the actual `sys_atf_test` XML and the assembled update-set XML from a sub-prod build.
4. ~~Wire the control-map CI check (regen-and-diff vs `aan-compliance-spine.yml`) into the book CI.~~ **Done** (`validate_day2_control_maps.py`, wired in `.pre-commit-config.yaml` and `.github/workflows/aan-authorities-drift.yml`).
5. Add catalog variable-set XMLs per item (mirroring the DDI app's `catalog/` variable sets).

## References

- `inbox/Federal_Compliance_Automation_Roadmap.md` (§3 Lane C, §5 crosswalk)
- `inbox/Application Aware Networking/Vol_VII_Book_05_FedAAN_ServiceNow_Compliance_App.qmd`
- `infoblox-ddi-book/servicenow-app/` (scoped-app exemplar)
- `inbox/Application Aware Networking/aan-compliance-spine.yml`
