# UIAO Compliance Query Language (CQL)

## Query Types

### 1. Control Status
```cql
SHOW CONTROLS WHERE status = 'FAIL' AND severity >= 'Medium';
```

### 2. Evidence Lookup
```cql
SHOW EVIDENCE FOR CONTROL 'AC-21' SINCE '2026-04-01';
```

### 3. Drift Queries
```cql
SHOW DRIFT WHERE tenant = 'contoso' AND control = 'IA-2';
```

### 4. POA&M Queries
```cql
SHOW POAM WHERE status = 'Open' ORDER BY severity DESC;
```

## Execution Model
- CQL is translated to:
  - Graph queries (for relationships)
  - Data lake queries (for time-series evidence)
- Read-only by default
