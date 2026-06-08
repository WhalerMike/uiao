# Intune + Azure Arc Modernization — Implementation Path

**Audience:** Cloud Platform, Identity Engineering, Security Operations, IT Leadership
**Scope:** Windows 10/11 endpoints · Windows Server 2016–2022 · Azure Arc · SQL Server · NTLM/SPN · Conditional Access
**Status:** Reference implementation for agency review and adaptation
**Companion code:** `scripts/` (Microsoft Graph + Az PowerShell) · `lib/IntuneArcModernization.psm1`

> This document turns the modernization domains into one executable path with
> **two ways to run it**: a **manual path** (you own each decision) and a
> **UIAO/OrgPath-governed path** (every change is bound to an organizational
> path, an actuation rung, and an approval). The **same scripts** serve both —
> the governance layer is a swappable seam, the execution layer does not change.

---

## 0. The two paths, one toolkit

| | Manual path | Governed path (UIAO / OrgPath) |
|---|---|---|
| How you invoke | `-WhatIf` to preview, then run | add `-OrgPath` + `-ApprovalRef` |
| Who owns the decision | the operator + local change control | the OrgPath owner; recorded approval |
| Write gating | your `-WhatIf`/`-Confirm` | `Assert-GovernanceApproval` enforces the actuation ceiling |
| Evidence | whatever you capture | structured actor + OrgPath + approval log per write |
| When to choose it | small estate, expedited, no control plane yet | enterprise scale, audit/attestation required |

Both paths produce the **same end state** on the Microsoft surface. The governed
path adds the binding from organizational intent to technical change. If you
build the manual path now, you can **retrofit** the governed path later without
redoing the Intune/Arc work — see [§6](#6-retrofitting-governance-later).

> **A note on terminology (read before the governed path).** In this repo,
> **UIAO** is the *Unified Identity-Addressing-Overlay Architecture* — an
> **active reconciliation control plane** that *governs* provider data planes
> (Entra, Intune, Azure Policy, AD), per **ADR-092**. It holds desired state,
> observes actual state, classifies drift, and reconciles toward intent. It is
> **not** an inline runtime component and it does not replace the providers.
> OrgPath is the organizational path carried by every governed object so its
> state is addressable in the same terms across every plane.

---

## 1. The modernization-domain spine

This single table is the source of truth, encoded as data in
`lib/IntuneArcModernization.psm1` (`Get-ModernizationDomains`) so the runbook
and the code never drift. Each domain names its script, its highest actuation
rung, the target plane, and the canon ADR that governs it.

| Domain | Plane | Script | Rung | Canon |
|---|---|---|---|---|
| Server onboarding | Azure Arc | `Invoke-ArcOnboarding.ps1` | L3 | ADR-002 |
| Server baseline | Azure Arc | `Set-ArcPolicyBaseline.ps1` | L3 | ADR-002 |
| Endpoint enrollment | Intune | `Set-IntuneAutoEnrollment.ps1` | L3 | ADR-071 / ADR-080 |
| Endpoint posture | Intune | `Get-IntuneEnrollmentStatus.ps1` | L1 | ADR-071 / UIAO_011 |
| NTLM elimination | Identity (LSA) | `Get-NtlmAudit.ps1` | L1 | ADR-068 |
| NTLM enforcement | Identity (LSA) | `Set-NtlmRestriction.ps1` | L3 | ADR-068 |
| SPN hygiene | Identity (AD) | `Repair-Spn.ps1` | L3 | ADR-068 |
| SQL hardening | Data (SQL) | `Invoke-SqlHardeningAudit.ps1` | L1 | ADR-091 |
| Conditional Access | Security (Entra) | `Deploy-ConditionalAccessBaseline.ps1` | L3 | ADR-092 |
| CA drift | Security (Entra) | `Compare-ConditionalAccessDrift.ps1` | L1 | ADR-040 |
| Cross-domain drift | All | `Get-ModernizationDriftReport.ps1` | L1 | ADR-040 / ADR-092 |
| OrgPath survey | All | `Get-OrgPathSurvey.ps1` | L2 | UIAO_011 / ADR-092 |

### The actuation maturity ladder (ADR-092)

Every state-changing operation declares a rung. The **federal default write
ceiling is L3** — autonomous (L4) actuation is refused in-boundary.

| Rung | Name | Meaning |
|---|---|---|
| L0 | Record | desired state in canon only |
| L1 | Observe | collect actual state, detect drift (read-only) |
| L2 | Advise | generate the corrective change-set, surface it (no writes) |
| L3 | Gated | a human approves; UIAO executes via the provider API (dry-run default) |
| L4 | Auto | the loop closes without a human (above the federal ceiling) |

---

## 2. Run order

```powershell
# One-time prerequisites
Install-Module Microsoft.Graph, Az, SqlServer -Scope CurrentUser
Import-Module .\lib\IntuneArcModernization.psm1

# --- Phase 1: observe (read-only, L1) — baseline before you change anything ---
.\scripts\Get-NtlmAudit.ps1 -DaysBack 30 -OutputPath .\artifacts\ntlm-audit.csv      # run 14–30 days
.\scripts\Repair-Spn.ps1 -OutputPath .\artifacts\spn-inventory.csv                    # audit only
.\scripts\Invoke-SqlHardeningAudit.ps1 -ServerInstance 'sql01.agency.gov' -OutputPath .\artifacts\sql-hardening.csv
.\scripts\Get-IntuneEnrollmentStatus.ps1 -OutputPath .\artifacts\intune-enrollment-status.csv

# --- Phase 2: onboard (gated, L3) — preview with -WhatIf first ---
.\scripts\Invoke-ArcOnboarding.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus -WhatIf
.\scripts\Set-ArcPolicyBaseline.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus -WhatIf
.\scripts\Set-IntuneAutoEnrollment.ps1 -TargetOU 'OU=Workstations,DC=agency,DC=gov' -WhatIf

# --- Phase 3: harden (gated, L3) — only AFTER the Phase-1 audits sign off ---
.\scripts\Repair-Spn.ps1 -Remove -Spn 'HTTP/app.agency.gov' -Account 'svc-app-old' -WhatIf
.\scripts\Set-NtlmRestriction.ps1 -Level 5 -WhatIf
.\scripts\Deploy-ConditionalAccessBaseline.ps1 -BreakGlassGroupId $bg -WhatIf   # report-only

# --- Phase 4: keep watching (L1) — weekly ---
.\scripts\Compare-ConditionalAccessDrift.ps1 -BaselinePath .\artifacts\ca-baseline.json
.\scripts\Get-ModernizationDriftReport.ps1 -ArtifactPath .\artifacts
```

Every state-changing script supports **`-WhatIf`**. Run it first.

---

## 3. Platform realities the code enforces

1. **Arc-enabled servers run non-domain-joined (ADR-002).** Onboarding attaches
   the *management* plane; it does not unjoin for you. Domain-unjoin is a
   separately sequenced decision — do not let `Invoke-ArcOnboarding` imply it.
2. **NTLM is blocked at the LSA layer, not in Conditional Access (ADR-068).**
   `Set-NtlmRestriction` sets `LmCompatibilityLevel`; CA only gates *cloud*
   auth. Never restrict NTLM before `Get-NtlmAudit` confirms zero remaining
   dependencies and app owners sign off (minimum 14–30 day audit).
3. **Duplicate SPNs silently break Kerberos** and fall back to NTLM. Fix SPNs
   (`Repair-Spn`) before enforcing Kerberos.
4. **CA baselines deploy report-only.** `Deploy-ConditionalAccessBaseline`
   creates policies in `enabledForReportingButNotEnforced`. Measure impact, then
   promote to enforce as a **separate** gated change. Always exclude a
   break-glass group.
5. **SQL engine auth is owned by ADR-091, not this kit.** This kit's
   `Invoke-SqlHardeningAudit` covers the hardening-checklist surface only; the
   Windows/SQL→Entra engine-auth transformation uses the canonical
   `Get-SQLServerAuthAudit.ps1` (Spec3-D1.8).

---

## 4. What you must configure

Search the scripts for `# CONFIGURE:` — tenant id, subscription id, resource
group, location/cloud (`AzureCloud` vs `AzureUSGovernment`), the workstation OU
DN, the break-glass group id, and the SQL instance list. The connectors are
scaffolded against current Microsoft Graph / Az PowerShell but are **not**
validated against a live tenant. Treat first runs as `-WhatIf` dry runs.

---

## 5. The governed path in practice

On the governed path you add two parameters to any state-changing script:

```powershell
.\scripts\Invoke-ArcOnboarding.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus `
    -OrgPath '/Agency/Infrastructure/Servers/Production' -ApprovalRef 'CR0012345'
```

`Assert-GovernanceApproval` then:

- refuses any write whose rung exceeds the actuation ceiling (default L3 — no L4);
- refuses a gated (L3) write that has no `-ApprovalRef`;
- logs actor + OrgPath + rung + approval for the evidence trail; and
- stamps `OrgPath` as an Azure tag where the provider supports it, so the
  object is addressable in the same terms across planes (ADR-092 requirement #3).

What the governed path adds on top of the providers — expressed in **canon**
terms, not invented components:

- **Desired state in canon** with `plan / apply / reconcile` adapters (ADR-036–039).
- **The OrtTree Drift Detection Engine** (ADR-040): Snapshot → Compare →
  Classify → Alert → Remediate → Verify, `dry_run=True` by default, with
  high-blast-radius operations gated for governance review.
- **Provider incorporation, not replacement** (ADR-092): Entra/Intune/Azure
  Policy/AD remain the data planes; UIAO reconciles their state against canon
  and emits evidence.

---

## 6. Retrofitting governance later

If you ran the **manual path** first, you do not redo the Intune/Arc work to add
governance. You **map what exists** onto OrgPath and attach the loop. The
step-by-step retrofit (import the estate, derive OrgPath from existing tags /
OUs / groups, attach approvals, turn on drift) is its own guide — see the
customer page **"Add OrgPath later (retrofit)."** In short:

1. **Inventory the manual artifacts** the scripts already produced (Arc tags,
   enrollment GPOs, CA policies, SPN/SQL/NTLM audits in `.\artifacts`).
2. **Derive OrgPath** from existing structure with `Get-OrgPathSurvey.ps1` — it
   *proposes* an OrgPath per server/endpoint from Arc tags and AD OUs (advisory,
   read-only). Review, then stamp it back onto each governed object with the
   existing scripts' `-OrgPath` parameter.
3. **Register the estate** as desired state in canon (L0).
4. **Turn on observe + advise** (L1/L2) with the drift report and CA drift.
5. **Promote selected domains to gated actuation** (L3) by adding `-OrgPath` +
   `-ApprovalRef` to the same scripts. Nothing else changes.

---

## 7. Source / canon cross-reference

| This guide | Source draft | Canon |
|---|---|---|
| §1 spine, ladder | Both guides §1–3 | ADR-092 |
| Arc onboarding | Manual §3; Governed §4 | ADR-002 |
| Intune enrollment | Manual §4; Governed §5 | ADR-071 / ADR-080 |
| NTLM elimination | Manual §5; Governed §6 | ADR-068 |
| SPN repair | Manual §6; Governed §7 | ADR-068 |
| SQL hardening | Manual §7; Governed §8 | ADR-091 |
| Conditional Access | Manual §8; Governed §9 | ADR-092 |
| Drift / monitoring | Manual §9; Governed §9.4/§10 | ADR-040 / ADR-092 |

> The source drafts named UIAO as "Unified IT Architecture Oversight" / "Universal
> Identity and Access Operations." Both are non-canonical; this kit uses the canon
> definition (Unified Identity-Addressing-Overlay Architecture, ADR-092) throughout.
