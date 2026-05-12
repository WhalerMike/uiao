# 03 — Batch Plan: HRIT Single-ATO Productization (v0.6.0)

> **Status:** Inbox draft. Not canon. Authored 2026-05-06. Each workstream
> below is a self-contained brief any Claude session can pick up cold.
>
> **Renumber note (2026-05-11):** References below to ADR-058 and
> UIAO_143 reflect the original proposal numbers. The canonical ADR for
> this mission theme is **ADR-065** (renumbered to resolve slot collision
> with Microsoft Purview coverage ADR-058 accepted 2026-05-07). The
> canonical operational spec is **UIAO_144** (UIAO_143 is now SCIM RFC
> Core Schema per PR #342). Historical body retained verbatim.

## Mission (one sentence)

Close the runtime gap that ADR-054 §Implementation explicitly deferred:
make the Single-ATO Reciprocity Model emit signed, OSCAL-mapped,
evidence-graph-anchored reciprocity records per consuming agency, with
ConMon SLA enforcement and configuration-latitude drift detection.

## Acceptance for the release

A maintainer can run, end-to-end, in <15 min on a synthetic three-agency
fixture:

```
uiao reciprocity onboard-agency \
  --controlling-ato OPM-HRIT-2026-001 \
  --consuming-agency TREAS \
  --legal-basis interagency-mou \
  --out-dir /tmp/hrit-recip
```

…and receive a signed, schema-valid `reciprocity-record.json` plus an
OSCAL component-definition scoped to TREAS, both linked into the
evidence graph as `ato-decision → reciprocity-record` edges.

## Phase structure

| Phase | What happens | Concurrency model |
|---|---|---|
| **Phase 0 — Foundation** | Promote ADR (now ADR-065) to canon, allocate UIAO_144, stub schema, create branch scaffolding | **One** session, sequential |
| **Phase 1 — Batch A** | 10 self-contained workstreams | **Up to 10** sessions in parallel |
| **Phase 2 — Integration** | Merge, full CI green, RC1 tag | **One** session |
| **Phase 3 — Validation** | Lab tenant validation, doc polish | **Up to 3** sessions in parallel |
| **Phase 4 — Release cut** | Tag v0.6.0, CHANGELOG, push | **One** session |

---

## Phase 0 — Foundation (sequential, one session)

**Branch:** `claude/v0.6.0-hrit-foundation`

**Tasks (updated for canonical numbering):**
1. Promote `02-proposed-adr-058-draft.md` to
   `src/uiao/canon/adr/adr-065-hrit-productization-mission.md` (status:
   Accepted) — renumbered from ADR-058 to resolve slot collision
2. Allocate **UIAO_144** in `src/uiao/canon/document-registry.yaml`
   (UIAO_143 claimed by SCIM RFC pin)
3. Create `src/uiao/canon/specs/hrit-productization.md` (UIAO_144)
   — frontmatter + outline only; sections filled by Batch A
4. Create stub schema `src/uiao/schemas/reciprocity-record/reciprocity-record.schema.json`
   with `$schema`, `$id`, and empty `properties` — Batch A WS-A1 fills
5. Create `examples/hrit/.gitkeep` so the directory exists for fixtures
6. Create the 10 Batch A branches on origin (push empty commits)
7. Tag baseline `v0.5.x-pre-hrit`

*(Historical Batch A WS cards continue unchanged below; substitute
ADR-065/UIAO_144 wherever ADR-058/UIAO_143 appears in the workstream
references. The canonical ratified versions live under
`src/uiao/canon/adr/adr-065-hrit-productization-mission.md` and
`src/uiao/canon/specs/hrit-productization.md`.)*

---

## Self-contained AI session prompt template (updated)

For each WS, hand the assigned Claude session this prompt:

```
You are working on UIAO at /home/user/uiao on branch
claude/v0.6.0-ws-XX-<name> (already created on origin).

Read in order before any code change:
- inbox/v0.6.0-hrit-productization/03-batch-plan.md §"WS-XX"
- AGENTS.md (especially invariants I1–I6 and Repository Invariants)
- The "Reads first" list in your WS card
- src/uiao/canon/adr/adr-065-hrit-productization-mission.md (renumbered
  from ADR-058)
- src/uiao/canon/specs/hrit-productization.md (UIAO_144, renumbered from
  UIAO_143)

Execute "Deliverables" until "Acceptance" criteria are all met. Run
`ruff check`, `mypy src/uiao`, and `pytest -q tests/test_<your_scope>.py`
before committing. Do not modify files outside your "Scope (in)" list.

Commit with conventional commit format (`feat:`, `test:`, `docs:`).
Push to origin. Do not open a PR — Phase 2 will handle integration.

If you hit a question that needs maintainer judgment, write the
question into inbox/v0.6.0-hrit-productization/questions-WS-XX.md
and stop. Do not guess.
```

*(WS-A1 through WS-A10 detail cards and concurrency tables remain in
the original draft in repository history. The structural and identifier
updates above are the only changes from the 2026-05-06 inbox draft.)*

## See also

- `src/uiao/canon/adr/adr-065-hrit-productization-mission.md` (canonical)
- `src/uiao/canon/specs/hrit-productization.md` (UIAO_144, canonical)
