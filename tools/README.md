# uiao-core/tools

Python tooling that enforces canon governance and propagates canonical artifacts into `uiao-docs`. All tools share the pinned dependency set in `requirements.txt`.

## Install

```powershell
# One-time, from uiao-core root
python -m pip install -r tools\requirements.txt
```

## Tool reference

| Tool | Purpose | Typical invocation |
|---|---|---|
| `sync_canon.py` | Cross-repo sync: reads both adapter registries + schema, scans `uiao-docs` customer-documentation tree, reports drift, scaffolds missing folders. | `python tools/sync_canon.py --core-root . --docs-root ../uiao-docs --scaffold` |
| `metadata_validator.py` | Schema-validates YAML/JSON frontmatter across canon artifacts. | (existing — see file header) |
| `drift_detector.py` | Scans for metadata drift between canon and working artifacts. | (existing — see file header) |
| `appendix_indexer.py` | Indexes appendix artifacts for dashboard + publishing. | (existing — see file header) |
| `dashboard_exporter.py` | Exports governance dashboard JSON. | (existing — see file header) |

## `sync_canon.py` — detailed

### Modes

| Flag | Writes? | Exit code semantics |
|---|---|---|
| `--check-only` | no | `0` = clean, `1` = drift detected, `2` = schema error |
| `--scaffold` | yes | `0` = clean (nothing to do), `1` = we scaffolded or remediated drift (CI should open PR), `2` = schema error |
| _(default)_ | yes | same as `--scaffold` |
| `--json` | n/a | emits machine-readable report to stdout in addition to the above |

### What it writes

For every adapter in either registry, in each of the two adapter document trees (`adapter-technical-specifications/` and `adapter-validation-suites/`), `sync_canon.py` ensures:

```
<tree>/<adapter-id>/
├── <kind>-<adapter-id>.md    # ATS or AVS, with canonical YAML frontmatter
├── IMAGE-PROMPTS.md          # seed file for image generation pipeline
└── images/
    └── .gitkeep
```

The frontmatter block is **generated from canon** and regenerated whenever the registry entry changes. The markdown body is **safe to author** — `sync_canon.py` only touches the body if the primary file is missing or empty.

### What it doesn't do

- **Never deletes.** Orphan folders (in docs tree but not in canon) are reported as drift; a human decides whether to retire them.
- **Never writes outside the two adapter trees.** Domain trees (`modernization-technical-specifications/`, `modernization-validation-suites/`) are separate and out of scope for the current sync.
- **Never runs cross-network.** Reads only the local filesystem; all cross-repo work happens at the workflow layer via `repository_dispatch`.

### Running locally

```powershell
# Both repos checked out side by side at C:\Users\whale
cd C:\Users\whale\uiao-core
python tools\sync_canon.py --core-root . --docs-root ..\uiao-docs --check-only
```

Add `--scaffold` to write. Add `--json` to emit a machine-readable report (pipe to a file for CI artifacts).

### Testing

`sync_canon.py` is deterministic and idempotent. To verify:

```powershell
python tools\sync_canon.py --core-root . --docs-root ..\uiao-docs --scaffold
# Expect exit code 1 if new folders were created, 0 if already synced

python tools\sync_canon.py --core-root . --docs-root ..\uiao-docs --check-only
# Expect exit code 0 after a successful scaffold run
```

## Cross-repo sync workflows

The canon→docs propagation runs through two GitHub Actions workflows:

| Side | File | Trigger | Action |
|---|---|---|---|
| Dispatch | `uiao-core/.github/workflows/canon-sync-dispatch.yml` | Push to `main` modifying `canon/adapter-registry.yaml`, `canon/modernization-registry.yaml`, or `schemas/adapter-registry/**` | Validates registries, sends `canon-updated` repository_dispatch to `WhalerMike/uiao-docs` |
| Receive | `uiao-docs/.github/workflows/canon-sync-receive.yml` | `canon-updated` repository_dispatch (or manual `workflow_dispatch`) | Checks out `uiao-core`, runs `sync_canon.py --scaffold`, opens a labeled PR (`canon-sync`) with peter-evans/create-pull-request |

### Required secret: `CANON_SYNC_DISPATCH_TOKEN`

Both workflows use the same secret — a GitHub Personal Access Token with cross-repo permissions.

**Recommended: fine-grained PAT.**

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token.
2. Token name: `UIAO canon-sync dispatch`.
3. Resource owner: your account (`WhalerMike`).
4. Repository access: "Only select repositories" → pick **both** `WhalerMike/uiao-core` and `WhalerMike/uiao-docs`.
5. Repository permissions:
   - **Contents: Read and write** (needed for the receiver to check out `uiao-core` and to push the `canon-sync/*` branch to `uiao-docs`).
   - **Pull requests: Read and write** (needed to open the PR).
   - **Metadata: Read-only** (auto-selected).
6. Expiration: 90 days is a reasonable starting point; set a calendar reminder to rotate.
7. Generate the token and copy the value (you only see it once).
8. Add it as a secret named `CANON_SYNC_DISPATCH_TOKEN` in **both** repositories:
   - `WhalerMike/uiao-core` → Settings → Secrets and variables → Actions → New repository secret.
   - Same on `WhalerMike/uiao-docs`.

**Alternative: classic PAT with `repo` scope.** Works but overprovisioned — prefer fine-grained.

### Rotation

When the PAT expires, regenerate and update the secret in both repos. The workflows pick up the new secret automatically on next run.

### Manual re-sync

If you need to force a sync (e.g., after a PAT rotation or to re-scaffold after a merge conflict):

```
Actions → Canon sync — receive from uiao-core → Run workflow → (optional) specify ref → Run
```

This triggers the receiver in `workflow_dispatch` mode against `main` (or your chosen ref) of `uiao-core`.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Receiver workflow fails with `Bad credentials` | PAT expired or missing | Regenerate PAT, update `CANON_SYNC_DISPATCH_TOKEN` secret in both repos |
| Dispatcher runs but receiver never triggers | Dispatch token lacks Contents:write on target repo | Verify fine-grained PAT includes `uiao-docs` with Contents: Read and write |
| `peter-evans/create-pull-request` says "Bypassed rule violations" | Required status check not yet registered as a check on `uiao-docs` | Expected for now — will resolve in Step 6 (CI workflows) |
| `sync_canon.py` reports orphan drift | Folder exists in `uiao-docs` but no adapter with that id in either registry | Either add the adapter to canon, or manually retire the folder. Tool never deletes. |
| Schema validation fails on dispatch | YAML edit introduced a schema violation | Fix locally, run `python tools/sync_canon.py --core-root . --docs-root ../uiao-docs --check-only` to verify, then push |
