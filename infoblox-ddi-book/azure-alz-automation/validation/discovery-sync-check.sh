#!/usr/bin/env bash
#
# discovery-sync-check.sh — Stage 3 (validation) cloud-discovery freshness gate.
#
# Proves that Infoblox's Azure cloud-discovery / vDiscovery job (the process
# that syncs Azure VNets/subnets/NICs into Infoblox IPAM using the least-
# privilege discovery identity from _module-contract.md §5) has completed
# successfully and recently. A stale or errored sync means IPAM no longer
# reflects Azure reality, so the script fails the pipeline `validate` stage.
#
# Two control planes exist and are queried differently — BOTH variants are
# implemented below and selected by DDI_API_FLAVOR:
#
#   * NIOS Grid (deployment_model=grid, the GCC-Moderate default):
#       WAPI on the Grid Master, object `vdiscoverytask`. Fields such as
#       `state` and the last-run timestamp are read to judge freshness.
#       NOTE: WAPI object/field names are version-specific. `state` is
#       documented (IDLE/RUNNING/COMPLETE/WARNING/ERROR/...); the exact
#       "last successful run" epoch field name varies by NIOS/WAPI release
#       (e.g. exposed via `_return_fields+=last_run` or a task status object).
#       Confirm against YOUR Grid Master at https://<gm>/wapidoc/ before relying
#       on it. The parsing below is intentionally defensive.
#
#   * Universal DDI / Infoblox Portal (deployment_model=universal_ddi, SaaS —
#       OUTSIDE the ATO boundary, gated on acknowledge_saas_boundary per §1):
#       Cloud Discovery REST API on csp.infoblox.com. Endpoint/paths shown are
#       illustrative; confirm against the current CSP API docs.
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
#   INFOBLOX_PASSWORD  (required for nios) WAPI password. Inject from Key Vault.
#   DISCOVERY_TASK_NAME(optional) Restrict to one vdiscoverytask by name.
#   WAPI_CA_BUNDLE     (optional) Path to CA bundle for TLS verify. If unset the
#                                 script verifies against the system trust store.
#                                 (Do NOT disable verification in production.)
#
#   -- Universal DDI / Portal variant --
#   INFOBLOX_CSP_URL   (optional) Default: https://csp.infoblox.com
#   INFOBLOX_CSP_TOKEN (required for universal_ddi) CSP API token. From Key Vault.
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
  : "${INFOBLOX_PASSWORD:?set INFOBLOX_PASSWORD (inject from Key Vault)}"
  local ver="${WAPI_VERSION:-v2.12}"
  local base="https://${GRID_MASTER}/wapi/${ver}"

  local -a tls=()
  [ -n "${WAPI_CA_BUNDLE:-}" ] && tls=(--cacert "${WAPI_CA_BUNDLE}")

  # Request the discovery task(s). `state` is a documented basic field; we also
  # ask for common status/timestamp fields, but which ones exist depends on the
  # NIOS/WAPI version — hence the defensive parsing below.
  local url="${base}/vdiscoverytask?_return_fields%2B=name,state,last_run,status,enabled&_return_as_object=1"
  [ -n "${DISCOVERY_TASK_NAME:-}" ] && url="${url}&name=${DISCOVERY_TASK_NAME}"

  log "Querying WAPI ${base} for vdiscoverytask objects"
  local resp
  resp="$(curl -fsS "${tls[@]}" -u "${INFOBLOX_USERNAME}:${INFOBLOX_PASSWORD}" \
            -H 'Accept: application/json' "${url}")" \
    || fail "WAPI request failed (auth, TLS, or endpoint). Base: ${base}"

  if [ "${HAVE_JQ}" -eq 0 ]; then
    log "ERROR: jq required to parse WAPI JSON for this check"; exit 2
  fi

  local count
  count="$(jq -r '(.result // []) | length' <<<"${resp}")"
  [ "${count}" != "0" ] || fail "no vdiscoverytask objects found (is Azure cloud discovery configured?)"

  # Reject any task in an error/warning state.
  local bad
  bad="$(jq -r '(.result // [])[] | select(.state=="ERROR" or .state=="WARNING") | .name' <<<"${resp}")"
  [ -z "${bad}" ] || fail "vdiscovery task(s) in ERROR/WARNING state: ${bad}"

  # Freshness: prefer an explicit epoch field if the version exposes one,
  # otherwise fall back to a nested status timestamp. Field name is
  # environment-specific — adjust the jq path for your NIOS release.
  local last_epoch
  last_epoch="$(jq -r '
    [ (.result // [])[]
      | (.last_run
         // .status.last_completed
         // .status_time
         // empty) ] | map(select(. != null)) | max // 0' <<<"${resp}")"

  if [ "${last_epoch}" = "0" ] || [ "${last_epoch}" = "null" ]; then
    log "WARN: no last-run epoch field present in this WAPI version's response."
    log "      Falling back to state-only health: all tasks must be COMPLETE/COLLECTION_COMPLETE/IDLE."
    local not_ok
    not_ok="$(jq -r '(.result // [])[] | select(.state|IN("COMPLETE","COLLECTION_COMPLETE","IDLE","READY")|not) | .name' <<<"${resp}")"
    [ -z "${not_ok}" ] || fail "task(s) not in a healthy state: ${not_ok}"
    log "PASS: all ${count} vdiscovery task(s) in a healthy state (timestamp freshness not verifiable on this WAPI version)."
    return 0
  fi

  assert_fresh "${last_epoch}" "NIOS vDiscovery (${count} task(s))"
}

# ---------------------------------------------------------------------------
# Universal DDI / Infoblox Portal (SaaS) variant
# ---------------------------------------------------------------------------
check_universal_ddi() {
  # Boundary note: this path talks to the Infoblox Portal SaaS control plane,
  # which is OUTSIDE the ATO boundary (contract §1). It should only run when
  # deployment_model=universal_ddi and acknowledge_saas_boundary=true.
  local csp="${INFOBLOX_CSP_URL:-https://csp.infoblox.com}"
  : "${INFOBLOX_CSP_TOKEN:?set INFOBLOX_CSP_TOKEN (CSP API token from Key Vault)}"

  # Endpoint is illustrative — confirm the current Cloud Discovery path/shape in
  # the CSP API docs for your tenant. The intent: list discovery jobs and read
  # each job's last-run result + timestamp.
  local url="${csp}/api/clouddiscovery/v2/jobs"
  log "Querying Universal DDI CSP ${csp} for cloud-discovery jobs"

  local resp
  resp="$(curl -fsS -H "Authorization: Token ${INFOBLOX_CSP_TOKEN}" \
            -H 'Accept: application/json' "${url}")" \
    || fail "CSP request failed (token, TLS, or endpoint). Base: ${csp}"

  if [ "${HAVE_JQ}" -eq 0 ]; then
    log "ERROR: jq required to parse CSP JSON for this check"; exit 2
  fi

  # Defensive parse: job list key and field names are illustrative.
  local count
  count="$(jq -r '(.results // .jobs // []) | length' <<<"${resp}")"
  [ "${count}" != "0" ] || fail "no cloud-discovery jobs returned by CSP"

  local bad
  bad="$(jq -r '(.results // .jobs // [])[] | select((.last_run_status // .status)=="FAILED" or (.last_run_status // .status)=="ERROR") | (.name // .id)' <<<"${resp}")"
  [ -z "${bad}" ] || fail "cloud-discovery job(s) failed: ${bad}"

  # Timestamps are ISO-8601 in CSP; convert the newest to epoch.
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
