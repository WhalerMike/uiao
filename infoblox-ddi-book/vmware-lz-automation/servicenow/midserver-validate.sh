#!/usr/bin/env bash
#
# midserver-validate.sh — ServiceNow MID Server validation gate (VMware).
#
# Runs this package's three Stage-3 validation scripts (../validation/*.sh) as a
# single post-apply flow gate on the in-boundary MID Server, captures each exit
# code, and emits ONE JSON result object to stdout for the Flow Designer flow to
# parse into work-notes. Exits non-zero if ANY child check fails, so the change
# task fails and returns to approval (see ServiceNow-Orchestration.md, figure
# vmware-sn-01-catalog-flow).
#
# STARTER SKELETON — labeled as such. Secrets (WAPI/CSP creds) and non-secret
# inputs (DDI_VIP, GRID_MASTER, TEST_FQDN, ...) are the SAME env-var contract the
# child scripts document; they are injected by the MID Server credential store /
# Vault / CI, never hard-coded here. See ../validation/README.md.
#
# Typical wiring in the flow (values from Stage-2 Terraform outputs):
#   export DDI_VIP="$(terraform -chdir=../terraform output -raw ddi_anycast_vip)"
#   export GRID_MASTER="$(terraform -chdir=../terraform output -raw grid_master_ip)"
#   ...then this script is invoked; its JSON stdout becomes the gate result.
#
# Exit codes: 0 all checks passed; 1 one or more checks failed; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

# Resolve paths relative to THIS script so it runs from any MID Server workdir.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_DIR="${VALIDATION_DIR:-${SCRIPT_DIR}/../validation}"

# The three Stage-3 gates, run in order. discovery-sync honours DDI_API_FLAVOR
# (nios | universal_ddi) exactly as the child script does.
CHECKS=(
  "dns-validation.sh"
  "discovery-sync-check.sh"
  "ipam-conflict-check.sh"
)

log() { printf '%s %s\n' "[$(date -u +%FT%TZ)]" "$*" >&2; }

# jq is used to assemble the final JSON safely; require it up front (exit 2).
command -v jq >/dev/null 2>&1 || { log "FATAL: jq not found on the MID Server"; exit 2; }

# Per-check result fragments accumulate here as JSON objects.
results_json="[]"
overall_rc=0

for script in "${CHECKS[@]}"; do
  path="${VALIDATION_DIR}/${script}"
  started="$(date -u +%FT%TZ)"

  if [[ ! -f "$path" ]]; then
    log "MISSING: ${path}"
    rc=2
    output="script not found at ${path}"
  else
    log "RUN: ${script}"
    # Capture combined output and the child exit code WITHOUT tripping set -e.
    set +e
    output="$(bash "$path" 2>&1)"
    rc=$?
    set -e
    log "DONE: ${script} rc=${rc}"
  fi

  # Any non-zero child rc fails the overall gate. rc=2 (tooling/usage) is still a
  # failure for gate purposes but is surfaced distinctly in the JSON.
  status="pass"
  if [[ "$rc" -ne 0 ]]; then
    status="fail"
    overall_rc=1
  fi

  finished="$(date -u +%FT%TZ)"
  frag="$(jq -n \
    --arg script "$script" \
    --arg status "$status" \
    --argjson rc "$rc" \
    --arg started "$started" \
    --arg finished "$finished" \
    --arg output "$output" \
    '{script:$script, status:$status, exit_code:$rc, started:$started, finished:$finished, output:$output}')"
  results_json="$(jq -c --argjson f "$frag" '. + [$f]' <<<"$results_json")"
done

overall_status="pass"
[[ "$overall_rc" -eq 0 ]] || overall_status="fail"

# One JSON result object to stdout — this is the MID Server gate payload.
jq -n \
  --arg gate "midserver-validate" \
  --arg flavor "${DDI_API_FLAVOR:-nios}" \
  --arg overall "$overall_status" \
  --arg ts "$(date -u +%FT%TZ)" \
  --argjson checks "$results_json" \
  '{gate:$gate, deployment_model_flavor:$flavor, overall:$overall, timestamp:$ts, checks:$checks}'

exit "$overall_rc"
