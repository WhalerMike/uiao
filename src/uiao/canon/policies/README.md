---
document_id: UIAO_116_policies_index
title: "EPL Reference Policies (UIAO_116)"
status: Current
classification: CANONICAL
---

# EPL Reference Policies

This directory holds the canonical Enforcement Policy Language
(UIAO_116, §3.5) policies the substrate's Enforcement Runtime
(UIAO_111, §3.3) consumes. Each YAML file ships one policy; the
loader (`uiao.governance.epl.load_canonical_policies`) walks the
directory and parses every `*.yaml` / `*.yml` it finds.

## Adding a policy

1. Create `<policy-slug>.yaml` in this directory. Use a unique `id:`
   following the convention `epl:<verb>-<subject>` (e.g.
   `epl:enforce-mfa`, `epl:block-out-of-scope`).
2. Provide a one-paragraph `description:` that explains the policy
   intent in operational terms (what an SOC analyst would do when this
   fires).
3. Specify the trigger predicate under `when:`. Empty fields are
   wildcards. Recognized fields:
   - `drift_class:` — list of `DRIFT-SCHEMA` / `DRIFT-SEMANTIC` /
     `DRIFT-PROVENANCE` / `DRIFT-AUTHZ` / `DRIFT-IDENTITY` /
     `DRIFT-BOUNDARY`
   - `controls:` — list of NIST control ids (e.g. `AC-2`, `IA-2`)
   - `adapter_ids:` — list of canon adapter ids
   - `pillars:` — list of CISA ZTMM v2.0 pillars (UIAO_120 vocabulary)
   - `severity_min:` — `Low` / `Medium` / `High` (or `P5`..`P1`).
     Triggers only when the finding severity meets or exceeds this.
4. Specify the action under `then:`:
   - `action:` — `log` / `alert` / `remediate` / `block` / `escalate`
   - `actor:` — responsible system or role
   - `sla_hours:` — response SLA in hours
   - `runbook:` — optional reference to a UIAO doc with detailed steps

## Reference policies shipped today

| Policy id | Trigger | Action | SLA |
|---|---|---|---|
| `epl:enforce-mfa` | DRIFT-SEMANTIC, IA-2 family, ≥Medium | alert+remediate | 24h |
| `epl:block-out-of-scope` | DRIFT-AUTHZ (any) | block | immediate |
| `epl:escalate-stale-evidence` | DRIFT-SEMANTIC, ≥High | escalate | 4h |
| `epl:fix-broken-issuer-chain` | DRIFT-IDENTITY, ≥High | alert+remediate | 8h |
| `epl:audit-schema-drift` | DRIFT-SCHEMA, ≥Medium | alert | 24h |
