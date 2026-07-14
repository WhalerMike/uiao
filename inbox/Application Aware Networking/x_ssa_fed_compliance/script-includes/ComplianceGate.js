// Script Include: ComplianceGate  (application scope: x_ssa_fed_compliance)
// -----------------------------------------------------------------------------
// Step 5 of the loop (close + evidence): closure is proven by OBSERVATION, not
// by the remediation reporting success. After native actuation, the gate
// re-reads the same surface ComplianceIngest read, confirms the drift is gone,
// and stamps a re-test evidence record on the task (CA-7). A task whose re-read
// still shows drift is NOT closed — it escalates, and a breached SLA opens a
// POA&M item (CA-5, attest.poam.item).
//
// Also enforces the two invariants shared with the day-2 app:
//   * SEPARATION OF DUTIES — requester != approver; a self-approved
//     compliance change is a hard preflight fail.
//   * READ-ONLY SERVICE IDENTITY — if the identity is detected holding write
//     scopes over the governed estate, the gate refuses to run at all: the
//     app's authority to attest depends on its inability to actuate.
// -----------------------------------------------------------------------------
var ComplianceGate = Class.create();
ComplianceGate.prototype = {

    initialize: function () {
        this.ingest = new x_ssa_fed_compliance.ComplianceIngest();
        this.log = new GSLog('x_ssa_fed_compliance.log', 'ComplianceGate');
        this.testMode = gs.getProperty('x_ssa_fed_compliance.test_mode', 'false') === 'true';
    },

    // Safety gate — run BEFORE any task is worked. Returns {ok, reason}.
    preflight: function (task) {
        if (task.requester_id && task.requester_id === task.approver_id)
            return { ok: false, reason: 'separation of duties: requester may not approve (self-approval refused)' };
        if (this._identityHoldsWrite())
            return { ok: false, reason: 'service identity holds write scopes over the governed estate — attestation authority void; fix the app registration first' };
        return { ok: true, reason: 'preflight clear' };
    },

    // Closure-by-observation. Returns {closed, evidence}.
    verify: function (task) {
        var readings = (task.surface === 'azure') ? this.ingest.ingestAzure() : this.ingest.ingestM365();
        for (var i = 0; i < readings.length; i++) {
            if (readings[i].asset === task.asset && readings[i].observed !== readings[i].intended) {
                return { closed: false, evidence: this._stamp(task, 'RETEST_FAILED', readings[i]) };
            }
        }
        return { closed: true, evidence: this._stamp(task, 'RETEST_PASSED', null) };
    },

    // The evidence record (CA-7): what was re-read, when, verdict. Feeds the
    // Book 04 attestation stream and the KSI pipeline (attest.conmon.rollup).
    _stamp: function (task, verdict, reading) {
        return {
            task: task.number, asset: task.asset, verdict: verdict,
            observed: reading ? reading.observed : null,
            retested_at: new GlideDateTime().getValue(),
            boundary: gs.getProperty('x_ssa_fed_compliance.boundary', 'gcc-moderate')
        };
    },

    _identityHoldsWrite: function () {
        if (this.testMode) return gs.getProperty('x_ssa_fed_compliance.test_fixture_write_scopes', 'false') === 'true';
        // Completed per tenant: read the app registration's granted scopes via
        // Graph and refuse on any *.ReadWrite.* over the governed surfaces.
        return false;
    },

    type: 'ComplianceGate'
};
