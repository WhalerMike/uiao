"""uiao.adapters.zta — Microsoft Zero Trust Assessment ingestion adapter.

Incorporates the output of Microsoft's open-source Zero Trust Assessment
(``github.com/microsoft/zerotrustassessment``) into UIAO as governed evidence,
following the ScubaGear pattern (UIAO_002 / UIAO_005) under the ADR-092 Active
Governance provider-incorporation contract.

UIAO does **not** re-implement the checks and does **not** auto-remediate. This
adapter consumes a ``ZeroTrustAssessmentReport`` (``.json`` export, or the
``.html`` report which embeds the same data as ``reportData = {…}``), recomputes
all roll-ups from ``Tests[]`` (the report's own ``TestResultSummary`` block is
unreliable), derives a boundary-applicability signal from existing fields, and
renders human-facing digests.

Public surface::

    from uiao.adapters.zta import load_report, build_triage
    report = load_report(Path("ZeroTrustAssessmentReport.html"))
    triage = build_triage(report)
"""

from __future__ import annotations

from uiao.adapters.zta.ingest import load_report
from uiao.adapters.zta.model import ZtReport, ZtTest
from uiao.adapters.zta.triage import Triage, build_triage

__all__ = ["ZtReport", "ZtTest", "Triage", "build_triage", "load_report"]
