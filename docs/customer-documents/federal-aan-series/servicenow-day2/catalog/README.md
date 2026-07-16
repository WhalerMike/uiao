# Catalog — Day-2 Operations app (Lane C exemplar)

The catalog form is the front door of every governed day-2 request. This folder
holds the **variable set** an admin imports and the **contract check** that keeps
it honest.

| File | Role |
|---|---|
| `variable-set-helpdesk-identity.xml` | `item_option_new` records — the Lane C form. Each variable's `<map_to>` names the `EntraHelpdeskClient` parameter (or `EntraHelpdeskGate` pre-flight field) it feeds. |
| `contract_check.py` | The gate. Asserts the form is a superset of what the client and gate actually require, that secrets are MID-resolved, and that every catalog item can actuate. |

## The form is the contract

The failure this prevents is quiet: someone renames a client parameter, or adds a
required one, and the form stops supplying it. Nothing breaks in review — it
breaks in a tenant, at 2am, on a request someone needed. `contract_check.py`
asserts the binding at **build time** instead. It runs in pre-commit
(`aan-day2-catalog-contract`) and in CI.

Three invariants:

1. **Coverage.** Every parameter `EntraHelpdeskClient` reads, and every field
   `EntraHelpdeskGate.preflight()` reads, is either collected as a form field
   (`<map_to>`) or resolved on the in-boundary MID Server (`<resolved_by_mid>`).

2. **Secrets are never form fields.** `opts.tempPassword` is generated on the MID
   Server and delivered out-of-band; it must never land on the catalog record
   (IA-5). Declaring it `<map_to>` is a hard fail. This mirrors the DDI kit's
   `vsphere_password` / `admin_password` rule.

3. **Every catalog item actuates — or says why it cannot.** Two items in
   `helpdesk-control-map.json` have no client method, and that is recorded in
   `ACTUATOR_GAPS` with the reason rather than left to be discovered:

   | Item | Why there is no actuator |
   |---|---|
   | `entra.credential.account_unlock` | Microsoft Graph exposes no admin account-unlock operation; Entra smart lockout auto-clears, so this reduces to `resetPassword` or an Entra-side wait. |
   | `entra.access.ca_exception` | Actuates as a Conditional-Access **policy** edit, not a user-object write. |

   A catalog item that cannot actuate is a control claim with nothing behind it.
   The check refuses to let that be silent.

## Actuation posture (L3 — ADR-092)

The form **raises and routes**; Microsoft Graph, reached through the in-boundary
MID Server, **actuates**; a human **approves**. ServiceNow never writes to the
estate. The federal default ceiling is L3 (human-approved actuation) — nothing in
this folder implements autonomous reconciliation.

## Import notes

Set the ServiceNow variable `type` codes and reference qualifiers per instance
(6 = Single Line Text, 5 = Select Box, 7 = Reference, 8 = Date/Time,
24 = Checkbox, 20 = Multi Line Text). Identity fields should be **reference
lookups** (type 7) so requesters cannot free-type directory ids — a free-typed id
is an unreconciled target, which the gate then has to catch.

## Run it

```bash
cd "docs/customer-documents/federal-aan-series/servicenow-day2/catalog"
python contract_check.py
```
