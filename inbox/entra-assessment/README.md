# Entra ID tenant assessment suite

Vendor-neutral assessment material for three identity-hygiene tracks in an
Entra ID tenant. Each track has its own folder with an assessment document
plus read-only PowerShell scripts. Remediation steps live in the docs as
manual runbooks; automated remediation scripts are intentionally out of
scope for v1.

## Tracks

| # | Track                                                              | Folder                                                                                       | Status   |
|---|--------------------------------------------------------------------|----------------------------------------------------------------------------------------------|----------|
| 1 | Client secrets to Managed Identity / WIF                           | [`01-client-secrets-to-managed-identity/`](./01-client-secrets-to-managed-identity/)         | drafted  |
| 2 | PIV to Entra CBA + FIDO2 / Passkeys / WHfB                         | [`02-piv-to-phishing-resistant-auth/`](./02-piv-to-phishing-resistant-auth/)                 | drafted  |
| 3 | Stale apps, roles, and accounts                                    | [`03-stale-inventory-review/`](./03-stale-inventory-review/)                                 | drafted  |
| 4 | SaaS integration authorization (SA-9)                              | [`04-saas-integration-authorization/`](./04-saas-integration-authorization/)                 | drafted  |

## Common conventions

- **Tooling:** Microsoft.Graph PowerShell SDK v2+. One script per
  read-only data source; scripts emit both CSV (for humans / Excel) and
  JSON (for tooling pipelines).
- **Permissions:** every script declares its required Graph scopes in
  the `.NOTES` header and warns at startup if any are missing from the
  current `Connect-MgGraph` context.
- **Idempotency:** all scripts are read-only and safe to re-run. They
  write timestamped output files; previous runs are never overwritten in
  place.
- **Throttling:** scripts use the SDK's built-in 429 retry. Long
  enumerations are paged.
- **Tenant parameterization:** scripts use the current `Connect-MgGraph`
  context. No tenant identifiers are hardcoded.

## Prerequisites

```powershell
# Minimum modules (PowerShell 7+)
Install-Module Microsoft.Graph         -Scope CurrentUser
Install-Module Microsoft.Graph.Beta    -Scope CurrentUser   # for SP sign-in activity

# Sign in once per session with the union of scopes the suite needs.
Connect-MgGraph -Scopes `
    Application.Read.All, `
    Directory.Read.All, `
    AuditLog.Read.All, `
    Reports.Read.All, `
    Policy.Read.All, `
    RoleManagement.Read.Directory, `
    UserAuthenticationMethod.Read.All
```

Individual scripts may need only a subset; their headers list per-script
requirements.

## Reading order

Start with Track 1. Its credential inventory feeds Track 3's stale-apps
analysis, so running it first avoids duplicate enumeration work later.

Track 4 picks up where Track 3 stops: Track 3's `MULTI_TENANT_HOME_ELSEWHERE`
disposition is the signature of a gallery app (the vendor owns the app
registration; you hold only the service principal). Track 4 re-detects those via
`applicationTemplateId` and asks the question Track 3 doesn't — is that SaaS
FedRAMP authorized, and is it receiving a directory replica? Track 4 is
independently runnable, but running Track 3 first gives a useful cross-check:
its `MULTI_TENANT_HOME_ELSEWHERE` rows should be a superset of Track 4's gallery
rows.
