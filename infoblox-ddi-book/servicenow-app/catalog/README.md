# Catalog variable sets + the form↔module contract

The "Request a DDI-backed subnet" catalog form, expressed as a **machine-readable**
variable set per platform, plus the test that keeps it honest.

| Platform | Variable set |
|---|---|
| Azure | [`variable-set-azure-ddi-subnet.xml`](./variable-set-azure-ddi-subnet.xml) |
| AWS | [`variable-set-aws-ddi-subnet.xml`](./variable-set-aws-ddi-subnet.xml) |
| Google Cloud | [`variable-set-gcp-ddi-subnet.xml`](./variable-set-gcp-ddi-subnet.xml) |
| Oracle Cloud | [`variable-set-oci-ddi-subnet.xml`](./variable-set-oci-ddi-subnet.xml) |
| VMware | [`variable-set-vmware-ddi-subnet.xml`](./variable-set-vmware-ddi-subnet.xml) |

Each `<item_option_new>` (a catalog variable) carries a `<map_to>` naming the Terraform
module variable it feeds. Secrets and connection endpoints that must **never** be typed
into the form (e.g. VMware's `vsphere_password`, `nsx_password`, `admin_password`) are
declared `<resolved_by_mid>` — the in-boundary MID Server resolves them via the credential
alias instead.

## The contract test (blocking in CI)

[`contract_check.py`](./contract_check.py) asserts that **every required module variable**
(a `variable "x" {}` with no `default` in each package's `terraform/variables.tf`) is
covered — as a `<map_to>` form field **or** a `<resolved_by_mid>` entry — for all five
platforms. It runs as a **blocking** step in
[`.github/workflows/infoblox-ddi-book-checks.yml`](../../../.github/workflows/infoblox-ddi-book-checks.yml),
so the requester-facing form and the modules cannot silently drift.

```
$ python3 servicenow-app/catalog/contract_check.py
[azure ] required= 9 form= 9 mid= 0 -> OK
[aws   ] required=10 form=10 mid= 0 -> OK
[gcp   ] required= 9 form= 9 mid= 0 -> OK
[oci   ] required=12 form=10 mid= 2 -> OK
[vmware] required=16 form= 9 mid= 7 -> OK
```

**Starter skeletons:** set the real ServiceNow `type` codes and reference qualifiers on
import, and turn Stage-1-sourced fields into reference lookups so requesters can't
free-type infrastructure identifiers. See the
[build playbook](../PLAYBOOK-servicenow-led-build.md) Phase 2 and each package's
`servicenow/ServiceNow-Orchestration.md`.
