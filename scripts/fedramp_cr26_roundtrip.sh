#!/usr/bin/env bash
# fedramp_cr26_roundtrip.sh — advisory round-trip check for vendored
# FedRAMP CR26 OSCAL snapshots.
#
# For every snapshot directory under
# src/uiao/canon/compliance/reference/fedramp-cr26/snapshot/<sha>/, this
# script:
#
#   1. Runs `oscal-cli validate` against each pinned XML / JSON / YAML
#      artifact. A validation failure marks that artifact as drifted.
#   2. Re-converts the pinned XML to JSON / YAML via `oscal-cli convert`
#      (canonical form A), and re-converts the pinned JSON / YAML via
#      `oscal-cli convert` to the same target format (canonical form B).
#      Then byte-diffs A against B. A clean diff means the Palladium
#      generator's JSON / YAML are faithful conversions of its XML.
#
# Output is the markdown report at $REPORT_PATH (default:
# /tmp/cr26-roundtrip/report.md). The CI workflow appends this report
# to $GITHUB_STEP_SUMMARY and uploads the temp dir as an artifact.
#
# Exits 0 always — this check is advisory per ADR-061 D4. CI marks the
# job with `continue-on-error: true` so the result never blocks merge.
#
# Requires `oscal-cli` on $PATH and Java 17+.

set -uo pipefail

REPO_ROOT="${REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SNAPSHOT_BASE="$REPO_ROOT/src/uiao/canon/compliance/reference/fedramp-cr26/snapshot"
WORK="${WORK:-/tmp/cr26-roundtrip}"
REPORT_PATH="${REPORT_PATH:-$WORK/report.md}"

mkdir -p "$WORK"

# Artifacts to check inside each snapshot directory: (label, xml, json, yaml).
# Mapping file lacks JSON/YAML conversions at this pin; treated as
# XML-only and validated alone.
ARTIFACTS=(
  "catalog|catalog/xml/FedRAMP_CR26_catalog.xml|catalog/json/FedRAMP_CR26_catalog.json|catalog/yaml/FedRAMP_CR26_catalog.yaml"
  "profile-20x|profile/20x/xml/FedRAMP_20x_profile.xml|profile/20x/json/FedRAMP_20x_profile.json|profile/20x/yaml/FedRAMP_20x_profile.yaml"
  "profile-rev5|profile/rev5/xml/FedRAMP_rev5_profile.xml|profile/rev5/json/FedRAMP_rev5_profile.json|profile/rev5/yaml/FedRAMP_rev5_profile.yaml"
  "mapping|mapping/xml/FedRAMP_CR26_to_NIST_SP-800-53_rev5_mapping-collection.xml||"
)

{
  echo "# FedRAMP CR26 Round-trip Report"
  echo ""
  echo "Tool: NIST \`oscal-cli\` (Maven cli-core, version pinned by SHA-256 in workflow)"
  echo "Method: canonicalize both sides via \`oscal-cli convert\` and byte-diff (option **b-normalize**)."
  echo "Status: **advisory** — drift here is informational, never blocks merge (ADR-061 D4)."
  echo ""
} > "$REPORT_PATH"

if [ ! -d "$SNAPSHOT_BASE" ]; then
  echo "_No snapshot directory found at \`$SNAPSHOT_BASE\` — nothing to do._" >> "$REPORT_PATH"
  exit 0
fi

# Color helpers (only used in step output, not in the markdown report).
log()  { printf '%s\n' "$*" >&2; }
mark() { printf '%s\n' "$*" >> "$REPORT_PATH"; }

oscal_validate() {
  local input="$1"
  local cmd
  cmd=$(_oscal_command_for "$input")
  # mapping-collection is not exposed as a sub-command in oscal-cli
  # 1.0.3; fall back to xmllint well-formedness for XML mapping files.
  if [ "$cmd" = "mapping-collection" ]; then
    if command -v xmllint >/dev/null 2>&1; then
      xmllint --noout "$input" 2>&1 && return 0 || return 1
    fi
    # No xmllint available; treat as non-fatal "not checked".
    return 3
  fi
  oscal-cli "$cmd" validate "$input" >/dev/null 2>&1 || return 1
  return 0
}

# oscal-cli sub-commands are per-model: `catalog`, `profile`, `mapping`,
# etc. Pick the right one based on the path or content marker. Note:
# oscal-cli 1.0.3 has NO mapping-collection sub-command — we special-case
# it above with an xmllint fallback.
_oscal_command_for() {
  case "$1" in
    *catalog*) echo "catalog" ;;
    *profile*) echo "profile" ;;
    *mapping*) echo "mapping-collection" ;;
    *) echo "catalog" ;;
  esac
}

oscal_convert() {
  local input="$1" target="$2" output="$3"
  oscal-cli "$(_oscal_command_for "$input")" convert --to="$target" --overwrite "$input" "$output" 2>&1
}

diff_canonical() {
  # Re-convert both sides through oscal-cli so any whitespace / attribute-order
  # quirks line up, then byte-diff.
  local xml="$1" peer="$2" target="$3" prefix="$4"
  local from_xml="$WORK/$prefix.from-xml.$target"
  local from_peer="$WORK/$prefix.from-peer.$target"
  if ! oscal_convert "$xml" "$target" "$from_xml" > "$WORK/$prefix.from-xml.log"; then
    return 2  # conversion failed
  fi
  if ! oscal_convert "$peer" "$target" "$from_peer" > "$WORK/$prefix.from-peer.log"; then
    return 2
  fi
  if diff -q "$from_xml" "$from_peer" > /dev/null 2>&1; then
    return 0  # no drift
  fi
  diff -u "$from_xml" "$from_peer" > "$WORK/$prefix.$target.patch" || true
  return 1  # drift
}

# ---------------------------------------------------------------------
# Walk snapshot directories.
# ---------------------------------------------------------------------

shopt -s nullglob
SHAS=()
for d in "$SNAPSHOT_BASE"/*/; do
  SHAS+=("$(basename "$d")")
done

if [ ${#SHAS[@]} -eq 0 ]; then
  mark "_No snapshot subdirectories found under \`$SNAPSHOT_BASE\`._"
  exit 0
fi

for SHA in "${SHAS[@]}"; do
  SROOT="$SNAPSHOT_BASE/$SHA"
  mark "## snapshot \`$SHA\`"
  mark ""

  for entry in "${ARTIFACTS[@]}"; do
    IFS='|' read -r label xml_rel json_rel yaml_rel <<< "$entry"
    xml="$SROOT/$xml_rel"
    json="${json_rel:+$SROOT/$json_rel}"
    yaml="${yaml_rel:+$SROOT/$yaml_rel}"

    mark "### $label"

    if [ ! -f "$xml" ]; then
      mark "- ⚪ XML missing — skipping artifact."
      mark ""
      continue
    fi

    # --- 1. Validate each pinned file. ---
    oscal_validate "$xml"
    case $? in
      0) mark "- ✅ XML validates" ;;
      3) mark "- ⚪ XML well-formedness not checked (no oscal-cli model + no xmllint)" ;;
      *) mark "- ⚠️ XML does NOT validate — see \`$label-xml-validate.log\`"
         oscal-cli "$(_oscal_command_for "$xml")" validate "$xml" \
           > "$WORK/$SHA.$label.xml-validate.log" 2>&1 || true ;;
    esac
    for peer in "$json" "$yaml"; do
      [ -n "$peer" ] || continue
      if [ ! -f "$peer" ]; then
        mark "- ⚪ peer \`$(basename "$peer")\` missing"
        continue
      fi
      ext="${peer##*.}"
      if oscal_validate "$peer"; then
        mark "- ✅ $ext validates as OSCAL"
      else
        mark "- ⚠️ $ext does NOT validate as OSCAL — see \`$label-$ext-validate.log\`"
        oscal-cli "$(_oscal_command_for "$peer")" validate "$peer" \
          > "$WORK/$SHA.$label.$ext-validate.log" 2>&1 || true
      fi
    done

    # --- 2. Canonicalized round-trip diffs. ---
    for peer in "$json" "$yaml"; do
      [ -n "$peer" ] || continue
      [ -f "$peer" ] || continue
      ext="${peer##*.}"
      prefix="$SHA.$label"
      if diff_canonical "$xml" "$peer" "$ext" "$prefix"; then
        mark "- ✅ canonicalized XML↔$ext byte-equivalent"
      else
        case $? in
          1) mark "- ⚠️ canonicalized XML↔$ext drift — see \`$prefix.$ext.patch\`" ;;
          2) mark "- ⚠️ conversion failed (cannot diff) — see \`$prefix.from-*.log\`" ;;
        esac
      fi
    done

    mark ""
  done
done

mark "---"
mark ""
mark "_Generated by \`scripts/fedramp_cr26_roundtrip.sh\` — advisory check per ADR-061 D4._"

exit 0
