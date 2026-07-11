#!/usr/bin/env bash
#
# discovery-sync-check.sh — Stage 3 (validation) cloud-discovery freshness gate (OCI).
#
# Proves that the OCI->IPAM synchronisation (the process that syncs OCI
# VCNs/subnets/VNICs into Infoblox IPAM using the least-privilege discovery
# identity from _module-contract.md §5) has completed successfully and recently.
# A stale or errored sync means IPAM no longer reflects OCI reality, so the script
# fails the pipeline `validate` stage.
#
# CANDID (OCI-specific): unlike AWS/Azure/GCP there is NO native, event-driven OCI
# discovery CONNECTOR. The sync is API/SDK/Terraform-driven — a scheduled OCI-SDK
# job or the Infoblox provider running in the provisioning pipeline (contract
# §0/§5). This check reads whatever task/sync-status object that job writes:
#
#   * NIOS Grid (deployment_model=grid, the FedRAMP-Moderate default):
#       WAPI on the Grid Master. If your sync records a `vdiscoverytask`-style
#       object it is read here; field names are version/implementation-specific,
#       so the parsing is intentionally defensive. Confirm against YOUR Grid Master
#       at <grid-master>/wapidoc/ (over HTTPS) before relying on it.
#
#   * Universal DDI / Infoblox Portal (deployment_model=universal_ddi, SaaS —
#       OUTSIDE the ATO boundary, gated on acknowledge_saas_boundary per §1):
#       Cloud Discovery REST API on csp.infoblox.com. Endpoints are illustrative;
#       confirm against the current CSP API docs.
#
# STARTER SKELETON — endpoints, object versions, and field names are
# environment-specific and flagged inline. Nothing is hard-coded to a guess.
#
# ---------------------------------------------------------------------------
# Environment-variable contract
# ---------------------------------------------------------------------------
#   DDI_API_FLAVOR     (optional) "nios" (default) | "universal_ddi".
#   STALE_THRESHOLD_MIN(optional) Max age of last successful sync, minutes.
#                                 Default: 1440 (24h).
#
#   -- NIOS / WAPI variant --
#   GRID_MASTER        (required for nios) Grid Master host/IP (WAPI endpoint).
#   WAPI_VERSION       (optional) Default: v2.12
#   INFOBLOX_USERNAME  (required for nios) WAPI user (read-only is sufficient).
#   INFOBLOX_PASSWORD  (required for nios) WAPI password. Inject from OCI Vault.
#   DISCOVERY_TASK_NAME(optional) Restrict to one sync/discovery task by name.
#   WAPI_CA_BUNDLE     (optional) Path to CA bundle for TLS verify. If unset the
#                                 script verifies against the system trust store.
#                                 (Do NOT disable verification in production.)
#
#   -- Universal DDI / Portal variant --
#   INFOBLOX_CSP_URL   (optional) Default host: csp.infoblox.com (scheme added here)
#   INFOBLOX_CSP_TOKEN (required for universal_ddi) CSP API token. From OCI Vault.
#
# Exit codes: 0 sync fresh & healthy; 1 stale/errored/not found; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

log()  { printf '%s %s\n' "[$(date -u +%FT%TZ)]" "$*"; }
fail() { log "FAIL: $*"; exit 1; }

command -v curl >/dev/null 2>&1 || { log "ERROR: curl not found"; exit 2; }
HAVE_JQ=0; command -v jq >/dev/null 2>&1 && HAVE_JQ=1

DDI_API_FLAVOR="${DDI_API_FLAVOR:-nios}"
STALE_THRESHOLD_MIN="${STALE_THRESHOLD_MIN:-1440}"
NOW_EPOCH="$(date -u +%s)"

# assert_fresh <epoch_seconds> <label>
assert_fresh() {
  local last_epoch="$1" label="$2" age_min
  if ! [[ "${last_epoch}" =~ ^[0-9]+$ ]] || [ "${last_epoch}" -le 0 ]; then
    fail "${label}: could not determine a valid last-success timestamp (got '${last_epoch}')"
  fi
  age_min=$(( (NOW_EPOCH - last_epoch) / 60 ))
  log "${label}: last success $(date -u -d "@${last_epoch}" +%FT%TZ 2>/dev/null || echo "epoch ${last_epoch}") (age ${age_min}m, threshold ${STALE_THRESHOLD_MIN}m)"
  [ "${age_min}" -le "${STALE_THRESHOLD_MIN}" ] || fail "${label}: sync is STALE (${age_min}m > ${STALE_THRESHOLD_MIN}m)"
  log "PASS: ${label} is fresh"
}

# ---------------------------------------------------------------------------
# NIOS / WAPI variant
# ---------------------------------------------------------------------------
check_nios() {
  : "${GRID_MASTER:?set GRID_MASTER (Grid Master WAPI host)}"
  : "${INFOBLOX_USERNAME:?set INFOBLOX_USERNAME}"
  : "${INFOBLOX_PASSWORD:?set INFOBLOX_PASSWORD (inject from OCI Vault)}"
  local ver="${WAPI_VERSION:-v2.12}"
  local base="https://${GRID_MASTER}/wapi/${ver}"

  local -a tls=()
  [ -n "${WAPI_CA_BUNDLE:-}" ] && tls=(--cacert "${WAPI_CA_BUNDLE}")

  # Read the discovery/sync task object your OCI->IPAM job records. `state` is a
  # documented basic field; other fields depend on your implementation — hence
  # the defensive parsing below.
  local url="${base}/vdiscoverytask?_return_fields%2B=name,state,last_run,status,enabled&_return_as_object=1"
  [ -n "${DISCOVERY_TASK_NAME:-}" ] && url="${url}&name=${DISCOVERY_TASK_NAME}"

  log "Querying WAPI ${base} for OCI discovery/sync task objects"
  local resp
  resp="$(curl -fsS "${tls[@]}" -u "${INFOBLOX_USERNAME}:${INFOBLOX_PASSWORD}" \
            -H 'Accept: application/json' "${url}")" \
    || fail "WAPI request failed (auth, TLS, or endpoint). Base: ${base}"

  if [ "${HAVE_JQ}" -eq 0 ]; then
    log "ERROR: jq required to parse WAPI JSON for this check"; exit 2
  fi

  local count
  count="$(jq -r '(.result // []) | length' <<<"${resp}")"
  [ "${count}" != "0" ] || fail "no discovery/sync task objects found (is the OCI->IPAM sync configured? It is API/SDK-driven on OCI — contract §5)"

  local bad
  bad="$(jq -r '(.result // [])[] | select(.state=="ERROR" or .state=="WARNING") | .name' <<<"${resp}")"
  [ -z "${bad}" ] || fail "discovery/sync task(s) in ERROR/WARNING state: ${bad}"

  local last_epoch
  last_epoch="$(jq -r '
    [ (.result // [])[]
      | (.last_run
         // .status.last_completed
         // .status_time
         // empty) ] | map(select(. != null)) | max // 0' <<<"${resp}")"

  if [ "${last_epoch}" = "0" ] || [ "${last_epoch}" = "null" ]; then
    log "WARN: no last-run epoch field present in this WAPI response."
    log "      Falling back to state-only health: all tasks must be COMPLETE/COLLECTION_COMPLETE/IDLE."
    local not_ok
    not_ok="$(jq -r '(.result // [])[] | select(.state|IN("COMPLETE","COLLECTION_COMPLETE","IDLE","READY")|not) | .name' <<<"${resp}")"
    [ -z "${not_ok}" ] || fail "task(s) not in a healthy state: ${not_ok}"
    log "PASS: all ${count} sync task(s) in a healthy state (timestamp freshness not verifiable here)."
    return 0
  fi

  assert_fresh "${last_epoch}" "OCI->IPAM sync (${count} task(s))"
}

# ---------------------------------------------------------------------------
# Universal DDI / Infoblox Portal (SaaS) variant
# ---------------------------------------------------------------------------
check_universal_ddi() {
  # Boundary note: this path talks to the Infoblox Portal SaaS control plane,
  # which is OUTSIDE the ATO boundary (contract §1). Only run when
  # deployment_model=universal_ddi and acknowledge_saas_boundary=true.
  local csp_host="${INFOBLOX_CSP_URL:-csp.infoblox.com}"
  : "${INFOBLOX_CSP_TOKEN:?set INFOBLOX_CSP_TOKEN (CSP API token from OCI Vault)}"

  # Endpoint is illustrative — confirm the current Cloud Discovery path in the CSP
  # API docs for your tenant. Scheme is added here (host-only default var).
  local url="https://${csp_host}/api/clouddiscovery/v2/jobs"
  log "Querying Universal DDI CSP ${csp_host} for cloud-discovery jobs"

  local resp
  resp="$(curl -fsS -H "Authorization: Token ${INFOBLOX_CSP_TOKEN}" \
            -H 'Accept: application/json' "${url}")" \
    || fail "CSP request failed (token, TLS, or endpoint). Host: ${csp_host}"

  if [ "${HAVE_JQ}" -eq 0 ]; then
    log "ERROR: jq required to parse CSP JSON for this check"; exit 2
  fi

  local count
  count="$(jq -r '(.results // .jobs // []) | length' <<<"${resp}")"
  [ "${count}" != "0" ] || fail "no cloud-discovery jobs returned by CSP"

  local bad
  bad="$(jq -r '(.results // .jobs // [])[] | select((.last_run_status // .status)=="FAILED" or (.last_run_status // .status)=="ERROR") | (.name // .id)' <<<"${resp}")"
  [ -z "${bad}" ] || fail "cloud-discovery job(s) failed: ${bad}"

  local last_iso last_epoch
  last_iso="$(jq -r '[ (.results // .jobs // [])[] | (.last_successful_run // .last_run_time // empty) ] | map(select(.!=null)) | sort | last // empty' <<<"${resp}")"
  [ -n "${last_iso}" ] || fail "CSP response had no last-run timestamp field (adjust jq path for your API version)"
  last_epoch="$(date -u -d "${last_iso}" +%s 2>/dev/null || echo 0)"

  assert_fresh "${last_epoch}" "Universal DDI cloud discovery (${count} job(s))"
}

case "${DDI_API_FLAVOR}" in
  nios)          check_nios ;;
  universal_ddi) check_universal_ddi ;;
  *) log "ERROR: DDI_API_FLAVOR must be 'nios' or 'universal_ddi' (got '${DDI_API_FLAVOR}')"; exit 2 ;;
esac

log "Discovery-sync freshness check passed."
