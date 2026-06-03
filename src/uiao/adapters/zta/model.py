"""Typed models for a Microsoft Zero Trust Assessment report.

Field names in the source artefact are PascalCase (``TestId``, ``TestStatus``,
``TestMinimumLicense``…). We expose pythonic ``snake_case`` attributes and map
them with a ``to_pascal`` alias generator, accepting either spelling on input.
Unknown fields are ignored so the models tolerate tool-version drift.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_pascal

# Outcome values emitted by the tool. Only FAILED / INVESTIGATE are findings;
# SKIPPED / PLANNED / ERROR are coverage / applicability signals, never gaps.
STATUS_PASSED = "Passed"
STATUS_FAILED = "Failed"
STATUS_SKIPPED = "Skipped"
STATUS_PLANNED = "Planned"
STATUS_INVESTIGATE = "Investigate"
STATUS_ERROR = "Error"

#: Canonical display order for statuses.
STATUS_ORDER: tuple[str, ...] = (
    STATUS_FAILED,
    STATUS_INVESTIGATE,
    STATUS_PASSED,
    STATUS_SKIPPED,
    STATUS_PLANNED,
    STATUS_ERROR,
)

#: Statuses that represent an actionable finding.
ACTIONABLE_STATUSES: frozenset[str] = frozenset({STATUS_FAILED, STATUS_INVESTIGATE})


class _ZtBase(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_pascal,
        populate_by_name=True,
        extra="ignore",
    )


class ZtTest(_ZtBase):
    """A single check result within a Zero Trust Assessment report."""

    test_id: str = Field(default="")
    test_title: str = Field(default="")
    test_description: str = Field(default="")
    test_pillar: str | None = Field(default=None)
    test_sfi_pillar: str | None = Field(default=None)
    test_category: str | None = Field(default=None)
    test_risk: str = Field(default="")
    test_impact: str = Field(default="")
    test_implementation_cost: str = Field(default="")
    test_status: str = Field(default="")
    test_result: str = Field(default="")
    test_skipped: str | None = Field(default=None)
    skipped_reason: str | None = Field(default=None)
    test_applies_to: list[str] | None = Field(default=None)
    test_minimum_license: list[str] = Field(default_factory=list)
    test_tags: list[str] | None = Field(default=None)

    @field_validator("test_id", mode="before")
    @classmethod
    def _coerce_id(cls, value: Any) -> str:
        """``TestId`` is a string for Graph checks but an int for some checks."""
        return "" if value is None else str(value)

    @field_validator("test_minimum_license", mode="before")
    @classmethod
    def _coerce_license(cls, value: Any) -> list[str]:
        """``TestMinimumLicense`` is sometimes a list, sometimes a bare string."""
        if value is None:
            return []
        if isinstance(value, str):
            return [value] if value else []
        if isinstance(value, list):
            return [str(item) for item in value]
        return [str(value)]

    @property
    def is_finding(self) -> bool:
        """True when this result is an actionable finding (Failed / Investigate)."""
        return self.test_status in ACTIONABLE_STATUSES

    @property
    def pillar(self) -> str:
        """Pillar with a stable fallback for grouping."""
        return self.test_pillar or "(none)"


class ZtReport(_ZtBase):
    """A full Zero Trust Assessment report.

    ``test_result_summary`` is preserved verbatim but is **not** authoritative —
    in shipped reports it does not reconcile with ``Tests[]``. Always recompute
    roll-ups from :attr:`tests` (see :func:`uiao.adapters.zta.triage.build_triage`).
    """

    executed_at: str | None = Field(default=None)
    tenant_id: str | None = Field(default=None)
    tenant_name: str | None = Field(default=None)
    domain: str | None = Field(default=None)
    account: str | None = Field(default=None)
    current_version: str | None = Field(default=None)
    latest_version: str | None = Field(default=None)
    test_result_summary: dict[str, Any] = Field(default_factory=dict)
    tests: list[ZtTest] = Field(default_factory=list)
    tenant_info: dict[str, Any] = Field(default_factory=dict)
    is_demo: bool = Field(default=False)
