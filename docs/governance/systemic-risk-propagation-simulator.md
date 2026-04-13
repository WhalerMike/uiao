---
id: systemic-risk-propagation-simulator
title: "Governance Systemic-Risk Propagation Simulator"
owner: governance-board
status: DRAFT
---

# UIAO Governance Systemic-Risk Propagation Simulator

## Simulating How Local Failures Escalate into Systemic Governance Risk

This simulator models how local drift, SLA stress, schema divergence, and automation instability propagate into systemic governance failures.

---

## 1. Purpose

To test:

- How quickly local drift becomes systemic
- Which couplings (structural, referential, ownership, automation) drive propagation
- How SLA cascades and schema divergence amplify risk
- Which interventions most effectively contain propagation

---

## 2. Inputs

### A. Corpus and Topology

- Document graph (structural and referential links)
- Owner graph (ownership coupling)
- Automation graph (CI, workflows, webhooks)
- Schema version map

### B. Initial Conditions

- Initial drift set (documents, severities)
- Initial SLA state (at-risk, breached)
- Initial automation stability (CI, webhook, workflow)
- Initial schema divergence level

### C. Propagation Parameters

| Parameter | Symbol | Description |
|-----------|--------|-------------|
| Structural coupling weight | SC | How strongly structural links transmit drift |
| Referential coupling weight | RC | How strongly referential links transmit drift |
| Ownership coupling weight | OC | How strongly shared ownership transmits drift |
| Automation coupling weight | AC | How strongly automation failures transmit drift |
| SLA cascade sensitivity | SCS | Amplification of SLA stress on propagation |
| Schema divergence sensitivity | SDS | Amplification of schema drift on propagation |

---

## 3. Simulation Loop

At each timestep t:

### Step 1: Compute Local Drift Pressure

    LDP_i(t) = f(Drift_i, Severity_i, SDR_i)

Where SDR_i is the schema divergence rate for document i.

### Step 2: Compute Coupling Pressure

    CP_i(t) = SC_i + RC_i + OC_i + AC_i

### Step 3: Compute SLA Cascade Pressure

    SCP_i(t) = SCS * SLA_risk_i(t)

### Step 4: Compute Automation Instability

    AI_i(t) = 1 - AS_i(t)

Where AS_i(t) is automation stability at timestep t.

### Step 5: Propagation Probability

    P_prop_i(t) = sigmoid(alpha*LDP_i + beta*CP_i + gamma*SCP_i + delta*AI_i)

### Step 6: State Update

- Sample propagation events based on P_prop_i(t)
- Update drift set, SLA state, schema divergence, and automation stability
- Record propagation extent for time-series output

---

## 4. Outputs

- Time-series of propagation extent (documents, appendices, owners)
- Systemic-risk score over time
- SLA cascade curves
- Schema divergence curves
- Automation instability curves
- Intervention effectiveness comparison across playbook strategies

---

## 5. Use Cases

- Stress-testing governance runtime against worst-case drift scenarios
- Validating containment playbooks before deployment
- Tuning systemic-risk detection thresholds
- Prioritizing schema hardening and automation resilience investments

---

## 6. Intervention Scenarios

| Scenario | Intervention | Expected Outcome |
|----------|-------------|-----------------|
| Baseline | None | Unconstrained propagation |
| Schema pin | Pin schema version at t=5 | Reduce schema divergence spread |
| Owner reassignment | Reassign at-risk owners at t=10 | Break ownership coupling chain |
| CI hardening | Increase automation stability to 0.99 | Reduce automation instability pressure |
| Full containment | All interventions at t=5 | Rapid propagation suppression |

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
