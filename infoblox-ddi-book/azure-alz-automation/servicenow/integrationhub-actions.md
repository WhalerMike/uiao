# IntegrationHub REST Actions — Azure Infoblox DDI calls

> **Starter skeleton.** Concrete request bodies the ServiceNow **IntegrationHub
> REST** actions send for this Azure package's active IPAM/DNS calls. These are
> the payloads behind the "IntegrationHub REST" row of the flow in
> [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md). Endpoint hosts,
> WAPI object/field names, and Universal DDI paths are version-specific — confirm
> against `<grid-master>/wapidoc/` (NIOS) or the current CSP API docs before
> relying on them. All hosts are shown as placeholders (`<grid-master>` /
> `$GRID_MASTER`, `<csp-host>`) with **no `https://` scheme** — the MID Server
> prepends the scheme from its connection record.

## Connection & credential model

- Base connection alias (NIOS): `WAPI` → host `$GRID_MASTER`, base path
  `/wapi/$WAPI_VERSION` (default `v2.12`), **Basic auth**
  (`$INFOBLOX_USERNAME` / `$INFOBLOX_PASSWORD`).
- Base connection alias (Universal DDI): `CSP` → host `<csp-host>`
  (commercial: `csp.infoblox.com`), **Token auth** (`Authorization: Token
  $INFOBLOX_CSP_TOKEN`).
- **Credentials come from Azure Key Vault**, surfaced to the MID Server, not
  stored in cleartext in ServiceNow — see the GCC-Moderate notes in
  `ServiceNow-Orchestration.md`. The Key Vault secret names are the module's
  `admin_password_secret_name`, `grid_shared_secret_name`, etc.
- All calls execute **on the in-boundary MID Server** so the WAPI-to-Grid path
  never leaves the ATO boundary.

---

## (a) Allocate next available IP from a network

Allocate the next free address from the network Infoblox synced for the Azure
DDI subnet (typically `ddi_subnet_address_prefix`, or a spoke range). This is
the classic "give me an IP" call the flow makes before creating the A record.

### NIOS WAPI

Two-step in NIOS: resolve the network's object reference (`_ref`), then invoke
the `next_available_ip` function on it.

**Step 1 — find the network `_ref`:**

```
GET  $GRID_MASTER/wapi/$WAPI_VERSION/network?network=10.10.4.0/27&network_view=default&_return_fields%2B=network
```

**Step 2 — allocate next available IP (function call on the `_ref`):**

```
POST $GRID_MASTER/wapi/$WAPI_VERSION/network/<ref>?_function=next_available_ip
Content-Type: application/json

{
  "num": 1,
  "exclude": []
}
```

Response (illustrative): `{ "ips": ["10.10.4.5"] }`. The flow stores the
returned address for the record-create step below.

> NIOS shortcut: some releases let you skip Step 1 and pass
> `func:nextavailableip:<cidr>` inline as the value of an `ipv4addr` field when
> creating the record (see (b)), which fuses allocate + create into one call.

### Universal DDI (Infoblox Portal / CSP)

Single call against the IPAM address-block; the API returns the allocated
address object directly. Endpoint shape is illustrative — confirm per tenant.

```
POST <csp-host>/api/ddi/v1/ipam/address?_nextavailable=1
Authorization: Token $INFOBLOX_CSP_TOKEN
Content-Type: application/json

{
  "space": "<ip-space-id>",
  "parent": "<address-block-id-for-10.10.4.0/27>",
  "count": 1
}
```

**Key difference:** NIOS keys everything on the opaque `_ref` and a
`_function=` query param; Universal DDI keys on resource IDs (`space`,
`parent`) and JSON body flags, with the Portal control plane **outside** the
ATO boundary (gated by `acknowledge_saas_boundary`).

---

## (b) Create host / A record

Register the allocated IP as a DNS name. Prefer a **host record** (`record:host`)
when you want IPAM to own the address + name together; use a plain **A record**
(`record:a`) when the zone/name is managed separately. Add the PTR by enabling
it on the host, or with a separate `record:ptr` for the A-record path.

### NIOS WAPI — host record (allocate + register fused)

```
POST $GRID_MASTER/wapi/$WAPI_VERSION/record:host
Content-Type: application/json

{
  "name": "app01.corp.example.com",
  "ipv4addrs": [
    { "ipv4addr": "func:nextavailableip:10.10.4.0/27" }
  ],
  "configure_for_dns": true,
  "view": "default",
  "comment": "SNOW REQ0012345 — Azure ALZ DDI",
  "extattrs": {
    "Tenant":           { "value": "azure-alz" },
    "environment":      { "value": "prod" },
    "servicenow_sys_id":{ "value": "<sys_id>" }
  }
}
```

### NIOS WAPI — A record (explicit IP from step (a))

```
POST $GRID_MASTER/wapi/$WAPI_VERSION/record:a
Content-Type: application/json

{
  "name": "app01.corp.example.com",
  "ipv4addr": "10.10.4.5",
  "view": "default",
  "comment": "SNOW REQ0012345",
  "extattrs": { "servicenow_sys_id": { "value": "<sys_id>" } }
}
```

The matching PTR (reverse) record:

```
POST $GRID_MASTER/wapi/$WAPI_VERSION/record:ptr
Content-Type: application/json

{
  "ptrdname": "app01.corp.example.com",
  "ipv4addr": "10.10.4.5",
  "view": "default"
}
```

### Universal DDI (Portal / CSP) — DNS record

```
POST <csp-host>/api/ddi/v1/dns/record
Authorization: Token $INFOBLOX_CSP_TOKEN
Content-Type: application/json

{
  "name_in_zone": "app01",
  "zone": "<zone-id-for-corp.example.com>",
  "type": "A",
  "rdata": { "address": "10.10.4.5" },
  "options": { "create_ptr": true },
  "tags": { "servicenow_sys_id": "<sys_id>", "Tenant": "azure-alz" }
}
```

**Key differences:** NIOS uses `record:host` / `record:a` / `record:ptr`
objects with `extattrs`; Universal DDI uses a single typed `dns/record` object
keyed on a `zone` ID with `rdata` + `tags`, and PTR creation is a body option
rather than a separate object.

---

## (c) Delete on reclaim (Day-2 retirement)

Called by the **retirement catalog item** (`terraform destroy` companion) to
release the IP and record so IPAM stays accurate (contract §CM-8 inventory).

### NIOS WAPI

Delete by object reference — resolve the `_ref` first, then `DELETE` it.
Deleting the host record (or A record) also releases the IPAM lease.

```
GET    $GRID_MASTER/wapi/$WAPI_VERSION/record:host?name=app01.corp.example.com&_return_fields%2B=name

DELETE $GRID_MASTER/wapi/$WAPI_VERSION/<ref>
```

For the A + PTR path, delete both `record:a` and `record:ptr` refs. To free a
fixed address without a DNS name, delete the `fixedaddress`/`ipv4address` `_ref`
instead.

### Universal DDI (Portal / CSP)

```
DELETE <csp-host>/api/ddi/v1/dns/record/<record-id>
Authorization: Token $INFOBLOX_CSP_TOKEN
```

Releasing the IPAM address (if allocated separately in (a)):

```
DELETE <csp-host>/api/ddi/v1/ipam/address/<address-id>
Authorization: Token $INFOBLOX_CSP_TOKEN
```

**Key difference:** NIOS requires a lookup-then-delete on the opaque `_ref`;
Universal DDI deletes directly by the resource ID returned at create time
(store it on the ServiceNow request/CI so reclaim doesn't need a lookup).

---

## Action summary

| Action | NIOS WAPI | Universal DDI (CSP) |
|---|---|---|
| Allocate next IP | `POST network/<ref>?_function=next_available_ip` | `POST /api/ddi/v1/ipam/address?_nextavailable=1` |
| Create host/A (+PTR) | `POST record:host` / `record:a` (+ `record:ptr`) | `POST /api/ddi/v1/dns/record` (`create_ptr`) |
| Delete on reclaim | `GET` for `_ref` → `DELETE /<ref>` | `DELETE /api/ddi/v1/dns/record/<id>` |
| Auth | Basic (`$INFOBLOX_USERNAME`/`$INFOBLOX_PASSWORD`) | Token (`$INFOBLOX_CSP_TOKEN`) |
| Boundary | in-boundary (Grid) | **out-of-boundary** (Portal SaaS) |

See [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md) for how these
actions slot into the Flow Designer flow and the catalog-item → tfvars mapping.
