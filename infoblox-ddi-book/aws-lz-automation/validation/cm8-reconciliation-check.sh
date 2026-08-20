#!/usr/bin/env bash
#
# cm8-reconciliation-check.sh — Phase 5.3 estate gate: AWS assets reconcile to
# the CM-8 join key.
#
# The provisioning loop (catalog → Terraform → WAPI → Service Graph Connector)
# reconciles what the pipeline CREATES. This check covers what the pipeline did
# not create: the whole discovered AWS estate. It proves, three ways, that the
# join key holds:
#
#   1. DISCOVERY IS THE INVENTORY. vDiscovery has walked the accounts (that
#      freshness is discovery-sync-check.sh's job — run it first; this script
#      assumes a current sync and only warns if it cannot confirm one).
#   2. EVERY DISCOVERED ADDRESS IS IN THE CMDB. Each in-scope AWS address that
#      Infoblox IPAM knows (the authoritative naming/IPAM plane) has a CMDB
#      record carrying the same address — the CM-8 join key. A discovered
#      address with no CMDB record is an UNREGISTERED asset: it exists in the
#      cloud, the truth plane sees it, but no compliance claim can be keyed
#      to it.
#   3. THE CMDB CARRIES NOTHING THE TRUTH PLANE DISAVOWS. An in-scope CMDB
#      address that IPAM does not know is a STALE record: the CMDB is claiming
#      an asset the naming plane cannot vouch for. (The CMDB reconciles; it
#      never replaces the truth planes.)
#
# Any unregistered or stale count above its threshold fails the check. Run this
# on a CADENCE (scheduled pipeline job or ServiceNow scheduled flow) — it is an
# estate audit, not a per-request gate; the per-request gate remains the three
# Stage-3 provisioning checks.
#
# STARTER SKELETON — WAPI object/field names are version-specific and the CMDB
# table/field the Service Graph Connector populates varies by connector version
# and instance customization. Both are env-configurable below; confirm against
# YOUR Grid Master (https://<gm>/wapidoc/) and YOUR instance's connector
# mappings before trusting the counts. Nothing is hard-coded to a guess.
#
# ---------------------------------------------------------------------------
# Environment-variable contract
# ---------------------------------------------------------------------------
#   -- Infoblox / NIOS WAPI (the truth plane) --
#   GRID_MASTER         (required) Grid Master host/IP (WAPI endpoint).
#   INFOBLOX_USERNAME   (required) WAPI read account.
#   INFOBLOX_PASSWORD   (required) From Secrets Manager / SSM — never committed.
#   WAPI_VERSION        (optional) Default: v2.12
#   NETWORK_VIEW        (optional) Default: "default".
#   WAPI_CA_BUNDLE      (optional) CA bundle path for the Grid Master's cert.
#
#   -- ServiceNow Table API (the reconciled CMDB) --
#   SN_INSTANCE         (required) e.g. https://<instance>.servicenowservices.com
#   SN_USERNAME         (required) Read-only account scoped to the CMDB table.
#   SN_PASSWORD         (required) From Secrets Manager / SSM.
#   SN_TABLE            (optional) CMDB table holding reconciled addresses.
#                                  Default: cmdb_ci_ip_address. If your Service
#                                  Graph Connector lands addresses elsewhere
#                                  (e.g. cmdb_ci_ip_network children), point
#                                  this there.
#   SN_IP_FIELD         (optional) Field carrying the address. Default:
#                                  ip_address.
#   SN_QUERY            (optional) Extra sysparm_query to scope rows to the AWS
#                                  estate (e.g. "sys_class_name=cmdb_ci_ip_address^
#                                  discovery_source=Infoblox"). Default: none.
#
#   -- Scope + thresholds --
#   SCOPE_CIDRS         (optional) Comma-separated CIDRs; only addresses inside
#                                  them are audited. Default: audit everything
#                                  IPAM returns for the view.
#   UNREGISTERED_THRESHOLD (optional) Max tolerated discovered-not-in-CMDB
#                                  addresses. Default: 0.
#   STALE_THRESHOLD     (optional) Max tolerated CMDB-not-in-IPAM addresses.
#                                  Default: 0.
#
# Exit: 0 = reconciled within thresholds; 1 = drift beyond thresholds or a
# query failed. Deps: bash 4+, curl, jq, python3 (CIDR math).
# ---------------------------------------------------------------------------

set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }
warn() { echo "WARN: $*" >&2; }

: "${GRID_MASTER:?GRID_MASTER is required}"
: "${INFOBLOX_USERNAME:?INFOBLOX_USERNAME is required}"
: "${INFOBLOX_PASSWORD:?INFOBLOX_PASSWORD is required}"
: "${SN_INSTANCE:?SN_INSTANCE is required}"
: "${SN_USERNAME:?SN_USERNAME is required}"
: "${SN_PASSWORD:?SN_PASSWORD is required}"

WAPI_VERSION="${WAPI_VERSION:-v2.12}"
NETWORK_VIEW="${NETWORK_VIEW:-default}"
SN_TABLE="${SN_TABLE:-cmdb_ci_ip_address}"
SN_IP_FIELD="${SN_IP_FIELD:-ip_address}"
SN_QUERY="${SN_QUERY:-}"
SCOPE_CIDRS="${SCOPE_CIDRS:-}"
UNREGISTERED_THRESHOLD="${UNREGISTERED_THRESHOLD:-0}"
STALE_THRESHOLD="${STALE_THRESHOLD:-0}"

CURL_WAPI=(curl -sS --fail-with-body -u "${INFOBLOX_USERNAME}:${INFOBLOX_PASSWORD}")
[ -n "${WAPI_CA_BUNDLE:-}" ] && CURL_WAPI+=(--cacert "${WAPI_CA_BUNDLE}")
WAPI="https://${GRID_MASTER}/wapi/${WAPI_VERSION}"

# --- 0. Best-effort: confirm a recent discovery sync exists -----------------
# Authoritative freshness gating lives in discovery-sync-check.sh; here we only
# warn, so a mis-set task name never masks reconciliation results.
if ! "${CURL_WAPI[@]}" "${WAPI}/vdiscoverytask?_return_fields=name,state" >/dev/null 2>&1; then
  warn "could not read vdiscoverytask — run discovery-sync-check.sh separately to prove sync freshness"
fi

# --- 1. IPAM truth: in-scope used addresses the truth plane knows -----------
# ipv4address is a paging-heavy object; page via _paging/_max_results. The
# status=USED filter keeps unassigned space out of the audit. Field names are
# WAPI-version-specific — confirm at https://<gm>/wapidoc/.
ipam_file="$(mktemp)"; trap 'rm -f "${ipam_file}" "${cmdb_file:-}"' EXIT
page_id=""
while :; do
  url="${WAPI}/ipv4address?network_view=${NETWORK_VIEW}&status=USED&_return_fields=ip_address&_paging=1&_return_as_object=1&_max_results=1000"
  [ -n "${page_id}" ] && url="${url}&_page_id=${page_id}"
  resp="$("${CURL_WAPI[@]}" "${url}")" || fail "WAPI ipv4address query failed"
  echo "${resp}" | jq -r '.result[].ip_address' >> "${ipam_file}"
  page_id="$(echo "${resp}" | jq -r '.next_page_id // empty')"
  [ -z "${page_id}" ] && break
done

# --- 2. CMDB view: reconciled addresses ServiceNow claims -------------------
cmdb_file="$(mktemp)"
offset=0
while :; do
  q="sysparm_fields=${SN_IP_FIELD}&sysparm_limit=1000&sysparm_offset=${offset}"
  [ -n "${SN_QUERY}" ] && q="${q}&sysparm_query=${SN_QUERY}"
  resp="$(curl -sS --fail-with-body -u "${SN_USERNAME}:${SN_PASSWORD}" \
          -H "Accept: application/json" \
          "${SN_INSTANCE}/api/now/table/${SN_TABLE}?${q}")" \
    || fail "ServiceNow Table API query failed (table=${SN_TABLE})"
  count="$(echo "${resp}" | jq ".result | length")"
  echo "${resp}" | jq -r ".result[].${SN_IP_FIELD} | select(. != null and . != \"\")" >> "${cmdb_file}"
  [ "${count}" -lt 1000 ] && break
  offset=$((offset + 1000))
done

# --- 3. Scope filter + set comparison (python3 for CIDR math) ---------------
UNREG_FILE="$(mktemp)"; STALE_FILE="$(mktemp)"
python3 - "$ipam_file" "$cmdb_file" "$SCOPE_CIDRS" "$UNREG_FILE" "$STALE_FILE" <<'PY'
import ipaddress, sys
ipam_f, cmdb_f, scope_s, unreg_f, stale_f = sys.argv[1:6]
scopes = [ipaddress.ip_network(c.strip()) for c in scope_s.split(",") if c.strip()]

def load(path):
    out = set()
    for line in open(path):
        line = line.strip()
        if not line:
            continue
        try:
            ip = ipaddress.ip_address(line)
        except ValueError:
            continue  # non-IP field content (defensive)
        if scopes and not any(ip in s for s in scopes):
            continue
        out.add(str(ip))
    return out

ipam, cmdb = load(ipam_f), load(cmdb_f)
open(unreg_f, "w").write("\n".join(sorted(ipam - cmdb)))
open(stale_f, "w").write("\n".join(sorted(cmdb - ipam)))
print(f"in-scope IPAM addresses: {len(ipam)}  CMDB addresses: {len(cmdb)}")
PY

unreg_n="$(grep -c . "${UNREG_FILE}" || true)"
stale_n="$(grep -c . "${STALE_FILE}" || true)"

echo "unregistered (IPAM-discovered, no CMDB record): ${unreg_n} (threshold ${UNREGISTERED_THRESHOLD})"
[ "${unreg_n}" -gt 0 ] && sed 's/^/  unregistered: /' "${UNREG_FILE}"
echo "stale (CMDB record, unknown to IPAM):           ${stale_n} (threshold ${STALE_THRESHOLD})"
[ "${stale_n}" -gt 0 ] && sed 's/^/  stale: /' "${STALE_FILE}"
rm -f "${UNREG_FILE}" "${STALE_FILE}"

[ "${unreg_n}" -gt "${UNREGISTERED_THRESHOLD}" ] && fail "CM-8 reconciliation drift: ${unreg_n} unregistered address(es)"
[ "${stale_n}" -gt "${STALE_THRESHOLD}" ] && fail "CM-8 reconciliation drift: ${stale_n} stale CMDB address(es)"

echo "OK — AWS estate reconciles to the CM-8 join key within thresholds."
