from __future__ import annotations

from typing import Dict

# Owner mapping by KSI prefix. Load from config in a future iteration.
OWNER_BY_KSI_PREFIX: Dict[str, str] = {
    "KSI-IA": "team-identity@contoso.gov",
    "KSI-AC": "team-access@contoso.gov",
    "KSI-AU": "team-audit@contoso.gov",
    "KSI-SC": "team-sec-arch@contoso.gov",
}

DEFAULT_OWNER = "team-compliance@contoso.gov"


def resolve_owner_for_ksi(ksi_id: str) -> str:
    """Resolve an owner email for a given KSI ID based on prefix."""
    for prefix, owner in OWNER_BY_KSI_PREFIX.items():
        if ksi_id.startswith(prefix):
            return owner
    return DEFAULT_OWNER
