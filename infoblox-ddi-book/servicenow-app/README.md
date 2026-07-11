# `x_infoblox_ddi` — importable ServiceNow app skeleton

Where [Chapter 7](../07-servicenow-orchestration.md) and each package's
`servicenow/` folder describe *how* ServiceNow fronts the DDI automation, this
folder is the **importable starting point**: the actual scoped-app records — Script
Includes, a REST Message, a Flow blueprint, and the MID Server gate script — so an
admin can stand it up instead of hand-building from prose.

> **Starter skeleton.** These are illustrative, un-signed source records for a scoped
> app named `x_infoblox_ddi`. Review, complete the catalog variable sets per platform,
> pin your WAPI/Universal DDI versions, and test in a sub-prod instance before use.

![ServiceNow app record model: a catalog item triggers the Flow, which calls the InfobloxDDIClient and InfobloxDDIGate Script Includes; the client drives the Infoblox REST Message through the in-boundary MID Server using a credential alias, the gate runs the validation scripts, and the Service Graph Connector feeds the CMDB](figs/snapp-01-record-model.png)

## What's here

| Path | Record / artifact | Role |
|---|---|---|
| [`script-includes/InfobloxDDIClient.js`](./script-includes/InfobloxDDIClient.js) | `sys_script_include` | Server-side Infoblox client — next-available-IP, create host (A+PTR), delete/reclaim; NIOS WAPI **and** Universal DDI branches |
| [`script-includes/InfobloxDDIGate.js`](./script-includes/InfobloxDDIGate.js) | `sys_script_include` | Post-apply validation gate; dispatches the MID wrapper and parses its JSON verdict |
| [`update-set/sys_rest_message_infoblox.xml`](./update-set/sys_rest_message_infoblox.xml) | `sys_rest_message` (+ `_fn`) | The outbound REST definition (endpoint/auth from a credential alias, routed via MID) |
| [`mid/infoblox-ddi-validate.sh`](./mid/infoblox-ddi-validate.sh) | MID Server script | Runs the three per-platform validation scripts, emits one JSON verdict |
| [`flow/flow-blueprint.md`](./flow/flow-blueprint.md) | Flow Designer blueprint | The "Provision DDI-backed subnet" flow, retirement flow, and staleness→Incident job, with inline Action scripts |

## Prerequisites (from the ServiceNow Store)

- **Cloud Provisioning & Governance: Terraform Connector** — fronts each package's
  `terraform/` module as a catalog item.
- **Service Graph Connector for Infoblox** — IPAM → CMDB sync.
- A **MID Server** registered **inside the ATO boundary** (Chapter 7 §7.4).

## Import & wire-up

1. Create the scoped app `x_infoblox_ddi` (or import these as an update set).
2. Add the two **Script Includes** and the **REST Message** records.
3. Create a **Connection & Credential alias** `x_infoblox_ddi.infoblox` → your Grid
   Master (WAPI) or Universal DDI base URL, with the MID Server selected.
4. Set the app properties: `x_infoblox_ddi.api_flavor` (`nios`|`universal_ddi`),
   `x_infoblox_ddi.wapi_version`, `x_infoblox_ddi.mid_server`,
   `x_infoblox_ddi.mid_scripts_dir`.
5. Copy `mid/infoblox-ddi-validate.sh` **and** each platform's `validation/*.sh` to
   the MID host under `mid_scripts_dir/<platform>/`.
6. Build the **Flow** per [`flow/flow-blueprint.md`](./flow/flow-blueprint.md) and
   publish the **catalog items** (subnet request + decommission), mapping variables
   to the target module's `tfvars` (per each package's `servicenow/` doc).

## Boundary & governance

Same discipline as the rest of the volume: FedRAMP-authorized ServiceNow instance,
**MID Server in-boundary** so credentials/execution never leave the ATO boundary,
and the Universal DDI SaaS path gated by `acknowledge_saas_boundary`. The catalog
approval, change record, gate output, and CMDB reconcile are the audit evidence
(control mapping in Chapter 7 §7.4).

---

*Vendor-integration skeleton, independent of UIAO governance canon; self-contained
under `infoblox-ddi-book/servicenow-app/`.*
