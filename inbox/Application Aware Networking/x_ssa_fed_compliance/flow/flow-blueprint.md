# Flow Designer blueprints — `x_ssa_fed_compliance`

> DRAFT (Vol VII Book 05). Build in Flow Designer per this spec, then export in
> the update set. Every flow enforces the coordination doctrine: ServiceNow
> raises/routes/evidences; actuation is platform-native.

## Flow 1 — Detect & Route Control Drift (scheduled)
1. **Trigger**: schedule (default 6h) or MID verdict-file arrival.
2. `ComplianceIngest.ingestM365()` + `.ingestAzure()` → findings.
3. For each finding: `ComplianceReconcile.reconcile(finding)`.
   - **No CI → no task**: `raiseUnreconciled()` instead (CM-8 inventory defect).
4. Look up the finding class in `data/control-map.json` → task type, approval,
   SLA class, KSI, slot. Unknown class = flow error, not a default task.
5. Open the Incident/Change with owner + SLA; stamp control + KSI on the record.

## Flow 2 — Exception Review
Approval path for `m365.account.exception`: security approver distinct from the
requester (`ComplianceGate.preflight` refuses self-approval), mandatory expiry,
scheduled access review at expiry. Reuses the Vol VII Book 02 pattern.

## Flow 3 — Attestation Emit (scheduled)
1. Collect `ComplianceGate.verify()` evidence stamps since last run.
2. Roll up posture per control; emit the OSCAL/KSI evidence record
   (`attest.conmon.rollup`) to the Book 04 attestation stream.
3. Any task closed WITHOUT a RETEST_PASSED stamp is reopened — closure is
   proven by observation, not by ticket state.

## SLA breach
A breached remediation SLA opens a POA&M item (`attest.poam.item`, CA-5) linked
to the breaching task. This is the atf-negative-sla-breach test.
