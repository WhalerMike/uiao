# Azure Gold Exemplar — the one deployment everything else is patterned on

This is the volume's answer to its own top finding
([REVIEW §2.2](../REVIEW-AND-IMPROVEMENTS.md)): pick **one** platform, make it a
**tested, worked reference** with committed inputs, a machine-checked contract, and a
real validation transcript — then let the other four platforms and the ServiceNow
mock-ups be explicitly *patterned on it* rather than each claiming independent maturity.

Azure (`deployment_model = "grid"`, `gcc-moderate`) is that exemplar.

> **What is real in this repo vs. what you run to certify.** Everything needed to
> deploy and validate is committed here, and the parts that *can* be checked without a
> cloud are checked in CI. But a repository cannot stand up Azure, Infoblox, and
> ServiceNow — the **live apply, the validation transcript, the ServiceNow screenshots,
> and the ATF run happen in your environment.** This doc is the kit + the checklist to
> get there; it does **not** claim to have been deployed. Sections marked _“paste yours”_
> are where the evidence lands once you run it.

## What is already proven in-repo (CI-enforced)

| Claim | How it's proven | Where |
|---|---|---|
| The module is valid HCL | `terraform validate` → `Success! The configuration is valid` | book CI, `Terraform fmt + validate (advisory)` job |
| There is a concrete, complete input set | committed worked example (every required variable) | [`terraform/terraform.tfvars.example`](./terraform/terraform.tfvars.example) |
| The catalog form collects every **required** module variable | `contract_check.py` asserts required-vars ⊆ form `<map_to>` (fails CI on drift) | [`../servicenow-app/catalog/`](../servicenow-app/catalog/variable-set-azure-ddi-subnet.xml), book CI `Catalog↔module contract check` |
| The scripts/Script Includes parse | `bash -n`, `node --check` | book CI `Shell + JS static checks` |

That is the difference between "looks right" and "provably consistent" — short of a live
apply, which is the next section.

## What you run to certify (in your environment)

### 1. Prerequisites
- A **Stage-1 ALZ Accelerator** landing zone (connectivity hub VNet, Key Vault). Read its
  outputs into `terraform.tfvars` — do not invent `hub_*` / `key_vault_id`.
- vNIOS Marketplace image accepted; VM SKU quota confirmed (see
  [`../01-azure.md`](../01-azure.md) §4).
- Secrets present in the referenced Key Vault (admin password, grid shared secret, …).

### 2. Two-phase apply (infra, then DDI objects)
The `azurerm` resources build the plumbing; the `infoblox` provider needs a **reachable
Grid/WAPI endpoint**, so DDI objects apply in a second phase once the members are up and
joined. Keep the phases explicit:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars    # then edit with your Stage-1 outputs
terraform init                                   # remote-state backend recommended

# Phase 1 — Azure plumbing + members (subnet, NSG, vNIOS, discovery identity)
terraform apply \
  -target=azurerm_subnet.ddi -target=azurerm_network_security_group.ddi \
  -target=azurerm_linux_virtual_machine.grid            # adjust to the module's resource names

# ... wait for members to boot and join the Grid (WAPI reachable) ...

# Phase 2 — Infoblox DDI objects (zone forwarders, IPAM networks)
terraform apply                                          # full apply now resolves the infoblox provider
```

Capture the plan/apply output — that is the first piece of certification evidence.

### 3. Validate (the same three checks the gate runs)
Run the package's validation scripts (also the ServiceNow MID gate); all must pass:

```bash
cd ../validation
./dns-validation.sh          # a record resolves via an Infoblox member + a privatelink name
./discovery-sync-check.sh    # Azure VNets/subnets/tags synced into IPAM
./ipam-conflict-check.sh     # no overlap between discovered Azure reality and IPAM
```

See [`validation/README.md`](./validation/README.md) for the env vars each expects.

### 4. Certification checklist
Complete every box, then this exemplar is "certified in your environment":

- [ ] `terraform validate` clean (already green in CI; re-confirm in your backend).
- [ ] Phase-1 apply created the subnet, NSG (default-deny + contract ports), and ≥2 members cross-AZ.
- [ ] Members joined the Grid (or enrolled to the Portal for `universal_ddi`); WAPI reachable.
- [ ] Phase-2 apply created the conditional forwarders + IPAM networks.
- [ ] `dns-validation.sh` · `discovery-sync-check.sh` · `ipam-conflict-check.sh` all pass — transcript captured.
- [ ] ServiceNow: the catalog item built from [`../servicenow-app/catalog/`](../servicenow-app/catalog/variable-set-azure-ddi-subnet.xml), one request driven end-to-end (approve → apply → allocate → gate → CMDB → close) per the [build playbook](../servicenow-app/PLAYBOOK-servicenow-led-build.md).
- [ ] The `cmdb_ci_ip_network` CI appeared, correlated by `servicenow_sys_id`.
- [ ] The ATF happy-path test passes on your sub-prod instance (once authored — see REVIEW §2.4).
- [ ] Real screenshots captured to replace the illustrative mock-ups for *this* platform.

### 5. Record the evidence _(paste yours)_

```
Verified against: NIOS vX.Y.Z · infobloxopen/infoblox provider v2.__ · azurerm v4.__
Date: ____-__-__   Operator: ______   Instance/region: ______

<paste terraform apply summary>
<paste dns-validation / discovery-sync / ipam-conflict transcript (overall: pass)>
<paste ServiceNow RITM number + closed-complete confirmation>
```

## After certification: relabel

Once Azure is certified in your environment:
- Keep the "starter skeleton" banners on the **other four** packages (AWS/GCP/OCI/VMware)
  and add "patterned on the certified Azure exemplar."
- Replace the illustrative ServiceNow mock-ups
  ([`../servicenow-app/mockups/`](../servicenow-app/mockups/README.md)) for Azure with real
  screenshots (keep the mock-ups for the not-yet-certified platforms).
- Update [REVIEW §2.2](../REVIEW-AND-IMPROVEMENTS.md) to move the gold-exemplar item from
  "open" to "done (Azure)".

---

## Sources & cross-references

- [`terraform/terraform.tfvars.example`](./terraform/terraform.tfvars.example) · [`terraform/README.md`](./terraform/README.md)
- [`../servicenow-app/catalog/variable-set-azure-ddi-subnet.xml`](../servicenow-app/catalog/variable-set-azure-ddi-subnet.xml) · [`contract_check.py`](../servicenow-app/catalog/contract_check.py)
- [Azure automation guide](./Azure-ALZ-Infoblox-DDI-Automation-Guide.md) · [step-by-step runbook](./Azure-ALZ-DDI-Step-by-Step-Runbook.md)
- [Chapter 8 — ServiceNow-Led Implementation](../08-servicenow-led-implementation.md) · [build playbook](../servicenow-app/PLAYBOOK-servicenow-led-build.md)
- [REVIEW-AND-IMPROVEMENTS.md](../REVIEW-AND-IMPROVEMENTS.md)
