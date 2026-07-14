# ATF test spec — `x_ssa_fed_compliance`

Runnable via `x_ssa_fed_compliance.test_mode = true` (deterministic fixtures,
no live tenant). Export the `sys_atf_test` XML from a sub-prod build into the
update set. Negatives are the point:

| Test | Asserts |
|---|---|
| `happy_path_drift_to_evidence` | fixture drift → reconciled CI → task with control+KSI from the map → RETEST_PASSED stamp on close |
| `unreconciled_asset_raises_inventory_finding` | asset `unreconciled-*` → NO task for the original finding; a CM-8 inventory finding instead |
| `self_approval_is_refused` | `preflight` fails when requester == approver |
| `write_scope_voids_attestation` | with `test_fixture_write_scopes=true`, the gate refuses to run at all |
| `retest_failed_blocks_closure` | a task whose re-read still shows drift cannot close; escalates |
| `sla_breach_opens_poam` | breached SLA → linked `attest.poam.item` (CA-5) |
| `unknown_finding_class_is_flow_error` | a finding class absent from control-map.json errors; no default task |
