// Script Include: InfobloxDDIGate  (application scope: x_infoblox_ddi)
// -----------------------------------------------------------------------------
// Post-apply validation gate. Dispatches the MID Server wrapper
// (mid/infoblox-ddi-validate.sh) which runs the three validation scripts shipped
// in each platform package (dns-validation / discovery-sync-check /
// ipam-conflict-check) and returns one JSON verdict. A non-"pass" overall fails
// the Flow so the change is not marked complete.
//
// Runs the checks on the MID Server so the credential + execution path stays
// inside the ATO boundary (Chapter 7 §7.4).
//
// STARTER SKELETON — wire the ECC/command execution to your MID Server capability
// model; the parse contract below matches infoblox-ddi-validate.sh's single-line
// JSON output (the wrapper this Script Include dispatches on runGate()).
// -----------------------------------------------------------------------------
var InfobloxDDIGate = Class.create();
InfobloxDDIGate.prototype = {

    initialize: function () {
        this.midServer = gs.getProperty('x_infoblox_ddi.mid_server', '');
        this.log = new GSLog('x_infoblox_ddi.log', 'InfobloxDDIGate');
    },

    // env: object of the DDI_VIP / TEST_FQDN / EXPECTED_IP / GRID_MASTER / ...
    // values (sourced from the request + credential alias). Returns:
    //   { overall: 'pass'|'fail', checks: [{name, exit}], raw: '<stdout>' }
    runGate: function (env) {
        var verdict = { overall: 'fail', checks: [], raw: '' };
        try {
            var stdout = this._execOnMid('infoblox-ddi-validate.sh', env);
            verdict.raw = stdout;
            var parsed = JSON.parse(stdout);
            verdict.overall = parsed.overall || 'fail';
            verdict.checks = parsed.checks || [];
        } catch (e) {
            this.log.logErr('runGate parse/exec failed: ' + e);
            verdict.overall = 'fail';
        }
        return verdict;
    },

    // Convenience for a Flow Action: returns true only when every check passed.
    passed: function (env) {
        return this.runGate(env).overall === 'pass';
    },

    // Dispatch to the MID Server. Implement with your standard pattern —
    // an ECC queue "command" probe, a Scripted REST callback, or the
    // MIDServer/Command capability. Env vars are passed to the wrapper.
    _execOnMid: function (script, env) {
        // SKELETON — ILLUSTRATIVE, NOT RUNNABLE AS-IS. A MID probe is asynchronous:
        // probe.create() enqueues an ECC job and the response arrives later on an
        // ecc_queue record — there is no synchronous getResponse(), so the fallback
        // below would always return 'fail'. Rework this into the async pattern before
        // use: run the gate from a MID "command"/Scripted-REST step and resume the
        // Flow on the ECC response, or use an orchestration Activity that blocks on it.
        // Also note JavascriptProbe runs JavaScript on the MID; to run the bash
        // wrapper use a CommandProbe (or a shell-invoking script). Left inline only to
        // show the shape (name → invocation → verdict string).
        var probe = new global.JavascriptProbe(this.midServer);
        probe.setName('x_infoblox_ddi.validate');
        probe.setJavascript(this._buildInvocation(script, env));
        probe.create();          // enqueues async ECC job; response handled separately
        return probe.getResponse ? probe.getResponse() : '{"overall":"fail","checks":[]}';
    },

    _buildInvocation: function (script, env) {
        var exports = '';
        for (var k in env) exports += 'export ' + k + '=' + JSON.stringify('' + env[k]) + '; ';
        return exports + 'bash ' + gs.getProperty('x_infoblox_ddi.mid_scripts_dir',
            '/opt/servicenow/mid/agent/scripts/ddi') + '/' + script;
    },

    type: 'InfobloxDDIGate'
};
