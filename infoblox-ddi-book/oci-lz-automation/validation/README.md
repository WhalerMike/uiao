# Stage 3 — Validation scripts

> **Starter skeleton.** These are real, runnable `bash` (`set -euo pipefail`), but
> every endpoint, WAPI object/field version, FQDN, and CIDR is environment-specific
> and supplied via env vars — nothing is hard-coded to a guess. Confirm WAPI
> object/field names against **your** Grid Master at `<grid-master>/wapidoc/` (over
> HTTPS) before trusting the freshness parsing.

Stage 3 is the pipeline gate. After Stage 2 (this Infoblox DDI module) applies, the
`validate` stage runs these three checks and **fails the pipeline on any non-zero
exit**. Together they answer: *is DNS actually resolving, is OCI→IPAM discovery
current, and is the address space clean?*

## What each check proves

| Script | Proves | Fails when |
|---|---|---|
| `dns-validation.sh` | The DDI anycast VIP (`ddi_anycast_vip`) answers DNS: an enterprise/authoritative A record resolves to its expected IP, and an OCI-owned name (`*.oraclevcn.com`) resolves through the conditional-forward path to the hub VCN OCI resolver LISTENING endpoint (contract §8). | No answer, wrong answer, or an OCI name that returns a public IP (forward path bypassed). |
| `discovery-sync-check.sh` | The OCI→IPAM sync (the API/SDK-driven job using the least-privilege discovery identity, contract §5) completed successfully and recently. | A task is in `ERROR`/`WARNING`/`FAILED` state, or the last successful run is older than `STALE_THRESHOLD_MIN`. |
| `ipam-conflict-check.sh` | The networks in IPAM (including freshly-discovered OCI VCNs/subnets) do not overlap — no two teams or clouds claiming the same CIDR. | Any overlapping or duplicate `network` object is found. |

## OCI-specific candor — discovery is API/SDK-driven

OCI has **no native, event-driven Infoblox discovery connector** (unlike AWS/Azure/GCP).
`discovery-sync-check.sh` therefore reads whatever task/sync-status object your
**API/SDK/Terraform-driven** OCI→IPAM job records (contract §0/§5). If your sync doesn't
write a `vdiscoverytask`-style object, adapt the WAPI object/jq path in the script to
whatever status marker your job leaves behind.

## Grid vs. Universal DDI (boundary-aware)

- **`deployment_model = grid`** (default, boundary-clean): checks talk **NIOS WAPI** on
  the in-tenancy Grid Master (`<grid-master>/wapi/v2.12/…` over HTTPS).
- **`deployment_model = universal_ddi`**: `discovery-sync-check.sh` has a second variant
  (`DDI_API_FLAVOR=universal_ddi`) that queries the **Infoblox Portal (CSP) SaaS** control
  plane at `csp.infoblox.com` — **outside the ATO boundary** (contract §1), only exercised
  when `acknowledge_saas_boundary = true`.

## Required environment variables

Secrets (WAPI/CSP creds) come from **OCI Vault** in the pipeline, never committed. See
each script header for the full contract.

**`dns-validation.sh`**
- `DDI_VIP` (req) — `ddi_anycast_vip` output from Stage 2
- `TEST_FQDN`, `EXPECTED_IP` (req) — enterprise A record + expected answer
- `OCI_FQDN`, `OCI_EXPECTED_IP` (opt) — OCI-owned name forward test
- `DNS_TIMEOUT` (opt, 5), `DNS_PORT` (opt, 53)

**`discovery-sync-check.sh`**
- `DDI_API_FLAVOR` (opt, `nios` | `universal_ddi`; default `nios`)
- `STALE_THRESHOLD_MIN` (opt, default 1440)
- NIOS: `GRID_MASTER`, `INFOBLOX_USERNAME`, `INFOBLOX_PASSWORD`, `WAPI_VERSION` (opt),
  `DISCOVERY_TASK_NAME` (opt), `WAPI_CA_BUNDLE` (opt)
- Universal DDI: `INFOBLOX_CSP_URL` (opt, host-only), `INFOBLOX_CSP_TOKEN` (req)

**`ipam-conflict-check.sh`**
- `GRID_MASTER`, `INFOBLOX_USERNAME`, `INFOBLOX_PASSWORD` (req)
- `WAPI_VERSION` (opt), `NETWORK_VIEW` (opt), `CANDIDATE_NETWORK` (opt), `WAPI_CA_BUNDLE` (opt)

## Invocation from the pipeline `validate` stage

Both runners run the scripts after DDI apply; secrets are injected from OCI Vault,
non-secret inputs from Stage 2 outputs:

```bash
export DDI_VIP="$(terraform -chdir=../terraform output -raw ddi_anycast_vip)"
export GRID_MASTER="$(terraform -chdir=../terraform output -raw grid_master_ip)"

bash validation/dns-validation.sh
bash validation/discovery-sync-check.sh
bash validation/ipam-conflict-check.sh
```

Any script exiting non-zero (`set -euo pipefail` + explicit `fail`) aborts the `validate`
stage, which fails the run. Tooling deps: `curl`, `jq`, and `dig`/`nslookup`.

## Local dependencies

- `bash` 4+ (`mapfile`, `IN()` jq builtin), `curl`, `jq`
- `dig` (bind-utils / dnsutils) preferred, `nslookup` fallback
- Network path from the runner to the DDI VIP / Grid Master / CSP endpoint.
