// Script Include: Day2Env  (application scope: x_fed_day2_ops)
// =============================================================================
// NEW — closes P0-5: `test_mode` was a bare sys_properties boolean that made
// every client return canned successes AND canned post-state. Set true on a
// production instance (update-set promotion, admin error, clone-back from
// sub-prod) it produced a complete, plausible, FALSE evidence trail indexed to
// real NIST controls, and the attestation pipeline downstream could not tell.
//
// Three defences, because a procedural control on an integrity property is the
// wrong control class:
//
//   1. ENVIRONMENT BINDING. test_mode is honoured only on an instance whose
//      name appears in x_fed_day2_ops.nonprod_instances. On any other instance
//      the property is IGNORED and, if set, the app refuses to actuate at all
//      (isRefusing) — because a production instance carrying test_mode=true is
//      evidence of a promotion mistake, and continuing in either direction is
//      worse than stopping.
//
//   2. STAMPING. Every evidence record produced while test_mode is honoured
//      carries test_mode:true and a synthetic marker. The attestation pipeline
//      must reject those rows rather than rely on a human noticing.
//
//   3. BUILD ASSERTION. assertProductionSafe() is callable from a promotion
//      check / the pilot go-live gate; see also check_actuator_coverage.py.
//
// Also hosts scrub(), the shared log sanitiser (P2 log injection), so every
// client uses one implementation instead of four.
// =============================================================================
var Day2Env = Class.create();

// Static so callers can sanitise without instantiating.
Day2Env.scrub = function (msg) {
    return ('' + msg).replace(/[\r\n\t]+/g, ' ').slice(0, 1000);
};

Day2Env.prototype = {

    initialize: function () {
        this.instance = gs.getProperty('instance_name', '');
        this.propTestMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
        this.nonProd = this._nonProdList();
        this.isNonProd = this._matchesNonProd(this.instance);
    },

    _nonProdList: function () {
        var raw = gs.getProperty('x_fed_day2_ops.nonprod_instances', '');
        var out = [], parts = raw.split(',');
        for (var i = 0; i < parts.length; i++) {
            var p = parts[i].trim().toLowerCase();
            if (p) out.push(p);
        }
        return out;
    },

    _matchesNonProd: function (name) {
        var n = ('' + name).trim().toLowerCase();
        if (!n) return false;                      // unknown instance is treated as production
        for (var i = 0; i < this.nonProd.length; i++) {
            if (n === this.nonProd[i]) return true;
        }
        return false;
    },

    // The only test_mode check any client should use.
    isTestMode: function () {
        return this.propTestMode && this.isNonProd;
    },

    // True when the property is set on an instance not declared non-production.
    // Clients MUST refuse to actuate in this state — it means either the
    // property or the allowlist is wrong, and guessing which is not safe.
    isRefusing: function () {
        return this.propTestMode && !this.isNonProd;
    },

    // Fail-closed guard for clients. Call at the top of any actuation.
    guard: function () {
        if (this.isRefusing()) {
            gs.error('[x_fed_day2_ops.Day2Env] REFUSING TO ACTUATE: x_fed_day2_ops.test_mode is true on instance "' +
                     Day2Env.scrub(this.instance) + '", which is not listed in x_fed_day2_ops.nonprod_instances. ' +
                     'Either this is a production instance carrying a sub-prod property (fix the property) or the ' +
                     'allowlist is incomplete (fix the allowlist). The app will not run until one of those is true.');
            return { ok: false, reason: 'test_mode set on an instance not declared non-production — refusing to actuate' };
        }
        return { ok: true };
    },

    // Deterministic fixture value for test_mode. Deliberately narrow: it may
    // supply an INPUT a test needs, never an OBSERVATION. Clients must not use
    // this to fabricate post-state.
    testFixture: function (key, fallback) {
        var v = gs.getProperty('x_fed_day2_ops.test_fixture_' + key, null);
        if (v === null || v === '') return fallback;
        if (v === 'true') return true;
        if (v === 'false') return false;
        return v;
    },

    // Fields every evidence record must carry so synthetic rows are machine-
    // detectable downstream rather than visually detectable by a reader.
    evidenceStamp: function () {
        return {
            instance: this.instance,
            boundary: gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate'),
            test_mode: this.isTestMode(),
            synthetic: this.isTestMode(),
            stamped_at: new GlideDateTime().getValue()
        };
    },

    // Callable from a promotion gate or the pilot checklist. Returns
    // { ok, problems[] }.
    assertProductionSafe: function () {
        var problems = [];
        if (this.propTestMode)
            problems.push('x_fed_day2_ops.test_mode is true on instance "' + this.instance + '"');
        if (!this.nonProd.length)
            problems.push('x_fed_day2_ops.nonprod_instances is empty — the environment binding cannot work');
        if (!gs.getProperty('x_fed_day2_ops.ad_managed_ous', ''))
            problems.push('x_fed_day2_ops.ad_managed_ous is empty — AD writes will fail closed (intended, but blocks the pilot)');
        return { ok: problems.length === 0, problems: problems };
    },

    type: 'Day2Env'
};
