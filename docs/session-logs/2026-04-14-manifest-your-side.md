---
doc-type: operational-manifest
session: 2026-04-14-customer-docs-platform
audience: Michael Stratton (owner)
generated: 2026-04-14T15:40Z
scope: Phase A + B actions that cannot be automated
---

# Manifest — Your Side (Phase A + B actions)

This is everything I can't do for you on Phase A (close Step 0b loop) and Phase B (housekeeping). Execute in listed order; each task is independent of later tasks, so you can stop after any one and resume later. Expected total time: **~15 min** (mostly waiting on GitHub Actions).

Phase C (qmd conversion, Master Document, image pipeline, aggregate_prompts) is my side — I'm working it in parallel with you running this manifest.

---

## Task A1 — Commit UIAO_003 into canon (2 min, PowerShell)

The doctrinal source doc is sitting untracked in `uiao-core/canon/`. Until it's committed, the schema validates `mission-class` values against a document that isn't in canon — which makes the governance story weak.

```powershell
Set-Location 'C:\Users\whale\uiao-core'
git add canon/UIAO_003_Adapter_Segmentation_Overview_v1.0.md
git commit -m "[UIAO-CORE] CREATE: canon/UIAO_003 — adapter segmentation overview v1.0"
git push
```

**Expected:** single-commit push, no rebase needed (no one's pushed to remote since you last pulled).

**If push rejects with fetch-first:** `git pull --rebase origin main` then `git push` (same pattern as last time).

---

## Task A2 — Set up `CANON_SYNC_DISPATCH_TOKEN` PAT (5 min, GitHub web UI)

Hard blocker for canon-sync workflows. Neither the dispatcher (`uiao-core`) nor the receiver (`uiao-docs`) can function without this shared secret.

### A2.1 — Generate fine-grained PAT

Open: **https://github.com/settings/personal-access-tokens/new**

| Field | Value |
|---|---|
| Token name | `UIAO canon-sync dispatch` |
| Description | `Cross-repo canon propagation (uiao-core → uiao-docs)` |
| Resource owner | `WhalerMike` |
| Expiration | Custom → 90 days from today (2026-07-13) |
| Repository access | **Only select repositories** |
| Repositories | `WhalerMike/uiao-core` **AND** `WhalerMike/uiao-docs` (pick both) |

**Permissions (Repository permissions section):**

| Permission | Access |
|---|---|
| Contents | Read and write |
| Pull requests | Read and write |
| Metadata | Read-only (auto-selected, required) |

Click **Generate token**. Copy the token value (starts with `github_pat_`). You won't see it again.

### A2.2 — Add as repository secret in `uiao-core`

Open: **https://github.com/WhalerMike/uiao-core/settings/secrets/actions/new**

| Field | Value |
|---|---|
| Name | `CANON_SYNC_DISPATCH_TOKEN` |
| Secret | *(paste the PAT value)* |

Click **Add secret**.

### A2.3 — Add same secret in `uiao-docs`

Open: **https://github.com/WhalerMike/uiao-docs/settings/secrets/actions/new**

Same values as A2.2. Click **Add secret**.

### A2.4 — Set a calendar reminder

Calendar entry for **2026-07-06** (1 week before PAT expires): "Rotate CANON_SYNC_DISPATCH_TOKEN per `uiao-core/tools/README.md §Rotation`."

---

## Task A3 — First round-trip sync test (3 min active, 2 min watching Actions)

Proves the dispatcher + receiver plumbing actually works end-to-end.

### A3.1 — Trigger with trivial canon edit

```powershell
Set-Location 'C:\Users\whale\uiao-core'
# Add a whitespace-only change to adapter-registry.yaml (end-of-file newline)
Add-Content -Path 'canon/adapter-registry.yaml' -Value ''
git add canon/adapter-registry.yaml
git commit -m "[UIAO-CORE] CHORE: canon-sync round-trip probe"
git push
```

### A3.2 — Watch both Actions tabs

Open side-by-side:

- **https://github.com/WhalerMike/uiao-core/actions** — watch for `Canon sync — dispatch to uiao-docs` workflow. Should go green in ~30 sec.
- **https://github.com/WhalerMike/uiao-docs/actions** — watch for `Canon sync — receive from uiao-core` workflow. Should trigger ~5 sec after dispatcher finishes.

### A3.3 — Expected outcomes

| Outcome | What it means | Action |
|---|---|---|
| Both workflows green, no new PR in uiao-docs | Idempotent — uiao-docs already in sync. **Plumbing works, nothing to merge.** | Done. Move to B1. |
| Receiver opens a `canon-sync`-labeled PR in uiao-docs | Plumbing works, and receiver detected drift worth propagating. | Review the PR, merge if clean. |
| Dispatcher fails with auth error | PAT not configured correctly in uiao-core. | Recheck A2.2 (must be exact secret name, exact token). |
| Receiver fails with auth error | PAT not configured correctly in uiao-docs. | Recheck A2.3. |
| Receiver fails during checkout of `.uiao-core-sync` | PAT lacks Contents:read on uiao-core. | Recheck A2.1 permissions. |
| Receiver fails during PR creation | PAT lacks Pull requests:write on uiao-docs. | Recheck A2.1 permissions. |

If any failure, grab the Actions log link and paste into chat — I'll triage.

---

## Task B1 — ODA-15 decision (you pick, I draft)

I'm **not** pre-drafting three speculative canon patches because canon is doctrinal and these edits define the semantic model permanently. Pick one, and I'll write the full §4 edit + schema update in my next turn.

| Option | Canon edit scope | Downstream effect | My recommendation |
|---|---|---|---|
| **(a) Add 5th class — `substrate`** | New §4.7 in UIAO_003 defining Substrate Adapter Class; schema `mission-class` enum grows by one value; modernization-registry migrates `unmapped` → `substrate`. | Cleanest doctrinal distinction. Identity/Telemetry/Policy/Enforcement are *mission* classes; Substrate is *what the adapter runs on*. Orthogonal, easy to explain. | ⭐ Favored. |
| **(b) Re-scope `enforcement`** | Edit §4.5 role statement to widen from "verifiable assurance artifacts" to include "modernization artifacts that enable enforcement"; modernization-registry migrates `unmapped` → `enforcement`. | Smallest canon edit. But dilutes the four-class semantic purity — Entra ID isn't really an *enforcement* adapter, it's what enforcement *runs against*. | Workable but semantically muddy. |
| **(c) Accept `unmapped` permanently** | Add §4.7 footnote stating modernization adapters intentionally sit outside the mission-class model; `mission-class-notes` field on each modernization adapter explains the rationale. | Zero canon edit to §4.2–§4.5. But every modernization adapter carries an `unmapped` label forever, which looks unresolved in the dashboard. | Acceptable as a temporary state; weak as permanent doctrine. |

**How to decide:** if you agree the cleanest mental model is "four mission classes + one substrate class", pick (a). If you want to minimize canon surface area for now, pick (c). (b) is my least favorite — it compromises §4.5's clean definition.

**Reply in chat:** "ODA-15 → a" / "ODA-15 → b" / "ODA-15 → c" and I'll draft the full patch in the same turn.

---

## Task B2 — Track 1 monitoring subscription (30 sec, GitHub web UI)

Prior-session carryover that's been drifting.

1. Open: **https://github.com/cisagov/ScubaGear**
2. Click **Watch** (top-right, near Star/Fork).
3. Click **Custom**.
4. Check **Releases**. Leave other boxes unchecked.
5. Click **Apply**.

You'll now get an email/notification on every new ScubaGear release — which matters because your `scubagear` conformance adapter in `adapter-registry.yaml` pins a specific version (`1.5.1`) and the policy layer pins `main`. When a new release ships, you want to know so you can evaluate whether to bump the pin.

---

## Task B3 — Build-and-deploy status check bypass (my investigation, your decision)

I inspected `uiao-docs/.github/workflows/build-docs.yml` and confirmed the workflow is real and configured. The "bypassed" message on every push is because:

1. Branch protection on `main` requires `Build and Deploy Documentation` to pass.
2. The check can only run *after* the push is received.
3. GitHub sees no check status at push time, so it would normally reject.
4. Your account has bypass permission (owner/admin), so the push succeeds with a "bypassed" flag.

**Your options:**

| Option | Trade-off |
|---|---|
| Keep bypassing (status quo) | Works, but every push leaves an audit trail of "required check bypassed" — looks bad in a governance story. |
| Remove the required-check rule | Silent pushes, cleaner audit. But any future failed render won't block future pushes. |
| Push via PR-only workflow | Forces every canon/docs change through a PR where the check runs as a gate. Cleanest. Slowest. |

**My recommendation:** switch to PR-only for `main` once Phase C is complete (that's when the doc tree stabilizes enough that PR review adds value). Until then, keep bypassing — it's cosmetic.

**No action required from you right now.** Park this as a Step 6 item.

---

## Summary — Time-boxed checklist

- [ ] **A1** — Commit UIAO_003 (2 min)
- [ ] **A2** — Generate PAT + add secret to both repos (5 min)
- [ ] **A3** — Trigger round-trip probe + watch Actions (3-5 min)
- [ ] **B1** — Reply in chat with ODA-15 choice (a/b/c) (30 sec)
- [ ] **B2** — Watch cisagov/ScubaGear releases (30 sec)
- [ ] **B3** — No action, parked for Step 6

Ping me when A1-A3 are done or if anything fails. While you're running these, I'm building Phase C.
