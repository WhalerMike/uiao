---
id: ci-testplan-metadata-validator
title: "Test Plan -- UIAO Metadata Validator CI Workflow"
owner: docs-ops
status: DRAFT
---

# Test Plan -- UIAO Metadata Validator CI Workflow

This test plan verifies that the CI enforcement workflow correctly detects metadata
drift, blocks merges, and provides actionable feedback.

---

## 1. Objectives

- Confirm validator runs on every PR to main.
- Confirm schema violations block merges.
- Confirm error messages identify file, field, and violation type.
- Confirm emergency bypass path works only with governance approval.

---

## 2. Test Matrix

### A. Positive Tests (should pass)

**1. Valid frontmatter**
- All required fields present.
- No deprecated fields.
- Expected: CI passes.

**2. Non-metadata changes**
- Narrative edits only.
- Expected: CI passes (validator ignores content).

**3. Valid new document**
- New file with correct metadata.
- Expected: CI passes.

---

### B. Negative Tests (should fail)

**1. Missing required field**
- Remove `owner` or `status`.
- Expected: CI fails with explicit missing-field error.

**2. Deprecated field present**
- Add `category:` or other removed keys.
- Expected: CI fails with deprecation error.

**3. Invalid ID format**
- Introduce malformed ID.
- Expected: CI fails with ID-format error.

**4. Broken YAML**
- Indentation or colon error.
- Expected: CI fails with YAML parse error.

**5. Cross-reference failure**
- Link to nonexistent appendix or ID.
- Expected: CI fails with reference error.

---

## 3. Emergency Bypass Test

- Apply label `ci-metadata-bypass`.
- Governance reviewer must approve.
- Expected: CI still runs but merge allowed.

---

## 4. Reporting Validation

Confirm CI logs show:
- File path
- Field name
- Error type
- Suggested fix

---

## 5. Acceptance Criteria

- 100% of negative tests fail as expected.
- 100% of positive tests pass.
- Error messages are deterministic and reproducible.
- Emergency bypass requires documented governance approval.

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
