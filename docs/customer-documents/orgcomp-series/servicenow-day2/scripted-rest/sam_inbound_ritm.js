// Scripted REST resource: POST /api/x_fed_day2_ops/sam/ritm  (scope: x_fed_day2_ops)
// =============================================================================
// REMEDIATED BUILD — closes P0-7.
//
// The original accepted the approval DECISION as caller-asserted data:
// approval_authority, risk_tier and access_item arrived in the body and were
// recorded as authoritative, with nothing verifying the IdentityRequest existed
// or was approved. Since the design intent is that "ServiceNow does not
// re-decide", that assertion WAS the entire authorization boundary — so misuse
// or compromise of the single integration account was sufficient to mint an
// "IGO-approved, tier 1" request the downstream Flow would treat as
// pre-authorized.
//
// What changed:
//   1. PULL-VERIFY. The push is now a NOTIFICATION, not an authorization. We
//      call back to IIQ on sam_request_id, confirm the request exists, is
//      approved, and matches the asserted subject/item, and record OUR
//      VERIFICATION — not the caller's claim — as the evidence. Optional JWS
//      verification is supported for deployments that can sign.
//   2. FAIL CLOSED ON LINEAGE. Lineage is written FIRST. Previously a failed
//      lineage write returned 202 and left an executable RITM with no audit
//      trail, in a file whose header said "FAIL CLOSED throughout".
//   3. IDENTITY RESOLUTION. correlation_id only (no mutable-email fallback),
//      active users only, and an ambiguous match is refused rather than
//      silently resolved to the first row.
//   4. IDEMPOTENCY. Keyed on (record_type='sam_lineage', sam_request_id) — the
//      integration table also holds sam_push_outcome telemetry rows carrying
//      the same sam_request_id, so an unscoped lookup matches a prior refusal
//      and silently drops the retried request (see clause 5). Paired with a
//      REQUIRED unique index (see the deployment note) because check-then-
//      insert alone races.
//   5. ROLE CHECK. gs.hasRole() returns true for admin, so the defensive
//      assertion was satisfied by any admin-scoped caller. Now checks explicit
//      role grant.
//   6. RESPONSES. No control identifiers or check names in the body — an
//      authenticated-but-hostile integration user should not receive a map of
//      the control surface.
//
// DEPLOYMENT NOTES (required, not optional):
//   * Create a UNIQUE INDEX on <integration table>.sam_request_id.
//     This is only safe because sam_request_id is now written by LINEAGE ROWS
//     ONLY — telemetry carries the id in sam_request_ref instead (see
//     KIT-BUILD-SPEC.md §2b). Before that split the index was unimplementable:
//     recordPushOutcome() writes a row on every refusal and every accept, so
//     many rows shared one sam_request_id and a unique index — on the column
//     alone OR on (record_type, sam_request_id) — would have rejected every
//     telemetry insert after the first, silently, inside its own try/catch.
//   * Configure x_fed_day2_ops.iiq_verify_endpoint + the credential alias, or
//     x_fed_day2_ops.sam_jws_public_key. With NEITHER configured this endpoint
//     refuses every push — that is intended.
//   * ACL the resource to x_fed_day2_ops.sam_inbound.
//
// TELEMETRY: every accept and refuse writes a sam_push_outcome row via
// SamCorrelationClient.recordPushOutcome — see "Monitoring the inbound
// endpoint" in KIT-USAGE-SAM-INTEGRATION.md. Best effort; never affects the
// response.
// =============================================================================
(function process(request, response) {
    // Top-level guard: every call this handler makes into SamCorrelationClient
    // (recordLineage/attachRitmToLineage/fetchIdentityRequest/verifyJws/
    // recordPushOutcome) now returns {ok:false} rather than throwing, so this
    // shouldn't normally fire. It exists as defense in depth so an unexpected
    // exception (a GlideRecord API misuse, a future refactor) returns the same
    // opaque error shape as every deliberate refusal in this file, never a stack
    // trace or script path, to an authenticated-but-hostile caller (design
    // goal #6 above).
    try {
        return handle(request, response);
    } catch (e) {
        gs.error('[x_fed_day2_ops.sam_inbound] unhandled exception: ' +
                 ('' + e).replace(/[\r\n]+/g, ' ').slice(0, 500));
        response.setStatus(500);
        return { ok: false, error: 'internal_error' };
    }

    function handle(request, response) {

    var sam = new x_fed_day2_ops.SamCorrelationClient();
    var env = new x_fed_day2_ops.Day2Env();

    function deny(status, code) {
        response.setStatus(status);
        // Telemetry: one row per refused push (Tier-2 item 6 — see
        // KIT-USAGE-SAM-INTEGRATION.md "Monitoring the inbound endpoint").
        // Only the opaque code goes to telemetry, same as the response body —
        // recordPushOutcome itself never throws, so this cannot turn a real
        // refusal into a 500.
        sam.recordPushOutcome(body && body.sam_request_id, 'refused', status, code);
        return { ok: false, error: code };   // opaque code; detail goes to the log
    }
    function logRefusal(reason) {
        gs.warn('[x_fed_day2_ops.sam_inbound] refused: ' + Day2Env.scrub(reason) +
                ' (caller: ' + Day2Env.scrub(gs.getUserName()) + ')');
    }

    var guard = env.guard();
    if (!guard.ok) { logRefusal(guard.reason); return deny(503, 'unavailable'); }

    // 1. AuthZ. Explicit role grant only — gs.hasRole() is true for admin.
    if (!gs.getUser().hasRoleExactly('x_fed_day2_ops.sam_inbound')) {
        logRefusal('caller lacks x_fed_day2_ops.sam_inbound (explicit grant required)');
        return deny(403, 'forbidden');
    }

    var body = (request.body && request.body.data) ? request.body.data : null;

    // 2. Contract validation.
    var v = sam.validateInboundPush(body);
    if (!v.ok) { logRefusal('contract validation: ' + v.reason); return deny(400, 'bad_request'); }

    // 3. PULL-VERIFY — the core of this fix. The body is a claim; this is the
    //    check. We never proceed on the caller's assertion alone.
    var verification = verifyWithSam(body);
    if (!verification.ok) {
        logRefusal('SAM verification failed for ' + body.sam_request_id + ': ' + verification.reason);
        return deny(verification.status || 422, verification.code || 'unverified');
    }

    // 4. Identity resolution — correlation_id only, active only, unambiguous only.
    var subject = resolveSubject(body.requested_for);
    if (!subject.ok) { logRefusal('subject resolution: ' + subject.reason); return deny(422, 'unresolved_subject'); }

    // 5. Idempotency. MUST be scoped to record_type = 'sam_lineage'.
    //
    //    The integration table is shared. Telemetry now carries its id in
    //    sam_request_ref, not sam_request_id, so this lookup can no longer
    //    collide — but the filter stays as defence in depth, because the
    //    failure it prevents is silent: recordPushOutcome() writes a
    //    'sam_push_outcome' row on EVERY accept and refuse, and those rows
    //    never carry a ritm. An unscoped
    //    lookup therefore matches this request's own earlier refusal telemetry
    //    and short-circuits with ritm:'' — reporting {ok:true, correlated:true}
    //    for a request that was never created. A push refused once (e.g. before
    //    iiq_verify_endpoint was configured) could never afterwards succeed:
    //    the retry would be swallowed and the caller told it had correlated.
    //    That inverts this file's fail-closed, lineage-first ordering, so the
    //    record_type filter is load-bearing, not hygiene.
    //
    //    Only 'sam_lineage' rows represent a correlated request. correlationReport()
    //    in SamCorrelationClient scopes the same way.
    var existing = new GlideRecord(gs.getProperty('x_fed_day2_ops.tbl_integration', 'x_fed_day2_ops_integration'));
    existing.addQuery('record_type', 'sam_lineage');
    existing.addQuery('sam_request_id', body.sam_request_id);
    existing.setLimit(1);
    existing.query();
    if (existing.next()) {
        response.setStatus(200);
        sam.recordPushOutcome(body.sam_request_id, 'accepted', 200, 'idempotent');
        return { ok: true, correlated: true, ritm: existing.getValue('ritm'), note: 'already correlated' };
    }

    // 6. LINEAGE FIRST. If the audit record cannot be written, no executable
    //    request is created. This is the fail-closed ordering.
    var lineage = sam.recordLineage(null, body.sam_request_id, subject.correlation_id, {
        verified_by: verification.method,
        verified_at: new GlideDateTime().getValue(),
        verified_authority: verification.approval_authority,
        verified_status: verification.status_text,
        verified_item: verification.access_item
    });
    if (!lineage.ok) {
        logRefusal('lineage write failed for ' + body.sam_request_id + ' — no RITM created');
        return deny(503, 'lineage_unavailable');
    }

    // 7. Create the RITM. Note it carries the VERIFIED authority, not the
    //    asserted one — if the two ever disagree, verification already refused.
    var req = new GlideRecord('sc_request');
    req.initialize();
    req.setValue('requested_for', subject.sys_id);
    req.setValue('short_description',
        'SAM-originated access request ' + safe(body.sam_request_id) +
        ' (' + safe(verification.access_item) + ', tier ' + safe(verification.risk_tier || '?') + ')');
    req.setValue('description',
        'Origin: SAM (' + gs.getProperty('x_fed_day2_ops.sam_flavor', 'identityiq') + '). ' +
        'Approval authority (verified with SAM, not asserted by caller): ' + safe(verification.approval_authority) + '. ' +
        'Verification method: ' + safe(verification.method) + '. ' +
        'Justification: ' + safe(verification.justification || body.justification || ''));
    var ritmSysId = req.insert();
    if (!ritmSysId) {
        logRefusal('RITM insert failed after lineage write for ' + body.sam_request_id);
        return deny(503, 'request_creation_failed');
    }
    var ritmNumber = req.getValue('number');

    // 8. Bind the lineage record to the RITM it now covers.
    sam.attachRitmToLineage(lineage.sys_id, ritmNumber, '' + ritmSysId);

    response.setStatus(201);
    sam.recordPushOutcome(body.sam_request_id, 'accepted', 201, 'created');
    return {
        ok: true,
        ritm: ritmNumber,
        ritm_sys_id: '' + ritmSysId,
        sam_request_id: body.sam_request_id,
        lineage_sys_id: lineage.sys_id,
        verified: true
    };

    // -------------------------------------------------------------------------

    function safe(s) { return Day2Env.scrub(s === null || s === undefined ? '' : s); }

    // Verify the decision independently of the caller. Two supported methods;
    // if neither is configured we refuse, because an unverifiable push is
    // exactly the condition this fix exists to stop.
    function verifyWithSam(b) {
        var jwsKey = gs.getProperty('x_fed_day2_ops.sam_jws_public_key', '');
        if (jwsKey && b.jws) {
            var jws = sam.verifyJws(b.jws, jwsKey);   // must validate sig, iss, exp, and bind to sam_request_id
            if (!jws.ok) return { ok: false, status: 401, code: 'bad_signature', reason: jws.reason };
            if (jws.claims.sam_request_id !== b.sam_request_id)
                return { ok: false, status: 400, code: 'signature_subject_mismatch',
                         reason: 'signed payload does not bind to the asserted sam_request_id' };
            return { ok: true, method: 'jws',
                     approval_authority: jws.claims.approval_authority,
                     access_item: jws.claims.access_item,
                     risk_tier: jws.claims.risk_tier,
                     justification: jws.claims.justification,
                     status_text: jws.claims.status };
        }

        var endpoint = gs.getProperty('x_fed_day2_ops.iiq_verify_endpoint', '');
        if (!endpoint) {
            return { ok: false, status: 503, code: 'verification_unavailable',
                     reason: 'neither iiq_verify_endpoint nor sam_jws_public_key is configured — cannot verify, refusing (fail closed)' };
        }

        var pulled = sam.fetchIdentityRequest(b.sam_request_id);   // MID-routed, credential-alias auth
        if (!pulled.ok)
            return { ok: false, status: 502, code: 'verification_unavailable', reason: pulled.reason };

        var st = ('' + (pulled.data.executionStatus || pulled.data.status || '')).toLowerCase();
        if (st !== 'approved' && st !== 'verified' && st !== 'complete')
            return { ok: false, status: 409, code: 'not_approved',
                     reason: 'SAM reports status "' + st + '" — not an approved request' };

        // The push must agree with SAM on subject and item. A mismatch is an
        // attempt to attach an approved decision to a different grant.
        if (pulled.data.requested_for && b.requested_for &&
            ('' + pulled.data.requested_for).toLowerCase() !== ('' + b.requested_for).toLowerCase())
            return { ok: false, status: 409, code: 'subject_mismatch',
                     reason: 'pushed requested_for does not match SAM' };
        if (pulled.data.access_item && b.access_item &&
            ('' + pulled.data.access_item).toLowerCase() !== ('' + b.access_item).toLowerCase())
            return { ok: false, status: 409, code: 'item_mismatch',
                     reason: 'pushed access_item does not match SAM' };

        return { ok: true, method: 'pull-verify',
                 approval_authority: pulled.data.approval_authority,
                 access_item: pulled.data.access_item,
                 risk_tier: pulled.data.risk_tier,
                 justification: pulled.data.justification,
                 status_text: st };
    }

    // correlation_id only. Email is mutable, non-unique in practice (shared and
    // functional mailboxes), and GlideRecord.get() on a non-unique field
    // silently returns the first match.
    function resolveSubject(correlationId) {
        if (!correlationId) return { ok: false, reason: 'requested_for empty' };
        var gr = new GlideRecord('sys_user');
        gr.addQuery('correlation_id', correlationId);
        gr.addQuery('active', true);
        gr.query();
        var count = gr.getRowCount();
        if (count === 0) return { ok: false, reason: 'no active reconciled identity for that correlation_id' };
        if (count > 1)  return { ok: false, reason: 'correlation_id matched ' + count + ' active users — ambiguous, refusing' };
        gr.next();
        return { ok: true, sys_id: gr.getUniqueValue(), correlation_id: gr.getValue('correlation_id') };
    }

    } // end handle()

})(request, response);
