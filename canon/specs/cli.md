---
document_id: UIAO_106
title: "UIAO Compliance CLI"
version: "1.0"
status: Current
classification: CANONICAL
owner: "Michael Stratton"
created_at: "2026-04-14"
updated_at: "2026-04-14"
boundary: "GCC-Moderate"
---

# UIAO Compliance CLI

The UIAO Compliance CLI provides a command-line interface for operators and maintainers to run assessments, inspect evidence, manage drift, generate OSCAL outputs, and test enforcement policies.

---

## Installation

The CLI is a PowerShell module located at:

```
uiao-core/cli/uiao-cli.ps1
```

Import and use:
```powershell
Import-Module ./uiao-core/cli/uiao-cli.ps1
```

---

## Commands

### uiao scuba run
Runs the full SCuBA pipeline locally.

```
uiao scuba run [--tenant <tenantId>] [--output <path>]
```

Steps executed:
1. adapter-run-scuba.ps1
2. normalize.ps1
3. evaluate-ksi.ps1
4. generate-manifest.ps1

---

### uiao evidence show <id>
Displays a single evidence object by ID.

```
uiao evidence show EV-0001
```

Output: JSON evidence object with hash and provenance reference.

---

### uiao evidence list
Lists all evidence objects.

```
uiao evidence list [--control <control-id>] [--collector <name>]
```

---

### uiao drift check
Runs the drift engine against the last two evidence snapshots.

```
uiao drift check [--severity <low|medium|high|critical>]
```

Output: List of drift findings with severity and affected controls.

---

### uiao oscal emit
Generates OSCAL outputs from current evidence.

```
uiao oscal emit --ssp --output ./oscal/ssp.json
uiao oscal emit --sap --output ./oscal/sap.json
uiao oscal emit --sar --output ./oscal/sar.json
uiao oscal emit --poam --output ./oscal/poam.json
```

---

### uiao enforce test <policy>
Tests an EPL enforcement policy without applying changes (dry run).

```
uiao enforce test enforce_mfa
uiao enforce test disable_legacy_auth
```

Output: Would-be enforcement actions and affected resources.

---

### uiao enforce apply <policy>
Applies an EPL enforcement policy (live run).

```
uiao enforce apply enforce_mfa
```

Requires: UIAO.Admin or UIAO.Operator role.

---

### uiao poam list
Lists all POA&M entries.

```
uiao poam list [--status <open|closed|all>]
```

---

### uiao poam close <id>
Closes a POA&M entry after remediation is verified.

```
uiao poam close POAM-0001
```

Requires: Evidence that the control is now satisfied.

---

### uiao health
Checks the health of the UIAO environment.

```
uiao health
```

Checks: ScubaGear installation, PowerShell version, repo access, credential status.

---

## File Location

```
uiao-core/cli/
  ├── uiao-cli.md        (this file)
  └── uiao-cli.ps1       (implementation)
```
