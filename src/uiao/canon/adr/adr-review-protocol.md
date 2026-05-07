---
document_id: UIAO_134
title: "ADR Review Protocol — Keeping Architectural Decisions Current"
version: "1.0"
status: Current
classification: OPERATIONAL
owner: Michael Stratton
boundary: GCC-Moderate
created_at: "2026-04-28"
updated_at: "2026-04-28"
---

# ADR Review Protocol — Keeping Architectural Decisions Current

> **Purpose:** Define the mechanisms, cadence, and responsibilities for ensuring UIAO Architectural Decision Records remain accurate as the Microsoft platform evolves.

---

## 1. The Problem

Architectural decisions in cloud-native identity are built on platform capabilities that Microsoft updates continuously. An ADR that was correct at decision time can become stale, wrong, or unnecessarily conservative within a single product cycle. UIAO cannot afford to build on assumptions that have silently expired.

## 2. Review Mechanisms

### 2.1 Event-Driven Reviews (Highest Priority)

These external events trigger mandatory ADR review within 5 business days of the event.

| Event | Frequency | ADRs Affected | Action |
|---|---|---|---|
| **Microsoft Ignite** | November annually | ALL ADRs | Review all identity/device/provisioning announcements against every ADR |
| **Microsoft Build** | May annually | ALL ADRs | Review all identity/device/provisioning announcements against every ADR |
| **OPM HR Vendor Selection** | One-time (expected mid-2026) | ADR-003 | Evaluate whether native connector replaces or supplements API-driven path |
| **GAO Protest Decision** | One-time (expected June 2026) | ADR-003 | Assess procurement timeline impact on architecture timing |
| **Windows Server vNext Announcement** | Ad hoc | ADR-001, ADR-002 | Evaluate new device/server identity capabilities |
| **Entra ID Breaking Change Notice** | Ad hoc | Affected ADRs | Assess impact on decided architecture patterns |

### 2.2 Cadence-Based Reviews (Scheduled)

| Cadence | Scope | Responsible | Method |
|---|---|---|---|
| **Monthly** | Scan Entra ID changelog for decision-relevant changes | Canon Steward | Review Microsoft Entra changelog (https://learn.microsoft.com/en-us/entra/fundamentals/whats-new) |
| **Quarterly** | Formal ADR status review as part of UIAO governance cycle | Canon Steward | Re-verify all Verification Sources; update Last Verified dates |
| **Annually** | Full ADR re-evaluation — challenge all assumptions | Canon Steward + Stakeholders | Re-run original research; validate rationale still holds |

### 2.3 Signal-Based Reviews (Automated Monitoring)

These are specific Microsoft documentation pages and changelog feeds that, if changed, may invalidate an ADR assumption.

#### ADR-001 Watch List (HAADJ Deprecation)
| Signal | URL | What to Watch For |
|---|---|---|
| Autopilot HAADJ enrollment page | https://learn.microsoft.com/en-us/autopilot/windows-autopilot-hybrid | Removal of deprecation notice; new HAADJ capabilities |
| Autopilot Device Preparation overview | https://learn.microsoft.com/en-us/autopilot/device-preparation/overview | Addition of HAADJ support |
| Cloud-native endpoints planning guide | https://learn.microsoft.com/en-us/mem/solutions/cloud-native-endpoints/cloud-native-endpoints-planning-guide | Change in join type recommendation |
| Entra ID What's New | https://learn.microsoft.com/en-us/entra/fundamentals/whats-new | Any device identity announcement |

#### ADR-002 Watch List (Arc Server Join)
| Signal | URL | What to Watch For |
|---|---|---|
| Arc-enabled server Entra ID sign-in | https://learn.microsoft.com/en-us/entra/identity/devices/howto-vm-sign-in-azure-ad-windows | Domain-join coexistence support; OS version expansion |
| Azure Arc release notes | https://learn.microsoft.com/en-us/azure/azure-arc/servers/release-notes | AADLoginForWindows extension updates |
| Windows Server release info | https://learn.microsoft.com/en-us/windows-server/get-started/windows-server-release-info | New server versions with identity changes |

#### ADR-003 Watch List (API-Driven Provisioning)
| Signal | URL | What to Watch For |
|---|---|---|
| API-driven inbound provisioning concepts | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/inbound-provisioning-api-concepts | API changes; new connector announcements |
| Entra ID provisioning What's New | https://learn.microsoft.com/en-us/entra/identity/app-provisioning/whats-new-docs | Native Oracle HCM connector; API deprecation |
| OPM HR IT procurement news | Federal News Network, GovExec | Vendor selection; GAO decision |

#### ADR-004 Watch List (Workload Identity Federation)
| Signal | URL | What to Watch For |
|---|---|---|
| Workload identity federation overview | https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation | Federated credential limit changes; new platform support |
| CA for workload identities | https://learn.microsoft.com/en-us/entra/identity/conditional-access/workload-identity | New policy controls for WIF |
| GitHub OIDC Azure docs | https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-azure | OIDC implementation changes |

## 3. Review Procedure

### 3.1 Monthly Changelog Scan (15 minutes)

1. Open the Entra ID What's New page
2. Filter to current month
3. Search for keywords: `device`, `join`, `Autopilot`, `Arc`, `provisioning`, `inbound`, `workload identity`, `federation`, `HAADJ`, `hybrid`, `service account`, `managed identity`
4. For each relevant entry: check if it impacts any ADR assumption
5. If impact found: create GitHub Issue tagged `adr-review` with the ADR ID and the change description
6. If no impact: log "No ADR impact" in monthly governance notes

### 3.2 Quarterly Verification (1 hour)

1. For each ADR, visit every URL in the Verification Sources table
2. Confirm the page still exists and the cited content is unchanged
3. Update the `Last Verified` date in each ADR
4. Check each Review Trigger checkbox — has the trigger condition occurred?
5. If any verification source has changed substantively: initiate a full ADR re-evaluation
6. Commit updated ADRs with message: `chore(adr): quarterly verification YYYY-QN`

### 3.3 Event-Driven Review (30-60 minutes)

1. Within 5 business days of the triggering event
2. Re-read the ADR's Decision and Rationale sections
3. Assess whether the event changes any of the rationale points
4. Document findings in the ADR's Review Triggers section (check the box, add date and finding)
5. If the decision is still valid: add a note with date and "Reaffirmed — [event] did not change decision basis"
6. If the decision needs amendment: update the ADR version, add Amendment section, update status to AMENDED
7. If the decision is superseded: create new ADR, update old ADR status to SUPERSEDED with pointer

### 3.4 Full Re-Evaluation (2-4 hours, annually)

1. Re-run the original research for each ADR
2. Challenge every assumption — is the rationale still valid?
3. Check competitor/alternative approaches — has the landscape shifted?
4. Validate consequences — did the predicted positive/negative outcomes materialize?
5. Update or reaffirm each ADR with findings

## 4. ADR Amendment vs. Supersession

| Situation | Action | ADR Status |
|---|---|---|
| Minor factual update (URL changed, version number updated) | Edit in place, bump version | ACCEPTED (unchanged) |
| Rationale refined but decision unchanged | Add Amendment section, bump version | AMENDED |
| Decision partially changed (scope narrowed/expanded) | Add Amendment section, bump version | AMENDED |
| Decision fundamentally changed | Create new ADR (ADR-NNN), update old with `superseded_by` pointer | Old: SUPERSEDED; New: ACCEPTED |
| Decision no longer relevant (feature deprecated, context eliminated) | Update status, add deprecation rationale | DEPRECATED |

## 5. Automation Opportunities

### 5.1 GitHub Actions — ADR Freshness Check (Recommended)

A scheduled GitHub Action that runs monthly and checks if any ADR's `next_review` date has passed without a version bump.

```yaml
# .github/workflows/adr-freshness.yml
name: ADR Freshness Check
on:
  schedule:
    - cron: '0 9 1 * *'  # First of each month at 9 AM
  workflow_dispatch:

jobs:
  check-freshness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Check ADR review dates
        run: |
          today=$(date +%Y-%m-%d)
          stale=0
          for adr in ADR/ADR-*.md; do
            next_review=$(grep '^next_review:' "$adr" | awk '{print $2}')
            if [[ "$next_review" < "$today" ]]; then
              echo "::warning file=$adr::ADR overdue for review (next_review: $next_review)"
              stale=$((stale + 1))
            fi
          done
          if [ $stale -gt 0 ]; then
            echo "::error::$stale ADR(s) overdue for review"
            exit 1
          fi
```

### 5.2 Copilot Tasks — Monthly Changelog Monitor (Optional)

A scheduled Copilot task that runs monthly, scans the Entra ID What's New page for decision-relevant changes, and sends a summary via chat or email.

### 5.3 GitHub Issue Templates — ADR Review Request

```yaml
# .github/ISSUE_TEMPLATE/adr-review.yml
name: ADR Review Request
description: Request review of an Architectural Decision Record
title: "[ADR Review] ADR-NNN: <title>"
labels: ["adr-review", "governance"]
body:
  - type: dropdown
    id: adr-id
    attributes:
      label: ADR ID
      options:
        - ADR-001
        - ADR-002
        - ADR-003
        - ADR-004
  - type: dropdown
    id: trigger-type
    attributes:
      label: Review Trigger
      options:
        - Scheduled (monthly/quarterly/annual)
        - Event-driven (Ignite/Build/announcement)
        - Signal-based (documentation changed)
        - Ad hoc (new information discovered)
  - type: textarea
    id: change-description
    attributes:
      label: What changed or was discovered?
  - type: textarea
    id: impact-assessment
    attributes:
      label: Potential impact on ADR decision
```

## 6. Governance Integration

ADR reviews are part of the UIAO quarterly governance cycle:

1. **Quarterly Governance Checklist** includes "ADR Verification Complete" as a required sign-off
2. **Governance Dashboard** shows ADR freshness status (green = verified this quarter, yellow = review pending, red = overdue)
3. **Canon Steward** is responsible for ADR review execution
4. **ADR amendments** follow the same provenance chain as other UIAO canonical artifacts (SHA-256 linked, git-committed, PR-reviewed)
