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
DDI="$(git -C "$HERE" rev-parse --show-toplevel)/infoblox-ddi-book"
# Prefer the bundled pypandoc binary (pinned, and what CI has); fall back to a
# pandoc on PATH so a local Windows/macOS checkout can build. Without the
# fallback the hardcoded Linux path simply does not exist: every render fails,
# and the build still ships a zip full of STALE docx seeded from the prior kit.
PANDOC="${PANDOC:-}"
if [ -z "$PANDOC" ]; then
  _bundled="/usr/local/lib/python3.11/dist-packages/pypandoc/files/pandoc"
  if [ -x "$_bundled" ]; then
    PANDOC="$_bundled"
  elif command -v pandoc >/dev/null 2>&1; then
    PANDOC="$(command -v pandoc)"
  else
    echo "FATAL: no pandoc found (set PANDOC=/path/to/pandoc)" >&2; exit 1
  fi
fi
echo "== pandoc: $PANDOC =="
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

echo "== Kits (deployable source) — every kit registered in the spine, into its volume =="
# Driven from aan-compliance-spine.yml so the zip carries EVERY registered kit
# (Terraform IaC, ServiceNow scoped apps, detection rules, training academy) —
# complete source, nothing dropped. Each kit lands under <Volume>/kits/<name>/.
REPO_ROOT="$(git -C "$HERE" rev-parse --show-toplevel)"
kits=0
# Purge every kits/ dir seeded from the prior zip BEFORE re-copying. The loop
# below re-adds every kit the spine registers, so nothing is lost — and this is
# the only way to evict a mis-named directory a previous run may have left
# behind. Per-kit `rm -rf "$destdir/$base"` cannot do it: if $base was mangled
# on the run that created the directory, the name no longer matches.
find "$STAGE" -type d -name kits -prune -exec rm -rf {} + 2>/dev/null || true
while IFS=$'\t' read -r volfolder src base; do
  # Strip a trailing CR: python3 on Windows emits CRLF, and `read` splits on \n
  # only — so the CR lands on the last field and `cp -r` then creates a
  # directory whose name carries it. That silently duplicated every kit on each
  # Windows rebuild (681 -> 942 entries) before this guard.
  base="${base%$'\r'}"
  src="${src%$'\r'}"
  volfolder="${volfolder%$'\r'}"
  [ -z "$volfolder" ] && continue
  destdir="$STAGE/$volfolder/kits"
  mkdir -p "$destdir"
  if [ -e "$REPO_ROOT/$src" ]; then
    rm -rf "$destdir/$base"   # idempotent: drop any copy seeded from the prior kit (avoids nesting)
    cp -r "$REPO_ROOT/$src" "$destdir/$base"
    n=$(find "$destdir/$base" -type f | wc -l)
    printf '   + %-34s %4s files -> %s/kits/%s\n' "$base" "$n" "$volfolder" "$base"
    kits=$((kits+1))
  else
    echo "   MISSING kit source: $src"
  fi
done < <(python3 - "$HERE/aan-compliance-spine.yml" <<'PY'
import sys, os, yaml
d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
volfolder = {
  "vol-0":"Vol_0_Executive_Summary_and_Program","vol-1":"Vol_I_Foundation_and_Transport",
  "vol-2":"Vol_II_Data_Platform","vol-3":"Vol_III_Security_Operations",
  "vol-4":"Vol_IV_Governance_and_Assurance","vol-5":"Vol_V_Training_and_Certification",
  "vol-6":"Vol_VI_Implementation","vol-7":"Vol_VII_ServiceNow_Automation",
  "vol-8":"Vol_VIII_Multi_Cloud_DDI","vol-9":"Vol_IX_Day2_Operations",
}
for k in d.get("kits", []):
    src = k["source"]
    print(f"{volfolder[k['volume']]}\t{src}\t{os.path.basename(src)}")
PY
)
echo "   bundled $kits kits"

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

Volume VIII (Multi-Cloud DDI Landing-Zone Automation) is included in FULL:
the series overview book plus all per-cloud chapters (Azure, AWS, GCP, OCI,
VMware), Cross-Platform Operations, the two ServiceNow chapters (07 ServiceNow
Orchestration, 08 ServiceNow-Led Implementation), and Appendix A.

DEPLOYABLE SOURCE — every kit registered in the compliance spine now ships in
this zip as complete source, under <Volume>/kits/<name>/:
  - Vol VIII: the five per-cloud landing-zone Terraform/IaC kits
    (azure-alz-automation, aws-lz-automation, gcp-lz-automation, oci-lz-automation,
    vmware-lz-automation) and the ServiceNow DDI scoped app (servicenow-app).
  - Vol IX:  the ServiceNow Day-2 scoped-app kit (servicenow-day2).
  - Vol VI:  the Sentinel detection-rule library (detection-rules).
  - Vol V:   the companion training academy curriculum (AAN-Training-Program).
Nothing is dropped — the Terraform (.tf), shell, ServiceNow XML/JS, and ATF
sources are all present. Prior kits carried only the rendered books (+ the
ServiceNow app); this kit carries the deployable code too.

Every AAN deliverable is bound by the compliance spine (aan-compliance-spine.yml):
each book carries an explicit source: file path and the non-prose kits are
registered in its kits: section — the same registry drives the kit bundling above.

All book .docx carry AAN house-style callout boxes (important/note/tip/warning,
FOUO and executive-summary blocks) produced with Pandoc + aan-reference.docx +
aan-callouts.lua. See BUILD-DERIVATIVES.md and build_distribution_kit.sh.

Scope: FedRAMP Moderate & Microsoft GCC Moderate (Volume VIII is the explicit,
author-directed multi-cloud breadth exception).
EOF

# ---------------------------------------------------------------------------
# Self-check — assert the staged tree's SHAPE before zipping.
#
# A closed-world assertion, not a diff. The CRLF bug above shipped a corrupt
# kit past a "nothing was dropped" check because the corruption was purely
# ADDITIVE (a mangled twin per kit, per rebuild: 420 -> 681 -> 942 files).
# Diffing for losses can never catch that; enumerating what is ALLOWED can.
# ---------------------------------------------------------------------------
echo "== Self-check =="
selfcheck_fail=0

# NOTE — these assertions deliberately avoid grep. MSYS/Git Bash grep strips \r
# from BOTH its input and its pattern, so `grep -qxF "$name"` silently matches
# "kit" against "kit<CR>" — i.e. grep is blind to precisely the corruption this
# check exists to catch. Bash's own [[ ]] compares the raw bytes. Verified: a
# grep-based version of check 1 scored 0 against an injected <CR> twin.
expected_kits=()
while IFS= read -r k; do
  k="${k%$'\r'}"
  [ -n "$k" ] && expected_kits+=("$k")
done < <(python3 - "$HERE/aan-compliance-spine.yml" <<'PY'
import sys, os, yaml
d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
for k in d.get("kits", []):
    print(os.path.basename(k["source"]))
PY
)

_is_expected() {  # exact byte-for-byte membership; no grep, no globbing
  local needle="$1" e
  for e in "${expected_kits[@]}"; do [[ "$e" == "$needle" ]] && return 0; done
  return 1
}

# 1. Every kits/<name> on disk must be a kit the spine registers. Anything else
#    is a mis-named directory a previous run left behind.
found_kits=()
while IFS= read -r -d '' dir; do
  name="${dir##*/}"
  found_kits+=("$name")
  if ! _is_expected "$name"; then
    echo "   FAIL unexpected kit dir: $(printf '%q' "$name")"
    selfcheck_fail=$((selfcheck_fail+1))
  fi
  if [[ "$name" =~ [[:cntrl:]] ]]; then
    echo "   FAIL kit dir name carries a control character (CRLF leak): $(printf '%q' "$name")"
    selfcheck_fail=$((selfcheck_fail+1))
  fi
done < <(find "$STAGE" -mindepth 3 -maxdepth 3 -type d -path '*/kits/*' -print0 2>/dev/null)

# 2. Every registered kit must actually be present.
for e in "${expected_kits[@]}"; do
  present=0
  for f in "${found_kits[@]}"; do [[ "$f" == "$e" ]] && present=1 && break; done
  if [ "$present" -eq 0 ]; then
    echo "   FAIL registered kit missing from staging: $e"
    selfcheck_fail=$((selfcheck_fail+1))
  fi
done

staged_files=$(find "$STAGE" -type f | wc -l)
echo "   staged files: $staged_files | kits expected: $(printf '%s\n' "$expected_kits" | grep -c .)"
if [ "$selfcheck_fail" -eq 0 ]; then
  echo "   self-check OK"
else
  echo "   SELF-CHECK FAILED ($selfcheck_fail problem(s)) — NOT zipping."
  echo "   Staging left at $STAGE for inspection."
  exit 1
fi

# The kit must not silently SHRINK. Staging is seeded from the prior zip because
# most .pptx decks and the governance docs exist nowhere else on disk — so if the
# prior zip is missing (deleted, renamed, not yet fetched), the build quietly
# produces a kit without them and still reports "self-check OK". That happened:
# a seedless run shipped 422 entries instead of 456, dropping the entire
# servicenow-app-kit, and nothing objected. The file count is the only signal
# that the seed did its job, so compare it against the prior kit.
# A legitimate shrink (a book genuinely retired) is declared: ALLOW_SHRINK=1.
if [ -z "$OLDZIP" ]; then
  # The dangerous case, and the one that actually bit: NO prior kit at all. There
  # is nothing to compare against, so a count check cannot catch it — refuse outright.
  if [ -z "${ALLOW_NO_SEED:-}" ]; then
    echo "   NO PRIOR KIT to seed from — NOT zipping."
    echo "   Most .pptx decks and the governance docs exist nowhere else on disk;"
    echo "   without a seed the kit ships silently incomplete (this dropped 44 files"
    echo "   once, including the whole servicenow-app-kit, reporting 'self-check OK')."
    echo "   Restore the prior AAN_Federal_Series_Complete_*.zip, or set ALLOW_NO_SEED=1"
    echo "   if you really intend to build from loose files only."
    exit 1
  fi
  echo "   (ALLOW_NO_SEED set — building without a prior kit)"
else
  old_entries=$(unzip -Z1 "$HERE/$OLDZIP" 2>/dev/null | grep -vc '/$')
  if [ "$staged_files" -lt "$old_entries" ] && [ -z "${ALLOW_SHRINK:-}" ]; then
    echo "   KIT SHRANK: $staged_files staged vs $old_entries in $OLDZIP — NOT zipping."
    echo "   Files that live only in the prior kit are missing. Restore it, or set"
    echo "   ALLOW_SHRINK=1 if the removal is intended."
    echo "   Staging left at $STAGE for inspection."
    exit 1
  fi
  echo "   entries vs prior kit: $staged_files (prior: $old_entries)"
fi

# A kit whose renders failed is a kit of STALE docx: staging is seeded from the
# prior zip, so a failed render silently leaves last release's file in place.
# The file count still looks right and the self-check still passes — this build
# once shipped 455 files with 0 successful renders and printed "self-check OK".
# BUILD-DERIVATIVES.md is explicit that a stale docx is worse than none, so a
# render failure blocks the zip exactly as a self-check failure does.
if [ "$fail" -ne 0 ]; then
  echo "   $fail RENDER FAILURE(S) — NOT zipping: the kit would carry stale docx"
  echo "   from the prior release. Fix the renders, or set PANDOC=/path/to/pandoc."
  echo "   Staging left at $STAGE for inspection."
  exit 1
fi

echo "== Zipping -> $ZIP =="
# Git Bash on Windows ships `unzip` but NOT `zip`, so this last step failed the
# whole build after every render had already succeeded. Fall back to Python's
# zipfile rather than lose the run.
#
# cygpath -m is load-bearing: Windows Python resolves a bare /tmp/aanbuild/kit
# as C:\tmp\aanbuild\kit, which does not exist, and writes a valid EMPTY archive
# instead of failing — a 22-byte zip that looks like a successful build.
if command -v zip >/dev/null 2>&1; then
  ( cd "$STAGE" && zip -r -q "$HERE/$ZIP" . )
else
  echo "   (zip not found — falling back to python zipfile)"
  python - "$(cygpath -m "$STAGE")" "$(cygpath -m "$HERE")/$ZIP" <<'PYZIP'
import os, sys, zipfile
stage, out = sys.argv[1], sys.argv[2]
n = 0
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, _, files in os.walk(stage):
        for f in files:
            p = os.path.join(root, f)
            z.write(p, os.path.relpath(p, stage).replace("\\", "/"))
            n += 1
if n == 0:
    sys.exit(f"refusing to ship an empty kit: no files under {stage}")
print(f"   python zipfile: {n} entries")
PYZIP
fi
ls -la "$HERE/$ZIP"
echo "entries: $(unzip -Z1 "$HERE/$ZIP" | wc -l)"
[ "$fail" -eq 0 ] && echo "BUILD OK" || echo "BUILD had $fail render failures"
