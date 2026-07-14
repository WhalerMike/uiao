# Track 1 — Client Secrets → Managed Identity / Workload Identity Federation

A self-contained learning module on how an Entra ID tenant can move off
long-lived application client secrets in favor of Managed Identities
(MI) and Workload Identity Federation (WIF). Audience: identity
engineers, platform engineers, and security architects who are familiar
with OAuth 2.0 but want a concrete grounding in the Entra-specific
mechanics.

The material is vendor-neutral (no agency-specific identifiers) and is
intended for study and team sharing. It includes a read-only PowerShell
inventory script you can read top-to-bottom as a worked example of
Microsoft Graph SDK usage — there is no expectation that you execute it
against a production tenant.

---

## Contents

1. [Why this matters](#why-this-matters)
2. [Three target models, explained](#three-target-models-explained)
3. [Common misconceptions](#common-misconceptions)
4. [Decision tree — which target when?](#decision-tree--which-target-when)
5. [Scope of this assessment](#scope-of-this-assessment)
6. [The inventory script — what it produces](#the-inventory-script--what-it-produces)
7. [Sample output (illustrative)](#sample-output-illustrative)
8. [How the script works (annotated walkthrough)](#how-the-script-works-annotated-walkthrough)
9. [Disposition classification](#disposition-classification)
10. [Migration playbooks](#migration-playbooks)
11. [Validation — confirming the secret is no longer used](#validation--confirming-the-secret-is-no-longer-used)
12. [Permissions required](#permissions-required)
13. [Risks and edge cases](#risks-and-edge-cases)
14. [Re-running the assessment](#re-running-the-assessment)
15. [Further reading](#further-reading)
16. [Glossary](#glossary)

---

## Why this matters

Client secrets are long-lived bearer credentials. They are:

- **Steal-once, use-forever** — anyone who reads the value can
  authenticate as the application from anywhere, until the secret is
  rotated or removed.
- **Routinely leaked** — through source control, CI logs, screenshots,
  chat transcripts, and abandoned `.env` files. Public-repo scanners
  find thousands of leaked Entra client secrets every month.
- **Difficult to rotate at scale** — every consuming workload must be
  updated in lockstep, so in practice many secrets are issued at the
  24-month maximum and never rotated until they expire and break.
- **Untraceable to a workload** — the sign-in log shows
  `credentialType = ClientSecret` and a 3-character `hint` from the
  secret value, but those are per-`keyId`, not per-deployment. Two
  copies of the same secret on two hosts log identically.

The alternatives are not "secrets with extra steps" — they're
structurally different:

- **Managed Identity (MI)** moves the credential out of your workload
  entirely. Azure issues short-lived tokens to the runtime via the
  Instance Metadata Service. There is still a credential underneath,
  but you never see it, never store it, and never rotate it. The
  blast radius of a leaked configuration file is zero — there's
  nothing in the file to leak.
- **Workload Identity Federation (WIF)** replaces the long-lived shared
  secret with a *trust relationship* anchored on an external IdP's
  signing key. Your CI system or Kubernetes cluster mints a
  short-lived OIDC token; Entra accepts that token as proof of
  identity and issues an Entra access token in exchange. The leakable
  thing — a 5–10 minute JWT — expires before an attacker can usefully
  exfiltrate it.

This track teaches the concepts, classifies what's in a tenant, and
hands off concrete migration playbooks.

---

## Three target models, explained

### 1. Managed Identity (MI)

**Where it lives:** Azure-hosted compute. App Service, Functions,
Logic Apps, VMs, VMSS, AKS (via Workload Identity), Container Apps,
Container Instances, Automation Accounts, Arc-enabled servers
(yes — Arc-enabled *on-prem* VMs get a system-assigned MI from the
Azure control plane).

**How the workload uses it:**

```text
Workload code
    │
    │ "I need a token for Key Vault"
    ↓
Azure Identity SDK
    │
    │ HTTP GET 169.254.169.254/metadata/identity/oauth2/token
    │   ?resource=https://vault.azure.net
    │   Header: Metadata: true
    ↓
Instance Metadata Service (IMDS)  ← runs on the Azure host
    │
    │ ↓ (Azure platform signs a JWT internally)
    ↓
Returns access token (JWT, ~1 hr)
```

The workload **never holds a credential**. The Azure platform handles
authentication on its behalf using a credential it manages internally.

**System-assigned vs user-assigned:**

| Aspect           | System-assigned MI                | User-assigned MI                          |
|------------------|-----------------------------------|-------------------------------------------|
| Lifecycle        | Tied to the resource              | Standalone — survives resource deletion   |
| Scope            | 1:1 with the resource             | Can be attached to many resources         |
| Use when…        | The workload is unique to the host| Multiple hosts share a workload identity  |
| Typical fit      | A single Function App             | A VMSS, blue/green deploys, shared SP     |

### 2. Workload Identity Federation (WIF)

**Where it lives:** Workloads outside Azure that run on a platform
which itself acts as an OIDC issuer. The Entra app registration is
configured with a `federatedIdentityCredential` that names the trusted
issuer + subject. At runtime, the platform mints a JWT identifying the
workload; the workload presents that JWT to Entra in exchange for an
Entra access token.

**How the trust is set up (one-time):**

```text
You, in the Entra portal or Graph API:
    │
    │ Create federatedIdentityCredential on app reg X:
    │   issuer    = "https://token.actions.githubusercontent.com"
    │   subject   = "repo:myorg/myrepo:ref:refs/heads/main"
    │   audiences = ["api://AzureADTokenExchange"]
    ↓
Entra now trusts JWTs from that issuer when the subject matches.
```

**How the workload uses it (every run):**

```text
GitHub Actions job (running on main)
    │
    │ Request OIDC token from GH → JWT with sub="repo:myorg/myrepo:ref:refs/heads/main"
    ↓
azure/login@v2
    │
    │ POST https://login.microsoftonline.com/<tenant>/oauth2/v2.0/token
    │   client_id              = <app-id>
    │   client_assertion_type  = urn:ietf:params:oauth:client-assertion-type:jwt-bearer
    │   client_assertion       = <GH JWT>
    │   grant_type             = client_credentials
    ↓
Entra validates the JWT signature against the GitHub JWKS,
checks issuer+subject+audience match the federatedIdentityCredential,
and returns an Entra access token.
```

The JWT lives for ~5 minutes. There is no long-lived shared secret
between GitHub and Entra — only a published OIDC trust on Entra's side.

**Supported issuers (current):**

| Issuer                  | Subject pattern                                             | Use case                            |
|-------------------------|-------------------------------------------------------------|-------------------------------------|
| GitHub Actions          | `repo:<org>/<repo>:ref:refs/heads/<branch>`                 | Branch-scoped CI                    |
| GitHub Actions          | `repo:<org>/<repo>:environment:<env>`                       | Environment-scoped deploys          |
| GitHub Actions          | `repo:<org>/<repo>:pull_request`                            | PR validation                       |
| Azure DevOps            | `sc://<org>/<project>/<service-connection>`                 | ADO pipelines                       |
| Kubernetes (any)        | `system:serviceaccount:<ns>:<sa>`                           | AKS, EKS, GKE, on-prem K8s w/ OIDC  |
| GitLab CI               | `project_path:<group>/<project>:ref_type:branch:ref:<br>`   | GitLab pipelines                    |
| BitBucket Pipelines     | `<workspace-uuid>:<repository-uuid>`                        | BitBucket CI                        |
| Generic OIDC            | any conformant issuer/subject/audience                      | Custom OIDC providers               |

### 3. Certificate credential (interim)

**Where it lives:** Workloads outside Azure on platforms with no OIDC
issuer (and no path to IMDS via Arc-enable). A `keyCredential`
(`AsymmetricX509Cert`) is uploaded to the app registration; the
workload signs JWT assertions locally with the matching private key
and presents them in the OAuth 2.0 `client_credentials` flow using
`client_assertion_type = …:jwt-bearer`.

The private key **is** the credential. The improvement over a client
secret is that the private key can be hardware-protected — TPM, HSM,
Key Vault Premium HSM-backed, Windows CNG, smartcard — so the
key material never leaves the trust boundary even when the workload's
host is compromised.

This is the **interim** target. Prefer WIF when the issuer is
available. Use cert credentials only when WIF is not yet possible.

---

## Common misconceptions

> "Managed Identity eliminates the credential."

No. MI moves the credential out of your code and out of your config.
The credential still exists — Azure manages it on your behalf, rotates
it automatically, and uses IMDS to hand short-lived access tokens to
your workload. You never see it, never store it, never rotate it. That
is the point. But "no credential" overstates it; the right framing is
"no customer-managed credential".

> "Workload Identity Federation means no setup on the Entra side."

No. You still create a `federatedIdentityCredential` on the app
registration, pinning the trust to a specific `(issuer, subject,
audience)` triple. Without that pre-registration, Entra has no reason
to accept any external JWT.

> "Federated credentials replace authentication with trust."

Partial. The external IdP (GitHub, ADO, K8s API server) still
*authenticates* the workload — its OIDC token is a cryptographic
attestation. WIF *delegates* the authentication step to a trusted IdP
rather than performing it itself with a shared secret.

> "The 3-character hint in the sign-in log identifies which copy of the secret was used."

No. The `hint` is per-`keyId` on the app registration. Every workload
holding the same copy of the secret produces the same hint. If you
have two copies of the same secret on two hosts, the sign-in log
cannot tell them apart.

> "Removing a client secret breaks the workload immediately."

No. Existing Entra access tokens remain valid until they expire (up to
~24h for refresh tokens, ~1h for access tokens). A workload that
authenticated recently may continue to work for a while after secret
removal. **Don't declare success until you've seen the workload
successfully *re-authenticate***, not just keep using a cached token.

> "DefaultAzureCredential always uses MI when running in Azure."

No. `DefaultAzureCredential` tries a chain of credentials in order
(env vars → workload identity → MI → Visual Studio → Azure CLI →
PowerShell → interactive). In a dev environment, it can pick up your
local AZ CLI sign-in and silently mask a missing MI. In production,
set `AZURE_TOKEN_CREDENTIALS=ManagedIdentityCredential` (or use the
explicit `ManagedIdentityCredential` class) to disable fallback.

> "An expired secret means the workload is broken."

Not necessarily. If the workload has a valid access token cached, it
will continue to function until the token expires. Conversely, a
secret that is *unexpired* but never used by any workload contributes
to clutter and risk — see Track 3.

> "Multi-tenant apps with secrets are fine because consumers manage their own."

Misleading. The app registration's *home tenant* owns the credential.
A multi-tenant app's secret is the same secret across every consuming
tenant. If you remove it, every consumer breaks. Coordinate before
acting.

---

## Decision tree — which target when?

```
START — application has one or more client secrets
  │
  ├─ Has the SP signed in within the last 180 days?
  │     ├─ No  → STALE — hand off to Track 3 (delete, do not migrate)
  │     └─ Yes ↓
  │
  ├─ Is it a vendor SaaS integration that requires Entra to issue the secret?
  │     ├─ Yes → KEEP as carve-out (Playbook 6: rotate ≤180d, monitor, re-evaluate annually)
  │     └─ No  ↓
  │
  ├─ Where does the consuming workload run?
  │     │
  │     ├─ Inside Azure (App Service / Function / VM / Container App / AKS w/ MI)
  │     │     → MIGRATE_TO_MI (Playbook 1)
  │     │
  │     ├─ GitHub Actions
  │     │     → MIGRATE_TO_WIF_GITHUB (Playbook 2)
  │     │
  │     ├─ Azure DevOps pipelines
  │     │     → MIGRATE_TO_WIF_ADO (Playbook 3)
  │     │
  │     ├─ Kubernetes (any cluster — AKS / EKS / GKE / on-prem with OIDC)
  │     │     → MIGRATE_TO_WIF_K8S (Playbook 4)
  │     │
  │     ├─ Other CI / platform with OIDC issuer (GitLab, BitBucket, custom)
  │     │     → Generic WIF variant of Playbook 2
  │     │
  │     ├─ On-prem or platform without OIDC, but Arc-enable possible
  │     │     → Arc-enable host, then MIGRATE_TO_MI (Playbook 1)
  │     │
  │     └─ On-prem, no OIDC, no Arc
  │           → MIGRATE_TO_CERT (Playbook 5; revisit annually)
  │
  └─ Workload location is unknown
        → INVESTIGATE (no migration until classified)
```

---

## Scope of this assessment

**In scope:**

- All `Application` objects in the tenant with one or more
  `passwordCredentials`.
- The matching `ServicePrincipal` objects (home-tenant apps only).
- First-party Microsoft service principals are **excluded** by default
  (customers can't rotate Microsoft-managed credentials); pass
  `-IncludeMicrosoftBuiltIn` to include them for completeness.

**Out of scope (separate tracks):**

- User credentials (passwords, MFA methods) → Track 2.
- Stale-app cleanup regardless of credential type → Track 3.
- Azure RBAC role assignments → Track 3.
- Multi-tenant apps whose `Application` object is in *another* tenant
  (we only see the local `ServicePrincipal`) — flagged but not
  classified.

---

## The inventory script — what it produces

[`scripts/Get-EntraAppCredentialInventory.ps1`](./scripts/Get-EntraAppCredentialInventory.ps1)
enumerates every application registration and emits four timestamped
artifacts:

| Output file              | Granularity                  | Use                                       |
|--------------------------|------------------------------|-------------------------------------------|
| `apps-<ts>.csv`          | One row per application      | Excel pivots, owner outreach              |
| `credentials-<ts>.csv`   | One row per credential       | Expiry sort, "rotate this week"           |
| `apps-<ts>.json`         | Structured app rows          | Tooling pipelines                         |
| `summary-<ts>.txt`       | Tenant-wide counts           | Quick read at the end of each run         |

### Per-app schema

| Column                   | Meaning                                                                |
|--------------------------|------------------------------------------------------------------------|
| `AppId`                  | Application (client) ID                                                |
| `ObjectId`               | Directory object ID of the app registration                            |
| `DisplayName`            | Friendly name                                                          |
| `Publisher`              | Publisher domain                                                       |
| `SignInAudience`         | `AzureADMyOrg` / `AzureADMultipleOrgs` / …                             |
| `OwnerCount`             | Users with `Owner` role on the app                                     |
| `OwnerUpns`              | Semicolon-delimited UPNs                                               |
| `SecretCount`            | `passwordCredentials.length`                                           |
| `CertCount`              | `keyCredentials.filter(type=AsymmetricX509Cert).length`                |
| `FederatedCredCount`     | `federatedIdentityCredentials.length`                                  |
| `NextSecretExpiry`       | ISO 8601                                                               |
| `DaysToNextSecretExpiry` | Integer; negative if already expired                                   |
| `SecretsExpiringSoon`    | Count expiring within `ExpiryWarningDays`                              |
| `SecretsAlreadyExpired`  | Count of expired but undeleted secrets                                 |
| `SpLastSignIn`           | ISO 8601 (Graph beta `servicePrincipalSignInActivity`)                 |
| `SpLastSignInDays`       | Integer days since last sign-in                                        |
| `AppLastSignIn`          | ISO 8601 (delegated-flow sign-ins)                                     |
| `ReplyUrls`              | Semicolon-delimited                                                    |
| `ReplyUrlHints`          | Platform hints (`AppService`, `StaticWebApps`, `Localhost`, …)         |
| `Tags`                   | Semicolon-delimited app tags                                           |
| `Notes`                  | App registration notes field                                           |
| `Disposition`            | Starting classification (see below)                                    |
| `DispositionReasons`     | Why this disposition was assigned                                      |

### Per-credential schema

| Column           | Meaning                                                       |
|------------------|---------------------------------------------------------------|
| `AppId`          | Parent app                                                    |
| `AppDisplayName` | Parent app name                                               |
| `CredentialType` | `Secret`, `Certificate`, or `Federated`                       |
| `KeyId`          | Credential identifier                                         |
| `DisplayName`    | Friendly name                                                 |
| `Hint`           | First three chars of secret (sign-in log correlation)         |
| `StartDate`      | ISO 8601                                                      |
| `EndDate`        | ISO 8601                                                      |
| `DaysToExpiry`   | Integer; negative if expired                                  |
| `Issuer`         | Federated only — OIDC issuer URL                              |
| `Subject`        | Federated only — OIDC subject claim                           |
| `Audiences`      | Federated only — comma-delimited trusted audiences            |

---

## Sample output (illustrative)

A real tenant would have hundreds or thousands of rows. Five
illustrative rows showing different dispositions:

`apps-2026-05-21T14-30-00.csv` (selected columns):

```csv
AppId,DisplayName,SecretCount,FederatedCredCount,SpLastSignInDays,ReplyUrlHints,Disposition,DispositionReasons
b3f1a8c2-1234-...,acme-deploy-prod,1,0,2,AppService,MIGRATE_TO_MI,"Azure-hosted hints: AppService"
c8a2bd97-5678-...,gha-deploy,1,1,5,,MIGRATE_TO_WIF_GITHUB,"GitHub mention in tags/notes"
d4e7f234-9abc-...,vendor-saas-bridge,1,0,12,,KEEP_SECRET_CARVEOUT,"carveout tag/note present"
e6b9c1ff-def0-...,old-poc-app,2,0,247,Localhost,STALE_NO_SIGNIN,"SP last signed in 247d ago (> 180)"
f1c3a504-1357-...,unknown-orphan,1,0,,Localhost,INVESTIGATE,"no owners"
```

Walkthrough of each row:

- **acme-deploy-prod** — has one secret, recent sign-in, reply URL on
  `*.azurewebsites.net`. Strong signal it runs in App Service →
  Playbook 1 (system-assigned MI).
- **gha-deploy** — already has one federated credential (good sign:
  someone started a migration). Recent sign-in. The display name and
  tag mention "github" → Playbook 2 (additional federated creds for
  other branches/environments, then remove the secret).
- **vendor-saas-bridge** — owner tagged it `carveout:contoso:2026-12-01`
  because the vendor requires a secret → Playbook 6 (rotate, monitor,
  revisit).
- **old-poc-app** — two secrets, no sign-in in 247 days, reply URL is
  `localhost`. Classic stale POC. → Track 3 (delete, don't migrate).
- **unknown-orphan** — no owners, no recent sign-in metadata, no
  hints. Cannot classify → `INVESTIGATE`. Track down who created it,
  whether it's still needed, before any other action.

`credentials-2026-05-21T14-30-00.csv` (selected):

```csv
AppId,CredentialType,KeyId,DisplayName,EndDate,DaysToExpiry,Issuer,Subject
b3f1...,Secret,a4d2...,deploy secret 2024,2026-08-15T00:00:00Z,86,,
c8a2...,Secret,b6e3...,migration interim,2026-06-30T00:00:00Z,40,,
c8a2...,Federated,fc12...,gha-main,,,https://token.actions.githubusercontent.com,repo:myorg/myrepo:ref:refs/heads/main
d4e7...,Secret,d7f4...,contoso integration,2026-11-30T00:00:00Z,193,,
e6b9...,Secret,e8g5...,initial,2024-09-01T00:00:00Z,-262,,
e6b9...,Secret,f9h6...,rotate-1,2026-09-01T00:00:00Z,103,,
```

Note: the credentials CSV mixes secrets, certs, and federated creds in
one table — that lets you sort by `DaysToExpiry` to plan rotation, or
filter by `CredentialType` to see only federated trust relationships.

`summary-2026-05-21T14-30-00.txt`:

```text
Entra ID app credential inventory
Tenant:    11111111-2222-3333-4444-555555555555
Generated: 2026-05-21T14:30:00.0000000Z

Apps total:                  847
Apps with >=1 client secret: 312
Total client secrets:        448
Already-expired secrets:     27
Secrets expiring <  90 d:    61

Disposition breakdown:
  NO_SECRET                       535
  MIGRATE_TO_MI                   108
  MIGRATE_TO_WIF_GITHUB            42
  STALE_NO_SIGNIN                  39
  INVESTIGATE                      31
  KEEP_SECRET_CARVEOUT             24
  MIGRATE_TO_WIF_ADO               18
  MIGRATE_TO_WIF_K8S               14
  MIGRATE_TO_WIF_OR_CERT           36
```

---

## How the script works (annotated walkthrough)

Reading the script top-to-bottom, here are the non-obvious choices and
why they're there. Skip this section if you don't intend to read the
PowerShell.

### 1. Strict mode and error policy

```powershell
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 3.0
```

- `ErrorActionPreference = Stop` turns non-terminating errors into
  terminating ones, so a typo in a property name fails loudly instead
  of producing empty output.
- `StrictMode 3.0` catches references to non-existent properties on
  `PSCustomObject`s — useful for catching SDK schema drift. **It does
  not apply to hashtables**, which is why we deliberately request
  hashtable output from raw Graph calls (see step 3).

### 2. Connection check up front

```powershell
function Test-GraphContext { … }
```

Validates that `Connect-MgGraph` has been called and that the current
context holds the recommended scopes. Missing scopes produce a warning
rather than a hard failure, so the script can run with partial
permissions (e.g. you got `Application.Read.All` but not
`Reports.Read.All` — sign-in activity columns will be empty, but the
inventory still works).

### 3. Why the beta Graph endpoint for sign-in activity

```powershell
$uri = 'https://graph.microsoft.com/beta/reports/servicePrincipalSignInActivity?$top=999'
```

The `servicePrincipalSignInActivity` endpoint is on Microsoft Graph's
`/beta` segment as of late 2024 / 2026. The v1.0 surface only exposes
per-user interactive sign-ins via `signInActivity`. We need the
per-SP rollup that the beta endpoint provides — that's where
`MIGRATE_TO_*` vs `STALE_NO_SIGNIN` separation comes from.

You'll often see two timestamps on the response:

- `lastSignInActivity.lastSignInDateTime` — most recent sign-in by the
  service principal (workload-identity flows: client_credentials,
  federated, MI).
- `applicationAuthenticationClientSignInActivity.lastSignInDateTime` —
  delegated flows (user signing into the app, OAuth on-behalf-of).

The first tells you whether the workload is still alive; the second
tells you whether end-users still use the app. For client-secret
migration, the first matters.

### 4. Hashtable output, not PSCustomObject

```powershell
$page = Invoke-MgGraphRequest -Method GET -Uri $uri   # default: HashTable
foreach ($row in $page['value']) {
    if ($row['appId']) { $spActivity[$row['appId']] = $row }
}
```

`Invoke-MgGraphRequest` can return either hashtables (default) or
`PSCustomObject` (`-OutputType PSObject`). Under `Set-StrictMode 3.0`,
accessing a *missing* property on a `PSCustomObject` throws — bad for
beta-endpoint responses that may omit fields per-row. Hashtables
return `$null` on missing keys, which is what we want for tolerant
parsing of an evolving schema.

### 5. Filtering Microsoft built-ins

```powershell
$apps = $apps | Where-Object { $_.PublisherDomain -notlike '*microsoft.com' }
```

First-party Microsoft service principals (Graph, Exchange Online,
Teams, etc.) are present in every tenant. They have credentials
Microsoft manages and customers can't rotate — including them in
the inventory just adds noise. `-IncludeMicrosoftBuiltIn` brings them
back if you want to study the full picture.

### 6. The owner extraction

```powershell
Get-MgApplicationOwner -ApplicationId $app.Id -All | ForEach-Object {
    $ap = $_.AdditionalProperties
    if     ($ap['userPrincipalName']) { $ap['userPrincipalName'] }
    elseif ($ap['displayName'])       { $ap['displayName'] }
    else                              { $_.Id }
}
```

`Get-MgApplicationOwner` returns `DirectoryObject` instances. The
concrete subtype (User, ServicePrincipal, Group) lives in
`AdditionalProperties` — a dictionary, indexed with `['key']`
(tolerant of missing keys, unlike `.Property` under StrictMode).
The fallback chain prefers UPN (most useful for outreach), then
display name (for non-user owners like a workspace SP), and finally
the object ID (last resort).

### 7. Disposition cascade

The `Get-Disposition` helper returns *one* starting hint plus all the
reasons that led there. The order matters:

1. `NO_SECRET` short-circuits — if there's nothing to migrate, no
   further analysis needed.
2. `STALE_NO_SIGNIN` short-circuits — don't bother classifying
   *where* a stale app runs; Track 3 will delete it.
3. `KEEP_SECRET_CARVEOUT` — explicit carve-out tags/notes override
   any other migration hint.
4. Tag/note hints (GitHub, ADO, K8s) — most reliable signal because
   they're human-curated.
5. Reply-URL hints (AppService, StaticWebApps, AWS) — heuristic,
   correct most of the time but not authoritative.
6. Fall through to `INVESTIGATE` if no signal landed.

The cascade is mutually exclusive — one hint per app. The accumulated
*reasons* string is informative even when the hint is `INVESTIGATE`
(e.g. "no owners; multi-tenant audience" tells you why it couldn't be
classified).

### 8. Reply-URL hint regex

```powershell
switch -Regex ($url) {
    'azurewebsites\.net' { $hints.Add('AppService'); break }
    'azurefd\.(net|com)' { $hints.Add('FrontDoor'); break }
    …
}
```

The list of patterns is deliberately conservative — only well-known
Azure-hosted domains and a few common alternatives (AWS, Vercel,
Netlify, Localhost). A reply URL on `mycompany.com` tells us nothing
about where the workload actually runs, so we leave it unclassified
and let the disposition fall through to other signals (tags, owners,
sign-in activity).

### 9. Date handling — UTC throughout

```powershell
function ConvertTo-Days {
    param([Nullable[datetime]] $From, [Nullable[datetime]] $To)
    if (-not $From -or -not $To) { return $null }
    return [int][math]::Floor((($To.ToUniversalTime() - $From.ToUniversalTime())).TotalDays)
}
```

All timestamps are normalized to UTC before subtraction. The Graph
API returns UTC; PowerShell's `Get-Date` returns local time. Failing
to normalize gives off-by-one days near midnight in your timezone.
Both inputs are `[Nullable[datetime]]` so the function returns
`$null` cleanly when either timestamp is missing (the caller should
not have to write a guard for every call).

### 10. Output file naming

Files are named `apps-2026-05-21T14-30-00.csv` — ISO 8601 timestamp
with `-` instead of `:` (which is illegal in Windows filenames).
That sorts lexicographically by run time, and a re-run never
overwrites a previous report. Diffing two runs becomes a `Compare-Object`
or simple Excel pivot.

---

## Disposition classification

The script assigns one starting hint per app. **Treat it as a
suggestion, not a decision.** A human should verify before acting on
any row.

| Disposition                | Trigger                                                                              | Recommended next step                                       |
|----------------------------|--------------------------------------------------------------------------------------|-------------------------------------------------------------|
| `MIGRATE_TO_MI`            | Reply URLs match `*.azurewebsites.net`, `*.azurecontainerapps.io`, `*.azure-api.net`, etc. | Playbook 1                                                  |
| `MIGRATE_TO_WIF_GITHUB`    | Tag or note mentions GitHub                                                          | Playbook 2                                                  |
| `MIGRATE_TO_WIF_ADO`       | Tag or note mentions Azure DevOps / ADO / VSTS                                       | Playbook 3                                                  |
| `MIGRATE_TO_WIF_K8S`       | Tag or note mentions AKS / Kubernetes / K8s                                          | Playbook 4                                                  |
| `MIGRATE_TO_WIF_OR_CERT`   | Reply URLs match non-Azure hosts (AWS, Vercel, Netlify, GitHub Pages)                | Playbook 2/3/4 if applicable, else Playbook 5               |
| `KEEP_SECRET_CARVEOUT`     | Tag or note contains `carveout:`                                                     | Playbook 6                                                  |
| `STALE_NO_SIGNIN`          | SP has no recorded sign-in within `StaleDays`                                        | Hand off to Track 3 — plan deletion                         |
| `NO_SECRET`                | App has no client secrets                                                            | Skip — already in target state                              |
| `INVESTIGATE`              | No owners, no recent sign-in metadata, no hints                                      | Manual investigation                                        |

---

## Migration playbooks

Six playbooks, one per target architecture. Each is a runnable sequence
of steps with the relevant Graph or Azure CLI commands; treat them as
reference material rather than scripts to memorize.

### Playbook 1 — Azure-hosted workload → Managed Identity

1. **Identify the resource.** Which App Service / Function App / VM /
   Container App owns the secret? Search the workload's config
   (`az webapp config appsettings list`, `appsettings.json`, K8s
   ConfigMaps) for the matching `client_id`.
2. **Enable a managed identity on the resource:**
   ```powershell
   az webapp identity assign --name <app> --resource-group <rg>
   ```
   For user-assigned: create the MI first (`az identity create`),
   then attach.
3. **Grant the MI the same permissions the old SP had.**
   - Azure RBAC (Key Vault, Storage, etc.): assign the role to the
     MI's principal ID.
   - Graph application permissions: use
     `New-MgServicePrincipalAppRoleAssignment` against the MI's SP.
4. **Update the workload code** to use `DefaultAzureCredential` or the
   explicit `ManagedIdentityCredential`. Remove `ClientSecretCredential`
   instantiations.
5. **Deploy and verify.** Confirm successful authentication in the
   workload's logs.
6. **Remove the client secret** from the original app registration:
   ```powershell
   Remove-MgApplicationPassword -ApplicationId <obj-id> -KeyId <key-id>
   ```
7. **Optionally delete the original app registration** if no other
   workload uses it — the MI's SP replaces it entirely.

### Playbook 2 — GitHub Actions → Workload Identity Federation

1. **Identify the workflow** consuming the secret. Search the org for
   `secrets.AZURE_CLIENT_SECRET` or the matching `client_id`.
2. **Add a federated credential:**
   ```powershell
   $params = @{
       name        = 'github-myorg-myrepo-main'
       issuer      = 'https://token.actions.githubusercontent.com'
       subject     = 'repo:myorg/myrepo:ref:refs/heads/main'
       audiences   = @('api://AzureADTokenExchange')
       description = 'GitHub Actions main branch deploy'
   }
   New-MgApplicationFederatedIdentityCredential `
       -ApplicationId <obj-id> -BodyParameter $params
   ```
   For per-environment deploys, use
   `subject = 'repo:myorg/myrepo:environment:prod'`.
3. **Update the workflow** to use `azure/login` in WIF mode:
   ```yaml
   permissions:
     id-token: write
     contents: read
   steps:
     - uses: azure/login@v2
       with:
         client-id:       ${{ vars.AZURE_CLIENT_ID }}
         tenant-id:       ${{ vars.AZURE_TENANT_ID }}
         subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
   ```
   `client-secret` is gone. Tenant/client/subscription move to `vars`
   (not `secrets`) because they're not sensitive.
4. **Test the workflow** with a no-op deploy.
5. **Remove the GitHub secret** (`AZURE_CLIENT_SECRET`).
6. **Remove the client secret** on the app registration.

### Playbook 3 — Azure DevOps → Workload Identity Federation

ADO service connections support WIF natively as of 2024.

1. In Project Settings → Service connections, open the existing
   "Azure Resource Manager" connection.
2. Click **Convert**. ADO offers to convert to a "Workload Identity
   Federation (automatic)" connection and creates the federated
   credential on the app registration for you.
3. **Verify** by running a pipeline that uses the connection.
4. **Remove the client secret** on the app registration after pipelines
   succeed.

For manual setup (service-principal-by-name connections): add a
federated credential with:

- `issuer  = https://vstoken.dev.azure.com/<org-guid>`
- `subject = sc://<org>/<project>/<connection-name>`

### Playbook 4 — AKS workload → Workload Identity

Requires AKS Workload Identity (GA since 2023).

1. **Enable workload identity on the cluster:**
   ```bash
   az aks update -g <rg> -n <cluster> --enable-oidc-issuer --enable-workload-identity
   ```
2. **Get the OIDC issuer URL:**
   ```bash
   az aks show -g <rg> -n <cluster> --query oidcIssuerProfile.issuerUrl -o tsv
   ```
3. **Add a federated credential on the app registration:**
   ```powershell
   $params = @{
       name      = 'aks-<cluster>-<ns>-<sa>'
       issuer    = '<issuer-url-from-step-2>'
       subject   = 'system:serviceaccount:<ns>:<sa>'
       audiences = @('api://AzureADTokenExchange')
   }
   New-MgApplicationFederatedIdentityCredential `
       -ApplicationId <obj-id> -BodyParameter $params
   ```
4. **Annotate the Kubernetes ServiceAccount:**
   ```yaml
   apiVersion: v1
   kind: ServiceAccount
   metadata:
     name: <sa>
     namespace: <ns>
     annotations:
       azure.workload.identity/client-id: <app-id>
   ```
5. **Label the pod spec and bind the SA:**
   ```yaml
   metadata:
     labels:
       azure.workload.identity/use: "true"
   spec:
     serviceAccountName: <sa>
   ```
6. **Remove the client secret** from the workload's environment.

### Playbook 5 — On-prem / external → Certificate credential

When no OIDC issuer is available. The workload signs JWT assertions
locally with a private key it holds.

1. **Generate a key pair** on the workload's host. Prefer hardware
   storage (TPM, HSM, Key Vault Premium HSM).
2. **Export only the public cert** (`.cer`).
3. **Upload to the app registration:**
   ```powershell
   $cert = [Convert]::ToBase64String((Get-Content .\workload.cer -AsByteStream))
   $params = @{
       keyCredentials = @(
           @{
               type        = 'AsymmetricX509Cert'
               usage       = 'Verify'
               key         = $cert
               displayName = 'workload-host-<name>'
           }
       )
   }
   Update-MgApplication -ApplicationId <obj-id> -BodyParameter $params
   ```
4. **Update the workload** to sign JWT assertions with the private key
   and present them in the OAuth2 client-assertion flow.
5. **Schedule rotation** (annual or per policy).
6. **Remove the client secret**.

### Playbook 6 — Carve-out (secret retained)

When a vendor or legacy integration genuinely requires a client secret:

1. **Tag the app registration** with `carveout:<vendor>:<expiry-date>`.
2. **Record the exception** in the tenant's exception register
   (wherever your org tracks these — wiki, repo file, ITSM record).
3. **Set the secret expiry to ≤ 180 days** and put rotation on the
   calendar.
4. **Audit the SP's application permissions** for least privilege.
   Over-broad `Directory.ReadWrite.All` etc. should be pushed back to
   the vendor.
5. **Add monitoring** — alert on sign-ins from new IP ASNs, new
   user-agent families, or outside an allow-listed time window.
6. **Re-evaluate annually** — contact the vendor about WIF support.

---

## Validation — confirming the secret is no longer used

After a migration, confirm no client_secret remains in use:

```kql
// Sign-ins by SPs using client_secret in the last 30 days.
// Run in Entra → Diagnostic settings → workspace → Logs.
AADServicePrincipalSignInLogs
| where TimeGenerated > ago(30d)
| extend cred = tostring(parse_json(tostring(AuthenticationDetails))[0].authenticationMethod)
| where cred == "ClientSecret"
| summarize SignInCount = count(), LastSignIn = max(TimeGenerated)
    by AppId, ServicePrincipalName
| order by SignInCount desc
```

Cross-reference against the inventory's `MIGRATE_TO_*` rows — any
AppId still appearing here has either:

- A workload that didn't get migrated (most common), or
- A residual cached token (will age out within ~1 hour for access
  tokens, ~24h for refresh), or
- A carve-out working as designed (expected — verify against the
  exception register).

This query requires that **Entra ID diagnostic settings** are
configured to forward sign-in logs to a Log Analytics workspace.
Without that, the data only lives in the Entra portal for 30 days and
isn't queryable via KQL.

---

## Permissions required

For the inventory script (read-only):

| Scope                  | Type                | Purpose                                          |
|------------------------|---------------------|--------------------------------------------------|
| `Application.Read.All` | Delegated or App    | Enumerate `Application` and `ServicePrincipal`   |
| `Directory.Read.All`   | Delegated or App    | Resolve owner UPNs                               |
| `AuditLog.Read.All`    | Delegated or App    | Sign-in activity reports                         |
| `Reports.Read.All`     | Delegated or App    | `servicePrincipalSignInActivity` (beta)          |

For remediation (Playbooks 1–6), additionally:

| Scope                                  | Used by                                       |
|----------------------------------------|-----------------------------------------------|
| `Application.ReadWrite.All`            | Add/remove credentials, federated creds       |
| `RoleManagement.ReadWrite.Directory`   | Reassign directory roles to MI                |
| `AppRoleAssignment.ReadWrite.All`      | Move Graph app-role assignments to MI         |

A common-sense pattern: prefer delegated calls with an admin signing
in interactively for one-off work. For pipeline-driven remediation,
use a *separate* app registration restricted to these scopes with its
own federated credential — don't dog-food a client secret to fix
client secrets.

---

## Risks and edge cases

- **Apps with downstream consumers you don't own.** Removing a secret
  on a multi-tenant app that other tenants consume breaks their
  integration. Coordinate before any deletion.
- **Tokens cached for up to 24 hours.** A workload that authenticated
  recently may continue to work after secret removal because its
  access token is still valid. Don't declare success until you've
  seen the workload successfully *re-authenticate*.
- **MI tokens have different `iss` and `oid` claims** than the
  original SP. Downstream services that pin to a specific `oid`
  (e.g. SQL Server contained users created against the old SP) need
  updating.
- **`DefaultAzureCredential` fallback order matters.** See
  misconceptions section above.
- **Federated credentials are per-subject.** A workflow running on
  both `main` and `develop` needs two federated credentials — or
  target a deploy environment (subject = `repo:o/r:environment:prod`)
  so the branch dimension is collapsed.
- **Conditional Access for workload identities** (stable since 2024)
  can restrict where MI/WIF tokens are usable — pair with this
  migration to limit blast radius further.
- **The script only sees `Application` objects in this tenant.**
  Multi-tenant apps homed elsewhere appear only as service principals
  here and are out of scope for v1.

---

## Re-running the assessment

The script writes timestamped output files. Diff successive runs to
track migration progress:

```powershell
$old = Import-Csv .\out\apps-2026-05-21T10-00-00.csv
$new = Import-Csv .\out\apps-2026-06-21T10-00-00.csv

$lookup = @{}
foreach ($r in $old) { $lookup[$r.AppId] = [int]$r.SecretCount }

$new |
    Where-Object { $lookup.ContainsKey($_.AppId) -and [int]$_.SecretCount -lt $lookup[$_.AppId] } |
    Select-Object AppId, DisplayName,
        @{n='Before';e={ $lookup[$_.AppId] }},
        @{n='After'; e={ [int]$_.SecretCount }}
```

Set a target trajectory — e.g. "reduce non-carveout `SecretCount`
from N to 0 by 2026-12-31".

---

## Further reading

Canonical Microsoft Learn pages (search the title verbatim if the URL
has moved):

- **What is managed identity?** —
  `https://learn.microsoft.com/entra/identity/managed-identities-azure-resources/overview`
- **Workload identity federation** —
  `https://learn.microsoft.com/entra/workload-id/workload-identity-federation`
- **Configure an app to trust an external identity provider** —
  `https://learn.microsoft.com/entra/workload-id/workload-identity-federation-create-trust`
- **Configure GitHub Actions to use workload identity federation** —
  search MS Learn for *"Configure a GitHub Actions workflow to get an
  access token"*
- **Use service connections in Azure Pipelines** —
  `https://learn.microsoft.com/azure/devops/pipelines/library/service-endpoints` (look for "workload identity")
- **Azure Kubernetes Service workload identity** —
  `https://learn.microsoft.com/azure/aks/workload-identity-overview`
- **Service principal sign-in activity (beta)** —
  `https://learn.microsoft.com/graph/api/resources/serviceprincipalsigninactivity`
- **DefaultAzureCredential** —
  `https://learn.microsoft.com/dotnet/api/azure.identity.defaultazurecredential`

Standards (stable URLs):

- **RFC 7521** — Assertion Framework for OAuth 2.0 Client Authentication —
  `https://datatracker.ietf.org/doc/html/rfc7521`
- **RFC 7523** — JWT Profile for OAuth 2.0 Client Authentication —
  `https://datatracker.ietf.org/doc/html/rfc7523`
- **RFC 8693** — OAuth 2.0 Token Exchange —
  `https://datatracker.ietf.org/doc/html/rfc8693`
- **RFC 9068** — JWT Profile for OAuth 2.0 Access Tokens —
  `https://datatracker.ietf.org/doc/html/rfc9068`
- **OIDC Core 1.0** — `https://openid.net/specs/openid-connect-core-1_0.html`

Microsoft Graph PowerShell SDK:

- **Get started with Microsoft Graph PowerShell** —
  `https://learn.microsoft.com/powershell/microsoftgraph/get-started`
- **`Get-MgApplication` cmdlet reference** —
  `https://learn.microsoft.com/powershell/module/microsoft.graph.applications/get-mgapplication`

---

## Glossary

| Term                       | Meaning                                                                                              |
|----------------------------|------------------------------------------------------------------------------------------------------|
| **Application** (object)   | Entra's "app registration" — the directory object holding the application's identity, permissions, and credentials. |
| **Service Principal**      | The runtime representation of an Application in a specific tenant. One Application can have one SP per tenant it operates in. |
| **Client secret**          | A long-lived shared secret on an Application, used in the OAuth2 `client_credentials` flow.          |
| **Managed Identity (MI)**  | An Azure-managed identity attached to a compute resource; the Azure platform handles authentication.|
| **Workload Identity Federation (WIF)** | A trust relationship between Entra and an external OIDC issuer; the external IdP attests to identity in lieu of a secret. |
| **Federated Identity Credential** | The Entra-side object defining a WIF trust — `(issuer, subject, audience)` triple.            |
| **IMDS**                   | Instance Metadata Service — the Azure platform's local endpoint (`169.254.169.254`) that hands out MI tokens to workloads. |
| **JWKS**                   | JSON Web Key Set — an IdP's published set of public signing keys, used to verify JWTs.               |
| **Carve-out**              | A documented exception: an app that retains a client secret because no alternative is available.     |
| **Disposition**            | This assessment's term for a starting-point classification (`MIGRATE_TO_MI`, `STALE_NO_SIGNIN`, etc.).|
