
# Intune + Azure Arc — Add OrgPath Later (Retrofit) {.unnumbered}

You built the [manual path](manual-path.qmd) — servers are Arc-onboarded,
endpoints are Intune-enrolled, NTLM is restricted, SPNs are clean, SQL is
hardened, Conditional Access is enforced. Now you want governance: ownership,
approval routing, continuous evidence, drift detection.

**You do not re-do any of it.** The retrofit *adopts the estate you already have*
into the [governed path](governed-path.qmd). The Microsoft-side configuration
stays exactly as it is; you add the binding from organizational intent to the
objects that already exist.

::: {.callout-tip title="The core idea"}
The manual path already produced everything the control plane needs — Arc tags,
enrollment GPOs, CA policies, and the audit CSVs in `.\artifacts`. The retrofit
**reads** those, **derives OrgPath** from the structure you already have, and
**attaches the loop**. No reimaging, no re-onboarding, no re-enrollment.
:::

![Retrofit flow: an existing manually-built estate is inventoried, OrgPath is derived from existing tags/OUs/groups and stamped back, the estate is registered as desired state, and the observe/advise/gated loop is switched on — without changing the Microsoft-side configuration.](images/intune-arc-diagram-04-retrofit.png){#fig-retrofit fig-alt="Retrofit pipeline turning a manually-built estate into a governed estate without rebuilding it"}

## Why this works

The two paths share **one set of scripts** and converge on **one end state**.
The only difference is whether a state-changing call carries `-OrgPath` +
`-ApprovalRef`. So "adding governance" is not a migration — it is turning on the
seam that was always there. The read-only scripts you have been running *are
already* the observe step of the [reconciliation loop](governed-path.qmd#5-the-reconciliation-loop);
the retrofit just gives their output an owner and a home.

## The retrofit, step by step

### Step 1 — Inventory what the manual path already produced

Everything the control plane needs is already on disk or in the providers:

| Manual artifact | Where it is | Becomes (governed) |
|---|---|---|
| Arc server tags (`Environment`, `Workload`, `Owner`, …) | Azure resource tags | OrgPath segments + owner |
| Intune enrollment + compliance | `artifacts\intune-enrollment-status.csv` | endpoint desired/actual state |
| CA policy set | `artifacts\ca-baseline.json` | desired CA state |
| NTLM / SPN / SQL audits | `artifacts\*.csv` | per-domain Compare baselines |

```powershell
Import-Module .\lib\IntuneArcModernization.psm1
.\scripts\Get-ModernizationDriftReport.ps1 -ArtifactPath .\artifacts   # confirm every domain has fresh evidence
```

### Step 2 — Derive OrgPath from existing structure

You almost certainly already have the organizational structure implicitly — you
just have not named it as OrgPath. The kit's survey helper proposes it for you
from what already exists (advisory, read-only — it does **not** write):

```powershell
# propose OrgPath for servers from their Arc tags
.\scripts\Get-OrgPathSurvey.ps1 -SubscriptionId $sub -ArcResourceGroup rg-arc-servers -OutputPath .\artifacts\orgpath-proposal.csv
# propose OrgPath for workstations from their AD OU
.\scripts\Get-OrgPathSurvey.ps1 -WorkstationOU 'OU=Workstations,DC=agency,DC=gov' -OutputPath .\artifacts\orgpath-proposal.csv
```

It derives:

- **Servers** → from the `Environment` / `Workload` / `Owner` Arc tags, e.g.
  `/Agency/Infrastructure/<Workload>/<Environment>`.
- **Workstations** → from the workstation OU each device enrolled from, e.g.
  `/Agency/<Department>/Endpoints`.
- **Applications / CA scope** → from the app-owner groups that already gate access.

Each proposal carries a **confidence** flag — review the Low-confidence rows
before accepting. The derivation rules live in `ConvertTo-OrgPathProposal` in the
shared module; tune them to your naming. Map each segment to the Azure resource
hierarchy (management group → subscription → resource group → tags) so
organizational and technical scope align.

::: {.callout-note title="Survey proposes; the gated write stamps"}
`Get-OrgPathSurvey.ps1` is an **L2 (Advise)** helper — even where full automated
OrgPath assignment is not yet implemented, it gives you the proposed mapping to
review. Applying it is the existing **L3 (gated)** write: re-run the relevant
script with the accepted `-OrgPath` (Step 4).
:::

### Step 3 — Register the estate as desired state (L0)

Record the existing configuration as canon desired state — a one-time capture, no
writes to the providers. The CA baseline you already saved is literally this for
the CA domain:

```powershell
# capture current CA as the desired baseline if you have not already
.\scripts\Compare-ConditionalAccessDrift.ps1 -BaselinePath .\artifacts\ca-baseline.json
```

Do the equivalent per domain: the most recent audit CSV is the recorded actual
state that becomes the Compare baseline.

### Step 4 — Stamp OrgPath back onto the live objects

Re-run the state-changing scripts in **`-WhatIf`** first, now **with `-OrgPath`**,
to see exactly what the tag/label write would touch — without changing any
behavior:

```powershell
$org = '/Agency/Infrastructure/Servers/Production'
.\scripts\Invoke-ArcOnboarding.ps1 -SubscriptionId $sub -ResourceGroup rg-arc-servers -Location eastus `
    -OrgPath $org -ApprovalRef 'CR-RETROFIT-001' -WhatIf
```

Because the server is already onboarded, the agent step is a no-op; the effective
change is the addition of the `OrgPath` tag. Confirm, then run for real. Repeat
per OrgPath scope.

### Step 5 — Turn on observe + advise (L1 / L2)

Schedule the read-only scripts as the recurring observe/advise loop:

```powershell
.\scripts\Compare-ConditionalAccessDrift.ps1 -BaselinePath .\artifacts\ca-baseline.json
.\scripts\Get-ModernizationDriftReport.ps1 -ArtifactPath .\artifacts
```

Now drift is caught and classified continuously, scoped by OrgPath, instead of
discovered by incident.

### Step 6 — Promote selected domains to gated actuation (L3)

For each domain you want UIAO to reconcile, switch the operator habit from "run
the script bare" to "run it with `-OrgPath` + `-ApprovalRef`." That is the entire
promotion — `Assert-GovernanceApproval` then refuses any gated write that lacks
an approval, and logs every one that has it. The actuation ceiling stays at L3
(no autonomous actuation) unless you deliberately raise it.

## What does *not* change

- No device is re-imaged or re-enrolled.
- No server is re-onboarded or domain-rejoined.
- No CA policy is recreated — the existing set becomes the desired baseline.
- No NTLM/SPN/SQL work is repeated — the existing audits become the baselines.

The retrofit is additive. The manual path was never a dead end; it was the first
half of the governed path.

## Where to go next

- The full governed model: [Governed path (UIAO / OrgPath)](governed-path.qmd).
- The runbook you already followed: [Manual path](manual-path.qmd).
- The runnable kit: [Download](../../../download/index.qmd#intune--azure-arc-modernization).
