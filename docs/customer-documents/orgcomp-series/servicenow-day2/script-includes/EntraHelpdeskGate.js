// Script Include: EntraHelpdeskGate  (application scope: x_fed_day2_ops)
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
//     is coerced (ServiceNow catalog variables arrive as the string 'true'), and
//     is ALSO derived server-side from the target against the allowlists in
//     x_fed_day2_ops.privileged_role_template_ids / .privileged_group_ids — a
//     client-supplied false can never override a derived-true classification.
//     Limitation: a request with no role_template_id/group_id/target_id can't be
//     classified against the allowlists and falls back to the self-declared flag
//     alone; the caller must populate one of those fields for full coverage.
//
// test_mode returns deterministic PASS verdicts so ATF can drive the Flow with no
// live Graph. Never enable in production.
// -----------------------------------------------------------------------------
var EntraHelpdeskGate = Class.create();
EntraHelpdeskGate.prototype = {

    initialize: function () {
        this.client = new x_fed_day2_ops.EntraHelpdeskClient();
        // Scoped logging via gs.* — a scoped app cannot `new GSLog(...)` a global
        // Script Include without the `global.` prefix, and GSLog may not exist on
        // every instance; gs.error/warn always resolve. (Sweep: js-cannot-run.)
        this.log = {
            err: function (m) { gs.error('[x_fed_day2_ops.EntraHelpdeskGate] ' + m); },
            warn: function (m) { gs.warn('[x_fed_day2_ops.EntraHelpdeskGate] ' + m); }
        };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
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
        // AC-6: privileged grant must be time-bound. Coerce string variables, and
        // OR in the server-derived classification — a self-declared-false flag
        // must never suppress a target that the allowlists say IS privileged.
        var privileged = this._truthy(request.privileged) || this._classifyPrivileged(request);
        if (privileged && !request.expiry)
            return { ok: false, reason: 'Least privilege: privileged grant requires an expiry (AC-6)' };
        return { ok: true, reason: 'preflight ok' };
    },

    // Server-side privilege classification — do not trust the client flag alone.
    // Checks the request's target against the configured allowlists so a caller
    // can't dodge the AC-6 expiry requirement by leaving `privileged` unticked.
    _classifyPrivileged: function (request) {
        var roleIds = gs.getProperty('x_fed_day2_ops.privileged_role_template_ids', '');
        var groupIds = gs.getProperty('x_fed_day2_ops.privileged_group_ids', '');
        // groupId (camelCase) reuses the SAME catalog field the client actuates
        // with (variable-set-helpdesk-identity.xml's group_id -> groupId); the
        // other two are gate-only fields with their own snake_case mappings.
        var target = request.role_template_id || request.groupId || request.target_id || '';
        if (!target) return false;   // nothing to classify against; self-declared flag still applies
        var ids = (roleIds + ',' + groupIds).split(',');
        for (var i = 0; i < ids.length; i++) {
            var id = ids[i].trim();
            if (id && id === ('' + target).trim()) return true;
        }
        return false;
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
        // Affirmative membership check via Graph's checkMemberGroups action — a
        // 2xx status is NOT membership; the returned group id set must actually
        // contain groupId. A failed or unparseable read is NOT membership.
        var r = this.client._graph('POST', '/users/' + userId + '/checkMemberGroups', { groupIds: [groupId] });
        if (!r.ok) return false;
        try {
            var body = JSON.parse(r.body) || {};
            var ids = body.value || [];
            for (var i = 0; i < ids.length; i++) { if (ids[i] === groupId) return true; }
            return false;
        } catch (e) { return false; }
    },

    type: 'EntraHelpdeskGate'
};
