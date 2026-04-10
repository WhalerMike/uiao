# UIAO Enforcement Runtime Specification

## 1. Policy Evaluation
- Parse EPL policy
- Evaluate condition against IR objects
- If condition = true → violation

---

## 2. Enforcement Execution
- Identify enforcement adapter
- Execute adapter with required parameters
- Capture adapter output

---

## 3. Evidence Collection
- Collect post-enforcement evidence
- Hash evidence
- Bind evidence to IR object
- Update provenance

---

## 4. POA&M Update
- If violation persists → keep POA&M open
- If resolved → close POA&M entry

---

## 5. OSCAL SAR Update
- Update SAR findings
- Update evidence references

---

## Enforcement Runtime Flow

```
[EPL Policy]
  ↓
[Condition Evaluator]
  ↓
[Violation?] → No → [Stop]
  ↓ Yes
[Enforcement Adapter]
  ↓
[Evidence Collector]
  ↓
[POA&M Update]
  ↓
[OSCAL SAR Update]
```

---

## Runtime States

| State | Description |
|-------|-------------|
| EVALUATING | Policy condition is being assessed |
| COMPLIANT | Condition is false, no violation |
| VIOLATED | Condition is true, enforcement required |
| ENFORCING | Adapter is executing |
| REMEDIATED | Violation resolved after enforcement |
| FAILED | Enforcement adapter failed |

---

## Integration Points

- **Input**: EPL policy files from `uiao-core/policy/`
- **IR Objects**: Read from normalized SCuBA evidence
- **Enforcement Adapters**: Located in `uiao-core/adapters/enforcement/`
- **Output**: Updated evidence, POA&M entries, OSCAL SAR
