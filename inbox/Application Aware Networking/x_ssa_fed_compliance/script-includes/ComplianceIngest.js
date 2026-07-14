// Script Include: ComplianceIngest  (application scope: x_ssa_fed_compliance)
// -----------------------------------------------------------------------------
// Step 1-2 of the loop (test -> detect): READ-ONLY pull of native control state
// from the two surfaces that carry most federal control work —
//   * M365:  Graph secureScoreControlProfiles + Conditional Access policy state,
//            SCuBA baseline results, Purview label/DLP posture
//   * Azure: Resource Graph posture queries, Defender for Cloud assessments,
//            Update Manager patch state
// Every callout is routed through the in-boundary MID Server; the service
// identity is READ + task-creation only (Vol VII Book 00 doctrine). Drift =
// (observed != intended baseline) => a finding record, classified against
// data/control-map.json by finding class key.
//
// test_mode (x_ssa_fed_compliance.test_mode) returns deterministic fixtures so
// ATF runs with no live tenant. Never enable in production.
// -----------------------------------------------------------------------------
var ComplianceIngest = Class.create();
ComplianceIngest.prototype = {

    initialize: function () {
        this.log = new GSLog('x_ssa_fed_compliance.log', 'ComplianceIngest');
        this.testMode = gs.getProperty('x_ssa_fed_compliance.test_mode', 'false') === 'true';
        this.midServer = gs.getProperty('x_ssa_fed_compliance.mid_server', '');
        this.boundary = gs.getProperty('x_ssa_fed_compliance.boundary', 'gcc-moderate');
    },

    // Pull M365 control state. Returns [{class, asset, observed, intended, source}].
    ingestM365: function () {
        if (this.testMode) return this._fixture('m365');
        var findings = [];
        findings = findings.concat(this._rest('graph', '/v1.0/identity/conditionalAccess/policies', 'm365.account.exception'));
        findings = findings.concat(this._rest('graph', '/beta/security/secureScoreControlProfiles', 'm365.baseline.drift'));
        // SCuBA results land as a MID file drop (mid/compliance-validate.sh) —
        // ingest the verdict JSON rather than re-running the scan here.
        return findings;
    },

    // Pull Azure control state. Returns the same finding shape.
    ingestAzure: function () {
        if (this.testMode) return this._fixture('azure');
        var findings = [];
        findings = findings.concat(this._rest('arm', '/providers/Microsoft.Security/assessments?api-version=2021-06-01', 'azure.vuln.finding'));
        findings = findings.concat(this._rest('arm', '/providers/Microsoft.Maintenance/updates?api-version=2023-04-01', 'azure.patch.remediation'));
        return findings;
    },

    // One outbound REST call via the MID-routed sys_rest_message (rest/README.md).
    // Returns [] on error — a failed READ must never fabricate a clean posture,
    // so the failure itself is raised as an attest.conmon.rollup finding.
    _rest: function (messageName, path, findingClass) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_ssa_fed_compliance.' + messageName, 'get');
            rm.setStringParameterNoEscape('path', path);
            if (this.midServer) rm.setMIDServer(this.midServer);
            var resp = rm.execute();
            if (resp.getStatusCode() !== 200) {
                this.log.logErr('read failed ' + messageName + path + ' -> ' + resp.getStatusCode());
                return [{ 'class': 'attest.conmon.rollup', asset: messageName, observed: 'READ_FAILED', intended: 'READABLE', source: path }];
            }
            return this._classify(JSON.parse(resp.getBody()), findingClass, path);
        } catch (e) {
            this.log.logErr('ingest exception: ' + e);
            return [{ 'class': 'attest.conmon.rollup', asset: messageName, observed: 'READ_FAILED', intended: 'READABLE', source: path }];
        }
    },

    // Compare observed state to the intended baseline (per-tenant table
    // x_ssa_fed_compliance_baseline). Skeleton: emit one finding per non-compliant
    // entry; the baseline compare is completed per tenant before production use.
    _classify: function (body, findingClass, source) {
        var out = [];
        var rows = (body && body.value) ? body.value : [];
        for (var i = 0; i < rows.length; i++) {
            if (rows[i].state === 'disabled' || rows[i].status === 'Unhealthy') {
                out.push({ 'class': findingClass, asset: rows[i].id || rows[i].name, observed: rows[i].state || rows[i].status, intended: 'compliant', source: source });
            }
        }
        return out;
    },

    _fixture: function (surface) {
        // Deterministic ATF fixtures — one drift finding per surface.
        if (surface === 'm365') return [{ 'class': 'm365.baseline.drift', asset: 'fixture-ca-policy', observed: 'disabled', intended: 'enabled', source: 'test_mode' }];
        return [{ 'class': 'azure.vuln.finding', asset: 'fixture-vm-01', observed: 'Unhealthy', intended: 'Healthy', source: 'test_mode' }];
    },

    type: 'ComplianceIngest'
};
