---
adr_id: adr-091
title: "SQL Server Engine Authentication Transformation — Windows/SQL Auth to Entra ID for SQL Server 2022+"
status: PROPOSED
decided: 2026-06-02
deciders: Michael Stratton
updated: 2026-06-22
next_review: 2026-12-01
review_trigger: SQL Server vNext authentication GA; Azure extension for SQL Server feature changes; any material change to ADR-068 NTLM-elimination phasing or vendor default milestones; consolidation-program target-state decision
impact: UIAO_135 §3.2 (Partially Defined gap closure — SQL Server Authentication, Transformation #7); engine-layer companion to ADR-068 (protocol layer) and ADR-002 (server/OS layer)
supersedes: null
superseded_by: null
publish_to_site: true
publication_style: include
published_at: docs/adr/adr-091-sql-server-authentication-transformation.html
---

# ADR-091: SQL Server Engine Authentication Transformation — Windows/SQL Auth to Entra ID for SQL Server 2022+

## Status

**PROPOSED** — June 2, 2026

## Context

UIAO_135 §3.2 classifies Transformation #7 (SQL Server Authentication — Service Identity) as **Partially Defined**. The destination is named in UIAO_135 §1.2: Windows Authentication and SQL Authentication are eliminated and replaced with Microsoft Entra ID authentication for SQL Server 2022 and later, enforced through OAuth 2.0 tokens, a Managed Identity for the engine process, and multi-factor authentication for all human principals. What is *partially defined* is the normative canon that governs **how the engine-layer transformation is reached**:

- **Discovery is covered.** `Spec3-D1.8` (`Get-SQLServerAuthAudit.ps1`) is the discovery baseline and produces the per-instance authentication-posture record consumed by the CCM-BIR ingestion pipeline.
- **The protocol layer is covered.** ADR-068 (Kerberos / NTLM Elimination) governs the program's progressive elimination of NTLM (direction-not-deadline), the Cloud Kerberos trust posture, and certificate-based-auth rollout. ADR-068 explicitly scopes SQL Server as a separately-covered workload class.
- **The server/OS layer is covered.** ADR-002 (Arc-Enabled Servers Require Non-Domain-Joined State) governs the OS-level Entra identity, Arc enablement, and the domain-unjoin sequencing.
- **The engine layer is NOT yet covered.** No ADR governs the SQL Server *engine* authentication transformation itself — the canonical login-migration sequence, the policy on SQL Authentication and the `sa` account, the exception path for pre-2022 instances, the relationship between estate consolidation and auth migration, and the CCM-BIR evidence artifact that proves an instance has completed the transformation. Without these positions, every engagement re-litigates the same engine-layer decisions and the migration audit cannot certify Transformation #7 closure.

**Numbering note.** This ADR was motivated by the *SQL Server Identity Transformation* narrative series, an early draft of which referred to a "forthcoming ADR-090." ADR-090 was independently accepted on 2026-06-02 for *UIAO Substrate High Availability* and is unrelated to SQL Server. The engine-layer SQL Server authentication decision is therefore recorded here as **ADR-091**.

## Decision

**Five canonical positions, in operational sequence.**

### 1. Estate consolidation assessment precedes and gates engine-layer auth migration

The SQL Server estate that has accumulated across an Active Directory forest over twenty years is not migrated in the shape it is discovered in. Before any instance is migrated to Entra ID authentication, the consolidation assessment (full-estate inventory, utilization and zombie-database detection, version/edition/EOL posture, dependency mapping, and consolidation candidacy) must classify the instance as **retain**, **consolidate-into-target**, or **retire**.

- Engine-layer auth migration is performed **only** on instances classified **retain** or on the **consolidation targets** that absorb consolidated workloads. Instances classified **retire** or **consolidate-into-target (source)** are not migrated — they are decommissioned or collapsed, and migrating their logins to Entra ID first would be wasted effort.
- The consolidation assessment is a documented prerequisite input to the per-instance migration plan. The Arc-eligibility classification from `Spec3-D1.8` (Category 1/2/3) is layered **on top of** the consolidation classification, not before it.
- Consolidation and auth transformation are mutually reinforcing: collapsing many instances across multiple domains into fewer modern SQL Server 2022 targets (or Azure SQL Managed Instance / Arc-enabled SQL) is the natural moment to retire cross-domain login sprawl, orphaned SPNs, and shared service accounts into Entra-backed identity.

### 2. The canonical login migration is a three-phase parallel-run; existing logins are disabled, not dropped, until validated

Principal-type letters throughout this ADR are the values of `sys.server_principals.type`, not mnemonics: **S** SQL login, **U** Windows login, **G** Windows group, **E** external (Entra) login, **X** external (Entra) group, **C** certificate-mapped login. There is no type `W`; a discovery query written against one returns zero rows and reports a clean instance, which would satisfy the §5 closure condition below falsely.

For every instance classified **retain** or **target**, Windows logins (type-U users, type-G groups) and SQL Authentication service-account logins (type-S) are migrated to Entra ID external-provider logins (`CREATE LOGIN [principal] FROM EXTERNAL PROVIDER`, type-E) across three principal types — Entra user, Entra security group, and Entra service principal / Managed Identity.

- **Phase 1 (create):** A type-E equivalent is created for every migrating login. The Entra-to-AD principal mapping (UPN-to-SAMAccountName for users, display name for groups, application ID for service principals) is verified before each `CREATE LOGIN`; any principal with no confirmable Entra equivalent is a blocking finding.
- **Phase 2 (validate):** Each type-E login is exercised with a real Entra-credentialed test authentication. Validation must succeed before the corresponding legacy login is touched.
- **Phase 3 (cutover):** Legacy Windows / SQL Auth logins are **disabled** — not dropped — after their Entra equivalents validate, retained for a **30-day observation window** during which connection monitoring confirms no residual dependency, then dropped.

The parallel-run pattern is **required** for production instances. Non-production instances may compress the observation window with documented owner sign-off.

### 3. SQL Authentication is eliminated; the `sa` account is disabled and renamed on every instance

- Every active SQL Authentication login (type-S) on a **retain**/**target** instance is migrated to a type-E service-principal or Managed-Identity login, or carries a **documented exception** (per §4) with a named compensating control and a sunset date. SQL Authentication produces no Entra ID sign-in events and is invisible to Conditional Access and Defender for Identity; it is not an acceptable steady-state credential.
- The built-in `sa` account is **disabled and renamed** on every production instance. Emergency-access recovery, if retained, is documented as a break-glass procedure with its own monitoring, not as an active `sa` login. An enabled `sa` account with a non-rotated password is the highest-priority remediation finding in the `Spec3-D1.8` audit.

### 4. Pre-2022 instances are upgrade-or-except, with CBA as the interim NTLM-replacement posture

`CREATE LOGIN ... FROM EXTERNAL PROVIDER` requires SQL Server 2022 + the Azure extension for SQL Server on an Arc-enabled host. A pre-2022 instance (Category 3) cannot accept type-E logins regardless of Arc status.

- A Category 3 instance classified **retain** has two paths: **upgrade** the engine to SQL Server 2022 (then proceed through the Category 2 → Category 1 pathway), or file a **documented exception** with a sunset date. Most Category 3 instances should be consolidation **retire** or **consolidate-into-target** candidates per §1 rather than upgrade candidates.
- The exception process requires: the inability-to-migrate reason, the compensating control, the maximum exception duration, and explicit acknowledgement that Microsoft's progressive NTLM default-disable will eventually apply at the network level regardless of engine-layer exception status. Where a connection cannot reach Kerberos or Entra OAuth as vendor defaults tighten, **Certificate-Based Authentication is the authorized interim posture per ADR-068** — which makes the certificate-authority dependency (ADCS → Cloud PKI, UIAO_135 §3.3, "Not Yet Defined") a hard dependency for the exception long-tail.

### 5. The CCM-BIR per-instance record is the closure artifact for Transformation #7

Transformation #7 is closed for an instance when its CCM-BIR record simultaneously shows: `LoginMode = 1` (Windows Authentication Only); zero active type-S logins outside the exception registry; zero active type-U / type-G logins; `sa` disabled and renamed; the Arc Connected Machine agent enrolled and healthy; the Azure extension for SQL Server deployed with the Managed Identity active; and — for human principals — Conditional Access MFA enforcement satisfied for SQL Server resource sign-ins over a defined validation period. Closure is **continuously verified**, not a point-in-time claim: `Spec3-D1.8` runs on a recurring schedule, and CCM-BIR drift events (LoginMode reverting to Mixed Mode, a new type-S/U/G login appearing, the Arc agent going offline) are compliance violations that trigger the remediation workflow.

## Rationale

1. **Consolidation-first prevents wasted migration.** A twenty-year forest estate contains instances that should not survive the transformation at all. Migrating their logins to Entra ID before the consolidation decision spends scarce engineering effort on instances slated for retirement and inflates the apparent migration surface.

2. **Parallel-run is the only safe cutover.** Dropping a Windows login before its Entra equivalent is validated risks locking out a principal whose UPN-to-SAM mapping was wrong. Disable-and-observe makes every cutover reversible inside the 30-day window.

3. **SQL Authentication is an opaque bypass path.** A single active `sa` or type-S login defeats the entire Conditional Access perimeter (§ Access Control), because it authenticates outside the Entra ID plane. The Entra perimeter is binary — it covers all connections or none.

4. **Vendor defaults will tighten regardless of migration status.** ADR-068 Phase C applies network-level NTLM restriction when dependencies are remediated; Microsoft's progressive default-disable milestones will eventually constrain NTLM reliance regardless. The engine-layer migration must therefore maintain forward momentum, with continuous-audit validation confirming posture at each phase.

5. **A defined closure artifact makes the transformation enforceable.** Without the CCM-BIR field set in §5, "done" is a subjective claim. With it, closure is a queryable, continuously-verified posture.

## Implementation Plan

| Phase | Deliverable | Owner | Program schedule |
|---|---|---|---|
| **0** | Full-estate consolidation assessment + per-instance retain/consolidate/retire classification (forthcoming `Spec3-D1.x` estate-consolidation inventory) | DBA + Infrastructure | Ahead of vendor defaults |
| **A** | `Spec3-D1.8` Arc-eligibility + login-type inventory per **retain**/**target** instance | DBA team | Ahead of vendor defaults |
| **A** | CCM-BIR ingestion of per-instance authentication posture | Telemetry team | Ahead of vendor defaults |
| **B** | Arc enablement + Azure extension for SQL Server on Category 2 targets (per ADR-002) | Infrastructure | 2026-Q4 |
| **B** | Phase 1–2 type-E login creation + validation (parallel-run) | DBA team | 2026-Q4 → 2027-Q1 |
| **C** | Phase 3 cutover: disable legacy logins, 30-day observation, drop | DBA team | 2027-Q1 |
| **C** | `sa` disable+rename across estate; type-S elimination or exception filing | DBA team | 2027-Q1 |
| **C** | Pre-2022 exception register with CBA interim posture (per ADR-068) | DBA + App owners | Continuous |
| **C** | CCM-BIR closure-artifact verification per production instance | Telemetry team | 2027-Q1 → 2027-Q2 |

## Consequences

**Positive:**
- The engine-layer transformation is sequenced behind the consolidation decision, so migration effort is spent only on instances that survive.
- Parallel-run cutover is reversible inside a 30-day window; no principal is locked out by a bad mapping.
- The Conditional Access perimeter becomes real once type-S/`sa` paths are closed.
- Closure is a continuously-verified CCM-BIR posture, not a point-in-time spreadsheet.

**Negative:**
- The consolidation assessment is a non-trivial prerequisite program in its own right and has no canonical discovery instrument yet (a `Spec3-D1.x` estate-consolidation inventory must be authored).
- Pre-2022 exception long-tail depends on the ADCS → Cloud PKI transformation (UIAO_135 §3.3), which is "Not Yet Defined."
- The 30-day observation window lengthens the per-instance cutover timeline and must be factored into each instance's migration schedule.

**Operationally accepted:** the post-migration audit must enumerate, per production instance, the CCM-BIR closure-artifact field set, and every pre-2022 exception must carry a sunset date and be reviewed against Microsoft's NTLM default-disable trajectory when updated.

## References

- UIAO_135 §1.2, §3.2, §3.3 — Identity & Directory Transformation Inventory (Transformation #7 destination; Partially Defined / Not Yet Defined gaps)
- ADR-068 — Kerberos / NTLM Elimination (protocol layer; CBA interim posture; progressive NTLM elimination strategy)
- ADR-002 — Arc-Enabled Servers Require Non-Domain-Joined State (server/OS layer; Arc Managed Identity)
- ADR-069 — LDAP-Dependent Application Migration (upstream SQL-consuming application chain)
- ADR-036 — Dynamic Group Provisioning (OrgPath-driven Entra security groups for SQL access)
- ADR-037 — Delegation Matrix / Entra AU provisioning (scoped DBA-team delegation)
- ADR-067 — AD Security Group Rationalization (group-type taxonomy for SQL role mapping)
- ADR-004 — Workload Identity Federation as Default (service-principal / Managed-Identity SQL connections)
- ADR-090 — UIAO Substrate High Availability (unrelated; resolves the prior "forthcoming ADR-090" mislabel)
- Spec3-D1.8 — `Get-SQLServerAuthAudit.ps1` (engine-layer discovery baseline)
- Microsoft Learn: "Microsoft Entra authentication for SQL Server enabled by Azure Arc"
- Microsoft Learn: "CREATE LOGIN ... FROM EXTERNAL PROVIDER (SQL Server 2022)"
