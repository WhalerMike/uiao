# OrgPath "hierarchical inheritance" claim — code-grounded assessment

**Date:** 2026-06-29
**Scope:** Whether OrgPath "uniquely composes org hierarchy *with inheritance*"
the way Active Directory Group Policy does.
**Verdict:** The mechanism-level moat claim is **falsified in code**. The
narrower modeling/projection/evidence framing is **confirmed in code** and is
honest, well-engineered, and defensible.

## The claim under test

AD GPO resolution is non-monotonic and order-dependent: an *Enforced*
(`NoOverride`) ancestor punches through a descendant's *Block Inheritance* and
reverses the usual child-wins precedence. Reproducing it requires an ordered
fold over the path with two control bits per link. "Inheritance" is the
load-bearing word in the moat claim.

## What the code actually shows

Three subsystems, read end to end:

1. **`governance/orgpath_runtime.py`** — a *drift-detection + remediation* loop
   (Snapshot → Compare → Classify → Alert → Remediate → Verify) over a per-facet
   codebook SSOT. It detects when Entra reality diverges from the codebook and
   projects facets into native constructs. It is **not** a policy resolver and
   never claims to be.

2. **`modernization/orgtree/enforcement_projection.py`** — a vendor-neutral
   *compiler* from facet predicates to native enforcement constructs (Entra
   dynamic groups, NSX / Palo Alto / AWS / GCP tags). It deliberately restricts
   itself to set-membership/equality operators
   (`-eq`, `-ne`, `-in`, `-notIn`) and **explicitly rejects** ordered/text
   operators "rather than silently approximated." This is the *right* engineering
   discipline and confirms the algebra is flat **by design**.

3. **`adapters/modernization/active_directory/gpo_orgpath_plan.py`** — the
   "differentiated join." `gpo_analytics` faithfully parses the per-link
   `enforced` bit (from `<NoOverride>`) and notes `Blocked` elements — but
   `build_migration_plan` consumes only `link.enabled` and the SOM path → OU
   intent. **`enforced` and Block Inheritance are discarded at the join.**
   `ScopeTarget`, the join's output type, has no field that can carry precedence
   at all.

## Findings

- **A — Moat claim falsified, with a line citation.** The information required
  to resolve effective non-monotonic policy (`enforced`, `Blocked`) is parsed
  and then dropped at `build_migration_plan`. The join is precedence-blind by
  construction. Any "GPO-class inheritance resolver" claim should be retired.

- **B — The scope defense is correct and confirmed.** Two of three subsystems
  are *correctly* designed as flat-algebra projection/detection, and
  `enforcement_projection.py` documents and enforces that boundary. The
  engineering is honest; the overclaim lived in the narrative layer, not the
  code. Recommended framing: "declarative, provenance-tracked effective-policy
  *materialization* over organizational hierarchies, optimized for OSCAL
  evidence, drift detection, and auditability" — accurate and harder to attack.

- **C — One genuine latent defect (independent of the moat question).** The GPO
  planner *parses* `enforced`/`Blocked`, then **silently drops** them — the
  exact "silent approximation" failure mode `enforcement_projection.py` was
  careful to avoid elsewhere. Two enabled links that differ only in their
  enforced flag produce byte-identical scope targets, so a downstream consumer
  cannot warn that a conflict will invert post-migration. Fix options:
  (i) carry `enforced`/`Blocked` through to a precedence/conflict warning in the
  plan, or (ii) document explicitly that the plan does not resolve precedence and
  effective policy must be verified post-migration.

## Why the fix dissolves the moat (unchanged conclusion)

To deliver true GPO-class inheritance you must either implement a real ordered
resolver (you have re-implemented a directory primitive — not novel) or flatten
and restamp (standard policy baking — not novel, and stale between
materializations). Either repair re-becomes a category that already exists.

## Artifact

`tests/test_gpo_orgpath_precedence_boundary.py` — a passing characterization
test that pins the boundary: the enforced bit exists pre-join, the join output
cannot carry it, and the Block+Enforced known-answer case resolves to
independent per-link targets rather than a single effective value. If a real
resolver is ever added, these tests must be updated deliberately and the moat
claim revisited.
