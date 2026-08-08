// Script Include: SamCorrelationClient  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// The ServiceNow side of the SAM (Systems Access Management / SailPoint IGA)
// integration for the Day-2 Operations app (Vol IX). SAM is the authoritative
// ORIGIN of higher-tier access decisions (MACD-R clause 2, Vol 0 Book 00): it
// decides and approves, then PUSHES a request into ServiceNow. This client does
// NOT actuate SAM and does NOT actuate the estate — it correlates the SAM request
// to the ServiceNow RITM and to the Entra object, reads SAM status for closure,
// and writes ServiceNow's own lineage record (AU-2). SAM stays the decision plane;
// ServiceNow stays the workflow plane; neither becomes the other.
//
// PRIMARY: SailPoint IdentityIQ (on-prem). IIQ's ServiceNow Service Desk
// Integration Module (SDIM) raises the RITM (IIQ-push). Because IIQ is on-prem
// INSIDE the boundary, the callback path is intra-boundary and still routes
// through the MID for a single, audited egress discipline. SCIM 2.0
// (<base>/scim/v2) + IIQ REST (<base>/rest) carry status and the IdentityRequest.
// SECONDARY: Identity Security Cloud (SaaS) over the same contract; selected by
// x_fed_day2_ops.sam_flavor = 'isc'. The client branches on sam_flavor.
//
// Config: see KIT-VARIABLES-REFERENCE.md, section 4. The `sam` alias holds the
// endpoint + credential; sam_flavor selects the dialect; sam_source_id ties the
// request to the Entra source.
//
// STARTER SKELETON — validate the SCIM/REST paths against your IIQ (or ISC) build
// before production. test_mode returns deterministic canned values so the ATF
// suites drive the Flow with no live SAM. Never enable test_mode in production.
// -----------------------------------------------------------------------------
var SamCorrelationClient = Class.create();
SamCorrelationClient.prototype = {

    initialize: function () {
        this.flavor = gs.getProperty('x_fed_day2_ops.sam_flavor', 'identityiq');
        this.baseUrl = gs.getProperty('x_fed_day2_ops.sam_base_url', '');
        this.sourceId = gs.getProperty('x_fed_day2_ops.sam_source_id', '');
        this.midServer = gs.getProperty('x_fed_day2_ops.mid_server', '');
        this.boundary = gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate');
        this.tblIntegration = gs.getProperty('x_fed_day2_ops.tbl_integration', 'x_fed_day2_ops_integration');
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.SamCorrelationClient] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // Read the SAM-side status of an access request, for closure. FAIL CLOSED: a
    // failed/unparseable read is inconclusive, never "approved". The dialect
    // (IIQ IdentityRequest vs ISC access-request) is selected by sam_flavor.
    getRequestStatus: function (samRequestId) {
        if (this.testMode)
            return { ok: true, id: samRequestId, status: 'approved', executionStatus: 'Completed' };
        if (!samRequestId)
            return { ok: false, reason: 'no SAM request id — cannot correlate' };

        var path = (this.flavor === 'isc')
            ? '/v3/access-request-status?requested-for=' + encodeURIComponent(samRequestId)
            : '/scim/v2/LaunchedWorkflows/' + encodeURIComponent(samRequestId);   // IIQ (primary)
        var r = this._sam('GET', path, null);
        if (!r.ok) return { ok: false, status: r.status, reason: 'SAM status read failed — inconclusive, not approved' };
        var parsed;
        try { parsed = JSON.parse(r.body) || {}; }
        catch (e) { return { ok: false, reason: 'SAM status unparseable — inconclusive' }; }
        return { ok: true, id: samRequestId, raw: parsed,
                 status: parsed.status || parsed.executionStatus || 'unknown' };
    },

    // Write ServiceNow's OWN lineage record binding the SAM request, the RITM and
    // the Entra object end to end (AU-2). This is bookkeeping in the workflow
    // plane — it writes a ServiceNow record, never the estate and never SAM.
    // The RITM<->IdentityRequest key is what makes the closure attestable back to
    // the access DECISION, not just the action.
    //
    // ritmNumber may be null: the P0-7 remediation writes lineage BEFORE the
    // RITM exists (fail-closed ordering — no executable request without an
    // audit trail), then binds the RITM once created via attachRitmToLineage.
    // Only samRequestId is required up front. verification (optional) carries
    // the pull-verify/JWS result that authorized this lineage record, so the
    // evidence reflects what was actually confirmed, not just what was pushed.
    recordLineage: function (ritmNumber, samRequestId, entraObjectId, verification) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-lineage-0001', ritm: ritmNumber, sam_request: samRequestId };
        if (!samRequestId)
            return { ok: false, reason: 'lineage requires the SAM request id (AU-2)' };
        var gr = new GlideRecord(this.tblIntegration);
        if (!gr.isValid()) return { ok: false, reason: 'integration table ' + this.tblIntegration + ' not found' };
        gr.initialize();
        gr.setValue('record_type', 'sam_lineage');
        gr.setValue('ritm', ritmNumber || '');
        gr.setValue('sam_flavor', this.flavor);
        gr.setValue('sam_request_id', samRequestId);
        gr.setValue('sam_source_id', this.sourceId);
        gr.setValue('entra_object_id', entraObjectId || '');
        gr.setValue('boundary', this.boundary);
        if (verification) {
            gr.setValue('verified_by', verification.verified_by || '');
            gr.setValue('verified_at', verification.verified_at || '');
            gr.setValue('verified_authority', verification.verified_authority || '');
            gr.setValue('verified_status', verification.verified_status || '');
            gr.setValue('verified_item', verification.verified_item || '');
        }
        var id = gr.insert();
        return { ok: !!id, sys_id: '' + id, ritm: ritmNumber || '', sam_request: samRequestId };
    },

    // Bind a lineage record written before the RITM existed (recordLineage
    // with ritmNumber=null) to the RITM now that it's been created. Plain
    // ServiceNow bookkeeping — no IIQ/ISC specifics required.
    attachRitmToLineage: function (lineageSysId, ritmNumber, ritmSysId) {
        if (!lineageSysId || !ritmNumber || !ritmSysId)
            return { ok: false, reason: 'attachRitmToLineage requires lineageSysId, ritmNumber, and ritmSysId' };
        if (this.testMode)
            return { ok: true, sys_id: lineageSysId, ritm: ritmNumber };
        var gr = new GlideRecord(this.tblIntegration);
        if (!gr.get(lineageSysId))
            return { ok: false, reason: 'lineage record ' + lineageSysId + ' not found' };
        gr.setValue('ritm', ritmNumber);
        gr.setValue('ritm_sys_id', ritmSysId);
        var updated = gr.update();
        return { ok: !!updated, sys_id: lineageSysId, ritm: ritmNumber };
    },

    // -------------------------------------------------------------------------
    // NOT IMPLEMENTED (live mode) — deliberate fail-closed stub, not a
    // placeholder someone forgot. A real implementation needs this tenant's
    // actual IIQ (or ISC) REST/SCIM contract — endpoint shape, auth, response
    // parsing — which cannot be filled in generically. With this stub in
    // place, sam_inbound_ritm.js's verifyWithSam() always refuses
    // ('verification_unavailable') whenever x_fed_day2_ops.iiq_verify_endpoint
    // is configured, which is the same safe, inert state as leaving it
    // unconfigured — a real pull-verify integration, not a functional one.
    // Replace the live-mode branch below with a MID-routed call to the
    // tenant's IIQ IdentityRequest / ISC access-request API before relying on
    // it in production.
    //
    // test_mode: returns a deterministic canned "approved" IdentityRequest so
    // the SAM ATF suite (atf/atf-sam-*.xml) can drive the full inbound push
    // — contract validation, pull-verify, lineage, RITM creation — with no
    // live IIQ/ISC, matching this class's header promise. test_mode is
    // refused outside a declared non-prod instance (P0-5, see
    // atf-negative-testmode-environment-binding.xml), so this canned path
    // can never fire in production.
    // -------------------------------------------------------------------------
    fetchIdentityRequest: function (samRequestId) {
        if (this.testMode) {
            if (!samRequestId) return { ok: false, reason: 'no SAM request id — cannot correlate' };
            return { ok: true, data: {
                id: samRequestId,
                executionStatus: 'Completed',
                status: 'approved',
                requested_for: 'test-user-0001',
                access_item: 'ATF-Test-Role',
                approval_authority: 'app-owner',
                risk_tier: '2',
                justification: 'ATF canned fixture — test_mode only'
            } };
        }
        return { ok: false, reason: 'fetchIdentityRequest is not implemented for this tenant — wire it to your ' +
                 'IIQ/ISC REST or SCIM API before relying on x_fed_day2_ops.iiq_verify_endpoint (fail closed)' };
    },

    // -------------------------------------------------------------------------
    // NOT IMPLEMENTED (live mode) — same fail-closed rationale as
    // fetchIdentityRequest. A real implementation MUST validate: the
    // signature against publicKey, the issuer, the expiry, AND that the
    // claims bind to the asserted sam_request_id — a validly-signed assertion
    // that covers a DIFFERENT request is the obvious bypass a shallow
    // "signature checks out" implementation would miss (see
    // sam_inbound_ritm.js's subject-mismatch check for the equivalent guard
    // on the pull-verify path).
    //
    // test_mode: returns a canned claim set bound to the JWS string passed in
    // (not a real signature check) so the ATF suite can exercise the JWS
    // branch of verifyWithSam() with no live signer. Same P0-5 guard as
    // fetchIdentityRequest keeps this out of production.
    // -------------------------------------------------------------------------
    verifyJws: function (jws, publicKey) {
        if (this.testMode) {
            if (!jws) return { ok: false, reason: 'empty jws' };
            return { ok: true, claims: {
                sam_request_id: jws,
                approval_authority: 'app-owner',
                access_item: 'ATF-Test-Role',
                risk_tier: '2',
                justification: 'ATF canned fixture — test_mode only',
                status: 'approved'
            } };
        }
        return { ok: false, reason: 'verifyJws is not implemented for this tenant — wire real JWS signature/issuer/' +
                 'expiry/subject-binding verification before relying on x_fed_day2_ops.sam_jws_public_key (fail closed)' };
    },

    // Validate an inbound IIQ-pushed payload (used by the scripted REST endpoint).
    // FAIL CLOSED: a push missing the correlation keys is refused — an
    // un-correlatable request cannot be attested back to its decision.
    validateInboundPush: function (payload) {
        if (!payload) return { ok: false, reason: 'empty push payload' };
        var missing = [];
        ['sam_request_id', 'access_item', 'requested_for', 'approval_authority'].forEach(function (k) {
            if (!payload[k] || !('' + payload[k]).trim()) missing.push(k);
        });
        if (missing.length)
            return { ok: false, reason: 'SAM push missing required correlation fields: ' + missing.join(', ') };
        return { ok: true };
    },

    // --- Internal: MID-routed SAM call via the sam credential alias. -----------
    _sam: function (method, path, body) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_fed_day2_ops.sam', method);
            rm.setEndpoint(this.baseUrl + path);
            if (this.midServer) rm.setMIDServer(this.midServer);   // single audited egress discipline
            if (body !== null && body !== undefined) rm.setRequestBody(JSON.stringify(body));
            var resp = rm.execute();
            var code = resp.getStatusCode();
            return { ok: code >= 200 && code < 300, status: code, body: resp.getBody() };
        } catch (e) {
            this.log.logErr('_sam ' + method + ' ' + path + ' failed: ' + ('' + e).replace(/[\r\n]+/g, ' ').slice(0, 500));
            return { ok: false, error: '' + e };
        }
    },

    type: 'SamCorrelationClient'
};
