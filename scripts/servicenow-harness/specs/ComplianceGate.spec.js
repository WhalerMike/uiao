'use strict';
// =============================================================================
// ComplianceGate — the x_fed_compliance safety gate and closure-by-observation
// check.
//
// Two properties matter here and neither was executable before this harness:
//   1. preflight() fails closed on separation-of-duties AND on an unconfirmed
//      read-only scope. The app's authority to ATTEST depends on its inability
//      to ACTUATE, so "unverified" must be treated exactly like "failed".
//   2. _isWriteShaped() is a security check, not a display helper -- a casing
//      mismatch must not let a write permission pass as read-only.
//
// Source: docs/customer-documents/orgcomp-series/x_fed_compliance/
//         script-includes/ComplianceGate.js
// =============================================================================

const { loadScriptInclude, construct, silentLog } = require('../load.js');

function gate(fields) {
    const { klass, captured } = loadScriptInclude('fedcompliance', 'ComplianceGate', {
        properties: { 'x_fed_compliance.test_mode': 'false' },
        globals: { x_fed_compliance: {} },
    });
    const instance = construct(klass, Object.assign({
        testMode: false,
        log: silentLog(),
        ingest: {},
    }, fields || {}));
    return { g: instance, captured };
}

/** A gate whose write-scope check reports a fixed status. */
function gateWithScope(status) {
    return gate({ _identityWriteScopeStatus: () => status });
}

module.exports = function (t, assert) {

    // --- separation of duties (CM-5) --------------------------------------
    t('preflight refuses when requester and approver are the same', () => {
        const { g } = gateWithScope('confirmed-readonly');
        const r = g.preflight({ requester_id: 'alice', approver_id: 'alice' });
        assert.equal(r.ok, false);
        assert.match(r.reason, /self-approval refused/);
    });

    t('preflight treats a missing approver as indeterminate, not a pass', () => {
        const { g } = gateWithScope('confirmed-readonly');
        assert.equal(g.preflight({ requester_id: 'alice' }).ok, false);
        assert.equal(g.preflight({ approver_id: 'bob' }).ok, false);
        assert.equal(g.preflight({}).ok, false);
    });

    t('preflight passes when SoD holds and the scope is confirmed read-only', () => {
        const { g } = gateWithScope('confirmed-readonly');
        const r = g.preflight({ requester_id: 'alice', approver_id: 'bob' });
        assert.ok(r.ok, `expected a clear preflight, got ${JSON.stringify(r)}`);
    });

    // --- attestation authority --------------------------------------------
    t('an UNVERIFIED write-scope check voids attestation authority', () => {
        // The critical asymmetry: "we did not check" must behave like
        // "the check failed", never like "the check passed".
        for (const status of ['unverified', 'unknown', 'holds-write', 'error', '']) {
            const { g } = gateWithScope(status);
            const r = g.preflight({ requester_id: 'alice', approver_id: 'bob' });
            assert.equal(r.ok, false, `status ${JSON.stringify(status)} must not pass preflight`);
            assert.match(r.reason, /attestation authority void/);
        }
    });

    // --- write-shape detection --------------------------------------------
    t('_isWriteShaped detects write permissions regardless of casing', () => {
        const { g } = gate();
        const writes = [
            'Directory.ReadWrite.All',
            'directory.readwrite.all',
            'DIRECTORY.READWRITE.ALL',
            'Group.Write',
            'Application.FullControl.All',
            'RoleManagement.Manage.Directory',
        ];
        for (const p of writes) {
            assert.ok(g._isWriteShaped(p), `${p} must be detected as write-shaped`);
        }
    });

    t('_isWriteShaped does not flag read-only permissions', () => {
        const { g } = gate();
        const reads = [
            'Directory.Read.All',
            'directory.read.all',
            'User.Read',
            'Policy.Read.ConditionalAccess',
        ];
        for (const p of reads) {
            assert.notOk(g._isWriteShaped(p), `${p} must not be flagged as write-shaped`);
        }
    });

    t('_isWriteShaped handles null and empty input without throwing', () => {
        const { g } = gate();
        assert.notOk(g._isWriteShaped(null));
        assert.notOk(g._isWriteShaped(undefined));
        assert.notOk(g._isWriteShaped(''));
    });

    // --- appRole resolution -------------------------------------------------
    t('_resolveAppRoleValue returns null rather than guessing', () => {
        const { g } = gate();
        const roles = [{ id: 'aaa', value: 'Directory.Read.All' }];
        assert.equal(g._resolveAppRoleValue(roles, 'aaa'), 'Directory.Read.All');
        assert.equal(g._resolveAppRoleValue(roles, 'missing-guid'), null,
            'an unresolvable appRoleId must be null, never a guess');
        assert.equal(g._resolveAppRoleValue([], 'anything'), null);
    });
};
