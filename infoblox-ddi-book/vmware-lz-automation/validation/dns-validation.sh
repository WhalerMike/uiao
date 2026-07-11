#!/usr/bin/env bash
#
# dns-validation.sh — Stage 3 (validation) DNS resolution check (VMware).
#
# Proves that the Infoblox DDI members deployed by Stage 2 are actually
# answering DNS for (a) an enterprise/authoritative A record and (b) an
# AD-integrated name that the Grid CONDITIONALLY FORWARDS to the on-prem AD DNS
# servers (see _module-contract.md §8). On VMware the query is aimed at the DDI
# anycast/VRRP VIP (contract output `ddi_anycast_vip`) — the address the NSX-T
# DNS forwarder points tenant resolution at.
#
# On any mismatch or resolver failure the script exits non-zero so the pipeline
# `validate` stage fails the run.
#
# STARTER SKELETON — labeled as such. The FQDNs, expected IPs, and VIP are
# environment-specific and MUST be supplied by the caller; nothing is hard-coded.
#
# ---------------------------------------------------------------------------
# Environment-variable contract
# ---------------------------------------------------------------------------
#   DDI_VIP            (required) Anycast/VRRP VIP / DNS server IP to query. This
#                                 is Stage 2 output `ddi_anycast_vip` (or one of
#                                 `dns_server_ips`). You may point it at the NSX
#                                 forwarder IP instead to test the full path.
#   TEST_FQDN          (required) Enterprise A record to resolve, e.g.
#                                 app01.corp.example
#   EXPECTED_IP        (required) IP that TEST_FQDN must resolve to.
#   AD_FQDN            (optional) An AD-integrated name to resolve through the
#                                 Grid's conditional-forward-to-AD path, e.g.
#                                 dc01.corp.example
#   AD_EXPECTED_IP     (optional) Expected IP for AD_FQDN. If AD_FQDN is set but
#                                 this is unset, the script asserts only that
#                                 resolution succeeds and returns a private
#                                 (RFC1918) A (i.e. the conditional forwarder to
#                                 on-prem AD DNS is working).
#   DNS_TIMEOUT        (optional) Per-query timeout seconds. Default: 5
#   DNS_PORT           (optional) DNS port. Default: 53
#
# Exit codes: 0 all asserted answers matched; 1 a check failed; 2 usage/tooling.
# ---------------------------------------------------------------------------

set -euo pipefail

log()  { printf '%s %s\n' "[$(date -u +%FT%TZ)]" "$*"; }
fail() { log "FAIL: $*"; exit 1; }

: "${DDI_VIP:?set DDI_VIP to the DDI anycast/VRRP VIP / DNS server IP}"
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

# --- Check 2: AD conditional-forward path (optional) -------------------------
if [ -n "${AD_FQDN:-}" ]; then
  log "Check 2: resolving AD name ${AD_FQDN} via the Grid conditional-forward path"
  ad_answers="$(resolve_a "${AD_FQDN}")"
  [ -n "${ad_answers}" ] || fail "no A answer for ${AD_FQDN} (conditional forward to on-prem AD DNS may be misconfigured)"
  if [ -n "${AD_EXPECTED_IP:-}" ]; then
    grep -qxF "${AD_EXPECTED_IP}" <<<"${ad_answers}" \
      || fail "${AD_FQDN} returned [$(tr '\n' ' ' <<<"${ad_answers}")], expected ${AD_EXPECTED_IP}"
    log "PASS: ${AD_FQDN} -> ${AD_EXPECTED_IP}"
  else
    first="$(head -n1 <<<"${ad_answers}")"
    is_rfc1918 "${first}" \
      || fail "${AD_FQDN} returned public IP ${first}; expected a private AD DNS answer (forward path likely bypassed)"
    log "PASS: ${AD_FQDN} -> private ${first}"
  fi
else
  log "Check 2 skipped: AD_FQDN not set"
fi

log "All DNS validation checks passed."
