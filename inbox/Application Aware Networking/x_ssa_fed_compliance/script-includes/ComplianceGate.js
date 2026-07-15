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
        // Scoped logging via gs.* (a scoped app cannot `new GSLog(...)` a global
        // Script Include unprefixed; gs.error/warn always resolve).
        this.log = {
            err: function (m) { gs.error('[x_ssa_fed_compliance.ComplianceGate] ' + m); },
            warn: function (m) { gs.warn('[x_ssa_fed_compliance.ComplianceGate] ' + m); }
        };
        this.testMode = gs.getProperty('x_ssa_fed_compliance.test_mode', 'false') === 'true';
    },

    // Safety gate — run BEFORE any task is worked. Returns {ok, reason}. FAIL CLOSED.
    preflight: function (task) {
        // CM-5: missing either id is indeterminate, not a pass.
        if (!task.requester_id || !task.approver_id)
            return { ok: false, reason: 'separation of duties indeterminate: requester/approver not populated' };
        if (task.requester_id === task.approver_id)
            return { ok: false, reason: 'separation of duties: requester may not approve (self-approval refused)' };
        // The app's authority to ATTEST depends on its inability to ACTUATE. An
        // UNVERIFIED read-only check is treated exactly like a failure — the gate
        // must not proceed as if it confirmed something it never checked.
        var scope = this._identityWriteScopeStatus();
        if (scope !== 'confirmed-readonly')
            return { ok: false, reason: 'read-only-identity check is ' + scope +
                     ' — attestation authority void until affirmatively confirmed read-only' };
        return { ok: true, reason: 'preflight clear' };
    },

    // Closure-by-observation. Returns {closed, evidence}. FAIL CLOSED on every
    // branch that is not an AFFIRMATIVE observation of compliance:
    //   * a READ_FAILED sentinel in the readings -> RETEST_INCONCLUSIVE
    //   * the asset absent from the re-read       -> RETEST_INCONCLUSIVE
    //   * observed != intended                    -> RETEST_FAILED
    //   * observed == intended                    -> RETEST_PASSED (the only close)
    // The old version inferred closure from ABSENCE of a drift reading, so a
    // failed re-read (which returns no drift row) looked like success. (Sweep H.)
    verify: function (task) {
        var readings = (task.surface === 'azure') ? this.ingest.ingestAzure() : this.ingest.ingestM365();

        for (var i = 0; i < readings.length; i++) {
            if (readings[i].observed === 'READ_FAILED') {
                this.log.warn('re-read failed for task ' + task.number + ' — inconclusive, not closing');
                return { closed: false, evidence: this._stamp(task, 'RETEST_INCONCLUSIVE', readings[i]) };
            }
        }
        var seen = null;
        for (var j = 0; j < readings.length; j++) {
            if (readings[j].asset === task.asset) { seen = readings[j]; break; }
        }
        if (!seen) {
            return { closed: false, evidence: this._stamp(task, 'RETEST_INCONCLUSIVE',
                     { asset: task.asset, observed: 'NOT_OBSERVED', intended: task.intended }) };
        }
        if (seen.observed !== seen.intended) {
            return { closed: false, evidence: this._stamp(task, 'RETEST_FAILED', seen) };
        }
        return { closed: true, evidence: this._stamp(task, 'RETEST_PASSED', seen) };
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

    // Returns 'confirmed-readonly' | 'holds-write' | 'unverified'. The gate closes
    // on 'confirmed-readonly' only; 'unverified' fails closed exactly like
    // 'holds-write'. The old _identityHoldsWrite() returned false unconditionally
    // in production, so the write-scope refusal existed ONLY under test_mode — a
    // stub that gave false assurance the identity was read-only. (Sweep H.)
    _identityWriteScopeStatus: function () {
        if (this.testMode) {
            return gs.getProperty('x_ssa_fed_compliance.test_fixture_write_scopes', 'false') === 'true'
                ? 'holds-write' : 'confirmed-readonly';
        }
        // Production: implemented per tenant — read the app registration's granted
        // appRoleAssignments / oauth2PermissionGrants via Graph and confirm no
        // *.ReadWrite.* over the governed surfaces, then return
        // 'confirmed-readonly' or 'holds-write'. Until that read is wired to the
        // tenant (guarded by scope_check_enabled), the status is UNVERIFIED and the
        // gate fails closed — it never assumes read-only it did not confirm.
        if (gs.getProperty('x_ssa_fed_compliance.scope_check_enabled', 'false') !== 'true') {
            return 'unverified';
        }
        // TODO(per-tenant): perform the Graph scope read here and return the verdict.
        return 'unverified';
    },

    type: 'ComplianceGate'
};
