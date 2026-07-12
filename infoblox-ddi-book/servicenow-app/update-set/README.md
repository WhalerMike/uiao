# Update set — one-step import of the `x_infoblox_ddi` app

Rather than hand-adding each record, this folder assembles the whole scoped app into a
single ServiceNow **update set** you retrieve in one step.

| File | Role |
|---|---|
| [`build-update-set.py`](./build-update-set.py) | Assembles the app's records into the combined update set (deterministic output) |
| `x_infoblox_ddi-update-set.xml` | The assembled update set — **19 records** (generated; re-run the script after editing any source record) |
| [`sys_rest_message_infoblox.xml`](./sys_rest_message_infoblox.xml) | The outbound REST Message (also bundled into the set) |

## What's in the set (19 records)

- **2 Script Includes** — `InfobloxDDIClient`, `InfobloxDDIGate` (JS wrapped as `sys_script_include`).
- **1 REST Message** — `Infoblox DDI` (`sys_rest_message`).
- **5 catalog variable sets** — one per platform ([`../catalog/`](../catalog/README.md)).
- **4 ATF tests** — happy path + three negatives ([`../atf/`](../atf/README.md)).
- **7 app properties** — `api_flavor`, `wapi_version`, `mid_server`, `mid_scripts_dir`, and the
  three TEST-ONLY toggles (`test_mode`, `test_force_gate_fail`, `test_ip`) defaulting to safe values.

The MID scripts ([`../mid/`](../mid/infoblox-ddi-validate.sh) and each package's
`validation/*.sh`) are **not** in the update set — they are deployed to the MID host
filesystem, not imported as instance records (see the [build playbook](../PLAYBOOK-servicenow-led-build.md) Phase 4).

## Build & import

```bash
python3 build-update-set.py        # regenerates x_infoblox_ddi-update-set.xml
```

Then in ServiceNow: **Retrieved Update Sets → Import Update Set from XML →** upload
`x_infoblox_ddi-update-set.xml` → **Preview → Commit**. Build the catalog item and Flow
per the [build playbook](../PLAYBOOK-servicenow-led-build.md) (the variable sets and Script
Includes they consume are now present).

## Honest scope

- **This is an *unsigned* update set, not a signed Store app.** Cryptographic signing is a
  ServiceNow Store publishing step, not something a repo can emit. For production, develop
  the app in a scoped application on a sub-prod instance and publish it through your normal
  app-repo / Store pipeline; use this assembled set to seed that app.
- The payload encoding here (escaped record XML inside `<sys_update_xml>`) is the standard
  update-set shape, but **preview it and adjust against your instance version** before
  relying on a one-click commit — some record types want extra fields on import.
- The records remain **labeled starter skeletons** (the Script Includes note where the ECC
  round-trip and Universal DDI id-resolution must be reworked; the ATF steps are rebuilt in
  the ATF Designer).
