#!/usr/bin/env bash
# MID Server validation wrapper for the Infoblox DDI ServiceNow app.
# Runs the three per-platform validation scripts and emits ONE JSON verdict line
# to stdout for InfobloxDDIGate to parse. Non-zero exit if any check fails.
#
# Deploy this alongside the per-platform validation/ scripts on the MID Server
# host (default dir: /opt/servicenow/mid/agent/scripts/ddi). Point SCRIPTS_DIR at
# the platform whose change is being validated (azure/aws/gcp/oci/vmware).
#
# Env contract (set by InfobloxDDIGate from the request + credential alias):
#   SCRIPTS_DIR  DDI_VIP TEST_FQDN EXPECTED_IP GRID_MASTER INFOBLOX_USERNAME
#   INFOBLOX_PASSWORD WAPI_VERSION DDI_API_FLAVOR STALE_THRESHOLD_MIN ...
# STARTER SKELETON.
set -uo pipefail

# SER-1 companion change. InfobloxDDIGate._buildInvocation no longer exports
# env vars via unescaped `export k=v` string concatenation (command injection,
# see Script Include header) -- it passes the whole env map as one opaque
# base64-encoded JSON argument instead. Decode it here and export only the
# allowlisted names, via plain assignment (never eval/re-parsed as shell).
ENV_B64=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-b64) ENV_B64="${2:-}"; shift 2 ;;
    *) echo "unexpected argument: $1" >&2; exit 2 ;;
  esac
done
if [[ -n "$ENV_B64" ]]; then
  ALLOWED="SCRIPTS_DIR DDI_VIP TEST_FQDN EXPECTED_IP PRIVATELINK_FQDN \
           PRIVATELINK_EXPECTED_IP GRID_MASTER INFOBLOX_USERNAME \
           INFOBLOX_PASSWORD WAPI_VERSION DDI_API_FLAVOR \
           STALE_THRESHOLD_MIN DNS_TIMEOUT DNS_PORT"
  ENV_JSON="$(printf '%s' "$ENV_B64" | base64 -d)"
  for name in $ALLOWED; do
    value="$(printf '%s' "$ENV_JSON" | jq -r --arg n "$name" '.[$n] // empty')"
    [[ -n "$value" ]] && export "$name=$value"      # assignment, never eval
  done
  unset ENV_B64 ENV_JSON
fi
# SER-7 is NOT closed by the above: INFOBLOX_PASSWORD is still exported here
# and inherited by the three child scripts below, visible in
# /proc/<pid>/environ to the same user. Closing that needs a coordinated
# 0600-temp-file change across this script and the three validation/*.sh
# scripts it invokes -- deliberately not done here, see the patch notes.

SCRIPTS_DIR="${SCRIPTS_DIR:-./validation}"
declare -a NAMES=(dns-validation discovery-sync-check ipam-conflict-check)
declare -a RESULTS=()
overall="pass"

for n in "${NAMES[@]}"; do
  s="${SCRIPTS_DIR}/${n}.sh"
  if [[ -x "$s" || -f "$s" ]]; then
    bash "$s" >/dev/null 2>&1
    code=$?
  else
    code=127   # script missing on the MID host
  fi
  [[ "$code" -ne 0 ]] && overall="fail"
  RESULTS+=("{\"name\":\"${n}\",\"exit\":${code}}")
done

# single-line JSON verdict (stdout only — logs go to stderr)
printf '{"overall":"%s","checks":[%s]}\n' "$overall" "$(IFS=,; echo "${RESULTS[*]}")"
[[ "$overall" == "pass" ]] || exit 1
