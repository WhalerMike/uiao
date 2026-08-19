# Day-2 Automation Kit — CURRENT STATE edition — Pilot Rollout & Update-Set Export

> A sequenced go-live for the **Active Directory (hybrid) edition** on a **pilot
> population**, plus how to export the built platform as an update set for
> promotion. Deploy small, prove it on real people, expand on evidence — never a
> big-bang enablement.

**Date Code:** 2026-08-19 10:22 ET · **Scope:** FedRAMP Moderate / GCC Moderate ·
**Audience:** the implementation lead + the ISSO/approver for the pilot

## 0. Entry criteria (do not start the pilot until all are true)

- The kit is **built in sub-production** from `CURRENT-STATE-BUILD-DELTA` and the
  base `Build Specification`, with `x_fed_day2_ops.hybrid_mode = true`.
- The **full ATF suite is green in `test_mode`** — the eight base suites **and**
  the four hybrid suites (synced→AD, cloud-only→Graph, unclassified fail-closed,
  sync-projection verify).
- The three build-time gates pass: `check_actuator_coverage.py`,
  `check_l3_ceiling.py`, `catalog/contract_check.py`.
- The **domain-joined AD MID** reaches the pinned writable DC (`ad_dc`), and its
  service account holds only the **delegated, least-privilege rights** on the
  pilot OUs (never Domain Admin).
- The instance's **`ecc_queue` insert ACL has been reviewed and restricted** —
  who can write `topic = 'Command'` / `name = 'Invoke-Day2AdAction'` /
  `agent = 'mid.server.' + ad_mid_server` records, scoped to this kit's own
  `name`/`agent` identifiers (`topic = 'Command'` alone is the platform's
  generic MID command topic and does not identify this channel). This queue
  insert is the AD leg's actual write channel (`AdHybridClient._dispatch`,
  `CURRENT-STATE-BUILD-DELTA` §5); an unreviewed ACL is a way to drive AD writes
  that bypasses the Flow, PIM, and the evidence record.
- The **ServiceNow PDI validation track is complete**
  (`CURRENT-STATE-PDI-VALIDATION.md`). The ATF suite proves the kit against a
  mock harness executing the real scripts over fixture data — a different thing
  from a real instance. Do not treat green ATF as a substitute for this track.
- The **AD lab validation track is complete**
  (`CURRENT-STATE-AD-LAB-VALIDATION.md`), **or explicitly waived by the ISSO
  with the waiver recorded** alongside the go/no-go decision. This is the only
  step that exercises the AD leg against a real domain controller: the
  delegated rights are otherwise asserted in code comments and never verified,
  and the VERIFY read-back has never run against a live DC. Waiving it is a
  legitimate risk decision; leaving it undone silently is not.
- The integration table carries the **`sam_request_ref`, `reason_code` and
  `http_status` columns and the UNIQUE INDEX on `sam_request_id`**
  (`KIT-BUILD-SPEC.md` §2b/§2b-i) — **verified by inspecting the table, not by
  a green ATF run**. ServiceNow ignores writes to columns that do not exist
  without raising anything, so every SAM suite can pass while push telemetry is
  silently discarded and the inbound idempotency check runs with no
  database-level backstop. This is the one entry criterion a passing test suite
  cannot demonstrate.
- A **rollback owner** and a **go/no-go approver** (ISSO) are named.

## 1. Choose the pilot cohort

- **10–50 synced users** in a **dedicated pilot OU** you control, plus **2–3
  cloud-only accounts** so both router legs are exercised on real objects.
- Include at least one of each lifecycle event you can stage safely: a test
  **joiner**, a **mover** (OU/attribute change), a **leaver**, a **password
  reset**, and an **AD-sourced group** membership change.
- **Exclude** privileged/production-critical identities from the first wave.

## 2. Phased enablement (each phase ends at a checkpoint; stop if it fails)

| Phase | Enable | Checkpoint (evidence, not a green write) |
|---|---|---|
| P0 | Read-only — the **morning check** against the pilot OU | The check runs, reconciles to the evidence table, opens no false deltas |
| P1 | **Password reset** for the pilot cohort | A reset routes to the **AD leg**, the DC re-read confirms `pwdLastSet`, evidence records the AD path |
| P2 | **Group membership** (one AD-sourced, one cloud-only) | Each routes to the **correct leg** by group source; membership verified in the right plane |
| P3 | **Mover** (attribute/OU change) | New access present **and stale access removed**; both planes verified |
| P4 | **Joiner** + **Leaver** | Joiner: AD create → sync → cloud entitlements; Leaver: AD disable → sync + cloud session revoke. Both close only on verify |

Run each phase for **at least one business day** before advancing. A phase that
stops at a clause (`authorize` / `elevate` / `route` / `actuate` / `verify`) is a
**stop-and-diagnose**, not a retry — read the evidence record's `trail`.

## 3. Evidence review (the pilot's real output)

After each phase, the ISSO reviews the evidence stream and confirms, per task:

- the **origin** (HR/AD event, catalog, or SAM decision) is present,
- the **approver ≠ requester** (SoD) and any **PIM activation id** is recorded,
- the **leg that actuated** (AD vs Graph) is recorded and matches the object's
  `onPremisesSyncEnabled`,
- the **verify verdict** re-read the post-state (and, for AD-leg writes, allowed
  for sync latency on the Entra side),
- **refused** tasks wrote evidence too.

The pilot is a success when a sample of closures is **auditable end to end** and
no task closed without a verify.

## 4. Exit criteria → expand

- ≥ 95% of pilot tasks closed with complete evidence; zero closed-without-verify.
- No AD-leg write to a cloud-only object and no Graph write to a synced attribute.
- The rollback path was tested at least once (see §6).

Expand in waves (next OUs), keeping privileged populations last and always behind
the same gates.

## 5. Update-set export & promotion

The kit is **built on the instance** (tables, ACLs, roles, the catalog, the Flow,
the router step) and promoted as a **ServiceNow update set** — a Flow / ATF / ACL
export is machine-serialized, not authorable text, so it is captured from the
instance you built it on.

1. **Build inside one update set.** Before you create the platform records
   (`CURRENT-STATE-BUILD-DELTA` + base `Build Specification`), set a **named
   update set current** (e.g. `x_fed_day2_ops — Current State v0.1`). All record
   creation lands in it.
2. **Confirm completeness.** In the update set, verify it captured: the scoped app
   records, the `AdHybridClient` Script Include, the four hybrid ATF tests, the
   Flow with the **router + AD-leg** steps, and the `hybrid_mode` / `ad_*` system
   properties. **System properties may need to be added to the update set
   manually** (make each `sys_properties` row a customer update) — a common miss.
3. **Batch shared + current-state.** If you built the base platform in a separate
   update set, add the current-state set as a **child** so they promote together.
4. **Mark Complete, then export.** Set the update set **Complete** and **export to
   XML** (Retrieved/Local Update Sets → export). Keep the XML as the promotion
   artifact for this build/date.
5. **Promote to the next environment.** **Import** the XML, **Preview** (resolve
   any collisions deliberately — do not skip), then **Commit**. Re-point the
   Connection & Credential aliases and the `ad_mid_server` / `ad_dc` at the target
   environment, and **leave `test_mode = false`** there.
6. **Re-run the ATF suite** in the target as a smoke test **in `test_mode` on a
   throwaway object**, then set `test_mode = false` for go-live.

**Do not** hand-edit the exported XML, and **do not** carry `test_mode = true`
into production — the ATF negative suite asserts it is off.

## 6. Rollback

- **Fastest, non-destructive:** set `x_fed_day2_ops.hybrid_mode`… **no** — that
  flips editions, it does not disable the kit. Instead **deactivate the catalog
  items** (or the Flow) so no new requests actuate; in-flight requests finish or
  stop at a clause.
- **Full back-out:** the update set is reversible in the source instance (**Back
  Out**); in a promoted environment, deactivate the app's catalog items and Flow
  and open a change to remove the update set.
- Because every task — including refused and rolled-back ones — leaves an evidence
  record, the rollback itself is auditable.

## 7. Versioning the two downloads

The kit zips (`orgcomp-day2-kit-active-directory-latest.zip` and the HRIT edition)
carry a **build date** rather than a fixed SHA — they rebuild on every deploy. For
a pilot, pin your promotion to a **tagged build**: record the **git commit** (or a
`vMAJOR.MINOR` tag) of the repo state you exported the update set from in the
change record, so the running platform, the exported XML, and the source tree all
agree. Bump the minor on a functional change to the Flow/scripts, the patch on a
doc/figure-only change.
