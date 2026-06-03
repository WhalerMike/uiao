"""Per-finding remediation extraction for Zero Trust Assessment reports.

Every check already ships its own fix guidance: the ``TestDescription`` carries a
"**Remediation action**" section (usually Microsoft Learn links / steps), and the
``TestResult`` lists the specific failing objects with deep links into the portal.
This module surfaces that faithfully — it does **not** author scripts or invent
steps — and classifies which admin console each fix lives in.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from uiao.adapters.zta.analytics import priority_bucket, priority_score, severity_score
from uiao.adapters.zta.model import ACTIONABLE_STATUSES, ZtReport, ZtTest

# Known admin consoles, matched against portal links in the finding. Order is
# priority for tie-breaks; the most-frequent matching console wins.
_CONSOLES: list[tuple[str, str, str]] = [
    ("intune.microsoft.com", "Microsoft Intune admin center", "https://intune.microsoft.com"),
    ("endpoint.microsoft.com", "Microsoft Intune admin center", "https://intune.microsoft.com"),
    ("purview.microsoft.com", "Microsoft Purview portal", "https://purview.microsoft.com"),
    ("compliance.microsoft.com", "Microsoft Purview portal", "https://purview.microsoft.com"),
    ("security.microsoft.com", "Microsoft Defender portal", "https://security.microsoft.com"),
    ("admin.exchange.microsoft.com", "Exchange admin center", "https://admin.exchange.microsoft.com"),
    ("admin.microsoft.com", "Microsoft 365 admin center", "https://admin.microsoft.com"),
    ("portal.azure.com", "Azure portal", "https://portal.azure.com"),
    ("entra.microsoft.com", "Microsoft Entra admin center", "https://entra.microsoft.com"),
]

# Fallback console when no portal link is present, keyed by Zero Trust pillar.
_PILLAR_CONSOLE: dict[str, tuple[str, str]] = {
    "Identity": ("Microsoft Entra admin center", "https://entra.microsoft.com"),
    "Devices": ("Microsoft Intune admin center", "https://intune.microsoft.com"),
    "Data": ("Microsoft Purview portal", "https://purview.microsoft.com"),
    "Network": ("Microsoft Entra admin center", "https://entra.microsoft.com"),
    "Infrastructure": ("Azure portal", "https://portal.azure.com"),
}
_DEFAULT_CONSOLE = ("Microsoft Entra admin center", "https://entra.microsoft.com")

_REMEDIATION_SPLIT = re.compile(r"\*\*\s*remediation action\s*\*\*", re.IGNORECASE)
_URL = re.compile(r"https?://[^\s)\]]+")
_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
_LEARN = "learn.microsoft.com"


def _blob(test: ZtTest) -> str:
    return f"{test.test_description}\n{test.test_result}"


def fix_surface(test: ZtTest) -> tuple[str, str]:
    """Classify the admin console where this finding is fixed: (label, entry URL)."""
    urls = [u for u in _URL.findall(_blob(test)) if _LEARN not in u]
    best: tuple[int, int, str, str] = (0, 0, "", "")
    for rank, (domain, label, entry) in enumerate(_CONSOLES):
        count = sum(1 for u in urls if domain in u)
        if count and (count, -rank) > (best[0], -best[1]):
            best = (count, rank, label, entry)
    if best[0]:
        return best[2], best[3]
    return _PILLAR_CONSOLE.get(test.test_pillar or "", _DEFAULT_CONSOLE)


def split_remediation(test: ZtTest) -> tuple[str, str]:
    """Split TestDescription into (rationale, remediation-action block)."""
    parts = _REMEDIATION_SPLIT.split(test.test_description, maxsplit=1)
    rationale = parts[0].strip()
    remediation = parts[1].strip() if len(parts) > 1 else ""
    return rationale, remediation


def learn_links(test: ZtTest) -> list[tuple[str, str]]:
    """Microsoft Learn links cited by the finding, as (title, url), deduped in order."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for title, url in _MD_LINK.findall(_blob(test)):
        if _LEARN in url and url not in seen:
            seen.add(url)
            out.append((title.strip(), url))
    return out


@dataclass(frozen=True)
class RemediationCard:
    """A single finding's remediation guidance, extracted from the report."""

    test_id: str
    title: str
    pillar: str
    risk: str
    status: str
    severity: int
    priority: float
    bucket: str
    console: str
    console_url: str
    rationale: str
    remediation: str
    learn: list[tuple[str, str]]
    affected: str


def card_for(test: ZtTest) -> RemediationCard:
    """Build the remediation card for one test."""
    console, console_url = fix_surface(test)
    rationale, remediation = split_remediation(test)
    return RemediationCard(
        test_id=test.test_id,
        title=test.test_title,
        pillar=test.pillar,
        risk=test.test_risk,
        status=test.test_status,
        severity=severity_score(test),
        priority=priority_score(test),
        bucket=priority_bucket(priority_score(test)),
        console=console,
        console_url=console_url,
        rationale=rationale,
        remediation=remediation,
        learn=learn_links(test),
        affected=test.test_result.strip(),
    )


def build_cards(
    report: ZtReport,
    *,
    statuses: tuple[str, ...] = ("Failed",),
) -> list[RemediationCard]:
    """Build remediation cards for tests in ``statuses`` (default: Failed only).

    Sorted by pillar, then severity desc, then test id — stable and grouped.
    """
    wanted = set(statuses)
    cards = [card_for(t) for t in report.tests if t.test_status in wanted]
    cards.sort(key=lambda c: (c.pillar, -c.severity, c.test_id))
    return cards


# Convenience: the statuses that are actionable findings.
ACTIONABLE = tuple(sorted(ACTIONABLE_STATUSES))
