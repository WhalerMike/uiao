# ServiceNow UI mock-ups (illustrative)

Sample **look-and-feel** of the ServiceNow front door for the Infoblox DDI
implementation — the screens a requester, an approver, and an admin actually
see. They are used by the [ServiceNow-led build playbook](../PLAYBOOK-servicenow-led-build.md)
and the [user guide](../USER-GUIDE.md), and by [Chapter 8](../../08-servicenow-led-implementation.md).

> **These are illustrative mock-ups, not real screenshots.** They resemble a
> ServiceNow Next Experience portal to communicate the intended experience.
> ServiceNow® is a trademark of its owner and is not affiliated with this
> material. Every rendered image carries a visible "ILLUSTRATIVE MOCK-UP" badge
> and a footer disclaimer. Field values (RITM numbers, IPs, names) are fictional.

| Screen | Source | Rendered | Shows |
|---|---|---|---|
| Catalog request | [`sn-01-catalog-request.html`](./sn-01-catalog-request.html) | `sn-01-catalog-request.png` | The "Request a DDI-backed subnet" form (fields mapped to module `tfvars`) |
| Approval | [`sn-02-approval.html`](./sn-02-approval.html) | `sn-02-approval.png` | The approver's SoD gate — what they see, Approve/Reject |
| Request status | [`sn-03-request-status.html`](./sn-03-request-status.html) | `sn-03-request-status.png` | The closed-loop progress timeline + work notes |
| Flow Designer | [`sn-04-flow-designer.html`](./sn-04-flow-designer.html) | `sn-04-flow-designer.png` | The provisioning flow canvas (trigger + 7 actions) |
| CMDB CI | [`sn-05-cmdb-ci.html`](./sn-05-cmdb-ci.html) | `sn-05-cmdb-ci.png` | The reconciled `cmdb_ci_ip_network` record |

## Rendering

The PNGs are produced from the HTML by [`render-mocks.sh`](./render-mocks.sh)
using the preinstalled Chromium at 2× scale (crisp for print/`.docx`). Shared
styling is in [`sn-mock.css`](./sn-mock.css). Edit an `.html` or the CSS, then:

```bash
./render-mocks.sh   # re-renders all five PNGs
```

Heights are tuned per screen in the script so each fits its content. Keep the
mock-up badge and footer disclaimer on every screen.
