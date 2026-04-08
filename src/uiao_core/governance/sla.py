from __future__ import annotations

from typing import Dict

# Governance escalation SLA (days to escalate/act).
# Distinct from POA&M remediation SLA — these are tighter.
SLA_BY_SEVERITY: Dict[str, int] = {
    "Critical": 7,
    "High": 14,
    "Medium": 30,
    "Low": 60,
}

DEFAULT_SLA_DAYS = 30


def resolve_sla_days(severity: str) -> int:
    """Map a severity string to a governance escalation SLA in days."""
    return SLA_BY_SEVERITY.get(severity, DEFAULT_SLA_DAYS)
