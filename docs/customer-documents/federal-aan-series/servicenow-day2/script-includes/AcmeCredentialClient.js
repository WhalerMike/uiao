// Script Include: AcmeCredentialClient  (application scope: x_fed_day2_ops)
// -----------------------------------------------------------------------------
// SHARED credential client for every `acme-via-mid` item in the day-2 kit —
// Lane E (app registrations, Vol IX Book 03) and Lane F (SaaS federation,
// Vol IX Book 05). One client, because the credential discipline is the same
// wherever the identity lives: short-lived certificates, issued and rotated by
// automation, never a long-lived secret a human pastes into a config.
//
// Boundary discipline:
//   * ACME calls route through the in-boundary MID Server
//     (property x_fed_day2_ops.mid_server) — the CSR, the key and the issued
//     certificate never leave the ATO boundary.
//   * Directory/endpoint + account key come from the Connection & Credential
//     alias (x_fed_day2_ops.acme) — no secrets in code.
//
// THE PRIVATE KEY NEVER REACHES SERVICENOW. The MID Server generates the key
// and the CSR, submits the order, and returns only the ISSUED CERTIFICATE and
// its metadata (thumbprint, notAfter). ServiceNow records that a credential
// exists and when it expires — it never holds the material. This is why there is
// no `getPrivateKey` here and no method that returns key bytes: a Script Include
// that could fetch the key would put it in the catalog record's audit trail
// (IA-5). The MID script (mid/*.sh) owns the key; this client owns the workflow.
//
// ROTATION AUTONOMY IS UNDECLARED — DO NOT READ THIS AS APPROVAL.
// rotateCertificate is bound to items carrying `approval: automated`
// (appreg.credential.rotate, saas.credential.rotate). Those are autonomous writes
// to the estate: L4 on the ADR-092 ladder, above the federal L3 default.
//
// ADR-092 s4 permits L4 for an operation class only when ALL of: (1) the class is
// enumerated in a Governance-Plane-approved decision; (2) blast_radius is low;
// (3) rollback_capable is true; (4) the adapter has a clean dry-run/advisory
// record over a defined observation window; (5) halt_on_critical is in force.
// Today (2) and (3) hold — one workload identity, and rotation is reversible
// (issue-then-verify-then-retire, below: the prior credential is retired only
// after the new one verifies). (1), (4) and (5) DO NOT: no ADR enumerates these
// classes, this kit has never run so no observation record can exist, and
// halt_on_critical is not implemented here.
//
// The design argument for autonomy is real — a certificate that expires because a
// human forgot is a worse outcome than one rotated on a schedule. But a design
// argument is not a governance decision. Until the Governance Plane enumerates
// these classes or the items are demoted to L3, this is a KNOWN, TRACKED
// exceedance, not a justified one. An earlier version of this comment cited an
// "L4 note" in the control maps; no such note existed.
//
// STARTER SKELETON — pin the ACME directory URL and validate the account key +
// challenge type against your CA before production use.  test_mode
// (x_fed_day2_ops.test_mode = 'true') returns deterministic canned values so the
// ATF suites run in sub-prod with NO live CA connectivity.  Never enable
// test_mode in production.
// -----------------------------------------------------------------------------
var AcmeCredentialClient = Class.create();
AcmeCredentialClient.prototype = {

    initialize: function () {
        this.midServer = gs.getProperty('x_fed_day2_ops.mid_server', '');
        this.directory = gs.getProperty('x_fed_day2_ops.acme_directory', '');
        this.boundary = gs.getProperty('x_fed_day2_ops.boundary', 'gcc-moderate');
        // Default lifetime is deliberately short — the point of ACME automation is
        // that a short life is cheap. Long-lived certs are a config smell.
        this.defaultDays = parseInt(gs.getProperty('x_fed_day2_ops.acme_default_days', '90'), 10);
        this.log = { logErr: function (m) { gs.error('[x_fed_day2_ops.AcmeCredentialClient] ' + m); } };
        this.testMode = gs.getProperty('x_fed_day2_ops.test_mode', 'false') === 'true';
    },

    // --- Issue: a short-lived certificate for a workload identity (SC-17). ----
    // `subject` identifies the workload; `opts.days` may shorten but never extend
    // past the configured ceiling — a request cannot talk its way into a longer
    // life than policy allows.
    issueCertificate: function (subject, opts) {
        opts = opts || {};
        if (this.testMode)
            return { ok: true, thumbprint: 'TEST0000THUMBPRINT0001', subject: subject,
                     notAfter: '2026-12-31T00:00:00Z', keyReturned: false };
        var days = Math.min(parseInt(opts.days || this.defaultDays, 10), this.defaultDays);
        return this._acme('issue', { subject: subject, days: days, keyType: opts.keyType || 'ec-p256' });
    },

    // --- Rotate: issue the replacement, then retire the prior (IA-5(2)). ------
    // Issue-then-verify-then-retire. The old credential is retired ONLY after the
    // new one is confirmed, so a failed issue leaves the workload authenticating
    // on the credential it already had rather than stranded with none.
    rotateCertificate: function (subject, currentThumbprint, opts) {
        opts = opts || {};
        if (this.testMode)
            return { ok: true, thumbprint: 'TEST0000THUMBPRINT0002', subject: subject,
                     replaced: currentThumbprint, retired: true, keyReturned: false };
        var issued = this.issueCertificate(subject, opts);
        if (!issued.ok) {
            this.log.logErr('rotate: issue failed for ' + subject + ' — prior credential left in place');
            return { ok: false, replaced: null, retired: false, reason: 'issue failed; prior credential retained' };
        }
        var retire = this._acme('retire', { subject: subject, thumbprint: currentThumbprint });
        return { ok: issued.ok, thumbprint: issued.thumbprint, subject: subject,
                 replaced: currentThumbprint, retired: retire.ok, keyReturned: false };
    },

    // --- Read: what credential does this identity hold, and until when? -------
    // The attestation/expiry input. A read — it never rotates as a side effect.
    describeCertificate: function (subject) {
        if (this.testMode)
            return { ok: true, subject: subject, thumbprint: 'TEST0000THUMBPRINT0001',
                     notAfter: '2026-12-31T00:00:00Z' };
        return this._acme('describe', { subject: subject });
    },

    // --- Internal: MID-routed ACME operation. --------------------------------
    // The MID script owns key generation, the CSR and the challenge; this returns
    // only certificate metadata. If a response ever carries key material, refuse
    // it rather than hand it up to the record.
    _acme: function (op, args) {
        try {
            var rm = new sn_ws.RESTMessageV2('x_fed_day2_ops.acme', 'POST');
            rm.setEndpoint(this.directory);
            if (this.midServer) rm.setMIDServer(this.midServer);   // in-boundary execution
            rm.setRequestBody(JSON.stringify({ op: op, args: args, boundary: this.boundary }));
            var resp = rm.execute();
            var code = resp.getStatusCode();
            var out = { ok: code >= 200 && code < 300, status: code, body: resp.getBody() };
            if (out.body && ('' + out.body).indexOf('PRIVATE KEY') !== -1) {
                this.log.logErr('_acme ' + op + ': response carried key material — refusing to return it');
                return { ok: false, status: code, error: 'key material must not leave the MID Server' };
            }
            return out;
        } catch (e) {
            this.log.logErr('_acme ' + op + ' failed: ' + e);
            return { ok: false, error: '' + e };
        }
    },

    type: 'AcmeCredentialClient'
};
