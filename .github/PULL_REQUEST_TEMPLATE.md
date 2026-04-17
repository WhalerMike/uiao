## Summary

<!-- What this PR does and why. Focus on the "why" — reviewers can read the diff for "what". -->

## Diff stat

<!-- Output of `git diff --stat main...HEAD | tail -5`. Helps reviewers size the change. -->

## Module(s) touched

- [ ] `core/` (canon authority)
- [ ] `docs/` (derived documentation)
- [ ] `impl/` (Python implementation)
- [ ] `.github/` (CI / workflows / repo config)

## Canon impact

- [ ] **None** — no files under `core/canon/**` changed
- [ ] New canon document (new `UIAO_NNN` ID allocated in `core/canon/document-registry.yaml`)
- [ ] Updated existing canon document (cite the ID)
- [ ] ADR added / superseded (cite ADR-NNN)
- [ ] Registry edit (adapter-registry / modernization-registry / document-registry)

## Test plan

- [ ] Substrate walker passes (`uiao substrate walk`)
- [ ] Ruff passes (`cd impl && ruff check .`)
- [ ] Pytest passes (`cd impl && pytest -q`)
- [ ] Schema validation passes (automatic in CI)
- [ ] Quarto render passes (if `docs/` touched)
- [ ] Other: <!-- describe -->

## Checklist

- [ ] Commit convention followed (`[UIAO-<MODULE>] <verb>: ...`)
- [ ] No hardcoded canon paths — all runtime paths via `$UIAO_WORKSPACE_ROOT` or `--canon-path`
- [ ] CODEOWNERS auto-requested the right owner
- [ ] Related ADR(s) linked in the PR body if this changes doctrine
