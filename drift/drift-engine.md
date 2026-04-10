# UIAO Drift Engine Specification

The Drift Engine is the core of UIAO's continuous monitoring capability.

---

## Purpose

- Compare current evidence snapshots to previous snapshots
- Detect configuration drift across all monitored controls
- Generate findings for violations
- Trigger POA&M entries automatically
- Update OSCAL SAR with drift findings

---

## Drift Engine Flow

```
[Evidence Snapshot N]
  ↓
[Evidence Snapshot N+1]
  ↓
[Diff Engine]
  ↓
[Drift Detected?] → No → [Status: Compliant, Stop]
  ↓ Yes
[Drift Classification]
  ↓
[Finding Created]
  ↓
[POA&M Entry Generated]
  ↓
[Enforcement Policy Evaluation]
  ↓
[OSCAL SAR Updated]
```

---
drift/drift-engine.md
## 1. Evidence Comparison

The drift engine compares normalized evidence snapshots field by field:

- **Boolean fields**: MFAEnabled, LegacyAuthEnabled, SafeLinksEnabled, etc.
- **Numeric thresholds**: AdminCount, ConditionalAccessPoliciesCount, DLPPoliciesCount
- **Policy states**: Enforcement policy enable/disable status
- **Timestamps**: Last collection time vs. expected cadence

---

## 2. Drift Classification

| Severity | Description | Example |
|----------|-------------|---------|
| Low | Benign configuration change | AdminCount changed from 3 to 4 |
| Medium | Policy weakening detected | ExternalSharingEnabled changed to true |
| High | Critical control violation | MFAEnabled changed to false |
| Critical | Multiple simultaneous violations | MFA + Legacy Auth + Sharing all violated |

---

## 3. Finding Generation

Each drift event produces a finding object:

```json
{
  "finding_id": "FIND-0001",
  "control_id": "AC-21",
  "ir_object": "IR-SHARE-EXT-006",
  "evidence_before": { "ExternalSharingEnabled": false },
  "evidence_after": { "ExternalSharingEnabled": true },
  "severity": "Medium",
  "detected_at": "2026-04-10T00:00:00Z",
  "status": "Open"
}
```

---

## 4. POA&M Integration

- Auto-generate POA&M entry for each finding
- Assign severity and remediation milestones
- Link to evidence and provenance
- Track status: Open → In Progress → Closed

---

## 5. Enforcement Integration

After a finding is created:
1. Evaluate applicable EPL policies
2. If an enforcement action exists → trigger adapter
3. Collect post-enforcement evidence
4. Update finding status

---

## 6. OSCAL SAR Update

- Add finding to SAR results
- Reference evidence IDs
- Update control status
- Timestamp the update

---

## File Locations

```
uiao-core/drift/
  ├── drift-engine.md        (this file)
  ├── drift-engine.ps1       (implementation)
  └── snapshots/             (evidence snapshot store)
```
