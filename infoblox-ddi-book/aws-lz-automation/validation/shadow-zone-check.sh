#!/usr/bin/env bash
#
# shadow-zone-check.sh — Phase 5.3 naming-plane gate: no shadow Route 53-only
# zones for in-scope assets.
#
# The chapter's DNS design (02-aws.md §7) gives every in-scope name a place in
# the AUTHORITATIVE naming plane: either Infoblox is authoritative for the
# zone, or the zone is deliberately Route 53-native and represented on the
# Infoblox side (synced into the Grid via the Route 53 sync, delegated, or
# reached via conditional forwarding). A private hosted zone that exists ONLY
# in Route 53 — invisible to the naming plane — is a SHADOW ZONE: names live
# there that the authoritative plane cannot vouch for, which is exactly the
# drift the DDI plane exists to prevent.
#
# This check enumerates the account's/org's private hosted zones and fails on
# any that the Infoblox side does not represent and that is not on the explicit
# allowlist. Run it on a CADENCE alongside cm8-reconciliation-check.sh.
#
# "Represented" is judged defensively as membership in ANY of:
#   * zone_auth     — Infoblox-authoritative zones (WAPI)
#   * zone_delegated— zones Infoblox delegates onward (WAPI)
#   * zone_forward  — zones Infoblox conditionally forwards (WAPI)
#   * the Route 53→NIOS hosted-zone sync, which lands zones as zone_auth
#     records flagged as externally managed (version-specific; the zone_auth
#     query above already captures them)
#
# STARTER SKELETON — WAPI object names are version-specific; confirm at
# https://<gm>/wapidoc/. The Route 53 listing uses the SAME least-privilege
# read actions the discovery role already carries (route53:ListHostedZones,
# route53:GetHostedZone — see 02-aws.md §6); no new IAM surface is required.
#
# ---------------------------------------------------------------------------
# Environment-variable contract
# ---------------------------------------------------------------------------
#   -- AWS (estate side) --
#   AWS CLI credentials/role in the environment (the discovery role's trust
#   path, or a CI role carrying the same read actions). AWS_PROFILE /
#   AWS_REGION respected as usual.
#   HOSTED_ZONE_SCOPE   (optional) "private" (default) | "all". Public zones
#                       are usually internet-facing and governed elsewhere.
#
#   -- Infoblox / NIOS WAPI (naming plane) --
#   GRID_MASTER         (required) Grid Master host/IP.
#   INFOBLOX_USERNAME   (required) WAPI read account.
#   INFOBLOX_PASSWORD   (required) From Secrets Manager / SSM.
#   WAPI_VERSION        (optional) Default: v2.12
#   DNS_VIEW            (optional) Restrict WAPI zone queries to one view.
#   WAPI_CA_BUNDLE      (optional) CA bundle for the Grid Master's cert.
#
#   -- Policy --
#   ALLOWLIST_FILE      (optional) File of zone names (one per line, comments
#                       with '#') that are ACCEPTED as Route 53-native and
#                       deliberately unrepresented — each entry is a recorded
#                       decision, not a silent skip.
#
# Exit: 0 = no shadow zones (outside the allowlist); 1 = shadow zones found or
# a query failed. Deps: bash 4+, aws CLI v2, curl, jq.
# ---------------------------------------------------------------------------

set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }

: "${GRID_MASTER:?GRID_MASTER is required}"
: "${INFOBLOX_USERNAME:?INFOBLOX_USERNAME is required}"
: "${INFOBLOX_PASSWORD:?INFOBLOX_PASSWORD is required}"

WAPI_VERSION="${WAPI_VERSION:-v2.12}"
HOSTED_ZONE_SCOPE="${HOSTED_ZONE_SCOPE:-private}"
CURL_WAPI=(curl -sS --fail-with-body -u "${INFOBLOX_USERNAME}:${INFOBLOX_PASSWORD}")
[ -n "${WAPI_CA_BUNDLE:-}" ] && CURL_WAPI+=(--cacert "${WAPI_CA_BUNDLE}")
WAPI="https://${GRID_MASTER}/wapi/${WAPI_VERSION}"

norm() { # lowercase, strip trailing dot
  tr '[:upper:]' '[:lower:]' | sed 's/\.$//'
}

# --- 1. Route 53 hosted zones (estate side) ---------------------------------
r53_json="$(aws route53 list-hosted-zones --output json)" \
  || fail "aws route53 list-hosted-zones failed — check the discovery role's read actions"
if [ "${HOSTED_ZONE_SCOPE}" = "private" ]; then
  r53_zones="$(echo "${r53_json}" | jq -r '.HostedZones[] | select(.Config.PrivateZone == true) | .Name')"
else
  r53_zones="$(echo "${r53_json}" | jq -r '.HostedZones[].Name')"
fi
r53_file="$(mktemp)"; trap 'rm -f "${r53_file}" "${nios_file:-}"' EXIT
echo "${r53_zones}" | norm | sort -u > "${r53_file}"
[ -s "${r53_file}" ] || { echo "OK — no ${HOSTED_ZONE_SCOPE} hosted zones to audit."; exit 0; }

# --- 2. Naming-plane representation (Infoblox side) -------------------------
nios_file="$(mktemp)"
view_q=""
[ -n "${DNS_VIEW:-}" ] && view_q="&view=${DNS_VIEW}"
for obj in zone_auth zone_delegated zone_forward; do
  # Objects and their availability vary by NIOS licensing/version; a missing
  # object type is tolerated (the remaining types still count as coverage).
  if resp="$("${CURL_WAPI[@]}" "${WAPI}/${obj}?_return_fields=fqdn&_max_results=10000${view_q}" 2>/dev/null)"; then
    echo "${resp}" | jq -r '.[].fqdn // empty' 2>/dev/null | norm >> "${nios_file}" || true
  else
    echo "note: WAPI object '${obj}' not readable on this Grid — continuing" >&2
  fi
done
sort -u -o "${nios_file}" "${nios_file}"

# --- 3. Allowlist -----------------------------------------------------------
allow_file="$(mktemp)"
if [ -n "${ALLOWLIST_FILE:-}" ] && [ -f "${ALLOWLIST_FILE}" ]; then
  grep -v '^\s*#' "${ALLOWLIST_FILE}" | grep -v '^\s*$' | norm | sort -u > "${allow_file}"
fi

# --- 4. Shadow = in Route 53, not represented, not allowlisted --------------
shadow="$(comm -23 "${r53_file}" "${nios_file}" | comm -23 - "${allow_file}")"
rm -f "${allow_file}"

total="$(grep -c . "${r53_file}" || true)"
echo "audited ${HOSTED_ZONE_SCOPE} hosted zones: ${total}"
if [ -n "${shadow}" ]; then
  echo "${shadow}" | sed 's/^/  SHADOW ZONE (Route 53-only, unrepresented): /'
  fail "$(echo "${shadow}" | grep -c .) shadow zone(s) — represent them in the naming plane (sync, delegate, or forward) or record them on the allowlist"
fi
echo "OK — every ${HOSTED_ZONE_SCOPE} hosted zone is represented in the authoritative naming plane (or allowlisted)."
