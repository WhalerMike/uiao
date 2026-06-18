"""AD-compatibility schema veneer for the Active Governance Directory (ADR-110).

ADR-110 lets the AGD project a bounded, opt-in, **read-only** veneer of
AD-shaped attributes (`sAMAccountName`, `userPrincipalName`, `displayName`,
the AD `objectClass` values, and a synthetic `objectSid`) **synthesized at
read time** from the governed principal data — never stored. The veneer is
compatibility *shape*, not directory *authority*: it never makes the AGD an
AD domain controller, and the synthetic SID is **non-authoritative**.

The synthetic ``objectSid`` is deterministic and namespaced under one
reserved synthetic domain (so every AGD SID is recognisably from the same
non-authoritative source), and every veneered entry carries a
``uiaoSyntheticSid: TRUE`` marker advertising that the SID must never be
honoured as a security principal (ADR-110 §2).
"""

from __future__ import annotations

import hashlib
import re

# Reserved synthetic domain identifier (the three SID sub-authorities) shared
# by every AGD-synthesised SID. Derived deterministically from a fixed marker
# so it is stable and recognisable — and advertised non-authoritative, never
# minted by a real AD domain (ADR-110 §2).
_SYNTHETIC_DOMAIN_MARKER = "UIAO-AGD-SYNTHETIC-DOMAIN"
_RID_FLOOR = 100_000  # keep RIDs in the ordinary user range, deterministically

# AD objectClass values added (on top of the existing projection classes) per
# principal type. Bounded allow-list — nothing outside this is synthesised.
_AD_OBJECTCLASS_BY_TYPE = {
    "user": ["person", "organizationalPerson", "user"],
    "device": ["computer"],
    "servicePrincipal": ["user"],
}

# sAMAccountName legal-ish chars; AD disallows " / \ [ ] : ; | = , + * ? < > @
_SAM_ILLEGAL = re.compile(r"[^A-Za-z0-9._\-]+")
_SAM_MAX = 20  # the classic AD sAMAccountName length limit


def _hash_int(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big")


def _subauthorities(marker: str) -> tuple[int, int, int]:
    digest = hashlib.sha256(marker.encode("utf-8")).digest()
    return (
        int.from_bytes(digest[0:4], "big"),
        int.from_bytes(digest[4:8], "big"),
        int.from_bytes(digest[8:12], "big"),
    )


_DOMAIN = _subauthorities(_SYNTHETIC_DOMAIN_MARKER)


def synthetic_sid(principal_id: str) -> str:
    """A deterministic, namespaced, non-authoritative synthetic SID (string form).

    Format ``S-1-5-21-<d1>-<d2>-<d3>-<rid>``: the three domain sub-authorities
    are fixed (the reserved synthetic domain); the RID is derived from the
    principal id. Stable across calls, never an authoritative AD SID.
    """
    rid = _RID_FLOOR + (_hash_int(principal_id) % 900_000)
    return f"S-1-5-21-{_DOMAIN[0]}-{_DOMAIN[1]}-{_DOMAIN[2]}-{rid}"


def sam_account_name(principal_id: str) -> str:
    """Derive a deterministic AD ``sAMAccountName`` from the principal id."""
    local = principal_id.split("@", 1)[0]
    cleaned = _SAM_ILLEGAL.sub("-", local).strip("-") or "principal"
    return cleaned[:_SAM_MAX]


def user_principal_name(principal_id: str) -> str:
    """The UPN: the principal id when already UPN-shaped, else as-is."""
    return principal_id


def ad_object_classes(principal_type: str) -> list[str]:
    """The AD ``objectClass`` values to add for ``principal_type``."""
    return list(_AD_OBJECTCLASS_BY_TYPE.get(principal_type, _AD_OBJECTCLASS_BY_TYPE["user"]))


def synthesize(principal_id: str, principal_type: str) -> dict[str, list[str]]:
    """Return the bounded AD-shaped attribute veneer for one principal.

    Read-only and non-authoritative: ``objectSid`` is synthetic (advertised by
    ``uiaoSyntheticSid``) and none of these attributes are governed facets, so
    a write to any of them is refused (ADR-109 §2 / ADR-110 §4).
    """
    return {
        "sAMAccountName": [sam_account_name(principal_id)],
        "userPrincipalName": [user_principal_name(principal_id)],
        "displayName": [principal_id],
        "objectSid": [synthetic_sid(principal_id)],
        "uiaoSyntheticSid": ["TRUE"],
    }
