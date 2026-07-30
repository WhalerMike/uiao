// Script Include: ComplianceGate  (application scope: x_fed_compliance)
// -----------------------------------------------------------------------------
// Step 5 of the loop (close + evidence): closure is proven by OBSERVATION, not
// by the remediation reporting success. After native actuation, the gate
// re-reads the same surface ComplianceIngest read, confirms the drift is gone,
// and stamps a re-test evidence record on the task (CA-7). A task whose re-read
// still shows drift is NOT closed — it escalates, and a breached SLA opens a
// POA&M item (CA-5, attest.poam.item).
//
// Also enforces the two invariants shared with the day-2 app:
//   * SEPARATION OF DUTIES — requester != approver; a self-approved
//     compliance change is a hard preflight fail.
//   * READ-ONLY SERVICE IDENTITY — if the identity is detected holding write
//     scopes over the governed estate, the gate refuses to run at all: the
//     app's authority to attest depends on its inability to actuate.
// -----------------------------------------------------------------------------
var ComplianceGate = Class.create();
ComplianceGate.prototype = {

    initialize: function () {
        this.ingest = new x_fed_compliance.ComplianceIngest();
        // Scoped logging via gs.* (a scoped app cannot `new GSLog(...)` a global
        // Script Include unprefixed; gs.error/warn always resolve).
        this.log = {
            err: function (m) { gs.error('[x_fed_compliance.ComplianceGate] ' + m); },
            warn: function (m) { gs.warn('[x_fed_compliance.ComplianceGate] ' + m); }
        };
        this.testMode = gs.getProperty('x_fed_compliance.test_mode', 'false') === 'true';
    },

    // Safety gate — run BEFORE any task is worked. Returns {ok, reason}. FAIL CLOSED.
    preflight: function (task) {
        // CM-5: missing either id is indeterminate, not a pass.
        if (!task.requester_id || !task.approver_id)
            return { ok: false, reason: 'separation of duties indeterminate: requester/approver not populated' };
        if (task.requester_id === task.approver_id)
            return { ok: false, reason: 'separation of duties: requester may not approve (self-approval refused)' };
        // The app's authority to ATTEST depends on its inability to ACTUATE. An
        // UNVERIFIED read-only check is treated exactly like a failure — the gate
        // must not proceed as if it confirmed something it never checked.
        var scope = this._identityWriteScopeStatus();
        if (scope !== 'confirmed-readonly')
            return { ok: false, reason: 'read-only-identity check is ' + scope +
                     ' — attestation authority void until affirmatively confirmed read-only' };
        return { ok: true, reason: 'preflight clear' };
    },

    // Closure-by-observation. Returns {closed, evidence}. FAIL CLOSED on every
    // branch that is not an AFFIRMATIVE observation of compliance:
    //   * a READ_FAILED sentinel in the readings -> RETEST_INCONCLUSIVE
    //   * the asset absent from the re-read       -> RETEST_INCONCLUSIVE
    //   * observed != intended                    -> RETEST_FAILED
    //   * observed == intended                    -> RETEST_PASSED (the only close)
    // The old version inferred closure from ABSENCE of a drift reading, so a
    // failed re-read (which returns no drift row) looked like success. (Sweep H.)
    verify: function (task) {
        var readings = (task.surface === 'azure') ? this.ingest.ingestAzure() : this.ingest.ingestM365();

        for (var i = 0; i < readings.length; i++) {
            if (readings[i].observed === 'READ_FAILED') {
                this.log.warn('re-read failed for task ' + task.number + ' — inconclusive, not closing');
                return { closed: false, evidence: this._stamp(task, 'RETEST_INCONCLUSIVE', readings[i]) };
            }
        }
        var seen = null;
        for (var j = 0; j < readings.length; j++) {
            if (readings[j].asset === task.asset) { seen = readings[j]; break; }
        }
        if (!seen) {
            return { closed: false, evidence: this._stamp(task, 'RETEST_INCONCLUSIVE',
                     { asset: task.asset, observed: 'NOT_OBSERVED', intended: task.intended }) };
        }
        if (seen.observed !== seen.intended) {
            return { closed: false, evidence: this._stamp(task, 'RETEST_FAILED', seen) };
        }
        return { closed: true, evidence: this._stamp(task, 'RETEST_PASSED', seen) };
    },

    // The evidence record (CA-7): what was re-read, when, verdict. Feeds the
    // Book 04 attestation stream and the KSI pipeline (attest.conmon.rollup).
    _stamp: function (task, verdict, reading) {
        return {
            task: task.number, asset: task.asset, verdict: verdict,
            observed: reading ? reading.observed : null,
            retested_at: new GlideDateTime().getValue(),
            boundary: gs.getProperty('x_fed_compliance.boundary', 'gcc-moderate')
        };
    },

    // Returns 'confirmed-readonly' | 'holds-write' | 'unverified'. The gate closes
    // on 'confirmed-readonly' only; 'unverified' fails closed exactly like
    // 'holds-write'. The old _identityHoldsWrite() returned false unconditionally
    // in production, so the write-scope refusal existed ONLY under test_mode — a
    // stub that gave false assurance the identity was read-only. (Sweep H.)
    _identityWriteScopeStatus: function () {
        if (this.testMode) {
            return gs.getProperty('x_fed_compliance.test_fixture_write_scopes', 'false') === 'true'
                ? 'holds-write' : 'confirmed-readonly';
        }
        // Production: implemented per tenant — read the app registration's granted
        // appRoleAssignments / oauth2PermissionGrants via Graph and confirm no
        // *.ReadWrite.* over the governed surfaces, then return
        // 'confirmed-readonly' or 'holds-write'. Until that read is wired to the
        // tenant (guarded by scope_check_enabled), the status is UNVERIFIED and the
        // gate fails closed — it never assumes read-only it did not confirm.
        if (gs.getProperty('x_fed_compliance.scope_check_enabled', 'false') !== 'true') {
            return 'unverified';
        }
        return this._checkWriteScope();
    },

    // SER-4: the live Graph scope read. Confirms the app registration's OWN
    // service principal (x_fed_compliance.service_principal_id) holds no
    // write-shaped grant, over EITHER surface Graph exposes a grant on:
    //   * appRoleAssignments      — application (app-only) permissions. The
    //     assignment record itself only carries an appRoleId (a GUID); the
    //     human-readable permission string ("Directory.ReadWrite.All") lives
    //     on the RESOURCE service principal's own appRoles collection, so
    //     each distinct resourceId is resolved once via _resolveAppRoleValue.
    //   * oauth2PermissionGrants  — delegated permissions, already carried as
    //     human-readable space-delimited scope strings on `.scope`.
    // Same discipline as preflight/verify above: ANY read failure, missing
    // config, unparseable body, or response shape that isn't the array this
    // method expects returns 'unverified', never a default 'confirmed-readonly'.
    // A failed read must never look like a clean posture.
    _checkWriteScope: function () {
        if (this.testMode) return this._checkWriteScopeFixture();

        var spId = gs.getProperty('x_fed_compliance.service_principal_id', '');
        if (!spId) {
            this.log.err('scope check enabled but x_fed_compliance.service_principal_id is not set — unverified');
            return 'unverified';
        }

        var appRoleAssignments = this._graphGet('/v1.0/servicePrincipals/' + spId + '/appRoleAssignments');
        var delegatedGrants = this._graphGet("/v1.0/oauth2PermissionGrants?$filter=clientId eq '" + spId + "'");
        if (!Array.isArray(appRoleAssignments) || !Array.isArray(delegatedGrants)) {
            this.log.err('scope check: Graph read failed or returned an unexpected shape — unverified');
            return 'unverified';
        }

        var resourceAppRolesCache = {};
        for (var i = 0; i < appRoleAssignments.length; i++) {
            var grant = appRoleAssignments[i];
            if (!grant || !grant.resourceId || !grant.appRoleId) {
                this.log.err('scope check: appRoleAssignment missing resourceId/appRoleId — unverified');
                return 'unverified';
            }
            if (!resourceAppRolesCache.hasOwnProperty(grant.resourceId)) {
                var resourceSp = this._graphGet('/v1.0/servicePrincipals/' + grant.resourceId + '?$select=appRoles');
                if (!resourceSp || !Array.isArray(resourceSp.appRoles)) {
                    this.log.err('scope check: could not resolve appRoles for resource ' + grant.resourceId + ' — unverified');
                    return 'unverified';
                }
                resourceAppRolesCache[grant.resourceId] = resourceSp.appRoles;
            }
            var roleValue = this._resolveAppRoleValue(resourceAppRolesCache[grant.resourceId], grant.appRoleId);
            if (roleValue === null) {
                this.log.err('scope check: appRoleId ' + grant.appRoleId + ' not found on resource ' +
                              grant.resourceId + ' — unverified');
                return 'unverified';
            }
            if (this._isWriteShaped(roleValue)) return 'holds-write';
        }

        for (var j = 0; j < delegatedGrants.length; j++) {
            var scopeStr = (delegatedGrants[j] && delegatedGrants[j].scope) || '';
            var scopes = scopeStr.split(/\s+/);
            for (var k = 0; k < scopes.length; k++) {
                if (scopes[k] && this._isWriteShaped(scopes[k])) return 'holds-write';
            }
        }

        return 'confirmed-readonly';
    },

    // test_mode fixture path for _checkWriteScope — deterministic, no tenant
    // credentials, same discipline as ComplianceIngest._fixture. Drives the
    // SAME _isWriteShaped matching logic production uses, from a JSON fixture
    // property (x_fed_compliance.test_fixture_scope_grants) shaped like:
    //   {"appRoleAssignments": ["Directory.Read.All"], "delegatedScopes": ["User.Read"]}
    // A missing/unparseable fixture fails closed to 'unverified' rather than
    // defaulting to a clean posture.
    _checkWriteScopeFixture: function () {
        var raw = gs.getProperty('x_fed_compliance.test_fixture_scope_grants', '');
        var fixture;
        try {
            fixture = raw ? JSON.parse(raw) : { appRoleAssignments: [], delegatedScopes: [] };
        } catch (e) {
            this.log.err('scope check fixture unparseable — unverified: ' + e);
            return 'unverified';
        }
        var roles = fixture.appRoleAssignments || [];
        for (var i = 0; i < roles.length; i++) {
            if (this._isWriteShaped(roles[i])) return 'holds-write';
        }
        var scopes = fixture.delegatedScopes || [];
        for (var j = 0; j < scopes.length; j++) {
            if (this._isWriteShaped(scopes[j])) return 'holds-write';
        }
        return 'confirmed-readonly';
    },

    // Judgment call (verify against how this instance is actually wired):
    // Graph's write-shaped permission names are not exclusively *.ReadWrite.* —
    // this also catches the *.Write.*, *.FullControl.* and *.Manage.* shapes
    // (e.g. Mail.Write, Sites.FullControl.All, Sites.Manage.All) since those are
    // write-capable grants a read-only compliance checker must not hold either.
    // Deliberately does NOT scope the check to only the surfaces this app reads
    // (Directory/Policy/SecurityEvents) — ANY write-shaped grant on the identity
    // disqualifies it, on the theory that a supposedly read-only checker holding
    // write ANYWHERE is itself the confused-deputy risk this guard exists for.
    // Also out of scope: delegated grants like Directory.AccessAsUser.All, which
    // carry no "Write" in the name but inherit whatever rights the signed-in user
    // has — a real gap, not caught by name-shape matching.
    _isWriteShaped: function (permissionName) {
        return /(\.|^)(ReadWrite|Write|FullControl|Manage)(\.|$)/.test(String(permissionName || ''));
    },

    // Resolve an appRoleId (GUID) granted via appRoleAssignments to its
    // human-readable permission string, from the RESOURCE service principal's
    // own appRoles collection (the assignment record itself never carries the
    // readable value). Returns null — not a guess — if the id isn't found.
    _resolveAppRoleValue: function (appRolesList, appRoleId) {
        for (var i = 0; i < appRolesList.length; i++) {
            if (appRolesList[i] && appRolesList[i].id === appRoleId) {
                return appRolesList[i].value || null;
            }
        }
        return null;
    },

    // One outbound Graph GET, MID-routed via the same credential alias and
    // calling convention ComplianceIngest._rest already uses (rest/README.md:
    // x_fed_compliance.graph, GET method named 'get', ${path} string parameter).
    // Returns the parsed `.value` collection (Graph's OData list shape) when
    // present, else the parsed body itself (a single-resource GET); returns
    // null — never [] or {} — on ANY failure, so a failed read can never be
    // mistaken by a caller for an empty, clean grant list.
    _graphGet: function (path) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_fed_compliance.graph', 'get');
            rm.setStringParameterNoEscape('path', path);
            var midServer = gs.getProperty('x_fed_compliance.mid_server', '');
            if (midServer) rm.setMIDServer(midServer);
            var resp = rm.execute();
            if (resp.getStatusCode() !== 200) {
                this.log.err('scope check read failed ' + path + ' -> ' + resp.getStatusCode());
                return null;
            }
            var parsed = JSON.parse(resp.getBody());
            if (parsed && parsed.hasOwnProperty('value')) return parsed.value;
            return parsed;
        } catch (e) {
            this.log.err('scope check read exception on ' + path + ': ' + e);
            return null;
        }
    },

    type: 'ComplianceGate'
};
