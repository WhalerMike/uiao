// Script Include: PimActivationClient  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// Just-in-time privileged elevation for the Day-2 Operations app (Vol IX) —
// MACD-R Lifecycle clause 3 (Vol 0 Book 00): every privileged task actuates under
// a SCOPED, TIME-BOXED role activated at execution, and holds NO standing admin.
//
// The kit activates a Privileged Access Group (PAG) via Microsoft PIM for Groups
// rather than a standing directory-role assignment. On activation PIM returns a
// request id — THE ACTIVATION ID — which the Flow stamps into the task's evidence
// record. That id is what binds *who could act* to *what was done*: least
// privilege made auditable (AC-6, AC-5, IA-2, AU-2).
//
// Config (see KIT-VARIABLES-REFERENCE.md, section 3b):
//   x_fed_day2_ops.pag_object_id          the PAG the operator self-activates into
//   x_fed_day2_ops.pim_activation_max_minutes time-box on the elevation (default 60)
//   x_fed_day2_ops.pim_justification      whether a justification is required
//
// Boundary discipline: the activation call is a Graph call and routes through the
// in-boundary MID via the shared EntraHelpdeskClient._graph transport — no second
// credential, no second egress path. GCC-Moderate → graph.microsoft.com.
//
// STARTER SKELETON — validate the PIM-for-Groups API shape against your tenant and
// pin the Graph version before production. test_mode returns a deterministic
// activation id so the ATF suites drive the Flow with no live PIM. Never enable
// test_mode in production.
// -----------------------------------------------------------------------------
var PimActivationClient = Class.create();
PimActivationClient.prototype = {

    initialize: function () {
        this.client = new x_fed_day2_ops.EntraHelpdeskClient();   // reuse the MID-routed Graph transport
        this.pag = gs.getProperty('x_fed_day2_ops.pag_object_id', '');
        this.minutes = parseInt(gs.getProperty('x_fed_day2_ops.pim_activation_max_minutes', '60'), 10) || 60;
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.PimActivationClient] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // Activate the PAG for the acting principal. Returns the activation id + window
    // so the Flow can (a) stamp evidence and (b) actuate only inside the window.
    // FAIL CLOSED: no PAG configured, or a non-2xx from PIM, yields ok:false — the
    // task must not actuate the estate without a proven, time-boxed elevation.
    activate: function (principalId, justification) {
        if (this.testMode)
            return { ok: true, activationId: 'test-pim-activation-0001', principalId: principalId,
                     expiresInMinutes: this.minutes, action: 'selfActivate' };
        if (!this.pag)
            return { ok: false, reason: 'no PAG configured (x_fed_day2_ops.pag_object_id) — refusing to actuate without JIT elevation (AC-6)' };
        if (!principalId)
            return { ok: false, reason: 'no acting principal — cannot bind who-could-act to what-was-done (AU-2)' };
        if (!justification)
            return { ok: false, reason: 'PIM activation requires a justification — captured as evidence (AU-2)' };

        var body = {
            accessId: 'member',
            principalId: principalId,
            groupId: this.pag,
            action: 'selfActivate',
            justification: justification,
            scheduleInfo: {
                startDateTime: null,   // now
                expiration: { type: 'afterDuration', duration: 'PT' + this.minutes + 'M' }
            }
        };
        var r = this.client._graph('POST', '/identityGovernance/privilegedAccess/group/assignmentScheduleRequests', body);
        if (!r.ok) {
            this.log.logErr('PIM activation failed: status ' + r.status);
            return { ok: false, status: r.status, reason: 'PIM activation did not succeed — no elevation, no actuation' };
        }
        var id = '';
        try { id = (JSON.parse(r.body) || {}).id || ''; } catch (e) { /* id absent — surfaced below */ }
        return { ok: !!id, activationId: id, principalId: principalId, expiresInMinutes: this.minutes,
                 reason: id ? 'activated' : 'PIM returned 2xx but no activation id — inconclusive, fail closed' };
    },

    // Deactivate early (least privilege: give the window back when the task closes).
    // Best-effort — the time-box guarantees expiry regardless, so a failed
    // deactivate does not fail the task, only logs.
    deactivate: function (principalId) {
        if (this.testMode) return { ok: true, principalId: principalId, action: 'selfDeactivate' };
        var body = { accessId: 'member', principalId: principalId, groupId: this.pag, action: 'selfDeactivate' };
        var r = this.client._graph('POST', '/identityGovernance/privilegedAccess/group/assignmentScheduleRequests', body);
        if (!r.ok) this.log.logErr('PIM deactivate best-effort failed: status ' + r.status);
        return { ok: r.ok, status: r.status };
    },

    type: 'PimActivationClient'
};
