# =============================================================================
# stage-4-batch-5.1.6-schema-rewrite.ps1
# Phase D Stage 5, Batch 5.1.6 — align schemas/metadata-schema.json to the
#                                contract actually enforced by
#                                tools/metadata_validator.py
# -----------------------------------------------------------------------------
# Context:
#   The validator does NOT read the schema at runtime (--schema arg is accepted
#   but ignored; jsonschema import is optional and never invoked). Every rule
#   is hardcoded in validate_frontmatter(). This batch makes the schema an
#   honest description of those hardcoded rules.
#
# Scope:
#   - Rewrite schemas/metadata-schema.json to:
#       * declare the 9 required fields the validator enforces
#       * mirror every pattern and enum
#       * express the DERIVED-requires-provenance rule via if/then
#       * document the non-schema-expressible rules under x-validator-rules
#   - Nothing else.
#
# Safety:
#   - Does NOT change the validator.
#   - Does NOT touch any canon file.
#   - Does NOT push.
#   - Validator behavior is unchanged (it ignores the schema). A before/after
#     smoke run must produce identical blocking counts.
# =============================================================================

$ErrorActionPreference = 'Stop'
$CoreDir    = 'C:\Users\whale\uiao-core'
$SchemaPath = Join-Path $CoreDir 'schemas\metadata-schema.json'

function Write-Step($msg) { Write-Host "`n>>> $msg" -ForegroundColor Cyan }
function Write-OK($msg)   { Write-Host "[OK]  $msg"  -ForegroundColor Green }
function Write-Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red }

Push-Location $CoreDir
try {
    # --- 0. Preflight -------------------------------------------------------
    Write-Step 'Preflight'
    $branch = git rev-parse --abbrev-ref HEAD
    if ($branch -ne 'main') { Write-Fail "not on main (on $branch)"; exit 1 }
    if (-not (Test-Path $SchemaPath)) {
        Write-Fail "missing: $SchemaPath — has Batch 5.1 landed?"; exit 1
    }
    $clean = git diff --quiet; $dirtyStaged = $LASTEXITCODE
    git diff --cached --quiet; $dirtyIndex = $LASTEXITCODE
    if ($dirtyStaged -ne 0 -or $dirtyIndex -ne 0) {
        Write-Host '  working tree has pending changes — review with git status' -ForegroundColor Yellow
        git status --short
        Write-Fail 'aborting: working tree not clean'
        exit 1
    }
    Write-OK "on main; schema present; working tree clean"

    # --- 1. BEFORE smoke: validator output pre-rewrite ---------------------
    Write-Step 'Step 1 — BEFORE smoke (validator blocking count)'
    New-Item -ItemType Directory -Force -Path 'reports' | Out-Null
    python tools/metadata_validator.py `
        --path canon/ `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-6-before.json `
        --ci 2>&1 | Out-Null
    $beforeExit = $LASTEXITCODE
    $beforeBlocking = (Get-Content reports/_5-1-6-before.json -Raw | ConvertFrom-Json).blocking
    Write-OK "before: exit=$beforeExit blocking=$beforeBlocking"

    # --- 2. Write new schema -----------------------------------------------
    Write-Step 'Step 2 — write aligned schema'
    $newSchema = @'
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://uiao.example.org/schemas/metadata-schema.json",
  "title": "UIAO Governance Metadata Schema",
  "description": "Canonical metadata contract for UIAO governance artifacts (canon/, playbooks/, appendices/). This schema documents the rules enforced by tools/metadata_validator.py. The validator currently hardcodes these rules and does not consume the schema at runtime; this schema is maintained as the single source of truth for the metadata contract so that (a) humans and tooling can read it, and (b) a future validator rewrite can switch to schema-driven validation without re-deriving the contract. Rules that are not purely JSON-Schema-expressible are documented under x-validator-rules.",
  "type": "object",
  "required": [
    "document_id",
    "title",
    "version",
    "status",
    "classification",
    "owner",
    "created_at",
    "updated_at",
    "boundary"
  ],
  "properties": {
    "document_id": {
      "type": "string",
      "pattern": "^UIAO_\\d{3}$",
      "description": "Canonical UIAO artifact identifier. Format: UIAO_NNN (exactly three digits). Reserved ranges are tracked in the canon registry."
    },
    "title": {
      "type": "string",
      "minLength": 1
    },
    "version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+$",
      "description": "Semantic major.minor version (e.g., 1.0). Patch component is not used at the metadata layer."
    },
    "status": {
      "type": "string",
      "enum": ["Current", "Draft", "Deprecated", "Needs Replacing", "Needs Creating"],
      "description": "Lifecycle state. Not to be confused with classification, which captures authority, not lifecycle."
    },
    "classification": {
      "type": "string",
      "enum": ["CANONICAL", "DERIVED", "OPERATIONAL"],
      "description": "Authority tier. CANONICAL = source of truth; DERIVED = generated from canonical source (requires provenance block); OPERATIONAL = runtime/process artifacts."
    },
    "owner": {
      "type": "string",
      "minLength": 1
    },
    "created_at": {
      "type": "string",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}(T\\d{2}:\\d{2}:\\d{2})?",
      "description": "ISO 8601 date (YYYY-MM-DD) or datetime prefix. Validator permits trailing precision/timezone suffixes."
    },
    "updated_at": {
      "type": "string",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}(T\\d{2}:\\d{2}:\\d{2})?",
      "description": "ISO 8601 date or datetime. Must be >= created_at (enforced by the validator via string comparison; see x-validator-rules.updated_at_monotonic)."
    },
    "boundary": {
      "type": "string",
      "enum": ["GCC-Moderate"],
      "description": "Compliance boundary. Only GCC-Moderate is permitted unless boundary-exception is true (Amazon Connect Contact Center is the sole documented Commercial Cloud exception under the UIAO canon)."
    },
    "boundary-exception": {
      "type": "boolean",
      "description": "Escape hatch for the boundary enum and the body-text boundary-violation scan. Use sparingly and document the justification in the body."
    },
    "provenance": {
      "type": "object",
      "description": "Required when classification == 'DERIVED'. Ties a derived artifact to its canonical source.",
      "required": ["source", "version", "derived_at", "derived_by"],
      "properties": {
        "source": {
          "type": "string",
          "description": "Path to the canonical source artifact. The validator verifies that this path resolves under the base path or its parent."
        },
        "version": { "type": "string" },
        "derived_at": { "type": "string" },
        "derived_by": { "type": "string" }
      },
      "additionalProperties": true
    }
  },
  "additionalProperties": true,
  "allOf": [
    {
      "if": {
        "required": ["classification"],
        "properties": { "classification": { "const": "DERIVED" } }
      },
      "then": { "required": ["provenance"] }
    }
  ],
  "x-validator-rules": {
    "description": "Rules enforced by tools/metadata_validator.py that are not purely JSON-Schema-expressible. Update this block if you modify the validator.",
    "updated_at_monotonic": "updated_at string comparison >= created_at string comparison; BLOCKING otherwise.",
    "provenance_source_resolution": "When classification == 'DERIVED', provenance.source must resolve to a path that exists under base_path or base_path.parent.",
    "body_boundary_violations": "Body text matching /GCC[\\s-]?High|DoD|IL[456]|Azure\\s+(IaaS|PaaS)|azure\\.com/i is BLOCKING unless boundary-exception == true.",
    "body_mermaid": "Body containing a ```mermaid fenced block raises a WARNING (PlantUML is the preferred diagram format).",
    "walker_skip": "Files named INDEX.md and README.md are skipped by the directory walker and therefore exempt from metadata rules."
  }
}
'@
    # Write as UTF-8 without BOM so git sees a clean single-line-ending file
    [System.IO.File]::WriteAllText(
        (Resolve-Path $SchemaPath),
        $newSchema,
        (New-Object System.Text.UTF8Encoding($false))
    )
    Write-OK 'schema rewritten'

    # --- 3. Validate the new schema is itself valid JSON -------------------
    Write-Step 'Step 3 — confirm new schema parses as JSON'
    python -c "import json; json.load(open(r'schemas/metadata-schema.json', encoding='utf-8'))"
    if ($LASTEXITCODE -ne 0) { Write-Fail 'new schema failed to parse as JSON'; exit 1 }
    Write-OK 'schema parses cleanly'

    # --- 4. Optional: validate new schema against JSON Schema metaschema ---
    Write-Step 'Step 4 — validate new schema against draft 2020-12 metaschema (best-effort)'
    $metaCheck = python -c @"
import json, sys
try:
    from jsonschema import Draft202012Validator
except ImportError:
    print('jsonschema not installed — skipping metaschema check'); sys.exit(0)
schema = json.load(open('schemas/metadata-schema.json', encoding='utf-8'))
try:
    Draft202012Validator.check_schema(schema)
    print('metaschema OK')
except Exception as e:
    print(f'metaschema FAIL: {e}'); sys.exit(2)
"@ 2>&1
    Write-Host $metaCheck
    if ($LASTEXITCODE -eq 2) { Write-Fail 'new schema violates JSON Schema draft 2020-12'; exit 1 }
    Write-OK 'metaschema gate passed (or skipped if jsonschema missing)'

    # --- 5. AFTER smoke: validator output post-rewrite ---------------------
    Write-Step 'Step 5 — AFTER smoke (validator blocking count — expected identical)'
    python tools/metadata_validator.py `
        --path canon/ `
        --schema schemas/metadata-schema.json `
        --output reports/_5-1-6-after.json `
        --ci 2>&1 | Out-Null
    $afterExit = $LASTEXITCODE
    $afterBlocking = (Get-Content reports/_5-1-6-after.json -Raw | ConvertFrom-Json).blocking
    Write-OK "after: exit=$afterExit blocking=$afterBlocking"

    if ($beforeBlocking -ne $afterBlocking) {
        Write-Fail "blocking count changed: before=$beforeBlocking after=$afterBlocking"
        Write-Fail 'validator should NOT read the schema — this is unexpected. Aborting before commit.'
        exit 1
    }
    Write-OK 'validator behavior unchanged (as expected — schema is documentation)'

    # --- 6. Cleanup temporary reports --------------------------------------
    Remove-Item reports/_5-1-6-before.json -Force -ErrorAction SilentlyContinue
    Remove-Item reports/_5-1-6-after.json  -Force -ErrorAction SilentlyContinue

    # --- 7. Stage + commit (no push) ---------------------------------------
    Write-Step 'Step 7 — stage + commit (no push)'
    git add schemas/metadata-schema.json

    Write-Host ''
    Write-Host '--- staged summary ---' -ForegroundColor Cyan
    git status --short

    $msgFile = Join-Path $env:TEMP 'uiao-core-5-1-6-msg.txt'
    @(
        '[UIAO-CORE] ENFORCE: align metadata-schema.json to validator contract',
        '',
        'The validator (tools/metadata_validator.py) hardcodes every metadata',
        'rule and does not consume the schema at runtime. This commit rewrites',
        'schemas/metadata-schema.json so it is an accurate, machine-readable',
        'description of the rules the validator actually enforces.',
        '',
        '- required: document_id, title, version, status, classification,',
        '  owner, created_at, updated_at, boundary',
        '- document_id pattern ^UIAO_\d{3}$, version pattern ^\d+\.\d+$,',
        '  ISO-8601 prefix pattern for created_at/updated_at',
        '- status enum: Current, Draft, Deprecated, Needs Replacing,',
        '  Needs Creating',
        '- classification enum: CANONICAL, DERIVED, OPERATIONAL',
        '- boundary: GCC-Moderate (with boundary-exception escape hatch)',
        '- if classification == DERIVED then provenance is required',
        '',
        'Non-schema-expressible rules (updated_at monotonicity, provenance',
        'source path resolution, body-text boundary-violation scan, Mermaid',
        'warning, INDEX.md/README.md walker skip) are documented under',
        'x-validator-rules.',
        '',
        'Behavior: validator output identical before and after (verified by',
        'before/after smoke run in the deploy script).'
    ) | Set-Content -Path $msgFile -Encoding UTF8

    git commit -F $msgFile
    Remove-Item $msgFile -Force

    Write-Host ''
    Write-OK 'Commit created locally. Review with: git show HEAD'
    Write-Host 'Next step (manual):' -ForegroundColor Yellow
    Write-Host '  git -C C:\Users\whale\uiao-core push origin main' -ForegroundColor Yellow
    Write-Host ''
    Write-Host 'After push, ready for:' -ForegroundColor Yellow
    Write-Host '  5.1.7 — document_id assignment + frontmatter stubs for the 22 no-frontmatter files' -ForegroundColor Yellow
    Write-Host '  5.1.8 — surgical fix for UIAO_002 frontmatter' -ForegroundColor Yellow
}
finally {
    Pop-Location
}
