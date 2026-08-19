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
        this.env = new x_fed_day2_ops.Day2Env();
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
    //
    // NO test_mode shortcut here (unlike fetchIdentityRequest/verifyJws/
    // getRequestStatus): this method's only effect is a LOCAL GlideRecord
    // write — there is no live SAM connectivity to fake, so faking it would
    // only defeat the ATF suite's ability to assert the lineage row actually
    // exists (atf-sam-happy-path.xml, atf-sam-idempotent-repush.xml). Rows
    // written under test_mode are stamped test_mode/synthetic so a monitoring
    // query (dailyOutcomeCounts / correlationReport below) can exclude them
    // the same way the evidence table already does (Day2Env.evidenceStamp).
    recordLineage: function (ritmNumber, samRequestId, entraObjectId, verification) {
        if (!samRequestId)
            return { ok: false, reason: 'lineage requires the SAM request id (AU-2)' };
        var gr = new GlideRecord(this.tblIntegration);
        if (!gr.isValid()) return { ok: false, reason: 'integration table ' + this.tblIntegration + ' not found' };
        var stamp = this.env.evidenceStamp();
        gr.initialize();
        gr.setValue('record_type', 'sam_lineage');
        gr.setValue('ritm', ritmNumber || '');
        gr.setValue('sam_flavor', this.flavor);
        gr.setValue('sam_request_id', samRequestId);
        gr.setValue('sam_source_id', this.sourceId);
        gr.setValue('entra_object_id', entraObjectId || '');
        gr.setValue('boundary', this.boundary);
        gr.setValue('test_mode', stamp.test_mode ? 'true' : 'false');
        gr.setValue('synthetic', stamp.synthetic ? 'true' : 'false');
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
    // ServiceNow bookkeeping — no IIQ/ISC specifics required, and — same
    // reasoning as recordLineage above — no test_mode shortcut, since this is
    // a local update with nothing external to fake.
    attachRitmToLineage: function (lineageSysId, ritmNumber, ritmSysId) {
        if (!lineageSysId || !ritmNumber || !ritmSysId)
            return { ok: false, reason: 'attachRitmToLineage requires lineageSysId, ritmNumber, and ritmSysId' };
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
    // fetchIdentityRequest. A real implementation MUST validate the signature
    // against publicKey, the issuer, and the expiry, and MUST return a claim
    // set that binds ALL THREE of:
    //
    //   1. sam_request_id — a validly-signed assertion covering a DIFFERENT
    //      request is the obvious bypass a shallow "signature checks out"
    //      implementation would miss.
    //   2. requested_for — the SUBJECT. Without it the endpoint has only the
    //      caller-supplied, unsigned body value, so a valid assertion for one
    //      person can be redirected to another. sam_inbound_ritm.js REFUSES a
    //      claim set with no requested_for (signature_subject_unbound); this is
    //      a hard requirement on your signer, not a nicety.
    //   3. status — the DECISION. A correctly-signed DENIAL is still a denial.
    //      The endpoint gates on it exactly as the pull-verify path does.
    //
    // Items 2 and 3 were absent from this contract until they were added
    // alongside the endpoint guards: the pull-verify branch checked subject and
    // decision while the JWS branch checked neither, so an implementer
    // following the old text would have built the permissive version.
    //
    // test_mode: returns a canned claim set bound to the JWS string passed in
    // (not a real signature check) so the ATF suite can exercise the JWS
    // branch of verifyWithSam() with no live signer. Same P0-5 guard as
    // fetchIdentityRequest keeps this out of production.
    // -------------------------------------------------------------------------
    verifyJws: function (jws, publicKey) {
        if (this.testMode) {
            if (!jws) return { ok: false, reason: 'empty jws' };
            // Mirrors fetchIdentityRequest's canned subject so both verification
            // paths are drivable from one fixture. requested_for is present
            // because the endpoint now REFUSES a claim set without it — a canned
            // set missing it would make every ATF JWS push fail closed.
            return { ok: true, claims: {
                sam_request_id: jws,
                requested_for: 'test-user-0001',
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

    // -------------------------------------------------------------------------
    // OPTIONAL closure write-back — richer than the RITM-number write the SDIM
    // itself performs onto IdentityRequest.externalTicketId (see
    // KIT-USAGE-SAM-INTEGRATION.md "Closure back to SAM"). Called by
    // MacdrOrchestrator.run() when a SAM-originated task reaches Closed
    // Complete, gated by x_fed_day2_ops.sam_closure_writeback (default false —
    // opt in).
    //
    // FAIL-OPEN TOWARD CLOSURE, ON PURPOSE: this is the one place in the SAM
    // surface where "fail closed" is the WRONG instinct. By the time this
    // runs, ServiceNow has already decided the task is closed — SAM is the
    // decision ORIGIN, not a dependency of ServiceNow's own closure. The
    // caller (MacdrOrchestrator._writeSamClosureSummary) wraps this in
    // try/catch and only logs a failure; it never reopens, blocks, or alters
    // the already-recorded result. An unreachable SAM at closure time must
    // never turn a real closure into a stuck or failed request.
    //
    // NOT IMPLEMENTED (live mode) — same rationale as fetchIdentityRequest/
    // verifyJws: the write shape (a SCIM PATCH, an IIQ REST comment endpoint,
    // a custom workflow variable) is tenant-specific and cannot be filled in
    // generically. test_mode returns a canned success so the ATF suite can
    // assert the call site invokes it with the right shape, with no live SAM.
    //
    // summary._forceWritebackFailure (test_mode only): an explicit, narrow
    // ATF hook that forces this call to fail even under test_mode, so
    // atf-sam-closure-writeback.xml can prove the fail-open contract above
    // without needing a live SAM outage to exercise it.
    // -------------------------------------------------------------------------
    writeClosureSummary: function (samRequestId, summary) {
        summary = summary || {};
        if (!samRequestId) return { ok: false, reason: 'no SAM request id — cannot write back' };
        if (this.testMode) {
            if (summary._forceWritebackFailure)
                return { ok: false, reason: 'forced failure for ATF (test_mode only)' };
            return { ok: true, method: 'test_mode', sam_request_id: samRequestId };
        }
        return { ok: false, reason: 'writeClosureSummary is not implemented for this tenant — wire it to your ' +
                 'IIQ/ISC write API before enabling x_fed_day2_ops.sam_closure_writeback (fail closed)' };
    },

    // -------------------------------------------------------------------------
    // OPERATIONAL TELEMETRY — one row per inbound push ATTEMPT, accepted or
    // refused, written by scripted-rest/sam_inbound_ritm.js at every deny()
    // and at every success. This is what dailyOutcomeCounts()/
    // sustainedFailureCheck() below read, and what an operator joins against
    // the sam_lineage rows and the evidence table (see correlationReport())
    // to answer "what happened to SAM request X" end to end. Only the OPAQUE
    // reason code is stored (the same code already returned to the caller in
    // the response body) — never the detailed log-only reason string, so
    // telemetry never becomes a second channel for the control-surface detail
    // sam_inbound_ritm.js's design goal #6 deliberately keeps out of
    // responses.
    //
    // Best effort: NEVER throws. A telemetry write failure must not turn a
    // real accept/refuse decision into a 500, or hide that decision from the
    // caller — the caller already has its real HTTP response before this
    // runs (see sam_inbound_ritm.js's deny()).
    // -------------------------------------------------------------------------
    recordPushOutcome: function (samRequestId, outcome, httpStatus, reasonCode) {
        try {
            var gr = new GlideRecord(this.tblIntegration);
            if (!gr.isValid()) return { ok: false, reason: 'integration table ' + this.tblIntegration + ' not found' };
            var stamp = this.env.evidenceStamp();
            gr.initialize();
            gr.setValue('record_type', 'sam_push_outcome');
            // sam_request_REF, not sam_request_id. The integration table's
            // sam_request_id is reserved for sam_lineage rows so that (a) the
            // inbound endpoint's idempotency lookup cannot match telemetry and
            // silently drop a retried request, and (b) the REQUIRED unique
            // index on sam_request_id is implementable at all — this method
            // writes a row per push ATTEMPT, so many telemetry rows share one
            // request id. See KIT-BUILD-SPEC.md §2b.
            gr.setValue('sam_request_ref', samRequestId || '');
            gr.setValue('sam_flavor', this.flavor);
            gr.setValue('sam_source_id', this.sourceId);
            gr.setValue('boundary', this.boundary);
            gr.setValue('state', outcome === 'accepted' ? 'accepted' : 'refused');
            // The canonical reason code and status get their OWN columns. They
            // used to be packed into business_need as
            // 'http_status=<n> reason=<code>' and recovered by /reason=(\S+)/,
            // which broke on any code containing whitespace -- note that
            // Day2Env.scrub REPLACES [\r\n\t] WITH A SPACE, so it can create
            // the very separator that truncates the match, bucketing a real
            // code as a wrong one or as 'unknown'. A governance table should
            // not require a regex to read its own key field.
            gr.setValue('reason_code', Day2Env.scrub(reasonCode || 'unknown'));
            gr.setValue('http_status', httpStatus || 0);
            // Human-readable prose only; no longer parsed by anything.
            gr.setValue('business_need', 'http_status=' + httpStatus + ' reason=' + Day2Env.scrub(reasonCode || ''));
            gr.setValue('test_mode', stamp.test_mode ? 'true' : 'false');
            gr.setValue('synthetic', stamp.synthetic ? 'true' : 'false');
            var id = gr.insert();
            return { ok: !!id, sys_id: '' + id };
        } catch (e) {
            this.log.logErr('recordPushOutcome failed: ' + e);
            return { ok: false };
        }
    },

    // Daily/periodic accepted-vs-refused counts for the inbound endpoint —
    // "Monitoring the inbound endpoint" in KIT-USAGE-SAM-INTEGRATION.md.
    // Excludes rows KNOWN to be synthetic (synthetic != 'true') so a sub-prod
    // ATF run never shows up as production traffic. Deliberately not
    // synthetic == 'false': that form requires proof of non-syntheticness and
    // drops every row where the field is unpopulated — rows predating the
    // column, rows from another writer, rows a future refactor forgets to
    // stamp. An alerting predicate that under-reports is worse than none: it
    // shows a green board during an outage. Fail toward counting, not silence.
    // Returns { ok, sinceDays, accepted, refused, refusedByReason: {code: count} }.
    dailyOutcomeCounts: function (sinceDays) {
        sinceDays = sinceDays || 1;
        var since = new GlideDateTime();
        since.addDaysUTC(-1 * sinceDays);
        // .getValue() -- pass the STRING, never the GlideDateTime object. An
        // object here may or may not coerce; if it does not, the window filter
        // silently matches the whole table and the alert numbers are wrong
        // with no error raised.
        var sinceStr = since.getValue();

        var counts = { accepted: 0, refused: 0, refusedByReason: {} };

        // GlideAggregate, not a row walk. This table takes one row per inbound
        // push ATTEMPT and is the highest-volume table in the app; the previous
        // implementation iterated every row in the window with no setLimit,
        // from a scheduled job.
        var byState = new GlideAggregate(this.tblIntegration);
        byState.addQuery('record_type', 'sam_push_outcome');
        byState.addQuery('synthetic', '!=', 'true');
        byState.addQuery('sys_created_on', '>=', sinceStr);
        byState.addAggregate('COUNT');
        byState.groupBy('state');
        byState.query();
        while (byState.next()) {
            var n = parseInt(byState.getAggregate('COUNT'), 10) || 0;
            if (byState.getValue('state') === 'accepted') counts.accepted += n;
            else counts.refused += n;
        }

        // Grouping on reason_code replaces the business_need regex outright.
        var byReason = new GlideAggregate(this.tblIntegration);
        byReason.addQuery('record_type', 'sam_push_outcome');
        byReason.addQuery('synthetic', '!=', 'true');
        byReason.addQuery('state', 'refused');
        byReason.addQuery('sys_created_on', '>=', sinceStr);
        byReason.addAggregate('COUNT');
        byReason.groupBy('reason_code');
        byReason.query();
        while (byReason.next()) {
            var code = byReason.getValue('reason_code') || 'unknown';
            counts.refusedByReason[code] = parseInt(byReason.getAggregate('COUNT'), 10) || 0;
        }

        return { ok: true, sinceDays: sinceDays, accepted: counts.accepted, refused: counts.refused,
                 refusedByReason: counts.refusedByReason };
    },

    // Alert predicate for a scheduled job: has the endpoint refused at least
    // `threshold` pushes in the trailing `windowMinutes`? A sustained run of
    // refusals — not one-off caller errors — usually means a SAM-side outage
    // (pull-verify unreachable), a rotated/expired credential, or an SDIM
    // field-map drift, all of which are worth paging on rather than
    // discovering the next time someone reads the system log.
    sustainedFailureCheck: function (windowMinutes, threshold) {
        windowMinutes = windowMinutes || 15;
        threshold = threshold || 5;
        var since = new GlideDateTime();
        since.addSeconds(-60 * windowMinutes);

        // See dailyOutcomeCounts for why this is a string, an aggregate, and
        // a != 'true' test rather than a == 'false' one.
        var ga = new GlideAggregate(this.tblIntegration);
        ga.addQuery('record_type', 'sam_push_outcome');
        ga.addQuery('state', 'refused');
        ga.addQuery('synthetic', '!=', 'true');
        ga.addQuery('sys_created_on', '>=', since.getValue());
        ga.addAggregate('COUNT');
        ga.query();
        var refused = ga.next() ? (parseInt(ga.getAggregate('COUNT'), 10) || 0) : 0;
        return { ok: true, windowMinutes: windowMinutes, threshold: threshold, refused: refused,
                 alert: refused >= threshold };
    },

    // Joins a SAM request id across the lineage row and the evidence table for
    // an operator/report: "what happened to SAM request X end to end" —
    // Tier-2 item 6's "simple dashboard or report that joins SAM request id
    // <-> RITM <-> evidence record", expressed as a callable query rather than
    // a platform report definition (which is a machine-serialized export, not
    // authorable text — see START-HERE.md §1).
    correlationReport: function (samRequestId) {
        if (!samRequestId) return { ok: false, reason: 'no SAM request id' };
        var report = { ok: true, sam_request_id: samRequestId, lineage: null, evidence: [] };

        var lin = new GlideRecord(this.tblIntegration);
        lin.addQuery('record_type', 'sam_lineage');
        lin.addQuery('sam_request_id', samRequestId);
        lin.query();
        if (lin.next()) {
            report.lineage = {
                sys_id: lin.getUniqueValue(), ritm: lin.getValue('ritm'),
                entra_object_id: lin.getValue('entra_object_id'),
                verified_by: lin.getValue('verified_by'), verified_authority: lin.getValue('verified_authority')
            };
        }

        var tblEvidence = gs.getProperty('x_fed_day2_ops.tbl_evidence', 'x_fed_day2_ops_evidence');
        var ev = new GlideRecord(tblEvidence);
        ev.addQuery('sam_request_id', samRequestId);
        ev.orderBy('sys_created_on');
        ev.query();
        while (ev.next()) {
            report.evidence.push({
                sys_id: ev.getUniqueValue(), verb: ev.getValue('verb'), control: ev.getValue('control'),
                closed: ev.getValue('closed'), stopped_at: ev.getValue('stopped_at'), hash: ev.getValue('hash')
            });
        }
        return report;
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
