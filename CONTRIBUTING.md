# Contributing to UIAO

Thanks for your interest in UIAO — the Unified Identity-Addressing-Overlay
Architecture substrate. This is a FedRAMP-Moderate-oriented governance OS
with strong canon invariants, so contribution flow is more disciplined
than a typical OSS project. The payoff: every change is traceable,
schema-validated, and drift-scanned before it lands.

[AGENTS.md](AGENTS.md) is the agent-facing companion to this document
and the source of truth for module topology, invariants, and the CI
stack — when this guide and AGENTS.md diverge, AGENTS.md wins.

## Quick start

### macOS / Linux

```bash
git clone https://github.com/WhalerMike/uiao.git
cd uiao
export UIAO_WORKSPACE_ROOT="$(pwd)"
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uiao substrate walk
```

### Windows (PowerShell)

```powershell
git clone https://github.com/WhalerMike/uiao.git
cd uiao
$env:UIAO_WORKSPACE_ROOT = (Get-Location).Path
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
uiao substrate walk
```

If `uiao substrate walk` exits 0, the substrate is intact.

## Repository layout

UIAO is a **single installable Python package** rooted at
[`src/uiao/`](src/uiao/). The pre-consolidation `core/`, `impl/`, and
`gos/` directories no longer exist (ADR-028 + ADR-032).

| Path | Role |
|---|---|
| [`src/uiao/`](src/uiao/) | The `uiao` distribution — runtime code, canon, schemas, rules, KSI, adapters, CLI |
| [`src/uiao/canon/`](src/uiao/canon/) | Canon authority (SSOT) — governance docs, ADRs, registries, control library, specs |
| [`src/uiao/schemas/`](src/uiao/schemas/) | JSON Schemas (drafts 07 and 2020-12) for canon, registries, manifests |
| [`src/uiao/adapters/`](src/uiao/adapters/) | Modernization and conformance adapters |
| [`src/uiao/cli/`](src/uiao/cli/) | Typer CLI — entry point `uiao.cli.app:app` |
| [`tests/`](tests/) | Pytest suite — unit, integration, adapter conformance, substrate drift |
| [`docs/`](docs/) | Quarto documentation source (`.qmd`, `.md`, `.yml`) |
| [`scripts/`](scripts/) | Workspace tooling — bootstrap, validators, generators |
| [`inbox/`](inbox/) | Draft staging — not canon. Promote to `src/uiao/canon/` or `docs/` when ready |
| [`.github/workflows/`](.github/workflows/) | CI — see [AGENTS.md § CI stack](AGENTS.md#ci-stack-all-live-at-repo-root-githubworkflows) |

Module topology is also declared machine-readably in
[`src/uiao/canon/substrate-manifest.yaml`](src/uiao/canon/substrate-manifest.yaml)
(UIAO_200).

## The three things you need to know

1. **Canon lives under `src/uiao/canon/` only.** Anything in `docs/`,
   adapters, generators, or CLI must *consume* canon, not define it.
   Code reads canon via `importlib.resources`, never by reaching outside
   its package (invariant I4).

2. **Every canon document has schema-validated frontmatter.** If you add
   a `.md` under `src/uiao/canon/` with a `document_id:`, it must match
   `^UIAO_\d{3}$` and be allocated in
   [`src/uiao/canon/document-registry.yaml`](src/uiao/canon/document-registry.yaml).
   CI enforces this via `metadata-validator.yml`.

3. **Adapters are a dual-axis taxonomy.** Every adapter declares:
   - `class:` — `modernization` (change-making) or `conformance` (read-only)
   - `mission-class:` — `identity | telemetry | policy | enforcement | integration`

   See
   [UIAO_003](src/uiao/canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md).

## Commit convention

Per [AGENTS.md § Commit convention](AGENTS.md#commit-convention):

```
<verb>: <module-or-area> — <description>
```

Common verbs: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `ci`.
Use a scope prefix (e.g. `feat(adapters/bluecat):`) when it clarifies
blast radius. Cross-cutting commits are permitted — describe the
cross-cut in the body.

Examples:
- `feat: adapters — add Defender-for-Endpoint posture adapter`
- `fix(canon): correct schema ref in modernization-registry.yaml`
- `docs(findings): land FINDING-002 internal remedy`

## Development workflow

### 1. Branch

```bash
git checkout -b fix/cyberark-adapter-timeout
```

### 2. Run checks locally

The repo Makefile wraps the most common gates:

```bash
make lint            # ruff check + format check
make test            # pytest -q
make walk            # uiao substrate walk
make check-links     # lychee on docs
```

Run full pytest plus mypy directly when you need them:

```bash
pytest -q
mypy src/uiao
```

### 3. Open the PR

Use the PR template
([`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md)).
Fill in **Summary**, **Diff stat**, **Test plan**.

### 4. CI

Ten workflows run on every PR — see
[AGENTS.md § CI stack](AGENTS.md#ci-stack-all-live-at-repo-root-githubworkflows)
for the full list. All are blocking except `link-check.yml` (soft-fail).

## Repository invariants

The monorepo structure and packaging rules are load-bearing. Six named
technical invariants (I1–I6) are defined in
[AGENTS.md § Repository Invariants](AGENTS.md#repository-invariants):

- **I1** — `src/uiao/` is a single regular package
- **I2** — Single CLI entry point: `uiao.cli.app:app`
- **I3** — One `pyproject.toml`, one editable install
- **I4** — Canon is a read-only dependency of code
- **I5** — Canon changes flow through the canon-change process
- **I6** — CLI commands live under sub-apps (ADR-046)

Any PR that modifies an invariant requires an ADR.

## Canon-change protocol

If your PR modifies `src/uiao/canon/**`:

1. **Allocate a `UIAO_NNN` ID first** in
   [`src/uiao/canon/document-registry.yaml`](src/uiao/canon/document-registry.yaml).
   Reserved ranges:
   - `UIAO_001` — Single Source of Truth
   - `UIAO_002–UIAO_099` — Top-level canon documents
   - `UIAO_100–UIAO_199` — `canon/specs/` subsystem specifications
   - `UIAO_200–UIAO_299` — Operational / runtime artifacts
   - `UIAO_900–UIAO_999` — Test fixtures

2. **ADRs are append-only.** If you supersede a prior ADR, add a
   SUPERSEDED callout at the section top and cite the newer ADR in
   both directions. Don't delete or rewrite decision text.

3. **Schema-validate before pushing.** CI will catch issues, but local
   validation catches them earlier.

## Activating a reserved adapter

Promoting an adapter from `status: reserved, phase: phase-planning` to
`active/phase-1` requires:

- [ ] Implementation at `src/uiao/adapters/<adapter_id>_adapter.py`
- [ ] Adapter inherits `DatabaseAdapterBase` and implements all 7
      canonical domain methods
- [ ] At least one test in `tests/adapters/test_<adapter_id>_*.py` passes
- [ ] Registry entry in
      [`src/uiao/canon/modernization-registry.yaml`](src/uiao/canon/modernization-registry.yaml)
      or
      [`src/uiao/canon/adapter-registry.yaml`](src/uiao/canon/adapter-registry.yaml)
      has all required fields per
      [`src/uiao/schemas/adapter-registry/adapter-registry.schema.json`](src/uiao/schemas/adapter-registry/adapter-registry.schema.json)
- [ ] `status:` and `phase:` fields flipped in the registry entry as
      the final commit

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md).
Be respectful, constructive, and collaborative.

## License

Apache 2.0. By contributing, you agree your contributions are licensed
under the same terms.

## Questions

Open a GitHub discussion or an issue using the appropriate template.
