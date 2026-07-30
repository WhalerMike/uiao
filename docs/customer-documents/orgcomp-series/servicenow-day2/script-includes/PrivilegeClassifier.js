// Script Include: PrivilegeClassifier  (application scope: x_fed_day2_ops)
// =============================================================================
// NEW — one privilege classifier for BOTH legs. Closes P1-1, NEW-2, NEW-3.
//
// The problem it replaces: there were two divergent classifiers with different
// keying and different blind spots.
//   * EntraHelpdeskGate._classifyPrivileged compared a GUID against a GUID
//     allowlist — so it structurally could not classify an AD-leg target, whose
//     identifier is a samAccountName or DN. AD-leg grants silently fell back to
//     the requester's self-declared checkbox.
//   * AdHybridClient._isProtectedGroup did case-insensitive SUBSTRING matching
//     on group NAMES — defeated by a renamed group or a non-English domain,
//     noisy on legitimate names ("Regional Administrators"), and blind to
//     nesting.
// Neither expanded transitive membership, which is the standard escalation
// path: grant into Helpdesk-Tier1, which is itself a member of Account
// Operators, and no name check fires.
//
// TRI-STATE BY DESIGN. Callers get one of:
//   'privileged'               — the target is privileged; enforce AC-6
//   'confirmed-unprivileged'   — affirmatively checked and clean
//   'inconclusive'             — could not be resolved
// 'inconclusive' must be treated as 'privileged' by any gate. An unclassifiable
// target is not a safe target; the old code's fallthrough-to-false is the bug
// this shape exists to prevent.
//
// Configuration:
//   x_fed_day2_ops.privileged_role_template_ids   Entra directory role template GUIDs
//   x_fed_day2_ops.privileged_group_ids           Entra group object GUIDs
//   x_fed_day2_ops.privileged_ad_rids             well-known RIDs (defaults below)
//   x_fed_day2_ops.privileged_ad_sids             extra full SIDs (custom Tier-0)
// =============================================================================
var PrivilegeClassifier = Class.create();

// Well-known RIDs. These are the stable identifiers — group NAMES are not, which
// is the whole reason the previous name-matching check was inadequate.
// 512 Domain Admins · 519 Enterprise Admins · 518 Schema Admins
// 544 Administrators · 548 Account Operators · 549 Server Operators
// 550 Print Operators · 551 Backup Operators · 552 Replicator
// 516 Domain Controllers · 521 Read-only Domain Controllers
// 520 Group Policy Creator Owners · 517 Cert Publishers
// 526 Key Admins · 527 Enterprise Key Admins
PrivilegeClassifier.DEFAULT_RIDS = '512,516,517,518,519,520,521,526,527,544,548,549,550,551,552';

PrivilegeClassifier.prototype = {

    initialize: function () {
        this.env = new x_fed_day2_ops.Day2Env();
        this.log = {
            warn: function (m) { gs.warn('[x_fed_day2_ops.PrivilegeClassifier] ' + Day2Env.scrub(m)); }
        };
        this._adCache = {};
    },

    // -------------------------------------------------------------------------
    // Entry point used by the gate. Accepts whatever identifiers the request
    // carries and returns the strongest verdict any of them produces.
    // request: { role_template_id, groupId, target_id, ad_group, actuation_leg }
    // -------------------------------------------------------------------------
    classifyRequest: function (request) {
        request = request || {};
        var verdicts = [];
        var attempted = false;

        if (request.ad_group || request.actuation_leg === 'ad') {
            var g = request.ad_group || request.groupId || request.target_id;
            if (g) { attempted = true; verdicts.push(this.classifyAdGroup(g)); }
        }
        var cloudTarget = request.role_template_id || request.groupId || request.target_id;
        if (cloudTarget) { attempted = true; verdicts.push(this.classifyCloudTarget(cloudTarget)); }

        // No group_id / role_template_id / target_id / ad_group on the request
        // at all is NOT the same failure as "one of those was supplied but
        // couldn't be resolved" -- most governed actions (password reset, MFA
        // reset, disable, create, attribute changes) are not privilege GRANTS
        // in the first place and legitimately carry none of these fields.
        // Treating "nothing to classify" as inconclusive-therefore-privileged
        // would require every such action to carry an AC-6 expiry, which is
        // not what AC-6 is about. Reserve 'inconclusive' for a classification
        // that was actually attempted (a target field was present) and failed
        // to resolve -- that is the case this shape exists to fail closed on.
        if (!attempted) {
            return { status: 'confirmed-unprivileged',
                     reason: 'request carries no group/role target (role_template_id, groupId, target_id, ad_group) — not a privilege-grant action' };
        }
        if (!verdicts.length) {
            return { status: 'inconclusive',
                     reason: 'a classifiable target was present but produced no verdict — treat as privileged' };
        }
        // Strongest wins: privileged > inconclusive > confirmed-unprivileged.
        for (var i = 0; i < verdicts.length; i++) if (verdicts[i].status === 'privileged') return verdicts[i];
        for (var j = 0; j < verdicts.length; j++) if (verdicts[j].status === 'inconclusive') return verdicts[j];
        return verdicts[0];
    },

    // -------------------------------------------------------------------------
    // Cloud side — exact GUID match against the configured allowlists.
    // -------------------------------------------------------------------------
    classifyCloudTarget: function (targetId) {
        var t = ('' + targetId).trim().toLowerCase();
        if (!t) return { status: 'inconclusive', reason: 'empty cloud target' };

        var ids = (gs.getProperty('x_fed_day2_ops.privileged_role_template_ids', '') + ',' +
                   gs.getProperty('x_fed_day2_ops.privileged_group_ids', '')).split(',');
        var configured = false;
        for (var i = 0; i < ids.length; i++) {
            var id = ids[i].trim().toLowerCase();
            if (!id) continue;
            configured = true;
            if (id === t) return { status: 'privileged', target: targetId, reason: 'target is on the privileged allowlist' };
        }
        if (!configured) {
            return { status: 'inconclusive',
                     reason: 'no privileged_role_template_ids / privileged_group_ids configured — cannot classify' };
        }
        return { status: 'confirmed-unprivileged', target: targetId, reason: 'not on the privileged allowlist' };
    },

    // -------------------------------------------------------------------------
    // AD side — resolve to SID, expand transitive membership, compare RIDs.
    // Never matches on name.
    // -------------------------------------------------------------------------
    classifyAdGroup: function (groupIdentity) {
        var key = ('' + groupIdentity).trim().toLowerCase();
        if (!key) return { status: 'inconclusive', reason: 'empty AD group identity' };
        if (this._adCache[key]) return this._adCache[key];

        var verdict;
        if (this.env.isTestMode()) {
            // Fixture supplies an INPUT (is this fixture group privileged?), not
            // an observation of the live directory.
            verdict = this.env.testFixture('privileged_ad_group', false) === true
                ? { status: 'privileged', target: groupIdentity, reason: 'test fixture: privileged group' }
                : { status: 'confirmed-unprivileged', target: groupIdentity, reason: 'test fixture: unprivileged group' };
            this._adCache[key] = verdict;
            return verdict;
        }

        var ad = new x_fed_day2_ops.AdHybridClient();
        var d = ad.getUserAd(groupIdentity, ['objectSid', 'memberOf', 'tokenGroups']);
        if (!d.ok) {
            verdict = { status: 'inconclusive', target: groupIdentity,
                        reason: 'AD read could not be dispatched — target unclassifiable, treat as privileged' };
            this._adCache[key] = verdict;
            return verdict;
        }
        var res = ad.awaitDispatch(d.ecc_sys_id);
        if (!res.ok || !res.data) {
            verdict = { status: 'inconclusive', target: groupIdentity,
                        reason: 'AD read inconclusive (' + (res.reason || 'no data') + ') — treat as privileged' };
            this._adCache[key] = verdict;
            return verdict;
        }

        // The MID wrapper returns the group's own SID plus the SIDs of every
        // group it is transitively a member of. Nesting is therefore covered.
        var sids = [];
        if (res.data.objectSid) sids.push(res.data.objectSid);
        var nested = res.data.transitiveMemberOfSids || [];
        for (var n = 0; n < nested.length; n++) sids.push(nested[n]);

        if (!sids.length) {
            verdict = { status: 'inconclusive', target: groupIdentity,
                        reason: 'AD read returned no SID — unclassifiable, treat as privileged' };
            this._adCache[key] = verdict;
            return verdict;
        }

        var hit = this._matchPrivilegedSid(sids);
        verdict = hit
            ? { status: 'privileged', target: groupIdentity, matched: hit,
                reason: 'resolves to (or is nested under) a privileged SID: ' + hit }
            : { status: 'confirmed-unprivileged', target: groupIdentity,
                reason: 'SID and all transitive parents checked; none privileged' };
        this._adCache[key] = verdict;
        return verdict;
    },

    _matchPrivilegedSid: function (sids) {
        var rids = gs.getProperty('x_fed_day2_ops.privileged_ad_rids', PrivilegeClassifier.DEFAULT_RIDS).split(',');
        var extraSids = gs.getProperty('x_fed_day2_ops.privileged_ad_sids', '').split(',');

        for (var i = 0; i < sids.length; i++) {
            var sid = ('' + sids[i]).trim();
            if (!sid) continue;

            for (var x = 0; x < extraSids.length; x++) {
                var ex = extraSids[x].trim();
                if (ex && ex.toLowerCase() === sid.toLowerCase()) return sid;
            }
            var parts = sid.split('-');
            var rid = parts[parts.length - 1];
            for (var r = 0; r < rids.length; r++) {
                if (rids[r].trim() === rid) return sid;
            }
        }
        return null;
    },

    type: 'PrivilegeClassifier'
};
