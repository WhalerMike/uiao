---
id: governance-dashboard-wireframe
title: "UIAO Governance Dashboard -- UI Wireframe (Text Spec)"
owner: governance-team
status: DRAFT
---

# UIAO Governance Dashboard -- UI Wireframe (Text Spec)

This document defines the high-level layout and interaction model for the governance dashboard.

---

## 1. Layout Overview

**Top Bar:** Left: Product name (UIAO Governance) | Center: Environment badge (prod / staging) | Right: User menu

**Primary Navigation (left sidebar):**
- Corpus Index
- Owners & SLAs
- Weekly Reports
- CI & Enforcement
- Settings (governance only)

---

## 2. Corpus Index View

**Header Row:** Title, Filters (Owner, Status, Drift Severity, Appendix, Date range), Actions (Export CSV, Open latest weekly report)

**Main Table Columns:**
1. Document ID (clickable -> detail drawer)
2. Title
3. Owner (avatar + handle)
4. Status (pill: healthy, needs remediation, missing metadata)
5. Drift Severity (pill: none, low, medium, critical)
6. Last Updated (timestamp)
7. Open Issues (count, clickable)
8. Actions (Open remediation PR, View drift details)

**Row Interaction:** Click row -> right-side detail drawer showing frontmatter summary,
open drift items, links to repo / latest PR / weekly issue entry.

---

## 3. Owners & SLAs View

**Owner Cards (grid or list):** Each card shows owner name + avatar, team/group, counts
(open drift items, critical items, items >72h unacknowledged, items >14d unresolved),
and buttons (View assigned documents, View remediation PRs).

---

## 4. Weekly Reports View

**List:** Each row shows week label, total items / critical / resolved, link to GitHub issue, status (open / in progress / closed).

**Detail Panel:** Breakdown by owner, top 10 documents by severity, trend chart over last N weeks.

---

## 5. CI & Enforcement View

Summary tiles: last CI run status, number of failing PRs, average time to fix CI metadata failures.

Table of recent PRs with metadata failures: PR number, title, owner, error type, age, link to logs.

---

## 6. Global Interaction Patterns

- Clicking an owner name anywhere -> Owner detail view.
- Clicking a document ID anywhere -> Document detail drawer.
- All severity/status pills are filterable chips.
- All lists sortable by severity, age, owner, and status.
