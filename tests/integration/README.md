# `tests/integration/` — Tier-1 Live-Tenant Tests

Per [UIAO_131 §3.1](../../src/uiao/canon/specs/adapter-test-strategy.md),
tier-1 tests are **live calls against the vendor's commercial cloud or
developer-program tenant**. They are the strongest evidence the substrate
emits, but they require credentials and run only when those credentials are
present.

This directory is **plumbing only** unless the relevant credentials are set.
Every test in `tier1/` calls `pytest.skip(...)` when its required environment
variables are absent, so `pytest tests/integration/` is always green — it
just does nothing useful without secrets.

## Tier separation

| Tier | Where | Trigger | Network |
|---|---|---|---|
| **Tier-1** — live | `tests/integration/tier1/` | manual `workflow_dispatch` (today); nightly cron once creds are wired | Yes — vendor tenant |
| **Tier-2** — contract | `tests/fixtures/contract/<adapter>/*.yaml` consumed by `tests/contract/test_<adapter>_contract.py` (separate PR) | every PR via `pytest.yml` | No |
| **Tier-3** — reference deployment | Agency tenant; evidence bundle lives outside this repo | Quarterly, per agency | Yes |

## Why "plumbing-only" lands first

Vendor sandbox / developer-program access is gated on signup, account
verification, license assignment, and (for Palo Alto and CyberArk) sales
engagement. Those are wall-clock weeks at minimum. Landing the test
scaffolding now means: when creds arrive, the work is filling in API request
bodies and golden assertions — not bootstrapping the entire test layout.

## Required environment variables (per adapter)

Each `test_<adapter>_tier1.py` declares its required environment variables
at module top. Tests skip when any of them is missing.

### service-now (ServiceNow Personal Developer Instance / PDI)

```
SERVICENOW_PDI_INSTANCE      # bare hostname, e.g. devNNNNNN.service-now.com
SERVICENOW_PDI_USER
SERVICENOW_PDI_PASSWORD
```

Sign-up: developer.servicenow.com (free PDI; Yokohama or later).

### palo-alto (PAN-OS eval VM or XSOAR developer)

```
PANOS_HOST                   # full URL of the eval VM, RFC1918 inside the dev VPC
PANOS_API_KEY
```

Access paths:
- PAN-OS eval ISO from Palo Alto support portal (account required).
- Stand up a PAN-OS VM in a developer Azure subscription via Terraform.

**Runner-reachability decision required before populating secrets.** The
default `runs-on: ubuntu-latest` runner cannot reach RFC1918 addresses
inside a dev VPC. Pick one before wiring `PANOS_HOST`:

- **Self-hosted runner inside the VPC** (preferred — keeps the PAN-OS
  management plane private). Change `runs-on:` in
  `.github/workflows/tier1-palo-alto.yml` to a self-hosted label.
- **Public eval VM with a non-RFC1918 IP**. Requires IP-allowlist on
  the firewall and a short-lived `PANOS_API_KEY` — exposes the
  management plane to the internet.
- **Tunnel** (Tailscale, Cloudflare Tunnel) added as a step before
  `Run tier-1`. Tunnels add their own auth surface and operational
  burden.

Track the choice in an ADR and update the workflow header + `runs-on:`
once resolved.

### cyberark (CyberArk Privilege Cloud trial)

```
CYBERARK_TENANT              # bare hostname, e.g. <slug>.privilegecloud.cyberark.cloud
CYBERARK_CLIENT_ID
CYBERARK_CLIENT_SECRET
CYBERARK_TEST_SAFE           # required by test_rotation_simulation only;
                             # name of a dedicated rotation-test Safe.
                             # Other tier-1 tests skip cleanly without it.
```

Access: cyberark.com — search for the Privilege Cloud trial program.

`CYBERARK_TEST_SAFE` is intentionally a separate opt-in: the rotation
simulation mutates account state, so the operator must name the Safe
explicitly to confirm intent. Provision a dedicated Safe in the trial
tenant (e.g. `uiao-tier1-rotation`) and never point this at production.

## Running locally

Tier-1 tests run only against accounts you own. **Do not** point them at a
production tenant.

```bash
# All tier-1 (skipped without creds; safe to run blind):
pytest tests/integration/tier1/ -v

# One adapter:
pytest tests/integration/tier1/test_service_now_tier1.py -v

# With credentials sourced from a local .env (gitignored):
set -a; source .env.tier1; set +a
pytest tests/integration/tier1/test_service_now_tier1.py -v
```

## CI workflows

Each adapter has a manual-dispatch workflow under
`.github/workflows/tier1-<adapter>.yml`. Today these run only when triggered
from the Actions tab. Once a repo secret is added for the adapter, the
follow-on PR adds a `schedule:` block (nightly cron) and the job becomes
continuous.

Each workflow checks for the relevant secrets at job start and exits 0 with
a clear log message when they're absent. Tests run inside a dedicated job
step which itself calls `pytest -m tier1 --no-header`; pytest's skip output
handles the per-test missing-cred reporting.

## Recording responses for tier-2 promotion

A helper in `conftest.py` (`record_response`) writes successful tier-1
responses to a temp directory. After a clean tier-1 run, those captures can
be sanitized (per `tests/fixtures/contract/README.md` §sanitization rules)
and promoted to tier-2 fixtures. The recorder is *opt-in* via
`UIAO_TIER1_RECORD=1` so production runs don't accidentally write to disk.

## What this directory does NOT do

- It does not call vendor APIs without explicit credentials.
- It does not assert behavior in a way that would suggest tier-1 has been
  achieved — the registry status of `service-now`, `palo-alto`, `cyberark`
  remains EXCLUDED from the tier-1 conformance gate until evidence lands.
- It does not commit captured responses. Promoted tier-2 fixtures are a
  separate, reviewed PR per adapter.

## Cross-references

- [UIAO_131 §3.1 Tier-1 definition](../../src/uiao/canon/specs/adapter-test-strategy.md)
- [UIAO_131 §5.1 Tier-1 exclusion criteria](../../src/uiao/canon/specs/adapter-test-strategy.md)
- [Roadmap §2.1–2.3](../../docs/docs/uiao-substrate-roadmap.md)
- [Tier-2 contract fixtures README](../fixtures/contract/README.md)
- [Adapter conformance template UIAO_121](../../src/uiao/canon/specs/adapter-conformance-test-plan-template.md)
- [Adapter integration template UIAO_123](../../src/uiao/canon/specs/adapter-integration-test-plan.md)
