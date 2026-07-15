from __future__ import annotations

import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _compiled_patterns() -> list[re.Pattern[str]]:
    patterns: list[re.Pattern[str]] = []
    for line in (REPO_ROOT / ".lycheeignore").read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(re.compile(stripped))
    return patterns


def test_lycheeignore_suppresses_known_ci_flaky_urls() -> None:
    urls = [
        "https://developers.login.gov/",
        "https://docs.snowflake.com/en/user-guide/security-mfa-rollout",
        "https://docs.aws.amazon.com/inspector/latest/user/what-is-inspector.html",
        "https://peps.python.org/pep-0420/",
    ]

    patterns = _compiled_patterns()

    for url in urls:
        assert any(pattern.search(url) for pattern in patterns), url
