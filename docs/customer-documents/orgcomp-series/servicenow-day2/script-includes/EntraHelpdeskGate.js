// Script Include: EntraHelpdeskGate  (application scope: x_fed_day2_ops)
// =============================================================================
// REMEDIATED BUILD.
//
//   P1-1 / NEW-3  Privilege classification moved out to PrivilegeClassifier, so
//                 both legs use one implementation with one keying scheme.
//                 'inconclusive' is now treated as privileged — the previous
//                 fallthrough returned false for anything it could not classify,
//                 which is the wrong direction for a safety gate.
//
//   P0-4          verify() is leg-aware. An AD-leg action is verified by
//                 re-reading AD on the pinned DC; the Entra projection is
//                 recorded SEPARATELY as a sync-latency-tolerant reconciliation
//                 and is never the closure assertion. Previously AD-leg writes
//                 had no post-state assertion at all while the Entra read raced
//                 Entra Connect sync.
//
//   NEW-6         Membership is asserted DIRECTLY. checkMemberGroups evaluates
//                 TRANSITIVE membership, so it returned true when the user was
//                 a member via nesting even if the intended direct add failed —
//                 a false pass in the closure-by-observation step.
//
//   P0-5          test_mode goes through Day2Env, and a verify under test_mode
//                 is marked synthetic rather than returning a bare pass.
// =============================================================================
var EntraHelpdeskGate = Class.create();
EntraHelpdeskGate.prototype = {

    initialize: function () {
        this.client = new x_fed_day2_ops.EntraHelpdeskClient();
        this.env = new x_fed_day2_ops.Day2Env();
        this.testMode = this.env.isTestMode();
        this.log = {
            err:  function (m) { gs.error('[x_fed_day2_ops.EntraHelpdeskGate] ' + Day2Env.scrub(m)); },
            warn: function (m) { gs.warn('[x_fed_day2_ops.EntraHelpdeskGate] ' + Day2Env.scrub(m)); }
        };
    },

    _truthy: function (v) { return v === true || v === 'true'; },

    // --- Safety gate — BEFORE actuation. FAIL CLOSED. ------------------------
    preflight: function (request) {
        request = request || {};

        var guard = this.env.guard();          // P0-5
        if (!guard.ok) return { ok: false, reason: guard.reason };

        // CM-5 separation of duties. Missing either id is INDETERMINATE.
        if (!request.requester_id || !request.approver_id)
            return { ok: false, reason: 'SoD indeterminate: requester/approver not populated (CM-5)' };
        if (request.requester_id === request.approver_id)
            return { ok: false, reason: 'SoD violation: requester == approver (CM-5)' };

        // AC-6 least privilege. Server-derived classification ORs with the
        // self-declared flag: a client-supplied false can never suppress it.
        var verdict = new x_fed_day2_ops.PrivilegeClassifier().classifyRequest(request);
        var declared = this._truthy(request.privileged);
        var privileged = declared || verdict.status === 'privileged' || verdict.status === 'inconclusive';

        if (privileged && !request.expiry) {
            return { ok: false,
                     reason: 'Least privilege: privileged grant requires an expiry (AC-6) [classification: ' +
                             verdict.status + ' — ' + verdict.reason + ']',
                     classification: verdict.status };
        }
        return { ok: true, reason: 'preflight ok', classification: verdict.status, privileged: privileged };
    },

    // --- Verify gate — AFTER actuation. -------------------------------------
    // FAIL CLOSED on every branch that is not an affirmative observation.
    // verifyArgs.leg is set by the orchestrator from the SERVER-DERIVED routing
    // decision, never from caller input (see MacdrOrchestrator NEW-1).
    verify: function (action, target, leg) {
        target = target || {};
        if (this.testMode) {
            return { ok: true, synthetic: true,
                     evidence: { action: action, target: target, verified: true,
                                 note: 'test_mode: synthetic verdict, not an observation' } };
        }
        return (leg === 'ad') ? this._verifyAd(action, target) : this._verifyGraph(action, target);
    },

    // -------- AD leg: observe on the pinned DC (P0-4) ------------------------
    _verifyAd: function (action, target) {
        var ad = new x_fed_day2_ops.AdHybridClient();

        if (action === 'addGroupMember' || action === 'removeGroupMember') {
            var isMember = ad.isGroupMemberAd(target.groupId, target.userId, false);
            if (isMember === null)
                return { ok: false, evidence: { action: action, leg: 'ad',
                         reason: 'AD membership re-read inconclusive — not closed' } };
            var want = (action === 'addGroupMember');
            return { ok: isMember === want,
                     evidence: { action: action, leg: 'ad', asserted: isMember === want,
                                 observed_member: isMember,
                                 entra_projection: this._projectionNote(target.userId) } };
        }

        var d = ad.getUserAd(target.identity || target.userId,
                             ['distinguishedName', 'enabled', 'userAccountControl', 'pwdLastSet']);
        if (!d.ok)
            return { ok: false, evidence: { action: action, leg: 'ad',
                     reason: 'AD re-read could not be dispatched — inconclusive, not closed' } };

        var res = ad.awaitDispatch(d.ecc_sys_id);
        if (!res.ok || !res.data)
            return { ok: false, evidence: { action: action, leg: 'ad',
                     reason: 'AD re-read inconclusive: ' + (res.reason || 'no data') } };

        var u = res.data, asserted;
        switch (action) {
            case 'disableUser':   asserted = (u.enabled === false); break;
            case 'createUser':    asserted = !!u.distinguishedName; break;
            case 'resetPassword': asserted = (('' + u.pwdLastSet) === '0'); break;   // must-change-at-logon
            case 'moveOu':        asserted = !!u.distinguishedName &&
                                   ('' + u.distinguishedName).toLowerCase().indexOf(('' + (target.targetOu || '')).toLowerCase()) !== -1;
                                  break;
            case 'setAttributes': asserted = this._attributesMatch(u, target.expected || {}); break;
            default:
                return { ok: false, evidence: { action: action, leg: 'ad',
                         reason: 'no AD post-state assertion defined for action — verification inconclusive' } };
        }
        return { ok: !!asserted,
                 evidence: { action: action, leg: 'ad', asserted: !!asserted, dc: res.dc,
                             observed_at: res.observed_at,
                             entra_projection: this._projectionNote(target.userId) } };
    },

    _attributesMatch: function (observed, expected) {
        for (var k in expected) {
            if (!expected.hasOwnProperty(k)) continue;
            if (('' + observed[k]) !== ('' + expected[k])) return false;
        }
        return true;
    },

    // The Entra side of an AD-leg write is a PROJECTION, not the closure. It
    // lands on the next Entra Connect cycle, so a mismatch here is expected and
    // must never fail the task. Recorded for reconciliation only.
    _projectionNote: function (userId) {
        if (!userId) return { status: 'not-checked' };
        var r = this.client._graph('GET', '/users/' + userId, null);
        if (!r.ok) return { status: 'unavailable', note: 'Entra projection not read; sync latency is expected' };
        var u;
        try { u = JSON.parse(r.body) || {}; }
        catch (e) { return { status: 'unparseable' }; }
        return { status: 'observed', accountEnabled: u.accountEnabled,
                 note: 'projection only — not the closure assertion (Entra Connect latency)' };
    },

    // -------- Graph leg ------------------------------------------------------
    _verifyGraph: function (action, target) {
        if (action === 'addGroupMember' || action === 'removeGroupMember') {
            var m = this._isDirectMember(target.groupId, target.userId);
            if (m === null)
                return { ok: false, evidence: { action: action, leg: 'graph',
                         reason: 'membership re-read inconclusive — not closed' } };
            var want = (action === 'addGroupMember');
            return { ok: m === want,
                     evidence: { action: action, leg: 'graph', asserted: m === want, observed_member: m } };
        }

        var r = this.client._graph('GET', '/users/' + target.userId, null);
        if (!r.ok)
            return { ok: false, evidence: { action: action, leg: 'graph', status: r.status,
                     reason: 're-read failed — inconclusive, not closed' } };
        var user;
        try { user = JSON.parse(r.body) || {}; }
        catch (e) { return { ok: false, evidence: { action: action, leg: 'graph',
                             reason: 're-read unparseable — inconclusive' } }; }

        var asserted;
        switch (action) {
            case 'disableUser':   asserted = (user.accountEnabled === false); break;
            case 'createUser':    asserted = !!user.id; break;
            case 'assignLicense': asserted = this._hasLicense(user, target.skuId); break;
            default:
                return { ok: false, evidence: { action: action, leg: 'graph',
                         reason: 'no post-state assertion for action — verification inconclusive' } };
        }
        return { ok: !!asserted,
                 evidence: { action: action, leg: 'graph', asserted: !!asserted,
                             accountEnabled: user.accountEnabled } };
    },

    _hasLicense: function (user, skuId) {
        var lic = (user && user.assignedLicenses) || [];
        for (var i = 0; i < lic.length; i++) { if (lic[i].skuId === skuId) return true; }
        return false;
    },

    // NEW-6: DIRECT membership only. checkMemberGroups is transitive and would
    // pass on a nested membership the actuation did not create.
    // Tri-state: true / false / null (inconclusive).
    _isDirectMember: function (groupId, userId) {
        if (!groupId || !userId) return null;
        var path = '/groups/' + groupId + "/members?$select=id&$filter=id eq '" + userId + "'";
        var r = this.client._graph('GET', path, null);
        if (!r.ok) return null;
        try {
            var body = JSON.parse(r.body) || {};
            var vals = body.value || [];
            for (var i = 0; i < vals.length; i++) { if (vals[i].id === userId) return true; }
            return false;
        } catch (e) { return null; }
    },

    type: 'EntraHelpdeskGate'
};
