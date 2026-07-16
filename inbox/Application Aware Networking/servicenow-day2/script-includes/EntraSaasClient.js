// Script Include: EntraSaasClient  (application scope: x_ssa_day2_ops)
// -----------------------------------------------------------------------------
// Server-side Microsoft Graph client for Lane F — SaaS Integration Governance
// (Vol IX Book 05). Onboarding a third-party SaaS is not one control event: it is
// the moment a gallery app, a federation trust, a directory replica and a set of
// assignments all come into existence — or are silently created by a portal click
// nobody reviewed. Each method maps to a NIST control in
// servicenow-day2/saas-control-map.json.
//
// Boundary discipline (Vol IX Book 00 / Vol VII):
//   * All Graph calls route through the in-boundary MID Server
//     (property x_ssa_day2_ops.mid_server) — credentials/execution never leave
//     the ATO boundary.
//   * Endpoint + auth come from the Connection & Credential alias
//     (x_ssa_day2_ops.graph) — no secrets in code.
//   * LEAST PRIVILEGE: the app registration behind that alias needs
//     Application.ReadWrite.OwnedBy, AppRoleAssignment.ReadWrite.All,
//     Synchronization.ReadWrite.All and AuditLog.Read.All. Note what is NOT here:
//     Directory.ReadWrite.All. A client that governs one integration must not be
//     able to rewrite the directory it federates from.
//   * Under GCC Moderate the Graph host resolves to the commercial endpoint that
//     serves that boundary: graph.microsoft.com. GCC High / DoD are not offered
//     here, and the telemetry reads below are bounded by what that boundary
//     actually exposes (see the SCuBA boundary-limitations brief) — they collect
//     what exists, they do not conjure what the boundary withholds.
//
// CREDENTIALS ARE NOT ISSUED HERE. The token-signing certificate and the SCIM
// bearer token are AcmeCredentialClient's job (acme-via-mid). This client has no
// method that mints or returns an authenticator: the "no long-lived secret in
// config" rule of Book 05 survives because the client that configures federation
// is given no way to break it.
//
// SERVICENOW NEVER WRITES ITS OWN RECORDS FROM HERE. This client only touches the
// tenant. Verdicts, ISAs, CIs, approvals and change records are ServiceNow's own
// records and belong to Day2NativeActuator — that split is the whole reason the
// two clients exist.
//
// STARTER SKELETON — pin the Graph API version and validate scopes against your
// tenant before production use.  test_mode (x_ssa_day2_ops.test_mode = 'true')
// returns deterministic canned values so the ATF suites drive the Flow in sub-prod
// with NO live Graph connectivity.  Never enable test_mode in production.
// -----------------------------------------------------------------------------
var EntraSaasClient = Class.create();
EntraSaasClient.prototype = {

    initialize: function () {
        this.graphVersion = gs.getProperty('x_ssa_day2_ops.graph_version', 'v1.0');
        this.midServer = gs.getProperty('x_ssa_day2_ops.mid_server', '');
        this.boundary = gs.getProperty('x_ssa_day2_ops.boundary', 'gcc-moderate');
        this.log = { logErr: function (m) { gs.error('[x_ssa_day2_ops.EntraSaasClient] ' + m); } };
        this.testMode = gs.getProperty('x_ssa_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Classify: assertion, or standing replica? (AC-4). --------------------
    // The most expensive modelling error available in this lane is collapsing the
    // two. SSO passes an assertion at sign-in and is gone — nothing of the
    // directory persists in the vendor cloud. SCIM leaves a durable, continuously
    // synced REPLICA of directory data there. Only the second is an
    // interconnection, and only the second needs an ISA (saas.isa).
    //
    // `declaredAttributes` comes from saas.request — the classification is derived
    // from what the integration said it would receive, not judged ad hoc. But the
    // tenant is consulted too, and the tenant WINS: if a synchronization job
    // actually exists, a replica exists, whatever the request claimed. A
    // classification that trusts only the paperwork cannot detect the portal click
    // that enabled sync behind its back.
    classifyFlow: function (servicePrincipalId, declaredAttributes) {
        if (this.testMode)
            return { ok: true, id: servicePrincipalId, classification: 'assertion',
                     isaRequired: false, syncJobObserved: false };
        var jobs = this._graph('GET', '/servicePrincipals/' + servicePrincipalId +
                                      '/synchronization/jobs', null);
        // A failed read is NOT "no replica" — fail closed. Guessing 'assertion'
        // here would route the integration around the ISA gate on a network blip.
        if (!jobs.ok)
            return { ok: false, id: servicePrincipalId,
                     reason: 'sync-job read failed — classification inconclusive, ISA gate not cleared' };
        var observed = ('' + jobs.body).indexOf('"id"') !== -1;
        var declaredReplica = !!(declaredAttributes && declaredAttributes.scimEnabled);
        var replica = observed || declaredReplica;
        return { ok: true, id: servicePrincipalId,
                 classification: replica ? 'standing-replica' : 'assertion',
                 isaRequired: replica, syncJobObserved: observed,
                 declaredReplica: declaredReplica };
    },

    // --- Register: read the tenant state the CI is reconciled FROM (CM-8). ----
    // The service principal, its applicationTemplateId, its SSO mode and its
    // sync-job state are the authoritative facts; the CMDB CI is a projection of
    // them (DDI stays the SSOT for asset identity, per Vol VII Book 01). The item
    // is declared graph-via-mid because THIS read is the actuation that CM-8
    // needs; the Flow's reconcile step projects the result onto the CI.
    // Reading here rather than trusting the request is the point: an integration
    // that exists in the tenant but not in the register is drift, and drift is
    // only detectable if something observes the tenant.
    describeServicePrincipal: function (servicePrincipalId) {
        if (this.testMode)
            return { ok: true, id: servicePrincipalId, appId: 'test-appid-0001',
                     displayName: 'test-saas', applicationTemplateId: 'test-template-0001',
                     preferredSingleSignOnMode: 'saml', accountEnabled: true };
        return this._graph('GET', '/servicePrincipals/' + servicePrincipalId +
                                  '?$select=id,appId,displayName,applicationTemplateId,' +
                                  'preferredSingleSignOnMode,accountEnabled,tags', null);
    },

    // --- Configure: federated SSO, never a portal click (IA-2). ---------------
    // Actuated through the MID so the change is attributable to an approved
    // request rather than to whoever had the tenant open. `mode` is 'saml' or
    // 'oidc'.
    //
    // Note what this method canNOT do: it cannot disable the SaaS's own local
    // accounts — that lives on the vendor side, beyond Graph's reach. "SSO
    // available" is not "SSO required", and only the second closes IA-2. The
    // catalog item carries the attestation that native credentials are disabled or
    // exception-approved; this client actuates the half it can reach and does not
    // pretend to the other half.
    configureSso: function (servicePrincipalId, mode, opts) {
        opts = opts || {};
        if (this.testMode)
            return { ok: true, id: servicePrincipalId, preferredSingleSignOnMode: mode,
                     localAccountsAttested: false };
        return this._graph('PATCH', '/servicePrincipals/' + servicePrincipalId, {
            preferredSingleSignOnMode: mode,
            loginUrl: opts.loginUrl,
            notificationEmailAddresses: opts.notificationEmailAddresses || []
        });
    },

    // --- Identifier: one enterprise identifier per person (IA-4). -------------
    // Sourced from the HR-derived worker record (Vol I Book 04) and carried into
    // the SaaS, so the vendor never mints its own identifier for an organizational
    // user. Per-app identity sprawl is what makes rehire and transfer correlation
    // impossible in the target system.
    //
    // *** L4 (AUTONOMOUS) — ABOVE THE FEDERAL L3 CEILING. ***
    // saas.identifier carries approval:'automated', so this WRITES to the tenant
    // with no human in the loop. ADR-092 sets L3 (platform-native, human-approved)
    // as the federal default; an autonomous write is L4 and needs a documented
    // ADR-092 justification that does not yet exist. The approval is left as-is
    // deliberately — changing the map to hide the exceedance would be worse than
    // carrying it visibly. Read this as a known, owned deviation pending that ADR,
    // not as settled doctrine.
    setEnterpriseIdentifier: function (servicePrincipalId, claimsMappingPolicyId) {
        if (this.testMode)
            return { ok: true, id: servicePrincipalId, policyId: claimsMappingPolicyId,
                     l4Autonomous: true };
        return this._graph('POST', '/servicePrincipals/' + servicePrincipalId +
                                   '/claimsMappingPolicies/$ref', {
            '@odata.id': 'https://graph.microsoft.com/' + this.graphVersion +
                         '/policies/claimsMappingPolicies/' + claimsMappingPolicyId
        });
    },

    // --- Provision: create the SCIM sync job — ISA-gated (AC-2(1)). -----------
    // Creating the synchronization job IS automated account management: from this
    // moment accounts in the SaaS are created, updated and removed from the
    // authoritative directory instead of by hand.
    //
    // The ISA check is a REQUIRED ARGUMENT, not a flow-step convention, because
    // this is the exact step CA-3 gates: a standing directory replica in an
    // external system is an interconnection, and the agreement must be approved
    // BEFORE the replica exists — not after it works. A caller that cannot prove
    // the ISA is approved gets a refusal here, even if the Flow forgot to ask.
    enableScimSyncJob: function (servicePrincipalId, templateId, isaApproved) {
        if (this.testMode)
            return { ok: true, id: 'test-syncjob-0001', servicePrincipalId: servicePrincipalId,
                     templateId: templateId };
        // Fail closed: anything other than an explicit true is "not approved".
        if (isaApproved !== true) {
            this.log.logErr('enableScimSyncJob refused for ' + servicePrincipalId +
                            ': ISA not approved (CA-3)');
            return { ok: false, reason: 'ISA not approved — a standing directory replica ' +
                                        'requires an approved interconnection agreement first (CA-3)' };
        }
        return this._graph('POST', '/servicePrincipals/' + servicePrincipalId +
                                   '/synchronization/jobs', { templateId: templateId });
    },

    // --- Authorize: access by assignment, never "all users" (AC-3). -----------
    // Once the federation trust exists, the assignment is the ONLY enforcement
    // point the agency still controls — everything else is the vendor's. An
    // enterprise app left "available to all users" hands that last control away.
    assignAccess: function (servicePrincipalId, principalId, appRoleId) {
        if (this.testMode)
            return { ok: true, id: 'test-assignment-0001', principalId: principalId,
                     resourceId: servicePrincipalId, appRoleId: appRoleId };
        return this._graph('POST', '/servicePrincipals/' + servicePrincipalId +
                                   '/appRoleAssignedTo', {
            principalId: principalId, resourceId: servicePrincipalId, appRoleId: appRoleId
        });
    },

    // --- Authorize: least-privilege app roles (AC-6). -------------------------
    // A read of the roles the SaaS actually publishes, so the mapping is made from
    // the authoritative org model against real roles — not from the vendor's
    // default "all users are admins" role accepted at setup. The mapping decision
    // and its security approval live on the catalog record; this supplies the
    // menu, it does not choose from it.
    mapAppRoles: function (servicePrincipalId) {
        if (this.testMode)
            return { ok: true, id: servicePrincipalId,
                     appRoles: [{ id: 'test-role-0001', value: 'User', isEnabled: true }] };
        return this._graph('GET', '/servicePrincipals/' + servicePrincipalId +
                                  '?$select=id,appRoles', null);
    },

    // --- Lifecycle: propagate separation to the SaaS (AC-2(3)). ---------------
    // Vol I Book 04 owns the separation fact (PS-4); this propagates it on the
    // effective date. Without it the directory is clean and the SaaS still has a
    // live account — the exact failure an assessor probes, and the reason
    // separation-to-revocation inside the SaaS is a ConMon metric.
    //
    // Remove the assignment AND revoke sessions: an assignment removal alone
    // leaves an already-issued session valid until it expires, so the two results
    // are folded into `ok`. A leaver is not de-provisioned if only half of it took.
    //
    // *** L4 (AUTONOMOUS) — ABOVE THE FEDERAL L3 CEILING. ***
    // saas.leaver carries approval:'automated' — an unattended tenant write, which
    // is L4 under ADR-092 where L3 is the federal default. The operational case is
    // real (a leaver who keeps SaaS access because an approver was on leave is its
    // own incident, and this direction is revocation — it only ever removes
    // access), but the case is not the same thing as a documented justification.
    // Pending that ADR-092 write-up, this is a known, owned exceedance.
    propagateLeaver: function (servicePrincipalId, assignmentId, userId) {
        if (this.testMode)
            return { ok: true, servicePrincipalId: servicePrincipalId,
                     assignmentId: assignmentId, sessionsRevoked: true, l4Autonomous: true };
        var removed = this._graph('DELETE', '/servicePrincipals/' + servicePrincipalId +
                                            '/appRoleAssignedTo/' + assignmentId, null);
        var revoke = this._graph('POST', '/users/' + userId + '/revokeSignInSessions', {});
        return { ok: removed.ok && revoke.ok, servicePrincipalId: servicePrincipalId,
                 assignmentId: assignmentId, removeStatus: removed.status,
                 sessionsRevoked: revoke.ok, revokeStatus: revoke.status };
    },

    // --- Lifecycle: re-derive access on transfer (PS-5). ----------------------
    // To the SaaS a transferred person is the same account doing the same things;
    // only the HR event makes the change visible at all. This reads what the person
    // currently holds so the residual can be compared against the entitlements
    // their NEW assignment derives — the difference is what the access review acts
    // on. A read: a mover is not a leaver, and silently stripping access on a
    // transfer is an outage, so the removal decision stays with the owner.
    rederiveAccessOnTransfer: function (userId) {
        if (this.testMode)
            return { ok: true, id: userId,
                     value: [{ id: 'test-assignment-0001', resourceId: 'test-sp-0001' }] };
        return this._graph('GET', '/users/' + userId + '/appRoleAssignments', null);
    },

    // --- Evidence: account-lifecycle audit records (AC-2(4)). ----------------
    // Create/modify/enable/disable/remove of SaaS accounts, correlated to the
    // originating HR or catalog event. The provisioning service's own log is the
    // source — the catalog item is what guarantees the record is COLLECTED rather
    // than left to age out in the tenant. A read, and approval:'automated' is
    // right here: reading evidence is not actuation, so no L3 question arises.
    getProvisioningAuditEvents: function (servicePrincipalId, sinceIso) {
        if (this.testMode)
            return { ok: true, value: [{ id: 'test-prov-0001', activityDateTime: '2026-01-01T00:00:00Z',
                                         changeId: 'test-change-0001' }] };
        return this._graph('GET', '/auditLogs/provisioning?$filter=' +
                                  "servicePrincipal/id eq '" + servicePrincipalId + "'" +
                                  ' and activityDateTime ge ' + sinceIso, null);
    },

    // --- Evidence: provisioning + sign-in telemetry to the SIEM (AU-2). ------
    // Routed at onboarding, not retrofitted after an incident. Both halves are
    // fetched and their results folded together: sign-in logs without provisioning
    // logs cannot answer "who was granted this and when", and the pair is the point.
    // Also a read — automated is fine.
    collectTelemetry: function (servicePrincipalId, sinceIso) {
        if (this.testMode)
            return { ok: true, signIns: [], provisioning: [], boundaryLimited: true };
        var signIns = this._graph('GET', '/auditLogs/signIns?$filter=' +
                                         "appId eq '" + servicePrincipalId + "'" +
                                         ' and createdDateTime ge ' + sinceIso, null);
        var prov = this.getProvisioningAuditEvents(servicePrincipalId, sinceIso);
        // Partial collection is not collection — say so rather than ship half the
        // evidence to the SIEM and call AU-2 closed.
        return { ok: signIns.ok && prov.ok, signIns: signIns.body, provisioning: prov.body,
                 signInStatus: signIns.status,
                 reason: (signIns.ok && prov.ok) ? 'collected' :
                         'partial collection — AU-2 not closed on a partial read' };
    },

    // --- Exit: terminate the integration and revoke the trust (AC-2). --------
    // The most-skipped step in the lane: an integration nobody uses still holds a
    // live directory replica and a valid signing certificate. Triggered by
    // attestation failure, business-need lapse, or a WITHDRAWN FedRAMP
    // authorization (saas.attest -> here).
    //
    // Order is deliberate: stop the replica FIRST, then remove access. Disabling
    // the sync job before pulling assignments means the last thing that happens is
    // not a burst of deprovisioning traffic through a job that is about to die
    // half-finished. Credential revocation is AcmeCredentialClient's; vendor-side
    // deletion is confirmed against the retention record by a human — Graph cannot
    // see inside the vendor's cloud, and this method does not pretend otherwise.
    offboardIntegration: function (servicePrincipalId, syncJobId) {
        if (this.testMode)
            return { ok: true, id: servicePrincipalId, syncJobDisabled: true,
                     servicePrincipalDisabled: true, vendorDeletionConfirmed: false };
        var job = this._graph('DELETE', '/servicePrincipals/' + servicePrincipalId +
                                        '/synchronization/jobs/' + syncJobId, null);
        var sp = this._graph('PATCH', '/servicePrincipals/' + servicePrincipalId,
                             { accountEnabled: false });
        return { ok: job.ok && sp.ok, id: servicePrincipalId,
                 syncJobDisabled: job.ok, servicePrincipalDisabled: sp.ok,
                 // Not a Graph-observable fact. Left false so nobody reads a 200
                 // here as proof the vendor deleted the replica.
                 vendorDeletionConfirmed: false };
    },

    // --- Internal: MID-routed Graph call via the credential alias. ------------
    _graph: function (method, path, body) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_ssa_day2_ops.graph', method);
            rm.setStringParameterNoEscape('graph_version', this.graphVersion);
            rm.setEndpoint('https://graph.microsoft.com/' + this.graphVersion + path);
            if (this.midServer) rm.setMIDServer(this.midServer);   // in-boundary execution
            if (body !== null && body !== undefined) rm.setRequestBody(JSON.stringify(body));
            var resp = rm.execute();
            var code = resp.getStatusCode();
            return { ok: code >= 200 && code < 300, status: code, body: resp.getBody() };
        } catch (e) {
            this.log.logErr('_graph ' + method + ' ' + path + ' failed: ' + e);
            return { ok: false, error: '' + e };
        }
    },

    type: 'EntraSaasClient'
};
