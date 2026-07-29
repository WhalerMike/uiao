// Script Include: Day2NativeActuator  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// Server-side actuator for every `servicenow-native` item in the day-2 kit —
// today the nine Lane F items (Vol IX Book 05) whose closure happens INSIDE
// ServiceNow: the intake record, the authorization verdict, the interface
// inventory, the ISA, the approval routing, the change record, the audit review,
// the attestation and the retention/lineage record. Each maps to a NIST control
// in servicenow-day2/saas-control-map.json.
//
// WHY THIS IS A SEPARATE CLIENT — and not a section of EntraSaasClient:
//   ServiceNow raises, routes and evidences; it NEVER writes to the estate. The
//   Graph clients actuate the tenant; this one writes ServiceNow's OWN records.
//   A CMDB CI, an ISA attachment and a change record are not the estate — they
//   are the workflow plane's own bookkeeping, which is exactly why they may be
//   written from here and why the tenant may not. Keeping them in one class with
//   the Graph methods would blur the one line the lane exists to hold, and the
//   first person to add a "convenience" method spanning both would erase it.
//
// THESE ARE STILL ACTUATORS. A control claim whose closure is "a human fills in a
// form" is not closed by anything a build can check. `saas.verify.authorization`
// records a VERDICT rather than configuring a tenant, but the record either
// exists with an approver, a date and a marketplace reference, or the gate did
// not happen. Code that writes it is what makes the difference auditable.
//
// Boundary discipline: no external transport at all. Nothing here leaves the
// instance, so there is no MID hop, no credential alias and no boundary egress to
// reason about — the strongest possible form of the rule. `boundary` is carried
// only so the evidence records say which boundary they were produced under.
//
// STARTER SKELETON — the table names below are the app's intended scoped tables;
// create them (or repoint to your instance's equivalents) before production use.
// test_mode (x_fed_day2_ops.test_mode = 'true') returns deterministic canned
// values so the ATF suites drive the Flow in sub-prod with NO record writes.
// Never enable test_mode in production.
// -----------------------------------------------------------------------------
var Day2NativeActuator = Class.create();
Day2NativeActuator.prototype = {

    initialize: function () {
        this.midServer = gs.getProperty('x_fed_day2_ops.mid_server', '');
        this.boundary = gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate');
        // The scoped tables this actuator writes. Held as properties so an
        // instance that already carries an ISA or interconnection table can
        // repoint without a code change.
        this.tblIntegration = gs.getProperty('x_fed_day2_ops.tbl_integration', 'x_fed_day2_ops_saas_integration');
        this.tblEvidence = gs.getProperty('x_fed_day2_ops.tbl_evidence', 'x_fed_day2_ops_evidence');
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.Day2NativeActuator] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Intake: record the integration request (AC-20). ----------------------
    // The SaaS, its business owner, the business need — and THE SPECIFIC IDENTITY
    // ATTRIBUTES IT WILL RECEIVE. That last field is load-bearing: it is what makes
    // saas.classify possible at all. Without it nobody can reason about exposure
    // except from vendor marketing, so it is required here rather than optional on
    // the form.
    //
    // This is the record of which organizational data LEAVES the boundary, and to
    // which external system — the outbound direction that inbound-scoped
    // external-access controls never reach.
    recordIntegrationRequest: function (request) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-integration-0001', vendor: request.vendor };
        if (!request || !request.attributes || !('' + request.attributes).trim()) {
            this.log.logErr('recordIntegrationRequest refused: no attributes declared (AC-20)');
            return { ok: false, reason: 'the identity attributes the SaaS will receive must be ' +
                                        'declared at request — classification is impossible without them (AC-20)' };
        }
        return this._insert(this.tblIntegration, {
            vendor: request.vendor,
            business_owner: request.ownerId,
            business_need: request.justification,
            attributes_shared: request.attributes,
            boundary: this.boundary,
            state: 'requested'
        });
    },

    // --- THE GATE: record the FedRAMP authorization verdict (SA-9). -----------
    // A Marketplace verdict at or above the Moderate baseline, recorded against the
    // request BEFORE anything is configured. No verdict, no progression. A verdict
    // collected AFTER configuration is a rationalization, not a gate — which is why
    // this refuses to write a verdict against an integration already past intake.
    //
    // The verdict is an ISSO DECISION recorded by a human. Note what this method
    // does not do: it does not call the Marketplace and decide. Name-matching a
    // gallery display name to a marketplace offering is unreliable, so tooling
    // narrows the queue and a person rules; an automated 'unauthorized' finding
    // from a fuzzy name match would be a false accusation with an approval attached.
    // `verdict` is therefore an input, and `approverId` is mandatory.
    recordAuthorizationVerdict: function (integrationId, verdict, approverId, marketplaceRef) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-verdict-0001', integration: integrationId,
                     verdict: verdict, gate: 'passed' };
        // Fail closed on an unattributed verdict: "authorized" with nobody's name
        // on it is the failure this control exists to prevent.
        if (!approverId)
            return { ok: false, reason: 'authorization verdict requires a named security approver (SA-9)' };
        return this._insert(this.tblEvidence, {
            integration: integrationId,
            control: 'SA-9',
            record_type: 'authorization_verdict',
            verdict: verdict,
            approver: approverId,
            marketplace_ref: marketplaceRef,
            boundary: this.boundary
        });
    },

    // --- Intake: record the CSO's functions, ports, protocols, endpoints ------
    // (SA-9(2)). The NGFW allow-list and the DDI/DNS records for the integration
    // DERIVE from this record rather than from a ticket comment. That derivation is
    // the whole value: an endpoint the SaaS uses but never declared is then
    // detectable as drift, instead of being indistinguishable from normal traffic.
    recordInterfaceInventory: function (integrationId, interfaces) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-interfaces-0001', integration: integrationId,
                     count: 0 };
        return this._insert(this.tblEvidence, {
            integration: integrationId,
            control: 'SA-9(2)',
            record_type: 'interface_inventory',
            // Serialized whole: the ACS URL, SCIM base URL, IdP-initiated targets,
            // ports and protocols travel together or the allow-list cannot be
            // derived from them.
            payload: JSON.stringify(interfaces || {}),
            boundary: this.boundary
        });
    },

    // --- Agreement: attach the ISA before sync is enabled (CA-3). -------------
    // SCIM path only. A standing directory replica in an external system is an
    // interconnection, and an interconnection needs an agreement — attached and
    // approved BEFORE the sync job is enabled, not after it works.
    //
    // SSO-only integrations skip this entirely and MUST NOT be made to wait for it:
    // over-gating the cheap path is how a control gets routed around. So the
    // classification is an argument, and an assertion-only flow returns a clean
    // not-applicable rather than an open task nobody can close.
    attachInterconnectionAgreement: function (integrationId, classification, isaAttachmentId, approverId) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-isa-0001', integration: integrationId,
                     applicable: classification === 'standing-replica' };
        if (classification !== 'standing-replica')
            return { ok: true, applicable: false, integration: integrationId,
                     reason: 'assertion-only flow — no standing replica, no interconnection (CA-3 n/a)' };
        if (!isaAttachmentId || !approverId)
            return { ok: false, reason: 'a standing replica requires an attached, approved ISA ' +
                                        'before synchronization is enabled (CA-3)' };
        return this._insert(this.tblEvidence, {
            integration: integrationId,
            control: 'CA-3',
            record_type: 'isa',
            attachment: isaAttachmentId,
            approver: approverId,
            boundary: this.boundary
        });
    },

    // --- Approval: separate request from approval (AC-5). ---------------------
    // The requester may never be the approver. Any integration receiving privileged
    // scopes, and any SCIM path, requires a security approver DISTINCT from the
    // business owner — a standing directory replica is a privileged outcome even
    // when no role says so.
    //
    // Fail closed on indeterminate: a missing id is not a pass. This mirrors
    // EntraHelpdeskGate.preflight rather than reimplementing it, because the rule
    // is the same rule and two copies would drift apart.
    routeApproval: function (integrationId, requesterId, approverId, opts) {
        opts = opts || {};
        if (this.testMode)
            return { ok: true, sys_id: 'test-approval-0001', integration: integrationId,
                     approver: approverId };
        if (!requesterId || !approverId)
            return { ok: false, reason: 'SoD indeterminate: requester/approver not populated (AC-5)' };
        if (requesterId === approverId)
            return { ok: false, reason: 'SoD violation: requester == approver (AC-5)' };
        var needsSecurity = opts.privileged === true || opts.privileged === 'true' ||
                            opts.classification === 'standing-replica';
        if (needsSecurity && approverId === opts.ownerId)
            return { ok: false, reason: 'privileged scope or SCIM path requires a security approver ' +
                                        'distinct from the business owner (AC-5)' };
        return this._insert('sysapproval_approver', {
            document_id: integrationId,
            approver: approverId,
            state: 'requested'
        });
    },

    // --- Change: gate actuation on an approved change record (CM-3). ----------
    // Every compliance-affecting change to the integration — enabling SSO, enabling
    // SCIM, widening scope, rotating a credential — carries an approved, reviewable
    // change record BEFORE actuation. This is the Vol VII Book 00 coordination
    // doctrine applied unchanged.
    //
    // The record opens in 'assess', never 'implement': a change record this method
    // could self-approve would be a receipt, not a gate.
    openChangeRecord: function (integrationId, summary, opts) {
        opts = opts || {};
        if (this.testMode)
            return { ok: true, sys_id: 'test-change-0001', number: 'CHG0000001',
                     state: 'assess' };
        return this._insert('change_request', {
            short_description: summary,
            description: opts.description || summary,
            type: opts.type || 'normal',
            cmdb_ci: opts.ciId || '',
            correlation_id: integrationId,
            state: 'assess'
        });
    },

    // --- Evidence: review the audit records on cadence (AU-6). ----------------
    // AU-6 is the control most often assumed by "the logs are in Sentinel".
    // Collection is AU-2; somebody actually LOOKING is AU-6, and only a task with a
    // named owner, a cadence and a closure record produces evidence that anyone did.
    // Hence a task, not a dashboard.
    openAuditReviewTask: function (integrationId, reviewerId, cadence) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-review-0001', integration: integrationId,
                     reviewer: reviewerId };
        if (!reviewerId)
            return { ok: false, reason: 'an audit review with no named reviewer evidences nothing (AU-6)' };
        return this._insert(this.tblEvidence, {
            integration: integrationId,
            control: 'AU-6',
            record_type: 'audit_review',
            assigned_to: reviewerId,
            cadence: cadence,
            state: 'open',
            boundary: this.boundary
        });
    },

    // --- Attest: re-verify authorization, ownership and scope (CA-7). ---------
    // Authorization is not a one-time fact. A CSO can LOSE its authorization, and an
    // integration can outlive the business need that justified it — neither event
    // sends a notification. Cadence re-verification of the marketplace verdict, the
    // owner and the attribute scope; a lapsed authorization or an orphaned
    // integration raises a task. Feeds Vol VII Book 04 attestation and the KSI
    // evidence pipeline.
    //
    // Raises, never self-remediates: the remedy for a failed attestation is
    // saas.offboard, which tears down a live trust and belongs to a human.
    openAttestationTask: function (integrationId, ownerId, findings) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-attest-0001', integration: integrationId,
                     lapsed: false };
        return this._insert(this.tblEvidence, {
            integration: integrationId,
            control: 'CA-7',
            record_type: 'attestation',
            assigned_to: ownerId,
            payload: JSON.stringify(findings || {}),
            state: 'open',
            boundary: this.boundary
        });
    },

    // --- Retention: record attribute lineage (SI-12). -------------------------
    // Which identity attributes flow to this SaaS, from which authoritative source,
    // and what the vendor's retention and deletion commitments are.
    //
    // Recorded HERE, where the data originates and flows, because lineage cannot be
    // reconstructed from the vendor's copy at audit time — by then the only evidence
    // of what left is whatever the vendor chose to keep. saas.offboard checks
    // vendor-side deletion against this record; without it there is nothing to check
    // deletion against.
    recordAttributeLineage: function (integrationId, lineage) {
        if (this.testMode)
            return { ok: true, sys_id: 'test-lineage-0001', integration: integrationId };
        if (!lineage || !lineage.attributes || !lineage.source)
            return { ok: false, reason: 'lineage requires the attributes AND their authoritative ' +
                                        'source — a list with no origin is not lineage (SI-12)' };
        return this._insert(this.tblEvidence, {
            integration: integrationId,
            control: 'SI-12',
            record_type: 'attribute_lineage',
            payload: JSON.stringify(lineage),
            retention_commitment: lineage.retention || '',
            boundary: this.boundary
        });
    },

    // --- Internal: the one write path — ServiceNow's own records. -------------
    // The native analogue of the Graph clients' _graph: a single choke point, the
    // same {ok, status, body} shape, the same try/catch discipline. Everything this
    // class writes goes through here, so "what can this actuator touch?" has one
    // answer: scoped records on the instance, by GlideRecord, and nothing else.
    // There is deliberately no update/delete path — day-2 evidence is append-only;
    // a record that can be rewritten after the fact is not evidence of anything.
    _insert: function (table, fields) {
        try {
            var gr = new GlideRecord(table);
            if (!gr.isValid()) {
                this.log.logErr('_insert: table ' + table + ' does not exist on this instance');
                return { ok: false, error: 'table ' + table + ' does not exist' };
            }
            gr.initialize();
            for (var f in fields) {
                if (fields.hasOwnProperty(f) && fields[f] !== undefined && fields[f] !== null)
                    gr.setValue(f, fields[f]);
            }
            var sysId = gr.insert();
            // insert() returns null when an ACL or a data-policy refused the write.
            // A refused write that returned ok:true would put a control claim behind
            // a record that does not exist.
            if (!sysId) {
                this.log.logErr('_insert into ' + table + ' returned no sys_id — refused by ACL or data policy');
                return { ok: false, error: 'insert refused (ACL or data policy) on ' + table };
            }
            return { ok: true, status: 201, sys_id: '' + sysId, table: table };
        } catch (e) {
            this.log.logErr('_insert into ' + table + ' failed: ' + ('' + e).replace(/[\r\n]+/g, ' ').slice(0, 500));
            return { ok: false, error: '' + e };
        }
    },

    type: 'Day2NativeActuator'
};
