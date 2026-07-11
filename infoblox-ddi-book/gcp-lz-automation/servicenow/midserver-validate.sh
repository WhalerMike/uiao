#!/usr/bin/env bash
#
# midserver-validate.sh — ServiceNow MID Server validation gate for the GCP DDI
# module. This is the post-apply gate the Flow Designer flow runs on the MID
# Server (inside the ATO boundary) after the CPG Terraform Connector applies
# ../terraform. It runs the package's three Stage-3 validation scripts under
# ../validation, captures each exit code, and emits ONE JSON result object to
# stdout so the flow can parse pass/fail and post the reason to the change
# work-notes. The wrapper exits non-zero if ANY check fails, which fails the
# ServiceNow change (contract: non-zero exit → change fails).
#
# STARTER SKELETON — labeled as such. Each underlying script reads its own
# environment-variable contract (see that script's header + ../validation/
# README.md and ../servicenow/integrationhub-actions.md). This wrapper injects
# nothing; the MID Server credential/parameter mapping supplies GRID_MASTER,
# INFOBLOX_USERNAME/PASSWORD (from Secret Manager), DDI_VIP, TEST_FQDN, etc.
#
# ---------------------------------------------------------------------------
# Wrapper environment variables (all optional)
#   VALIDATION_DIR   Path to the validation scripts. Default: ../validation
#                    resolved relative to this script's location.
#   SKIP_CHECKS      Space/comma-separated basenames to skip (e.g.
#                    "discovery-sync-check.sh"). Skipped checks report
#                    status "skipped" and do not affect the exit code.
# Exit codes: 0 all executed checks passed; 1 one or more failed; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

# Resolve this script's directory so ../validation works regardless of CWD
# (the MID Server may invoke the script from an arbitrary working directory).
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
VALIDATION_DIR="${VALIDATION_DIR:-${SCRIPT_DIR}/../validation}"

# The three Stage-3 gates, run in order. Order is deliberate: prove DNS answers,
# then that discovery is fresh, then that IPAM has no conflicts.
CHECKS=(
  "dns-validation.sh"
  "discovery-sync-check.sh"
  "ipam-conflict-check.sh"
)

if [ ! -d "${VALIDATION_DIR}" ]; then
  printf '{"schema":"gcp-ddi-midserver-validate/v1","status":"error","error":"validation dir not found: %s"}\n' "${VALIDATION_DIR}"
  exit 2
fi

# json_escape <string> — minimal JSON string escaping for embedding log tails.
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/}"
  s="${s//$'\t'/\\t}"
  printf '%s' "${s}"
}

# Normalize SKIP_CHECKS (commas -> spaces) for word-membership testing.
skip_list=" ${SKIP_CHECKS:-} "
skip_list="${skip_list//,/ }"

started_at="$(date -u +%FT%TZ)"
overall_rc=0
results_json=""

for check in "${CHECKS[@]}"; do
  path="${VALIDATION_DIR}/${check}"

  if [[ "${skip_list}" == *" ${check} "* ]]; then
    entry="{\"check\":\"${check}\",\"status\":\"skipped\",\"exit_code\":null}"
    results_json="${results_json:+${results_json},}${entry}"
    continue
  fi

  if [ ! -x "${path}" ]; then
    # Missing/non-executable script is a tooling failure for that gate.
    entry="{\"check\":\"${check}\",\"status\":\"fail\",\"exit_code\":2,\"detail\":\"not found or not executable\"}"
    results_json="${results_json:+${results_json},}${entry}"
    overall_rc=1
    continue
  fi

  # Run the check, capturing combined output and its exit code WITHOUT letting
  # set -e abort the wrapper (we want to run every gate and report all of them).
  rc=0
  output="$(bash "${path}" 2>&1)" || rc=$?

  # Keep only the last line of output as a compact reason for the JSON payload
  # (the validation scripts print a FAIL:/PASS summary line last).
  tail_line="$(printf '%s' "${output}" | tail -n 1)"
  status="pass"
  if [ "${rc}" -ne 0 ]; then
    status="fail"
    overall_rc=1
  fi

  entry="{\"check\":\"${check}\",\"status\":\"${status}\",\"exit_code\":${rc},\"detail\":\"$(json_escape "${tail_line}")\"}"
  results_json="${results_json:+${results_json},}${entry}"
done

finished_at="$(date -u +%FT%TZ)"
overall_status="pass"
[ "${overall_rc}" -ne 0 ] && overall_status="fail"

# One JSON result object to stdout (single line — easy for a MID Server /
# Flow Designer JSON parser to consume). Diagnostic logs went to stderr above.
printf '{"schema":"gcp-ddi-midserver-validate/v1","status":"%s","started_at":"%s","finished_at":"%s","checks":[%s]}\n' \
  "${overall_status}" "${started_at}" "${finished_at}" "${results_json}"

exit "${overall_rc}"
