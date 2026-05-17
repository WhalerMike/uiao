# SQL Modernization Research — Inbox Draft

> **Status:** Draft research, not canon. Promotion path is documented in the
> research artifact's §9 (Proposed Canonical Actions).

## Contents

| File | Purpose |
|---|---|
| [`2026-05-17-sql-modernization-strategy-expansion.md`](2026-05-17-sql-modernization-strategy-expansion.md) | Full research artifact: SQL surface audit + single-not-stacked core database doctrine + proposed canon edits |

## Scope at a glance

The artifact answers: where does SQL already live in the UIAO substrate,
and what does the AD-to-Entra modernization need to add so the steady
state is a *single* canonical core operating database rather than a
*stack* of vendor SoR databases? The argument touches OrgPath / OrgTree
(UIAO_007, UIAO_010–012), session-to-tagged-network-security (ADR-073,
UIAO_012), the SSOT principle (UIAO_001), and the Compliance Data Lake
model (UIAO_109).

## Proposed canonical follow-ons

- **ADR-074** — Single Core Operating Database Doctrine
- **UIAO_013** — OrgPath in the Core Operating Database
- **UIAO_109 v2.0** — Data Lake anchored to a Core Operating Store
- **ADR-068 amend** — Auth modernization scope beyond SQL Server
- **UIAO_135 amend** — Data-Plane Transformation rows (7a / 7b / 7c)
- **DM_090 amend** — Workload → Substrate bridge
- **UIAO_001 (UIAO-SSOT) amend** — New drift class `DRIFT-PERSISTENCE`
  with sub-class `::stacked-sor`

Each item is sized for one PR with one ADR or one canon-document
amendment. Sequencing is recorded in §10.3 of the artifact.

## How to review

1. Read §0 (Executive Summary) and §2 (the stacked-databases problem)
   for the framing.
2. Read §4 for the architectural decision (target = Azure SQL DB; OrgPath
   is the row-level join key on every governed object).
3. Read §6 and §7 for the OrgPath and session-tagged-network-security
   data models in the proposed core DB.
4. Read §9 for the canon-PR work that follows.
5. Open issues for any of the §10.2 governance-review questions.
