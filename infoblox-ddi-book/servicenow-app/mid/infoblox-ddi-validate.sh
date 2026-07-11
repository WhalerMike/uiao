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
