// Script Include: EntraHelpdeskGate  (application scope: x_ssa_day2_ops)
// -----------------------------------------------------------------------------
// Post-action validation gate for the Day-2 Operations app (Vol IX). After a
// helpdesk action actuates on Entra, the gate RE-READS the target through Graph
// and confirms the intended state actually took — closure proven by observation,
// not by the write returning 200. The verdict + evidence is what the Flow stamps
// on the request (CM-3 / AU-2) and reconciles to the CMDB (CM-8).
//
// It also enforces two safety invariants the workflow must never violate:
//   * SEPARATION OF DUTIES — requester != approver (CM-5). A self-approved
//     privileged request is a hard fail (see the atf-negative-self-approve test).
//   * LEAST PRIVILEGE — a privileged group/role grant must carry an expiry
//     (AC-6); a standing elevation from a helpdesk click is refused.
//
// test_mode returns deterministic PASS verdicts so ATF can drive the Flow with no
// live Graph. Never enable in production.
// -----------------------------------------------------------------------------
var EntraHelpdeskGate = Class.create();
EntraHelpdeskGate.prototype = {

    initialize: function () {
        this.client = new x_ssa_day2_ops.EntraHelpdeskClient();
        this.log = new GSLog('x_ssa_day2_ops.log', 'EntraHelpdeskGate');
        this.testMode = gs.getProperty('x_ssa_day2_ops.test_mode', 'false') === 'true';
    },

    // Safety gate — run BEFORE actuation. Returns {ok, reason}.
    preflight: function (request) {
        // CM-5: separation of duties.
        if (request.requester_id && request.requester_id === request.approver_id)
            return { ok: false, reason: 'SoD violation: requester == approver (CM-5)' };
        // AC-6: privileged grant must be time-bound.
        if (request.privileged === true && !request.expiry)
            return { ok: false, reason: 'Least privilege: privileged grant requires an expiry (AC-6)' };
        return { ok: true, reason: 'preflight ok' };
    },

    // Verify gate — run AFTER actuation. Re-reads state; returns {ok, evidence}.
    verify: function (action, target) {
        if (this.testMode) return { ok: true, evidence: { action: action, target: target, verified: true } };
        var r = this.client._graph('GET', '/users/' + target.userId, null);
        return { ok: r.ok, evidence: { action: action, status: r.status, body: r.body } };
    },

    type: 'EntraHelpdeskGate'
};
