#!/usr/bin/env bash
#
# midserver-validate.sh — ServiceNow MID Server validation gate for the AWS DDI
# module. Runs the three Stage-3 validation scripts that ship with this package
# (../validation/) as a single post-apply flow gate, captures each script's exit
# code, and emits ONE machine-readable JSON result to stdout that a Flow Designer
# flow can parse into work-notes and a pass/fail branch.
#
#   ../validation/dns-validation.sh        DNS resolution proof
#   ../validation/discovery-sync-check.sh  cloud-discovery freshness
#   ../validation/ipam-conflict-check.sh   IPAM overlap/conflict scan
#
# The wrapper does NOT set any of the per-check environment variables itself —
# it inherits them from the MID Server / Flow Designer execution context (which
# injects Grid credentials from AWS Secrets Manager and the request's tfvars-
# derived values). See ServiceNow-Orchestration.md for the variable list each
# child script requires (DDI_VIP, TEST_FQDN, GRID_MASTER, INFOBLOX_USERNAME, ...).
#
# STARTER SKELETON — labeled as such. Runnable as-is; wire the env-var injection
# on your MID Server. Nothing is hard-coded to a guess.
#
# Output contract (stdout is JSON ONLY; human logs go to stderr):
#   {
#     "overall": "pass" | "fail",
#     "generated": "<UTC ISO-8601>",
#     "checks": [
#       {"name":"dns-validation","script":"../validation/dns-validation.sh",
#        "exit_code":0,"status":"pass"},
#       ...
#     ]
#   }
#
# Exit codes: 0 all checks passed (overall=pass); 1 one or more checks failed
#             (overall=fail); 2 a wrapper/tooling error (bad path, unreadable).
# ---------------------------------------------------------------------------

set -euo pipefail

# Resolve paths relative to THIS script so it runs from any CWD (the MID Server
# work directory is not guaranteed to be servicenow/).
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_DIR="${VALIDATION_DIR:-${SCRIPT_DIR}/../validation}"

# Human-readable progress goes to stderr so stdout stays pure JSON.
log() { printf '%s %s\n' "[$(date -u +%FT%TZ)]" "$*" >&2; }

# The three child gates, in run order. Keys are the JSON `name` values; values
# are the script basenames under $VALIDATION_DIR.
CHECK_NAMES=("dns-validation" "discovery-sync" "ipam-conflict")
CHECK_SCRIPTS=("dns-validation.sh" "discovery-sync-check.sh" "ipam-conflict-check.sh")

# JSON string escaper (backslash, double-quote, control chars) so paths/labels
# are safe to embed without pulling in jq as a hard dependency.
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  printf '%s' "${s}"
}

overall_rc=0
checks_json=""

for i in "${!CHECK_NAMES[@]}"; do
  name="${CHECK_NAMES[$i]}"
  script_path="${VALIDATION_DIR}/${CHECK_SCRIPTS[$i]}"
  rel_path="../validation/${CHECK_SCRIPTS[$i]}"

  if [ ! -f "${script_path}" ]; then
    log "ERROR: validation script not found: ${script_path}"
    # Tooling/config error — emit a minimal JSON so the flow still gets a body.
    printf '{"overall":"error","generated":"%s","checks":[],"error":"%s"}\n' \
      "$(date -u +%FT%TZ)" "$(json_escape "missing script: ${rel_path}")"
    exit 2
  fi

  log "Running ${name} gate (${rel_path})"
  # Run the child gate. It streams its own [timestamp] logs to stdout; redirect
  # those to stderr so they don't corrupt this wrapper's JSON stdout. Disable
  # errexit around the call so a non-zero child does not abort the wrapper — we
  # want to run every gate and report all of them.
  set +e
  bash "${script_path}" >&2
  rc=$?
  set -e

  if [ "${rc}" -eq 0 ]; then
    status="pass"
  else
    status="fail"
    overall_rc=1
  fi
  log "Gate ${name} exited ${rc} (${status})"

  entry="$(printf '{"name":"%s","script":"%s","exit_code":%d,"status":"%s"}' \
    "$(json_escape "${name}")" "$(json_escape "${rel_path}")" "${rc}" "${status}")"
  if [ -z "${checks_json}" ]; then
    checks_json="${entry}"
  else
    checks_json="${checks_json},${entry}"
  fi
done

if [ "${overall_rc}" -eq 0 ]; then
  overall="pass"
else
  overall="fail"
fi

# Single JSON document to stdout — the ONLY thing on stdout.
printf '{"overall":"%s","generated":"%s","checks":[%s]}\n' \
  "${overall}" "$(date -u +%FT%TZ)" "${checks_json}"

log "Validation gate overall=${overall}"
exit "${overall_rc}"
