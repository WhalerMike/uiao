#!/usr/bin/env bash
#
# midserver-validate.sh — ServiceNow MID Server post-apply validation gate (OCI).
#
# STARTER SKELETON — labeled as such. Runnable bash, but the endpoints, FQDNs,
# CIDRs, and credentials are environment-specific and supplied via env vars /
# OCI Vault by the Flow Designer flow; nothing is hard-coded to a guess.
#
# Role in the loop (see ServiceNow-Orchestration.md, step 5):
#   After the CPG Terraform Connector applies ../terraform, the Flow Designer flow
#   invokes this wrapper ON THE MID SERVER (inside the OCI ATO boundary). It runs
#   the three Stage-3 validation scripts in ../validation, captures each exit code,
#   and emits ONE machine-readable JSON result object to stdout for the flow to
#   parse into work-notes and the change record. Any failing check makes this
#   wrapper exit non-zero, which fails the ServiceNow change (gate returns to
#   approval).
#
# The three checks are the SAME scripts the pipeline `validate` stage runs — this
# wrapper is only the ServiceNow-facing adapter (single JSON result, aggregate
# exit code). It invents no new validation logic.
#
# ---------------------------------------------------------------------------
# Environment-variable contract (passed in by the flow; secrets from OCI Vault)
# ---------------------------------------------------------------------------
#   Consumed by the wrapped scripts (see ../validation/README.md for the full
#   list and each script header for details). Typically wired from Stage 2
#   Terraform outputs + OCI Vault:
#     DDI_VIP, TEST_FQDN, EXPECTED_IP                (dns-validation.sh)
#     OCI_FQDN, OCI_EXPECTED_IP                      (optional, dns-validation.sh)
#     DDI_API_FLAVOR, STALE_THRESHOLD_MIN            (discovery-sync-check.sh)
#     GRID_MASTER, INFOBLOX_USERNAME, INFOBLOX_PASSWORD, WAPI_VERSION,
#     WAPI_CA_BUNDLE, NETWORK_VIEW, CANDIDATE_NETWORK (WAPI scripts)
#     INFOBLOX_CSP_URL, INFOBLOX_CSP_TOKEN           (universal_ddi variant)
#
#   Wrapper-only knobs:
#     VALIDATION_DIR  (optional) Path to the validation scripts.
#                                Default: <this-dir>/../validation
#     SN_CHANGE_ID    (optional) ServiceNow change/request number, echoed into the
#                                JSON so the flow can correlate the result.
#
# Output: exactly one JSON object on stdout. All human/log lines from the wrapped
#         scripts are redirected to stderr so stdout stays parseable.
# Exit codes: 0 all checks passed; 1 one or more checks failed; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
VALIDATION_DIR="${VALIDATION_DIR:-${SCRIPT_DIR}/../validation}"
SN_CHANGE_ID="${SN_CHANGE_ID:-}"
STARTED_AT="$(date -u +%FT%TZ)"

log() { printf '%s %s\n' "[$(date -u +%FT%TZ)] midserver-validate" "$*" >&2; }

# The three Stage-3 checks, run in dependency order (DNS, then sync, then IPAM).
CHECKS=(
  "dns-validation.sh"
  "discovery-sync-check.sh"
  "ipam-conflict-check.sh"
)

# json_escape <string> — minimal JSON string escaping (quotes, backslash, control).
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/ }"
  s="${s//$'\r'/ }"
  s="${s//$'\t'/ }"
  printf '%s' "${s}"
}

if [ ! -d "${VALIDATION_DIR}" ]; then
  log "ERROR: validation dir not found: ${VALIDATION_DIR}"
  printf '{"schema":"oci-ddi-midserver-validate/v1","status":"error","reason":"validation dir not found: %s"}\n' \
    "$(json_escape "${VALIDATION_DIR}")"
  exit 2
fi

overall_rc=0
results_json=""
sep=""

for check in "${CHECKS[@]}"; do
  path="${VALIDATION_DIR}/${check}"
  log "running ${check}"

  if [ ! -x "${path}" ] && [ ! -f "${path}" ]; then
    log "ERROR: check not found: ${path}"
    rc=2
    tail="check script not found"
  else
    # Capture the last line of stderr as a short reason; never let a non-zero
    # exit abort the loop (we aggregate). `|| rc=$?` disarms `set -e` per check.
    err_file="$(mktemp)"
    rc=0
    bash "${path}" >"${err_file}.out" 2>"${err_file}" || rc=$?
    tail="$(tail -n 1 "${err_file}" 2>/dev/null || true)"
    [ -n "${tail}" ] || tail="$(tail -n 1 "${err_file}.out" 2>/dev/null || true)"
    # Surface the wrapped script's own logs on the MID Server's stderr for audit.
    cat "${err_file}" >&2 || true
    rm -f "${err_file}" "${err_file}.out"
  fi

  if [ "${rc}" -eq 0 ]; then
    status="pass"
  else
    status="fail"
    [ "${overall_rc}" -eq 2 ] || overall_rc=1
    [ "${rc}" -ne 2 ] || overall_rc=2
  fi

  log "${check} -> ${status} (exit ${rc})"
  results_json="${results_json}${sep}{\"check\":\"$(json_escape "${check}")\",\"status\":\"${status}\",\"exit_code\":${rc},\"detail\":\"$(json_escape "${tail}")\"}"
  sep=","
done

if [ "${overall_rc}" -eq 0 ]; then
  overall_status="pass"
elif [ "${overall_rc}" -eq 2 ]; then
  overall_status="error"
else
  overall_status="fail"
fi

FINISHED_AT="$(date -u +%FT%TZ)"

# One JSON result object to stdout — the ONLY thing on stdout.
printf '{"schema":"oci-ddi-midserver-validate/v1","change_id":"%s","status":"%s","started_at":"%s","finished_at":"%s","checks":[%s]}\n' \
  "$(json_escape "${SN_CHANGE_ID}")" \
  "${overall_status}" \
  "${STARTED_AT}" \
  "${FINISHED_AT}" \
  "${results_json}"

exit "${overall_rc}"
