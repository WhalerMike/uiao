// Script Include: AdHybridClient  (application scope: x_fed_day2_ops)
// =============================================================================
// REMEDIATED BUILD — replaces the string-rendering skeleton.
//
// What changed and why (external security review Rev 1/Rev 2):
//
//   P0-1  Command injection. The old _render() interpolated caller-supplied
//         parameter NAMES into a PowerShell command string unescaped. There is
//         no command string here any more: _dispatch() emits a structured JSON
//         payload that mid/Invoke-Day2AdAction.ps1 binds via splatting. Nothing
//         a caller supplies is ever concatenated into executable text.
//
//   P0-2  Target substitution. The old _merge() let a caller-supplied attribute
//         bag override the approved `Identity`. Reserved parameters are now
//         rejected outright if they appear in caller input (_assertNoReserved),
//         and are applied by this class AFTER validation, never merged from the
//         caller side.
//
//   P0-3  Cleartext credential. setPasswordAd() no longer accepts or transports
//         a password. The MID wrapper generates it, applies it as a SecureString
//         and returns only a delivery handle; ecc_queue never holds secret
//         material. opts.tempPassword is explicitly REFUSED so old callers fail
//         loudly rather than silently leaking.
//
//   P0-4  No verification. Read-back methods now exist (getUserAd,
//         getGroupMembersAd, isGroupMemberAd) against the pinned DC, plus
//         resolveDispatch() to read the ECC response record. A write returns
//         { ok, dispatched, ecc_sys_id } and NEVER asserts post-state.
//
//   NEW-2 Protected-group deny-list was name/substring based, missed nesting,
//         and did not guard removal. Classification now lives in
//         PrivilegeClassifier (SID + transitive), and BOTH add and remove are
//         gated.
//
//   P1-3  createUserAd's target OU is now validated against the same allowlist
//         moveUserOuAd uses.
//
// Boundary discipline is unchanged: a domain-joined, in-boundary MID Server,
// a delegated least-privilege service account (NEVER Domain Admin — still
// asserted here and still requiring an effective-permissions dump to verify),
// and a pinned writable DC so write and read-back are replication-consistent.
// =============================================================================
var AdHybridClient = Class.create();

// --- Parameter contracts -----------------------------------------------------
// Every action declares exactly which caller-supplied keys are permitted. An
// unknown key is a refusal, not a pass-through. This is the allowlist that
// replaces escaping: nothing outside these names can reach the MID at all.
AdHybridClient.ACTIONS = {
    'create-user':      { allowed: ['samAccountName', 'upn', 'givenName', 'surname', 'displayName', 'ou'],
                          required: ['samAccountName', 'upn', 'ou'] },
    'disable-user':     { allowed: [], required: [] },
    'move-object':      { allowed: ['targetOu'], required: ['targetOu'] },
    'set-attributes':   { allowed: ['title', 'department', 'company', 'description', 'office',
                                    'telephoneNumber', 'mobile', 'manager', 'employeeId',
                                    'employeeType', 'streetAddress', 'city', 'state',
                                    'postalCode', 'country', 'givenName', 'surname',
                                    'displayName', 'extensionAttribute1', 'extensionAttribute2',
                                    'extensionAttribute3', 'extensionAttribute4',
                                    'extensionAttribute5'],
                          required: [] },
    'reset-password':   { allowed: ['mustChangeAtLogon', 'deliveryRef'], required: [] },
    'add-group-member': { allowed: ['group'], required: ['group'] },
    'remove-group-member': { allowed: ['group'], required: ['group'] },
    'get-user':         { allowed: ['properties'], required: [] },
    'get-group-members': { allowed: ['group', 'recursive'], required: ['group'] }
};

// Parameters this class controls. A caller may never supply them — supplying one
// is treated as an attempted target/transport override and refused.
AdHybridClient.RESERVED = ['identity', 'server', 'credential', 'path', 'confirm',
                           'reset', 'newpassword', 'passthru', 'authtype', 'partition'];

AdHybridClient.prototype = {

    initialize: function () {
        this.midServer   = gs.getProperty('x_fed_day2_ops.ad_mid_server', '');
        this.dc          = gs.getProperty('x_fed_day2_ops.ad_dc', '');
        this.disabledOu  = gs.getProperty('x_fed_day2_ops.ad_disabled_ou', '');
        this.boundary    = gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate');
        this.env         = new x_fed_day2_ops.Day2Env();
        this.testMode    = this.env.isTestMode();
        this.log = {
            err:  function (m) { gs.error('[x_fed_day2_ops.AdHybridClient] ' + Day2Env.scrub(m)); },
            warn: function (m) { gs.warn('[x_fed_day2_ops.AdHybridClient] ' + Day2Env.scrub(m)); }
        };
    },

    // --- Routing predicate ---------------------------------------------------
    isAdMastered: function (entraUser) {
        return !!(entraUser && entraUser.onPremisesSyncEnabled === true);
    },

    // =========================================================================
    // WRITES — each returns { ok, dispatched, ecc_sys_id }. `ok` means the job
    // was ACCEPTED FOR DISPATCH. It never means the change took. Post-state is
    // established only by a read-back (see the READS section) — this is the
    // P0-4 contract and it is deliberate that no write method returns any field
    // resembling an observation.
    // =========================================================================

    createUserAd: function (payload) {
        payload = payload || {};
        if (!this._isAllowedOu(payload.ou))
            return this._refuse('create-user', 'target OU is outside x_fed_day2_ops.ad_managed_ous: ' + payload.ou);
        return this._dispatch('create-user', null, payload);
    },

    disableUserAd: function (identity) {
        var disable = this._dispatch('disable-user', identity, {});
        if (!disable.ok) return disable;
        if (!this.disabledOu)
            return { ok: true, dispatched: true, ecc_sys_id: disable.ecc_sys_id,
                     note: 'disable dispatched; no ad_disabled_ou configured so no move was dispatched' };
        var move = this._dispatch('move-object', identity, { targetOu: this.disabledOu });
        return { ok: disable.ok && move.ok, dispatched: true,
                 ecc_sys_id: disable.ecc_sys_id, ecc_sys_id_move: move.ecc_sys_id };
    },

    // P0-3: no password crosses this boundary. The MID generates it.
    setPasswordAd: function (identity, opts) {
        opts = opts || {};
        if (opts.tempPassword || opts.password || opts.newPassword) {
            this.log.err('setPasswordAd refused: caller supplied password material. ' +
                         'The MID Server generates and applies the password; ServiceNow must never hold or transport it (IA-5).');
            return { ok: false, error: 'password material must not be passed to this method (IA-5) — the MID generates it' };
        }
        return this._dispatch('reset-password', identity, {
            mustChangeAtLogon: (opts.mustChangeAtLogon === false) ? false : true,
            deliveryRef: opts.deliveryRef || ''
        });
    },

    setUserAttributesAd: function (identity, attrs) {
        return this._dispatch('set-attributes', identity, attrs || {});
    },

    moveUserOuAd: function (identity, targetOu) {
        if (!this._isAllowedOu(targetOu))
            return this._refuse('move-object', 'target OU is outside x_fed_day2_ops.ad_managed_ous: ' + targetOu);
        return this._dispatch('move-object', identity, { targetOu: targetOu });
    },

    // NEW-2: both directions gated. Removing a break-glass account from a
    // Tier-0 group is a denial-of-recovery primitive and was previously
    // unguarded while the add was blocked.
    addGroupMemberAd: function (group, member) {
        return this._groupWrite('add-group-member', group, member);
    },

    removeGroupMemberAd: function (group, member) {
        return this._groupWrite('remove-group-member', group, member);
    },

    _groupWrite: function (action, group, member) {
        var verdict = new x_fed_day2_ops.PrivilegeClassifier().classifyAdGroup(group);
        if (verdict.status !== 'confirmed-unprivileged') {
            this.log.warn(action + ' refused for group ' + group + ': ' + verdict.reason);
            return { ok: false, error: 'refused: ' + verdict.reason, classification: verdict.status };
        }
        return this._dispatch(action, member, { group: group });
    },

    // =========================================================================
    // READS — the P0-4 verification path. These dispatch a read job and return
    // its ECC sys_id; resolveDispatch() turns that into an observation.
    //
    // The ECC queue is asynchronous. Two supported patterns:
    //   (a) Flow: dispatch, wait on the ECC response, then call resolveDispatch.
    //       This is the production pattern.
    //   (b) awaitDispatch(): a BOUNDED poll for ATF and synchronous server
    //       scripts. It is capped and it fails closed on timeout — a timeout is
    //       'inconclusive', never 'verified'.
    // =========================================================================

    getUserAd: function (identity, properties) {
        return this._dispatch('get-user', identity, { properties: properties || [] });
    },

    getGroupMembersAd: function (group, recursive) {
        return this._dispatch('get-group-members', null, { group: group, recursive: !!recursive });
    },

    // Direct-membership assertion. Returns tri-state: true / false / null where
    // null means INCONCLUSIVE (never conflate with false at the call site).
    isGroupMemberAd: function (group, member, recursive) {
        if (this.testMode) return this.env.testFixture('ad_is_group_member', false);
        var d = this.getGroupMembersAd(group, recursive);
        if (!d.ok) return null;
        var res = this.awaitDispatch(d.ecc_sys_id);
        if (!res.ok || !res.data || !res.data.members) return null;
        var want = ('' + member).toLowerCase();
        for (var i = 0; i < res.data.members.length; i++) {
            var m = res.data.members[i] || {};
            if (('' + (m.samAccountName || '')).toLowerCase() === want ||
                ('' + (m.distinguishedName || '')).toLowerCase() === want ||
                ('' + (m.sid || '')).toLowerCase() === want) return true;
        }
        return false;
    },

    // Read the ECC response record for a dispatch. Returns
    // { ok, status, data, reason }. FAIL CLOSED: a missing, errored or
    // unparseable response is ok:false — never an assumed success.
    resolveDispatch: function (eccSysId) {
        if (!eccSysId) return { ok: false, reason: 'no ecc_sys_id supplied' };
        var gr = new GlideRecord('ecc_queue');
        gr.addQuery('response_to', eccSysId);
        gr.addQuery('queue', 'input');
        gr.orderByDesc('sys_created_on');
        gr.setLimit(1);
        gr.query();
        if (!gr.next()) return { ok: false, reason: 'no ECC response yet — inconclusive, not closed' };

        var state = gr.getValue('state');
        if (state === 'error')
            return { ok: false, reason: 'MID reported error: ' + Day2Env.scrub(gr.getValue('error_string') || '') };

        var payload = gr.getValue('payload') || '';
        var parsed;
        try { parsed = JSON.parse(payload); }
        catch (e) { return { ok: false, reason: 'MID response unparseable — inconclusive' }; }

        if (!parsed || parsed.ok !== true)
            return { ok: false, status: parsed ? parsed.status : null,
                     reason: parsed && parsed.error ? Day2Env.scrub(parsed.error) : 'MID reported failure' };
        return { ok: true, data: parsed.data || {}, dc: parsed.dc || null, observed_at: parsed.observed_at || null };
    },

    // Bounded wait. Cap is deliberately small — this is a convenience for ATF
    // and synchronous scripts, not the production path.
    awaitDispatch: function (eccSysId, maxMs) {
        var cap = Math.min(parseInt(maxMs || gs.getProperty('x_fed_day2_ops.ad_await_ms', '15000'), 10) || 15000, 60000);
        var waited = 0, step = 1000;
        while (waited < cap) {
            var r = this.resolveDispatch(eccSysId);
            if (r.ok || (r.reason && r.reason.indexOf('no ECC response yet') === -1)) return r;
            gs.sleep(step);
            waited += step;
        }
        return { ok: false, reason: 'timed out waiting for MID response after ' + cap + 'ms — inconclusive, not closed' };
    },

    // =========================================================================
    // Internals
    // =========================================================================

    // P0-1 / P0-2. Builds a STRUCTURED payload. No command text is assembled
    // anywhere in this class; the MID wrapper binds these as native parameters.
    _dispatch: function (action, identity, callerArgs) {
        try {
            var contract = AdHybridClient.ACTIONS[action];
            if (!contract) return { ok: false, error: 'unknown action: ' + action };
            if (!this.midServer) return { ok: false, error: 'ad_mid_server not configured — refusing to actuate' };

            var check = this._validateArgs(contract, callerArgs);
            if (!check.ok) {
                this.log.err(action + ' refused: ' + check.reason);
                return { ok: false, error: check.reason };
            }

            // Reserved parameters are set HERE, after validation, and can never
            // be supplied or overridden by the caller (P0-2).
            var job = {
                schema: 1,
                action: action,
                identity: identity ? ('' + identity) : null,
                server: this.dc || null,
                boundary: this.boundary,
                args: check.args,
                requested_at: new GlideDateTime().getValue()
            };
            if (this.testMode) job.test_mode = true;

            if (this.testMode) {
                // Canned dispatch acknowledgement only. Note what is NOT here:
                // no post-state, no `synced`, no `accountEnabled`. test_mode may
                // simulate a dispatch; it may not simulate an observation.
                return { ok: true, dispatched: true, ecc_sys_id: 'test-ecc-' + action, test_mode: true };
            }

            var gr = new GlideRecord('ecc_queue');
            gr.initialize();
            gr.setValue('agent', 'mid.server.' + this.midServer);
            gr.setValue('topic', 'Command');
            gr.setValue('name', 'Invoke-Day2AdAction');
            gr.setValue('source', 'x_fed_day2_ops.AdHybridClient');
            gr.setValue('queue', 'output');
            gr.setValue('payload', JSON.stringify(job));
            var id = gr.insert();
            if (!id) return { ok: false, error: 'ECC dispatch insert failed' };
            return { ok: true, dispatched: true, ecc_sys_id: '' + id, action: action };
        } catch (e) {
            this.log.err('_dispatch ' + action + ' failed: ' + e);
            return { ok: false, error: 'dispatch failed' };
        }
    },

    // The allowlist. Three refusals, in order of severity:
    //   1. a reserved parameter appeared in caller input  -> override attempt
    //   2. a key is not in the action's allowed set       -> unknown parameter
    //   3. a key is not a bare identifier                 -> injection attempt
    _validateArgs: function (contract, callerArgs) {
        var out = {}, k;
        callerArgs = callerArgs || {};

        for (k in callerArgs) {
            if (!callerArgs.hasOwnProperty(k)) continue;

            if (!/^[A-Za-z][A-Za-z0-9]*$/.test(k))
                return { ok: false, reason: 'illegal parameter name (must be a bare identifier): ' + JSON.stringify(k) };

            if (AdHybridClient.RESERVED.indexOf(('' + k).toLowerCase()) !== -1)
                return { ok: false, reason: 'reserved parameter may not be supplied by the caller: ' + k };

            if (contract.allowed.indexOf(k) === -1)
                return { ok: false, reason: 'parameter not permitted for this action: ' + k };

            var v = callerArgs[k];
            if (v === null || v === undefined) continue;
            if (typeof v === 'object' && !(v instanceof Array))
                return { ok: false, reason: 'parameter value must be scalar or array: ' + k };
            out[k] = v;
        }

        for (var i = 0; i < contract.required.length; i++) {
            var req = contract.required[i];
            if (out[req] === undefined || out[req] === null || ('' + out[req]).trim() === '')
                return { ok: false, reason: 'required parameter missing: ' + req };
        }
        return { ok: true, args: out };
    },

    _isAllowedOu: function (targetOu) {
        var allow = gs.getProperty('x_fed_day2_ops.ad_managed_ous', '');
        if (!allow) return false;   // fail closed: no allowlist means no writes to any OU
        if (!targetOu) return false;
        var ous = allow.split(',');
        var norm = ('' + targetOu).trim().toLowerCase();
        for (var i = 0; i < ous.length; i++) {
            if (norm === ous[i].trim().toLowerCase()) return true;
        }
        return false;
    },

    _refuse: function (action, reason) {
        this.log.warn(action + ' refused: ' + reason);
        return { ok: false, error: 'refused: ' + reason };
    },

    type: 'AdHybridClient'
};
