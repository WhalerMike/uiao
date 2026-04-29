# UIAO AD Survey API — Full Project Plan
## Windows Server 2026 · IIS · Kerberos (AD) · MSAL Token (Entra ID)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  CALLER (admin workstation / GitHub Actions / Claude Code)       │
│  Authenticates with: Windows credentials (Kerberos/Negotiate)    │
└──────────────────────┬───────────────────────────────────────────┘
                       │ HTTPS + Windows Auth (IIS)
                       ▼
┌──────────────────────────────────────────────────────────────────┐
│  WINDOWS SERVER 2026  (domain-joined)                            │
│  IIS 10 → HttpPlatformHandler → Python 3.13 FastAPI              │
│                                                                  │
│  ┌─────────────────────┐   ┌──────────────────────────────────┐  │
│  │  AD Survey API      │   │  Auth Layer                      │  │
│  │  /api/v1/survey     │   │  Kerberos (inbound):             │  │
│  │  /api/v1/orgpath    │   │    IIS Windows Auth → GSSAPI     │  │
│  │  /api/v1/validate   │   │  MSAL (outbound to Entra):       │  │
│  │  /health            │   │    Client Credentials → Graph    │  │
│  └──────┬──────────────┘   └──────────────────────────────────┘  │
│         │ ldap3 + GSSAPI/Kerberos                                 │
│         ▼                                                         │
│  ┌──────────────┐    ┌──────────────────────────────────────────┐ │
│  │  AD Forest   │    │  UIAO Python Adapter                     │ │
│  │  (read-only) │    │  survey.py · orgpath.py                  │ │
│  └──────────────┘    └──────────┬───────────────────────────────┘ │
└─────────────────────────────────┼────────────────────────────────┘
                                  │ HTTPS + Bearer Token (MSAL)
                                  ▼
                    ┌─────────────────────────┐
                    │  Microsoft Graph API     │
                    │  Entra ID tenant         │
                    │  (validate + enrich)     │
                    └─────────────────────────┘
```

### Auth Model — Two Directions, Two Mechanisms

| Direction | Protocol | Why |
|---|---|---|
| Caller → API | Kerberos (Windows Auth via IIS Negotiate) | Callers are domain users/agents; no secret management needed |
| API → AD | GSSAPI/Kerberos (ldap3 SASL) | Service account runs as domain principal; no password in code |
| API → Entra ID Graph | MSAL Client Credentials (OAuth2 token) | Graph API is cloud; requires app identity token |

---

## 2. Git Placement

### Target structure in `WhalerMike/uiao` (`main` branch)

```
uiao/
├── impl/
│   └── src/uiao/impl/
│       ├── adapters/
│       │   └── modernization/
│       │       └── active-directory/       ← ADAPTER (already built)
│       │           ├── __init__.py
│       │           ├── survey.py
│       │           └── orgpath.py
│       └── api/                            ← NEW: API surface
│           ├── __init__.py
│           ├── app.py                      ← FastAPI application
│           ├── auth/
│           │   ├── __init__.py
│           │   ├── kerberos.py             ← Inbound Windows Auth
│           │   └── entra_token.py          ← Outbound MSAL
│           └── routes/
│               ├── __init__.py
│               ├── survey.py               ← /api/v1/survey
│               ├── orgpath.py              ← /api/v1/orgpath
│               └── health.py              ← /health
│
├── scripts/
│   ├── ad-survey/
│   │   └── Invoke-ADSurvey.ps1            ← PS fallback (already built)
│   └── deploy/
│       ├── Install-UIAOServer.ps1         ← Full IIS + Python setup
│       ├── Register-UIAOAPI.ps1           ← IIS site + app pool
│       └── Register-ServiceAccount.ps1    ← AD service acct + SPN
│
├── deploy/
│   └── windows-server/
│       ├── web.config                     ← IIS HttpPlatformHandler
│       ├── requirements-windows.txt       ← Python deps
│       └── run.py                         ← uvicorn entrypoint for IIS
│
└── src/uiao/canon/
    ├── adr/
    │   └── adr-029-ad-survey-adapter.md   ← Needs completion
    └── modernization-registry.yaml        ← Add adapter entry
```

### Commit convention (per AGENTS.md)
```
[UIAO-IMPL] add: active-directory-api — FastAPI surface for AD survey adapter
[UIAO-IMPL] add: active-directory-api — IIS deploy scripts and web.config
[UIAO-CORE] add: ADR-029 — active-directory-survey-adapter registration
```

---

## 3. Prerequisites Checklist

### Infrastructure
- [ ] Windows Server 2026 Standard/Datacenter (2-4 vCPU, 8GB RAM minimum)
- [ ] Domain-joined to the target AD forest
- [ ] Static IP + DNS A record (e.g. `uiao-api.corp.contoso.com`)
- [ ] TLS certificate (internal CA or public — must match DNS name)
- [ ] Outbound HTTPS to `graph.microsoft.com` (port 443)
- [ ] Inbound LDAP/LDAPS to domain controllers (port 389/636)
- [ ] Inbound HTTPS from caller workstations (port 443)

### Active Directory
- [ ] Dedicated service account created (e.g. `SVC-UIAO-API`)
- [ ] Service account has: Domain Users + Read all user attributes
- [ ] SPN registered: `HTTP/uiao-api.corp.contoso.com` on service account
- [ ] Constrained delegation configured (if Kerberos pass-through needed)

### Entra ID
- [ ] App registration created in Entra ID (e.g. `UIAO-AD-Survey`)
- [ ] API permissions granted: `User.Read.All`, `Group.Read.All` (Application type)
- [ ] Admin consent granted
- [ ] Client secret or certificate created (certificate preferred)
- [ ] Tenant ID, Client ID, Client Secret/Cert noted

### Developer workstation
- [ ] Git access to `WhalerMike/uiao`
- [ ] Python 3.13 installed locally for testing
- [ ] RSAT tools installed (for SPN and AD verification)

---

## 4. Step-by-Step Implementation

### Phase 0: Repository Setup (Day 1)

**Step 0.1 — Branch**
```bash
git clone https://github.com/WhalerMike/uiao.git
cd uiao
git checkout -b governance/modernization/active-directory-api
```

**Step 0.2 — Place adapter files** (from previous session)
```
impl/src/uiao/impl/adapters/modernization/active-directory/
  __init__.py   (provided)
  survey.py     (provided)
  orgpath.py    (provided)
```

**Step 0.3 — Create API directory skeleton**
```bash
mkdir -p impl/src/uiao/impl/api/auth
mkdir -p impl/src/uiao/impl/api/routes
mkdir -p deploy/windows-server
mkdir -p scripts/deploy
touch impl/src/uiao/impl/api/__init__.py
touch impl/src/uiao/impl/api/auth/__init__.py
touch impl/src/uiao/impl/api/routes/__init__.py
```

**Step 0.4 — Place all files** (see Section 5 — File Inventory)

**Step 0.5 — Update impl/pyproject.toml**
Add under `[project].dependencies`:
```toml
"fastapi>=0.111",
"uvicorn[standard]>=0.29",
"ldap3>=2.9",
"msal>=1.28",
"python-multipart>=0.0.9",
```

---

### Phase 1: Windows Server Foundation (Days 2–3)

**Step 1.1 — Provision server**
- Deploy Windows Server 2026 (VM or bare metal)
- Apply Windows Updates
- Set static IP and hostname

**Step 1.2 — Domain join**
```powershell
Add-Computer -DomainName "corp.contoso.com" `
             -Credential (Get-Credential) `
             -Restart
```

**Step 1.3 — Run Install-UIAOServer.ps1** (provided in Section 5)
This script installs:
- IIS with required features
- HttpPlatformHandler module
- Python 3.13
- Git (for repo clone)

```powershell
# Run as Administrator
.\scripts\deploy\Install-UIAOServer.ps1 -PythonVersion "3.13" -Verbose
```

**Step 1.4 — Clone repository to server**
```powershell
cd C:\srv
git clone https://github.com/WhalerMike/uiao.git
cd uiao
git checkout governance/modernization/active-directory-api
```

**Step 1.5 — Install Python dependencies**
```powershell
cd C:\srv\uiao
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e impl/
pip install -r deploy\windows-server\requirements-windows.txt
```

---

### Phase 2: Active Directory Service Account (Day 3)

**Step 2.1 — Create service account** (run on a DC or RSAT machine)
```powershell
.\scripts\deploy\Register-ServiceAccount.ps1 `
    -AccountName "SVC-UIAO-API" `
    -ServerDNS "uiao-api.corp.contoso.com" `
    -Verbose
```

This script:
- Creates `SVC-UIAO-API` domain user
- Sets a long random password (stored in a vault or passed as SecureString)
- Grants read-all-user-attributes permission
- Registers SPN: `HTTP/uiao-api.corp.contoso.com`
- Registers SPN: `HTTP/uiao-api` (short form)

**Step 2.2 — Verify SPN**
```powershell
setspn -L SVC-UIAO-API
# Should show both HTTP SPNs
```

**Step 2.3 — Configure app pool identity**
The IIS app pool will run as `CORP\SVC-UIAO-API`. This means:
- Kerberos LDAP queries run under this identity (no password in code)
- The service ticket from IIS callers is automatically handled by the OS

---

### Phase 3: Entra ID App Registration (Day 3–4)

**Step 3.1 — Create app registration**
In Azure portal → Entra ID → App registrations → New registration:
- Name: `UIAO-AD-Survey`
- Supported account types: Single tenant
- No redirect URI needed (daemon app)

**Step 3.2 — Grant API permissions**
App registrations → `UIAO-AD-Survey` → API permissions:
- Add: `Microsoft Graph` → Application permissions:
  - `User.Read.All`
  - `Group.Read.All`
- Click: Grant admin consent

**Step 3.3 — Create client secret or certificate**
Certificates & secrets:
- Certificate (preferred): upload the server's TLS cert or generate dedicated cert
- Secret: create with 24-month expiry, note the value immediately

**Step 3.4 — Note credentials**
```
Tenant ID:     xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Client ID:     xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Client Secret: (vault it — never in code or git)
```

**Step 3.5 — Store in Windows environment (server)**
```powershell
# Store in machine-level environment (not user — IIS runs as service account)
[System.Environment]::SetEnvironmentVariable(
    "UIAO_ENTRA_TENANT_ID", "your-tenant-id",
    [System.EnvironmentVariableTarget]::Machine
)
[System.Environment]::SetEnvironmentVariable(
    "UIAO_ENTRA_CLIENT_ID", "your-client-id",
    [System.EnvironmentVariableTarget]::Machine
)
[System.Environment]::SetEnvironmentVariable(
    "UIAO_ENTRA_CLIENT_SECRET", "your-secret",
    [System.EnvironmentVariableTarget]::Machine
)
# Also set workspace root
[System.Environment]::SetEnvironmentVariable(
    "UIAO_WORKSPACE_ROOT", "C:\srv\uiao",
    [System.EnvironmentVariableTarget]::Machine
)
```

---

### Phase 4: IIS Site Configuration (Day 4–5)

**Step 4.1 — Run Register-UIAOAPI.ps1** (provided in Section 5)
```powershell
.\scripts\deploy\Register-UIAOAPI.ps1 `
    -SiteName "UIAO-API" `
    -AppPoolIdentity "CORP\SVC-UIAO-API" `
    -AppPoolPassword (Read-Host -AsSecureString) `
    -PhysicalPath "C:\inetpub\uiao-api" `
    -BindingPort 443 `
    -CertThumbprint "AABBCC..." `
    -Verbose
```

This script:
- Creates IIS app pool (No Managed Code, identity = service account)
- Creates IIS site bound to port 443
- Copies `deploy\windows-server\web.config` to site root
- Enables Windows Authentication, disables Anonymous
- Sets kernel-mode auth (Kerberos)

**Step 4.2 — Copy application files**
```powershell
# Copy the FastAPI app to the IIS physical path
$src = "C:\srv\uiao"
$dst = "C:\inetpub\uiao-api"
New-Item -ItemType Directory -Path $dst -Force
Copy-Item "$src\deploy\windows-server\web.config" $dst
Copy-Item "$src\deploy\windows-server\run.py" $dst
# Symlink or copy the impl package
New-Item -ItemType SymbolicLink -Path "$dst\uiao_impl" `
         -Target "$src\impl\src\uiao\impl"
```

**Step 4.3 — Test IIS starts Python**
```powershell
iisreset /noforce
# Check event log and C:\Logs\uiao-api\python.log
# Should see: "Uvicorn running on http://0.0.0.0:{PORT}"
```

---

### Phase 5: End-to-End Verification (Day 5–6)

**Step 5.1 — Health check (unauthenticated)**
```powershell
Invoke-WebRequest -Uri "https://uiao-api.corp.contoso.com/health" `
                  -UseDefaultCredentials
# Expected: {"status":"healthy","ad":"reachable","entra":"reachable"}
```

**Step 5.2 — Survey dry-run**
```powershell
$body = @{
    ldap_server = "dc01.corp.contoso.com"
    base_dn     = "DC=corp,DC=contoso,DC=com"
    dry_run     = $true
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "https://uiao-api.corp.contoso.com/api/v1/survey/run" `
    -Method POST `
    -Body $body `
    -ContentType "application/json" `
    -UseDefaultCredentials
```

**Step 5.3 — Verify Kerberos (not NTLM)**
```powershell
# On the server, check IIS logs for auth type
# Should see: cs-auth-header "Negotiate" not "NTLM"
# Event ID 4624 on DC should show LogonType 3 with AuthPackage Kerberos
```

**Step 5.4 — Verify Entra token**
```powershell
Invoke-RestMethod `
    -Uri "https://uiao-api.corp.contoso.com/api/v1/validate/entra-connectivity" `
    -UseDefaultCredentials
# Expected: {"token_acquired":true,"graph_reachable":true}
```

---

### Phase 6: Governance Gates (Days 6–8)

**Step 6.1 — Complete ADR-029**
Edit `src/uiao/canon/adr/adr-029-ad-survey-adapter.md` — fill in the
`status: proposed` stub with real decision rationale.

**Step 6.2 — Update modernization-registry.yaml**
Apply the entry from `registry-entry-and-adr.yaml` (from previous session).

**Step 6.3 — Add to document-registry.yaml**
```yaml
- id: UIAO_AD_001
  path: adr/adr-029-ad-survey-adapter.md
  title: Active Directory Survey Adapter
  status: proposed
```

**Step 6.4 — Run substrate walker**
```bash
# On any machine with the repo cloned
uiao substrate walk
# Must show zero P1 findings before PR
```

**Step 6.5 — Open PR**
Use the Appendix V PR template. Required fields:
- Change type: New Artifact
- Affected appendices: F, C, A, M
- Boundary impact: No (AD is read-only source; all writes go to AD not to M365 directly)
- CI must pass all 6 blocking workflows

---

### Phase 7: Pilot Survey (Week 2)

**Step 7.1 — Read-only survey: one domain**
Start with the smallest, least-critical domain in the forest.
```powershell
Invoke-RestMethod `
    -Uri "https://uiao-api.corp.contoso.com/api/v1/survey/run" `
    -Method POST `
    -Body (@{ ldap_server="dc01.east.corp.com"; base_dn="DC=east,DC=corp,DC=com"; dry_run=$true } | ConvertTo-Json) `
    -ContentType "application/json" `
    -UseDefaultCredentials
```

**Step 7.2 — Review unresolved queue**
Download `unresolved-queue.csv` from the output. This is the governance
review backlog — users who require HR data to get a valid OrgPath.

**Step 7.3 — OrgPath assignment dry-run**
With HR export in hand:
```powershell
Invoke-RestMethod `
    -Uri "https://uiao-api.corp.contoso.com/api/v1/orgpath/assign" `
    -Method POST `
    -Body (@{
        ldap_server = "dc01.east.corp.com"
        base_dn     = "DC=east,DC=corp,DC=com"
        hr_export   = "C:\data\hr-export.csv"
        dry_run     = $true   # No writes yet
    } | ConvertTo-Json) `
    -ContentType "application/json" `
    -UseDefaultCredentials
```

**Step 7.4 — Review report, govern unresolvables, approve write-back**
Governance Steward reviews `orgpath-assignment-report.json`.
When unresolved count = 0 (or unresolvables documented):
```powershell
# Set dry_run = false ONLY after governance approval
# This writes extensionAttribute1 to AD
# Entra Connect will pick up on next sync cycle (default: 30 min)
```

---

## 5. Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Kerberos token delegation fails | Medium | High | Verify SPN before deployment; test with `klist` |
| AD query times out on large forest | Medium | Medium | Use ldap3 paging; increase `requestTimeout` in web.config |
| MSAL token refresh fails | Low | Medium | Implement token cache; monitor expiry |
| extensionAttribute1 already in use | Medium | High | Survey existing values before ANY write-back |
| Entra Connect sync delay causes drift false positives | Medium | Low | Set drift detection grace period post-writeback |
| Service account password expires | Low | Critical | Set password never-expires + alert on 80% of expiry |
| IIS kills Python process on idle | Medium | Medium | Set app pool idle timeout to 0 in web.config |

---

## 6. Timeline Summary

| Phase | Duration | Owner | Gate |
|---|---|---|---|
| 0. Repository setup | 0.5 days | Dev | Branch created, files placed |
| 1. Server foundation | 1.5 days | Infra | IIS + Python running, domain joined |
| 2. Service account | 0.5 days | AD Admin | SPN verified with setspn |
| 3. Entra app registration | 0.5 days | Entra Admin | Token acquired in test |
| 4. IIS configuration | 1 day | Dev + Infra | Health endpoint responds |
| 5. End-to-end verification | 1 day | Dev | All 4 verification tests pass |
| 6. Governance gates | 2 days | Dev + Gov Steward | PR merged to main |
| 7. Pilot survey | 3 days | Dev + Gov Steward | Report reviewed, dry-run approved |
| **Total** | **~10 business days** | | |

---

## 7. Ongoing Operations

- **Entra Connect sync** runs every 30 minutes by default. OrgPath changes
  written to AD appear in Entra ID within one sync cycle.
- **Drift detection** (Appendix M) runs post-sync to validate that
  extensionAttribute1 values in Entra ID match what was written to AD.
- **Service account password**: set a calendar reminder 30 days before
  expiry; update IIS app pool identity and machine environment.
- **MSAL client secret**: set a calendar reminder 60 days before expiry;
  rotate in Entra ID and update machine environment variable.
- **API logs**: `C:\Logs\uiao-api\` — retain per Appendix X retention policy
  (Critical=7yr, High=3yr, Info=90d).
