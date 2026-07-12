# Flow blueprint — "Governed Day-2 Request"

The Flow Designer flow that ties the Day-2 Operations app together. Flow exports
are large opaque XML; this blueprint documents the trigger, steps, and inline
Action scripts so an admin (or a partner) can rebuild it in Flow Designer exactly.
It implements the request loop from Vol IX Book 01.

**Scope:** `x_ssa_day2_ops` · **Run as:** the app's least-privilege service account
· **Trigger:** Service Catalog — any Day-2 catalog item submitted.

## Canonical order

**pre-flight (safety) → approval (the gate the control requires) → actuate (Graph
via MID) → verify gate → reconcile to CMDB → close with evidence.** Safety is checked
*before* approval so a bad request (self-approval, standing privilege) fails fast.

## Steps

1. **Trigger — Catalog item submitted.** Inputs = the catalog variables (target
   identity, action, justification, expiry). The item's `control_key` maps into
   `servicenow-day2/helpdesk-control-map.json` to pick the control, approval gate,
   KSI, and slot.

2. **Pre-flight safety (Action → Script, `EntraHelpdeskGate.preflight`).** Enforces
   separation of duties (requester ≠ approver, CM-5) and least privilege (a
   privileged grant must carry an expiry, AC-6). A failure ends the flow with a
   refusal the requester can read — before any approval or actuation.
   ```javascript
   (function execute(inputs, outputs) {
     var g = new x_ssa_day2_ops.EntraHelpdeskGate();
     var v = g.preflight({ requester_id: inputs.requester_id, approver_id: inputs.approver_id,
                           privileged: inputs.privileged, expiry: inputs.expiry });
     outputs.ok = v.ok; outputs.reason = v.reason;
   })(inputs, outputs);
   ```

3. **Approval.** The gate the control requires (per the control map): self-service
   (SSPR/unlock), manager, identity, owner+approver, or **security approver** for a
   Conditional-Access exception or any privileged grant. Reuses the Vol VII Book 02
   CA-exception approval for that item — no second path.

4. **Actuate (Action → Script, `EntraHelpdeskClient`).** The one client method for
   the requested action — `createUser` / `disableUser` / `resetPassword` /
   `resetMfaMethod` / `addGroupMember` / `assignLicense` / `inviteGuest` — each a
   **MID-routed** Graph call. ServiceNow never holds standing tenant admin.
   ```javascript
   (function execute(inputs, outputs) {
     var c = new x_ssa_day2_ops.EntraHelpdeskClient();
     var r = c[inputs.action](inputs.target_id, inputs.opts);   // dispatch by action
     outputs.ok = r.ok; outputs.result = JSON.stringify(r);
   })(inputs, outputs);
   ```

5. **Verify gate (Action → Script, `EntraHelpdeskGate.verify`).** Re-reads the target
   through Graph and confirms the intended state took — closure by observation, not
   by a 200. Produces the evidence object.

6. **Reconcile to CMDB.** Update the reconciled identity CI (CM-8 join key) with the
   action outcome; a target that does not match an authoritative identity routes to
   the reconcile-exception queue (Vol VII Book 01).

7. **Close with evidence.** Stamp the request with the approval trail, the Graph
   result, and the verify evidence as a change record (CM-3 / AU-2); emit to the
   evidence contract for Vol VII Book 04 attestation. A failed gate returns the
   request to approval rather than closing.

## Companion flows

- **Access-review flow** — drives expiry/re-attestation for time-bound grants and
  Conditional-Access exceptions (AC-6).
- **Leaver-completion flow** — confirms de-provision evidence (disabled, sessions
  revoked, owned objects reassigned) before closing an AC-2 leaver.
