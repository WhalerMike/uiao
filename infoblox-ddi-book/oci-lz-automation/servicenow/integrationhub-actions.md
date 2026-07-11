# IntegrationHub REST actions — Infoblox DDI for OCI

> **Starter skeleton — illustrative, not certified.** These are the REST bodies the
> ServiceNow **IntegrationHub REST** step invokes from the Flow Designer flow
> (see [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md) step 4) to make
> the *active* IPAM/DNS calls the [`../terraform`](../terraform) apply does not: allocate
> the next free IP, create the forward/reverse records, and reclaim them on retirement.
> WAPI object/field names are version-specific — confirm against **your** Grid Master at
> `<grid-master>/wapidoc/` before relying on them (contract §9).

## Conventions (match the rest of the package)

- **No `https://` scheme in placeholders.** Hosts appear as `<grid-master>` /
  `$GRID_MASTER` (NIOS Grid, in-tenancy) and `csp.infoblox.com` (Universal DDI / Portal
  SaaS). IntegrationHub adds the scheme at connection-config time; the boundary-clean
  default is Grid over WAPI (contract §1).
- **WAPI base path:** `<grid-master>/wapi/v2.12` (pin `WAPI_VERSION` to your Grid release).
- **Auth:** WAPI basic auth; the username/password come from an **OCI Vault** secret
  surfaced to the MID Server / IntegrationHub connection, never inline (contract §9).
  Universal DDI uses `Authorization: Token <csp-token>` from the same Vault.
- **Views:** `network_view` / `dns_view` default to `default`; pass explicitly for
  split-horizon. Reverse (PTR) records live in the delegated OCI reverse zones (contract §8).
- **Boundary flavor:** the **NIOS / WAPI** bodies are the default (in-boundary). The
  **Universal DDI** bodies talk to the Portal SaaS control plane **outside the ATO
  boundary** — only used when `deployment_model = universal_ddi` and
  `acknowledge_saas_boundary = true`.

Each action lists **method**, **path** (relative to the base), and the **JSON body**.

---

## NIOS / WAPI (deployment_model = grid — default, in-boundary)

Base: `<grid-master>/wapi/v2.12`

### 1. Allocate next-available IP (from the DDI subnet or a target network)

Allocate and register in one call by creating a **host record** with a
`func:nextavailableip` value scoped to the network the Terraform apply created
(`ddi_subnet_cidr`, or a spoke range). This reserves the IP *and* names it atomically.

- **Method:** `POST`
- **Path:** `/record:host?_return_fields%2B=ipv4addrs,name&_return_as_object=1`
- **Body:**

```json
{
  "name": "app01.corp.example",
  "view": "default",
  "ipv4addrs": [
    {
      "ipv4addr": {
        "_object_function": "next_available_ip",
        "_object": "network",
        "_object_parameters": { "network": "10.10.4.0/27", "network_view": "default" },
        "_result_field": "ips"
      }
    }
  ],
  "comment": "SNOW REQ <req-number> — allocated by IntegrationHub",
  "extattrs": {
    "ServiceNow Request": { "value": "<req-number>" },
    "deployment_model":    { "value": "grid" }
  }
}
```

If you prefer to reserve a bare address (no host object), use `network`'s
`next_available_ip` function instead:

- **Method:** `POST`
- **Path:** `/network/<network-ref>?_function=next_available_ip`
- **Body:** `{ "num": 1 }` → returns `{ "ips": ["10.10.4.5"] }`.

### 2. Create the A record

- **Method:** `POST`
- **Path:** `/record:a?_return_fields%2B=name,ipv4addr&_return_as_object=1`
- **Body:**

```json
{
  "name": "app01.corp.example",
  "ipv4addr": "10.10.4.5",
  "view": "default",
  "comment": "SNOW REQ <req-number>",
  "extattrs": { "ServiceNow Request": { "value": "<req-number>" } }
}
```

### 3. Create the PTR record (reverse)

Reverse zones for the OCI CIDRs are delegated to Infoblox (contract §8), so the PTR is
authoritative in IPAM.

- **Method:** `POST`
- **Path:** `/record:ptr?_return_fields%2B=ptrdname,ipv4addr&_return_as_object=1`
- **Body:**

```json
{
  "ptrdname": "app01.corp.example",
  "ipv4addr": "10.10.4.5",
  "view": "default",
  "comment": "SNOW REQ <req-number>",
  "extattrs": { "ServiceNow Request": { "value": "<req-number>" } }
}
```

### 4. Delete on retirement (reclaim IP + records)

The retirement catalog item runs `terraform destroy`, then IntegrationHub reclaims the
DDI objects. WAPI deletes by object **_ref**, so first read the ref, then delete it.

**4a. Look up the record ref**

- **Method:** `GET`
- **Path:** `/record:a?name=app01.corp.example&view=default`
- **Body:** *(none — query string only)* → returns `[{"_ref":"record:a/ZG5z…:app01.corp.example/default", ...}]`

**4b. Delete the A record**

- **Method:** `DELETE`
- **Path:** `/record:a/ZG5z…:app01.corp.example/default`
- **Body:** *(none)*

**4c. Delete the PTR record** (repeat the lookup on `/record:ptr`, then)

- **Method:** `DELETE`
- **Path:** `/record:ptr/ZG5z…:5.4.10.10.in-addr.arpa/default`
- **Body:** *(none)*

**4d. Release the fixed address / host (if a host record was used in step 1)**

- **Method:** `DELETE`
- **Path:** `/record:host/ZG5z…:app01.corp.example/default`
- **Body:** *(none)* — releases the IP back to the network for reuse (CM-8 accurate inventory).

---

## Universal DDI / Infoblox Portal (deployment_model = universal_ddi — SaaS, OUT of boundary)

> **Boundary caveat.** These call the Infoblox Portal (CSP) SaaS control plane at
> `csp.infoblox.com` — **outside the ATO boundary** (contract §1). Only wire these when
> `acknowledge_saas_boundary = true`. Endpoints are illustrative; confirm the current
> paths in the CSP API docs for your tenant. Auth header: `Authorization: Token <csp-token>`.

Base: `csp.infoblox.com/api/ddi/v1`

### 1. Allocate next-available IP (IPAM)

- **Method:** `POST`
- **Path:** `/ipam/address?_fields=address,names`
- **Body:**

```json
{
  "space": "<ip-space-id>",
  "next_available_id": "<subnet-resource-id>",
  "comment": "SNOW REQ <req-number>",
  "tags": { "servicenow_request": "<req-number>", "deployment_model": "universal_ddi" }
}
```

### 2. Create the A record

- **Method:** `POST`
- **Path:** `/dns/record`
- **Body:**

```json
{
  "name_in_zone": "app01",
  "zone": "<zone-resource-id>",
  "type": "A",
  "rdata": { "address": "10.10.4.5" },
  "comment": "SNOW REQ <req-number>",
  "tags": { "servicenow_request": "<req-number>" }
}
```

### 3. Create the PTR record

- **Method:** `POST`
- **Path:** `/dns/record`
- **Body:**

```json
{
  "name_in_zone": "5",
  "zone": "<reverse-zone-resource-id>",
  "type": "PTR",
  "rdata": { "dname": "app01.corp.example" },
  "comment": "SNOW REQ <req-number>"
}
```

### 4. Delete on retirement

- **Method:** `DELETE`
- **Path:** `/dns/record/<record-resource-id>` — repeat for the A and PTR ids.
- **Body:** *(none)*
- Then release the address: **`DELETE`** `/ipam/address/<address-resource-id>`.

---

## Wiring notes

- **Idempotency:** on re-run, `record:host`/`record:a` creation returns a `duplicate` WAPI
  error — treat "already exists" as success in the flow, or `GET` first and skip.
- **Result capture:** parse the returned `ipv4addr` / `ips` value into the flow so the
  MID Server validation gate ([`midserver-validate.sh`](./midserver-validate.sh)) can set
  `TEST_FQDN`/`EXPECTED_IP` and confirm the record actually resolves (contract §8, Stage 3).
- **Secrets:** every credential above resolves from an **OCI Vault** secret OCID
  (`admin_password_secret_ocid`, WAPI creds, or `saas_join_token_secret_ocid` for CSP) —
  never inline in the action definition.
- **Extensible attributes → CMDB:** the `ServiceNow Request` EA written here is what the
  Service Graph Connector later reconciles onto the CMDB CI, closing the loop.
