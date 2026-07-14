# Track 4 — SaaS integration authorization (SA-9)

> Status: DRAFT · Surface: `inbox/` (not canon) · Date Code: 2026-07-14 08:38 ET
> Scope: **FedRAMP Moderate + Microsoft GCC Moderate** only.

Track 4 answers one question the other three don't ask:

> For every third-party SaaS this tenant is integrated with, **is that service
> FedRAMP authorized at Moderate or higher** — and if it is receiving a
> continuous outbound replica of our directory, **is that interconnection
> covered by an ISA?**

That question is already canon. `src/uiao/canon/data/control-library/sa/SA-9.yml`
states it (`PARAM-SA-009-001`: *"FedRAMP authorization required for cloud
services"*) and names the exact two evidence artifacts that would answer it:

- `entra-id-external-application-registrations`
- `fedramp-marketplace-authorization-verifications`

Neither artifact is produced today, and SA-9 is `status: not-implemented`.
This track produces both.

## Why this track exists — the boundary is administrative, not technical

FedRAMP Moderate for M365 means **GCC Moderate**, and GCC Moderate is paired
with **Commercial Entra ID on Azure Commercial infrastructure**. Only GCC High
and DoD sit on Azure Government Entra ID.

The practical consequence: the **full commercial application gallery is
available** to a GCC Moderate tenant. Thousands of apps, full SSO, full
provisioning connectors. Nothing is blocked, nothing is marked, and the
[gallery tutorials](https://learn.microsoft.com/en-us/entra/identity/saas-apps/tutorial-list)
never mention FedRAMP, boundary, or authorization status.

So there is no technical gate to inventory. The only gate is SA-9, and SA-9
is not implemented. That is the whole gap.

> **Do not file this in `gcc-boundary-gap-registry.yaml` as-is.** That
> registry's `microsoft_status` enum has no value for this condition.
> Everything here is `FUNCTIONAL` — the gap is not that Microsoft blocked
> something, it's that Microsoft blocks *nothing* and SA-9 was supposed to.

## SSO and SCIM are not the same risk

The tutorial list presents them as adjacent columns. Under Moderate they are
different control events, and this track keeps them apart:

| Integration | Data exposure | Control weight |
|---|---|---|
| **SSO** (SAML/OIDC/password) | An assertion at authentication time; transient | SA-9 — is the service authorized? |
| **SCIM provisioning** | A **durable, continuously synced replica** of the directory — names, emails, employee IDs, manager chains, org structure | SA-9 **+ CA-3** — an interconnection needing an ISA |

A SCIM-provisioned unauthorized SaaS is the worst cell in the matrix: standing
federal identity data resident in a CSO with no authorization and no agreement.
The script reports that cell explicitly.

## What Track 3 already gives us

`03-stale-inventory-review/scripts/Get-EntraStaleAppInventory.ps1` already
detects gallery apps — it just doesn't know that's what it's doing. Its
`MULTI_TENANT_HOME_ELSEWHERE` disposition fires when a service principal
exists in the tenant with no matching app registration homed here. **That is
the signature of a gallery app**: the vendor owns the app registration in
their tenant; you hold only the service principal.

Track 4 starts exactly where Track 3 stops, and uses a stronger marker:
`servicePrincipal.applicationTemplateId`. Non-null means the SP was
instantiated from a gallery template.

## The script

[`scripts/Get-EntraSaaSIntegrationInventory.ps1`](./scripts/Get-EntraSaaSIntegrationInventory.ps1)

Read-only. For every gallery-instantiated service principal it records the SSO
mode, whether a SCIM synchronization job exists, the app's owners and consent
grants, and — if you supply a FedRAMP Marketplace export — an authorization
match verdict.

```powershell
Connect-MgGraph -Scopes Application.Read.All, Directory.Read.All, `
    AuditLog.Read.All, Synchronization.Read.All, `
    DelegatedPermissionGrant.Read.All, AppRoleAssignment.Read.All

# Inventory only — no authorization verdict
./scripts/Get-EntraSaaSIntegrationInventory.ps1 -OutputPath ./out

# With the FedRAMP join
./scripts/Get-EntraSaaSIntegrationInventory.ps1 -OutputPath ./out `
    -FedrampMarketplacePath ./fedramp-moderate-export.csv
```

### Getting the FedRAMP Marketplace export

There is no stable public API, and the script deliberately does not scrape one.
Export it by hand from [fedramp.gov/marketplace](https://www.fedramp.gov/marketplace/)
(the old `marketplace.fedramp.gov` is deprecated and redirects), filtered to
**Authorized** at **Moderate or High**. The marketplace offers CSV and JSON
export of a filtered result set.

The script needs one column containing the service offering name. It
auto-detects common headers (`Cloud Service Offering`, `CSO`, `Service Name`,
`Name`); override with `-FedrampNameColumn` if yours differs.

## The verdicts — and the one this script will never emit

Name-matching an Entra gallery display name against a FedRAMP service offering
name is **unreliable**. "Atlassian Cloud" in the gallery is not obviously the
same record as "Atlassian Cloud for Government" on the marketplace, and a
confident-looking wrong answer here is worse than no answer.

So the script emits:

| Verdict | Meaning |
|---|---|
| `AUTHORIZED_EXACT` | Normalized name matched a marketplace row exactly |
| `AUTHORIZED_FUZZY_VERIFY` | Token-subset match — **plausible, must be confirmed by a human** |
| `NO_MATCH_VERIFY_MANUALLY` | No match found — could be unauthorized, could be a naming mismatch |
| `NOT_CHECKED` | No marketplace export supplied |

**There is no `UNAUTHORIZED` verdict.** Absence of a name match is not evidence
of absence of authorization. The script narrows the human review queue; it does
not adjudicate. A control decision that an app is unauthorized is the ISSO's to
make and record, not a string comparison's.

`NO_MATCH_VERIFY_MANUALLY` + `HasScimProvisioning = True` is the review queue
to work first.

## Output

| File | Purpose |
|---|---|
| `saas-integrations-<ts>.csv` / `.json` | Per-integration record — the `entra-id-external-application-registrations` evidence artifact |
| `fedramp-verification-<ts>.csv` / `.json` | The marketplace join — the `fedramp-marketplace-authorization-verifications` evidence artifact |
| `summary-<ts>.txt` | Verdict and risk-cell breakdown |

The two CSVs are the SA-9 evidence artifacts by the names SA-9.yml already
uses. That is the point of the track: SA-9 doesn't need new evidence
identifiers invented for it, it needs the two it already declares to exist.

## What this track does not do

- **No remediation.** Consistent with the suite: findings are manual runbooks.
- **No verdict on Microsoft first-party SPs.** Filtered by default; M365 itself
  is the boundary, not an integration into it.
- **No ISA authoring.** It identifies which integrations need one under CA-3.
  See [`CA-3-SA-9-reconciliation.md`](./CA-3-SA-9-reconciliation.md) for why
  that list is currently in conflict with canon.

## Reading order

Track 4 reuses Track 3's enumeration shape but is independently runnable. If
you run both, run Track 3 first — its `MULTI_TENANT_HOME_ELSEWHERE` rows should
be a superset of Track 4's gallery rows, and a mismatch between them is itself
worth investigating.
