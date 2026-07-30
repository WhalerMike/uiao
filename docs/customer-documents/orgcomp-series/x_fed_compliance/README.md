# `x_fed_compliance` — ServiceNow Federal Control-Compliance scoped app

> Status: DRAFT importable skeleton · Surface: `inbox/` (not canon) · Vol VII Book 05's deployable
> Scope: **FedRAMP Moderate + Microsoft GCC Moderate** only. Date Code: 2026-07-14 11:55 ET

The scoped app Vol VII Book 05 describes — the deployable counterpart to Books
00–04. It implements the five-step compliance loop (**test → detect → raise →
actuate-native → close+evidence**) over the two surfaces that carry most federal
control work: **M365** (Graph Conditional-Access + secure-score) and **Azure**
(ARM — Defender-for-Cloud assessments + Update Manager). ServiceNow **coordinates** — who, when, approval,
evidence; actuation stays **platform-native** (Vol VII Book 00 doctrine, no
exceptions).

Until 2026-07-14 this kit existed only as prose: Book 05 called itself "the
deployable counterpart" while Volume VII registered no kit and nothing named
`x_fed_compliance` was on disk. This skeleton closes that gap and is
registered in `orgcomp-compliance-spine.yml` (`kits:`), so the distribution-kit
build bundles it — and its self-check *expects* it — automatically from here on.

## What's here

| Path | Record / artifact | Role |
|---|---|---|
| [`script-includes/ComplianceIngest.js`](./script-includes/ComplianceIngest.js) | `sys_script_include` | Reader — pulls M365 (Graph Conditional-Access + secure-score) and Azure (ARM Defender-for-Cloud assessments + Update Manager) control state via the in-boundary MID |
| [`script-includes/ComplianceReconcile.js`](./script-includes/ComplianceReconcile.js) | `sys_script_include` | Binds each finding's asset to the authoritative IPAM/DDI CI (CM-8 join) **before** any task is raised — an unreconciled asset is itself a finding |
| [`script-includes/ComplianceGate.js`](./script-includes/ComplianceGate.js) | `sys_script_include` | Post-actuation validation — re-reads the native surface, confirms closure by observation, stamps the re-test evidence (CA-7) |
| [`data/control-map.json`](./data/control-map.json) | app data (CI-checked) | Finding-class → (control, task type, approval, actuation, KSI, slot) — projection of the spine's Book 02/03/04 closures, validated by `validate_day2_control_maps.py` |
| [`flow/flow-blueprint.md`](./flow/flow-blueprint.md) | Flow Designer blueprint | "Detect & Route Control Drift", the exception-review flow, and the attestation-emit job |
| [`rest/README.md`](./rest/README.md) | `sys_rest_message` spec | Graph + ARM outbound REST messages — endpoint/auth shape; XML exported per tenant |
| [`mid/compliance-validate.sh`](./mid/compliance-validate.sh) | MID Server script | Runs the per-surface read/validate on the in-boundary MID host; one JSON verdict out |
| [`atf/README.md`](./atf/README.md) | ATF test spec | Happy path + negatives (unreconciled asset, self-approval, SLA breach) via `test_mode` |
| [`update-set/README.md`](./update-set/README.md) | update set | How the app assembles into one importable XML |
| [`LIVE-VALIDATION-M365-TENANT.md`](./LIVE-VALIDATION-M365-TENANT.md) | validation runbook | SER-4: proving `ComplianceGate._checkWriteScope` against a real Microsoft 365 Developer Program tenant, not just `test_mode` fixtures |

## The pattern (Vol VII Books 00–04, as code)

1. **Test/Detect** — `ComplianceIngest` reads native control state on a schedule; drift = a finding.
2. **Reconcile** — `ComplianceReconcile` joins the finding's asset to its IPAM/DDI-keyed CI (the CM-8 inventory join, Vol VII Book 01). No CI, no task — the unreconciled asset becomes its own finding, booked under the CA-7 conmon rollup (`attest.conmon.rollup`).
3. **Raise** — the Flow opens the Incident/Change the control map dictates, with the KSI binding from `data/control-map.json`; owner and SLA come from ServiceNow assignment rules and SLA definitions, not the control map.
4. **Actuate native** — remediation runs on the platform (Azure Policy remediation, Conditional Access edit) — never from ServiceNow write scopes.
5. **Close + evidence** — `ComplianceGate` re-reads the surface, proves closure by observation, and stamps the evidence record that feeds Book 04 attestation (CA-2/CA-5/CA-7) and the KSI pipeline.

## Boundary and least privilege

- Every callout runs through a **MID Server registered inside the ATO boundary**; credentials and execution never leave it.
- The service identity holds **read** over Conditional Access, directory, secure-configuration and Azure posture state — plus task-creation only. **Never standing write** over the estate it governs.
- `test_mode` (`x_fed_compliance.test_mode`) returns deterministic fixtures so ATF runs with no live tenant. Never enable in production.

## Status — starter skeleton, not a signed product

Same disposition as the DDI app skeleton and the day-2 kit: review the records,
complete the connector credential aliases per tenant, pin API versions, and test
in a sub-prod instance before any production use. The `rest/`, `atf/` and
`update-set/` artifacts are specs to export from a sub-prod build, exactly as
`servicenow-day2` ships them.
