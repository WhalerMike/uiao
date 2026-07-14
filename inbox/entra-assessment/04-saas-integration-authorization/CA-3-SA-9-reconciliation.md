# Reconciliation memo — CA-3 / AC-20 / SA-9 and outbound SaaS integration

> Status: DRAFT for review · Surface: `inbox/` (not canon) · Date Code: 2026-07-14 08:38 ET
> Scope: **FedRAMP Moderate + Microsoft GCC Moderate** only.
> Proposes edits to `src/uiao/canon/data/control-library/` — none applied.

## The question

An Entra admin follows a [gallery tutorial](https://learn.microsoft.com/en-us/entra/identity/saas-apps/tutorial-list),
configures SAML SSO and SCIM provisioning to a third-party SaaS, and walks away.
A continuous outbound replica of the directory — names, emails, employee IDs,
manager chains, org structure — now lives in that vendor's cloud.

**Which control in our library caught that?**

Answer: none. Not because the library is thin — it has all three candidates —
but because all three contemplate a different direction of travel.

## The finding: a shared directional blind spot

| Control | Status | What its narrative actually covers | Covers outbound SaaS? |
|---|---|---|---|
| `ac/AC-20.yml` | `implemented` | Users reaching **in** from external systems (Entra B2B guests + CA); admins reaching **out** to partner systems via CyberArk PSM; portable storage | **No** |
| `ca/CA-3.yml` | `Implemented` | Network interconnections (VNet peering, VPN, ExpressRoute); Entra federated trust with **partner organizations**; ISAs/MOUs | **No** |
| `sa/SA-9.yml` | `not-implemented` | External service providers; FedRAMP authorization verification; ISAs | **Yes — and it's the one not implemented** |

This is not three separate gaps. It is one gap, three times: **every control
models an external party reaching in, or two systems peering. None models our
IdP pushing a directory replica out to a SaaS relying party.**

Two of the three are marked implemented on the strength of narratives that never
contemplated the flow. The third — which does contemplate it, precisely — is
`not-implemented`.

### Why I am not calling CA-3 a false claim

CA-3's narrative says *"Entra ID federated trust relationships govern identity
exchange with partner organizations."* A SaaS relying party is arguably not a
"partner organization," and CA-3's evidence (ISAs/MOUs, network boundary
diagrams, data-flow diagrams) is coherent for the interconnections it does
describe.

So CA-3 has a **coverage hole**, not a lie. The distinction matters for how we
fix it: CA-3's implemented claim should be **narrowed to what it covers**, not
revoked. Revoking it would understate a control that is genuinely operating for
network interconnections.

The same reading applies to AC-20. Its CyberArk PSM and Palo Alto NGFW
mechanisms are real; they just govern the opposite direction from the one at
risk.

### SA-9 is already right — it was just never stood up

`sa/SA-9.yml` needs no rewrite. It already says the correct thing:

- `PARAM-SA-009-001` → *"FedRAMP authorization required for cloud services"*
- narrative → *"All cloud service providers must maintain a current FedRAMP
  authorization at the Moderate impact level or higher."*
- `evidence:` already names `fedramp-marketplace-authorization-verifications`
  **and** `entra-id-external-application-registrations`

The rule exists, names its own evidence, and produces none of it. `SA-9(2)` is
`not-implemented` on the same footing.

**The gap is not conceptual. It is that SA-9 was specified and never
implemented.** That is a much cheaper problem than it looks.

## Why there is no technical backstop

FedRAMP Moderate for M365 means **GCC Moderate**, which is paired with
**Commercial Entra ID on Azure Commercial infrastructure** — only GCC High and
DoD sit on Azure Government Entra ID.

So a GCC Moderate tenant has the **full commercial gallery**: thousands of apps,
full SSO, full provisioning connectors, nothing blocked, nothing marked. The
tutorials never mention FedRAMP or boundary. Microsoft's own gallery risk score
names SOC 2, ISO 27001, HIPAA and PCI as compliance factors — **not FedRAMP** —
and is licensed behind Entra Suite / Internet Access.

**The entire control surface is administrative.** SA-9 is the only gate, and
it's open.

## Cross-corpus observation — the AAN series has the same blind spot

Worth recording because it suggests the omission is systemic rather than an
oversight in one library. Across AAN Vol VII (ServiceNow), Vol VIII (DDI) and
Vol IX (Day-2), on `main`:

- `gallery`, `SCIM`, `enterprise app`, `tutorial` → **zero hits**
- `SA-9`, `AC-20`, `CA-3` → **zero hits**

`Vol_IX_Book_03_FedAAN_App_Registration_Governance.qmd` (Lane E) is the closest
match and governs the app-registration lifecycle well — request → scoped consent
→ short-lived credential → rotate → attest, closing AC-2, AC-6, IA-5(2), SC-17,
CA-7. But it opens by defining its subject as *"a workload identity: a service
principal with credentials and consented permissions"* — **single-tenant machine
identity calling in**. It has zero hits for third-party, external service,
outbound, federation, trust, or relying party.

Lane E is inbound-scoped in exactly the way AC-20 is. Same blind spot,
independently arrived at.

Two AAN mechanisms are nonetheless the right precedents to borrow:

1. **Vol 0 Book 01 Product Inventory Questionnaire** + *"verify on the FedRAMP
   Marketplace at procurement"* (Vol VII Book 00) — the series already has a
   FedRAMP-status verification discipline. It is scoped to products the series
   *deploys* (ServiceNow, Infoblox), not SaaS an agency *integrates*. The
   discipline generalizes; the scope needs widening.
2. **The Universal DDI SaaS boundary gate** (Vol VIII Book 00) — *"the Universal
   DDI SaaS path is gated by an explicit boundary acknowledgment."* This is the
   only place in the corpus where a third-party SaaS gets an explicit boundary
   treatment. **It is the pattern to generalize**, and it is already ours.

> **Doctrine note:** per the AAN↔UIAO integration doctrine, AAN stands alone via
> the open evidence contract and UIAO stays out of the AAN corpus. Nothing here
> proposes an AAN edit. This section is evidence that the directional gap is
> systemic, and a pointer to two AAN patterns worth reusing on the UIAO side.

## Proposed resolution

**Recommended: narrow the two, implement the third.** Do not widen AC-20/CA-3 to
cover outbound SaaS — that would extend an implemented claim over a flow with no
evidence behind it, which is strictly worse than the current state.

### 1. `sa/SA-9.yml` — implement, don't rewrite

Produce the two artifacts it already declares, via
[`scripts/Get-EntraSaaSIntegrationInventory.ps1`](./scripts/Get-EntraSaaSIntegrationInventory.ps1):

```yaml
# sa/SA-9.yml
status: not-implemented   # → implemented, ONLY once both artifacts exist:
                          #   - entra-id-external-application-registrations
                          #   - fedramp-marketplace-authorization-verifications
```

Flip to `implemented` only when both files are real and on a review cadence.
Not before.

### 2. `ca/CA-3.yml` — scope the claim, add the SaaS case

Add an explicit parameter for the outbound case rather than letting it hide
inside the partner-federation sentence:

```yaml
parameters:
  - id: PARAM-CA-003-003
    text: >-
      Outbound identity-data flows to third-party SaaS relying parties
      (SCIM provisioning from Entra ID) constitute interconnections and
      require an ISA. SSO-only integrations, which pass assertions at
      authentication time without a standing data replica, do not.
    value: "ISA required for SCIM-provisioned integrations"
related_controls:
  - SA-9   # already present — this is the dependency that carries the SaaS case
```

The script's `RequiresIsaUnderCa3` column is the population this parameter
governs.

### 3. `ac/AC-20.yml` — state the direction it covers

One narrative sentence, so the hole is visible instead of implied:

> AC-20 governs access **to** organizational systems **from** external systems,
> and privileged administrative access **to** external partner systems. Outbound
> replication of organizational identity data **to** third-party SaaS providers
> is governed by **SA-9** (external service authorization) and **CA-3**
> (interconnection agreements), not by this control.

### 4. Confirm AC-20(1) against the SSP before treating it as a gap

`ac/AC-20(1).yml` ("Limits on Authorized Use") does not exist. It is the most
on-point enhancement here — verify the external system's controls before
permitting use. **But** `index.yaml` declares the library a deliberate
**247-of-323** curation, with the SSP (**UIAO_185 §3**) carrying the remainder at
summary level. Check the SSP before calling this missing. Same for whether the
SSP already carries SA-9 differently than the library does.

## Sequencing

1. Run Track 4 read-only against the tenant → get the real integration count and
   the SCIM subset. **The size of the problem is currently unknown**, and every
   recommendation above is cheaper or dearer depending on it.
2. Take the `SCIM_UNVERIFIED` risk cell to the ISSO first — standing directory
   data in an unverified CSO.
3. Apply edits 2 and 3 (narrowing) — these are honest immediately, independent
   of the inventory.
4. Apply edit 1 (SA-9 → implemented) only once the artifacts exist and have an
   owner and a cadence.

## Dependency — the status-casing defect

`ca/CA-3.yml` uses `status: Implemented` (capital I). It is one of **31** files
that do, against 101 lowercase `implemented` and 117 `not-implemented`.
`oscal/generator.py:311` and `ssp.py:522` compare the string exactly against
lowercase, and `check_control_library.py` does not validate the field at all —
so those 31 controls match neither bucket and the generated SSP summary
undercounts.

**CA-3 is therefore already invisible to the generated summary.** Any
reconciliation that reasons from generated output rather than the YAML will
mis-read CA-3's state. Fix the casing first (spawned task `task_7dc02ea6`) or
read the source files directly.

## Open questions for review

1. Is `RequiresIsaUnderCa3 = HasScimProvisioning` the right line? A password-SSO
   gallery app stores credentials in Entra and replays them — arguably a
   standing flow too, though of secrets rather than directory data.
2. Should SA-9 distinguish *Li-SaaS* from full Moderate authorization? The
   marketplace export does; `PARAM-SA-009-001` currently says only "Moderate or
   higher."
3. Does the SSP's all-323 mapping already claim SA-9 as implemented? If so, the
   library and the SSP disagree, and that is a bigger finding than this memo.
