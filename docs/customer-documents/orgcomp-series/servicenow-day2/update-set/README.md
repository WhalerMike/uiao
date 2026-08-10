# Update set — Day-2 Operations app

The whole `x_fed_day2_ops` scoped app assembled into one importable update-set XML
(same pattern as `infoblox-ddi-book/servicenow-app/update-set/`). This directory
ships no XML today — the platform records (tables, ACLs, roles, catalog items,
Flow, Scripted REST API) are **built on your instance from `KIT-BUILD-SPEC.md` and
exported here**, because an update-set / Flow / ATF XML is a machine-serialized
export, not authorable text (see `../START-HERE.md` §1). What follows is the
object-by-object contents list and the per-surface checklist for what to verify
after import, since there is no XML to inspect until you build and export it.

## Contents by surface

- **Script Includes** — the full set from `KIT-BUILD-SPEC.md` §3:
  `EntraHelpdeskClient`, `EntraHelpdeskGate`, `AzureArmClient`, `PimActivationClient`,
  `SamCorrelationClient`, `MacdrOrchestrator`, `Day2Env`, `Day2NativeActuator`,
  `EntraAppRegClient`, `EntraSaasClient`, `AcmeCredentialClient`,
  `TeamsTelephonyClient`, `TerraformCpgClient`, and (Current State / AD edition
  only) `AdHybridClient`.
- **Scripted REST API** — `x_fed_day2_ops/sam`, resource `POST /ritm`
  (`../scripted-rest/sam_inbound_ritm.js`), requires authentication, ACL'd to the
  `x_fed_day2_ops.sam_inbound` role only. See the SAM subsection below — this is
  the one surface in the app that accepts an inbound push rather than only being
  called from a Flow.
- **REST Message** — `x_fed_day2_ops.graph` (Microsoft Graph, MID-routed, credential
  alias — no secrets in the record) and, for the SAM correlation/status API,
  `x_fed_day2_ops.sam` (see below).
- **Flow** — "Governed Day-2 Request" (see `../flow/flow-blueprint.md`).
- **Catalog items + variable sets** — one per catalog entry across the five control
  maps (`helpdesk-`, `landingzone-`, `appreg-`, `telephony-`, `saas-control-map.json`).
- **Roles** — `x_fed_day2_ops.operator`, `x_fed_day2_ops.approver`,
  `x_fed_day2_ops.sam_inbound`, `x_fed_day2_ops.admin` (`KIT-BUILD-SPEC.md` §1).
- **Tables** — `x_fed_day2_ops_evidence` and `x_fed_day2_ops_integration`, exact
  columns per `KIT-BUILD-SPEC.md` §2.
- **ACLs** — least-privilege create/read/execute grants per `KIT-BUILD-SPEC.md` §5;
  evidence and integration rows are write-once (no operator update/delete ACL).
- **App properties** — every row in `../KIT-VARIABLES-REFERENCE.md` §1a, including
  `mid_server`, `boundary` (`gcc-moderate`), `graph_version`, `test_mode`, and the
  SAM-specific properties below.
- **ATF tests** — the suites in `../atf/`, including the seven SAM tests
  (`atf-sam-*.xml` — see `../atf/README.md`).

## The SAM inbound objects — packaging checklist

The SAM (SailPoint IGA) surface is the one inbound entry point in the app (SAM
pushes; everything else is ServiceNow-initiated), so it has its own cross-cutting
checklist. Import/build every row below before enabling a live SDIM push —
missing any one of them leaves the endpoint either non-functional or, worse,
functional without its safety gate:

| Object | Where | Post-import check |
|---|---|---|
| Scripted REST resource | `x_fed_day2_ops/sam`, `POST /ritm` → `../scripted-rest/sam_inbound_ritm.js` | Requires authentication = **true**. Confirm no anonymous access is possible. |
| ACL on the resource | `execute` on `POST /api/x_fed_day2_ops/sam/ritm` | Role = `x_fed_day2_ops.sam_inbound` **only** — not `admin`, not `itil`. `atf-sam-negative-missing-role.xml` proves `hasRoleExactly` refuses even an admin without the explicit grant. |
| Role | `x_fed_day2_ops.sam_inbound` | Granted to the IIQ (or ISC) integration user **only** — no human, no service account shared with another integration. |
| Script Includes | `SamCorrelationClient`, `Day2Env` | `Day2Env` must import first or alongside — `SamCorrelationClient`'s consumers (`sam_inbound_ritm.js`) construct both. |
| Integration table | `x_fed_day2_ops_integration` (`tbl_integration` property), columns per `KIT-BUILD-SPEC.md` §2b | **Create a UNIQUE INDEX on `sam_request_id`** — the endpoint's idempotency check (`GlideRecord.get` then insert) races without one under concurrent SDIM retries; this is a required deployment step, not optional (see the header of `sam_inbound_ritm.js`). |
| System properties | `sam_flavor`, `sam_base_url`, `sam_source_id`, `iiq_verify_endpoint`, `sam_jws_public_key`, `nonprod_instances`, `tbl_integration`, `sam_closure_writeback` | With **neither** `iiq_verify_endpoint` nor `sam_jws_public_key` set, every push is refused by design — that is the safe post-import default, not a broken install. Set exactly one verification method before going live. `sam_closure_writeback` defaults `false` (opt-in) and is safe to leave off. |
| Alias | `x_fed_day2_ops.sam` (Connection & Credential) | Points at `sam_base_url`; IIQ = API-Client OAuth2 or least-privilege Basic service account, ISC = OAuth2 PAT. Bound to the in-boundary MID Server — SAM callbacks are intra-boundary egress, same discipline as Graph/ARM. |
| Script Include | `MacdrOrchestrator` | The one that calls `SamCorrelationClient.writeClosureSummary` when `sam_closure_writeback` is enabled — see `KIT-USAGE-SAM-INTEGRATION.md` "Optional: richer closure write-back". Already required for every non-SAM lane too; called out here because it is the SAM closure integration point. |
| Telemetry | `x_fed_day2_ops_integration` rows with `record_type = sam_push_outcome` | Written automatically by every push, accepted or refused — no separate object to import, but confirm the integration table has the `test_mode`/`synthetic` columns (added alongside the lineage columns, `KIT-BUILD-SPEC.md` §2b) so monitoring queries can exclude sub-prod ATF noise. |
| ATF suite | `../atf/atf-sam-*.xml` (9 tests) | Run in `test_mode` before enabling the live connector — see the next section. |

## Build & import

1. Develop the records in a sub-prod scoped app `x_fed_day2_ops`.
2. Capture them in an update set and export the XML here.
3. In the target instance: create the `x_fed_day2_ops.graph` and `x_fed_day2_ops.sam`
   Connection & Credential aliases (endpoints + MID Server selected), set every app
   property in `../KIT-VARIABLES-REFERENCE.md` §1a (including the SAM properties
   above), create the unique index on `x_fed_day2_ops_integration.sam_request_id`,
   run the control-map CI check against `orgcomp-compliance-spine.yml`, and run the
   ATF suites — including `atf-sam-*.xml` — in `test_mode` before enabling any live
   connector (Graph, ARM, or SAM).
4. Only after the full ATF suite is green: configure exactly one SAM verification
   method (`iiq_verify_endpoint` for pull-verify, or `sam_jws_public_key` for
   signed-push) and set `test_mode = false`.

Boundary discipline is identical to the DDI app: FedRAMP-authorized ServiceNow, MID
Server in-boundary, least-privilege Graph app registration (read + scoped, logged,
individually-approved write — never standing tenant admin). GCC Moderate only.
