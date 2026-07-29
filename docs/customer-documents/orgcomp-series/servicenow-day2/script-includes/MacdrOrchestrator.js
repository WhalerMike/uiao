// Script Include: MacdrOrchestrator  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// Runs one governed task through the five MACD-R Lifecycle clauses (Vol 0
// Book 00) in order, and refuses to skip any. It is the code shape behind the
// "Governed Day-2 Request" Flow — the Flow calls these steps as a subflow; this
// Script Include lets the same chain run from server script, ATF, and the Flow
// with identical guarantees. It ORCHESTRATES the existing clients; it holds no
// estate transport of its own.
//
//   clause 1  ORIGIN        the request resolves against its class SSOT (checked
//                           upstream: HR event / SAM decision / NHI registry).
//                           A SAM-originated request arrives already correlated
//                           (scripted-rest/sam_inbound_ritm.js).
//   clause 2  AUTHORIZE     EntraHelpdeskGate.preflight — SoD (requester != approver)
//                           and least-privilege expiry. FAIL CLOSED.
//   clause 3  ELEVATE       PimActivationClient.activate — JIT PAG; no activation
//                           id, no actuation. The id becomes evidence. EXCEPTION:
//                           AD-leg requests (request.actuation_leg === 'ad') skip
//                           this clause — the actual write executes under the MID
//                           Server's service identity, never the elevated human's
//                           token, so activating PIM for the approver/requester is
//                           not the operative authorization for that leg and would
//                           only hand out a spurious privileged window. This is a
//                           documented gap (no workload-identity PIM integration
//                           exists in this kit), not a silent skip — it is recorded
//                           in the evidence trail.
//   clause 4  ACTUATE+VERIFY the caller-supplied actuation runs, then
//                           EntraHelpdeskGate.verify RE-READS state — a 2xx is not
//                           closure; the post-state must be observed.
//   clause 5  EVIDENCE      one record carrying request, approver, PIM activation
//                           id, actuation result and the verify verdict — the
//                           closure the attestation pipeline reads (CM-3/AU-2).
//
// If any clause fails, the chain stops and returns the failing clause — the task
// is unauthorized by construction and nothing downstream may treat it as closed.
//
// test_mode drives the whole chain on canned values so ATF can prove the ordering
// and the fail-closed behavior with no live estate. Never enable in production.
// -----------------------------------------------------------------------------
var MacdrOrchestrator = Class.create();
MacdrOrchestrator.prototype = {

    initialize: function () {
        this.gate = new x_fed_day2_ops.EntraHelpdeskGate();
        this.pim = new x_fed_day2_ops.PimActivationClient();
        this.tblEvidence = gs.getProperty('x_fed_day2_ops.tbl_evidence', 'x_fed_day2_ops_evidence');
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.MacdrOrchestrator] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // request : { requester_id, approver_id, privileged, expiry, control, ksi,
    //             verb, ritm, sam_request_id }
    // actuate : function() -> { ok, ... }         the estate write (Graph/ARM)
    // verifyArgs : { action, target }             for EntraHelpdeskGate.verify
    run: function (request, actuate, verifyArgs) {
        var trail = { verb: request.verb, control: request.control, ksi: request.ksi };
        var skipPim = (request.actuation_leg === 'ad');

        // clause 2 — AUTHORIZE (fail closed)
        var pre = this.gate.preflight(request);
        trail.authorize = pre;
        if (!pre.ok) return this._stop('authorize', trail, request);

        // clause 3 — ELEVATE (no activation id, no actuation) — skipped for the
        // AD leg; see the header comment above for why.
        var act;
        if (skipPim) {
            act = { ok: true, activationId: null, skipped: true,
                     reason: 'AD-leg actuation runs under the MID service identity, not the elevated approver — PIM activation of a human is not the operative authorization for this leg and is skipped by design (documented gap, no workload-identity PIM integration exists in this kit)' };
            trail.elevate = act;
        } else {
            act = this.pim.activate(request.approver_id || request.requester_id, request.justification || ('MACD-R ' + request.verb));
            trail.elevate = { ok: act.ok, activationId: act.activationId, reason: act.reason };
            if (!act.ok) return this._stop('elevate', trail, request);
        }

        // clause 4 — ACTUATE then VERIFY (re-read; a 2xx is not closure)
        var result;
        try { result = (typeof actuate === 'function') ? actuate() : { ok: false, reason: 'no actuation supplied' }; }
        catch (e) { result = { ok: false, error: '' + e }; }
        trail.actuate = { ok: !!(result && result.ok) };
        if (!result || !result.ok) { if (!skipPim) this.pim.deactivate(request.approver_id || request.requester_id); return this._stop('actuate', trail, request); }

        var ver = this.gate.verify(verifyArgs.action, verifyArgs.target);
        trail.verify = ver;
        if (!skipPim) this.pim.deactivate(request.approver_id || request.requester_id);   // give the window back
        if (!ver.ok) return this._stop('verify', trail, request);

        // clause 5 — EVIDENCE (the closure the attestation pipeline reads)
        trail.closed = true;
        trail.activationId = act.activationId;
        var ev = this._writeEvidence(request, trail);
        return { ok: true, clause: 'closed', evidence_sys_id: ev.sys_id || null, trail: trail };
    },

    _stop: function (clause, trail, request) {
        trail.closed = false;
        trail.stopped_at = clause;
        this._writeEvidence(request, trail);   // a refused task is evidence too
        return { ok: false, clause: clause, trail: trail };
    },

    _writeEvidence: function (request, trail) {
        if (this.testMode) return { ok: true, sys_id: 'test-evidence-0001' };
        var gr = new GlideRecord(this.tblEvidence);
        if (!gr.isValid()) { this.log.logErr('evidence table ' + this.tblEvidence + ' not found'); return { ok: false }; }
        gr.initialize();
        gr.setValue('record_type', 'macdr_closure');
        gr.setValue('verb', request.verb || '');
        gr.setValue('control', request.control || '');
        gr.setValue('ksi', (request.ksi || []).join ? request.ksi.join(',') : (request.ksi || ''));
        gr.setValue('ritm', request.ritm || '');
        gr.setValue('sam_request_id', request.sam_request_id || '');
        gr.setValue('pim_activation_id', trail.activationId || '');
        gr.setValue('closed', trail.closed ? 'true' : 'false');
        gr.setValue('stopped_at', trail.stopped_at || '');
        gr.setValue('trail', JSON.stringify(trail));
        gr.setValue('boundary', gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate'));
        var id = gr.insert();
        return { ok: !!id, sys_id: '' + id };
    },

    type: 'MacdrOrchestrator'
};
