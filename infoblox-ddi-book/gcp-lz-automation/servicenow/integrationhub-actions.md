# IntegrationHub REST Actions — Infoblox WAPI / Universal DDI (GCP DDI package)

> **Starter skeleton — labeled as such.** These are the REST request bodies the
> ServiceNow **IntegrationHub REST** steps issue from the Flow Designer flow
> (see [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md) §Flow and
> the volume chapter [`../../07-servicenow-orchestration.md`](../../07-servicenow-orchestration.md)).
> They drive the same Infoblox calls the GCP module and validation scripts use.
> WAPI object/field names are **version-specific** — confirm against
> `<grid-master>/wapidoc/` (over HTTPS) for your NIOS release before relying on
> them; nothing here is hard-coded to a guess.

## Conventions

- **No scheme in the host placeholder.** The Grid Master host is written as the
  bare placeholder `<grid-master>` (or the MID Server variable `$GRID_MASTER`) —
  **without** an `https://` prefix. The IntegrationHub REST connection record
  supplies the scheme, TLS verification (CA bundle), and port; the flow only
  appends the WAPI path. So a base is `<grid-master>/wapi/v2.12` and a full
  resource path is `<grid-master>/wapi/v2.12/network`.
- **Auth.** NIOS/WAPI uses HTTP Basic auth with a WAPI service credential pulled
  from **Secret Manager** through the MID Server credential store — never inline
  in the flow. Universal DDI (Portal/CSP) uses `Authorization: Token <csp-token>`
  (also from Secret Manager); the CSP host placeholder is `<csp-host>`
  (commercial: `csp.infoblox.com`) — likewise written **without** a scheme.
- **WAPI version.** Paths below use `v2.12` as the placeholder version
  (`WAPI_VERSION` in the validation scripts). Pin the version your Grid supports.
- **Boundary.** The NIOS/WAPI path is **in-boundary** (Grid inside the ATO
  boundary, `deployment_model = grid`). The Universal DDI/CSP path is the
  **out-of-boundary** SaaS case (`deployment_model = universal_ddi`), gated on
  `acknowledge_saas_boundary = true` — see the GCC-Moderate notes in
  `ServiceNow-Orchestration.md`.
- All hosts/paths are **relative placeholders**; no live endpoints are embedded.

---

## Action 1 — Allocate next-available IP (IPAM)

Reserve the next free address in the target network (typically the module's
`ddi_subnet_cidr`, or a spoke/service-project range) and register the host name
in one call. Uses the WAPI `func:nextavailableip` allocation on the `network`
object, embedded in a `record:host` (or `record:a`) create.

**NIOS / WAPI (in-boundary, `deployment_model = grid`)**

- **Method / Path**

  ```
  POST  <grid-master>/wapi/v2.12/record:host?_return_fields%2B=name,ipv4addrs
  ```

- **Body** (allocate next IP from `<network-cidr>`, e.g. the GCP DDI subnet):

  ```json
  {
    "name": "<hostname-fqdn>",
    "ipv4addrs": [
      {
        "ipv4addr": {
          "_object_function": "next_available_ip",
          "_object": "network",
          "_object_parameters": { "network": "<network-cidr>" },
          "_result_field": "ips"
        }
      }
    ],
    "network_view": "default",
    "comment": "Allocated by ServiceNow catalog request <request-number>",
    "extattrs": {
      "gcp_project":   { "value": "<host-project-id>" },
      "gcp_region":    { "value": "<region>" },
      "cmdb_ci":       { "value": "<cmdb-ci-sys-id>" },
      "sn_request":    { "value": "<request-number>" }
    }
  }
  ```

  Response returns the allocated `ipv4addrs[].ipv4addr` — capture it into a flow
  variable for Action 2 (PTR) and for the CMDB reconcile.

**Universal DDI / CSP (out-of-boundary, `deployment_model = universal_ddi`)**

- **Method / Path** (IPAM next-available address; confirm path for your tenant):

  ```
  POST  <csp-host>/api/ddi/v1/ipam/address?_next_available=1
  ```

- **Body**:

  ```json
  {
    "space": "<ip-space-id>",
    "next_available_id": "<subnet-resource-id>",
    "names": [ { "name": "<hostname-fqdn>", "type": "user" } ],
    "tags": {
      "gcp_project": "<host-project-id>",
      "gcp_region":  "<region>",
      "sn_request":  "<request-number>"
    }
  }
  ```

---

## Action 2 — Create A record (+ PTR)

Create the forward A record for the allocated address, and the matching reverse
PTR. (If Action 1 used `record:host`, forward+reverse are created together and
this A-record step is only needed for standalone A records.)

**NIOS / WAPI — create A record**

- **Method / Path**

  ```
  POST  <grid-master>/wapi/v2.12/record:a
  ```

- **Body**:

  ```json
  {
    "name": "<hostname-fqdn>",
    "ipv4addr": "<allocated-ip>",
    "view": "default",
    "comment": "ServiceNow request <request-number>",
    "extattrs": {
      "gcp_project": { "value": "<host-project-id>" },
      "sn_request":  { "value": "<request-number>" }
    }
  }
  ```

**NIOS / WAPI — create PTR record**

- **Method / Path**

  ```
  POST  <grid-master>/wapi/v2.12/record:ptr
  ```

- **Body**:

  ```json
  {
    "ptrdname": "<hostname-fqdn>",
    "ipv4addr": "<allocated-ip>",
    "view": "default",
    "comment": "ServiceNow request <request-number>"
  }
  ```

**Universal DDI / CSP — create A record**

- **Method / Path**

  ```
  POST  <csp-host>/api/ddi/v1/dns/record
  ```

- **Body**:

  ```json
  {
    "name_in_zone": "<hostname-label>",
    "zone": "<zone-resource-id>",
    "type": "A",
    "rdata": { "address": "<allocated-ip>" },
    "comment": "ServiceNow request <request-number>"
  }
  ```

  (Set `"type": "PTR"` with `rdata.dname` = `<hostname-fqdn>` against the reverse
  zone for the PTR.)

---

## Action 3 — Delete (Day-2 retirement / reclaim)

The retirement catalog item calls `terraform destroy` for the infra and reclaims
the DNS/IP objects. WAPI deletes are addressed by the object **reference**
(`_ref`), so a delete is a two-step read-then-delete.

**NIOS / WAPI — find the record reference**

- **Method / Path** (look up the A record by name to get its `_ref`):

  ```
  GET  <grid-master>/wapi/v2.12/record:a?name=<hostname-fqdn>&_return_fields=name,ipv4addr
  ```

  The response is an array of objects each carrying a `_ref` such as
  `record:a/ZG5zLmJpbmRfYQ...:<hostname-fqdn>/default`.

**NIOS / WAPI — delete by reference**

- **Method / Path** (delete the A record; repeat for `record:ptr` / `record:host`):

  ```
  DELETE  <grid-master>/wapi/v2.12/<record-ref>
  ```

- **Body**: none (empty). The `<record-ref>` path segment is the URL-encoded
  `_ref` returned by the GET above.

**NIOS / WAPI — release the IPAM address (fixed reservation, if used)**

- **Method / Path**:

  ```
  DELETE  <grid-master>/wapi/v2.12/<fixedaddress-ref>
  ```

  Look the reference up first with
  `GET <grid-master>/wapi/v2.12/fixedaddress?ipv4addr=<allocated-ip>`.

**Universal DDI / CSP — delete DNS record**

- **Method / Path**:

  ```
  DELETE  <csp-host>/api/ddi/v1/dns/record/<record-resource-id>
  ```

- **Body**: none. Follow with a `DELETE
  <csp-host>/api/ddi/v1/ipam/address/<address-resource-id>` to release the IP.

---

## Summary table

| Action | Flavor | Method | Path (scheme supplied by connection record) |
|---|---|---|---|
| Next-available IP + host | NIOS/WAPI | `POST` | `<grid-master>/wapi/v2.12/record:host` |
| Next-available IP | Universal DDI | `POST` | `<csp-host>/api/ddi/v1/ipam/address?_next_available=1` |
| Create A | NIOS/WAPI | `POST` | `<grid-master>/wapi/v2.12/record:a` |
| Create PTR | NIOS/WAPI | `POST` | `<grid-master>/wapi/v2.12/record:ptr` |
| Create A/PTR | Universal DDI | `POST` | `<csp-host>/api/ddi/v1/dns/record` |
| Find record `_ref` | NIOS/WAPI | `GET` | `<grid-master>/wapi/v2.12/record:a?name=<hostname-fqdn>` |
| Delete record | NIOS/WAPI | `DELETE` | `<grid-master>/wapi/v2.12/<record-ref>` |
| Delete record | Universal DDI | `DELETE` | `<csp-host>/api/ddi/v1/dns/record/<record-resource-id>` |

> Credentials (WAPI Basic auth / CSP token) come from **Secret Manager** via the
> MID Server credential store — see `admin_password_secret_id`,
> `grid_shared_secret_id`, `saas_join_token_secret_id` in
> [`../terraform/variables.tf`](../terraform/variables.tf) and the mapping table
> in [`ServiceNow-Orchestration.md`](./ServiceNow-Orchestration.md).
