# Intune + Azure Arc Modernization kit (manual + UIAO/OrgPath-governed)

Built from the three drafts in `../` (NO-UIAO Intune+Arc guide, WITH-GOVERNANCE
OrgPath guide, NO-UIAO script pack). Doctrine is reconciled to repo **canon** —
the drafts' invented UIAO/OrgPath definitions are not used. Only platforms the
agency already runs appear (Entra ID, Intune, Azure Arc, Azure Policy, AD).

## Contents

| File | What it is |
|---|---|
| `implementation-path.md` | **Start here.** The two-path operating model, the modernization-domain spine, the actuation ladder, run order, and the retrofit summary. |
| `lib/IntuneArcModernization.psm1` | Shared module. The domain spine (`Get-ModernizationDomains`), the Connect helpers, the **governance seam** (`Assert-GovernanceApproval`), the actuation ladder, and risk lists. **Extend the spine here.** |
| `scripts/Invoke-ArcOnboarding.ps1` | Arc: SP create + CMA install + connect + validate. |
| `scripts/Set-ArcPolicyBaseline.ps1` | Arc: Guest Config security baseline + Defender for Servers. |
| `scripts/Set-IntuneAutoEnrollment.ps1` | Intune: Hybrid AADJ MDM auto-enrollment GPO. |
| `scripts/Get-IntuneEnrollmentStatus.ps1` | Intune: enrollment/compliance report (read-only). |
| `scripts/Get-NtlmAudit.ps1` | Identity: NTLM (4776) audit + summary (read-only). |
| `scripts/Set-NtlmRestriction.ps1` | Identity: staged NTLM block at the LSA layer. |
| `scripts/Repair-Spn.ps1` | Identity: duplicate/orphan SPN detect + repair. |
| `scripts/Invoke-SqlHardeningAudit.ps1` | Data: SQL hardening checklist audit (read-only). |
| `scripts/Deploy-ConditionalAccessBaseline.ps1` | Security: core CA set, report-only. |
| `scripts/Compare-ConditionalAccessDrift.ps1` | Security: CA drift vs JSON baseline (read-only). |
| `scripts/Get-ModernizationDriftReport.ps1` | Cross-domain status roll-up (read-only). |
| `scripts/Get-OrgPathSurvey.ps1` | Retrofit helper: **propose** OrgPath from existing Arc tags / AD OUs (advisory, read-only — does not write). |
| `published/` | Cleaned `.md` (+ AutoFit `.docx`) of the two reference guides. |

## Quick start

```powershell
Install-Module Microsoft.Graph, Az, SqlServer -Scope CurrentUser
Import-Module .\lib\IntuneArcModernization.psm1

# observe first (read-only)
.\scripts\Get-NtlmAudit.ps1 -DaysBack 30
# preview everything that changes state
.\scripts\Invoke-ArcOnboarding.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus -WhatIf
```

Search the scripts for `# CONFIGURE:` for the values you must supply.

**Manual vs governed:** run with `-WhatIf` then bare for the manual path; add
`-OrgPath` + `-ApprovalRef` for the governed path. The same scripts serve both.

> Reference implementation for review/adaptation — correct against current
> Microsoft Graph / Az PowerShell, not validated against a live tenant. Dry-run
> with `-WhatIf` before removing the guards.
