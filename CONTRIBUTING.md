# Contributing to UIAO

Thanks for your interest in UIAO — the Unified Identity-Addressing-Overlay Architecture substrate. This is a FedRAMP-Moderate-oriented governance OS with strong canon invariants, so contribution flow is more disciplined than a typical OSS project. The payoff: every change is traceable, schema-validated, and drift-scanned before it lands.

## Quick start

```bash
git clone https://github.com/WhalerMike/uiao.git
cd uiao
export UIAO_WORKSPACE_ROOT="$(pwd)"   # canon-consumer rule: never hardcode paths

# Install the Python package (for impl/)
pip install -e ./impl

# Verify the substrate is intact
uiao substrate walk
```

If `uiao substrate walk` prints `PASS — no drift detected`, the repo is healthy.

## Repository map

| Module | Role | Authority |
|---|---|---|
| [`core/`](core/) | Canonical governance | Authoritative — schemas, canon docs, control library, ADRs |
| [`docs/`](docs/) | Derived documentation | Consumer — every doc traces provenance to `core/` canon |
| [`impl/`](impl/) | Python implementation | Consumer — CLI, generators, adapters, tests |

Declared machine-readably in [`src/uiao/canon/substrate-manifest.yaml`](src/uiao/canon/substrate-manifest.yaml) (UIAO_200).

## The three things you need to know before contributing

1. **Canon lives in `core/` only.** If your change creates a new canonical governance document (SSOT, document registry, adapter registry, spec, ADR, crosswalk), it belongs under `src/uiao/canon/`. Anything in `docs/` or `impl/` must **consume** canon, not define it. Enforced by the canon-consumer rule in [`impl/.claude/rules/canon-consumer.md`](impl/.claude/rules/canon-consumer.md).

2. **Every canon document has a schema-validated frontmatter.** If you add a `.md` under `src/uiao/canon/` with a `document_id:`, it must match `^UIAO_\d{3}$` and be allocated in [`src/uiao/canon/document-registry.yaml`](src/uiao/canon/document-registry.yaml). CI enforces this via `.github/workflows/metadata-validator.yml`.

3. **Adapters are a dual-axis taxonomy.** Every adapter declares:
   - `class:` — `modernization` (change-making) or `conformance` (read-only)
   - `mission-class:` — `identity | telemetry | policy | enforcement | integration`

   See [`src/uiao/canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md`](src/uiao/canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md).

## Commit convention

Commits touching a specific module use a module-prefixed convention:

```
[UIAO-CORE] <verb>: <artifact-id> — <short description>
[UIAO-DOCS] <verb>: <artifact-id> — <short description>
[UIAO-IMPL] <verb>: <module> — <short description>
```

Verbs:
- `CORE`: CREATE, UPDATE, FIX, ENFORCE, MIGRATE, DEPRECATE
- `DOCS`: CREATE, UPDATE, FIX, PUBLISH, MIGRATE, DEPRECATE
- `IMPL`: CREATE, UPDATE, FIX, REFACTOR, TEST, DEPRECATE

Cross-module commits (touching more than one top-level module) should be split into per-module commits when possible. If they must stay combined, use the `[UIAO]` generic prefix and describe the cross-cutting nature in the body.

## Development workflow

### 1. Branch

Create a branch off `main` with a descriptive kebab-case name:

```bash
git checkout -b fix/cyberark-adapter-timeout
git checkout -b feat/mainframe-adapter-activation
```

### 2. Make the change

Follow the scope rules above. If your change touches canon, read the relevant ADR history under [`src/uiao/canon/adr/`](src/uiao/canon/adr/) to understand prior decisions.

### 3. Run the checks locally

```bash
# Python lint + format
cd impl
ruff check .
ruff format --check .

# Tests
pytest -q                           # full suite (~10s)
pytest tests/test_my_change.py -q   # targeted

# Substrate walker
cd ..
uiao substrate walk

# Canon frontmatter validation (for canon edits)
python -c "
import json, pathlib, re, sys, yaml
from jsonschema import Draft202012Validator
schema = json.load(open('src/uiao/schemas/metadata-schema.json'))
v = Draft202012Validator(schema)
fm = re.compile(r'^---\s*\n(.*?)\n---\s*(?:\n|$)', re.DOTALL)
for md in pathlib.Path('core/canon').rglob('*.md'):
    m = fm.match(md.read_text())
    if not m: continue
    data = yaml.safe_load(m.group(1)) or {}
    if 'document_id' not in data: continue
    errs = list(v.iter_errors(data))
    if errs:
        print(f'{md}: {errs[0].message}')
        sys.exit(1)
print('canon frontmatter: PASS')
"
```

### 4. Open the PR

Use the appropriate PR template (auto-applied from `.github/PULL_REQUEST_TEMPLATE.md`). Fill in:
- **Summary** — what and why (the "why" matters more)
- **Diff stat** — helps reviewers size the change
- **Test plan** — what you ran and what passed

### 5. CI

Seven workflows run on every PR. See [`.github/workflows/`](.github/workflows/). All are blocking except `link-check.yml` (soft-fail baseline).

## Canon-change protocol

If your PR modifies `src/uiao/canon/**`:

1. **Search for the UIAO_NNN ID first.** Every new canon document needs a unique ID allocated in [`src/uiao/canon/document-registry.yaml`](src/uiao/canon/document-registry.yaml) before it's authored. Reserved ranges:
   - `UIAO_001` — Single Source of Truth
   - `UIAO_002–UIAO_099` — Top-level canon documents
   - `UIAO_100–UIAO_199` — `canon/specs/` subsystem specifications
   - `UIAO_200–UIAO_299` — Operational / runtime artifacts
   - `UIAO_900–UIAO_999` — Test fixtures

2. **ADRs are append-only.** If you supersede a prior ADR, add a SUPERSEDED callout at the section top and cite the newer ADR in both directions. Don't delete or rewrite decision text.

3. **Schema-validate before pushing.** CI will do this, but local validation catches issues early.

## Activating a reserved adapter

Promoting an adapter from `status: reserved, phase: phase-planning` → `active/phase-1` requires:

- [ ] Implementation exists at `impl/src/uiao/impl/adapters/<adapter_id>_adapter.py`
- [ ] Adapter inherits `DatabaseAdapterBase` and implements all 7 canonical domain methods
- [ ] At least one test in `impl/tests/test_<adapter_id>_*.py` passes
- [ ] Registry entry in `src/uiao/canon/modernization-registry.yaml` or `src/uiao/canon/adapter-registry.yaml` has all required fields per `src/uiao/schemas/adapter-registry/adapter-registry.schema.json`
- [ ] `status:` and `phase:` fields flipped in the registry entry as the final commit

See [PR #32 (cyberark activation)](https://github.com/WhalerMike/uiao/pull/32) as a canonical example.

## License

Apache 2.0. By contributing, you agree your contributions are licensed under the same terms.

## Questions

Open a GitHub discussion or an issue using the appropriate template.

## Repository invariants

The monorepo structure and packaging rules are load-bearing. Read [AGENTS.md § Repository Invariants](AGENTS.md#repository-invariants) before making changes. Any PR that modifies an invariant requires an ADR referencing ADR-031 (PEP 420 namespace package) or ADR-028 (monorepo consolidation), as applicable.

The five named technical invariants (I1 through I5) protect: the PEP 420 namespace, the CLI lazy-import bridge, the install order, Canon's read-only status for code, and the canon-change governance process.
