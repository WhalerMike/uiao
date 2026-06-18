"""AISystemRecord — machine-identity schema for federal AI systems.

Every deployed or piloted federal AI system inventoried under M-25-21 /
EO 13960 is an identity subject in UIAO's machine-identity surface. This
module defines the canonical record shape, lifecycle states, and
OrgPath-binding rules.

Canon reference: UIAO_196, ADR-109 §2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DevStage(str, Enum):
    """M-25-21 development_stage values (normalised)."""

    PRE_DEPLOYMENT = "pre-deployment"
    PILOT = "pilot"
    DEPLOYED = "deployed"
    RETIRED = "retired"
    UNKNOWN = "unknown"


class AgentClass(str, Enum):
    """OMB classification field normalised to UIAO agent types.

    ``AGENTIC`` entries operate autonomously inside the identity substrate
    and carry the highest governance priority per ADR-109 §4.
    """

    AGENTIC = "agentic-ai"
    ML = "classical-ml"
    GENERATIVE = "generative-ai"
    NLP = "nlp"
    COMPUTER_VISION = "computer-vision"
    REINFORCEMENT = "reinforcement-learning"
    OTHER = "other"


class ATOStatus(str, Enum):
    YES = "yes"
    NO = "no"
    NOT_APPLICABLE = "not-applicable"
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# OrgPath binding for AI systems (ADR-109 §2 field mapping)
# ---------------------------------------------------------------------------


def _orgpath_from_bureau(agency: str, bureau: str) -> str | None:
    """Derive the OrgPath namespace prefix from agency + bureau.

    Returns a colon-separated prefix (e.g. ``DOD:DISA``) that callers
    can extend with a system-specific leaf.  Returns None when either
    input is blank — the absence itself is a drift finding.
    """
    a = (agency or "").strip().upper()
    b = (bureau or "").strip()
    if not a:
        return None
    if not b or b.upper() == a:
        return a
    return f"{a}:{b}"


# ---------------------------------------------------------------------------
# AISystemRecord
# ---------------------------------------------------------------------------


@dataclass
class AISystemRecord:
    """Machine-identity record for one federal AI system.

    Populated from one row of the OMB 2025 Federal AI Use Case Inventory
    CSV.  The record is the unit of comparison for drift detection: each
    field has an expected UIAO governance state; deviations become
    ``Finding`` objects in the scanner.

    Fields are named after the OMB inventory columns where they come from
    so the mapping is auditable without consulting a separate table.
    """

    # --- OMB identity keys ------------------------------------------------
    omg_id: str  # inventory ``id`` field
    use_case_name: str
    agency: str  # abbreviated (e.g. ``DOD``)
    agency_name: str  # full name
    agency_bureau: str

    # --- lifecycle state --------------------------------------------------
    development_stage: DevStage
    agent_class: AgentClass
    operational_date: str | None  # ISO date string or empty

    # --- authorization ----------------------------------------------------
    ato_status: ATOStatus
    system_name_ato: str | None  # UIAO registry join key

    # --- identity governance fields ---------------------------------------
    vendor_name: str | None  # → KYC / NERM non-employee surface
    contact_email: str | None  # owner identity anchor
    has_pii: bool
    pia_url: str | None

    # --- high-impact checklist (M-25-21 §V) ------------------------------
    is_high_impact: bool
    hi_testing_conducted: str | None
    hi_assessment_completed: str | None
    hi_independent_review: str | None
    hi_ongoing_monitoring: str | None
    hi_failsafe_presence: str | None
    hi_appeal_process: str | None

    # --- UIAO-derived fields (set by scanner) ----------------------------
    orgpath: str | None = field(default=None)
    # ``orgpath`` is populated by the scanner from agency + bureau.
    # A None value after population is itself a P2 finding.

    @classmethod
    def from_csv_row(cls, row: dict) -> AISystemRecord:
        """Construct from one row of the OMB CSV (header → value dict)."""

        def _bool(v: str) -> bool:
            s = str(v).strip().lower()
            # OMB inventory uses "High-impact" / "yes" / "true" / "1"
            return s in {"yes", "true", "1"} or s.startswith("high-impact")

        def _stage(v: str) -> DevStage:
            v = (v or "").strip().lower()
            mapping = {
                "deployed": DevStage.DEPLOYED,
                "pilot": DevStage.PILOT,
                "pre-deployment": DevStage.PRE_DEPLOYMENT,
                "pre_deployment": DevStage.PRE_DEPLOYMENT,
                "retired": DevStage.RETIRED,
            }
            return mapping.get(v, DevStage.UNKNOWN)

        def _agent(v: str) -> AgentClass:
            v = (v or "").strip().lower()
            if "agentic" in v:
                return AgentClass.AGENTIC
            if "generative" in v:
                return AgentClass.GENERATIVE
            if "natural language" in v or "nlp" in v:
                return AgentClass.NLP
            if "computer vision" in v:
                return AgentClass.COMPUTER_VISION
            if "reinforcement" in v:
                return AgentClass.REINFORCEMENT
            if "classical" in v or "predictive" in v or "machine learning" in v:
                return AgentClass.ML
            return AgentClass.OTHER

        def _ato(v: str) -> ATOStatus:
            v = (v or "").strip().lower()
            if v in {"yes", "true", "1"}:
                return ATOStatus.YES
            if v in {"no", "false", "0"}:
                return ATOStatus.NO
            if "not applicable" in v or "n/a" in v:
                return ATOStatus.NOT_APPLICABLE
            return ATOStatus.UNKNOWN

        def _opt(v: str) -> str | None:
            s = (v or "").strip()
            return s if s else None

        agency = row.get("agency", "")
        bureau = row.get("agency_bureau", "")
        orgpath = _orgpath_from_bureau(agency, bureau)

        return cls(
            omg_id=row.get("id", ""),
            use_case_name=row.get("use_case_name", ""),
            agency=agency,
            agency_name=row.get("agency_name", ""),
            agency_bureau=bureau,
            development_stage=_stage(row.get("development_stage", "")),
            agent_class=_agent(row.get("classification", "")),
            operational_date=_opt(row.get("operational_date", "")),
            ato_status=_ato(row.get("have_ato", "")),
            system_name_ato=_opt(row.get("system_name_ato", "")),
            vendor_name=_opt(row.get("vendor_name", "")),
            contact_email=_opt(row.get("contact_email", "")),
            has_pii=_bool(row.get("has_pii", "")),
            pia_url=_opt(row.get("pia_url", "")),
            is_high_impact=_bool(row.get("is_high_impact", "")),
            hi_testing_conducted=_opt(row.get("hi_testing_conducted", "")),
            hi_assessment_completed=_opt(row.get("hi_assessment_completed", "")),
            hi_independent_review=_opt(row.get("hi_independent_review", "")),
            hi_ongoing_monitoring=_opt(row.get("hi_ongoing_monitoring", "")),
            hi_failsafe_presence=_opt(row.get("hi_failsafe_presence", "")),
            hi_appeal_process=_opt(row.get("hi_appeal_process", "")),
            orgpath=orgpath,
        )

    @property
    def is_live(self) -> bool:
        """True for deployed and pilot systems — the governed population."""
        return self.development_stage in (DevStage.DEPLOYED, DevStage.PILOT)

    @property
    def identity_label(self) -> str:
        """Human-readable key used in drift finding names."""
        name = self.system_name_ato or self.use_case_name or self.omg_id
        agency = self.agency or "UNKNOWN-AGENCY"
        return f"{agency}::{name}"
