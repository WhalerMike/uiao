// Script Include: MacdrOrchestrator  (application scope: x_fed_day2_ops)
// =============================================================================
// REMEDIATED BUILD.
//
//   P0-6  CLAUSE 1 IS NOW ENFORCED. run() previously began at clause 2 and
//         wrote request.ritm / request.sam_request_id into the evidence record
//         without ever validating them ("checked upstream" — there was no
//         upstream enforcement point). Any caller with the scoped role could
//         run the whole chain with no origin at all, which made the SSOT
//         guarantee the one clause with no enforcement. _clauseOrigin() now
//         resolves the origin record and refuses when it cannot.
//
//   NEW-1 THE LEG IS DERIVED, NOT ACCEPTED. skipPim keyed on
//         request.actuation_leg — a caller-supplied field — so anyone could set
//         'ad' on a Graph request and skip PIM elevation entirely. The leg is
//         now computed here from hybrid_mode + a LIVE Graph read of
//         onPremisesSyncEnabled (never a caller-supplied request.entra_user
//         object — that would just move the same bypass one field over) and
//         OVERWRITES whatever the caller sent.
//
//   SER-5 EVIDENCE IS TAMPER-EVIDENT. Records are hash-chained (each carries
//         the SHA-256 of its canonical content plus its predecessor's hash), so
//         an edited or deleted row is detectable by verifyChain(). Previously
//         the evidence an ATO package depends on was an ordinary, freely
//         editable table row — AU-9 / AU-10 appeared in no control map.
//
//   P0-5  test_mode routed through Day2Env; refuses outright on a production
//         instance carrying the property.
// =============================================================================
var MacdrOrchestrator = Class.create();
// Keys a CALLER may not supply on a request object. Same doctrine as
// AdHybridClient.RESERVED (P0-2): a field that changes control behaviour is
// refused if it arrives from the caller, rather than trusted because a comment
// says no real form sets it.
//
// _forceWritebackFailure is an ATF hook that suppresses the SAM closure
// write-back. It is inert in production today only because
// SamCorrelationClient.writeClosureSummary's live branch is an unimplemented
// stub -- the moment a tenant wires up a real write-back, an unguarded
// caller-supplied field becomes a suppression switch on closure evidence.
// Compared lower-case, like AdHybridClient's list.
MacdrOrchestrator.RESERVED = ['_forcewritebackfailure'];

MacdrOrchestrator.prototype = {

    initialize: function () {
        this.gate = new x_fed_day2_ops.EntraHelpdeskGate();
        this.pim = new x_fed_day2_ops.PimActivationClient();
        this.sam = new x_fed_day2_ops.SamCorrelationClient();
        this.env = new x_fed_day2_ops.Day2Env();
        this.tblEvidence = gs.getProperty('x_fed_day2_ops.tbl_evidence', 'x_fed_day2_ops_evidence');
        this.tblIntegration = gs.getProperty('x_fed_day2_ops.tbl_integration', 'x_fed_day2_ops_integration');
        this.testMode = this.env.isTestMode();
        this.log = {
            err: function (m) { gs.error('[x_fed_day2_ops.MacdrOrchestrator] ' + Day2Env.scrub(m)); }
        };
    },

    // request : { requester_id, approver_id, privileged, expiry, control, ksi,
    //             verb, ritm, sam_request_id, entra_user, ... }
    // actuate : function() -> { ok, ... }
    // verifyArgs : { action, target }
    // Reserved keys present on a caller-supplied request object, if any.
    _reservedKeysIn: function (request) {
        var found = [];
        for (var k in request) {
            if (!request.hasOwnProperty(k)) continue;
            if (MacdrOrchestrator.RESERVED.indexOf(('' + k).toLowerCase()) !== -1) found.push(k);
        }
        return found;
    },

    run: function (request, actuate, verifyArgs) {
        request = request || {};
        verifyArgs = verifyArgs || {};
        var trail = { verb: request.verb, control: request.control, ksi: request.ksi };

        var guard = this.env.guard();
        if (!guard.ok) { trail.environment = guard; return this._stop('environment', trail, request); }

        // Reserved keys are an ATF affordance and must never arrive from a real
        // caller. Refused outside test_mode rather than everywhere, because the
        // suite legitimately sets them (atf-sam-closure-writeback.xml) -- so the
        // hook keeps working in the harness while the production path stops
        // depending on a comment. Folded into the environment clause: this is a
        // precondition failure, not a new stop reason for the docs to enumerate.
        if (!this.testMode) {
            var reserved = this._reservedKeysIn(request);
            if (reserved.length) {
                trail.environment = { ok: false,
                    reason: 'reserved key supplied by caller: ' + reserved.join(', ') };
                return this._stop('environment', trail, request);
            }
        }

        // ---- clause 1 — ORIGIN (fail closed) --------------------------------
        var origin = this._clauseOrigin(request);
        trail.origin = origin;
        if (!origin.ok) return this._stop('origin', trail, request);

        // ---- server-derived routing (NEW-1) ---------------------------------
        var leg = this._deriveLeg(request);
        trail.routing = leg;
        if (!leg.ok) return this._stop('route', trail, request);
        request.actuation_leg = leg.leg;          // authoritative; caller value discarded
        var skipPim = (leg.leg === 'ad');

        // ---- clause 2 — AUTHORIZE (fail closed) -----------------------------
        var pre = this.gate.preflight(request);
        trail.authorize = pre;
        if (!pre.ok) return this._stop('authorize', trail, request);

        // ---- clause 3 — ELEVATE ---------------------------------------------
        // Skipped for the AD leg: the write executes under the MID Server's
        // service identity, so activating PIM for a human is not the operative
        // authorization and would only issue a spurious privileged window.
        // Documented gap (no workload-identity PIM integration exists here), and
        // it is recorded in the trail rather than silently skipped.
        var act;
        if (skipPim) {
            act = { ok: true, activationId: null, skipped: true,
                    reason: 'AD-leg actuation runs under the MID service identity; PIM activation of a human is not the operative authorization for this leg (documented gap)' };
            trail.elevate = act;
        } else {
            act = this.pim.activate(request.approver_id || request.requester_id,
                                    request.justification || ('MACD-R ' + request.verb));
            trail.elevate = { ok: act.ok, activationId: act.activationId, reason: act.reason };
            if (!act.ok) return this._stop('elevate', trail, request);
        }

        // ---- clause 4 — ACTUATE then VERIFY ---------------------------------
        var result;
        try { result = (typeof actuate === 'function') ? actuate() : { ok: false, reason: 'no actuation supplied' }; }
        catch (e) { result = { ok: false, error: Day2Env.scrub(e) }; }
        trail.actuate = { ok: !!(result && result.ok), dispatched: !!(result && result.dispatched),
                          ecc_sys_id: result ? result.ecc_sys_id : null };
        if (!result || !result.ok) {
            if (!skipPim) this.pim.deactivate(request.approver_id || request.requester_id);
            return this._stop('actuate', trail, request);
        }

        var ver = this.gate.verify(verifyArgs.action, verifyArgs.target, leg.leg);
        trail.verify = ver;
        if (!skipPim) this.pim.deactivate(request.approver_id || request.requester_id);
        if (!ver.ok) return this._stop('verify', trail, request);

        // ---- clause 5 — EVIDENCE --------------------------------------------
        trail.closed = true;
        trail.activationId = act.activationId;
        var ev = this._writeEvidence(request, trail);

        // ---- optional: SAM closure write-back --------------------------------
        // Best effort and NEVER allowed to affect the result already decided
        // above (SEE _writeSamClosureSummary) — SAM is the decision origin,
        // not a dependency of ServiceNow's own closure.
        if (origin.origin === 'sam' && gs.getProperty('x_fed_day2_ops.sam_closure_writeback', 'false') === 'true') {
            this._writeSamClosureSummary(origin.sam_request_id, request, trail, ev);
        }

        return { ok: true, clause: 'closed', evidence_sys_id: ev.sys_id || null,
                 evidence_hash: ev.hash || null, trail: trail };
    },

    // -------------------------------------------------------------------------
    // Tier-1 item 4 (closure write-back enrichment). Pushes a structured
    // status/evidence summary back onto the SAM IdentityRequest — richer than
    // the RITM-number write the SDIM already performs onto
    // IdentityRequest.externalTicketId (see KIT-USAGE-SAM-INTEGRATION.md
    // "Closure back to SAM"). Optional (x_fed_day2_ops.sam_closure_writeback,
    // default false) and fail-OPEN toward closure: the try/catch here exists
    // specifically so an unreachable or slow SAM at closure time cannot turn
    // an already-decided closure into a stuck or failed request — closure was
    // already recorded by _writeEvidence above by the time this runs.
    // -------------------------------------------------------------------------
    _writeSamClosureSummary: function (samRequestId, request, trail, ev) {
        try {
            var summary = {
                closed: true,
                verb: request.verb || '',
                control: request.control || '',
                ksi: request.ksi || '',
                ritm: request.ritm || '',
                actuation_leg: request.actuation_leg || '',
                boundary: gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate'),
                evidence_sys_id: ev.sys_id || '',
                evidence_hash: ev.hash || '',
                closed_at: new GlideDateTime().getValue(),
                // ATF-only hook — see SamCorrelationClient.writeClosureSummary.
                // Gated on THIS class's own test_mode state, not on the callee's
                // test_mode branch: run() already refuses the key from a caller
                // outside test_mode (see RESERVED), and this makes the forward
                // conditional too, so the production path cannot carry it even
                // if that check is ever bypassed.
                _forceWritebackFailure: this.testMode && !!request._forceWritebackFailure
            };
            var wrote = this.sam.writeClosureSummary(samRequestId, summary);
            if (!wrote.ok) {
                this.log.err('SAM closure write-back failed for ' + Day2Env.scrub(samRequestId) +
                              ' (closure already recorded and unaffected): ' + wrote.reason);
            }
        } catch (e) {
            this.log.err('SAM closure write-back threw for ' + Day2Env.scrub(samRequestId) +
                          ' (closure already recorded and unaffected): ' + e);
        }
    },

    // -------------------------------------------------------------------------
    // Clause 1. A governed request must resolve to a record that says where it
    // came from. Three accepted origins; anything else is refused.
    // -------------------------------------------------------------------------
    _clauseOrigin: function (request) {
        // (a) SAM-originated: the integration/lineage record must already exist.
        if (request.sam_request_id) {
            var integ = new GlideRecord(this.tblIntegration);
            if (integ.get('sam_request_id', request.sam_request_id)) {
                return { ok: true, origin: 'sam', sam_request_id: request.sam_request_id,
                         lineage_sys_id: integ.getUniqueValue() };
            }
            return { ok: false, origin: 'sam',
                     reason: 'sam_request_id does not resolve to a lineage record — origin unproven (fail closed)' };
        }

        // (b) Catalog-originated: the RITM must exist and be a real request item.
        if (request.ritm) {
            var ritm = new GlideRecord('sc_req_item');
            if (ritm.get('number', request.ritm) || ritm.get(request.ritm)) {
                return { ok: true, origin: 'catalog', ritm: ritm.getValue('number'),
                         ritm_sys_id: ritm.getUniqueValue() };
            }
            return { ok: false, origin: 'catalog',
                     reason: 'ritm does not resolve to an sc_req_item — origin unproven (fail closed)' };
        }

        // (c) Break-glass: permitted, but only explicitly, only with a named
        // approver, and it is loud in the evidence record. An unlabelled
        // origin-less run is exactly what clause 1 exists to stop.
        if (request.breakglass === true || request.breakglass === 'true') {
            if (!request.breakglass_approver_id || !request.breakglass_justification) {
                return { ok: false, origin: 'breakglass',
                         reason: 'break-glass origin requires breakglass_approver_id and breakglass_justification' };
            }
            gs.warn('[x_fed_day2_ops.MacdrOrchestrator] BREAK-GLASS origin used by ' +
                    Day2Env.scrub(request.requester_id) + ' approved by ' +
                    Day2Env.scrub(request.breakglass_approver_id));
            return { ok: true, origin: 'breakglass',
                     approver: request.breakglass_approver_id,
                     justification: Day2Env.scrub(request.breakglass_justification) };
        }

        return { ok: false, origin: null,
                 reason: 'no origin: request carries neither sam_request_id, ritm, nor a declared break-glass (MACD-R clause 1, fail closed)' };
    },

    // -------------------------------------------------------------------------
    // Server-derived routing. The caller does not get a vote.
    //
    // SECURITY: an earlier revision trusted request.entra_user.onPremisesSyncEnabled
    // as supplied by the caller. That field decides whether PIM elevation is
    // skipped (skipPim in run()) -- a caller-suppliable security classification
    // is a control-bypass primitive, not a routing hint, no different in kind
    // from the original request.actuation_leg bug this method exists to fix.
    // The classification is now fetched live from Graph, keyed only on the
    // target's identifier (which the caller has to supply regardless, for the
    // actuation itself to mean anything) -- never trusted pre-fetched.
    // -------------------------------------------------------------------------
    _deriveLeg: function (request) {
        var hybrid = gs.getProperty('x_fed_day2_ops.hybrid_mode', 'false') === 'true';
        if (!hybrid) return { ok: true, leg: 'graph', basis: 'hybrid_mode=false' };

        // Cloud-native verbs never route to AD regardless of hybrid_mode.
        var cloudOnly = ['resetMfaMethod', 'assignLicense', 'inviteGuest', 'adminConsent', 'azureRbac'];
        if (cloudOnly.indexOf(request.verb) !== -1)
            return { ok: true, leg: 'graph', basis: 'verb is cloud-native by nature' };

        // test_mode fixture: Day2Env.guard() already confines test_mode to a
        // declared non-prod instance, so the caller-forgery concern below
        // doesn't apply here -- ATF can supply request.entra_user directly
        // instead of standing up a live Graph call. The live path (below)
        // NEVER reads request.entra_user; only entra_user_id, to fetch it.
        if (this.testMode) {
            var fixture = request.entra_user;
            if (!fixture || typeof fixture.onPremisesSyncEnabled !== 'boolean') {
                return { ok: false,
                         reason: 'test_mode: request.entra_user fixture missing or malformed — object unclassified, refusing to actuate (fail closed)' };
            }
            var masteredFixture = new x_fed_day2_ops.AdHybridClient().isAdMastered(fixture);
            return { ok: true, leg: masteredFixture ? 'ad' : 'graph',
                     basis: 'test_mode fixture: onPremisesSyncEnabled=' + fixture.onPremisesSyncEnabled };
        }

        var targetId = request.entra_user_id || (request.entra_user && request.entra_user.id);
        if (!targetId) {
            return { ok: false,
                     reason: 'no target identifier to classify — object unclassified, refusing to actuate (fail closed)' };
        }
        var client = new x_fed_day2_ops.EntraHelpdeskClient();
        var r = client._graph('GET', '/users/' + targetId + '?$select=onPremisesSyncEnabled', null);
        if (!r.ok) {
            return { ok: false,
                     reason: 'classifying Entra read failed (status ' + r.status + ') — object unclassified, refusing to actuate (fail closed)' };
        }
        var body;
        try { body = JSON.parse(r.body) || {}; }
        catch (e) {
            return { ok: false, reason: 'classifying Entra read unparseable — refusing to actuate (fail closed)' };
        }
        if (typeof body.onPremisesSyncEnabled !== 'boolean') {
            return { ok: false,
                     reason: 'classifying Entra read missing onPremisesSyncEnabled — object unclassified, refusing to actuate (fail closed)' };
        }
        var mastered = new x_fed_day2_ops.AdHybridClient().isAdMastered(body);
        return { ok: true, leg: mastered ? 'ad' : 'graph',
                 basis: 'onPremisesSyncEnabled=' + body.onPremisesSyncEnabled + ' (server-verified via Graph, not caller-supplied)' };
    },

    // -------------------------------------------------------------------------
    // SER-5. Hash-chained evidence.
    // -------------------------------------------------------------------------
    _writeEvidence: function (request, trail) {
        try {
            var stamp = this.env.evidenceStamp();
            var body = {
                request: {
                    verb: request.verb, control: request.control, ksi: request.ksi,
                    requester_id: request.requester_id, approver_id: request.approver_id,
                    ritm: request.ritm || '', sam_request_id: request.sam_request_id || '',
                    actuation_leg: request.actuation_leg
                },
                trail: trail,
                stamp: stamp
            };
            var canonical = this._canonical(body);
            var prev = this._lastHash();
            var hash = this._sha256(prev + '|' + canonical);

            var gr = new GlideRecord(this.tblEvidence);
            gr.initialize();
            gr.setValue('verb', request.verb || '');
            gr.setValue('control', request.control || '');
            gr.setValue('ksi', request.ksi || '');
            gr.setValue('ritm', request.ritm || '');
            gr.setValue('sam_request_id', request.sam_request_id || '');
            gr.setValue('origin', trail.origin ? trail.origin.origin : '');
            gr.setValue('actuation_leg', request.actuation_leg || '');
            gr.setValue('closed', trail.closed ? 'true' : 'false');
            gr.setValue('stopped_at', trail.stopped_at || '');
            gr.setValue('test_mode', stamp.test_mode ? 'true' : 'false');
            gr.setValue('synthetic', stamp.synthetic ? 'true' : 'false');
            gr.setValue('payload', canonical);
            gr.setValue('prev_hash', prev);
            gr.setValue('hash', hash);
            var id = gr.insert();
            return { ok: !!id, sys_id: '' + id, hash: hash };
        } catch (e) {
            this.log.err('_writeEvidence failed: ' + e);
            return { ok: false };
        }
    },

    _lastHash: function () {
        var gr = new GlideRecord(this.tblEvidence);
        gr.orderByDesc('sys_created_on');
        gr.setLimit(1);
        gr.query();
        return gr.next() ? (gr.getValue('hash') || 'GENESIS') : 'GENESIS';
    },

    _sha256: function (s) {
        try { return new GlideDigest().getSHA256Base64(s); }
        catch (e) {
            // If GlideDigest is unavailable the chain must not silently degrade
            // to an unverifiable value — mark it so verifyChain() reports it.
            this.log.err('GlideDigest unavailable — evidence chain cannot be computed');
            return 'NOHASH';
        }
    },

    // Stable key ordering so the same content always hashes identically.
    _canonical: function (obj) {
        var self = this;
        if (obj === null || typeof obj !== 'object') return JSON.stringify(obj);
        if (obj instanceof Array) {
            var parts = [];
            for (var i = 0; i < obj.length; i++) parts.push(self._canonical(obj[i]));
            return '[' + parts.join(',') + ']';
        }
        var keys = [];
        for (var k in obj) { if (obj.hasOwnProperty(k)) keys.push(k); }
        keys.sort();
        var out = [];
        for (var j = 0; j < keys.length; j++) {
            out.push(JSON.stringify(keys[j]) + ':' + self._canonical(obj[keys[j]]));
        }
        return '{' + out.join(',') + '}';
    },

    // Run from a scheduled job / the attestation pipeline. Returns the first
    // break in the chain, which is where a row was edited, inserted or deleted.
    verifyChain: function (limit) {
        var gr = new GlideRecord(this.tblEvidence);
        gr.orderBy('sys_created_on');
        if (limit) gr.setLimit(limit);
        gr.query();
        var expectedPrev = 'GENESIS', checked = 0;
        while (gr.next()) {
            checked++;
            var storedPrev = gr.getValue('prev_hash') || '';
            var storedHash = gr.getValue('hash') || '';
            var payload = gr.getValue('payload') || '';
            if (storedPrev !== expectedPrev) {
                return { ok: false, checked: checked, broken_at: gr.getUniqueValue(),
                         reason: 'prev_hash does not match the preceding record — a row was inserted, deleted or reordered' };
            }
            if (this._sha256(storedPrev + '|' + payload) !== storedHash) {
                return { ok: false, checked: checked, broken_at: gr.getUniqueValue(),
                         reason: 'recomputed hash does not match stored hash — this record was edited after insert' };
            }
            expectedPrev = storedHash;
        }
        return { ok: true, checked: checked };
    },

    _stop: function (clause, trail, request) {
        trail.closed = false;
        trail.stopped_at = clause;
        var ev = this._writeEvidence(request, trail);
        return { ok: false, clause: clause, evidence_sys_id: ev.sys_id || null,
                 evidence_hash: ev.hash || null, trail: trail };
    },

    type: 'MacdrOrchestrator'
};
