// Scripted REST resource: POST /api/x_fed_day2_ops/sam/ritm  (scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// The inbound endpoint SailPoint IdentityIQ's ServiceNow Service Desk Integration
// Module (SDIM) PUSHES an approved access request to (IIQ-push, the recommended
// pattern). It creates/correlates the ServiceNow RITM for the SAM-originated
// request and writes the lineage record — MACD-R clauses 1–2 (Vol 0 Book 00): the
// request ORIGINATES in SAM and arrives already carrying its authoritative
// approval. ServiceNow does not re-decide; it records the decision and routes the
// governed execution.
//
// Install as a Scripted REST API (sys_ws_definition) resource:
//   API name:  x_fed_day2_ops/sam
//   Resource:  POST /ritm      (this script is the resource's "Script" field)
//   Security:  require authentication; restrict to the IIQ integration user's
//              role (x_fed_day2_ops.sam_inbound). ACL is the boundary here.
//
// FAIL CLOSED throughout: unauthenticated caller, wrong role, missing correlation
// fields, or an un-resolvable requested-for identity → 4xx and NO RITM created.
// An un-correlatable or unauthenticated push is refused, never best-guessed.
//
// Expected IIQ push body (SDIM field map):
//   { "sam_request_id":   "<IIQ IdentityRequest id>",
//     "access_item":      "<IIQ Role or Entitlement name>",
//     "requested_for":    "<correlation id resolving to the Entra object>",
//     "approval_authority":"<IGO | app-owner | dept-owner>",
//     "risk_tier":        "1|2|3",
//     "justification":    "<business justification>" }
// -----------------------------------------------------------------------------
(function process(request, response) {

    var sam = new x_fed_day2_ops.SamCorrelationClient();

    // 1. AuthN/Z is enforced by the Scripted REST ACL; assert role defensively too.
    if (!gs.hasRole('x_fed_day2_ops.sam_inbound')) {
        response.setStatus(403);
        return { ok: false, error: 'caller lacks x_fed_day2_ops.sam_inbound role (fail closed)' };
    }

    var body = request.body && request.body.data ? request.body.data : null;

    // 2. Validate the correlation contract (fail closed on any missing key).
    var v = sam.validateInboundPush(body);
    if (!v.ok) {
        response.setStatus(400);
        return { ok: false, error: v.reason };
    }

    // 3. Resolve the requested-for identity to a reconciled ServiceNow record.
    //    An unresolved identity is refused — a request we cannot bind to a known
    //    subject cannot be attested (AC-2).
    var user = new GlideRecord('sys_user');
    if (!user.get('correlation_id', body.requested_for) &&
        !user.get('email', body.requested_for)) {
        response.setStatus(422);
        return { ok: false, error: 'requested_for did not resolve to a reconciled identity (AC-2, fail closed)' };
    }

    // 4. Create the RITM carrying the SAM origin + authority. The catalog item and
    //    variable mapping are instance-specific; this creates the request record
    //    and tags it so the governed Flow picks it up. (Idempotent on sam_request_id.)
    var existing = new GlideRecord('x_fed_day2_ops_integration');
    if (existing.get('sam_request_id', body.sam_request_id)) {
        response.setStatus(200);
        return { ok: true, correlated: true, ritm: existing.getValue('ritm'), note: 'already correlated (idempotent)' };
    }

    var req = new GlideRecord('sc_request');   // or sc_req_item per your catalog wiring
    req.initialize();
    req.setValue('requested_for', user.getUniqueValue());
    req.setValue('short_description', 'SAM-originated access request ' + body.sam_request_id +
                 ' (' + body.access_item + ', tier ' + (body.risk_tier || '?') + ')');
    req.setValue('description', 'Origin: SAM (' + gs.getProperty('x_fed_day2_ops.sam_flavor', 'identityiq') +
                 '). Approval authority: ' + body.approval_authority +
                 '. Justification: ' + (body.justification || ''));
    var ritmSysId = req.insert();
    var ritmNumber = req.getValue('number');

    // 5. Write the end-to-end lineage (AU-2): SAM request <-> RITM <-> subject.
    var lineage = sam.recordLineage(ritmNumber, body.sam_request_id, user.getValue('correlation_id'));

    response.setStatus(lineage.ok ? 201 : 202);
    return {
        ok: lineage.ok,
        ritm: ritmNumber,
        ritm_sys_id: '' + ritmSysId,
        sam_request_id: body.sam_request_id,
        lineage_sys_id: lineage.sys_id || null,
        note: lineage.ok ? 'RITM created and correlated to the SAM decision'
                         : 'RITM created; lineage write incomplete — see logs'
    };

})(request, response);
