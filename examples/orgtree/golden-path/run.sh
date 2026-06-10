#!/usr/bin/env bash
#
# OrgPath Governance Golden Path — end-to-end, offline, no credentials.
#
# Runs the four stages of the OrgPath wedge against the committed sample data
# in this directory, writing every artifact to ./out (gitignored):
#
#   1. assess     — Active Directory identity plane  -> OrgPath facet assignments
#   2. inventory  — Entra + Arc device plane         -> capture status + backfill worklist + snapshot
#   3. govern     — one governance pass over the snapshot -> drift findings + telemetry (dry-run, halt-on-critical)
#   4. ir bundle  — AD survey -> signed evidence bundle + OSCAL Assessment Results
#
# Everything is read-only / dry-run by default and uses --from-export +
# --insecure-dev-key, so it needs no live AD, no Azure tenant, and no API keys.
# This is the artifact a design partner runs to see the wedge work on their
# own desk before any pilot touches a real tenant.
#
# Usage:
#   examples/orgtree/golden-path/run.sh            # writes to ./out next to this script
#   OUT=/tmp/gp examples/orgtree/golden-path/run.sh
#
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../../.." && pwd)"
OUT="${OUT:-$HERE/out}"
SURVEY="$REPO_ROOT/examples/orgtree/synthetic-forest-export.json"

mkdir -p "$OUT"

echo "==> OrgPath Governance Golden Path"
echo "    sample data : $HERE"
echo "    artifacts   : $OUT"
echo

echo "########## STEP 1 — assess (Active Directory identity plane) ##########"
uiao orgtree assess \
  --from-export "$HERE/ad-users.json" \
  --out "$OUT/assignments.json"
echo

echo "########## STEP 2 — inventory (Entra + Arc device plane) ##########"
uiao orgtree inventory \
  --devices-export "$HERE/entra-devices.json" \
  --machines-export "$HERE/arc-machines.json" \
  --owner-map "$HERE/owner-map.json" \
  --snapshot-out "$OUT/inventory-snapshot.json" \
  --worklist-out "$OUT/worklist.json"
echo

echo "########## STEP 3 — govern (one governance pass over the snapshot) ##########"
uiao orgtree govern "$OUT/inventory-snapshot.json" \
  --detection-only \
  --out "$OUT/drift-report.json"
echo

echo "########## STEP 4 — signed OSCAL evidence bundle ##########"
# NOTE: --insecure-dev-key is for this offline demo ONLY. In a real run, set
# UIAO_BUNDLE_HMAC_KEY and drop the flag so the signature is meaningful.
uiao ir orgtree-readiness-bundle "$SURVEY" \
  --out-dir "$OUT/bundle" \
  --oscal-out "$OUT/oscal" \
  --insecure-dev-key
echo

echo "==> Done. Artifacts written under $OUT:"
echo "    assignments.json        — per-user OrgPath facet derivation + findings (step 1)"
echo "    inventory-snapshot.json — govern-compatible snapshot of current device state (step 2)"
echo "    worklist.json           — per-device capture status + backfill proposal (step 2)"
echo "    drift-report.json       — full drift scan + UIAO_174 telemetry (step 3)"
echo "    bundle/bundle.{json,hash,sig} — signed OrgTree evidence bundle (step 4)"
echo "    oscal/orgtree-evidence.json   — OSCAL Assessment Results (step 4)"
