"""OrgPath facet assigner — derive facet values from AD object records.

Consumes a plain AD object record (a dict of AD attributes, from the live
directory reader or a survey export) plus an :class:`OrgPathMapping` and the
Codebook (UIAO_151), and produces a :class:`FacetAssignmentResult`: the
per-facet values that should be written to Entra/ARM, plus findings for any AD
value that does not map cleanly onto the codebook enum.

This is pure (no I/O) and therefore fully offline-testable. The live LDAP read
lives in the directory reader; the Entra/ARM write lives in the existing
adapters. This module is the assessment in between.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable, Mapping

from uiao.modernization.orgtree.ad_mapping import FacetRule, OrgPathMapping, default_mapping
from uiao.modernization.orgtree.codebook import Codebook, default_codebook

# AD accountExpires sentinels meaning "never expires" → no term_date.
_NEVER_EXPIRES = {"0", "9223372036854775807"}
# DN fragments that mark a privileged group for account_type derivation.
_PRIVILEGED_GROUPS = (
    "domain admins",
    "enterprise admins",
    "schema admins",
    "administrators",
    "account operators",
    "backup operators",
)
_GENERALIZED_TIME_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})\d{6}")
_ISO_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})")


@dataclass(frozen=True)
class AssignmentFinding:
    """One facet that could not be derived/validated for a target."""

    facet: str
    source_value: str
    reason: str
    severity: str = "P3"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class FacetAssignmentResult:
    """The derived per-facet values + findings for one AD object."""

    target_id: str
    target_type: str  # "user" | "device"
    facet_values: Mapping[str, str] = field(default_factory=dict)
    findings: tuple[AssignmentFinding, ...] = ()

    @property
    def assigned_count(self) -> int:
        return len(self.facet_values)

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "facet_values": dict(self.facet_values),
            "findings": [f.to_dict() for f in self.findings],
        }


def _target_id(record: Mapping[str, Any]) -> str:
    for key in ("id", "objectGUID", "distinguishedName", "sAMAccountName"):
        val = record.get(key)
        if val:
            return str(val)
    return ""


def _normalize_date(raw: str) -> str | None:
    """Normalise an AD date value to ``YYYY-MM-DD``; return None if unparseable."""
    raw = raw.strip()
    if not raw or raw in _NEVER_EXPIRES:
        return ""
    m = _GENERALIZED_TIME_RE.match(raw)  # e.g. 20200115103000.0Z
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = _ISO_DATE_RE.match(raw)  # e.g. 2020-01-15 or 2020-01-15T10:30:00Z
    if m:
        return m.group(1)
    return None


def _derive_account_type(record: Mapping[str, Any], default: str | None) -> str | None:
    spns = record.get("servicePrincipalNames") or record.get("servicePrincipalName") or []
    object_classes = [str(c).lower() for c in (record.get("objectClass") or [])]
    if spns or any("managedserviceaccount" in c for c in object_classes):
        return "Service"
    member_of = [str(g).lower() for g in (record.get("memberOf") or [])]
    if any(pg in dn for dn in member_of for pg in _PRIVILEGED_GROUPS):
        return "Privileged"
    return default


def _raw_source_value(rule: FacetRule, record: Mapping[str, Any]) -> str:
    """The record's raw value for a rule's source attribute (first of a list), trimmed."""
    if not rule.source:
        return ""
    raw = record.get(rule.source)
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
    return "" if raw is None else str(raw).strip()


def _candidate_for_rule(rule: FacetRule, record: Mapping[str, Any]) -> str | None:
    """Apply a rule's transform to the record, returning a raw facet candidate."""
    if rule.transform == "derive_account_type":
        return _derive_account_type(record, rule.default)

    raw = record.get(rule.source) if rule.source else None
    if isinstance(raw, (list, tuple)):
        raw = raw[0] if raw else None
    raw_str = "" if raw is None else str(raw).strip()

    if rule.transform == "date":
        if not raw_str:
            return rule.default
        return _normalize_date(raw_str)

    if not raw_str:
        return rule.default

    if rule.transform == "passthrough":
        return raw_str

    # transform == "alias"
    lowered = raw_str.lower()
    if rule.match == "exact":
        return rule.aliases.get(lowered, rule.default)
    # substring: first alias key contained in the raw value wins
    for key, value in rule.aliases.items():
        if key in lowered:
            return value
    return rule.default


class OrgPathAssigner:
    """Derive OrgPath facet values from AD object records (pure)."""

    def __init__(self, mapping: OrgPathMapping | None = None, codebook: Codebook | None = None) -> None:
        self.mapping = mapping or default_mapping()
        self.codebook = codebook or default_codebook()

    def assign(self, record: Mapping[str, Any], *, target_type: str = "user") -> FacetAssignmentResult:
        """Derive facet values for one AD object record."""
        facet_values: dict[str, str] = {}
        findings: list[AssignmentFinding] = []

        for rule in self.mapping.rules:
            facet = self.codebook.facet(rule.facet) if self.codebook.has_facet(rule.facet) else None
            if facet is None:
                findings.append(AssignmentFinding(rule.facet, "", f"facet '{rule.facet}' is not in the codebook", "P2"))
                continue

            candidate = _candidate_for_rule(rule, record)
            raw_value = _raw_source_value(rule, record)
            raw_present = bool(raw_value)

            if candidate is None or candidate == "":
                # Empty is legitimate for facets that allow it (e.g. term_date);
                # only flag when the facet requires a value.
                if candidate == "" and facet.is_active(""):
                    facet_values[rule.facet] = ""
                elif raw_present:
                    # The AD attribute had a value, but it didn't map to a
                    # codebook value and there's no default → unmapped (P2).
                    findings.append(
                        AssignmentFinding(
                            rule.facet,
                            raw_value,
                            f"AD value '{raw_value}' did not map to a valid '{rule.facet}' codebook value",
                            "P2",
                        )
                    )
                elif candidate is None:
                    findings.append(
                        AssignmentFinding(
                            rule.facet,
                            "",
                            f"no AD value for source '{rule.source}' and no default",
                        )
                    )
                continue

            if facet.is_active(candidate):
                facet_values[rule.facet] = candidate
            else:
                findings.append(
                    AssignmentFinding(
                        rule.facet,
                        raw_value or candidate,
                        f"derived value '{candidate}' is not a valid '{rule.facet}' codebook value",
                        "P2",
                    )
                )

        return FacetAssignmentResult(
            target_id=_target_id(record),
            target_type=target_type,
            facet_values=facet_values,
            findings=tuple(findings),
        )

    def assign_all(
        self, records: Iterable[Mapping[str, Any]], *, target_type: str = "user"
    ) -> list[FacetAssignmentResult]:
        return [self.assign(r, target_type=target_type) for r in records]
