#!/usr/bin/env bash
#
# midserver-validate.sh — ServiceNow MID Server validation gate (Azure package).
#
# Runs the three Stage-3 validation scripts this package ships, in sequence,
# captures each exit code, and emits ONE JSON result object to stdout that the
# ServiceNow Flow Designer flow parses into work-notes. The script exits
# non-zero if ANY check failed, so the CPG/IntegrationHub step that invokes it
# marks the change task failed and routes back to the approval/SoD gate.
#
# It is deliberately a thin wrapper: it does NOT re-implement any check. The
# env-var contract below is exactly the union of the contracts documented in
#   ../validation/dns-validation.sh
#   ../validation/discovery-sync-check.sh
#   ../validation/ipam-conflict-check.sh
# so the MID Server credential/parameter mapping stays single-sourced.
#
# STARTER SKELETON — labeled as such. Wire the env vars from the MID Server
# credential store / Azure Key Vault references (see ServiceNow-Orchestration.md
# §GCC-Moderate notes). Nothing is hard-coded.
#
# ---------------------------------------------------------------------------
# Environment-variable contract (passed by the MID Server / flow)
# ---------------------------------------------------------------------------
#   -- DNS check (dns-validation.sh) --
#   DDI_VIP            (required) Anycast VIP / DNS server IP to query
#                                 (Stage-2 output ddi_anycast_vip).
#   TEST_FQDN          (required) Enterprise A record to resolve.
#   EXPECTED_IP        (required) IP TEST_FQDN must return.
#   PRIVATELINK_FQDN / PRIVATELINK_EXPECTED_IP / DNS_TIMEOUT / DNS_PORT (optional)
#
#   -- Discovery-sync check (discovery-sync-check.sh) --
#   DDI_API_FLAVOR     (optional) "nios" (default) | "universal_ddi".
#   STALE_THRESHOLD_MIN(optional) Max sync age in minutes (default 1440).
#   GRID_MASTER        (required for nios) Grid Master WAPI host/IP.
#   WAPI_VERSION       (optional) Default v2.12.
#   INFOBLOX_USERNAME / INFOBLOX_PASSWORD (required for nios) WAPI creds
#                                 (inject from Azure Key Vault via the module's
#                                 *_secret_name variables).
#   DISCOVERY_TASK_NAME / WAPI_CA_BUNDLE (optional)
#   INFOBLOX_CSP_URL / INFOBLOX_CSP_TOKEN (required for universal_ddi)
#
#   -- IPAM conflict check (ipam-conflict-check.sh) --
#   GRID_MASTER / INFOBLOX_USERNAME / INFOBLOX_PASSWORD (required, as above)
#   NETWORK_VIEW       (optional) Restrict to a network view.
#   CANDIDATE_NETWORK  (optional) CIDR to test (e.g. ddi_subnet_address_prefix).
#
#   -- Wrapper-only --
#   VALIDATION_DIR     (optional) Path to the validation scripts. Default:
#                                 the sibling ../validation relative to this file.
#   CHECK_LOG_DIR      (optional) Directory for per-check stderr/stdout logs.
#                                 Default: a mktemp dir (logs referenced in notes).
#
# Output (stdout): a single JSON object, e.g.
#   {"overall":"fail","checks":[
#     {"name":"dns-validation","exit":0},
#     {"name":"discovery-sync-check","exit":1},
#     {"name":"ipam-conflict-check","exit":0}]}
#
# Exit codes: 0 all checks passed; 1 one or more checks failed; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

# Resolve the validation directory relative to THIS script unless overridden.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VALIDATION_DIR="${VALIDATION_DIR:-${SCRIPT_DIR}/../validation}"
CHECK_LOG_DIR="${CHECK_LOG_DIR:-$(mktemp -d 2>/dev/null || echo /tmp)}"

log() { printf '%s %s\n' "[$(date -u +%FT%TZ)]" "$*" >&2; }

# The three checks, in gate order. Names double as the JSON "name" values.
CHECKS=(
  "dns-validation:dns-validation.sh"
  "discovery-sync-check:discovery-sync-check.sh"
  "ipam-conflict-check:ipam-conflict-check.sh"
)

# Preflight: every script must exist and be executable.
for spec in "${CHECKS[@]}"; do
  file="${spec#*:}"
  path="${VALIDATION_DIR}/${file}"
  [ -f "${path}" ] || { log "ERROR: validation script not found: ${path}"; exit 2; }
done

overall="pass"
json_checks=""

run_check() {
  # run_check <name> <script-file> -> sets global rc; appends a JSON fragment.
  local name="$1" file="$2" path rc
  path="${VALIDATION_DIR}/${file}"
  log "RUN ${name} (${path})"
  # Each check inherits the exported env-var contract. Capture combined output
  # to a per-check log the flow can attach; never abort the wrapper on failure
  # (we want ALL results in one JSON object), hence the guarded invocation.
  set +e
  bash "${path}" >"${CHECK_LOG_DIR}/${name}.log" 2>&1
  rc=$?
  set -e
  log "DONE ${name} exit=${rc} (log: ${CHECK_LOG_DIR}/${name}.log)"
  [ "${rc}" -eq 0 ] || overall="fail"
  # Append comma-separated JSON object fragment.
  local frag
  frag=$(printf '{"name":"%s","exit":%d}' "${name}" "${rc}")
  if [ -z "${json_checks}" ]; then
    json_checks="${frag}"
  else
    json_checks="${json_checks},${frag}"
  fi
}

for spec in "${CHECKS[@]}"; do
  run_check "${spec%%:*}" "${spec#*:}"
done

# Single JSON result object to stdout for ServiceNow to parse into work-notes.
printf '{"overall":"%s","checks":[%s]}\n' "${overall}" "${json_checks}"

[ "${overall}" = "pass" ] || exit 1
exit 0
