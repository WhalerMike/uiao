# Provisional Patent Application — DRAFT

> **Status:** Draft for inventor review and patent-counsel review. **Not legal
> advice.** This draft was prepared from the repository's existing technical
> artifacts and is intended to be enablement-compliant on its own; nothing
> outside this document needs to be "incorporated by reference" for the
> specification to stand. Inventor should still have a registered patent
> agent or attorney review before filing.

---

## Provisional Application Cover Sheet (Form PTO/SB/16) — Data to Enter

**Title of the Invention**

Systems and Methods for Deterministic Provenance-Chained Migration of
On-Premises Directory Governance to Cloud Identity Platforms via a
Dual-Axis Adapter Registry and Canonical Claim Pipeline.

**Inventor(s)**

- Full Name: \[INVENTOR FULL LEGAL NAME\]
- Residence: Gambrills, Maryland, United States of America

**Correspondence Address**

\[Inventor Name / Street / City / State / ZIP / Email / Phone\]

**Entity Status:** Micro Entity (verify eligibility under 37 C.F.R. § 1.29)

**Attorney/Agent:** None (pro se) *— recommend a registered practitioner
review prior to filing the non-provisional within the 12-month window.*

---

## Specification

### Title of the Invention

Systems and Methods for Deterministic Provenance-Chained Migration of
On-Premises Directory Governance to Cloud Identity Platforms via a
Dual-Axis Adapter Registry and Canonical Claim Pipeline.

### Cross-Reference to Related Applications

None.

### Statement Regarding Federally Sponsored Research or Development

Not applicable.

### Field of the Invention

The present invention relates to enterprise identity and infrastructure
migration. More specifically, it relates to a computer-implemented
system and method for preserving governance continuity when migrating
on-premises directory services (for example, on-premises Active
Directory) to cloud identity platforms (for example, Microsoft Entra ID
and associated cloud services), by means of (i) a deterministic
provenance chain over discovered claims, (ii) a vendor-agnostic adapter
contract enforcing seven defined responsibility domains, (iii) a
dual-axis adapter registry validated against a machine-readable schema,
(iv) an immutable raw-evidence storage tier with write-once semantics,
and (v) drift- and freshness-aware validation against governance
indicators.

### Background of the Invention

#### Technical Problem

On-premises directory services such as Active Directory function not
merely as identity stores but as the de-facto governance plane for at
least eleven categories of dependent infrastructure objects, including
users, computers, service accounts, security groups, group policy
objects, integrated DNS/DHCP, public-key infrastructure (PKI),
RADIUS/802.1X authenticators, LDAP-bound applications, service
principal names (SPNs), and cross-domain trust relationships.

Conventional cloud-migration tooling typically performs object-level
synchronization (for example, Entra Cloud Sync replicating users and
groups) and surface-level analytics (for example, Intune group policy
analytics). Such tooling does not reconstruct the governance semantics
that the on-premises directory had implicitly provided — namely,
hierarchical inheritance, lifecycle authority, certificate auto-renewal,
Kerberos delegation, integrated name-resolution authority, and
deterministic policy targeting.

In practice, the resulting governance loss manifests as silent
post-migration failures: certificates that expire without renewal
because their auto-enrollment templates were lost; RADIUS/802.1X access
control breaking because the policy server can no longer evaluate group
membership against the previous directory; LDAP-bound legacy
applications failing to authenticate because no equivalent LDAP endpoint
exists in the cloud target; service accounts losing Kerberos delegation;
and DNS/DHCP records becoming stale. These failures are characteristic
of the prior art because no existing system provides (a) a uniform
contract for *discovering* the governance state across heterogeneous
sources, (b) a *deterministic* representation of that state suitable
for downstream validation, or (c) a *machine-validated* registry by
which migration tooling may be composed across vendors.

#### Limitations of the Prior Art

Existing approaches fall into three categories, each with technical
limitations the present invention overcomes:

1. **Vendor-supplied synchronization tools** (e.g., directory
   synchronization engines) operate at the object level only. They do
   not capture or reproduce inheritance, delegation semantics, or
   certificate lifecycle policy. They produce no portable provenance
   record.
2. **Configuration-management add-ons** (e.g., group policy analytics)
   produce non-deterministic mappings, lack adversarial drift
   detection, and provide no rollback evidence.
3. **Custom one-off migration scripts** are non-reusable, lack a
   uniform contract, write to mutable target stores without
   write-once recovery guarantees, and cannot be validated against a
   machine-readable schema.

No prior system, to the inventor's knowledge, combines (i) a
dual-axis adapter registry with formal JSON-Schema-based validation,
(ii) a per-claim cryptographic provenance hash chained to connection
and query provenance, (iii) an immutable raw-evidence storage tier
that rejects modification of archived runs at the storage layer, and
(iv) a freshness-and-drift-aware validation pipeline producing
governance evidence in standardized formats.

### Summary of the Invention

The invention provides a computer-implemented system and method,
hereafter referred to as the Unified Infrastructure Administration
Overlay ("UIAO"), comprising:

1. **A vendor-agnostic adapter contract** implemented as an abstract
   base class enforcing seven defined responsibility domains:
   (2.1) Connection & Identity; (2.2) Schema Discovery & Canonical
   Mapping; (2.3) Query Normalization & Deterministic Extraction;
   (2.4) Data Normalization & Claim Construction; (2.5) Drift
   Detection & Version Integrity; (2.6) Evidence Packaging &
   Indicator Integration; and (2.7) Security, Privacy, and
   Operational Controls.

2. **A plurality of concrete adapters** each implementing the
   contract for a distinct dependency category, including (without
   limitation) IP-address management ("ipam"), public-key
   infrastructure ("pki"), RADIUS/network access ("radius"), LDAP
   proxying ("ldap-proxy"), directory synchronization-engine
   retirement ("sync-engine"), device-management migration
   ("device-management"), time-services ("ntp"), and distributed-file
   services ("dfs").

3. **A dual-axis adapter registry**, expressed in a machine-readable
   document (for example, YAML), in which each adapter declares one
   value on an *operational axis* (`class`: modernization vs.
   conformance) and one value on a *doctrinal axis* (`mission-class`:
   identity, telemetry, policy, enforcement, integration, mixed, or
   unmapped). The registry is validated against a JSON Schema
   document that enforces required fields, enumerated values,
   identifier patterns, and lifecycle invariants.

4. **A canonical claim pipeline** in which raw data discovered by an
   adapter is normalized into a `ClaimObject` carrying a
   cryptographic `provenance_hash`, grouped into a `ClaimSet`,
   correlated with `ConnectionProvenance` and `QueryProvenance`
   envelopes, and packaged as an `EvidenceObject` keyed to a
   governance indicator identifier ("ksi_id").

5. **A deterministic provenance chain** under which the same
   discovered state, queried from the same source at the same
   logical time, yields identical canonical output, including
   identical `version_hash` on the schema mapping and identical
   `provenance_hash` on each claim, computed as a stable hash over a
   canonically serialized payload.

6. **An immutable raw-evidence storage tier** ("Raw Zone") that
   checkpoints each run into a per-adapter, per-run path, enforces
   write-once semantics by raising a `RawZoneViolation` exception on
   any attempted modification of an archived run, and is governed by
   a retention policy expressed in years.

7. **A drift- and freshness-aware validation engine** that consumes
   `EvidenceObject` instances, evaluates them against governance
   indicators and per-adapter freshness windows, emits a
   `ValidationResult` with a status drawn from {pass, fail, error,
   stale}, and records drift indicators of typed categories.

8. **A multi-plane orchestrator** that transforms upstream policy
   findings into an intermediate representation, evaluates that
   representation against governance indicators, builds evidence
   bundles, and exports artifacts in standardized control-catalog
   formats.

The above components, in combination, solve the previously
unaddressed technical problem of governance continuity during cloud
identity migration by reconstructing, in vendor-agnostic and
machine-verifiable form, the implicit governance that the
on-premises directory had supplied.

### Brief Description of the Drawings

**Figure 1** is a block diagram of the UIAO system, depicting an
on-premises directory and dependent infrastructure on the left, a
cloud identity platform on the right, and the UIAO components
(adapter contract, registry, claim pipeline, raw zone, validator,
orchestrator) positioned between them.

![FIG. 1 — System Overview](patent-figures/figure-01.png)

**Figure 2** is a class diagram of the adapter contract, showing
`DatabaseAdapterBase` and the seven dataclasses
(`ConnectionProvenance`, `SchemaMappingObject`, `QueryProvenance`,
`ClaimObject`, `ClaimSet`, `DriftReport`, `EvidenceObject`).

![FIG. 2 — Adapter Contract Class Diagram](patent-figures/figure-02.png)

**Figure 3** is a sequence diagram of the canonical claim pipeline,
from `connect()` through `discover_schema()`, `execute_query()`,
`normalize()`, `detect_drift()`, and `collect_evidence()`.

![FIG. 3 — Canonical Claim Pipeline Sequence](patent-figures/figure-03.png)

**Figure 4** is a schematic of the dual-axis registry, showing the
operational axis (modernization vs. conformance) crossed with the
doctrinal axis (identity / telemetry / policy / enforcement /
integration).

![FIG. 4 — Dual-Axis Adapter Registry](patent-figures/figure-04.png)

**Figure 5** is a state diagram of an adapter's lifecycle
(`reserved → proposed → active → deprecated → retired`).

![FIG. 5 — Adapter Lifecycle State Diagram](patent-figures/figure-05.png)

**Figure 6** is a flowchart of the five-stage migration pipeline
(Discover → Normalize → Map → Migrate → Validate), with the
governance gates between stages.

![FIG. 6 — Five-Stage Migration Pipeline](patent-figures/figure-06.png)

**Figure 7** is a block diagram of the Raw Zone storage layout,
showing the per-adapter / per-run directory structure and the
`RawZoneViolation` enforcement point.

![FIG. 7 — Immutable Raw Zone Storage Layout](patent-figures/figure-07.png)

**Figure 8** is a flowchart of the validation engine, showing
evaluation of freshness windows, computation of drift indicators,
and emission of `ValidationResult`.

![FIG. 8 — Validation Engine Flowchart](patent-figures/figure-08.png)

**Figure 9** is a table of the eleven on-premises directory
dependency categories and their corresponding adapter assignments.

![FIG. 9 — Eleven AD Dependency Categories and Adapter Mapping](patent-figures/figure-09.png)

### Detailed Description of the Invention

The following description discloses preferred and alternative
embodiments. The invention is not limited to these embodiments;
modifications consistent with the principles described will be
apparent to a person of ordinary skill in the art.

#### 1. System Overview

Referring to Figure 1, the system comprises a plurality of
adapter modules ("adapters"), an adapter registry, a canonical
claim pipeline, a write-once raw-evidence storage tier, a
validation engine, and an orchestrator. The adapters interface
on one side with sources of on-premises governance state (the
directory, PKI, IPAM, RADIUS, etc.) and on the other side with
cloud identity targets and downstream evidence consumers. The
registry, schema, and validator together form a vendor-agnostic
overlay that does not depend on any particular cloud identity
implementation.

#### 2. The Adapter Contract

In a preferred embodiment, the adapter contract is implemented
as an abstract base class (the "adapter base"). The adapter base
enforces seven canonical responsibility domains and exposes the
following abstract methods, each returning a typed dataclass:

```
connect()           -> ConnectionProvenance
discover_schema()   -> SchemaMappingObject
execute_query(q)    -> QueryProvenance
normalize(rows)     -> ClaimSet
detect_drift()      -> DriftReport
collect_evidence(k) -> EvidenceObject    # concrete, composes the above
```

A concrete adapter ("ipam", "pki", "radius", "ldap-proxy",
"sync-engine", "device-management", "ntp", "dfs", and similar)
subclasses the adapter base, supplies a stable
`ADAPTER_ID` string, and implements the abstract methods.

The adapter contract enforces three invariants that distinguish
the invention from prior-art migration tooling:

- **Idempotency.** Repeated invocation of `discover_schema()` or
  `execute_query()` against an unchanged source produces
  identical output, including identical hashes.
- **Statelessness across runs.** Adapters carry no
  implementation state between invocations; all run-relevant
  state is persisted through the provenance envelopes and the
  raw zone.
- **Conformance vs. modernization separation.** An adapter
  declares, in its registry entry, whether it observes state
  ("conformance") or mutates a target environment
  ("modernization"). The registry schema enforces this
  separation.

#### 3. Canonical Dataclasses (Provenance Envelopes)

Each abstract method returns a frozen-style dataclass providing
the provenance and content envelope for that domain. In a
preferred embodiment:

```python
@dataclass
class ConnectionProvenance:
    identity: str
    auth_method: str
    endpoint: str
    tls_version: Optional[str]
    mtls_enabled: bool
    timestamp: datetime

@dataclass
class SchemaMappingObject:
    vendor_schema: Dict[str, Any]
    canonical_schema: Dict[str, Any]
    mapping_rules: Dict[str, Any]
    unmapped_fields: List[str]
    version_hash: str

@dataclass
class QueryProvenance:
    canonical_query: Dict[str, Any]
    vendor_query: str
    execution_plan_hash: str
    row_count: int
    timestamp: datetime

@dataclass
class ClaimObject:
    claim_id: str
    entity: str
    fields: Dict[str, Any]
    source: str
    provenance_hash: str

@dataclass
class ClaimSet:
    claims: List[ClaimObject]
    source_reference: str

@dataclass
class DriftReport:
    drift_type: str
    severity: str
    first_observed: datetime
    last_observed: datetime
    details: Dict[str, Any]
    remediation: Optional[str]

@dataclass
class EvidenceObject:
    ksi_id: str
    source: str
    timestamp: datetime
    raw_data: Any
    normalized_data: Optional[Dict[str, Any]]
    provenance: Dict[str, Any]
    freshness_valid: bool
```

The `provenance_hash` and `version_hash` are computed as
SHA-256 digests over a deterministic JSON serialization (sorted
keys, default string coercion for non-JSON-native types). In a
preferred embodiment the helper is:

```python
def _hash(self, payload: Any) -> str:
    serialized = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
```

This design produces a deterministic provenance chain: given an
unchanged source, two independent runs of `collect_evidence()`
yield byte-identical `version_hash` and `provenance_hash`
values, enabling downstream verification of authenticity,
reproducibility, and unchanged-state attestation.

#### 4. The Dual-Axis Adapter Registry

Adapters are registered in a machine-readable registry document
(in a preferred embodiment, YAML). Each registry entry declares
the adapter on two orthogonal axes:

- **Operational axis (`class`)** — drawn from the enumeration
  `{modernization, conformance}`. A `modernization` adapter is
  permitted to write to a target environment; a `conformance`
  adapter is read-only and may not mutate the target.
- **Doctrinal axis (`mission-class`)** — drawn from the
  enumeration `{identity, telemetry, policy, enforcement,
  integration, mixed, unmapped}`. Each value corresponds to a
  canonical role against a single source of truth (SSOT).

The dual-axis design is itself a technical mechanism: by
crossing operational behavior against doctrinal role, the
registry can be partitioned for independent continuous-integration
drift scanning, can be feature-flagged at runtime per axis, and
can reject ambiguous adapter declarations at validation time
before any target environment is touched.

The registry is validated against a JSON Schema document. In a
preferred embodiment, the schema requires the following fields
on every adapter entry: `id` (kebab-case identifier, never
renamed once assigned), `name`, `class`, `mission-class`,
`status` (drawn from `{reserved, proposed, active, deprecated,
retired}`), `gcc-boundary`, `ssot-mutation`,
`certificate-anchored`, and `object-identity-only`. Optional
fields include `phase` (deployment phase),
`mission-class-notes` (required when `mission-class` is `mixed`
or `unmapped`), `successor` (required when `status` is
`deprecated` or `retired`), `vendor`, `license`, `runtime`,
`runner-class`, `tenancy`, and `evidence-class`.

Identifier stability is enforced by an invariant: once assigned,
an `id` is never renamed; retirement proceeds by setting
`status: deprecated` and naming a `successor`. This invariant
preserves provenance integrity across registry versions —
historical `EvidenceObject` records continue to resolve to the
correct adapter identity even after the active implementation
has been replaced.

#### 5. The Canonical Claim Pipeline

Referring to Figure 3, in operation an adapter executes the
following sequence:

1. `connect()` establishes a secure authenticated connection
   (in a preferred embodiment, mutually authenticated TLS) and
   returns a `ConnectionProvenance` envelope.
2. `discover_schema()` retrieves the vendor schema, maps it to
   the UIAO canonical schema, records unmapped fields, and
   returns a `SchemaMappingObject` carrying a `version_hash`.
3. `execute_query(canonical_query)` translates a canonical
   query into a vendor-specific query, executes it
   deterministically, and returns a `QueryProvenance` envelope
   including an `execution_plan_hash` and row count.
4. `normalize(raw_rows)` reduces vendor rows to a `ClaimSet` of
   `ClaimObject` instances. Each `ClaimObject` carries a
   `provenance_hash` over its canonicalized fields.
5. `detect_drift()` compares the current state against prior
   recorded state and returns a `DriftReport` typed under one
   or more drift categories (for example, `DRIFT-IDENTITY`,
   `DRIFT-SCHEMA`, `DRIFT-PROVENANCE`, `DRIFT-SEMANTIC`).
6. `collect_evidence(ksi_id)` composes the above outputs into
   an `EvidenceObject` keyed to the supplied governance-
   indicator identifier, populating `raw_data`,
   `normalized_data`, and a `provenance` block that includes a
   hash over the normalized claim set.

The pipeline is deterministic end-to-end: every output
artifact carries provenance back to the connection, the
schema mapping, the canonical query, and the source adapter.

#### 6. The Immutable Raw Zone

Referring to Figure 7, the system persists adapter outputs into
a write-once raw-evidence storage tier (the "Raw Zone"). In a
preferred embodiment, the Raw Zone is laid out as:

```
<lake_root>/<adapter_id>/<run_id>/<artifacts>
```

The Raw Zone enforces the following invariants:

- **No silent drops.** Every artifact emitted by an adapter is
  recorded; the pipeline does not discard rows.
- **Write-once semantics.** Any attempt to modify, overwrite,
  or delete an archived run raises a `RawZoneViolation`
  exception at the storage layer. Corrections are appended as
  new runs, never applied in place.
- **Ordered sequence.** Runs are ordered by a combination of
  monotonic timestamp and a tie-breaking sequence number,
  permitting deterministic replay.
- **Content integrity.** Each artifact is bound to the
  per-claim `provenance_hash` and per-mapping `version_hash`
  computed in the pipeline, providing tamper-evidence under
  the SHA-256 collision-resistance assumption.
- **Idempotent writes.** Duplicate artifacts under the same
  event identifier are deduplicated rather than rewritten.
- **Retention policy.** Each adapter declares a
  `retention-years` value; an archive manager component
  enforces lifecycle expiration in accordance with that
  policy.

The Raw Zone backend is pluggable: a filesystem
implementation is provided in a preferred embodiment, with
object-store backends (for example, blob storage or S3-API
compatible stores) contemplated as alternative embodiments.

#### 7. The Validation Engine

A validation engine consumes `EvidenceObject` instances from
the Raw Zone and evaluates them against named governance
indicators. In a preferred embodiment the engine emits a
`ValidationResult` with the following structure:

- `status` ∈ {`pass`, `fail`, `error`, `stale`}
- `evidence` — the evaluated `EvidenceObject` reference
- `drift_indicators` — a typed list of drift categories
  (`DRIFT-IDENTITY`, `DRIFT-SCHEMA`, `DRIFT-PROVENANCE`,
  `DRIFT-SEMANTIC`)
- `freshness_valid` — boolean derived by comparing the
  evidence timestamp against the adapter's declared
  `freshness-window-hours` (ranging in preferred embodiments
  from a single hour to thirty or more days, with a
  family-default fallback)

A `status` of `stale` is emitted when evidence is otherwise
well-formed but the freshness window has elapsed; this state
is distinguished from `fail` (substantive non-compliance) and
`error` (pipeline malfunction), which permits downstream
remediation logic to discriminate between collection failures
and substantive governance regressions.

#### 8. The Multi-Plane Orchestrator

The orchestrator coordinates the transformation of governance
data through a plurality of compliance planes. In a preferred
embodiment, four planes are implemented:

- **Plane 1** transforms upstream policy findings (for
  example, automated security-baseline assessment output) into
  an intermediate representation.
- **Plane 2** evaluates the intermediate representation against
  named governance indicators, producing per-indicator
  pass/fail/stale state.
- **Plane 3** builds an evidence bundle keyed by indicator,
  joining indicator results to underlying `EvidenceObject`
  records.
- **Plane 4** exports the evidence bundle into one or more
  standardized control-catalog formats (for example, OSCAL
  artifacts including system security plans and plans of action
  and milestones).

Each plane is feature-flagged for selective enable/disable per
environment or tenant, writes to per-run isolated output
directories, emits structured logs to both standard error and
a run-specific log file, and supports a dry-run mode in which
side effects are suppressed.

#### 9. The Migration Pipeline (Five-Stage Process)

Referring to Figure 6, the invention contemplates a five-stage
migration pipeline composed of the foregoing components:

1. **Discover.** Each adapter executes `connect()`,
   `discover_schema()`, `execute_query()`, and `normalize()`
   to produce a canonical claim set describing the current
   governance state. Discovery is read-only.
2. **Normalize.** Adapter outputs are reconciled against the
   canonical schema and any organic on-premises divergence is
   rationalized into a normalized governance graph.
3. **Map.** Source-side governance constructs (for example,
   distinguished-name based identities, group-policy targeting
   expressions, certificate-template auto-enrollment rules)
   are mapped to cloud-target equivalents (for example,
   directory-services identities, configuration-management
   profiles, certificate-based authentication policies).
4. **Migrate.** Modernization-class adapters apply the mapped
   state to the cloud target, with each mutation accompanied
   by an `EvidenceObject` recorded to the Raw Zone.
5. **Validate.** The validation engine evaluates post-migration
   evidence against indicators and freshness windows, emitting
   `ValidationResult` records that constitute the governance-
   continuity attestation.

Each stage is gated: progression from one stage to the next
requires that prior-stage evidence is present in the Raw Zone,
is fresh, and validates to `status: pass`.

#### 10. Architectural Invariants (Eight Core Concepts)

In a preferred embodiment, the invention is governed by eight
named architectural invariants which together distinguish it
from prior-art migration tooling:

1. **Single source of truth.** Every governance claim has
   exactly one authoritative origin; all other references are
   pointers, not duplicates.
2. **Conversation as atomic unit.** Each session binds, in a
   single envelope, identity, certificate state, addressing,
   network path, quality-of-service, and telemetry.
3. **Identity as root namespace.** Every derived
   resource — addresses, certificates, subnets, policies,
   telemetry — is rooted in identity rather than in
   network location.
4. **Deterministic addressing.** Addressing is identity-
   derived and policy-driven, not assigned by side-band
   procedure.
5. **Certificate-anchored overlay.** Trust between services
   is anchored in mutually authenticated TLS rather than in
   network position.
6. **Telemetry as control.** Real-time telemetry is consumed
   as a control input to orchestration, not solely as a
   passive reporting channel.
7. **Embedded governance.** Workflows are orchestrated
   programmatically against the registry, rather than
   actuated through human ticketing.
8. **User-experience continuity.** Migration is invisible to
   the end user when governance is reconstructed correctly.

Each adapter's registry entry declares which of the eight
invariants it implements, enabling registry-level reasoning
about governance coverage.

#### 11. Eleven Dependency Categories Addressed

The invention addresses, in a preferred embodiment, the
following eleven categories of on-premises directory
dependency, each mapped to the adapter family responsible
for reconstructing its governance in the cloud target:

| # | Dependency Category | Failure Mode Without Governance | Adapter Family |
|---|---|---|---|
| 1 | Users / Identities | Orphaned accounts; privilege drift | identity-modernization |
| 2 | Computers / Devices | Unmanaged endpoints; missing patches | device-management |
| 3 | Service Accounts | Silent service outages; lost delegation | ldap-proxy |
| 4 | Security Groups | Permission sprawl; lost inheritance | identity-modernization |
| 5 | Group Policy Objects | Configuration drift; inconsistent baselines | device-management |
| 6 | DNS / DHCP | Name-resolution failure; split-brain DNS | ipam |
| 7 | PKI / Certificates | Silent certificate expiration | pki |
| 8 | RADIUS / 802.1X | Network access failure; VPN outage | radius |
| 9 | LDAP Applications | Application login failure | ldap-proxy |
| 10 | SPNs / Kerberos | Single sign-on breakage | ldap-proxy |
| 11 | Trust Relationships | Cross-domain authentication failure | (architectural) |

#### 12. Alternative Embodiments

- **Alternative storage backends.** While a filesystem
  embodiment of the Raw Zone is preferred for clarity, the
  invention contemplates object-store backends, content-
  addressable backends, and append-only ledger backends with
  equivalent write-once enforcement.
- **Alternative hash functions.** SHA-256 is preferred for
  provenance hashing; the invention contemplates equivalent
  collision-resistant hashes (for example, SHA-3 or
  BLAKE3).
- **Alternative registry serializations.** YAML is preferred
  for human-editability; the invention contemplates JSON,
  TOML, and binary serializations of the same schema.
- **Alternative cloud targets.** While the preferred
  embodiment targets a particular cloud identity platform
  (Microsoft Entra ID and associated services), the
  vendor-agnostic adapter contract permits embodiments
  targeting other cloud identity platforms.
- **Alternative orchestrator topologies.** The preferred
  embodiment uses a four-plane orchestrator; alternative
  embodiments contemplate fewer or additional planes,
  including a federated multi-tenant variant.

### Industrial Applicability

The invention is industrially applicable to enterprises and
public-sector entities migrating from on-premises directory
infrastructure to cloud identity platforms. It enables such
migrations to be conducted with governance continuity,
auditable provenance, and post-migration validation that the
governance posture has been preserved.

---

## Draft Claims (for Anchoring the Non-Provisional)

> **Note.** A provisional application is not required to include
> claims, and these claims are not examined. They are included
> here to anchor the scope of the priority date and to focus the
> non-provisional drafting effort within the twelve-month window.
> Counsel should refine before non-provisional filing.

### Independent Claims

**1.** A computer-implemented system for migrating governance
state from an on-premises directory service to a cloud identity
platform, the system comprising:

- a plurality of adapter modules, each adapter module
  conforming to a vendor-agnostic adapter contract enforcing
  seven defined responsibility domains, said domains
  comprising connection and identity, schema discovery and
  canonical mapping, query normalization and deterministic
  extraction, data normalization and claim construction,
  drift detection and version integrity, evidence packaging
  and indicator integration, and security, privacy, and
  operational controls;
- an adapter registry comprising a machine-readable document
  in which each adapter is declared along an operational axis
  drawn from the enumeration {modernization, conformance} and
  along a doctrinal axis drawn from the enumeration
  {identity, telemetry, policy, enforcement, integration,
  mixed, unmapped}, said registry being validated against a
  schema document that enforces required fields, enumerated
  values, and lifecycle state transitions;
- a claim pipeline configured to produce, from outputs of one
  or more of the adapter modules, a plurality of claim
  objects, each claim object carrying a cryptographic
  provenance hash computed over a canonically serialized
  representation of the claim's content;
- a write-once evidence storage tier configured to persist
  outputs of the claim pipeline under a per-adapter,
  per-run path and to reject modification of any persisted
  run by raising a designated exception at the storage
  layer; and
- a validation engine configured to evaluate evidence
  objects from the storage tier against named governance
  indicators and against per-adapter freshness windows, and
  to emit a validation result whose status is drawn from the
  enumeration {pass, fail, error, stale}.

**2.** A computer-implemented method for migrating governance
state from an on-premises directory service to a cloud identity
platform, the method comprising:

- registering, in a machine-validated registry, a plurality
  of adapter modules along an operational axis and a
  doctrinal axis;
- discovering, by each of the adapter modules, governance
  state from a source system, and producing a connection
  provenance envelope, a schema mapping object carrying a
  version hash, a query provenance envelope, and a claim set
  in which each claim carries a cryptographic provenance
  hash;
- composing the foregoing into an evidence object keyed to
  a governance indicator identifier;
- persisting the evidence object into a write-once storage
  tier that rejects modification of persisted runs;
- evaluating the persisted evidence object against the
  governance indicator and against a freshness window
  declared by the adapter; and
- emitting a validation result whose status is drawn from
  {pass, fail, error, stale}.

### Dependent Claims

**3.** The system of claim 1, wherein the cryptographic
provenance hash is computed as a SHA-256 digest over a JSON
serialization in which object keys are sorted lexicographically
and non-native types are coerced to strings.

**4.** The system of claim 1, wherein the operational axis
value `modernization` permits the adapter module to write to a
target environment and the operational axis value
`conformance` prohibits the adapter module from mutating the
target environment.

**5.** The system of claim 1, wherein the adapter registry
further enforces an identifier-stability invariant under which
an adapter identifier, once assigned, is never renamed, and
retirement of an adapter is recorded by setting a status field
to `deprecated` or `retired` and populating a successor
identifier field.

**6.** The system of claim 1, wherein the write-once evidence
storage tier is laid out as `<root>/<adapter_id>/<run_id>/` and
attempts to modify, overwrite, or delete an existing
`<run_id>` directory cause the storage tier to raise a
`RawZoneViolation` exception.

**7.** The system of claim 1, wherein each adapter declares a
retention period expressed in years, and an archive manager
enforces lifecycle expiration in accordance with the declared
retention period.

**8.** The system of claim 1, wherein the validation engine
distinguishes a `stale` status, indicating that an evidence
object is otherwise well-formed but exceeds its adapter's
declared freshness window, from a `fail` status indicating
substantive non-compliance and an `error` status indicating
a pipeline malfunction.

**9.** The system of claim 1, wherein the validation engine
emits drift indicators drawn from a typed set comprising
`DRIFT-IDENTITY`, `DRIFT-SCHEMA`, `DRIFT-PROVENANCE`, and
`DRIFT-SEMANTIC`.

**10.** The system of claim 1, further comprising a
multi-plane orchestrator configured to (i) transform upstream
policy findings into an intermediate representation, (ii)
evaluate the intermediate representation against named
governance indicators, (iii) build an evidence bundle keyed by
indicator, and (iv) export the evidence bundle into a
standardized control-catalog format.

**11.** The system of claim 1, wherein the plurality of
adapter modules comprises at least one adapter from each of
the following categories: IP-address management; public-key
infrastructure; RADIUS network access; LDAP proxy;
synchronization-engine retirement; device-management
migration; time-services; and distributed-file services.

**12.** The system of claim 1, wherein the schema mapping
object's `version_hash` is identical across independent
invocations of `discover_schema()` against an unchanged
source, and the claim object's `provenance_hash` is identical
across independent invocations of `normalize()` over an
unchanged input row set.

**13.** The method of claim 2, further comprising progressing
through a five-stage migration pipeline comprising discovery,
normalization, mapping, migration, and validation, wherein
progression from each stage to the next is gated by the
presence of fresh, passing evidence in the write-once storage
tier.

**14.** The method of claim 2, wherein the cloud identity
platform comprises a directory service to which user and group
objects are synchronized, and the method further comprises
reconstructing governance for at least the following
on-premises directory dependency categories: users, computers,
service accounts, security groups, group policy objects,
DNS/DHCP, public-key infrastructure, RADIUS/802.1X, LDAP
applications, service principal names, and trust
relationships.

**15.** A non-transitory computer-readable medium storing
instructions that, when executed by one or more processors,
cause the one or more processors to perform the method of
claim 2.

---

## Abstract of the Disclosure

A computer-implemented system and method for migrating
governance state from an on-premises directory service to a
cloud identity platform. A plurality of vendor-agnostic
adapter modules conforming to a seven-domain contract emit
provenance-bearing envelopes (connection, schema mapping,
query, claim, drift, evidence) under a deterministic
provenance chain anchored in SHA-256 digests over canonically
serialized payloads. A dual-axis registry, validated against
a JSON Schema, declares each adapter along an operational
axis (modernization vs. conformance) and a doctrinal axis
(identity / telemetry / policy / enforcement / integration /
mixed / unmapped) and enforces identifier-stability and
lifecycle invariants. An immutable, write-once raw-evidence
storage tier persists adapter outputs and rejects
modification of archived runs at the storage layer. A
validation engine evaluates evidence against named governance
indicators and per-adapter freshness windows, emitting
results drawn from {pass, fail, error, stale} together with
typed drift indicators. A multi-plane orchestrator transforms
findings, evaluates indicators, builds evidence bundles, and
exports standardized control-catalog artifacts. The system
reconstructs governance continuity for eleven categories of
on-premises directory dependency during migration to a cloud
identity platform.

---

## Filing Checklist (Pro Se on Patent Center)

1. **Verify micro-entity eligibility** under 37 C.F.R. § 1.29
   (gross-income test and fewer than four prior non-provisional
   filings, with exclusions). If ineligible, file as small
   entity.
2. **Verify current USPTO fee** for a provisional application
   at micro / small entity rates on `uspto.gov` before filing;
   fees change.
3. **Save this specification as a single PDF**, paginated, with
   line numbers if convenient.
4. **Prepare the cover sheet** (Form PTO/SB/16) using the data
   in the section above.
5. **Prepare drawings** (Figures 1–9 above) as a separate PDF
   if drawings will be filed. Provisional drawings are
   permissible in informal form so long as the disclosure is
   understandable.
6. **File via Patent Center** at `patentcenter.uspto.gov`.
   Select **New → Provisional**. Upload the specification PDF,
   drawings PDF (optional but recommended for §112
   enablement), and the cover sheet. Pay the fee.
7. **Record the filing receipt** (Application No. 63/XXX,XXX
   and filing date) and calendar the **12-month deadline** for
   the non-provisional / PCT decision.
8. **Foreign-filing note.** Public disclosure on a public
   repository prior to the priority date may have already
   forfeited absolute-novelty jurisdictions (most non-US
   jurisdictions). The U.S. 35 U.S.C. § 102(b)(1) grace period
   may still preserve U.S. rights for one year from the
   inventor's own disclosure; confirm with counsel.

---

## Risks the Inventor Should Discuss with a Patent Practitioner

- **§101 (subject-matter eligibility).** The claims above are
  framed around concrete technical mechanisms (cryptographic
  hash chains, schema-validated registries, write-once storage
  enforcement, typed drift indicators). Counsel should still
  pressure-test the claims against the 2019 PEG Step 2A/2B
  analysis and the most recent Federal Circuit guidance.
- **§112 (written description and enablement).** This draft
  quotes the canonical dataclasses and method signatures
  in-line rather than incorporating external URLs by
  reference. Counsel should confirm sufficiency, particularly
  for the orchestrator planes and the drift-typing logic.
- **Prior-art landscape.** Commercial AD-to-Entra migration
  toolchains (for example, those sold by Quest, BitTitan,
  Semperis, ENow, and others) and Microsoft's own Cloud Sync
  and Intune analytics products should be searched on Google
  Patents and on `patentscope.wipo.int` for the closest art.
- **Prior public disclosure.** Public materials on
  `whalermike.github.io` and the public source repository may
  constitute prior art outside the U.S. one-year grace period.
- **Inventorship.** Confirm sole / joint inventorship of every
  claimed feature; misjoinder or non-joinder is curable but
  best avoided.

---

*End of provisional patent application draft.*
