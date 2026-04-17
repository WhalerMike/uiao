# HANDOFF — Adapter Test Site Research

> Process note, not canon. Transient. Delete or supersede once the
> next session has consumed it.

## 1. Local state

| Field | Value |
|---|---|
| Repo | `WhalerMike/uiao` (monorepo) |
| Local checkout | `/home/user/uiao/` |
| Branch | `claude/document-research-handoff-iOLze` |
| Base | `main` at `7a98935` (refactor(impl): rename Python package uiao_impl → uiao.impl) |
| File path | `impl/HANDOFF-adapter-test-site-research.md` |
| Working tree | clean before this commit |
| Parallel branch in stub | `claude/document-research-handoff-iOLze` exists in the `WhalerMike/uiao-impl` redirect stub — ignore it; the stub is read-only per its README |

The three other repos (`uiao-core`, `uiao-gos`, `uiao-impl`) carry the
same branch name but are all redirect stubs since the 2026-04-17
monorepo consolidation (ADR-028). Only this repo's branch is active.

## 2. Why the prior session's push was blocked

The prior session logged the blocker as "GitHub MCP allow-list refresh
— current session still sees the old list." That framing is partially
wrong and worth correcting for the next session:

- **Git push itself** is not mediated by the GitHub MCP server. It
  goes to the `origin` remote via standard git. The push blocker, if
  any, is a git/auth issue — not an MCP allow-list issue.
- **MCP tools** (`mcp__github__*`) are what need `WhalerMike/uiao` in
  their allow-list in order to create PRs, post comments, list CI
  runs, etc. against the monorepo.

In the current session the system prompt's repository scope lists
all four repos including `WhalerMike/uiao`, so MCP access to the
monorepo is available here. If a future session sees only the
pre-consolidation three (`uiao-core`, `uiao-gos`, `uiao-impl`) in
scope, that session needs an allow-list refresh before it can use
MCP against `WhalerMike/uiao`.

**Action for the next session:** verify MCP scope includes
`whalermike/uiao` before attempting any `mcp__github__*` call
against the monorepo. A `git push` itself does not depend on MCP.

## 3. Original research input (verbatim)

> 1. Live tests — against a Microsoft 365 Developer Program commercial tenant. Run in CI.
> Validates the adapter's common-plane behavior. Tractable now.
> 2. Contract tests — Microsoft Learn docs for GCC-Moderate-specific behavior get
> recorded as expected responses (YAML fixtures); tests replay them against the adapter in
> CI. Proves GCC-M-specific error paths don't regress. Tractable without a live GCC-M
> tenant.
> 3. Reference-deployment tests — run only when an agency partners with UIAO and
> grants access to a live GCC-M tenant. Infrequent, high-signal.
> This is worth landing as UIAO_131 — Adapter Test Strategy (new spec) or an update to
> UIAO_121 (existing Adapter Conformance Test Plan Template). I'd recommend the update to
> UIAO_121 — the three tiers are test-plan content, not a separate spec.
> Sources:
> • Microsoft 365 Developer Program — Microsoft Learn
> • Set up a Microsoft 365 developer sandbox subscription
> • Set up your application's Microsoft Entra test environment
> • Create a Microsoft Entra developer tenant — Verified ID
> • Infoblox Developer Portal
> • BloxOne API documentation
> • CISA CDM Program
> • FedRAMP Marketplace
> Now executing (a) — grep-heuristic sca[n]

## 4. Research finding — the recommendation has already been overridden in execution

The input's recommendation was: **update UIAO_121**.

Canon state in `main` as of `7a98935` says otherwise. The three-tier
model was landed as a **new canonical spec**, `UIAO_131`, not as an
update to `UIAO_121`. Both specs coexist — they answer different
questions:

| Doc | Path | Answers |
|---|---|---|
| `UIAO_121` | `core/canon/specs/adapter-conformance-test-plan-template.md` | Per-adapter pass/fail criteria (domain 2.1–2.7, extension methods, canon consistency). Template each adapter's AVS populates from. |
| `UIAO_131` | `core/canon/specs/adapter-test-strategy.md` | Three-tier test architecture (live commercial / contract fixtures / reference deployment) — the surrounding strategy doc that `UIAO_121` plugs into. |

Both are registered in `core/canon/document-registry.yaml` at
lines 146–149 (`UIAO_121`) and 196–199 (`UIAO_131`), status
`Current`, classification `CANONICAL`.

Trail of execution commits (oldest → newest):

| Commit | Message |
|---|---|
| `e2e7e80` | `[UIAO-CORE] CREATE: UIAO_131 Adapter Test Strategy — three-tier model` |
| `c2edf63` | `Merge pull request #58 from WhalerMike/claude/uiao-131-adapter-test-strategy` |
| `19d2a44` | `[UIAO-DOCS] CREATE: FINDING-001 — FedRAMP GCC-Moderate INR unavailable` |
| `c70c823` | `[UIAO-DOCS] CREATE: Academy contributor tier-1 setup page (M365 Developer Program)` |
| `5a04727` | `[UIAO-IMPL] CREATE: tier-2 contract fixture scaffold + first fixture (FINDING-001)` |
| `92a5b1e` | `[UIAO-DOCS] CREATE: entra-id adapter integration guide (template for 10-adapter series)` |

**Net:** the research question is closed in canon. A next session
looking to extend the three-tier model should treat `UIAO_131` as
the governing spec and propose amendments there, not re-open the
"update UIAO_121 vs new spec" debate.

## 5. Audit — repos / files read during this exploration

### `WhalerMike/uiao` (monorepo, active)

| Path | Relevance |
|---|---|
| `core/canon/specs/adapter-test-strategy.md` | `UIAO_131` — the landed three-tier spec |
| `core/canon/specs/adapter-conformance-test-plan-template.md` | `UIAO_121` — per-adapter criteria template |
| `core/canon/document-registry.yaml` | Registration of both specs, plus UIAO_120/122/123/124/125–130 context |
| `docs/findings/fedramp-gcc-moderate-informed-network-routing.md` | `FINDING-001` — the GCC-M constraint driving the tier-2 fixture class |
| `impl/tests/fixtures/contract/README.md` | Contract-fixture contract: directory layout, provenance block, sanitization rules, empty-adapter convention |
| `impl/tests/fixtures/contract/m365/informed-network-routing-unavailable-gcc-moderate.yaml` | First tier-2 fixture (instance of `UIAO_131` §7) |
| `impl/tests/fixtures/contract/{bluecat-address-manager,cyberark,entra-id,infoblox,m365,palo-alto,scuba,scubagear,service-now,terraform}/` | Ten adapter subdirectories, mostly `.gitkeep`-only pending fixtures |
| `AGENTS.md`, `README.md`, `impl/.claude/rules/canon-consumer.md`, `impl/.claude/rules/test-coverage.md` | Operating rules — `impl/` is a canon consumer; no canonical artifacts land here |

### `WhalerMike/uiao-impl` (redirect stub, read-only)

Only the redirect `README.md` and historical content. Contains a
`claude/document-research-handoff-iOLze` branch with no commits
beyond its tip — a leftover from the prior session's confusion
between `uiao-impl` (old repo) and `uiao/impl/` (monorepo module).
**Do not land anything here.** README §"This repo is now read-only"
is the authoritative statement.

### `WhalerMike/uiao-core` and `WhalerMike/uiao-gos`

Both are redirect stubs with the same branch name. Not touched.

## 6. Copy-paste prompt for the next session

```
Context: handoff doc at uiao/impl/HANDOFF-adapter-test-site-research.md
on branch claude/document-research-handoff-iOLze of WhalerMike/uiao.

The three-tier adapter test strategy is already landed as UIAO_131.
The original research recommendation ("update UIAO_121 instead") was
overridden in execution. Both UIAO_121 (per-adapter conformance
criteria) and UIAO_131 (tier architecture) are canonical and coexist.

Before doing anything:
1. Read uiao/impl/HANDOFF-adapter-test-site-research.md end to end.
2. Verify git state: `git -C /home/user/uiao status` should be clean
   on claude/document-research-handoff-iOLze.
3. Verify MCP scope: call mcp__github__get_me and confirm that you
   can call mcp__github__list_pull_requests on WhalerMike/uiao
   without an authorization error.
4. Only then pick up the follow-on work (see §7 of the handoff).
```

## 7. Follow-on work (non-exhaustive)

Not done this session; candidates for the next session:

1. **Populate the 9 empty tier-2 fixture directories** under
   `impl/tests/fixtures/contract/` with at least one fixture each,
   starting with adapters that have public Microsoft Learn / vendor
   docs citing GCC-Moderate behavior.
2. **Add tier-tier annotations to the adapter / modernization
   registries.** `UIAO_131` §5.1 names `tier-3-exclusion` as a
   registry field; the registries don't yet declare it per-adapter.
3. **Extend the Academy contributor tier-1 setup** beyond M365
   Developer Program to cover ServiceNow Developer Instance,
   CyberArk Cloud Trial, Palo Alto Networks Terraform modules,
   and Azure VM eval-ISO standup (per `UIAO_131` §3.1).
4. **Fixture staleness surface** in the Modernization Atlas
   footer. `UIAO_131` §6 defines the footer; implementation is
   pending.

None of these unblock the handoff itself. They are the next wedge
of adapter-test-strategy work.

## 8. Verify-then-push commands

Run from the monorepo root (`/home/user/uiao`):

```bash
# 8.1 Git state
git -C /home/user/uiao status
git -C /home/user/uiao log --oneline main..HEAD
git -C /home/user/uiao diff --stat main..HEAD

# 8.2 Push this branch
git -C /home/user/uiao push -u origin claude/document-research-handoff-iOLze

# 8.3 MCP verification (after push, optional — only if you need PR ops)
#   Use the exact tool names:
#   - mcp__github__get_me                  → confirms MCP auth
#   - mcp__github__list_branches           → owner=WhalerMike repo=uiao; confirm the new branch is visible
#   - mcp__github__list_pull_requests      → owner=WhalerMike repo=uiao state=open; confirm you can list
```

If 8.3 fails with a scope / authorization error, the MCP server
needs `WhalerMike/uiao` in its allow-list before PR-related work
can proceed. The push itself from step 8.2 is independent of MCP
and should succeed on plain-git auth.

---

*Generated 2026-04-17. Supersede or delete once consumed.*
