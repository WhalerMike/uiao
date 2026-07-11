# IntegrationHub REST actions — Infoblox WAPI / Universal DDI (VMware)

> **Starter skeleton.** These are the REST request bodies the ServiceNow
> **IntegrationHub REST** step calls from the Flow Designer flow (see
> [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md) §4). Every host,
> object/field version, view, CIDR, and record name is environment-specific and
> supplied by the flow's inputs / MID Server credential store / Vault — **nothing
> is hard-coded to a guess**. Confirm WAPI object and field names against **your**
> Grid Master at `<grid-master>/wapidoc/` before trusting any body below.

All calls run over the MID Server **inside the ATO boundary**. Placeholders:

- `<grid-master>` / `$GRID_MASTER` — Grid Master host/IP (NIOS WAPI). **No scheme**
  is written here; IntegrationHub prepends `https://` and pins the CA bundle.
- `$WAPI_VERSION` — e.g. `v2.12` (version-specific; confirm on your Grid).
- `<csp-host>` / `$INFOBLOX_CSP_URL` — Universal DDI / Portal host (SaaS,
  **outside** the boundary — `universal_ddi` path only; gated on
  `acknowledge_saas_boundary`).
- Auth: NIOS uses HTTP Basic (`$INFOBLOX_USERNAME` / `$INFOBLOX_PASSWORD`);
  Universal DDI uses `Authorization: Token $INFOBLOX_CSP_TOKEN`.

The base WAPI path is `<grid-master>/wapi/$WAPI_VERSION/`.

---

## 1. Next-available-IP (allocate from a network)

NIOS WAPI — call the `next_available_ip` function on the target `network`. Two
common forms: (a) reference the network by its `_ref`, or (b) allocate straight
into a new host/A record via a func-call field.

**Method / path**

```
POST  <grid-master>/wapi/$WAPI_VERSION/network?_function=next_available_ip
```

**Body**

```json
{
  "network": "$DDI_MGMT_NETWORK_CIDR",
  "network_view": "$NETWORK_VIEW",
  "num": 1
}
```

Returns `{"ips": ["10.20.10.42"]}`. The allocated IP feeds the A/PTR create in §2
(or the fixed-address in §3). `$DDI_MGMT_NETWORK_CIDR` maps to the Terraform
`ddi_mgmt_network_cidr` / a tenant segment CIDR.

**Universal DDI equivalent**

```
POST  <csp-host>/api/ddi/v1/ipam/address/nextavailableip
```

```json
{
  "id": "$ADDRESS_BLOCK_ID",
  "count": 1
}
```

---

## 2. Create A record (and PTR)

NIOS WAPI — creating the A record; add `"creator": "STATIC"`. Set the `_return_fields`
so the flow can capture the new `_ref` for later delete.

**A record — method / path / body**

```
POST  <grid-master>/wapi/$WAPI_VERSION/record:a?_return_fields=ipv4addr,name,_ref
```

```json
{
  "name": "$RECORD_FQDN",
  "ipv4addr": "$ALLOCATED_IP",
  "view": "$DNS_VIEW",
  "comment": "SNOW REQ $CATALOG_REQUEST_ID (VMware LZ)"
}
```

**PTR record**

```
POST  <grid-master>/wapi/$WAPI_VERSION/record:ptr
```

```json
{
  "ptrdname": "$RECORD_FQDN",
  "ipv4addr": "$ALLOCATED_IP",
  "view": "$DNS_VIEW"
}
```

> A single **`record:host`** with `configure_for_dns=true` will create the forward
> and reverse together and hold the IP in one object — often the cleaner choice
> for catalog provisioning. Path: `POST <grid-master>/wapi/$WAPI_VERSION/record:host`.

**Universal DDI equivalent**

```
POST  <csp-host>/api/ddi/v1/dns/record
```

```json
{
  "name_in_zone": "$HOSTNAME",
  "zone": "$ZONE_ID",
  "type": "A",
  "rdata": { "address": "$ALLOCATED_IP" }
}
```

---

## 3. Create fixed-address / DHCP reservation

VMware-relevant because **DHCP is genuinely Infoblox's job here** (contract §4/§8):
a catalog "reserve a DHCP address" action creates a `fixedaddress` bound to a MAC,
served to the NSX-relayed segment. On VMware `mac` is the natural key (the tenant
VM's vNIC MAC); a reservation-by-MAC is the DHCP equivalent of the static A above.

**Method / path**

```
POST  <grid-master>/wapi/$WAPI_VERSION/fixedaddress?_return_fields=ipv4addr,mac,_ref
```

**Body**

```json
{
  "ipv4addr": "$ALLOCATED_IP",
  "mac": "$VNIC_MAC",
  "network_view": "$NETWORK_VIEW",
  "name": "$RECORD_FQDN",
  "comment": "DHCP reservation — SNOW REQ $CATALOG_REQUEST_ID"
}
```

To let Infoblox pick the IP at reservation time, replace `ipv4addr` with the
func-call form `"ipv4addr": {"_object_function": "next_available_ip", "_parameters": {"num": 1}, "_result_field": "ips", "_object": "network", "_object_parameters": {"network": "$DDI_MGMT_NETWORK_CIDR"}}`.

> **DHCP scope / lease as a catalog action.** A "create DHCP range" action creates
> a `range` object (`POST <grid-master>/wapi/$WAPI_VERSION/range` with
> `start_addr`/`end_addr`/`network`); a "release lease" action deletes the lease
> ref found via `GET <grid-master>/wapi/$WAPI_VERSION/lease?address=$IP`. Run the
> `ipam-conflict-check.sh` gate first so the scope is conflict-free before the NSX
> DHCP relay is pointed at it.

**Universal DDI equivalent** (fixed address / reservation)

```
POST  <csp-host>/api/ddi/v1/dhcp/fixed_address
```

```json
{
  "address": "$ALLOCATED_IP",
  "match_type": "mac",
  "match_value": "$VNIC_MAC",
  "ip_space": "$IP_SPACE_ID",
  "name": "$RECORD_FQDN"
}
```

---

## 4. Delete (reclaim on retirement / Day-2)

NIOS WAPI — every object above is deleted by its `_ref` (captured on create). The
retirement catalog item releases the IP, removes the DNS records, and drops any
fixed-address, mirroring the Aria plug-in's reclaim path.

**Method / path (works for `record:a`, `record:ptr`, `record:host`, `fixedaddress`)**

```
DELETE  <grid-master>/wapi/$WAPI_VERSION/$OBJECT_REF
```

`$OBJECT_REF` is the URL-encoded `_ref`, e.g.
`record:a/ZG5zLmJpbmRfYQ...:app01.corp.example/default`. No request body. A `200`
with the returned `_ref` confirms deletion.

To release an allocation held only in IPAM (no record), clear the IP status:

```
PUT  <grid-master>/wapi/$WAPI_VERSION/$IPV4ADDRESS_REF
```

```json
{ "status": "UNUSED" }
```

**Universal DDI equivalent**

```
DELETE  <csp-host>/api/ddi/v1/dns/record/$RECORD_ID
DELETE  <csp-host>/api/ddi/v1/dhcp/fixed_address/$FIXED_ADDRESS_ID
```

---

## Action summary

| Catalog action | Method | Path (NIOS WAPI, no scheme) |
|---|---|---|
| Next-available-IP | `POST` | `<grid-master>/wapi/$WAPI_VERSION/network?_function=next_available_ip` |
| Create A | `POST` | `<grid-master>/wapi/$WAPI_VERSION/record:a` |
| Create PTR | `POST` | `<grid-master>/wapi/$WAPI_VERSION/record:ptr` |
| Create host (A+PTR+hold) | `POST` | `<grid-master>/wapi/$WAPI_VERSION/record:host` |
| Fixed-address / DHCP reservation | `POST` | `<grid-master>/wapi/$WAPI_VERSION/fixedaddress` |
| Create DHCP range | `POST` | `<grid-master>/wapi/$WAPI_VERSION/range` |
| Delete any object | `DELETE` | `<grid-master>/wapi/$WAPI_VERSION/$OBJECT_REF` |

All secrets come from the MID Server credential store / Vault / CI; the MID Server
keeps the WAPI call path in-boundary (see [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md)
§ GCC-Moderate notes).
