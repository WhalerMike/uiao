#!/usr/bin/env bash
#
# dns-validation.sh — Stage 3 (validation) DNS resolution check (OCI).
#
# Proves that the Infoblox DDI members deployed by Stage 2 are actually answering
# DNS for (a) an enterprise/authoritative A record and (b) an OCI-owned name
# (e.g. *.oraclevcn.com) that the DDI members conditionally forward to the hub VCN
# OCI resolver LISTENING endpoint (see _module-contract.md §8).
#
# The query is aimed at the DDI anycast VIP (contract output `ddi_anycast_vip`).
# On any mismatch or resolver failure the script exits non-zero so the pipeline
# `validate` stage fails the run.
#
# STARTER SKELETON — labeled as such. The FQDNs, expected IPs, and VIP are
# environment-specific and MUST be supplied by the caller; nothing is hard-coded.
#
# ---------------------------------------------------------------------------
# Environment-variable contract
# ---------------------------------------------------------------------------
#   DDI_VIP            (required) Anycast VIP / DNS server IP to query. This is
#                                 Stage 2 output `ddi_anycast_vip` (or one of
#                                 `dns_server_ips`).
#   TEST_FQDN          (required) Enterprise A record to resolve, e.g.
#                                 app01.corp.example
#   EXPECTED_IP        (required) IP that TEST_FQDN must resolve to.
#   OCI_FQDN           (optional) An OCI-owned name to resolve through the DDI
#                                 conditional-forward path, e.g.
#                                 app.<subnet>.<vcn>.oraclevcn.com
#   OCI_EXPECTED_IP    (optional) Expected private IP for OCI_FQDN. If OCI_FQDN is
#                                 set but this is unset, the script asserts only
#                                 that resolution succeeds and returns a private
#                                 (RFC1918) A.
#   DNS_TIMEOUT        (optional) Per-query timeout seconds. Default: 5
#   DNS_PORT           (optional) DNS port. Default: 53
#
# Exit codes: 0 all asserted answers matched; 1 a check failed; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

log()  { printf '%s %s\n' "[$(date -u +%FT%TZ)]" "$*"; }
fail() { log "FAIL: $*"; exit 1; }

: "${DDI_VIP:?set DDI_VIP to the DDI anycast VIP / DNS server IP}"
: "${TEST_FQDN:?set TEST_FQDN to the enterprise A record to resolve}"
: "${EXPECTED_IP:?set EXPECTED_IP to the address TEST_FQDN must return}"
DNS_TIMEOUT="${DNS_TIMEOUT:-5}"
DNS_PORT="${DNS_PORT:-53}"

# Pick an available resolver tool. `dig` is preferred (scriptable +short);
# fall back to `nslookup` where dig is unavailable (some minimal images).
if command -v dig >/dev/null 2>&1; then
  RESOLVER="dig"
elif command -v nslookup >/dev/null 2>&1; then
  RESOLVER="nslookup"
else
  log "ERROR: neither dig nor nslookup found in PATH"; exit 2
fi
log "Using resolver tool: ${RESOLVER}; querying VIP ${DDI_VIP}:${DNS_PORT}"

# resolve_a <fqdn> -> prints newline-separated A answers (may be empty)
resolve_a() {
  local fqdn="$1"
  if [ "${RESOLVER}" = "dig" ]; then
    dig +short +time="${DNS_TIMEOUT}" +tries=1 -p "${DNS_PORT}" \
        "@${DDI_VIP}" A "${fqdn}" 2>/dev/null | grep -E '^[0-9]+\.' || true
  else
    nslookup -type=A -timeout="${DNS_TIMEOUT}" -port="${DNS_PORT}" \
        "${fqdn}" "${DDI_VIP}" 2>/dev/null \
      | awk '/^Name:/{f=1} f&&/^Address: /{print $2}' || true
  fi
}

is_rfc1918() {
  case "$1" in
    10.*|192.168.*) return 0 ;;
    172.1[6-9].*|172.2[0-9].*|172.3[0-1].*) return 0 ;;
    *) return 1 ;;
  esac
}

# --- Check 1: enterprise A record --------------------------------------------
log "Check 1: resolving enterprise record ${TEST_FQDN} (expect ${EXPECTED_IP})"
answers="$(resolve_a "${TEST_FQDN}")"
[ -n "${answers}" ] || fail "no A answer for ${TEST_FQDN} from ${DDI_VIP}"
if grep -qxF "${EXPECTED_IP}" <<<"${answers}"; then
  log "PASS: ${TEST_FQDN} -> ${EXPECTED_IP}"
else
  fail "${TEST_FQDN} returned [$(tr '\n' ' ' <<<"${answers}")], expected ${EXPECTED_IP}"
fi

# --- Check 2: OCI-owned name conditional-forward path (optional) --------------
# Confirms Infoblox conditionally forwards OCI names (oraclevcn.com / private
# zones) to the OCI resolver LISTENING endpoint (contract §8).
if [ -n "${OCI_FQDN:-}" ]; then
  log "Check 2: resolving OCI name ${OCI_FQDN} via DDI forward path"
  oci_answers="$(resolve_a "${OCI_FQDN}")"
  [ -n "${oci_answers}" ] || fail "no A answer for ${OCI_FQDN} (conditional-forward to the OCI resolver LISTENING endpoint may be misconfigured)"
  if [ -n "${OCI_EXPECTED_IP:-}" ]; then
    grep -qxF "${OCI_EXPECTED_IP}" <<<"${oci_answers}" \
      || fail "${OCI_FQDN} returned [$(tr '\n' ' ' <<<"${oci_answers}")], expected ${OCI_EXPECTED_IP}"
    log "PASS: ${OCI_FQDN} -> ${OCI_EXPECTED_IP}"
  else
    first="$(head -n1 <<<"${oci_answers}")"
    is_rfc1918 "${first}" \
      || fail "${OCI_FQDN} returned public IP ${first}; expected a private VCN IP (forward path likely bypassed)"
    log "PASS: ${OCI_FQDN} -> private ${first}"
  fi
else
  log "Check 2 skipped: OCI_FQDN not set"
fi

log "All DNS validation checks passed."
