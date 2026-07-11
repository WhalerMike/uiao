# IntegrationHub REST Actions — Infoblox WAPI / Universal DDI (AWS package)

> **Scope.** The exact REST request bodies the ServiceNow **IntegrationHub REST**
> steps issue against Infoblox for the AWS DDI module — *allocate-next-available-IP*,
> *create A + PTR*, and *delete-on-reclaim* (Day-2). Two control planes are covered,
> selected by the module's [`deployment_model`](../terraform/variables.tf) variable:
> **NIOS Grid** (WAPI, the GCC-Moderate default) and **Universal DDI** (Infoblox
> Portal / CSP, SaaS — outside the ATO boundary, see the boundary note at the end).
>
> **Starter skeleton — labeled as such.** WAPI object/field names are
> version-specific; confirm against `<grid-master>/wapidoc/` for your NIOS release.
> Nothing here is a certified payload.

## Placeholder / connection conventions

These are the values the IntegrationHub **Connection & Credential alias** and the
flow's input variables supply. Host placeholders are written **without an
`https://` scheme** — IntegrationHub's REST connection record holds the scheme and
base host; the action steps below carry only host + path.

| Placeholder | Meaning | Source |
|---|---|---|
| `<grid-master>` / `$GRID_MASTER` | Grid Master WAPI host/IP | module input / Stage-1 |
| `$WAPI_VERSION` | WAPI version, e.g. `v2.12` | default `v2.12` (matches `../validation/*`) |
| `$INFOBLOX_USERNAME` / `$INFOBLOX_PASSWORD` | WAPI basic-auth credential | **AWS Secrets Manager** via MID Server |
| `<csp-host>` / `$INFOBLOX_CSP_URL` | Universal DDI Portal host (`csp.infoblox.com`) | `deployment_model=universal_ddi` |
| `$INFOBLOX_CSP_TOKEN` | CSP API token | AWS Secrets Manager |
| `$NETWORK` | Parent CIDR to allocate from (a `ddi_subnet_cidrs` entry) | catalog request |
| `$NETWORK_VIEW` | Network view, e.g. `default` | catalog request (optional) |
| `$FQDN` | Record name, e.g. `app01.corp.example.com` | catalog request |
| `$DNS_VIEW` | Authoritative DNS view, e.g. `default` | catalog request (optional) |

Auth: NIOS uses **HTTP Basic** (`$INFOBLOX_USERNAME:$INFOBLOX_PASSWORD`); Universal
DDI uses header `Authorization: Token $INFOBLOX_CSP_TOKEN`. TLS is verified against
the system/MID-Server trust store — never disabled.

---

## 1. Allocate next-available IP

Reserve the next free address in a `ddi_subnet_cidrs` CIDR. Two-step on NIOS: the
allocation happens as part of creating the object that will own the IP (here a host/A
record) using the `func:nextavailableip` value, so the address is never orphaned.

### NIOS / WAPI

Allocate **and** bind to a new A record in one call (the address is chosen by the
Grid, returned in the create response):

```
POST <grid-master>/wapi/$WAPI_VERSION/record:a
Content-Type: application/json
Authorization: Basic <base64($INFOBLOX_USERNAME:$INFOBLOX_PASSWORD)>

{
  "name": "$FQDN",
  "view": "$DNS_VIEW",
  "ipv4addr": "func:nextavailableip:$NETWORK,$NETWORK_VIEW",
  "comment": "ServiceNow REQ allocation (aws-lz-automation)",
  "extattrs": {
    "Source":        {"value": "ServiceNow"},
    "aws_account_id":{"value": "$AWS_ACCOUNT_ID"},
    "aws_region":    {"value": "$AWS_REGION"}
  }
}
```

To reserve an address **without** a name yet (fixed reservation), request an empty
`network`'s next IP and store it on a `network`/`ipv4address` object instead:

```
POST <grid-master>/wapi/$WAPI_VERSION/network/<network-ref>?_function=next_available_ip
Content-Type: application/json

{ "num": 1 }
```

Response: `{ "ips": ["10.10.4.7"] }` — capture `ips[0]` into the flow variable.

### Universal DDI (Portal / CSP)

```
POST <csp-host>/api/ddi/v1/ipam/address
Content-Type: application/json
Authorization: Token $INFOBLOX_CSP_TOKEN

{
  "space":       "$IP_SPACE_ID",
  "parent":      "$NETWORK",
  "next_available_id": "$SUBNET_RESOURCE_ID",
  "comment":     "ServiceNow REQ allocation (aws-lz-automation)",
  "tags": { "Source": "ServiceNow", "aws_region": "$AWS_REGION" }
}
```

---

## 2. Create A + PTR records

Forward (A) and reverse (PTR) for the allocated address. If step 1 created the A
record via `func:nextavailableip`, this step adds the matching PTR; otherwise create
both explicitly with the captured IP `$IPV4ADDR`.

### NIOS / WAPI

A record (explicit IP):

```
POST <grid-master>/wapi/$WAPI_VERSION/record:a
Content-Type: application/json

{
  "name":     "$FQDN",
  "ipv4addr": "$IPV4ADDR",
  "view":     "$DNS_VIEW",
  "comment":  "ServiceNow REQ (aws-lz-automation)"
}
```

PTR record (reverse):

```
POST <grid-master>/wapi/$WAPI_VERSION/record:ptr
Content-Type: application/json

{
  "ptrdname": "$FQDN",
  "ipv4addr": "$IPV4ADDR",
  "view":     "$DNS_VIEW",
  "comment":  "ServiceNow REQ (aws-lz-automation)"
}
```

Each create returns the object `_ref` (e.g. `record:a/ZG5z...:app01.corp.example.com/default`).
**Store both `_ref` strings on the ServiceNow request** — they are the handles the
reclaim step (§3) deletes.

### Universal DDI (Portal / CSP)

```
POST <csp-host>/api/ddi/v1/dns/record
Content-Type: application/json
Authorization: Token $INFOBLOX_CSP_TOKEN

{
  "name_in_zone": "$HOSTNAME",
  "zone":         "$ZONE_ID",
  "type":         "A",
  "rdata":        { "address": "$IPV4ADDR" }
}
```

Repeat with `"type": "PTR"` and `"rdata": { "dname": "$FQDN" }` against the reverse
zone. Capture each returned `id`.

---

## 3. Delete on reclaim (Day-2 retirement)

Fired by the **retirement** catalog item alongside `terraform destroy`. Delete the
DNS records first, then release the IPAM lease/reservation so the address returns to
the pool.

### NIOS / WAPI

Delete by the stored `_ref` (A, then PTR):

```
DELETE <grid-master>/wapi/$WAPI_VERSION/$RECORD_A_REF
Authorization: Basic <base64($INFOBLOX_USERNAME:$INFOBLOX_PASSWORD)>
```

```
DELETE <grid-master>/wapi/$WAPI_VERSION/$RECORD_PTR_REF
```

Release a fixed reservation / address object (if one was created in §1):

```
DELETE <grid-master>/wapi/$WAPI_VERSION/$FIXEDADDRESS_REF
```

A successful DELETE returns the deleted `_ref`. A `404`/empty `_ref` means the object
was already reclaimed — treat as idempotent success in the flow.

### Universal DDI (Portal / CSP)

```
DELETE <csp-host>/api/ddi/v1/dns/record/$RECORD_ID
Authorization: Token $INFOBLOX_CSP_TOKEN
```

```
DELETE <csp-host>/api/ddi/v1/ipam/address/$ADDRESS_ID
```

---

## Boundary note

The **NIOS / WAPI** column keeps every call **inside the ATO boundary** (MID Server →
Grid Master over the in-boundary network) — the GCC-Moderate default. The **Universal
DDI (CSP)** column targets the Infoblox Portal SaaS control plane, which is **outside**
the boundary and is gated in the module by
[`acknowledge_saas_boundary`](../terraform/variables.tf). Only wire the CSP action
steps when `deployment_model = universal_ddi` and that acknowledgement is set. See
[`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md) and the volume chapter
[`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md) §7.4.
