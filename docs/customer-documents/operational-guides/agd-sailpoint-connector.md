---
title: "AGD — SailPoint ISC LDAP Connector Configuration"
subtitle: "Connecting SailPoint Identity Security Cloud to the Active Governance Directory"
document_id: UIAO_198
status: DRAFT
classification: UNCLASSIFIED
boundary: GCC-Moderate
publish_to_site: false
---

# AGD — SailPoint ISC LDAP Connector Configuration

> **Step 1C of the AGD in-path program.** This guide configures SailPoint
> Identity Security Cloud (ISC) to query the Active Governance Directory (AGD)
> as its authoritative source for OrgPath organizational placement data.
> Once wired, SailPoint provisioning decisions — access requests, access
> reviews, joiner/mover/leaver routing — depend on what the AGD answers.
> This is the first point at which something in the real governance stack
> fails if the AGD is offline.

## Why this matters

Active Directory embedded organizational structure in the OU hierarchy.
Every provisioning tool that read AD got `department`, `division`, `office`,
and `manager` for free — the OU path was the org chart.

When AD is gone, that structure has to come from somewhere. Without a
deliberate replacement, SailPoint ISC either (a) reads it from Entra
`onPremisesExtensionAttributes` (which are only populated if your AD sync
puts them there) or (b) has no organizational context at all, reducing
access reviews to flat user lists with no routing logic.

The AGD is that replacement. It projects OrgPath canonical facets over
LDAPv3 — the protocol SailPoint has spoken since it was built. Pointing
ISC at the AGD means:

- **Access reviews route by OrgPath** — reviews for CyberOps go to the
  CyberOps Manager; Finance reviews go to the Finance Director
- **Provisioning decisions respect placement** — a contractor with a
  `term_date` in the next 90 days is flagged; a `Service` account-type
  triggers different certification rules than a `Standard` one
- **The AGD going offline is a governance failure** — SailPoint cannot
  complete routing lookups, making the dependency real and the AGD
  operationally load-bearing

---

## Prerequisites

| Requirement | Detail |
|---|---|
| AGD running | `uiao directory serve --from-assessment <assess-out.json> --bind operator=<secret>` |
| AGD reachable from ISC | Network path open (TCP 1389 plaintext or 636 LDAPS) from ISC's SaaS connector pod or your VA (Virtual Appliance) |
| SailPoint ISC tenant | Admin access to configure Sources |
| OrgPath assessment complete | `uiao orgtree assess --out assess-out.json` run against your Entra tenant |

---

## Step 1 — Start the AGD with your assessment output

```powershell
# Run the OrgPath assessment against your Entra tenant
uiao orgtree assess --out C:\uiao\assess-out.json

# Start the AGD, feeding from the assessment output
# Use --bind to create an operator credential for ISC's simple bind
uiao directory serve `
  --from-assessment C:\uiao\assess-out.json `
  --bind "sailpoint-isc=<strong-random-secret>" `
  --host 0.0.0.0 `
  --port 1389
```

For production, run behind LDAPS (port 636):

```powershell
uiao directory serve `
  --from-assessment C:\uiao\assess-out.json `
  --bind "sailpoint-isc=<strong-random-secret>" `
  --tls-cert C:\certs\agd.pem `
  --tls-key C:\certs\agd-key.pem `
  --host 0.0.0.0
```

---

## Step 2 — Create an LDAP Source in SailPoint ISC

Navigate to **Admin → Connections → Sources → Create Source → Active Directory / LDAP**.

### Connection settings

| Field | Value |
|---|---|
| **Source name** | `UIAO Active Governance Directory` |
| **Connector** | `Active Directory` or `LDAP` |
| **Host** | AGD host IP or hostname |
| **Port** | `1389` (plaintext) or `636` (LDAPS) |
| **Base DN** | `dc=agd,dc=uiao,dc=gov` |
| **Bind DN** | `sailpoint-isc` |
| **Bind password** | the secret you set in `--bind` |
| **Connection security** | `None` (plaintext) or `SSL` (LDAPS) |

### Schema — Account attributes to correlate

Map AGD's OrgPath attributes to ISC identity attributes:

| AGD attribute | ISC identity attribute | Purpose |
|---|---|---|
| `cn` | `uid` / correlation key | Matches AGD entry to the ISC identity |
| `uiaoOrgPathRegion` | `region` | Region-scoped access review routing |
| `uiaoOrgPathDepartment` | `department` | Department-level entitlement scoping |
| `uiaoOrgPathDivision` | `division` | Division-level certification campaigns |
| `uiaoOrgPathRole` | `jobTitle` / `role` | Role-based access request eligibility |
| `uiaoOrgPathCostCenter` | `costCenter` | Budget owner for access approvals |
| `uiaoOrgPathClassification` | `employeeType` | Drives contractor vs employee cert rules |
| `uiaoOrgPathHireDate` | `startDate` | Joiner detection threshold |
| `uiaoOrgPathTermDate` | `endDate` | Leaver detection — 90-day flag |
| `uiaoOrgPathClearanceLevel` | `clearance` | Clearance-gated entitlement eligibility |
| `uiaoOrgPathAccountType` | `accountType` | Service account certification routing |
| `uiaoPrincipalType` | `principalType` | Separates user / device / service workflows |

### Account correlation rule

ISC needs to correlate AGD entries to its identity cube. Use `cn` (the
principal UPN/ID) as the correlation key against the identity's `uid`
or `email` attribute:

```xml
<!-- ISC Correlation Rule (XML) -->
<CorrelationConfig>
  <AttributeAssignment name="uid">
    <AttributeReference application="UIAO Active Governance Directory"
                        attribute="cn" />
  </AttributeAssignment>
</CorrelationConfig>
```

---

## Step 3 — Configure access review routing by OrgPath

Once the AGD source is aggregated into ISC, use OrgPath attributes in
certification campaigns to route reviews to the right manager:

```
Certification campaign: "CyberOps Annual Access Review"
  Filter: division = CyberOps
  Reviewer: manager lookup via uiaoOrgPathDivision → GRC Manager (d.vasquez@agency.gov)
  Escalation: uiaoOrgPathRole = CISO after 14 days

Certification campaign: "Contractor Expiry Review"
  Filter: classification = Contractor AND term_date ≤ (today + 90 days)
  Reviewer: cost_center owner
  Action on no-response: deprovision
```

---

## Step 4 — The dependency test

After configuration, run this verification to confirm ISC depends on the AGD:

```powershell
# 1. Confirm ISC aggregation succeeds with AGD running
#    (ISC Admin → Sources → UIAO AGD → Test Connection → should show principal count)

# 2. Stop the AGD
#    Ctrl-C on the serve process

# 3. Trigger an ISC aggregation
#    ISC Admin → Sources → UIAO AGD → Aggregate Now

# 4. Expected result: aggregation fails with a connection error
#    ISC cannot retrieve OrgPath data → cannot route the pending access review
#    → the governance dependency is now real
```

When step 4 fails as expected: **OrgPath is load-bearing.** The AGD is
not an optional enrichment — it is a required input to a governance
workflow that cannot complete without it.

---

## Refresh cadence

The AGD projection is computed at server start from the assessment output.
Refreshing it requires re-running the assessment and restarting the server
(or a future hot-reload path). For a federal agency running quarterly
access reviews, a weekly or monthly refresh is adequate. The drift engine
(ADR-040) will flag stale principal data as `DRIFT-PROVENANCE` findings
if the assessment is not refreshed on schedule.

Recommended schedule:

```powershell
# Scheduled task (weekly, Sunday 02:00)
uiao orgtree assess --out C:\uiao\assess-out.json
Restart-Service UIAO-AGD   # if running as a Windows Service (ADR-service)
```

---

## What this does NOT do

This connector gives SailPoint read access to OrgPath data. It does not:

- **Write back to the AGD** — provisioning changes SailPoint makes go
  directly to Entra via the Entra connector, not to the AGD. The AGD
  is a read projection (ADR-100 §3); writes route through the OrgPath
  modernization adapters (ADR-109).
- **Replace the Entra connector** — the AGD connector carries OrgPath
  placement; the Entra connector carries credentials and group membership.
  Both are required.
- **Provide authentication** — the AGD does not issue Kerberos tickets or
  OAuth tokens. Authentication remains with Entra. The AGD simple bind is
  for connector authentication only, not identity authentication.

---

## Related

- [AGD operator guide](../../platform/active-governance-directory.qmd)
- [ADR-100 — AGD LDAPv3 read projection](../../../adr/adr-100-active-governance-directory-ldap.html)
- [ADR-109 — AGD write operations as governed intent](../../../adr/adr-109-active-governance-directory-write-as-intent.html)
- [OrgPath codebook (UIAO_151)](../../../specs/OrgPath-Codebook.html)
