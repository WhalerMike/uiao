#!/usr/bin/env bash
#
# ipam-conflict-check.sh — Stage 3 (validation) IPAM overlap/conflict gate.
#
# Proves that the networks Infoblox knows about (including those just synced from
# GCP by cloud discovery) do not overlap or conflict. Overlapping CIDRs in IPAM
# are the classic symptom of two teams claiming the same address space, or a GCP
# VPC subnet colliding with an on-prem/enterprise supernet — either of which will
# cause routing/DNS breakage. Any conflict fails the pipeline `validate` stage.
#
# Strategy (NIOS WAPI, deployment_model=grid — the GCC-Moderate default):
#   1. If CANDIDATE_NETWORK is set, ask WAPI for networks that overlap it — the
#      authoritative, server-side answer for "does my new subnet collide with
#      anything already in IPAM?".
#   2. Otherwise, enumerate all `network` objects in the (optional) NETWORK_VIEW
#      and detect pairwise CIDR overlaps locally. This catches pre-existing
#      overlaps across the whole view.
#
# STARTER SKELETON — WAPI object/modifier names are version-specific and flagged
# inline. Confirm against <grid-master>/wapidoc/ (over HTTPS) for your release.
#
# ---------------------------------------------------------------------------
# Environment-variable contract  (identical to the Azure package for drop-in parity)
# ---------------------------------------------------------------------------
#   GRID_MASTER        (required) Grid Master host/IP (WAPI endpoint).
#   WAPI_VERSION       (optional) Default: v2.12
#   INFOBLOX_USERNAME  (required) WAPI user (read-only is sufficient).
#   INFOBLOX_PASSWORD  (required) WAPI password. Inject from Secret Manager.
#   NETWORK_VIEW       (optional) Restrict to a network view, e.g. "default".
#   CANDIDATE_NETWORK  (optional) A single CIDR to test for overlap against IPAM
#                                 (e.g. the ddi_subnet or a new spoke range).
#                                 If set, uses the server-side overlap query.
#   WAPI_CA_BUNDLE     (optional) CA bundle for TLS verify (system trust if unset;
#                                 never disable verification in production).
#
# Exit codes: 0 no conflicts; 1 overlap/conflict found; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

log()  { printf '%s %s\n' "[$(date -u +%FT%TZ)]" "$*"; }
fail() { log "FAIL: $*"; exit 1; }

command -v curl >/dev/null 2>&1 || { log "ERROR: curl not found"; exit 2; }
command -v jq   >/dev/null 2>&1 || { log "ERROR: jq required to parse WAPI JSON"; exit 2; }

: "${GRID_MASTER:?set GRID_MASTER (Grid Master WAPI host)}"
: "${INFOBLOX_USERNAME:?set INFOBLOX_USERNAME}"
: "${INFOBLOX_PASSWORD:?set INFOBLOX_PASSWORD (inject from Secret Manager)}"

WAPI_VERSION="${WAPI_VERSION:-v2.12}"
BASE="https://${GRID_MASTER}/wapi/${WAPI_VERSION}"
declare -a TLS=(); [ -n "${WAPI_CA_BUNDLE:-}" ] && TLS=(--cacert "${WAPI_CA_BUNDLE}")
VIEW_Q=""; [ -n "${NETWORK_VIEW:-}" ] && VIEW_Q="&network_view=${NETWORK_VIEW}"

wapi_get() {
  # wapi_get <path+query> -> raw JSON body (fails the script on HTTP error)
  curl -fsS "${TLS[@]}" -u "${INFOBLOX_USERNAME}:${INFOBLOX_PASSWORD}" \
       -H 'Accept: application/json' "${BASE}/$1" \
    || fail "WAPI request failed for /$1 (auth, TLS, or endpoint). Base: ${BASE}"
}

# --- ipcalc-free CIDR overlap math (IPv4) ------------------------------------
# ip_to_int a.b.c.d -> integer
ip_to_int() {
  local IFS=. ; read -r a b c d <<<"$1"
  echo $(( (a<<24) + (b<<16) + (c<<8) + d ))
}
# cidr_bounds a.b.c.d/nn -> "network_int broadcast_int"
cidr_bounds() {
  local cidr="$1" ip mask base_int size
  ip="${cidr%/*}"; mask="${cidr#*/}"
  base_int="$(ip_to_int "${ip}")"
  size=$(( 1 << (32 - mask) ))
  local net=$(( base_int & ~(size - 1) & 0xFFFFFFFF ))
  echo "${net} $(( net + size - 1 ))"
}
# overlaps A B -> 0 if CIDRs A and B overlap
overlaps() {
  read -r a1 a2 <<<"$(cidr_bounds "$1")"
  read -r b1 b2 <<<"$(cidr_bounds "$2")"
  [ "${a1}" -le "${b2}" ] && [ "${b1}" -le "${a2}" ]
}

conflicts=0

if [ -n "${CANDIDATE_NETWORK:-}" ]; then
  # ----- Mode 1: server-side overlap query for one candidate CIDR ------------
  # WAPI supports searching networks that contain / are contained by a CIDR.
  # The exact modifier is version-specific; `network~` (regex) is NOT an overlap
  # test. Common approaches:
  #   - GET network?contains_address=<ip>            (single address)
  #   - GET network?network_container=<cidr>         (children of a container)
  # There is no single universal "overlaps" modifier across all versions, so we
  # fetch candidates near the CANDIDATE_NETWORK and confirm overlap locally.
  log "Mode 1: testing CANDIDATE_NETWORK=${CANDIDATE_NETWORK} for overlap in IPAM"
  resp="$(wapi_get "network?_return_fields%2B=network,comment&_max_results=10000${VIEW_Q}")"
  mapfile -t nets < <(jq -r '.[].network' <<<"${resp}")
  for n in "${nets[@]}"; do
    [ "${n}" = "${CANDIDATE_NETWORK}" ] && continue
    if overlaps "${CANDIDATE_NETWORK}" "${n}"; then
      log "CONFLICT: candidate ${CANDIDATE_NETWORK} overlaps existing IPAM network ${n}"
      conflicts=$((conflicts+1))
    fi
  done
  [ "${conflicts}" -eq 0 ] && log "PASS: ${CANDIDATE_NETWORK} does not overlap any of ${#nets[@]} IPAM networks"
else
  # ----- Mode 2: whole-view pairwise overlap scan ----------------------------
  log "Mode 2: scanning all networks${NETWORK_VIEW:+ in view ${NETWORK_VIEW}} for pairwise overlaps"
  resp="$(wapi_get "network?_return_fields%2B=network,comment&_max_results=10000${VIEW_Q}")"
  mapfile -t nets < <(jq -r '.[].network' <<<"${resp}")
  count="${#nets[@]}"
  log "Fetched ${count} network object(s)"
  [ "${count}" -gt 1 ] || { log "PASS: ${count} network(s) — nothing to compare"; exit 0; }

  for ((i=0; i<count; i++)); do
    for ((j=i+1; j<count; j++)); do
      # Distinct entries with the identical CIDR are also a conflict (duplicate
      # declaration), and overlaps() returns true for them too.
      if overlaps "${nets[i]}" "${nets[j]}"; then
        log "CONFLICT: ${nets[i]} overlaps ${nets[j]}"
        conflicts=$((conflicts+1))
      fi
    done
  done
  [ "${conflicts}" -eq 0 ] && log "PASS: no overlapping networks among ${count} entries"
fi

if [ "${conflicts}" -gt 0 ]; then
  fail "${conflicts} IPAM network conflict(s) detected"
fi
log "IPAM conflict check passed."
