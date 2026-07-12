# Chapter 8 — ServiceNow-Led Implementation

Chapters 1–6 build DDI **platform-first**: stand up the appliances, wire discovery
and DNS, then (in each chapter's §8) put a ServiceNow front door on the result.
[Chapter 7](./07-servicenow-orchestration.md) defines that front door. This chapter
turns the order around and makes it a deliberate implementation strategy:
**lead with ServiceNow.** Stand up the governed *experience* — the catalog request,
the approval, the closed-loop flow — **first**, then wire the Terraform and Infoblox
automation *behind* a contract that already exists.

> **Illustrative screens.** The ServiceNow screens in this chapter and its companion
> docs are **mock-ups**, not real screenshots — they communicate the intended look
> and feel. See [`servicenow-app/mockups/`](./servicenow-app/mockups/README.md).
> ServiceNow® is a trademark of its owner and is not affiliated with this material.

## 8.1 Why lead with ServiceNow

The thing an enterprise actually consumes is not a Terraform module — it is *"I need
a subnet, safely, with someone accountable signing off."* When you build that
experience last, you retrofit governance onto plumbing and discover the mismatches
late. When you build it **first**, the catalog form and the approval define the
contract, and every automation decision downstream serves it.

| | Platform-led (Ch. 1–6) | **ServiceNow-led (this chapter)** |
|---|---|---|
| First thing built | vNIOS members, discovery, DNS | The **catalog item, approval, and flow** |
| Governance | Added at §8, after the plumbing | **Designed in from step 1** |
| The Terraform module is… | the starting point | the *fulfillment engine behind* the request |
| Who validates the design | engineers, at the end | requesters/approvers, immediately (the form is the spec) |
| Typical failure avoided | "it works but nobody can request it safely" | "we automated the wrong contract" |

Both paths land in the same place — the closed loop of [Chapter 7](./07-servicenow-orchestration.md).
ServiceNow-led just sequences the build so the **governed front door is the reference
point**, not an afterthought. It suits organizations that already run ServiceNow as
the system of engagement and want DDI to arrive through it like every other service.

## 8.2 What the requester sees first

The design starts at the request, because the request *is* the specification. Every
field maps to a module input (`tfvars`); the form is where the contract is agreed.

![Illustrative ServiceNow catalog request form "Request a DDI-backed subnet": target platform and region selectors, a pre-populated hub network, requested CIDR, environment, deployment model, host FQDN, an acknowledge-SaaS-boundary control, and a business justification, with an order summary rail showing approval required, validated, and CMDB-synced](./servicenow-app/mockups/sn-01-catalog-request.png)

Designing this screen first forces the right questions up front: which fields are
pre-populated from the landing zone (so requesters can't invent hub identifiers),
which are validated (CIDR fits the hub, no overlap), and where the compliance gate
lives (`acknowledge_saas_boundary` for the Universal DDI SaaS path). Those answers
become the module's variable contract — not the other way around.

## 8.3 The closed loop, experience-first

After **Order Now**, the requester tracks one auditable loop — approval → Terraform
apply on the in-boundary MID Server → Infoblox allocate/register → validation gate →
CMDB reconcile → close. Designing the *status view* early makes the loop's stages
explicit before any of them is automated.

![Illustrative ServiceNow request status view for a DDI-backed subnet: a closed-loop progress timeline (submitted, approved, Terraform apply, IPAM allocate and register, validation gate running, CMDB reconcile, close) beside a work-notes stream showing the allocated IP, the Terraform apply result, and the approval](./servicenow-app/mockups/sn-03-request-status.png)

The approval, the flow canvas, and the reconciled CMDB record round out the
experience. The full set of sample screens — catalog, approval, status, Flow
Designer, and CMDB — lives in the [mock-up gallery](./servicenow-app/mockups/README.md).

## 8.4 The inverted build sequence

The detailed, numbered build is the
[**ServiceNow-led build playbook**](./servicenow-app/PLAYBOOK-servicenow-led-build.md).
At a chapter level it runs experience-first:

1. **Prerequisites** — a FedRAMP-authorized ServiceNow instance, a MID Server
   **inside the ATO boundary**, and the two certified Store apps (CPG Terraform
   Connector, Service Graph Connector for Infoblox).
2. **Scoped app** — import the [`servicenow-app/`](./servicenow-app/README.md) records
   (Script Includes, REST Message, MID gate) and set the app properties. These are a
   **labeled starter skeleton** — review, complete the platform variable sets, and test in
   a sub-prod instance before use; they are not a signed, production-certified store app.
3. **Catalog item** — build the request form (§8.2); its variables define the contract.
4. **Flow + approval** — build the closed loop per
   [`flow/flow-blueprint.md`](./servicenow-app/flow/flow-blueprint.md).
5. **Validation gate + IntegrationHub** — wire the MID validation and the Infoblox
   WAPI/Universal DDI calls.
6. **Automation behind it** — *only now* ingest each platform's `terraform/` module
   into the CPG Terraform Connector as the fulfillment engine.
7. **CMDB** — schedule the Service Graph import so IPAM reconciles into `cmdb_ci_ip_network`.
8. **Pilot** — submit, approve, watch the loop, verify — then promote dev → prod.

Note steps 3–4 (the experience) precede step 6 (the plumbing). That is the whole point.

## 8.5 Documentation set

Leading with ServiceNow means the *humans* using it need first-class docs. This
chapter ships three:

| Deliverable | For | Contents |
|---|---|---|
| [Build playbook](./servicenow-app/PLAYBOOK-servicenow-led-build.md) | Implementers | The numbered, experience-first build with the sample screens |
| [User guide](./servicenow-app/USER-GUIDE.md) | Requesters · Approvers · Admins | How to order, approve, run, and troubleshoot the front door |
| [Mock-up gallery](./servicenow-app/mockups/README.md) | Everyone | The five sample screens + how they're rendered |

## 8.6 Boundary & governance (unchanged)

Leading with ServiceNow does not relax the volume's discipline — it applies it earlier:

- The **MID Server stays in-boundary**; the Terraform apply, the REST callouts, and the
  validation gate all run there, so the execution and credential path never leaves the
  ATO boundary.
- **Secrets never enter ServiceNow.** The catalog collects a vault *reference*; the MID
  Server resolves the actual credential at run time.
- The **Universal DDI SaaS path** remains the explicit, `acknowledge_saas_boundary`-gated
  exception, now surfaced as a form control and an extra approval.
- The control-family mapping (AC-5/AC-6, AU-2/AU-6/AU-12, CM-3/CM-5/CM-6/CM-8) is
  inherited from [Chapter 7 §7.4](./07-servicenow-orchestration.md).

---

## Sources

- [Service Graph Connector for Infoblox — ServiceNow Store](https://store.servicenow.com/store/app/eeb927621b246a50a85b16db234bcbf1)
- [Cloud Provisioning & Governance: Terraform Connector — ServiceNow Store](https://store.servicenow.com/store/app/6ff8ef2e1be06a50a85b16db234bcbcb)
- Volume cross-references: [Chapter 7 — ServiceNow Orchestration](./07-servicenow-orchestration.md) ·
  [Chapter 6 §6.9](./06-cross-platform-operations.md) ·
  [Introduction §0.5](./00-introduction.md) ·
  [`servicenow-app/`](./servicenow-app/README.md)
