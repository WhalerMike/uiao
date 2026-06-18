## Summary

<!-- What this PR does and why. Focus on the "why" — reviewers can read the diff for "what". -->

## Diff stat

<!-- Output of `git diff --stat main...HEAD | tail -5`. Helps reviewers size the change. -->

## Module(s) touched

- [ ] `src/uiao/canon/` (canon authority)
- [ ] `src/uiao/` (Python implementation — non-canon)
- [ ] `tests/` (test suite)
- [ ] `docs/` (derived documentation)
- [ ] `.github/` (CI / workflows / repo config)

## Canon impact

- [ ] **None** — no files under `src/uiao/canon/**` changed
- [ ] New canon document (new `UIAO_NNN` ID allocated in `src/uiao/canon/document-registry.yaml`)
- [ ] Updated existing canon document (cite the ID)
- [ ] ADR added / superseded (cite ADR-NNN)
- [ ] Registry edit (adapter-registry / modernization-registry / document-registry)

## Test plan

- [ ] Substrate walker passes (`uiao substrate walk`)
- [ ] Ruff passes (`ruff check . && ruff format --check .`)
- [ ] Pytest passes (`pytest -q`)
- [ ] Schema validation passes (automatic in CI)
- [ ] Quarto render passes (if `docs/` touched)
- [ ] Other: <!-- describe -->

## Checklist

- [ ] Commit convention followed (`<verb>: <module-or-area> — <description>`; see AGENTS.md)
- [ ] No hardcoded canon paths — all runtime paths via `$UIAO_WORKSPACE_ROOT` or `--canon-path`
- [ ] CODEOWNERS auto-requested the right owner
- [ ] Related ADR(s) linked in the PR body if this changes doctrine
