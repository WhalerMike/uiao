# History rewrite runbook — purge deleted binaries from git history

**Status: EXECUTED 2026-07-20 (per owner's "run now").** Results:

- Server pack 1.49 GiB → fresh clone `.git` **582 MB**; purge set was
  **2,191 paths** at cutover (2,189 deleted binaries + 2 Windows-invalid
  junk paths).
- Rewritten `main` = `7696b68c…`, tree `a8a5f931…` — **byte-identical**
  to the pre-rewrite tree (verified before push and on a fresh clone).
- All heads + tags force-pushed; GitHub Releases intact by tag name;
  PR #1302 survived on its rewritten branch; CI green on rewritten main.
- Pre-rewrite backup mirror parked at
  `C:\Users\whale\git\uiao-backup-preRewrite.git` (main was
  `bd05e021…`, tree `a8a5f931…`).
- **Stale-clone rule is now live:** any clone or worktree from before
  2026-07-20 (including `copilot-worktrees/*` and `uiao-wt-dems`) is
  read-only — re-clone before pushing anything.

The procedure below is retained for reference and for any future
rewrite (e.g. the legacy AI PNGs once an SVG-regeneration story exists).
Repo-review round 2 follow-through (2026-07-20). Executing this is a
one-way door for every existing clone — do not run outside a window.

## Dry-run result (2026-07-20, mirror clone, main @ `a2680e30` era)

| Metric | Before | After |
|---|---|---|
| Pack size | 1.63 GiB | **595.9 MiB** (−64%) |
| `main` tree hash | `236c01c4…` | `236c01c4…` — **byte-identical** |
| Commits on main | 1,459 | 1,449 (10 binary-only commits pruned as empty) |

Purge set: **2,098 binary paths** (`png/jpg/gif/pptx/docx/zip/pdf/mp4/
mp3/wav/xlsx/bin/crypt14`) that ever existed in history but are absent
from HEAD — i.e. every already-deleted/untracked binary's historical
blobs — plus **2 junk paths with commit-messages-as-filenames** that are
invalid on Windows and crash `git fast-import` until purged:

- `core/providers/azure/azure_adapter.py— ARC 6 adds real Azure queries.`
- `src/uiao_core/generators/fix(mypy): use or-empty-string pattern for PackageMetadata.get() in sbom.py`

Nothing in HEAD is touched: the ~620 legacy AI PNGs still referenced by
pages stay in the tree and in history. Purging *those* requires the
separate regeneration story (redraw as SVG per ADR-093) and is out of
scope here.

## What breaks, and for whom

- **Every commit hash changes** from the first rewritten commit forward.
- **Every existing clone and worktree is invalidated** — including the
  five `copilot-worktrees` checkouts and any Claude worktrees. A push
  from a stale clone would resurrect the old history; treat old clones
  as read-only and delete them after the cutover.
- **Open branches/PRs die**: anything not merged before the window must
  be rebased onto the rewritten history by hand (or recreated).
- **Old hashes in PR/issue text** stop resolving to commits (GitHub
  keeps old objects reachable via `refs/pull/*` server-side, so links
  degrade rather than 404, but fresh clones no longer download them —
  which is the point).
- **Tags are rewritten** (`v0.x`, kit tags). GitHub Releases stay
  attached by tag *name*; verify release assets after the push.

## Preconditions checklist (the window)

1. All PRs merged or closed; no unmerged branch anyone cares about.
2. All CoPilot / Claude sessions stopped; worktrees pruned.
3. Fresh backup mirror taken and parked outside the repo
   (`git clone --mirror <repo> uiao-backup-preRewrite.git`).
4. Announce: after the push, everyone re-clones; old clones are
   delete-only.

## Exact procedure

```bash
# 1. Fresh mirror
git clone --mirror https://github.com/WhalerMike/uiao.git uiao-rw.git
cd uiao-rw.git

# 2. Regenerate the purge list (binary paths absent from HEAD)
git -c core.quotepath=false log --all --format= --name-only |
  grep -aiE '\.(png|jpe?g|gif|pptx|docx|zip|pdf|mp4|mp3|wav|xlsx|bin|crypt14)$' |
  sort -u > /tmp/hist.txt
git -c core.quotepath=false ls-tree -r main --name-only |
  grep -aiE '\.(png|jpe?g|gif|pptx|docx|zip|pdf|mp4|mp3|wav|xlsx|bin|crypt14)$' |
  sort -u > /tmp/head.txt
comm -23 /tmp/hist.txt /tmp/head.txt > /tmp/purge.txt
# add the two Windows-invalid junk paths (they crash fast-import):
git -c core.quotepath=false log --all --format= --name-only |
  sort -u | grep -aE '([:*?"<>|]|[. ]$)' >> /tmp/purge.txt

# 3. Rewrite (also prunes newly-empty commits)
git filter-repo --invert-paths --paths-from-file /tmp/purge.txt --force

# 4. VERIFY before any push — tree must be byte-identical:
git rev-parse main^{tree}     # must equal origin's main^{tree}
git count-objects -vH         # expect ~596 MiB

# 5. Push the rewritten history (destructive)
git push --force origin 'refs/heads/*' 'refs/tags/*'
```

## Post-cutover

1. Everyone re-clones; delete stale clones/worktrees.
2. Recreate `.claude`/CoPilot worktrees from the fresh clone.
3. Verify: GitHub Releases assets intact; Pages redeploys on next main
   push; CI green on a no-op commit.
4. Optional: ask GitHub Support to run a server-side GC to shrink the
   server pack (fresh clones are small regardless).
