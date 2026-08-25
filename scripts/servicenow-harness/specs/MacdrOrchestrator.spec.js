'use strict';
// =============================================================================
// MacdrOrchestrator — the five-clause MACD-R gate every governed identity
// request runs through.
//
// Focus: clause 1 (Origin) and the reserved-key refusal. Clause 1 was the gap
// the 2026-07-29 external review found -- it was the one clause with no
// enforcement, so a request with no provable origin ran anyway. These specs
// assert the fail-closed behaviour directly against the source.
//
// Source: docs/customer-documents/orgcomp-series/servicenow-day2/
//         script-includes/MacdrOrchestrator.js
// =============================================================================

const { loadScriptInclude, construct, silentLog } = require('../load.js');

// Day2Env.scrub is a cross-Script-Include static the orchestrator calls when
// logging. Identity is fine for a spec -- the scrubbing itself is Day2Env's
// own responsibility, not this file's.
const Day2Env = { scrub: (v) => String(v === undefined || v === null ? '' : v) };

function orchestrator(opts) {
    opts = opts || {};
    const { klass, captured, context } = loadScriptInclude('day2', 'MacdrOrchestrator', {
        properties: Object.assign({
            'x_fed_day2_ops.tbl_evidence': 'x_fed_day2_ops_evidence',
            'x_fed_day2_ops.tbl_integration': 'x_fed_day2_ops_integration',
            'x_fed_day2_ops.hybrid_mode': 'false',
        }, opts.properties || {}),
        records: opts.records || {},
        globals: { Day2Env, x_fed_day2_ops: {} },
    });

    const instance = construct(klass, Object.assign({
        tblEvidence: 'x_fed_day2_ops_evidence',
        tblIntegration: 'x_fed_day2_ops_integration',
        testMode: false,
        log: silentLog(),
        // Collaborators. Default to permissive so a refusal observed in a spec
        // can only have come from the clause under test.
        env: { guard: () => ({ ok: true }), isTestMode: () => false },
        gate: { preflight: () => ({ ok: true }) },
        pim: { activate: () => ({ ok: true }) },
        sam: { writeClosureSummary: () => ({ ok: true }) },
    }, opts.fields || {}));

    return { o: instance, captured, context, klass };
}

module.exports = function (t, assert) {

    t('declares the RESERVED key list', () => {
        const { klass } = orchestrator();
        assert.ok(Array.isArray(klass.RESERVED), 'RESERVED must be present');
        assert.includes(klass.RESERVED.join(','), '_forcewritebackfailure');
    });

    // --- clause 1: ORIGIN, fail closed ------------------------------------
    t('clause 1 stops a request with no origin at all', () => {
        const { o } = orchestrator();
        const r = o.run({ verb: 'grant', control: 'AC-2' }, () => ({ ok: true }), {});
        assert.equal(r.ok, false, 'an origin-less request must not run');
        assert.equal(r.clause, 'origin');
    });

    t('clause 1 stops a sam_request_id that resolves to nothing', () => {
        const { o } = orchestrator();          // no integration records seeded
        const r = o.run({ sam_request_id: 'SAM-9999' }, () => ({ ok: true }), {});
        assert.equal(r.ok, false);
        assert.equal(r.clause, 'origin');
    });

    t('clause 1 accepts a sam_request_id that resolves to a lineage record', () => {
        const { o } = orchestrator({
            records: {
                x_fed_day2_ops_integration: [{ sys_id: 'lin1', sam_request_id: 'SAM-1234' }],
            },
        });
        const origin = o._clauseOrigin({ sam_request_id: 'SAM-1234' });
        assert.ok(origin.ok, 'a resolvable SAM id is a valid origin');
        assert.equal(origin.origin, 'sam');
    });

    t('clause 1 stops a RITM that resolves to nothing', () => {
        const { o } = orchestrator();
        const origin = o._clauseOrigin({ ritm: 'RITM0099999' });
        assert.equal(origin.ok, false);
        assert.match(origin.reason, /origin unproven/);
    });

    t('clause 1 accepts a RITM that resolves to an sc_req_item', () => {
        const { o } = orchestrator({
            records: { sc_req_item: [{ sys_id: 'r1', number: 'RITM0010001' }] },
        });
        const origin = o._clauseOrigin({ ritm: 'RITM0010001' });
        assert.ok(origin.ok);
        assert.equal(origin.origin, 'catalog');
    });

    // --- break-glass: allowed, but never silent ---------------------------
    t('break-glass without an approver is refused', () => {
        const { o } = orchestrator();
        const origin = o._clauseOrigin({ breakglass: true, breakglass_justification: 'outage' });
        assert.equal(origin.ok, false, 'break-glass needs a named approver');
    });

    t('break-glass without a justification is refused', () => {
        const { o } = orchestrator();
        const origin = o._clauseOrigin({ breakglass: true, breakglass_approver_id: 'alice' });
        assert.equal(origin.ok, false);
    });

    t('break-glass with approver and justification is accepted and logged loudly', () => {
        const { o, captured } = orchestrator();
        const origin = o._clauseOrigin({
            breakglass: true,
            breakglass_approver_id: 'alice',
            breakglass_justification: 'sev1 outage',
            requester_id: 'bob',
        });
        assert.ok(origin.ok);
        assert.equal(origin.origin, 'breakglass');
        assert.ok(origin.approver, 'break-glass must record its approver');
        // "Loud" is the point: a break-glass origin that leaves no warning
        // behind is indistinguishable from a normal run in the log.
        assert.ok(captured.logs.warn.length > 0, 'break-glass must emit a warning');
        assert.match(captured.logs.warn.join(' '), /BREAK-GLASS/);
    });

    // --- reserved keys ------------------------------------------------------
    t('a caller-supplied reserved key is refused outside test_mode', () => {
        const { o } = orchestrator();
        const found = o._reservedKeysIn({ _forceWritebackFailure: true });
        assert.equal(found.length, 1, 'reserved key must be detected regardless of case');
    });

    t('reserved-key detection is case-insensitive', () => {
        const { o } = orchestrator();
        assert.equal(o._reservedKeysIn({ _FORCEWRITEBACKFAILURE: true }).length, 1);
        assert.equal(o._reservedKeysIn({ requester_id: 'bob' }).length, 0);
    });

    t('run() stops on a reserved key before any clause is evaluated', () => {
        const { o } = orchestrator();
        let actuated = false;
        const r = o.run(
            { ritm: 'RITM0010001', _forceWritebackFailure: true },
            () => { actuated = true; return { ok: true }; },
            {}
        );
        assert.equal(r.ok, false);
        assert.equal(r.clause, 'environment');
        assert.notOk(actuated, 'actuation must never run');
    });

    // --- environment guard --------------------------------------------------
    t('a failing environment guard stops the run before origin', () => {
        const { o } = orchestrator({
            fields: { env: { guard: () => ({ ok: false, reason: 'prod instance in test_mode' }), isTestMode: () => false } },
        });
        let actuated = false;
        const r = o.run({ ritm: 'RITM1' }, () => { actuated = true; return { ok: true }; }, {});
        assert.equal(r.ok, false);
        assert.equal(r.clause, 'environment');
        assert.notOk(actuated);
    });

    // --- the actuate callback is never invoked on any refusal --------------
    t('no refusal path ever invokes the actuator', () => {
        const cases = [
            {},                                   // no origin
            { sam_request_id: 'SAM-nope' },       // unresolvable SAM id
            { ritm: 'RITM-nope' },                // unresolvable RITM
            { breakglass: true },                 // incomplete break-glass
        ];
        for (const request of cases) {
            const { o } = orchestrator();
            let actuated = false;
            const r = o.run(request, () => { actuated = true; return { ok: true }; }, {});
            assert.equal(r.ok, false, `expected refusal for ${JSON.stringify(request)}`);
            assert.notOk(actuated, `actuator ran for ${JSON.stringify(request)}`);
        }
    });
};
