---
document_id: UIAO_133
title: "Architectural Decision Records — Index"
version: "1.0"
status: Current
classification: OPERATIONAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-04-28"
updated_at: "2026-04-28"
---

# Architectural Decision Records — Index

> **Purpose:** Registry of all UIAO Architectural Decision Records (ADRs). Each ADR captures a load-bearing architectural decision, its context, consequences, and the specific conditions under which it must be re-evaluated.

## ADR Registry

| ADR ID | Title | Status | Decided | Next Review | Impact |
|---|---|---|---|---|---|
| [ADR-001](adr-001-haadj-deprecated-entra-join-only.md) | HAADJ Deprecated — Entra ID Join as Sole Device Join Target | ACCEPTED | 2026-04-28 | 2026-11-01 (post-Ignite) | Spec 1: Computer Objects |
| [ADR-002](adr-002-arc-entra-join-no-domain-join.md) | Arc-Enabled Servers Require Non-Domain-Joined State | ACCEPTED | 2026-04-28 | 2026-11-01 (post-Ignite) | Spec 1: Computer Objects |
| [ADR-003](adr-003-api-driven-inbound-provisioning.md) | API-Driven Inbound Provisioning as HR-Agnostic Canonical Path | ACCEPTED | 2026-04-28 | 2026-07-01 (post-GAO decision) | Spec 2: HR Provisioning |
| [ADR-004](adr-004-workload-identity-federation-default.md) | Workload Identity Federation as Default for External Integrations | ACCEPTED | 2026-04-28 | 2026-11-01 (post-Ignite) | Spec 3: Service Accounts |

## ADR Lifecycle

```
PROPOSED → ACCEPTED → CURRENT
                   ↘ SUPERSEDED (by ADR-NNN)
                   ↘ DEPRECATED (rationale no longer applies)
                   ↘ AMENDED (minor update, same ADR ID, version bump)
```

## Review Cadence

See [adr-review-protocol.md](adr-review-protocol.md) for the full review mechanism.

| Trigger | Timing | Action |
|---|---|---|
| **Microsoft Ignite** | November annually | Review all ADRs against announcements |
| **Microsoft Build** | May annually | Review all ADRs against announcements |
| **Entra ID Changelog** | Monthly | Scan for changes to decision-relevant features |
| **OPM HR Procurement** | Ad hoc (GAO decisions) | Review ADR-003 specifically |
| **UIAO Quarterly Governance** | Quarterly | Formal ADR status review as part of governance cycle |
