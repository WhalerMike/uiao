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
//     privileged request is a hard fail. INDETERMINATE (either id missing) also
//     fails — the check is fail-CLOSED, never skipped.
//   * LEAST PRIVILEGE — a privileged group/role grant must carry an expiry
//     (AC-6); a standing elevation from a helpdesk click is refused. `privileged`
//     is coerced (ServiceNow catalog variables arrive as the string 'true').
//
// test_mode returns deterministic PASS verdicts so ATF can drive the Flow with no
// live Graph. Never enable in production.
// -----------------------------------------------------------------------------
var EntraHelpdeskGate = Class.create();
EntraHelpdeskGate.prototype = {

    initialize: function () {
        this.client = new x_ssa_day2_ops.EntraHelpdeskClient();
        // Scoped logging via gs.* — a scoped app cannot `new GSLog(...)` a global
        // Script Include without the `global.` prefix, and GSLog may not exist on
        // every instance; gs.error/warn always resolve. (Sweep: js-cannot-run.)
        this.log = {
            err: function (m) { gs.error('[x_ssa_day2_ops.EntraHelpdeskGate] ' + m); },
            warn: function (m) { gs.warn('[x_ssa_day2_ops.EntraHelpdeskGate] ' + m); }
        };
        this.testMode = gs.getProperty('x_ssa_day2_ops.test_mode', 'false') === 'true';
    },

    // Coerce a ServiceNow variable (boolean true OR string 'true') to boolean.
    _truthy: function (v) { return v === true || v === 'true'; },

    // Safety gate — run BEFORE actuation. Returns {ok, reason}. FAIL CLOSED.
    preflight: function (request) {
        // CM-5: separation of duties. Missing either id is INDETERMINATE, not a
        // pass — a request with no populated requester/approver must not proceed.
        if (!request.requester_id || !request.approver_id)
            return { ok: false, reason: 'SoD indeterminate: requester/approver not populated (CM-5)' };
        if (request.requester_id === request.approver_id)
            return { ok: false, reason: 'SoD violation: requester == approver (CM-5)' };
        // AC-6: privileged grant must be time-bound. Coerce string variables.
        if (this._truthy(request.privileged) && !request.expiry)
            return { ok: false, reason: 'Least privilege: privileged grant requires an expiry (AC-6)' };
        return { ok: true, reason: 'preflight ok' };
    },

    // Verify gate — run AFTER actuation. Re-reads state and asserts the intended
    // post-state actually took. FAIL CLOSED: a failed/unparseable re-read, or an
    // action with no post-state assertion, returns ok:false (inconclusive), never
    // a pass. A 2xx on the read is NOT closure — the property must be observed.
    verify: function (action, target) {
        if (this.testMode) return { ok: true, evidence: { action: action, target: target, verified: true } };

        var r = this.client._graph('GET', '/users/' + target.userId, null);
        if (!r.ok)
            return { ok: false, evidence: { action: action, status: r.status, reason: 're-read failed — inconclusive, not closed' } };
        var user;
        try { user = JSON.parse(r.body) || {}; }
        catch (e) { return { ok: false, evidence: { action: action, reason: 're-read unparseable — inconclusive' } }; }

        var asserted;
        switch (action) {
            case 'disableUser':
                asserted = (user.accountEnabled === false); break;
            case 'createUser':
                asserted = !!user.id; break;
            case 'assignLicense':
                asserted = this._hasLicense(user, target.skuId); break;
            case 'addGroupMember':
                asserted = this._isMember(target.groupId, target.userId); break;
            default:
                // No post-state assertion defined — do NOT claim verified.
                return { ok: false, evidence: { action: action, reason: 'no post-state assertion for action — verification inconclusive' } };
        }
        return { ok: asserted, evidence: { action: action, asserted: asserted, accountEnabled: user.accountEnabled } };
    },

    _hasLicense: function (user, skuId) {
        var lic = (user && user.assignedLicenses) || [];
        for (var i = 0; i < lic.length; i++) { if (lic[i].skuId === skuId) return true; }
        return false;
    },

    _isMember: function (groupId, userId) {
        // Affirmative membership check; a failed read is NOT membership.
        var r = this.client._graph('GET', '/groups/' + groupId + '/members/' + userId, null);
        return r.ok;
    },

    type: 'EntraHelpdeskGate'
};
