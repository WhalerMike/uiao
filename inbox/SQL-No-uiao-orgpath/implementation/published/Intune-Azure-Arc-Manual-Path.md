
# Intune + Azure Arc — Manual Path {.unnumbered}

This is the modernization runbook for organizations executing **without** a
governance control plane — by structure, acquisition, expedited timeline, or
resource constraint. Every runbook and script here is self-contained: it is
meant to be run by technically qualified staff with no external advisory
dependency.

The manual path is not the *un-governed* path. Because no control plane validates
each decision in real time, **you** own the change record, the approval, and the
rollback. Document accepted risks in a change record before you begin, and treat
every first run as a `-WhatIf` dry run.

::: {.callout-important}
If you expect to add governance later, this path is designed so you can — see
[Add OrgPath later (retrofit)](../../../../docs/customer-documents/operational-guides/intune-arc-modernization/retrofit-path.qmd). Nothing here forecloses it.
:::

## 0. Phases and run order

Modernization runs in four phases. **Observe before you change anything.**

| Phase | Rung | What runs | Why |
|---|---|---|---|
| 1 — Observe | read-only | NTLM audit, SPN inventory, SQL audit, Intune posture | Baseline; you cannot safely restrict what you have not measured |
| 2 — Onboard | gated | Arc onboarding + baseline, Intune auto-enrollment | Attach the management planes |
| 3 — Harden | gated | SPN repair, NTLM restriction, CA baseline | Close the identity gaps — only after Phase 1 signs off |
| 4 — Watch | read-only | CA drift, cross-domain status | Keep it from drifting back |

```powershell
Install-Module Microsoft.Graph, Az, SqlServer -Scope CurrentUser
Import-Module .\lib\IntuneArcModernization.psm1
```

## 1. Prerequisites and assessment

::: {.callout-warning title="Do not skip assessment"}
Beginning Arc onboarding or Intune enrollment without completing the inventory
and the NTLM audit is the single most common cause of failed modernization:
authentication failures, policy conflicts, and application outages. Budget a
minimum of two weeks for assessment before any production change.
:::

**Licensing (verify before starting):** Intune (M365 E3 minimum; E5 adds
Defender for Endpoint P2), Entra ID P1 (CA) / P2 (risk-based CA), an Azure
subscription (Arc connectivity is free; extensions incur cost), Defender for
Servers Plan 2, Defender for SQL, and a Log Analytics workspace.

**Roles (least privilege):** *Azure Connected Machine Onboarding* (not Owner)
for Arc; *Intune Administrator* (via PIM) for endpoints; *Conditional Access
Administrator* for CA; *Hybrid Identity Administrator* for Azure AD Connect;
delegated OU admin for SPN work.

Baseline the estate (all read-only):

```powershell
.\scripts\Get-NtlmAudit.ps1 -DaysBack 30 -OutputPath .\artifacts\ntlm-audit.csv
.\scripts\Repair-Spn.ps1 -OutputPath .\artifacts\spn-inventory.csv
.\scripts\Invoke-SqlHardeningAudit.ps1 -ServerInstance 'sql01.agency.gov' -OutputPath .\artifacts\sql-hardening.csv
.\scripts\Get-IntuneEnrollmentStatus.ps1 -OutputPath .\artifacts\intune-enrollment-status.csv
```

## 2. Azure Arc onboarding (servers)

Azure Arc extends the Azure control plane to on-premises servers. The Connected
Machine Agent (CMA) makes an **outbound** HTTPS (443) connection — no inbound
firewall rules are required. Each server appears as a
`Microsoft.HybridCompute/machines` resource, enabling RBAC, tags, Policy, and
extensions.

::: {.callout-note title="Arc servers run non-domain-joined"}
Per the target architecture, Arc-enabled servers carry an Entra machine identity
and run **non-domain-joined**. Onboarding attaches the *management* plane; it does
**not** unjoin the domain for you. Domain-unjoin is a separately sequenced
decision — plan it, don't let onboarding imply it.
:::

```powershell
# preview, then run without -WhatIf
.\scripts\Invoke-ArcOnboarding.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus -WhatIf
.\scripts\Set-ArcPolicyBaseline.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus -WhatIf
```

`Invoke-ArcOnboarding.ps1` creates a least-privilege onboarding service
principal, installs and connects the CMA, and validates registration.
`Set-ArcPolicyBaseline.ps1` assigns the Windows security-baseline Guest
Configuration initiative and enables Defender for Servers Plan 2.

::: {.callout-warning title="Never embed the SP secret in a SYSVOL startup script"}
A service-principal secret in a GPO startup script is readable by every
domain-authenticated user via SYSVOL. Retrieve it at runtime from Key Vault, or —
for an expedited deployment — rotate the secret immediately after onboarding and
restrict the SP to the onboarding role only.
:::

**Tag taxonomy** (apply consistently — tags drive policy scope, cost, and
operational queries): `Environment`, `Workload`, `Criticality`, `Owner`,
`CostCenter`, plus `PatchGroup` and `ArcOnboardedDate`. On the governed path the
same taxonomy carries an `OrgPath` tag.

## 3. Intune endpoint modernization (workstations)

For an existing domain-joined fleet with Azure AD Connect, **Hybrid Azure AD
Join + auto-enrollment** is the lowest-friction path: no reimage, no user action.
Target it for the existing fleet before evaluating Autopilot for new procurement.

```powershell
.\scripts\Set-IntuneAutoEnrollment.ps1 -TargetOU 'OU=Workstations,DC=agency,DC=gov' -WhatIf
# verify on a client:  dsregcmd /status   (AzureAdJoined: YES, DomainJoined: YES, MDMUrl set)
.\scripts\Get-IntuneEnrollmentStatus.ps1 -OutputPath .\artifacts\intune-enrollment-status.csv
```

Deploy the critical configuration profiles in priority order: security baseline
(CIS-L1 equivalent), BitLocker (XTS-AES-256, TPM, recovery escrow to Entra),
Windows Hello for Business, Defender AV, firewall profiles, and modern LAPS.
Then attach the compliance policy (minimum OS, BitLocker, Secure Boot, code
integrity, Defender real-time, signature age ≤ 3 days, firewall, TPM, health
attestation) so non-compliant devices can be blocked by Conditional Access.

::: {.callout-note title="GPO ↔ Intune conflict"}
Where Intune and a GPO target the same setting (BitLocker, Defender, firewall),
last-writer-wins produces unpredictable results. Document overlapping settings
before enabling Intune policy in production, and retire the GPO copy once Intune
owns the setting. The companion **GPO Migration Triage** tool classifies every
GPO for Intune vs Arc.
:::

## 4. Identity modernization — NTLM elimination

NTLM is the most-exploited authentication weakness in AD estates (NTLM relay,
pass-the-hash, PetitPotam). The destination is Kerberos-only; the federal
deadline for NTLM elimination is **2027-04-01** (Notice 0009).

::: {.callout-warning title="Audit before you restrict"}
Prematurely blocking NTLM breaks legacy web apps, UNC file access without SPNs,
and some third-party apps. Enforce **only** after a 14–30 day audit confirms no
remaining dependencies and application owners sign off.
:::

**Staged elimination:**

| Stage | LSA `LmCompatibilityLevel` | `Restrict NTLM` |
|---|---|---|
| 1 — Audit | 3 (NTLMv2 only) | Audit NTLM in this domain = enable all |
| 2 — Restrict NTLMv1 | 4 (DC refuses LM) | Deny domain accounts (with exceptions) |
| 3 — Block all | 5 (DC refuses LM & NTLM) | Deny all; remove exceptions |

```powershell
.\scripts\Get-NtlmAudit.ps1 -DaysBack 30 -OutputPath .\artifacts\ntlm-audit.csv   # run daily across DCs
# after sign-off only:
.\scripts\Set-NtlmRestriction.ps1 -Level 5 -WhatIf
```

::: {.callout-important title="Enforcement layer"}
NTLM is blocked at the **LSA** layer (`LmCompatibilityLevel`) and via Group
Policy — **not** in Conditional Access. CA blocks *legacy auth to cloud apps*
only; it cannot block on-premises NTLM inside the domain.
:::

## 5. SPN audit and repair

Kerberos needs correct, unique Service Principal Names. A **duplicate** SPN
breaks Kerberos and silently falls back to NTLM; an SPN on a disabled account is
stale. Fix SPNs before enforcing Kerberos.

```powershell
.\scripts\Repair-Spn.ps1 -OutputPath .\artifacts\spn-inventory.csv               # audit + flag duplicates/stale
.\scripts\Repair-Spn.ps1 -Remove -Spn 'HTTP/app.agency.gov' -Account 'svc-app-old' -WhatIf
```

Validate post-repair with `klist purge` then access the service and confirm a
Kerberos ticket was issued (not NTLM). For SQL: `SELECT auth_scheme FROM
sys.dm_exec_connections WHERE session_id = @@SPID` should return `KERBEROS`.

## 6. SQL Server audit and hardening

```powershell
.\scripts\Invoke-SqlHardeningAudit.ps1 -ServerInstance 'sql01.agency.gov','sql02.agency.gov' -OutputPath .\artifacts\sql-hardening.csv
```

The audit reports authentication mode (Windows-auth-only is the goal), the
dangerous server-config switches that should be **off** (`xp_cmdshell`, OLE
Automation, CLR, cross-DB ownership chaining, Database Mail XPs, …), and the `sa`
account status. Then Arc-connect the SQL hosts and enable Defender for SQL.

::: {.callout-note title="SQL engine authentication is a separate, deeper track"}
This audit covers the **hardening checklist** only. Replacing Windows/SQL
authentication with **Entra ID** for SQL Server 2022+ (OAuth tokens, managed
identity for the engine, MFA for human principals) is its own engine-layer
transformation. Use the canonical SQL authentication audit and the SQL Server
identity-transformation guidance for that track.
:::

## 7. Conditional Access baseline

```powershell
.\scripts\Deploy-ConditionalAccessBaseline.ps1 -BreakGlassGroupId $bg -WhatIf
```

The baseline creates the core policies — block legacy auth, require MFA, require
compliant device, require MFA for admins and for the Azure management plane — in
**report-only** state. Measure impact, then promote to enforce as a **separate**
change.

::: {.callout-warning title="Always exclude break-glass"}
Exclude a break-glass account group from every policy before enforcing, or you
can lock yourself out. Keep two cloud-only break-glass accounts with long unique
passwords, excluded from all CA, and alert on their use.
:::

## 8. Monitoring and drift

```powershell
.\scripts\Compare-ConditionalAccessDrift.ps1 -BaselinePath .\artifacts\ca-baseline.json   # first run captures the baseline
.\scripts\Get-ModernizationDriftReport.ps1 -ArtifactPath .\artifacts -OutputPath .\artifacts\modernization-status.csv
```

Send Arc heartbeat, Intune compliance, AD audit, and Defender alerts to Log
Analytics with defined alert rules. The cross-domain report rolls up which
domains have fresh evidence and the headline pass/attention counts — your weekly
status page.

## 9. Rollback

Define rollback criteria before you begin. Each domain has a defined back-out:

- **Intune:** un-enroll devices and re-apply the GPO baseline.
- **Arc:** `azcmagent disconnect` then uninstall the agent.
- **Conditional Access:** keep policies report-only until validated; the
  break-glass accounts are the emergency exclusion.
- **NTLM:** revert `LmCompatibilityLevel` to 3 if a missed dependency surfaces —
  this is exactly why the audit gate exists.

## 10. What you must configure

Search the scripts for `# CONFIGURE:` — tenant id, subscription id, resource
group, location/cloud (`AzureCloud` vs `AzureUSGovernment`), workstation OU DN,
break-glass group id, SQL instance list. The scripts are correct against current
Microsoft Graph / Az PowerShell but are **not** validated against a live tenant.
Dry-run with `-WhatIf` before removing the guards.
