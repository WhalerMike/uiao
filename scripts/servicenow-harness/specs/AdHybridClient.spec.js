'use strict';
// =============================================================================
// AdHybridClient — the AD write leg.
//
// Every assertion here corresponds to a finding from the external adversarial
// security review (2026-07-29) that the kit's own ATF suite could not exercise,
// because `test_mode` short-circuited before the vulnerable code path. These
// run against the real source with no instance, so the refusal paths are
// observed rather than asserted.
//
// Source: docs/customer-documents/orgcomp-series/servicenow-day2/
//         script-includes/AdHybridClient.js
// =============================================================================

const { loadScriptInclude, construct, silentLog } = require('../load.js');

const PROPERTIES = {
    'x_fed_day2_ops.ad_mid_server': 'mid01',
    'x_fed_day2_ops.ad_managed_ous': 'OU=Users,DC=corp,DC=gov',
    'x_fed_day2_ops.ad_writable_dc': 'dc01.corp.gov',
};

/** A client wired to the fields the write path reads, with initialize() skipped. */
function client(overrides) {
    const { klass, captured } = loadScriptInclude('day2', 'AdHybridClient', { properties: PROPERTIES });
    const instance = construct(klass, Object.assign({
        midServer: 'mid01',
        dc: 'dc01.corp.gov',
        boundary: 'gcc-moderate',
        testMode: false,
        log: silentLog(),
    }, overrides));
    return { c: instance, captured };
}

module.exports = function (t, assert) {

    t('loads and exposes the documented ACTIONS contract', () => {
        const { klass } = loadScriptInclude('day2', 'AdHybridClient', { properties: PROPERTIES });
        assert.ok(klass.ACTIONS, 'ACTIONS table must be present');
        assert.ok(Array.isArray(klass.RESERVED), 'RESERVED list must be present');
        assert.ok(Object.keys(klass.ACTIONS).length >= 9, 'expected at least 9 declared actions');
    });

    // --- P0-1: command injection ------------------------------------------
    t('P0-1 refuses an injection-shaped parameter name', () => {
        const { c } = client();
        const r = c.setUserAttributesAd('jdoe', { 'title; Remove-ADUser -Identity x': 'x' });
        assert.refused(r, /illegal parameter name/);
    });

    t('P0-1 refuses a parameter name containing whitespace', () => {
        const { c } = client();
        assert.refused(c.setUserAttributesAd('jdoe', { 'title ': 'x' }), /illegal parameter name/);
    });

    t('P0-1 no command text is ever assembled — the payload is structured JSON', () => {
        const { c, captured } = client();
        const r = c.setUserAttributesAd('jdoe', { title: 'Analyst' });
        assert.ok(r.ok, 'allowlisted write should be accepted');
        assert.equal(captured.inserts.length, 1, 'exactly one ECC row');
        const row = captured.inserts[0];
        assert.equal(row.table, 'ecc_queue');
        const job = JSON.parse(row.values.payload);
        assert.equal(job.action, 'set-attributes');
        assert.equal(job.identity, 'jdoe');
        assert.equal(job.args.title, 'Analyst');
    });

    // --- P0-2: target substitution ----------------------------------------
    t('P0-2 refuses a caller-supplied reserved parameter', () => {
        const { c } = client();
        assert.refused(c.setUserAttributesAd('jdoe', { identity: 'administrator' }), /reserved parameter/);
    });

    t('P0-2 the approved identity survives — it is set after validation', () => {
        const { c, captured } = client();
        c.setUserAttributesAd('jdoe', { title: 'Analyst' });
        const job = JSON.parse(captured.inserts[0].values.payload);
        assert.equal(job.identity, 'jdoe', 'identity must come from the approved argument');
    });

    t('rejects a prototype-pollution shaped key', () => {
        const { c } = client();
        const hostile = JSON.parse('{"__proto__":"x"}');
        assert.refused(c.setUserAttributesAd('jdoe', hostile), /illegal parameter name/);
    });

    // --- P0-3: cleartext credential ---------------------------------------
    t('P0-3 refuses caller-supplied password material', () => {
        const { c } = client();
        assert.refused(c.setPasswordAd('jdoe', { tempPassword: 'Summer2026!' }));
    });

    t('P0-3 no ECC payload ever carries a password field', () => {
        const { c, captured } = client();
        c.setPasswordAd('jdoe', { mustChangeAtLogon: true });
        for (const row of captured.inserts) {
            const payload = String(row.values.payload || '');
            assert.notOk(/password/i.test(payload) && /["'][^"']{8,}["']/.test(payload)
                && /tempPassword/.test(payload), 'payload must not carry secret material');
        }
    });

    // --- P0-4: unverified writes ------------------------------------------
    t('P0-4 a write returns a dispatch handle and never asserts post-state', () => {
        const { c } = client();
        const r = c.disableUserAd('jdoe');
        assert.ok(r.ok);
        assert.ok(r.dispatched, 'must report dispatch');
        assert.lacksKeys(r, ['synced', 'accountEnabled', 'verified', 'closed']);
    });

    t('P0-4 read-back methods exist', () => {
        const { klass } = loadScriptInclude('day2', 'AdHybridClient', { properties: PROPERTIES });
        for (const m of ['getUserAd', 'getGroupMembersAd', 'isGroupMemberAd', 'resolveDispatch']) {
            assert.equal(typeof klass.prototype[m], 'function', `${m} must exist`);
        }
    });

    // --- allowlist behaviour ----------------------------------------------
    t('refuses a parameter not permitted for the action', () => {
        const { c } = client();
        assert.refused(c.setUserAttributesAd('jdoe', { notARealAttribute: 'x' }), /not permitted/);
    });

    t('refuses when a required parameter is missing', () => {
        const { c } = client();
        assert.refused(c.moveUserOuAd('jdoe', ''));
    });

    t('refuses an object-valued parameter', () => {
        const { c } = client();
        assert.refused(c.setUserAttributesAd('jdoe', { title: { nested: 'object' } }), /scalar or array/);
    });

    // --- fail-closed configuration ----------------------------------------
    t('refuses to actuate when no MID server is configured', () => {
        const { c } = client({ midServer: null });
        assert.refused(c.setUserAttributesAd('jdoe', { title: 'Analyst' }), /mid_server|refusing to actuate/);
    });

    t('OU allowlist fails closed when unset', () => {
        const { klass } = loadScriptInclude('day2', 'AdHybridClient', { properties: {} });
        const c = construct(klass, { midServer: 'mid01', log: silentLog(), testMode: false });
        assert.notOk(c._isAllowedOu('OU=Anything,DC=corp,DC=gov'),
            'an unset allowlist must permit no OU at all');
    });

    t('OU allowlist matches a whole distinguished name', () => {
        // Regression: the separator was ',' -- which is also the DN component
        // separator -- so every DN was shredded and no OU could ever match.
        const { c } = client();
        assert.ok(c._isAllowedOu('OU=Users,DC=corp,DC=gov'), 'a listed DN must be allowed');
        assert.notOk(c._isAllowedOu('OU=Executives,DC=corp,DC=gov'), 'an unlisted DN must be refused');
    });

    t('OU allowlist never matches a bare DN component', () => {
        const { c } = client();
        for (const fragment of ['OU=Users', 'DC=corp', 'DC=gov', '']) {
            assert.notOk(c._isAllowedOu(fragment), `must not match fragment ${JSON.stringify(fragment)}`);
        }
    });

    t('OU allowlist accepts multiple DNs and tolerates newlines', () => {
        const { klass } = loadScriptInclude('day2', 'AdHybridClient', {
            properties: {
                'x_fed_day2_ops.ad_managed_ous':
                    'OU=Users,DC=corp,DC=gov;\nOU=Contractors,DC=corp,DC=gov',
            },
        });
        const c = construct(klass, { log: silentLog() });
        assert.ok(c._isAllowedOu('OU=Users,DC=corp,DC=gov'));
        assert.ok(c._isAllowedOu('OU=Contractors,DC=corp,DC=gov'));
        assert.notOk(c._isAllowedOu('OU=Executives,DC=corp,DC=gov'));
    });

    // --- test_mode discipline ---------------------------------------------
    t('test_mode still runs validation before short-circuiting (the 2026-07 gap)', () => {
        const { c } = client({ testMode: true });
        // This is the regression that matters: under the pre-remediation kit,
        // test_mode returned success before validation ran, so no ATF spec
        // could ever reach the injection path.
        assert.refused(c.setUserAttributesAd('jdoe', { 'title; whoami': 'x' }), /illegal parameter name/);
    });

    t('test_mode simulates dispatch but never simulates observation', () => {
        const { c, captured } = client({ testMode: true });
        const r = c.setUserAttributesAd('jdoe', { title: 'Analyst' });
        assert.ok(r.ok);
        assert.ok(r.test_mode, 'must mark itself as simulated');
        assert.lacksKeys(r, ['synced', 'accountEnabled', 'verified']);
        assert.equal(captured.inserts.length, 0, 'test_mode must not queue a real ECC row');
    });
};
