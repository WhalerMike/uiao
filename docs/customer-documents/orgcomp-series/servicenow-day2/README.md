# `x_fed_day2_ops` — ServiceNow Day-2 Operations scoped app

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
| [`helpdesk-control-map.json`](./helpdesk-control-map.json) | app data (CI-checked) | Helpdesk catalog → (control, task type, approval, KSI, slot) — projection of `orgcomp-compliance-spine.yml` |
| [`landingzone-control-map.json`](./landingzone-control-map.json) | app data | Lane D landing-zone front-door bindings (CM-2/3/8) |
| [`appreg-control-map.json`](./appreg-control-map.json) | app data | Lane E app-registration lifecycle bindings (AC-2/IA-5(2)/SC-17/AC-6) |
| [`telephony-control-map.json`](./telephony-control-map.json) | app data | §4 Teams telephony + SCuBA-drift bindings (CM-3/CM-6/AU-2) |
| [`saas-control-map.json`](./saas-control-map.json) | app data | Lane F SaaS integration governance bindings (Vol IX Book 05) |
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

## Closure provenance — the closure rules (doctrine: Vol 0 Book 00)

Every lane's task closure enforces the **Closure Provenance Doctrine** — no
closure counts unless it carries its proof — and every task travels the full
**MACD-R lifecycle** (Vol 0 Book 00): SSOT-originated → authoritatively
authorized → least-privilege executed → provenance-closed → evidence-emitted.
The upstream clauses, in scoped-app terms:

- **Work originates with the SSOT — the class SSOT.** Catalog tasks are
  created from divergence — drift detection, joiner/mover/leaver events
  from the HR system of record, control gaps against the compliance spine.
  A direct-to-catalog request resolves against the SSOT record **of the
  object's class** (the Vol 0 Book 00 SSOT Registry: HR record for a
  person, non-human identity registry for a service account or app
  registration, IPAM/DDI for a name or address, the IaC repo for declared
  infrastructure) or the form does not validate — there is nothing
  authoritative to verify the closure against. A non-human target whose
  registry record is missing, or whose human owner no longer resolves, is
  an **orphan**: the item gets an orphan finding, not a fulfilled request.
- **The authorization is authoritative.** Approvals resolve from the
  owner/manager routing derived from the HR SSOT — not from a hand-picked
  approver field — and the A0/A1 pre-authorized lanes are recorded standing
  grants with scope and expiry.
- **Execution elevates just-in-time.** The executing identity (human or the
  MID-server automation account) activates a time-boxed, scoped PIM role
  for the task's verb set (Move, Add, Change, Deletion, Reset); no standing
  privilege. The activation id is stamped on the task and rides into the
  closure evidence, binding *who could act* to *what was done*.

The closure clauses:

- **The close is the contract.** A closing update must carry a verification
  payload — the probe/re-test output that justified the close, its timestamp,
  and the checking mechanism — mirroring the Lane C rule that the form
  supplies every parameter the Script Include reads. A data policy rejects a
  `Closed Complete` whose closure-evidence field is empty.
- **A0/A1 auto-close on probe pass.** For the pre-authorized lanes the
  closing actor is the probe itself: when the verification query confirms
  target state, the task closes with the payload attached. Full automation is
  lawful here because verification is a **read** — the L3 ceiling governs
  autonomous estate *writes*, not evidence reads (`check_l3_ceiling.py`
  stays the gate for the write side).
- **Human-only closure is a flagged exception.** A manual close remains
  possible (operations need the escape hatch) but carries a
  `closed_manually` flag into every roll-up; control tests and KSI emission
  count probe-backed closures only, and the manual-closure rate is itself a
  reported indicator — expected to trend toward zero.
- **Reports are derivations, never compilations.** SLA attainment, patch
  conformance, POA&M aging, and the attestation roll-ups are generated from
  the closure stream (re-runnable, diffable) — the same
  generated-and-gated discipline the series applies to its own tables.

## Status — promoted to Volume IX

This scaffold is now the data layer of **Volume IX — ServiceNow Day-2 Operations**
(registered in `orgcomp-compliance-spine.yml` as `vol-9`):

- `Vol_IX_Book_00_OrgComp_Day2_Operations_Overview.qmd` — the day-2 coordination discipline
- `Vol_IX_Book_01_OrgComp_Helpdesk_ITSM_Catalog.qmd` — the ten catalog items this map binds
- `Vol_IX_Book_02_OrgComp_Landing_Zone_Front_Door.qmd` — Lane D
- `Vol_IX_Book_03_OrgComp_App_Registration_Governance.qmd` — Lane E (issue #1140)
- `Vol_IX_Book_04_OrgComp_Teams_Telephony_Catalog.qmd` — §4 (issue #1141)

## Remaining steps (issue #1139)

1. ~~Author the scoped-app records (Script Includes, Flows, ATF) mirroring the DDI app.~~ **Done** (this skeleton).
2. ~~Add per-lane control maps (landing-zone, app-reg, telephony).~~ **Done.**
3. Export the actual `sys_atf_test` XML and the assembled update-set XML from a sub-prod build.
4. ~~Wire the control-map CI check (regen-and-diff vs `orgcomp-compliance-spine.yml`) into the book CI.~~ **Done** (`validate_day2_control_maps.py`, wired in `.pre-commit-config.yaml` and `.github/workflows/orgcomp-authorities-drift.yml`).
5. Add catalog variable-set XMLs per item (mirroring the DDI app's `catalog/` variable sets).

## References

- `inbox/Federal_Compliance_Automation_Roadmap.md` (§3 Lane C, §5 crosswalk)
- `docs/customer-documents/orgcomp-series/Vol_VII_Book_05_OrgComp_ServiceNow_Compliance_App.qmd`
- `infoblox-ddi-book/servicenow-app/` (scoped-app exemplar)
- `docs/customer-documents/orgcomp-series/orgcomp-compliance-spine.yml`
