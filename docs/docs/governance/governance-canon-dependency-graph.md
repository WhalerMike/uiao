---
id: governance-canon-dependency-graph
title: "Governance Canon Dependency Graph"
owner: governance-board
status: DRAFT
---

# UIAO Governance Canon Dependency Graph

## Cross-Volume Dependency Map

This document defines the dependency relationships between all canonical governance volumes.

---

## 1. Dependency Diagram

```mermaid
flowchart TD
    Blue["Blue Book: Core Canon"] --> Red
    Blue --> Green
    Blue --> Black
    Blue --> White
    Blue --> Silver
    Blue --> Gold
    Blue --> Platinum
    Blue --> Obsidian
    Blue --> Crystal

    Red["Red Book: Incident Response"] --> Silver
    Red --> Black
    Red --> Obsidian

    Green["Green Book: Schema and Normalization"] --> Black
    Green --> Silver
    Green --> Obsidian

    Black["Black Book: Runtime and Automation"] --> Red
    Black --> Gold
    Black --> Obsidian

    Platinum["Platinum Book: Federation"] --> Obsidian
    Platinum --> Gold

    White["White Book: Ethics and Provenance"] --> Silver
    White --> Gold
    White --> Crystal

    Silver["Silver Book: Owner and SLA Governance"] --> Gold

    Obsidian["Obsidian Book: Security and Zero-Trust"] --> Gold

    Crystal["Crystal Book: Visualization"] --> Gold

    Gold["Gold Book: Executive Strategy"]
```

---

## 2. Dependency Rules

- Blue Book is the root of the canon. All other volumes extend it.
- Gold Book is the apex. It depends on all other volumes.
- No circular dependencies exist.
- Platinum Book (federation) and Obsidian Book (security) are peers that reinforce each other.
- Crystal Book (visualization) consumes outputs from all volumes but does not modify them.

---

## 3. Dependency Summary Table

| Volume | Depends On | Extended By |
|--------|-----------|-------------|
| Blue Book | None (root) | All others |
| Red Book | Blue, Black | Gold, Obsidian |
| Green Book | Blue | Black, Silver, Obsidian |
| Black Book | Blue, Green | Red, Gold, Obsidian |
| Platinum Book | Blue | Obsidian, Gold |
| Obsidian Book | Blue, Red, Green, Black, Platinum | Gold |
| Crystal Book | Blue, all others (data) | Gold |
| White Book | Blue | Silver, Gold, Crystal |
| Silver Book | Blue, Red, Green, White | Gold |
| Gold Book | All others | None (apex) |

---

## 4. Canonical Flow

    Blue Book (Root)
        -> Domain Books (Red, Green, Black, Platinum, Obsidian, White, Silver, Crystal)
        -> Gold Book (Apex)

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
