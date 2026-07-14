# Track 3 — Stale Apps, Roles, and Accounts

A self-contained learning module on identifying and dispositioning
stale objects in an Entra ID tenant. "Stale" means different things
for different object types, so this track is split into three
sub-inventories:

- **Stale apps** — service principals and app registrations nobody
  uses.
- **Stale role assignments** — directory roles granted to disabled,
  deleted, or never-active principals.
- **Stale accounts** — user objects that have gone dormant.

Each sub-inventory has its own read-only PowerShell script. All
three share a common disposition pattern — **review → notify →
disable → delete** — with hard exemptions for compliance and legal
hold.

This track ties back to the others:
- Stale apps **extends** Track 1's credential inventory with deeper
  staleness signals (consent grants, owners, creation date).
- Stale accounts **extends** Track 2's user inventory with lifecycle
  signals (manager presence, never-signed-in, account age).

Running Track 1 and Track 2 first is not required, but doing so
gives you a richer joined dataset for governance reviews.

The material is vendor-neutral and intended for self-study and team
sharing. Scripts are read-only and meant to be read as worked
examples.

---

## Contents

1. [Why this matters](#why-this-matters)
2. [What "stale" actually means](#what-stale-actually-means)
3. [Sub-inventory 1 — Stale apps and service principals](#sub-inventory-1--stale-apps-and-service-principals)
4. [Sub-inventory 2 — Stale role assignments](#sub-inventory-2--stale-role-assignments)
5. [Sub-inventory 3 — Stale user accounts](#sub-inventory-3--stale-user-accounts)
6. [Common misconceptions](#common-misconceptions)
7. [Disposition workflow — review, notify, disable, delete](#disposition-workflow--review-notify-disable-delete)
8. [Decision tree by object type](#decision-tree-by-object-type)
9. [Scope of this assessment](#scope-of-this-assessment)
10. [The three scripts — what they produce](#the-three-scripts--what-they-produce)
11. [Sample output (illustrative)](#sample-output-illustrative)
12. [How the scripts work (annotated walkthrough)](#how-the-scripts-work-annotated-walkthrough)
13. [Disposition classifications](#disposition-classifications)
14. [Governance playbooks](#governance-playbooks)
15. [Validation](#validation)
16. [Permissions required](#permissions-required)
17. [Risks and edge cases](#risks-and-edge-cases)
18. [Further reading](#further-reading)
19. [Glossary](#glossary)

---

## Why this matters

Stale objects accumulate silently. A POC app reg from 2021 with
expired secrets nobody owns. A contractor's user account left
enabled after their engagement ended. A Global Admin role still
assigned to an engineer who moved teams two years ago. Each one is
a small footprint, but they compound:

- **Attack surface.** Orphan accounts and apps are favored footholds.
  Nobody monitors them; nobody notices when they're used.
- **Audit and compliance.** "What do you have, and who has access?"
  is question one of every identity audit. Stale objects make the
  answer unreliable.
- **License cost.** Entra P1 / P2, Office, Intune — most are
  per-enabled-user. Disabled-but-undeleted users may or may not
  count depending on license SKU.
- **Operational drag.** Every dropdown list of "users" or "apps"
  gets longer. Search results have more noise. Real objects are
  harder to find.
- **Mistaken trust.** Permissions you forgot you granted still
  resolve. Tokens still mint. Workloads still run.

Hygiene is unglamorous and ongoing. The goal of this track is to
make it **reproducible** — same inventory every quarter, same
disposition criteria, same workflow.

---

## What "stale" actually means

"Stale" has at least three definitions, and they don't always
align:

- **No recent sign-in** — the most common operational signal.
  Tenant-wide, "no sign-in in N days" is the workhorse staleness
  criterion. Caveats: federation can mask sign-in updates;
  background apps (sync jobs, scheduled tasks) may not update
  `lastSignInDateTime` in all flows; some sign-in events take
  minutes to hours to propagate to the activity log.
- **No recent change** — `lastDirSyncTime` for on-prem-sync'd
  objects, `modifiedDateTime` for various resources. Useful for
  detecting orphan-from-source objects.
- **No structural anchor** — orphan reference (assignment to a
  deleted principal), missing owner, missing manager, no group
  membership, no consent grants. A "live" object whose
  *governance scaffolding* has eroded.

The scripts in this track use **no recent sign-in** as the primary
signal and **structural anchors** as secondary signals. Combining
them avoids false positives:

> *"This SP hasn't signed in for 180 days AND has no owners AND no
> consent grants AND was created more than 30 days ago"* is a much
> stronger "safe to delete" signal than any one criterion alone.

---

## Sub-inventory 1 — Stale apps and service principals

### What we look at

Two related object types:

- **Application** — the app registration in the directory. Owns
  credentials, redirect URIs, required permissions.
- **ServicePrincipal** — the runtime identity of an app *in this
  tenant*. One app may have one SP per tenant where it's consented.

The script enumerates both, joins them, and looks at:

- **Service-principal sign-in activity** — last workload-identity
  sign-in (client_credentials, federated, MI flows).
- **Application sign-in activity** — last delegated sign-in (user
  interactively signing into the app).
- **Owners** — directory role `Owner` on the app. Apps with no
  owners are governance failures; deleting them silently is also a
  failure.
- **Consent grants** — `oauth2PermissionGrants` (delegated) and
  `appRoleAssignments` (application). An app with no consent
  grants and no sign-in is far safer to delete than one with
  consent grants someone may still depend on.
- **Created date** — to distinguish "stale" from "new and just
  hasn't run yet."
- **Credential state** — expired secrets, expired certs (Track 1
  surface, repeated here with a different lens).
- **Multi-tenancy** — SPs whose Application object is in another
  tenant. These are governed by the consumer side (consenting
  users), not the producer side, and need separate treatment.

### Where it overlaps with Track 1

Track 1 (`Get-EntraAppCredentialInventory.ps1`) looks at apps for
credential migration. Track 3's stale-app script looks at the same
apps for staleness. They share most fields. If you've run Track 1
recently, you can re-use its `apps-*.csv` for first-pass triage and
just run the stale-app script for the *additional* signals
(consent grants, never-signed-in age).

---

## Sub-inventory 2 — Stale role assignments

### What we look at

**Entra directory roles** — Global Administrator, User
Administrator, Application Administrator, etc. These are the
"who can do what *in the directory*" assignments. They are
distinct from **Azure RBAC** roles, which govern access to Azure
subscriptions and resources. Track 3 covers directory roles;
Azure RBAC is a follow-on (see [Out of scope](#scope-of-this-assessment)).

The script enumerates:

- **Active role assignments** — `unifiedRoleAssignmentSchedules` /
  `roleAssignments`. Both permanent and PIM-active.
- **Eligibility instances** — `unifiedRoleEligibilitySchedules`.
  Users who *can* activate a role but currently are not active.
- **Principal type** — User, Group, ServicePrincipal.
- **Principal state** — enabled / disabled / orphan (object
  reference exists but the principal can't be resolved).
- **Role definition** — the role's display name and whether it's
  a "high-privilege" role (Global Admin, Privileged Role Admin,
  User Access Admin, etc.).

### The "convert to eligible" suggestion

Permanent active assignments to high-privilege roles are an
anti-pattern when **PIM eligible** assignments are available
(requires Entra P2). The script flags these as a *suggestion*,
not a directive — converting to eligible requires policy work
(approval workflows, time limits, MFA requirements) that lives
outside this inventory.

### PIM activation history — out of v1 scope

Knowing "this user is PIM-eligible for Global Admin but has never
activated in 180 days" requires querying the audit logs for PIM
activation events. The script flags eligibility instances but
*does not* enrich with activation history in v1. See "Further
reading" for the relevant Graph endpoint to extend this.

---

## Sub-inventory 3 — Stale user accounts

### What we look at

The script enumerates `User` objects and looks at:

- **Sign-in activity** — `signInActivity.lastSignInDateTime` and
  `lastNonInteractiveSignInDateTime`. Interactive is the primary
  signal; non-interactive catches token-only flows.
- **Account state** — `accountEnabled = true | false`.
- **User type** — Member vs Guest. Guests are evaluated with
  separate criteria (their primary identity lives in another
  tenant).
- **Account age** — `createdDateTime`. "Never signed in" means
  different things at age 5 days vs age 6 months.
- **Manager presence** — many JML processes assume every member
  has a manager. Missing managers are a governance signal.
- **External identity source** — `externalUserState` for guests:
  `Invited`, `Accepted`, `Pending`.
- **On-prem sync source** — `onPremisesSyncEnabled` and
  `onPremisesImmutableId` indicate the user is sync'd from AD.
  If the source AD account is disabled, the cloud copy lingers
  unless lifecycle automation handles it (out of v1 scope).

### What it doesn't look at (yet)

- **Owned objects** — users who own apps, groups, devices. The
  script does not enumerate ownership; deleting a user without
  checking ownership can orphan critical apps. This is an
  important manual step in the disposition playbook.
- **License assignment** — staleness vs license-cost is two
  separate questions; the v1 script doesn't pull license SKUs.
- **Group memberships** — adjacent governance concern; out of
  v1 scope.

---

## Common misconceptions

> "No sign-in in 90 days means the user / app is unused."

Mostly true, with caveats. Federation can mask sign-in updates
in some flows. Background workload identities may authenticate
without producing `lastSignInDateTime` updates in all paths.
Some users only access non-Entra resources (e.g. on-prem AD-only
apps with no Entra integration). Combine with other signals.

> "Disable is a safe alternative to delete."

Partial. Disabled accounts:
- Cannot sign in. ✓ Real protection.
- Still appear in directory queries. ✗ Still searchable.
- Still hold group memberships. ✗ Re-enabling restores
  permissions implicitly.
- Still own resources (apps, groups, devices). ✗ Ownership
  persists.
- Still hold role assignments. ✗ Re-enable = re-grant.

For privileged users, *also* remove role assignments and
group memberships when disabling.

> "Deleting a user deletes their data."

No. M365 mailbox, OneDrive, and Teams content go through *separate*
retention policies. Deleting an Entra user puts them in the
**deleted-items recycle bin for 30 days**, then permanently. Their
mailbox / OneDrive may be retained much longer per retention rules.

> "Deleting an app removes all its consent grants."

Partial. Deleting the Application *registration* removes its home.
ServicePrincipals in *consumer tenants* (for multi-tenant apps)
persist — they were created by the consumer's consent grant. To
fully revoke, each consenting tenant must also remove their SP.

> "PIM-eligible is risk-free because it requires activation."

Partial. Eligible-but-never-activated still represents a permission
grant. The act of activation can happen in seconds. The risk is
*lower* than permanent active, but it's not zero — especially if
activation lacks MFA or approval gates.

> "Role assignment to a disabled user is harmless because they
> can't sign in."

Wrong. Re-enabling the user restores the role implicitly. If the
account is later compromised (e.g. password leaked, attacker
re-enables via another compromised admin), the role is back.
Better hygiene: remove the role assignment when disabling.

> "Stale guest cleanup is the guest's problem."

Partial. The guest's home tenant manages *their identity*. But
the inviting tenant manages *their access to this tenant*. A
guest whose account at their home tenant is deleted continues to
appear here as an enabled guest — your tenant's responsibility to
clean up.

> "Soft-deleted users / apps are recoverable forever."

No. 30 days for users, 30 days for apps in the deleted-items
recycle bin. After that, hard-deleted and not recoverable through
normal admin channels.

> "Entra Access Reviews automates everything."

Entra Access Reviews (P2) is excellent for *recurring* reviews —
quarterly access certifications for groups, apps, roles. It
doesn't replace the inventory and disposition workflow; it
operationalizes the *review* step. Pair with this track, don't
substitute.

---

## Disposition workflow — review, notify, disable, delete

For every stale finding, the disposition workflow is the same
four-step pattern. The duration of each step varies by object
class and by your org's risk tolerance:

```
DETECT  ─►  REVIEW  ─►  NOTIFY  ─►  DISABLE  ─►  DELETE
   │           │            │            │           │
   │           │            │            │           └─ Permanent (after recycle-bin window)
   │           │            │            │
   │           │            │            └─ Reversible state. Object exists but inert.
   │           │            │
   │           │            └─ Reach out to owner/manager/principal. Set deadline.
   │           │
   │           └─ Human judgment: is this finding correct? Any compliance flag?
   │
   └─ Script-generated finding.
```

Typical durations:

| Object type             | Review window | Notify → Disable | Disable → Delete |
|-------------------------|---------------|------------------|------------------|
| User account (member)   | 7 days        | 14 days          | 365 days         |
| User account (guest)    | 7 days        | 7 days           | 90 days          |
| App / SP (with owner)   | 14 days       | 30 days          | 30 days          |
| App / SP (no owner)     | 7 days        | n/a              | 30 days          |
| Role assignment         | 7 days        | 14 days          | (one-step remove)|

These are starting points — tighter for security-sensitive
populations (admins, finance), looser for low-risk populations
(read-only roles).

### Hard exemptions

Some objects must **never** be auto-dispositioned, regardless of
staleness:

- **Break-glass accounts.** Two emergency admin accounts with
  long, vaulted passwords. They *should* be rarely-used; stale is
  the design.
- **Legal hold / litigation hold.** Mailboxes and accounts under
  hold cannot be deleted without compliance sign-off.
- **Service accounts you control.** Document them. Tag them
  `carveout:`. They appear in the inventory but with
  `KEEP_LEGAL_HOLD` or equivalent disposition.
- **Built-in Microsoft service principals.** Filtered by default
  on inclusion.

---

## Decision tree by object type

### Apps and service principals

```
Stale app finding:
  ├─ Is it a Microsoft built-in?   → SKIP
  ├─ Is the SP's home tenant elsewhere? → MULTI_TENANT_HOME_ELSEWHERE (consumer-side, separate process)
  ├─ Was it created < 30 days ago?  → INVESTIGATE_NEW (might just be new)
  ├─ Recent sign-in + has owner?    → KEEP
  ├─ Recent sign-in + no owner?     → ASSIGN_OWNER
  ├─ No sign-in 180d + has owner?   → NOTIFY_OWNER_STALE → DISABLE → DELETE
  ├─ No sign-in 180d + no owner +
  │   no consent grants?            → SAFE_TO_DELETE
  ├─ Expired secret + recent sign-in → INVESTIGATE_EXPIRED_CRED (broken workload?)
  └─ Default                        → INVESTIGATE
```

### Role assignments

```
Stale role-assignment finding:
  ├─ Principal cannot be resolved?  → REMOVE_DELETED_PRINCIPAL (orphan)
  ├─ Principal is a User and disabled? → REMOVE_DISABLED_PRINCIPAL
  ├─ Principal is a Group with 0 members? → REMOVE_GROUP_NO_MEMBERS
  ├─ Permanent active assignment to a high-privilege role?
  │   → CONVERT_TO_ELIGIBLE (PIM suggestion — requires P2)
  ├─ Eligibility instance, no activation in 180d?
  │   → REMOVE_NEVER_ACTIVATED (requires audit-log enrichment, v2)
  └─ Default                        → KEEP
```

### User accounts

```
Stale user finding:
  ├─ Legal hold / retention flag?   → KEEP_LEGAL_HOLD
  ├─ Guest user, no activity 90d?   → STALE_GUEST_90 → revoke invitation
  ├─ Guest from unlisted tenant?    → GUEST_UNKNOWN_TENANT (manual review)
  ├─ Disabled member > 365d?        → DELETE_DISABLED_365 (after retention check)
  ├─ Enabled member, no sign-in 180d? → DISABLE_NO_SIGNIN_180
  ├─ Enabled member, no sign-in 90d?  → NOTIFY_NO_SIGNIN_90
  ├─ Created > 30d ago, enabled, never signed in?
  │                                  → REVIEW_NEVER_SIGNED_IN
  ├─ Enabled member, no manager set? → REVIEW_NO_MANAGER (governance gap)
  └─ Default                         → KEEP
```

---

## Scope of this assessment

**In scope:**

- All `Application` and `ServicePrincipal` objects (apps script).
- All Entra directory role assignments and eligibility instances
  (roles script).
- All `User` objects, Members and Guests (accounts script).

**Out of scope (separate concerns):**

- **Azure RBAC role assignments** on subscriptions / resource
  groups / resources. These are enumerated per subscription and
  require Azure Resource Manager APIs, not Graph. See *Further
  reading* for the canonical AzureRM enumeration approach.
- **PIM for Groups** — eligibility on group memberships. Same
  pattern as PIM for roles but at the group layer.
- **License assignment cleanup** — adjacent to user staleness;
  separate operational concern.
- **Group hygiene** — empty groups, groups with no owners. Related
  to role hygiene (role-assignable groups) but warrants its own
  inventory.
- **Device hygiene** — stale device objects. Related to user
  staleness (deleting a user often orphans their devices) but
  separate.

---

## The three scripts — what they produce

### `Get-EntraStaleAppInventory.ps1`

| Output file              | Granularity                      | Use                                     |
|--------------------------|----------------------------------|-----------------------------------------|
| `stale-apps-<ts>.csv`    | One row per app / SP             | Quarterly app review pivot              |
| `stale-apps-<ts>.json`   | Same, structured                 | Tooling pipelines                       |
| `summary-<ts>.txt`       | Disposition counts               | At-a-glance progress                    |

### `Get-EntraStaleRoleInventory.ps1`

| Output file               | Granularity                      | Use                                     |
|---------------------------|----------------------------------|-----------------------------------------|
| `stale-roles-<ts>.csv`    | One row per role assignment      | Role-cleanup ticket source              |
| `stale-roles-<ts>.json`   | Same, structured                 | Tooling pipelines                       |
| `summary-<ts>.txt`        | Disposition counts               | At-a-glance progress                    |

### `Get-EntraStaleAccountInventory.ps1`

| Output file                  | Granularity                  | Use                                  |
|------------------------------|------------------------------|--------------------------------------|
| `stale-accounts-<ts>.csv`    | One row per user             | JML / lifecycle review               |
| `stale-accounts-<ts>.json`   | Same, structured             | Tooling pipelines                    |
| `summary-<ts>.txt`           | Disposition counts           | At-a-glance progress                 |

Per-app schema (selected):

| Column                  | Meaning                                            |
|-------------------------|----------------------------------------------------|
| `AppId`                 | Application (client) ID                            |
| `DisplayName`           | Friendly name                                      |
| `SpObjectId`            | Service principal object ID                        |
| `AppObjectId`           | Application object ID (null if SP-only)            |
| `IsMultiTenantHomeElsewhere` | True if no app reg in this tenant             |
| `OwnerCount`            | Number of users with Owner role                    |
| `CreatedDateTime`       | When created                                       |
| `AccountAgeDays`        | Days since creation                                |
| `SpLastSignIn`          | Workload sign-in (client_credentials, MI, etc.)    |
| `SpLastSignInDays`      | Integer days since last SP sign-in                 |
| `AppLastSignIn`         | Delegated sign-in                                  |
| `AppLastSignInDays`     | Integer days                                       |
| `Oauth2GrantCount`      | Delegated permission grants                        |
| `AppRoleAssignmentCount`| Application permission grants                      |
| `ExpiredSecretCount`    | Expired but undeleted secrets                      |
| `Disposition`           | Disposition hint                                   |
| `DispositionReasons`    | Why                                                |

Per-role-assignment schema (selected):

| Column                    | Meaning                                          |
|---------------------------|--------------------------------------------------|
| `AssignmentType`          | `Active` or `Eligible`                           |
| `RoleDisplayName`         | Role name (e.g. "Global Administrator")          |
| `IsHighPrivilege`         | True for known sensitive roles                   |
| `PrincipalId`             | Object ID of the assignee                        |
| `PrincipalDisplayName`    | Friendly name                                    |
| `PrincipalType`           | User / Group / ServicePrincipal                  |
| `PrincipalEnabled`        | true / false / null (for orphan / SP / group)    |
| `PrincipalResolved`       | true if principal could be looked up             |
| `Scope`                   | Directory scope or AU scope                      |
| `StartDateTime`           | Assignment start                                 |
| `Disposition`             | Disposition hint                                 |
| `DispositionReasons`      | Why                                              |

Per-account schema (selected):

| Column                  | Meaning                                            |
|-------------------------|----------------------------------------------------|
| `Upn`                   | userPrincipalName                                  |
| `ObjectId`              | User object ID                                     |
| `DisplayName`           | Friendly name                                      |
| `UserType`              | Member or Guest                                    |
| `AccountEnabled`        | true / false                                       |
| `CreatedDateTime`       | When created                                       |
| `AccountAgeDays`        | Days since creation                                |
| `LastSignIn`            | Interactive sign-in timestamp                      |
| `LastSignInDays`        | Days since last interactive sign-in                |
| `LastNonInteractiveSignIn` | Token-based sign-in timestamp                   |
| `HasManager`            | true if `manager` reference resolves               |
| `OnPremSync`            | true if sync'd from AD                             |
| `ExternalUserState`     | Guest invitation state                             |
| `Disposition`           | Disposition hint                                   |
| `DispositionReasons`    | Why                                                |

---

## Sample output (illustrative)

### Stale apps

`stale-apps-2026-05-21T16-00-00.csv` (selected):

```csv
AppId,DisplayName,OwnerCount,SpLastSignInDays,AccountAgeDays,Oauth2GrantCount,Disposition,DispositionReasons
b3f1...,acme-deploy-prod,2,2,820,3,KEEP,"recent sign-in; has owners"
c8a2...,gha-deploy,1,5,210,2,KEEP,"recent sign-in; has owners"
g4h7...,proto-2024,0,247,420,0,SAFE_TO_DELETE,"no sign-in 247d; no owners; no consent grants"
h5i8...,intern-pilot,1,201,180,0,NOTIFY_OWNER_STALE,"no sign-in 201d; has owners"
i6j9...,ghost-app,0,,460,0,SAFE_TO_DELETE,"never signed in; no owners; no consent grants; > 30d old"
j7k0...,new-thing,0,,12,0,INVESTIGATE_NEW,"created 12d ago; no sign-in yet"
k8l1...,vendor-mt-x,0,15,,5,MULTI_TENANT_HOME_ELSEWHERE,"app reg not in this tenant"
l9m2...,broken-sync,1,3,540,1,INVESTIGATE_EXPIRED_CRED,"recent sign-in; 2 expired secrets"
```

Walkthrough:
- **acme-deploy-prod**, **gha-deploy** — healthy, recent sign-in, owned. KEEP.
- **proto-2024** — abandoned POC. No owner means nobody to notify; no consent grants means no downstream dependency. SAFE_TO_DELETE.
- **intern-pilot** — has an owner; notify them with a deletion deadline before acting.
- **ghost-app** — never signed in despite being 460 days old. Pure clutter. SAFE_TO_DELETE.
- **new-thing** — just registered. Don't panic.
- **vendor-mt-x** — multi-tenant SP whose home is elsewhere. Out of unilateral scope; talk to whoever consented if you want to revoke.
- **broken-sync** — recent sign-in but all secrets expired. Worth investigating — may be using an old token, may have a parallel cert-creds path, may be about to break.

### Stale roles

`stale-roles-2026-05-21T16-00-00.csv` (selected):

```csv
AssignmentType,RoleDisplayName,IsHighPrivilege,PrincipalDisplayName,PrincipalType,PrincipalEnabled,Disposition,DispositionReasons
Active,Global Administrator,True,Alice Admin,User,True,KEEP,"active high-priv assignment"
Active,Global Administrator,True,Old Service Account,User,False,REMOVE_DISABLED_PRINCIPAL,"high-priv role to disabled user"
Active,User Administrator,False,(unresolved),Unknown,,REMOVE_DELETED_PRINCIPAL,"principal not found"
Active,Application Administrator,True,App-Admins-Group,Group,,KEEP,"group assignment — check members separately"
Eligible,Conditional Access Administrator,True,Bob Engineer,User,True,KEEP,"eligible (PIM)"
Active,Privileged Role Administrator,True,Frank Contractor,User,True,CONVERT_TO_ELIGIBLE,"permanent high-priv — candidate for PIM eligible"
Active,Helpdesk Administrator,False,Empty-Group,Group,,REMOVE_GROUP_NO_MEMBERS,"group has 0 members"
```

Walkthrough:
- **Alice Admin** as Global Admin — active and enabled, expected.
- **Old Service Account** — still has Global Admin but disabled. Re-enable = re-grant. Remove the assignment.
- **(unresolved)** — orphan reference. The principal ID points to something Graph can't resolve. Remove.
- **App-Admins-Group** — group-based assignment. Group membership is a separate concern; the assignment itself is fine but needs its membership reviewed.
- **Bob Engineer** PIM-eligible — best practice; KEEP.
- **Frank Contractor** with permanent Privileged Role Admin — should be eligible-only with approval workflow, not permanent. Suggested for conversion.
- **Empty-Group** — Helpdesk Admin assignment that resolves to a group with no members. Effectively dead.

### Stale accounts

`stale-accounts-2026-05-21T16-00-00.csv` (selected):

```csv
Upn,UserType,AccountEnabled,LastSignInDays,AccountAgeDays,HasManager,Disposition,DispositionReasons
alice@agency.gov,Member,True,1,1820,True,KEEP,"recent sign-in"
bob@agency.gov,Member,True,107,720,True,NOTIFY_NO_SIGNIN_90,"no sign-in 107d"
carol@agency.gov,Member,True,212,910,True,DISABLE_NO_SIGNIN_180,"no sign-in 212d"
dan@agency.gov,Member,False,830,1240,True,DELETE_DISABLED_365,"disabled 830d (> 365)"
eve@agency.gov,Member,True,,180,False,REVIEW_NEVER_SIGNED_IN,"never signed in; account 180d old"
frank@agency.gov,Member,True,15,210,False,REVIEW_NO_MANAGER,"no manager set"
guest1#EXT#@agency.gov,Guest,True,95,300,False,STALE_GUEST_90,"guest no activity 95d"
service-acct@agency.gov,Member,True,1,2000,False,KEEP_LEGAL_HOLD,"carveout tag present"
```

Walkthrough:
- **alice** — healthy. KEEP.
- **bob** — 107 days dormant. Notify with deadline.
- **carol** — past 180-day threshold. Disable. (Verify she doesn't own critical SPs first.)
- **dan** — disabled over 2 years. Past 365-day delete threshold. Recycle-bin and confirm no legal hold.
- **eve** — 180-day-old account never signed in. Almost certainly an onboarding that didn't complete; investigate before any action.
- **frank** — actively signing in but no manager set. Governance gap, not a deletion candidate.
- **guest1** — guest who hasn't been active in 95 days. Revoke their invitation.
- **service-acct** — tagged carveout. Stays.

---

## How the scripts work (annotated walkthrough)

The three scripts share a common skeleton (Connect / enumerate /
classify / write) and three common helpers (`Test-GraphContext`,
`ConvertTo-Days`, `Invoke-GraphGet`). The non-obvious choices:

### Apps script

- **Two enumerations needed.** `Get-MgServicePrincipal -All`
  enumerates all SPs in the tenant, including those whose
  Application registration is in another tenant.
  `Get-MgApplication -All` enumerates only local Application
  objects. The script enumerates both and joins on `appId` so it
  catches `MULTI_TENANT_HOME_ELSEWHERE` (SP present, Application
  absent).
- **Consent grants are expensive to enumerate per-SP.** The
  script pulls `oauth2PermissionGrants` and
  `appRoleAssignments` **once tenant-wide**, then aggregates
  counts per SP locally. Per-SP enumeration would be tens of
  thousands of round trips.
- **Created-date heuristic.** Some apps register but never sign
  in for legitimate reasons (still in development, dormant
  feature flag). Apps younger than 30 days are flagged
  `INVESTIGATE_NEW` rather than `SAFE_TO_DELETE` to avoid
  trampling work in progress.

### Roles script

- **Two endpoint families.** Active role assignments come from
  `/roleManagement/directory/roleAssignments`. PIM eligibility
  instances come from
  `/roleManagement/directory/roleEligibilityScheduleInstances`.
  The script enumerates both and emits unified rows with an
  `AssignmentType` column.
- **High-privilege role detection.** Hardcoded list of role
  template IDs for known-sensitive roles (Global Admin, Privileged
  Role Admin, User Access Admin, Application Admin, Privileged
  Authentication Admin, etc.). Update the list as Microsoft adds
  roles.
- **Principal resolution.** Each assignment names a principal by
  ID. Resolving the principal type and enabled-state requires
  separate Graph calls. The script caches resolutions to avoid
  re-querying the same principal across many assignments.

### Accounts script

- **`signInActivity` requires `AuditLog.Read.All`.** Without it,
  the property is silently null. The script warns at startup if
  the scope is missing.
- **Created-date heuristic for "never signed in."** A user
  created yesterday with no sign-in is normal; one created six
  months ago with no sign-in is a problem. The script uses
  `createdDateTime > 30 days ago AND lastSignInDateTime is null`
  to flag this case specifically.
- **Manager lookup is per-user.** No bulk endpoint for `manager`;
  the script does a `/users/{id}/manager` call per user, or uses
  `?$expand=manager` if you set `-IncludeManagerExpand` (heavier
  call but fewer round trips). Trade-off: expansion increases per-page
  payload size; per-user lookups balance more evenly.

---

## Disposition classifications

### Apps

| Disposition                       | Trigger                                                                | Recommended next step                                   |
|-----------------------------------|------------------------------------------------------------------------|---------------------------------------------------------|
| `KEEP`                            | Recent sign-in; has owners                                             | None — healthy                                          |
| `ASSIGN_OWNER`                    | Recent sign-in; no owners                                              | Identify and assign an owner                            |
| `NOTIFY_OWNER_STALE`              | No sign-in N days; has owners                                          | Notify; set deadline; then DISABLE → DELETE             |
| `SAFE_TO_DELETE`                  | No sign-in N days; no owners; no consent grants                        | Disable then delete after grace                         |
| `INVESTIGATE_NEW`                 | Created < 30d ago; no sign-in yet                                      | Wait; check back in 30 days                             |
| `INVESTIGATE_EXPIRED_CRED`        | Has sign-in but all secrets expired                                    | Verify workload health; rotate                          |
| `MULTI_TENANT_HOME_ELSEWHERE`     | SP present in this tenant; Application home elsewhere                  | Consumer-side concern; out of unilateral scope          |
| `MICROSOFT_BUILTIN`               | First-party publisher                                                  | Filtered by default                                     |
| `INVESTIGATE`                     | Other / unclassified                                                   | Manual review                                           |

### Role assignments

| Disposition                       | Trigger                                                                | Recommended next step                                   |
|-----------------------------------|------------------------------------------------------------------------|---------------------------------------------------------|
| `KEEP`                            | Healthy assignment                                                     | None                                                    |
| `REMOVE_DISABLED_PRINCIPAL`       | Principal is a User with `accountEnabled = false`                      | Remove assignment                                       |
| `REMOVE_DELETED_PRINCIPAL`        | Principal cannot be resolved (orphan reference)                        | Remove assignment                                       |
| `REMOVE_GROUP_NO_MEMBERS`         | Principal is a role-assignable Group with 0 members                    | Remove or populate group                                |
| `CONVERT_TO_ELIGIBLE`             | Permanent active assignment to a high-privilege role                   | Requires PIM (P2); convert to eligible with approval    |
| `REVIEW`                          | Other / governance review                                              | Manual review                                           |

### User accounts

| Disposition                       | Trigger                                                                | Recommended next step                                   |
|-----------------------------------|------------------------------------------------------------------------|---------------------------------------------------------|
| `KEEP`                            | Recent sign-in                                                         | None                                                    |
| `KEEP_LEGAL_HOLD`                 | Tagged carveout / on legal hold                                        | Documented exception                                    |
| `NOTIFY_NO_SIGNIN_90`             | Member, enabled, no sign-in 90+ days                                   | Notify user and manager; set disable deadline           |
| `DISABLE_NO_SIGNIN_180`           | Member, enabled, no sign-in 180+ days                                  | Disable after ownership check                           |
| `DELETE_DISABLED_365`             | Member, disabled, > 365 days                                           | Delete after retention check                            |
| `REVIEW_NEVER_SIGNED_IN`          | Member, enabled, created > 30d ago, never signed in                    | Confirm onboarding intent                               |
| `REVIEW_NO_MANAGER`               | Member, enabled, no manager reference                                  | Governance gap; assign manager                          |
| `STALE_GUEST_90`                  | Guest, no activity 90+ days                                            | Revoke invitation                                       |
| `GUEST_UNKNOWN_TENANT`            | Guest from a tenant not on the allowlist                               | Manual review                                           |

---

## Governance playbooks

### Playbook 1 — Quarterly app review

Cadence: every 90 days.

1. **Run the apps inventory.**
2. **Sort by disposition.** Triage in this order:
   1. `SAFE_TO_DELETE` (lowest risk)
   2. `MULTI_TENANT_HOME_ELSEWHERE` (informational only)
   3. `NOTIFY_OWNER_STALE`
   4. `ASSIGN_OWNER`
   5. `INVESTIGATE_*`
3. **For `NOTIFY_OWNER_STALE`:** open a ticket per app; email the
   owner with the disposition deadline (30 days typical). If no
   response after the deadline, escalate to `DISABLE`.
4. **For `SAFE_TO_DELETE`:** disable first (set `accountEnabled` on
   the SP); wait 30 days; if no complaints, delete.
5. **For `ASSIGN_OWNER`:** track down the consumer of the app
   (search source repos for the appId; look at sign-in source
   IPs); assign an owner; tag with a description.
6. **Document carve-outs** as you find them. Apps that look stale
   but legitimately must stay get a `carveout:` tag explaining
   why.

### Playbook 2 — Role-assignment hygiene cycle

Cadence: monthly for privileged roles, quarterly for others.

1. **Run the roles inventory.**
2. **Immediately remove** `REMOVE_DELETED_PRINCIPAL` findings
   (orphans). Zero risk to fix; they only confuse subsequent
   reviews.
3. **For `REMOVE_DISABLED_PRINCIPAL`:** verify the user is not
   pending reactivation; remove assignment.
4. **For `CONVERT_TO_ELIGIBLE`:** open a tracking item per
   assignment. Conversion requires:
   - PIM policy work (approval workflow, MFA on activation,
     max activation duration).
   - User communication (their daily workflow changes — must
     activate before doing admin work).
   - Phased rollout.
5. **For `REMOVE_GROUP_NO_MEMBERS`:** remove the role assignment
   *or* document why the group exists (e.g. about-to-be-populated
   by Joiner automation).
6. **Audit high-privilege role count.** Microsoft recommends ≤5
   Global Admins per tenant for most organizations. Adjust based
   on your org's structure but watch the trend.

### Playbook 3 — User-account lifecycle (JML)

Cadence: continuous (ideally driven by HR system events) plus
monthly catch-all review.

1. **Run the accounts inventory.**
2. **Joiner (J):** new accounts should be created with manager,
   group memberships, and license. `REVIEW_NO_MANAGER` findings
   are joiner-process gaps.
3. **Mover (M):** changed-role users may have stale group
   memberships from their old role. Out of v1 scope but adjacent.
4. **Leaver (L):**
   - `NOTIFY_NO_SIGNIN_90` — first warning. Email the user
     and their manager. Possible explanations: extended leave,
     extended travel, role change to non-Entra-app domain.
   - `DISABLE_NO_SIGNIN_180` — after ownership check, disable.
   - `DELETE_DISABLED_365` — after retention check (legal hold,
     M365 mailbox retention), permanently delete.
5. **Guests:**
   - `STALE_GUEST_90` — revoke invitation (deletes the guest
     object).
   - `GUEST_UNKNOWN_TENANT` — manual review; may indicate
     unsanctioned external collaboration.

### Playbook 4 — Disposition workflow (one-step-at-a-time)

For *each* finding, the safe sequence is **detect → review →
notify → disable → delete**. Never skip steps for non-trivial
objects.

```text
Day 0   Detect       (script flags object as stale)
Day 0-7 Review       (human verifies — compliance, ownership, dependencies)
Day 7   Notify       (owner / manager / principal informed; deadline given)
Day 7-D Grace        (object remains active; principal can respond)
Day D   Disable      (object set inactive but recoverable)
Day D+R Delete       (object permanently removed)
```

Where `D` and `R` come from the duration table in *Disposition
workflow*. Configure per object class.

### Playbook 5 — Soft-delete and recovery

Entra ID maintains a 30-day soft-delete window for users and
applications. To recover within the window:

```powershell
# Restore a deleted user
Restore-MgDirectoryDeletedItem -DirectoryObjectId <object-id>

# List deleted items in the recycle bin
Get-MgDirectoryDeletedItemAsUser -All
Get-MgDirectoryDeletedItemAsApplication -All
```

Role assignments are *not* soft-deleted; removed assignments are
permanently gone (can be recreated, but no recycle bin).

### Playbook 6 — Entra Access Reviews (P2)

For tenants licensed for Entra ID P2, **Access Reviews**
operationalizes recurring access certification:

- **Recurring** — set monthly, quarterly, annual cadence.
- **Reviewer assignment** — owners, managers, or specific
  reviewers.
- **Auto-apply** — denial = automatic access removal (or
  notification-only).
- **Scope** — groups, apps, directory roles, Azure RBAC roles,
  guest users.

Use Access Reviews for the *review* step in the disposition
workflow. Inventory scripts identify candidates; Access Reviews
operationalizes the human decision.

### Playbook 7 — Carve-outs

Always-stale objects that must remain:

1. **Break-glass admin accounts.** Two emergency Global Admin
   accounts. Vaulted credentials, FIDO2 hardware key in safe,
   excluded from CA policies that could lock them out, excluded
   from Track 3 disposition.
2. **Service identities not yet migrated to MI/WIF** (Track 1
   carve-outs from Track 1).
3. **Legal hold / retention.** Document in the exception register
   per object.
4. **System accounts created by Microsoft features** (e.g.
   on-prem Connect sync account, Intune apps). Often appear as
   stale but are operationally critical.

Mark each with a `carveout:` tag where possible (apps), or
maintain an external allowlist (accounts, roles).

---

## Validation

After dispositioning a set of objects, validate that:

- **No regressions.** Sign-in success rate didn't dip; no helpdesk
  tickets correlated with the disposition window.
- **Recovery works.** Pick one deleted object; recover it from the
  soft-delete bin; confirm it works. Build the muscle so you can
  recover in an emergency.

```kql
// Sign-in failures correlated with recently-disabled accounts
let disabledRecently = dynamic(["upn1@agency.gov", "upn2@agency.gov"]);
SigninLogs
| where TimeGenerated > ago(7d)
| where ResultType != 0
| where UserPrincipalName in (disabledRecently)
| project TimeGenerated, UserPrincipalName, AppDisplayName, ResultType, ResultDescription
| order by TimeGenerated desc
```

```kql
// Service principals still signing in despite being marked for disposition
let dispositionedAppIds = dynamic(["b3f1...", "c8a2..."]);
AADServicePrincipalSignInLogs
| where TimeGenerated > ago(7d)
| where AppId in (dispositionedAppIds)
| summarize Count = count(), LastSignIn = max(TimeGenerated) by AppId, ServicePrincipalName
```

---

## Permissions required

For the three inventory scripts (read-only):

| Scope                        | Used by               | Purpose                                          |
|------------------------------|-----------------------|--------------------------------------------------|
| `Application.Read.All`       | Apps                  | Enumerate Apps, SPs, owners, credentials         |
| `Directory.Read.All`         | All three             | Resolve owner UPNs, principal types, groups      |
| `AuditLog.Read.All`          | Apps, Accounts        | SP sign-in activity; user sign-in activity       |
| `Reports.Read.All`           | Apps                  | `servicePrincipalSignInActivity` (beta)          |
| `User.Read.All`              | Accounts              | Enumerate users                                  |
| `RoleManagement.Read.Directory` | Roles               | Role assignments and eligibility                 |
| `DelegatedPermissionGrant.Read.All` | Apps           | `oauth2PermissionGrants`                         |
| `AppRoleAssignment.Read.All` | Apps                  | Service principal app-role grants                |

For remediation (Playbooks 1–7), additionally:

| Scope                                  | Used by                                       |
|----------------------------------------|-----------------------------------------------|
| `Application.ReadWrite.All`            | Delete apps/SPs                               |
| `User.ReadWrite.All`                   | Disable/delete users                          |
| `RoleManagement.ReadWrite.Directory`   | Remove role assignments                       |
| `Directory.AccessAsUser.All` (delegated) | Some recycle-bin operations                |

---

## Risks and edge cases

- **Disabling a user who owns critical apps.** Always check
  `/users/{id}/ownedObjects` before disabling. The apps script
  flags `ASSIGN_OWNER` to surface ownership gaps proactively.
- **Deleting an app that has consumer-side service principals.**
  Multi-tenant app deletion in the home tenant doesn't remove
  consumer SPs. Communicate before deleting if the app is
  multi-tenant.
- **Role assignments via groups.** Removing the role assignment
  on a group affects every member. Don't remove the assignment;
  remove the user from the group instead.
- **PIM eligibility removal cascades.** Removing eligibility while
  someone is *currently* active on that role does not deactivate
  them. They remain active until their activation expires.
  Watch the timing.
- **Soft-delete window is 30 days, not forever.** If you delete
  a user and find out 31 days later it was a mistake, you cannot
  restore through normal admin tools. Recovery requires Microsoft
  support and is not guaranteed.
- **Mailbox / OneDrive retention is separate from user deletion.**
  Compliance retention policies may keep mail / files long after
  the user is deleted from Entra. This is usually desirable; just
  know it's the case.
- **On-prem-sync'd users cannot be deleted from cloud.** They
  must be deleted from on-prem AD; the sync will then remove them
  from cloud. Trying to delete a sync'd user via cloud admin
  tools will be undone by the next sync cycle.
- **The 'never signed in but enabled' population includes**
  service-account look-alikes (created for an integration that
  never went live), abandoned onboarding (account created, hire
  fell through), and federation edge cases. Investigate before
  disabling — these are often someone's forgotten responsibility.
- **High-privilege role removal blast radius.** Removing the
  *last* Global Admin assignment locks the tenant. Always
  maintain at least two break-glass GA accounts that are exempt
  from automation.

---

## Further reading

Microsoft Learn:

- **Service principal sign-in activity** —
  `https://learn.microsoft.com/graph/api/resources/serviceprincipalsigninactivity`
- **Delete and recover deleted users** —
  `https://learn.microsoft.com/entra/fundamentals/users-restore`
- **Manage role assignments via Graph** —
  `https://learn.microsoft.com/graph/api/resources/unifiedroleassignment`
- **Privileged Identity Management overview** —
  `https://learn.microsoft.com/entra/id-governance/privileged-identity-management/pim-configure`
- **Entra Access Reviews** —
  `https://learn.microsoft.com/entra/id-governance/access-reviews-overview`
- **Microsoft Graph user signInActivity** —
  `https://learn.microsoft.com/graph/api/resources/signinactivity`
- **Azure RBAC role assignments (out of scope here)** —
  `https://learn.microsoft.com/azure/role-based-access-control/role-assignments-list-powershell`

Standards:

- **NIST SP 800-53** — AC family (Access Control) — relevant
  controls for stale access cleanup
- **NIST SP 800-63A** — Identity Proofing (lifecycle context)
- **ISO 27001 Annex A.9** — Access Control (review requirements)

---

## Glossary

| Term                          | Meaning                                                                                              |
|-------------------------------|------------------------------------------------------------------------------------------------------|
| **Application**               | Entra app registration. Owns credentials, redirect URIs, permissions.                                |
| **ServicePrincipal**          | Runtime identity of an Application in a tenant.                                                      |
| **Multi-tenant app**          | An Application that can be consented to and used by tenants other than its home tenant.              |
| **Consent grant**             | Permission a user or admin has granted to an app — `oauth2PermissionGrant` (delegated) or `appRoleAssignment` (application). |
| **Directory role**            | Entra-side role (Global Admin, User Admin, App Admin, etc.); distinct from Azure RBAC roles.         |
| **PIM**                       | Privileged Identity Management — Entra P2 feature for just-in-time role activation.                  |
| **Active assignment**         | Role granted permanently or currently scheduled.                                                     |
| **Eligible assignment**       | PIM concept — user can activate the role on demand but is not currently active.                      |
| **Soft-delete**               | Recycle-bin state, 30 days for users/apps; recoverable in that window.                               |
| **JML**                       | Joiner / Mover / Leaver — the identity-lifecycle process.                                            |
| **Legal hold**                | Compliance requirement to preserve an account / mailbox during litigation or investigation.           |
| **Carve-out**                 | Documented exception — object that looks stale but must remain.                                      |
| **Break-glass account**       | Emergency admin account with vaulted credentials, excluded from automation.                          |
| **Orphan reference**          | Object that points to a principal/resource that no longer exists.                                    |
| **Role-assignable group**     | A group that can hold directory-role assignments. Special-purpose, restricted membership rules.       |
| **`onPremisesSyncEnabled`**   | Indicates a user object is sourced from on-prem AD via Entra Connect / Cloud Sync.                   |
