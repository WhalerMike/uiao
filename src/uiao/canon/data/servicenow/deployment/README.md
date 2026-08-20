# ServiceNow Deployment Export — Evidence Side

This directory holds the **evidence side** of the ServiceNow deployment
contract pin (UIAO_211): a `sys_dictionary` / `sys_db_object` export taken
from the target instance.

It is empty on purpose. Nothing here can be produced from the repository —
the artifacts require read access to the instance, and until they exist
`scripts/check_servicenow_schema_pin.py` reports instance agreement as
*pending* rather than passing it silently.

## What to commit

| File | Source | Purpose |
|---|---|---|
| `sys-dictionary.<env>.json` | `sys_dictionary` | Column-level truth: which columns exist on each table, their types, and their owning scope |
| `sys-db-object.<env>.json` | `sys_db_object` | Table-level truth: which tables exist, their labels, parents, and owning scope |
| `oas.<env>.json` *(optional)* | Instance OpenAPI export | Vendor half, instance-flavoured — ServiceNow has supported OAS export since Tokyo |

`<env>` names the instance the export came from (for example `prod`, `test`,
`dev`). The checker picks up any file matching `sys-dictionary*.json`.

## How to take the export

Use `scripts/export_servicenow_schema.py`. It reads the table list from
`../expected-schema.yaml` (so the two cannot drift), resolves the host through
`ServiceNowCollector` (so it cannot disagree with the adapters about which
cloud it is talking to), writes both artifacts here, and fills in the export
log below.

```
$env:SERVICENOW_INSTANCE = "<instance>"     # host is <instance>.servicenowservices.com
$env:SERVICENOW_TOKEN    = "<bearer token>"

python scripts/export_servicenow_schema.py --env prod --dry-run   # show the calls
python scripts/export_servicenow_schema.py --env prod --operator "<name>"
```

Credentials come from the environment only — the script takes no credential
arguments, so they cannot land in shell history. It fails closed rather than
constructing a placeholder host, and refuses to write an export that came back
empty, because an empty export would make the gate report every column missing.

The underlying calls, if you would rather run them by hand: both are ordinary
Table API reads against the GCC host recorded in `../expected-schema.yaml`. Run
them with an account that can read the dictionary; no write access is needed.

```
GET https://<instance>.servicenowservices.com/api/now/table/sys_dictionary
    ?sysparm_query=nameINincident,change_request,problem,sc_request,cmdb_ci_ip_network,cmdb_ci_privileged_id^elementISNOTEMPTY
    &sysparm_fields=name,element,internal_type,column_label,active,sys_scope.scope
    &sysparm_limit=2000
```

```
GET https://<instance>.servicenowservices.com/api/now/table/sys_db_object
    ?sysparm_query=nameINincident,change_request,problem,sc_request,cmdb_ci_ip_network,cmdb_ci_privileged_id
    &sysparm_fields=name,label,super_class,sys_scope.scope
    &sysparm_limit=200
```

Save each response body verbatim. The checker accepts either the raw Table API
envelope (`{"result": [...]}`) or a bare list.

## What must NOT be committed

The export is **configuration inventory only** — table names, column names,
types, labels, and scopes. It must never contain record data: no incidents, no
catalog requests, no user references, no `sys_id` values from business
records. `sysparm_fields` above is written to make that structural rather than
a matter of discipline.

## After the export lands

1. Run `python scripts/check_servicenow_schema_pin.py` and resolve every
   finding it reports.
2. Settle the `control-id-prefix` discrepancy recorded under `unresolved:` in
   `../expected-schema.yaml` — the export is what decides it.
3. Record each artifact's SHA-256 and the export date in this README, matching
   the hash-anchoring UIAO_210 §2 uses for the SailPoint pin.
4. Promote the pre-commit hook to `--strict`, so a missing export becomes a
   failure rather than a pending note.

## Export log

| Artifact | SHA-256 | Instance | Exported | Operator |
|---|---|---|---|---|
| *(none yet)* | — | — | — | — |
