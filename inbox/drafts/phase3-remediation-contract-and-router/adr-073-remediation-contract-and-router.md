---
adr_id: adr-073
title: "Drift Finding Remediation Contract + Router — Promote §4 to Typed Inline Field, Dispatch Findings to Halt / Fix / Flag / Log Handlers"
status: PROPOSED
decided: null
deciders: Michael Stratton
updated: 2026-05-15
next_review: 2026-11-01
review_trigger: First production halt event; POA&M generator change; OrgTree engine refactor (Phase 5)
impact: Promotes the §4 remediation contract from `16_DriftDetectionStandard.qmd` into a typed inline field on `DriftFinding`; introduces a `RemediationRouter` dispatching findings to four handlers (halt/fix/flag/log); extends the OSCAL Component Definition generator to surface runtime findings as observations; consolidates two of the substrate's three `DriftFinding` classes into a shared canonical class (OrgTree engine's class deferred to Phase 5)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
depends_on: adr-070, adr-071, adr-072
---

# ADR-073: Drift Finding Remediation Contract + Router

## Status

**PROPOSED** — 2026-05-15

## Context

After Phase 2, the substrate has runtime drift detection, but findings
go to two distinct places with no shared lifecycle:

- **Substrate walker hygiene findings** (`subkind="hygiene"`) — emitted
  in CI; produce build failures; do not flow into POA&M, do not flow
  into OSCAL bundles.
- **Runtime sink findings** (`subkind="runtime"`) — emitted at adapter
  emit time; appended to the JSONL event log; do not flow into POA&M;
  reach OSCAL only via the snapshot-and-event-log assembly path (Phase
  1d), and even then are not distinguished from accepted-envelope events.

[`16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd) §4 prescribes a
remediation contract every adapter MUST implement:

```yaml
remediation_contract:
  drift_class: "{DRIFT-*}"
  severity: "{P1|P2|P3|P4}"
  detection_timestamp: "{ISO8601}"
  detected_by: "{adapter_id | workflow_id}"
  auto_remediated: true | false
  remediation_action: "halt | fix | flag | log"
  remediation_timestamp: "{ISO8601}"
  remediation_evidence: "{commit_sha or audit_record_id}"
  escalation_path: "{Canon Steward | Architecture Lead | CISO}"
```

The contract is documentation today; no adapter actually emits it
because there is no typed shape to carry it and no router to consume
it. Three design questions must be answered together:

1. **Where does the contract live on the finding?** Sidecar field?
   Subclass per drift class? Inline fields on the canonical
   `DriftFinding`?
2. **Who decides `remediation_action`?** The adapter that detected the
   drift? The router? A per-drift-class rule table?
3. **Do we unify the three `DriftFinding` classes now, or defer?** The
   substrate has three: substrate walker, OrgTree engine, runtime sink
   (Phase 1 introduced). All three carry similar but not identical
   fields. The Phase 5 strategy memo defers OrgTree refactor; this ADR
   has to pick a scope.

## Decision

**The §4 remediation contract is carried as inline fields on a single
canonical `DriftFinding` dataclass. A `RemediationRouter` consumes
every finding from the substrate walker and the runtime sink, decides
the `remediation_action` from a per-drift-class rule table, and
dispatches to one of four handlers. The OrgTree engine's `DriftFinding`
stays peer for now; Phase 5 unifies.**

Six sub-decisions land with this:

### 1. Inline contract fields, not a sidecar

The canonical `DriftFinding` carries every §4 field as a named
attribute. No sidecar map, no subclass-per-drift-class hierarchy.
Adding fields keeps the JSON serialization flat (one finding = one
JSON object), keeps OSCAL emission straightforward, and lets the
substrate walker's existing reports continue to work without an extra
indirection.

```python
@dataclass
class DriftFinding:
    # Existing fields (carried from substrate walker):
    drift_class: str
    severity: str
    path: str
    detail: str
    subkind: Optional[str] = None

    # NEW (§4 remediation contract):
    detection_timestamp: str = ""        # ISO-8601 UTC; default = now() at construction
    detected_by: str = ""                # adapter_id or workflow_id; "" until router fills it
    auto_remediated: bool = False        # set by router after fix-handler success
    remediation_action: str = ""         # "halt" | "fix" | "flag" | "log"; set by router
    remediation_timestamp: Optional[str] = None
    remediation_evidence: Optional[str] = None
    escalation_path: Optional[str] = None
```

Findings emitted by walker / sink leave the new fields at their
defaults; the router populates them via `route(finding)`. This keeps
the emission sites simple — they don't know or care about the
remediation rules — and centralizes the rule logic in the router.

### 2. `RemediationRouter` owns the action table

A per-drift-class × severity table determines the `remediation_action`:

| drift_class | severity | action | escalation_path | auto_remediated? |
|---|---|---|---|---|
| DRIFT-PROVENANCE | P1 | halt | CISO | false |
| DRIFT-PROVENANCE | P2 | fix (if deterministic) → flag | Canon Steward | true if fix succeeds |
| DRIFT-AUTHZ | P1 | halt | CISO | false |
| DRIFT-AUTHZ | P2 | flag | Canon Steward | false |
| DRIFT-IDENTITY | P1 | halt | Architecture Lead | false |
| DRIFT-IDENTITY | P2 | fix (if deterministic) → flag | Architecture Lead | true if fix succeeds |
| DRIFT-SCHEMA | P1 | halt | Architecture Lead | false |
| DRIFT-SCHEMA | P2 | fix (if deterministic) → flag | Architecture Lead | true if fix succeeds |
| DRIFT-SCHEMA | P3 | flag | Architecture Lead | false |
| DRIFT-SEMANTIC | P2 | log | Canon Steward | false |
| DRIFT-SEMANTIC | P3 | log | Canon Steward | false |
| (any) | P4 | log | Canon Steward | false |

The table lives in `src/uiao/canon/data/remediation-routes.yaml` so
it's amendable via the canon-change ADR process, not a code change.
The router loads it at boot; an empty/missing entry falls back to
`log` + Canon Steward (the conservative default).

The router decides; the adapter doesn't. This keeps adapters policy-
free — they detect drift, the router decides what to do about it.

### 3. Four handlers, with clear contracts

| Handler | What it does | When `auto_remediated` becomes True |
|---|---|---|
| `halt` | Records the finding, signals the caller (sink / walker / CI) to stop. The sink already short-circuits P1 emissions; `halt` just records the contract. | never |
| `fix` | Looks up an adapter-specific apply() function in the modernization registry; runs it; on success populates `remediation_timestamp` + `remediation_evidence` + `auto_remediated=True`; on failure demotes to `flag`. | when the apply() succeeds |
| `flag` | Constructs a `POAMEntry` from the finding and writes it to the configured POA&M store. `remediation_evidence` carries the POA&M UUID. | never |
| `log` | Appends the finding (with contract populated) to the runtime event log if not already there. No POA&M, no halt, no apply(). | never |

Handlers are pure functions of `(finding, context)`. The router knows
how to invoke each; the handlers do not know about each other. The
`fix → flag` demotion path runs inside the `fix` handler itself, not
as a router special case — keeps the demotion deterministic.

### 4. Two-of-three `DriftFinding` consolidation

The canonical class lives at `src/uiao/models/drift_finding.py`. Two
sites adopt it:

- **Substrate walker.** `src/uiao/substrate/walker.py` keeps the same
  `DriftFinding` name; the module re-exports the canonical class.
  Existing imports `from uiao.substrate.walker import DriftFinding`
  continue to work unchanged.
- **Runtime sink.** `src/uiao/telemetry/provenance.py` already imports
  `DriftFinding` from somewhere (Phase 1 inlined it; Phase 3 routes
  it to the canonical module). Same re-export pattern; no caller
  changes.

The OrgTree engine's `DriftFinding`
(`src/uiao/governance/drift_engine.py`) stays peer. It's not renamed,
not refactored, not consolidated. Phase 5 unifies all three; doing it
now adds scope without buying anything substrate-wide.

### 5. OSCAL Component Definition gets a runtime-findings mode

`src/uiao/generators/oscal.py` gains a `include_runtime_findings: bool`
parameter, surfaced as `--include-runtime-findings` on the CLI. When
true, the generator:

1. Loads runtime findings from the JSONL event log over the same time
   window used for evidence assembly (Phase 1d path).
2. Projects each finding into an OSCAL Observation under the
   `_UIAO_RUNTIME_NS` namespace (`https://uiao.gov/ns/oscal/runtime`).
3. Attaches Observations to the `implemented-requirement` whose
   `control-id` corresponds to the finding's drift class via the
   §6 compliance mapping (CM-3, SI-7, CA-7, IR-6).

The flag defaults off — today's bundles stay byte-identical. Flipping
the flag on is the assessor-facing change; agencies opt in per ATO
package.

### 6. POA&M write path is one-way for now

The `flag` handler writes `POAMEntry` records but does not read them.
A finding that triggers `flag` produces a new POA&M entry every time;
deduplication is not in scope for Phase 3. This will produce noise for
recurring findings (e.g., a stale claim from a slow-publishing
upstream system). Phase 3 documents this as a Negative; Phase 4 or a
later cleanup ADR adds a dedup key derived from `(drift_class, path)`.

## Consequences

### Positive

- **Every finding now carries the §4 contract.** The whitepaper claim
  that "every finding carries deterministic class and severity" gets a
  real machine-readable form — not just the class+severity but the
  full remediation lifecycle.
- **Routing logic lives in one place.** Adapters don't decide actions;
  the router does. The table is in canon (`remediation-routes.yaml`)
  so changes go through the ADR process, not code review of an
  adapter PR.
- **Assessors see runtime findings in OSCAL bundles.** The
  `--include-runtime-findings` flag is the bridge between Phase 1's
  event log and the ATO package. Without it, runtime drift detection
  is invisible to assessors and the whitepaper's "deterministic
  governance" claim is half-realized.
- **No big-bang unification of the three DriftFinding classes.** Two
  of three consolidate (walker + sink); OrgTree stays peer. Smaller PR,
  smaller blast radius.
- **POA&M integration is additive.** The `flag` handler uses
  `POAMEntry` as it exists today; no schema change, no POA&M generator
  refactor.
- **Phase 4 whitepaper flip is unblocked.** With contract + router +
  OSCAL integration in place, the substrate's runtime-drift surface is
  feature-complete enough to claim SHIPPED.

### Negative

- **Three `DriftFinding` classes shrinks to two, but doesn't reach
  one.** The OrgTree engine's class stays peer. Documented as a known
  duplication; Phase 5 cleanup ADR addresses it. A reader of the code
  has to know which class lives where.
- **POA&M dedup is not in scope.** A recurring runtime finding
  produces a new POA&M entry per detection. For high-volume
  DRIFT-SEMANTIC findings, this could flood the store. Mitigated by
  routing P2/P3 SEMANTIC to `log` (not `flag`) in the default rule
  table — the noisy class doesn't hit POA&M today.
- **`fix` handler depends on adapter apply() functions existing.** Many
  adapters don't have one. The handler demotes to `flag` when no
  apply() is registered, but this means the auto-remediation surface
  is sparse out of the gate. The whitepaper carefully says
  "auto-remediate if deterministic"; this ADR honors that ("if
  deterministic" is observable in the rule table, not a marketing
  hedge).
- **Default escalation paths are policy choices.** "CISO for
  DRIFT-PROVENANCE P1" is a default; agencies may wire the
  escalation_path to a different role in their tenant config.
  Mitigated by the canon table living at
  `remediation-routes.yaml` (overridable per deployment); not free.

### Neutral

- The canonical `DriftFinding` is a dataclass, not a pydantic model.
  Matches the existing substrate-walker class; matches the OrgTree
  engine's class; matches the established substrate idiom for
  internal-flow data (pydantic is reserved for wire-format contracts
  like the envelope and consent model).
- ADR-073 does not commit to a specific POA&M store backend. The `flag`
  handler writes through `uiao.evidence.poam.PoamStore`, which has
  pluggable backends (filesystem JSONL today; Postgres in a future
  deployment).

## Alternatives considered

### Alternative A — Adapter decides `remediation_action`

Each adapter declares its action policy in its manifest; the router
just dispatches. **Rejected** because:

- Three adapters that detect the same drift class with the same
  severity should produce the same action. A per-adapter declaration
  invites drift (literally) in the action policy across adapters.
- The §4 contract is substrate-wide; the table belongs in canon, not
  in each adapter manifest.

### Alternative B — Subclass `DriftFinding` per drift class

Replace the `drift_class: str` field with a class hierarchy
(`ProvenanceDriftFinding(DriftFinding)`, etc.). **Rejected** because:

- Adds an inheritance dimension without buying anything — every
  subclass would carry identical fields.
- Breaks the substrate walker's existing flat JSON serialization;
  callers that filter by `drift_class` string have to switch to
  `isinstance()` checks.

### Alternative C — Unify all three DriftFinding classes now

Refactor OrgTree's class into the canonical one in this PR. **Rejected**
because:

- Strategy memo explicitly defers this to Phase 5.
- OrgTree engine's class has fields specific to the six-phase
  orchestrator (op-type, phase, remediation_results); folding them
  into the canonical class either bloats the shared model or splits
  it via composition. Either way, it's a bigger change than this ADR
  needs.

### Alternative D — Skip the router; have each emission site call the handlers directly

The walker calls `halt_handler()` on P1; the sink does the same; etc.
**Rejected** because:

- Duplicates the rule-table logic at every call site.
- Forces every new emission site to re-implement routing rules.
- Makes the rule table harder to change — a single ADR-route-table
  edit becomes N call-site edits.

## Mechanical interface (informative)

### Canonical `DriftFinding` with contract

```python
# src/uiao/models/drift_finding.py
@dataclass
class DriftFinding:
    drift_class: str
    severity: str
    path: str
    detail: str
    subkind: Optional[str] = None

    # §4 remediation contract
    detection_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    detected_by: str = ""
    auto_remediated: bool = False
    remediation_action: str = ""
    remediation_timestamp: Optional[str] = None
    remediation_evidence: Optional[str] = None
    escalation_path: Optional[str] = None

    def with_routing(self, *, action: str, escalation: str, detected_by: str) -> "DriftFinding":
        return replace(self, remediation_action=action, escalation_path=escalation, detected_by=detected_by)
```

### Router

```python
# src/uiao/governance/router.py
class RemediationRouter:
    def __init__(self, *, routes_yaml: Path, poam_store: PoamStore) -> None:
        self._table = self._load_routes(routes_yaml)
        self._poam = poam_store
        self._fix_registry: dict[str, Callable[..., Any]] = {}

    def register_fix(self, *, drift_class: str, fn: Callable[..., Any]) -> None:
        """Adapter calls this at boot to declare a fix() function for a drift class."""
        self._fix_registry[drift_class] = fn

    def route(self, finding: DriftFinding) -> DriftFinding:
        rule = self._table.lookup(finding.drift_class, finding.severity)
        finding = finding.with_routing(
            action=rule.action,
            escalation=rule.escalation_path,
            detected_by=finding.detected_by or "substrate",
        )
        handler = self._handler_for(rule.action)
        return handler(finding)
```

### OSCAL integration (CLI)

```bash
# Today (unchanged):
uiao oscal generate --source snapshot
uiao oscal generate --source event-log

# After Phase 3:
uiao oscal generate --source event-log --include-runtime-findings
```

## Cross-references

- [`docs/docs/16_DriftDetectionStandard.qmd`](../../../docs/docs/16_DriftDetectionStandard.qmd) — §4 promoted by this ADR
- [`src/uiao/canon/adr/adr-009-drift-ledger-immutability.md`](../../../src/uiao/canon/adr/adr-009-drift-ledger-immutability.md) — immutability the routing-decision audit trail inherits
- [`src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md`](../../../src/uiao/canon/adr/adr-012-canonical-drift-taxonomy.md) — taxonomy the router's rule table indexes
- [`src/uiao/canon/adr/adr-014-evidence-severity-model.md`](../../../src/uiao/canon/adr/adr-014-evidence-severity-model.md) — severity model the rule table consumes
- [`src/uiao/governance/drift_engine.py`](../../../src/uiao/governance/drift_engine.py) — OrgTree engine NOT refactored in this phase
- [`src/uiao/models/poam.py`](../../../src/uiao/models/poam.py) — `POAMEntry` written by the `flag` handler
- [`src/uiao/evidence/poam.py`](../../../src/uiao/evidence/poam.py) — POA&M store backend
- [`src/uiao/generators/oscal.py`](../../../src/uiao/generators/oscal.py) — gains `include_runtime_findings` mode

## Revision history

| Version | Date | Author | Summary |
|---|---|---|---|
| 1.0 | 2026-05-15 | UIAO Architecture | Initial PROPOSED draft — Phase 3 of the whitepaper TARGET → SHIPPED plan; promotes §4 to typed inline fields, introduces RemediationRouter + four handlers, consolidates two of three `DriftFinding` classes, adds OSCAL `--include-runtime-findings` mode |
