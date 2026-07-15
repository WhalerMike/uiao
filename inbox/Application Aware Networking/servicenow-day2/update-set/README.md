# Update set — Day-2 Operations app

The whole `x_ssa_day2_ops` scoped app assembled into one importable update-set XML
(same pattern as `infoblox-ddi-book/servicenow-app/update-set/`). Contents:

- **Script Includes** — `EntraHelpdeskClient`, `EntraHelpdeskGate`.
- **REST Message** — `x_ssa_day2_ops.graph` (Microsoft Graph, MID-routed, credential
  alias — no secrets in the record).
- **Flow** — "Governed Day-2 Request" (see `../flow/flow-blueprint.md`).
- **Catalog items + variable sets** — one per catalog entry across the five control
  maps (`helpdesk-`, `landingzone-`, `appreg-`, `telephony-`, `saas-control-map.json`).
- **App properties** — `mid_server`, `boundary` (`gcc-moderate`), `graph_version`,
  `test_mode`.
- **ATF tests** — the suites in `../atf/`.

## Build & import

1. Develop the records in a sub-prod scoped app `x_ssa_day2_ops`.
2. Capture them in an update set and export the XML here.
3. In the target instance: create the `x_ssa_day2_ops.graph` Connection & Credential
   alias (Graph endpoint, MID Server selected), set the app properties, run the
   control-map CI check against `aan-compliance-spine.yml`, and run the ATF suites in
   `test_mode` before enabling the live connector.

Boundary discipline is identical to the DDI app: FedRAMP-authorized ServiceNow, MID
Server in-boundary, least-privilege Graph app registration (read + scoped, logged,
individually-approved write — never standing tenant admin). GCC Moderate only.
