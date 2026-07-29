// Script Include: AdHybridClient  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// CURRENT-STATE actuation path for the hybrid identity estate.
//
// WHY THIS EXISTS. Today the agency's Entra ID users are SYNCED FROM ACTIVE
// DIRECTORY (Entra Connect); Active Directory is the identity master and Entra
// is its synchronized projection. For a synced object
// (Entra `onPremisesSyncEnabled = true`) the authoritative write for the account
// lifecycle and its on-prem-mastered attributes MUST land in AD and then flow
// to Entra on the next sync cycle. Writing those directly in Entra Graph is
// wrong: Entra Connect overwrites cloud edits to synced attributes on the next
// cycle, and admin-initiated actions like a cloud password reset are not
// supported for a synced user unless password writeback is enabled.
//
// So this client is the AD leg of the Day-2 kit's CURRENT-STATE configuration
// (property `x_fed_day2_ops.hybrid_mode = 'true'`). It is the sibling of
// EntraHelpdeskClient (the Graph leg): the router in the Flow sends
// synced-object lifecycle / attribute / password / AD-sourced-group work HERE,
// and keeps cloud-native work (MFA methods, Azure RBAC, guests, app consent,
// cloud-only groups) on the Graph leg. In the 2027 TARGET state
// (`hybrid_mode = 'false'`, OPM-HRIT SSOT, cloud-native provisioning) the router
// sends everything to Graph and this client is dormant.
//
// Boundary discipline (mirrors EntraHelpdeskClient / Vol IX Book 00):
//   * AD actuation runs on a DOMAIN-JOINED, in-boundary MID Server
//     (property x_fed_day2_ops.ad_mid_server) — the PowerShell / LDAP call and
//     its credential never leave the ATO boundary. This is a DIFFERENT MID from
//     the Graph MID only if AD reachability requires it.
//   * The MID's service account holds DELEGATED, least-privilege AD rights on
//     the specific OUs it manages (create/disable users, reset password, manage
//     membership of the delegated groups) — NEVER Domain Admin.
//   * The preferred writable DC comes from x_fed_day2_ops.ad_dc so the write and
//     the read-back verify hit the same DC (avoid replication-lag false reads).
//
// STARTER SKELETON — the transport below is modeled as a MID PowerShell dispatch
// (ActiveDirectory module). Pin it to your hardened PowerShell activity or the
// Integration Hub AD spoke before production, and validate the delegated rights
// against your OU model. test_mode (x_fed_day2_ops.test_mode = 'true') returns
// deterministic canned values so the ATF suites drive the Flow with NO live AD
// connectivity. Never enable test_mode in production.
// -----------------------------------------------------------------------------
var AdHybridClient = Class.create();
AdHybridClient.prototype = {

    initialize: function () {
        this.midServer = gs.getProperty('x_fed_day2_ops.ad_mid_server', '');
        this.dc = gs.getProperty('x_fed_day2_ops.ad_dc', '');            // preferred writable DC
        this.disabledOu = gs.getProperty('x_fed_day2_ops.ad_disabled_ou', '');
        this.boundary = gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate');
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.AdHybridClient] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Routing predicate: is this object AD-mastered (synced) or cloud-only? -
    // The router reads the Entra user's onPremisesSyncEnabled (via the Graph leg)
    // and calls this. true  -> lifecycle/attribute/password/AD-group writes come
    // HERE; false -> the object is cloud-only, everything stays on the Graph leg.
    isAdMastered: function (entraUser) {
        return !!(entraUser && entraUser.onPremisesSyncEnabled === true);
    },

    // --- Joiner: create the account in AD; sync projects it into Entra (AC-2). -
    // Cloud-only entitlements (license, cloud groups) are assigned on the Graph
    // leg AFTER the synced object appears in Entra — not here.
    createUserAd: function (payload) {
        // payload: { samAccountName, upn, givenName, sn, displayName, ou, ... }
        if (this.testMode) return { ok: true, distinguishedName: 'CN=' + payload.samAccountName + ',' + (payload.ou || 'OU=Users'), synced: true };
        return this._ps('New-ADUser', {
            Name: payload.displayName, SamAccountName: payload.samAccountName,
            UserPrincipalName: payload.upn, GivenName: payload.givenName, Surname: payload.sn,
            Path: payload.ou, Enabled: true
        });
    },

    // --- Leaver: disable in AD, move to the disabled OU; sync flows the disable -
    // to Entra. Session/token revoke and cloud-owned object reassignment are
    // CLOUD actions — they run on the Graph leg, not here (AC-2).
    disableUserAd: function (samOrDn) {
        if (this.testMode) return { ok: true, id: samOrDn, accountEnabled: false, movedToDisabledOu: !!this.disabledOu, synced: true };
        var disable = this._ps('Disable-ADAccount', { Identity: samOrDn });
        var moved = this.disabledOu ? this._ps('Move-ADObject', { Identity: samOrDn, TargetPath: this.disabledOu }) : { ok: true, skipped: 'no disabled OU configured' };
        return { ok: disable.ok && moved.ok, id: samOrDn, accountEnabled: false, disableStatus: disable, moveStatus: moved };
    },

    // --- Credential: reset the password in AD; it syncs to Entra (IA-5). -------
    // Prefer SSPR with writeback; this admin path is the approver-gated fallback.
    setPasswordAd: function (samOrDn, opts) {
        if (this.testMode) return { ok: true, id: samOrDn, action: 'ad-password-reset', synced: true };
        var reset = this._ps('Set-ADAccountPassword', { Identity: samOrDn, Reset: true, NewPassword: opts.tempPassword });
        var mustChange = this._ps('Set-ADUser', { Identity: samOrDn, ChangePasswordAtLogon: true });
        return { ok: reset.ok && mustChange.ok, id: samOrDn, resetStatus: reset, mustChangeStatus: mustChange };
    },

    // --- Mover: set on-prem-mastered attributes / move OU in AD; syncs (AC-6). -
    // Cloud-only access changes (licenses, cloud groups) run on the Graph leg.
    setUserAttributesAd: function (samOrDn, attrs) {
        if (this.testMode) return { ok: true, id: samOrDn, applied: Object.keys(attrs || {}), synced: true };
        return this._ps('Set-ADUser', this._merge({ Identity: samOrDn }, attrs));
    },

    moveUserOuAd: function (samOrDn, targetOu) {
        if (this.testMode) return { ok: true, id: samOrDn, targetOu: targetOu };
        if (!this._isAllowedOu(targetOu)) {
            return { ok: false, error: 'refusing to move to an OU outside the managed allowlist: ' + targetOu };
        }
        return this._ps('Move-ADObject', { Identity: samOrDn, TargetPath: targetOu });
    },
    _isAllowedOu: function (targetOu) {
        var allow = gs.getProperty('x_fed_day2_ops.ad_managed_ous', '');
        if (!allow) return false;   // fail closed: no allowlist configured means no moves permitted
        var ous = allow.split(',');
        var norm = ('' + targetOu).trim().toLowerCase();
        for (var i = 0; i < ous.length; i++) { if (norm === ous[i].trim().toLowerCase()) return true; }
        return false;
    },

    // --- Access: AD-SOURCED (synced) group membership (AC-6). ------------------
    // Only for groups that originate in AD and sync to Entra. Cloud-only / M365
    // groups are managed on the Graph leg — the router decides by group source.
    // The deny-list below is defense-in-depth ONLY — it is not a substitute for
    // verifying the MID service account's actual AD delegation, which remains a
    // separate, still-open pre-production item (see CURRENT-STATE-SCRIPTS.md §1).
    addGroupMemberAd: function (groupSamOrDn, memberSamOrDn) {
        if (this.testMode) return { ok: true, groupId: groupSamOrDn, memberId: memberSamOrDn, synced: true };
        if (this._isProtectedGroup(groupSamOrDn)) {
            return { ok: false, error: 'refusing to modify a protected/tier-0 group via the AD leg: ' + groupSamOrDn };
        }
        return this._ps('Add-ADGroupMember', { Identity: groupSamOrDn, Members: memberSamOrDn });
    },
    _isProtectedGroup: function (groupSamOrDn) {
        var defaults = 'Domain Admins,Enterprise Admins,Schema Admins,Administrators,Account Operators,Backup Operators,Server Operators,Print Operators,Domain Controllers,Read-only Domain Controllers,Group Policy Creator Owners,Cert Publishers,Key Admins,Enterprise Key Admins,DnsAdmins';
        var denyList = gs.getProperty('x_fed_day2_ops.ad_protected_groups', defaults).split(',');
        var name = ('' + groupSamOrDn).toLowerCase();
        for (var i = 0; i < denyList.length; i++) {
            var entry = denyList[i].trim().toLowerCase();
            if (entry && name.indexOf(entry) !== -1) return true;
        }
        return false;
    },

    removeGroupMemberAd: function (groupSamOrDn, memberSamOrDn) {
        if (this.testMode) return { ok: true, groupId: groupSamOrDn, memberId: memberSamOrDn, removed: true };
        return this._ps('Remove-ADGroupMember', { Identity: groupSamOrDn, Members: memberSamOrDn, Confirm: false });
    },

    // --- Internal: MID-dispatched PowerShell (ActiveDirectory module). ---------
    // Skeleton transport: writes an ECC-queue output record targeting the
    // domain-joined MID, pinned to the preferred DC so the verify re-read is
    // replication-consistent. Replace with your hardened PowerShell activity /
    // AD spoke for production; keep the fail-closed contract (any error -> ok:false).
    _ps: function (cmdlet, params) {
        try {
            if (!this.midServer) return { ok: false, error: 'ad_mid_server not configured — refusing to actuate' };
            var args = this._merge({}, params);
            if (this.dc) args.Server = this.dc;                          // pin the DC
            var command = this._render(cmdlet, args);
            var gr = new GlideRecord('ecc_queue');
            gr.initialize();
            gr.setValue('agent', 'mid.server.' + this.midServer);
            gr.setValue('topic', 'PowerShell');
            gr.setValue('name', cmdlet);
            gr.setValue('source', 'x_fed_day2_ops.AdHybridClient');
            gr.setValue('payload', command);
            var id = gr.insert();
            // The ECC output is asynchronous; the Flow's VERIFY clause re-reads AD
            // state on the same DC to confirm the post-state (a dispatch is not a
            // closure). Returning ok here means "dispatched", not "verified".
            return { ok: !!id, dispatched: true, ecc_sys_id: '' + id, cmdlet: cmdlet };
        } catch (e) {
            this.log.logErr('_ps ' + cmdlet + ' failed: ' + e);
            return { ok: false, error: '' + e };
        }
    },

    _render: function (cmdlet, args) {
        var parts = [cmdlet];
        for (var k in args) {
            if (!args.hasOwnProperty(k)) continue;
            var v = args[k];
            if (v === true) { parts.push('-' + k); }
            else if (v === false || v === null || v === undefined) { continue; }
            else { parts.push('-' + k + " '" + ('' + v).replace(/'/g, "''") + "'"); }
        }
        return parts.join(' ');
    },

    _merge: function (a, b) {
        var out = {}, k;
        for (k in a) { if (a.hasOwnProperty(k)) out[k] = a[k]; }
        for (k in (b || {})) { if (b.hasOwnProperty(k)) out[k] = b[k]; }
        return out;
    },

    type: 'AdHybridClient'
};
