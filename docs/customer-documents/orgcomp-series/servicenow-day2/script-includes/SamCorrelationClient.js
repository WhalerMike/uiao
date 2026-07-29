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
    recordLineage: function (ritmNumber, samRequestId, entraObjectId) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-lineage-0001', ritm: ritmNumber, sam_request: samRequestId };
        if (!ritmNumber || !samRequestId)
            return { ok: false, reason: 'lineage requires both the RITM number and the SAM request id (AU-2)' };
        var gr = new GlideRecord(this.tblIntegration);
        if (!gr.isValid()) return { ok: false, reason: 'integration table ' + this.tblIntegration + ' not found' };
        gr.initialize();
        gr.setValue('record_type', 'sam_lineage');
        gr.setValue('ritm', ritmNumber);
        gr.setValue('sam_flavor', this.flavor);
        gr.setValue('sam_request_id', samRequestId);
        gr.setValue('sam_source_id', this.sourceId);
        gr.setValue('entra_object_id', entraObjectId || '');
        gr.setValue('boundary', this.boundary);
        var id = gr.insert();
        return { ok: !!id, sys_id: '' + id, ritm: ritmNumber, sam_request: samRequestId };
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
