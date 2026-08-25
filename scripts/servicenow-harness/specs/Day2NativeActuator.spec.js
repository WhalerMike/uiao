'use strict';
// =============================================================================
// Day2NativeActuator — the Lane F actuator that writes ServiceNow's OWN records.
//
// This file carries the kit's load-bearing doctrine sentence: "ServiceNow
// raises, routes and evidences; it NEVER writes to the estate." That claim is
// what lets the whole coordination argument stand, and until now it was a
// comment. These specs make it a gate: the class must have no external
// transport at all, and a refused insert must never be reported as success.
//
// Source: docs/customer-documents/orgcomp-series/servicenow-day2/
//         script-includes/Day2NativeActuator.js
// =============================================================================

const { loadScriptInclude, construct, silentLog } = require('../load.js');

const TABLES = [
    'x_fed_day2_ops_integration',
    'x_fed_day2_ops_evidence',
    'change_request',
    'sc_req_item',
];

function actuator(opts) {
    opts = opts || {};
    const { klass, captured, source } = loadScriptInclude('day2', 'Day2NativeActuator', {
        properties: { 'x_fed_day2_ops.mid_server': '' },
        validTables: opts.validTables,
        globals: { x_fed_day2_ops: {} },
    });
    const instance = construct(klass, Object.assign({
        boundary: 'gcc-moderate',
        testMode: false,
        log: { logErr: silentLog().err, logWarn: silentLog().warn, err: silentLog().err },
    }, opts.fields || {}));
    return { a: instance, captured, source, klass };
}

module.exports = function (t, assert) {

    // --- the doctrine claim, as a gate ------------------------------------
    t('has no external transport — no RESTMessageV2 anywhere in the source', () => {
        const { source } = actuator();
        assert.notOk(/RESTMessageV2/.test(source),
            'a native actuator that gained an HTTP client would have crossed the lane it exists to hold');
    });

    t('never queues work to a MID server', () => {
        const { source } = actuator();
        assert.notOk(/ecc_queue/.test(source),
            'an ECC insert here would mean ServiceNow actuating the estate directly');
    });

    t('writes only to ServiceNow-side tables', () => {
        const { source } = actuator();
        // Every table this class touches must be a workflow-plane record, not a
        // tenant object. Assert the shape rather than an exact list so adding a
        // legitimate scoped table does not fail the gate.
        const tables = [...source.matchAll(/new GlideRecord\(\s*([^)]+?)\s*\)/g)].map((m) => m[1]);
        for (const expr of tables) {
            assert.ok(
                /^(table|this\.tbl|'x_fed_day2_ops|'sc_|'change_|'cmdb_|'sys_|'sn_)/.test(expr.trim()),
                `unexpected GlideRecord target: ${expr}`
            );
        }
    });

    // --- a refused insert is never success --------------------------------
    t('_insert refuses when the table does not exist on the instance', () => {
        const { a } = actuator({ validTables: TABLES });
        const r = a._insert('x_fed_day2_ops_not_created_yet', { foo: 'bar' });
        assert.equal(r.ok, false);
        assert.match(r.error, /does not exist/);
    });

    t('_insert reports success with a sys_id on a real write', () => {
        const { a, captured } = actuator({ validTables: TABLES });
        const r = a._insert('x_fed_day2_ops_integration', { name: 'demo', boundary: 'gcc-moderate' });
        assert.ok(r.ok);
        assert.ok(r.sys_id, 'a successful insert must return a sys_id');
        assert.equal(captured.inserts.length, 1);
        assert.equal(captured.inserts[0].table, 'x_fed_day2_ops_integration');
    });

    t('_insert skips null and undefined fields rather than writing empties', () => {
        const { a, captured } = actuator({ validTables: TABLES });
        a._insert('x_fed_day2_ops_integration', {
            name: 'demo', missing: null, absent: undefined, zero: 0, empty: '',
        });
        const written = captured.inserts[0].values;
        assert.equal(written.name, 'demo');
        assert.notOk('missing' in written, 'null must not be written');
        assert.notOk('absent' in written, 'undefined must not be written');
        // 0 and '' are legitimate values and must survive the filter.
        assert.equal(written.zero, 0, 'zero is a value, not an absence');
        assert.equal(written.empty, '', 'empty string is a value, not an absence');
    });

    t('_insert never throws — a platform error becomes a refusal', () => {
        const { a } = actuator({ validTables: TABLES });
        // Drive the catch branch by making field ACCESS throw. A throwing
        // toString() would not do it: the shim's setValue stores the raw value
        // (deliberately, so specs can assert what was passed rather than its
        // string coercion), so nothing stringifies it on the way in.
        const fields = { name: 'demo' };
        Object.defineProperty(fields, 'bad', {
            enumerable: true,
            get() { throw new Error('simulated platform failure'); },
        });
        const r = a._insert('x_fed_day2_ops_integration', fields);
        assert.equal(typeof r, 'object', 'must return a result object, not propagate');
        assert.equal(r.ok, false);
    });
};
