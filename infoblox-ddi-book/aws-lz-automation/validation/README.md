# Stage 3 — Validation scripts

> **Starter skeleton.** These are real, runnable `bash` (`set -euo pipefail`),
> but every endpoint, WAPI object/field version, FQDN, and CIDR is
> environment-specific and supplied via env vars — nothing is hard-coded to a
> guess. Confirm WAPI object/field names against **your** Grid Master at
> `<grid-master>/wapidoc/` (over HTTPS) before trusting the freshness parsing.

Stage 3 is the pipeline gate. After Stage 2 (this Infoblox DDI module) applies,
the `validate` stage runs these three checks and **fails the pipeline on any
non-zero exit**. Together they answer: *is DNS actually resolving, is AWS→IPAM
discovery current, and is the address space clean?* They are the same scripts as
the Azure package's Stage 3, with AWS-specific comments — the env-var contracts
are identical for cross-cloud parity.

## What each check proves

| Script | Proves | Fails when |
|---|---|---|
| `dns-validation.sh` | The DDI anycast VIP (contract output `ddi_anycast_vip`) answers DNS: an enterprise/authoritative A record resolves to its expected IP, and an AWS-service / forwarded name resolves through the conditional-forward path to the Route 53 Resolver inbound endpoint (contract §8). | No answer, wrong answer, or a forwarded name that returns a public IP (forward path bypassed). |
| `discovery-sync-check.sh` | Infoblox cloud-discovery / vDiscovery (the AWS→IPAM sync using the least-privilege cross-account discovery role, contract §5) completed successfully and recently. | A task is in `ERROR`/`WARNING`/`FAILED` state, or the last successful run is older than `STALE_THRESHOLD_MIN`. |
| `ipam-conflict-check.sh` | The networks in IPAM (including freshly-discovered AWS VPCs/subnets) do not overlap — no two teams or clouds claiming the same CIDR. | Any overlapping or duplicate `network` object is found (server-side candidate query or whole-view pairwise scan). |

## Grid vs. Universal DDI (boundary-aware)

- **`deployment_model = grid`** (default, boundary-clean for GCC-Moderate):
  discovery-sync and IPAM checks talk **NIOS WAPI** on the in-account Grid Master
  (`<grid-master>/wapi/v2.12/…` over HTTPS). This is the default code path.
- **`deployment_model = universal_ddi`**: `discovery-sync-check.sh` has a second
  variant (`DDI_API_FLAVOR=universal_ddi`) that queries the **Infoblox Portal
  (CSP) SaaS** control plane at `csp.infoblox.com`. That endpoint is **outside the
  ATO boundary** (contract §1) and should only be exercised when
  `acknowledge_saas_boundary = true`. The pipeline passes the flavor through.

## Required environment variables

Secrets (WAPI/CSP creds) come from **AWS Secrets Manager** (or SSM Parameter
Store) in the pipeline, never committed. See each script header for the full
contract.

**`dns-validation.sh`**
- `DDI_VIP` (req) — `ddi_anycast_vip` output from Stage 2
- `TEST_FQDN`, `EXPECTED_IP` (req) — enterprise A record + expected answer
- `PRIVATELINK_FQDN`, `PRIVATELINK_EXPECTED_IP` (opt) — an AWS-service / Route 53
  private-zone name that must resolve through the DDI forward path (var name kept
  for cross-cloud parity with the Azure package)
- `DNS_TIMEOUT` (opt, 5), `DNS_PORT` (opt, 53)

**`discovery-sync-check.sh`**
- `DDI_API_FLAVOR` (opt, `nios` | `universal_ddi`; default `nios`)
- `STALE_THRESHOLD_MIN` (opt, default 1440)
- NIOS: `GRID_MASTER`, `INFOBLOX_USERNAME`, `INFOBLOX_PASSWORD`,
  `WAPI_VERSION` (opt), `DISCOVERY_TASK_NAME` (opt), `WAPI_CA_BUNDLE` (opt)
- Universal DDI: `INFOBLOX_CSP_URL` (opt), `INFOBLOX_CSP_TOKEN` (req)

**`ipam-conflict-check.sh`**
- `GRID_MASTER`, `INFOBLOX_USERNAME`, `INFOBLOX_PASSWORD` (req)
- `WAPI_VERSION` (opt), `NETWORK_VIEW` (opt), `CANDIDATE_NETWORK` (opt),
  `WAPI_CA_BUNDLE` (opt)

## Invocation from the pipeline `validate` stage

Both CI examples run the scripts after DDI apply; secrets are injected from
Secrets Manager, non-secret inputs from Stage 2 remote-state outputs:

```bash
export DDI_VIP="$(terraform -chdir=../terraform output -raw ddi_anycast_vip)"
export GRID_MASTER="$(terraform -chdir=../terraform output -raw grid_master_ip)"

bash validation/dns-validation.sh
bash validation/discovery-sync-check.sh
bash validation/ipam-conflict-check.sh
```

Any script exiting non-zero (`set -euo pipefail` + explicit `fail`) aborts the
`validate` stage, which fails the run. Tooling deps: `curl`, `jq`, and
`dig`/`nslookup` (present on the CI runners; see pipeline README).

## Local dependencies

- `bash` 4+ (`mapfile`, `IN()` jq builtin), `curl`, `jq`
- `dig` (bind-utils / dnsutils) preferred, `nslookup` fallback
- Network path from the runner to the DDI VIP / Grid Master / CSP endpoint.
