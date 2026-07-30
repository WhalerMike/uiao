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
        // TEST MODE — see InfobloxDDIClient. When x_infoblox_ddi.test_mode = 'true',
        // runGate() returns a canned verdict so ATF can run the Flow's gate step
        // without a MID Server or live validation scripts. Set
        // x_infoblox_ddi.test_force_gate_fail = 'true' to force a FAIL verdict — this
        // is how the negative ATF test proves a failed gate routes back to approval
        // and does NOT close the change. Never enable either in production.
        this.testMode = gs.getProperty('x_infoblox_ddi.test_mode', 'false') === 'true';
        this.testForceGateFail = gs.getProperty('x_infoblox_ddi.test_force_gate_fail', 'false') === 'true';
    },

    // env: object of the DDI_VIP / TEST_FQDN / EXPECTED_IP / GRID_MASTER / ...
    // values (sourced from the request + credential alias). Returns:
    //   { overall: 'pass'|'fail', checks: [{name, exit}], raw: '<stdout>' }
    runGate: function (env) {
        if (this.testMode) {
            if (this.testForceGateFail) {
                return {
                    overall: 'fail',
                    checks: [
                        { name: 'dns', exit: 0 },
                        { name: 'discovery-sync', exit: 0 },
                        { name: 'ipam-conflict', exit: 1 }
                    ],
                    raw: '{"overall":"fail","checks":[{"name":"ipam-conflict","exit":1}],"note":"test_mode force-fail"}'
                };
            }
            return {
                overall: 'pass',
                checks: [
                    { name: 'dns', exit: 0 },
                    { name: 'discovery-sync', exit: 0 },
                    { name: 'ipam-conflict', exit: 0 }
                ],
                raw: '{"overall":"pass","checks":[],"note":"test_mode"}'
            };
        }
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

    // Names the wrapper is permitted to export. Anything else is dropped and
    // logged. Keep in sync with the wrapper's own allowlist — both sides
    // validate; neither trusts the other.
    ALLOWED_ENV: ['SCRIPTS_DIR', 'DDI_VIP', 'TEST_FQDN', 'EXPECTED_IP',
                  'PRIVATELINK_FQDN', 'PRIVATELINK_EXPECTED_IP',
                  'GRID_MASTER', 'INFOBLOX_USERNAME', 'INFOBLOX_PASSWORD',
                  'WAPI_VERSION', 'DDI_API_FLAVOR', 'STALE_THRESHOLD_MIN',
                  'DNS_TIMEOUT', 'DNS_PORT'],

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
        // show the shape (name → invocation → verdict string). The injection fix below
        // is independent of that rework and should be carried into whichever dispatch
        // pattern you land on.
        var probe = new global.JavascriptProbe(this.midServer);
        probe.setName('x_infoblox_ddi.validate');
        probe.setJavascript(this._buildInvocation(script, env));
        probe.create();          // enqueues async ECC job; response handled separately
        return probe.getResponse ? probe.getResponse() : '{"overall":"fail","checks":[]}';
    },

    // SER-1 remediation: single opaque argument, no interpolation of caller
    // data into shell text. The old version built `export k=...` lines by
    // string concatenation — JSON.stringify quotes a VALUE for bash but does
    // not stop $()/backtick command substitution inside double quotes, and the
    // KEY was never escaped at all (the same defect class as
    // AdHybridClient._render in the Day-2 kit — two independent instances
    // means this was a house pattern, not a one-off). Here the env map is
    // JSON-serialized, base64-encoded, and passed as ONE argv element; the
    // wrapper (mid/infoblox-ddi-validate.sh) decodes it and exports only
    // allowlisted names via a plain assignment, which bash never re-parses.
    _buildInvocation: function (script, env) {
        var safe = this._filterEnv(env);
        var json = JSON.stringify(safe);
        var b64 = GlideStringUtil.base64Encode(json);

        // b64 is [A-Za-z0-9+/=] by construction, so it cannot carry shell
        // metacharacters. The script name and directory come from properties,
        // never from the request. Nothing else is concatenated.
        if (!/^[A-Za-z0-9+/=]+$/.test(b64)) {
            this.log.logErr('_buildInvocation: encoded payload failed its own charset check — refusing to dispatch');
            return 'exit 64';
        }
        if (!/^[A-Za-z0-9._-]+$/.test('' + script)) {
            this.log.logErr('_buildInvocation: illegal script name — refusing to dispatch');
            return 'exit 64';
        }

        var dir = gs.getProperty('x_infoblox_ddi.mid_scripts_dir',
                                 '/opt/servicenow/mid/agent/scripts/ddi');
        return "bash '" + dir.replace(/'/g, "'\\''") + "/" + script + "' --env-b64 " + b64;
    },

    // Allowlist filter. Values are carried as JSON, so they need no escaping —
    // but names are still constrained to bare identifiers so a malformed key
    // cannot survive into the wrapper's export loop.
    _filterEnv: function (env) {
        var out = {};
        env = env || {};
        for (var k in env) {
            if (!env.hasOwnProperty(k)) continue;
            if (!/^[A-Z][A-Z0-9_]*$/.test(k)) {
                this.log.logErr('_filterEnv: dropped illegal env name');
                continue;
            }
            if (this.ALLOWED_ENV.indexOf(k) === -1) {
                this.log.logErr('_filterEnv: dropped env name not on the allowlist: ' + k);
                continue;
            }
            out[k] = '' + env[k];
        }
        return out;
    },

    type: 'InfobloxDDIGate'
};
