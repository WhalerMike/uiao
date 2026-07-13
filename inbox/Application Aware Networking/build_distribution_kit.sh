#!/usr/bin/env bash
# Build the AAN distribution kit (.zip): rendered book .docx + .pptx decks,
# per-volume folders, governance docs. This rebuild ADDS the full Volume VIII
# chapter set (infoblox-ddi-book/) and the ServiceNow app kit, which the prior
# kit omitted (it shipped only the Vol VIII overview shim).
#
# Usage: ./build_distribution_kit.sh
# Requires the bundled pandoc (pypandoc-binary) + aan-reference.docx + aan-callouts.lua.
set -uo pipefail
cd "$(dirname "$0")"
HERE="$(pwd)"
DDI="$HERE/../../infoblox-ddi-book"
PANDOC="${PANDOC:-/usr/local/lib/python3.11/dist-packages/pypandoc/files/pandoc}"
REF="aan-reference.docx"; LUA="aan-callouts.lua"
STAGE="/tmp/aanbuild/kit"
DATECODE="$(date +'%Y-%m-%d_%H%MET')"
ZIP="AAN_Federal_Series_Complete_${DATECODE}.zip"
OLDZIP="$(ls -1 AAN_Federal_Series_Complete_*.zip 2>/dev/null | grep -v "$DATECODE" | head -1)"

rm -rf "$STAGE"; mkdir -p "$STAGE"

# Seed from the prior kit so every existing .pptx deck and governance doc is
# preserved (only Vol VII/IX decks exist as loose files; the rest live only in
# the prior zip). The render passes below then OVERWRITE each book's .docx with
# a fresh render and ADD the full Volume VIII set on top.
if [ -n "$OLDZIP" ]; then
  echo "== Seeding staging from prior kit: $OLDZIP =="
  ( cd "$STAGE" && unzip -q "$HERE/$OLDZIP" )
fi

# Map a Vol_X_ book filename prefix to its distribution folder.
vol_folder() {
  case "$1" in
    Vol_0_*)    echo "Vol_0_Executive_Summary_and_Program";;
    Vol_I_*)    echo "Vol_I_Foundation_and_Transport";;
    Vol_II_*)   echo "Vol_II_Data_Platform";;
    Vol_III_*)  echo "Vol_III_Security_Operations";;
    Vol_IV_*)   echo "Vol_IV_Governance_and_Assurance";;
    Vol_V_*)    echo "Vol_V_Training_and_Certification";;
    Vol_VI_*)   echo "Vol_VI_Implementation";;
    Vol_VII_*)  echo "Vol_VII_ServiceNow_Automation";;
    Vol_VIII_*) echo "Vol_VIII_Multi_Cloud_DDI";;
    Vol_IX_*)   echo "Vol_IX_Day2_Operations";;
    *) echo "";;
  esac
}

render() { # src outdocx resourcepath
  "$PANDOC" "$1" -f markdown -o "$2" --reference-doc="$REF" --lua-filter="$LUA" --resource-path="$3" 2>/tmp/pderr.txt \
    && return 0 || { echo "   FAIL render $1"; sed 's/^/     /' /tmp/pderr.txt; return 1; }
}

ok=0; fail=0
echo "== Rendering series books (Vol_*_Book_*.qmd) =="
for qmd in Vol_*_Book_*.qmd; do
  base="${qmd%.qmd}"
  folder="$(vol_folder "$base")"; [ -z "$folder" ] && { echo "   skip (no folder) $base"; continue; }
  mkdir -p "$STAGE/$folder"
  if render "$qmd" "$STAGE/$folder/$base.docx" "."; then ok=$((ok+1)); else fail=$((fail+1)); fi
  # ride the committed deck if present
  [ -f "$base.pptx" ] && cp "$base.pptx" "$STAGE/$folder/"
done

echo "== Rendering Volume VIII chapters (infoblox-ddi-book/) =="
V8="$STAGE/Vol_VIII_Multi_Cloud_DDI"; mkdir -p "$V8"
declare -A V8MAP=(
  ["01-azure"]="Vol_VIII_Book_01_FedAAN_DDI_Azure"
  ["02-aws"]="Vol_VIII_Book_02_FedAAN_DDI_AWS"
  ["03-gcp"]="Vol_VIII_Book_03_FedAAN_DDI_GCP"
  ["04-oci"]="Vol_VIII_Book_04_FedAAN_DDI_OCI"
  ["05-vmware"]="Vol_VIII_Book_05_FedAAN_DDI_VMware"
  ["06-cross-platform-operations"]="Vol_VIII_Book_06_FedAAN_DDI_Cross_Platform_Operations"
  ["07-servicenow-orchestration"]="Vol_VIII_Book_07_FedAAN_DDI_ServiceNow_Orchestration"
  ["08-servicenow-led-implementation"]="Vol_VIII_Book_08_FedAAN_DDI_ServiceNow_Led_Implementation"
  ["appendix-A-sizing-cost-ipv6-dhcp"]="Vol_VIII_Book_A_FedAAN_DDI_Appendix_Sizing_Cost_IPv6_DHCP"
)
for src in "${!V8MAP[@]}"; do
  if render "$DDI/$src.md" "$V8/${V8MAP[$src]}.docx" "$DDI"; then ok=$((ok+1)); else fail=$((fail+1)); fi
done

echo "== ServiceNow app kit (source) into Vol VIII =="
cp -r "$DDI/servicenow-app" "$V8/servicenow-app-kit"
find "$V8/servicenow-app-kit" -name '*.png' -delete 2>/dev/null  # drop heavy raster mock renders if any

echo "== Governance / roadmap docs (rendered from .md) =="
render "federal-aan-conmon-gap-roadmap.md" "$STAGE/federal-aan-conmon-gap-roadmap.docx" "." && ok=$((ok+1)) || fail=$((fail+1))
[ -f "federal-aan-conmon-gap-roadmap.pptx" ] && cp "federal-aan-conmon-gap-roadmap.pptx" "$STAGE/"
render "federal-aan-governance-ownership-model.md" "$STAGE/federal-aan-governance-ownership-model.docx" "." && ok=$((ok+1)) || fail=$((fail+1))

echo "rendered $ok ok, $fail failed"

echo "== README.txt =="
cat > "$STAGE/README.txt" <<EOF
AAN Federal Series — Complete distribution kit
Date Code: $(date +'%Y-%m-%d %H%M') ET

Volumes 0-IX are included here (rendered .docx books + .pptx briefing decks).

Volume VIII (Multi-Cloud DDI Landing-Zone Automation) is now included in FULL:
the series overview book plus all per-cloud chapters (Azure, AWS, GCP, OCI,
VMware), Cross-Platform Operations, the two ServiceNow chapters (07 ServiceNow
Orchestration, 08 ServiceNow-Led Implementation), and Appendix A. The ServiceNow
scoped-app kit (catalog, Flow, Script Includes, ATF, Update Set, mockups) ships
as source under Vol_VIII_Multi_Cloud_DDI/servicenow-app-kit/. This replaces the
prior kit, which represented Volume VIII by its overview book only.

Every AAN deliverable is bound by the compliance spine (aan-compliance-spine.yml):
each book carries an explicit source: file path and the non-prose kits are
registered in its kits: section.

All book .docx carry AAN house-style callout boxes (important/note/tip/warning,
FOUO and executive-summary blocks) produced with Pandoc + aan-reference.docx +
aan-callouts.lua. See BUILD-DERIVATIVES.md and build_distribution_kit.sh.

Scope: FedRAMP Moderate & Microsoft GCC Moderate (Volume VIII is the explicit,
author-directed multi-cloud breadth exception).
EOF

echo "== Zipping -> $ZIP =="
( cd "$STAGE" && zip -r -q "$HERE/$ZIP" . )
ls -la "$HERE/$ZIP"
echo "entries: $(unzip -Z1 "$HERE/$ZIP" | wc -l)"
[ "$fail" -eq 0 ] && echo "BUILD OK" || echo "BUILD had $fail render failures"
