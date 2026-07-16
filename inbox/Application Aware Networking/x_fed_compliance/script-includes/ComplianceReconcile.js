// Script Include: ComplianceReconcile  (application scope: x_fed_compliance)
// -----------------------------------------------------------------------------
// The CM-8 join (Vol VII Book 01): every finding's asset is bound to its
// authoritative IPAM/DDI-keyed CI BEFORE a task is raised. DDI stays the SSOT;
// the CMDB is the workflow projection.
//
// The invariant that makes governance real: NO CI, NO TASK. An asset that
// cannot be reconciled is not silently worked anyway — the unreconciled asset
// becomes its own finding (it means the inventory is wrong, which is the more
// serious defect). This is the atf-negative-unreconciled test.
// -----------------------------------------------------------------------------
var ComplianceReconcile = Class.create();
ComplianceReconcile.prototype = {

    initialize: function () {
        // Scoped logging via gs.* (a scoped app cannot `new GSLog(...)` a global
        // Script Include unprefixed; gs.warn/error always resolve).
        this.log = {
            logErr: function (m) { gs.error('[x_fed_compliance.ComplianceReconcile] ' + m); },
            logWarning: function (m) { gs.warn('[x_fed_compliance.ComplianceReconcile] ' + m); }
        };
        this.testMode = gs.getProperty('x_fed_compliance.test_mode', 'false') === 'true';
    },

    // Bind one finding to its CI. Returns {ok, ciSysId, reason}.
    reconcile: function (finding) {
        if (this.testMode) {
            // Fixture: assets named fixture-* reconcile; 'unreconciled-*' do not.
            if (String(finding.asset).indexOf('unreconciled-') === 0)
                return { ok: false, ciSysId: null, reason: 'no CI carries this asset (fixture)' };
            return { ok: true, ciSysId: 'fixture-ci-sysid', reason: 'test_mode' };
        }
        // The join key is the IPAM/DDI-reconciled identity Discovery/Service Graph
        // wrote to the CI (Vol VII Book 01) — correlation_id here; adjust per tenant.
        var gr = new GlideRecord('cmdb_ci');
        gr.addQuery('correlation_id', finding.asset);
        gr.query();
        if (gr.next()) return { ok: true, ciSysId: gr.getUniqueValue(), reason: 'joined on correlation_id' };
        return { ok: false, ciSysId: null, reason: 'no CI carries asset ' + finding.asset };
    },

    // The no-CI path: raise the inventory defect instead of the original task.
    raiseUnreconciled: function (finding) {
        this.log.logWarning('unreconciled asset ' + finding.asset + ' — booking the inventory defect under the CA-7 conmon rollup (attest.conmon.rollup); the CM-8 inventory control itself closes in Vol VII Book 01. Suppressing the original task.');
        return { 'class': 'attest.conmon.rollup', asset: finding.asset, observed: 'NOT_IN_CMDB', intended: 'RECONCILED_TO_DDI', source: 'ComplianceReconcile' };
    },

    type: 'ComplianceReconcile'
};
