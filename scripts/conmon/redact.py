"""Scan-finding redaction pipeline stage — RFC-0026 E7 / ADR-045.

Consumes normalized scan findings (dicts) and the UIAO redaction
profile (``src/uiao/canon/redaction-profile.yaml``), and produces
Tier-2 agency-distribution records with the profile's deny fields
stripped, the remediation summary truncated, and a ``tier_1_ref``
sha256 that links the redacted record back to its unredacted source.

Design:
    * Pure stdlib + PyYAML — runs on the lean conmon-aggregate runner
      that already installs pyyaml.
    * Deny-by-default: only fields in the profile's ``retain_fields``
      survive into Tier-2 output. The explicit ``strip_fields`` list
      is documentation for human readers; redaction relies on the
      allow list as the authoritative gate.
    * The ``tier_1_ref`` sha256 is computed over the *original* finding
      with ``json.dumps(..., sort_keys=True, separators=(",", ":"))``
      so the hash is deterministic and canonical.
    * Never mutates the input. Callers can re-use the same finding
      dict for Tier-1 storage.

Usage (programmatic)::

    from scripts.conmon.redact import load_profile, redact_finding

    profile = load_profile()
    t2_finding = redact_finding(raw_finding, profile)

Usage (CLI)::

    python scripts/conmon/redact.py \\
        --input  evidence/raw/vuln-scan/2027-01/findings.json \\
        --output evidence/distribution/tier2-findings.json

ADR reference: src/uiao/canon/adr/adr-045-scan-redaction-policy.md
Roadmap: docs/docs/uiao-rfc-0026-roadmap.md § E7
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from typing import Any, Dict, Iterable, List, Optional

import yaml

# Repo root (scripts/conmon/redact.py → parents[2]).
_DEFAULT_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_DEFAULT_PROFILE_PATH = "src/uiao/canon/redaction-profile.yaml"


def _canonical_hash(payload: Dict[str, Any]) -> str:
    """Deterministic sha256 over a dict; canonicalization pinned by ADR-045."""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_profile(
    profile_path: Optional[str] = None,
    *,
    repo_root: Optional[pathlib.Path] = None,
) -> Dict[str, Any]:
    """Load the redaction profile from canon.

    Defaults to ``src/uiao/canon/redaction-profile.yaml`` relative to
    the repo root. The profile is the *control*; callers should not
    pass a different path in production — the override exists for
    tests that exercise profile-variation behavior.
    """
    root = repo_root if repo_root is not None else _DEFAULT_REPO_ROOT
    rel_path = profile_path or _DEFAULT_PROFILE_PATH
    abs_path = (root / rel_path).resolve()
    if not abs_path.is_file():
        raise FileNotFoundError(
            f"Redaction profile not found at {abs_path}. Check the canon "
            "artifact src/uiao/canon/redaction-profile.yaml — this file "
            "is mandatory per ADR-045 D6 and its absence is a canon "
            "violation, not a configuration issue."
        )
    data = yaml.safe_load(abs_path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Redaction profile {abs_path} does not parse as a YAML mapping.")
    return data


def _truncate_summary(summary: Any, max_chars: int, suffix: str) -> str:
    """Truncate the remediation summary at max_chars, appending suffix."""
    if summary is None:
        return ""
    text = str(summary)
    if len(text) <= max_chars:
        return text
    # Leave room for the suffix within the nominal length.
    budget = max(1, max_chars - len(suffix))
    return text[:budget] + suffix


def redact_finding(
    finding: Dict[str, Any],
    profile: Dict[str, Any],
) -> Dict[str, Any]:
    """Apply the redaction profile to a single finding.

    Returns a new dict. The input is never mutated.

    The returned dict carries *only* the fields in the profile's
    ``retain_fields`` list, plus the auto-added ``tier_1_ref``. Any
    field named in ``retain_fields`` but absent from the input is
    silently skipped (rather than emitted as ``None``); this keeps
    Tier-2 output free of empty fields that could confuse downstream
    CSV generators.

    The ``remediation_summary`` field (if retained) is truncated at
    ``remediation_summary_max_chars`` and given the profile's
    truncation suffix.
    """
    retain = profile.get("retain_fields") or []
    if not isinstance(retain, list):
        raise ValueError("profile.retain_fields must be a list of field names")
    retain_set = set(retain)

    # Cache the profile knobs; bail loudly if the profile is
    # structurally broken (this is an ADR-045 D6 integrity check).
    max_chars = int(profile.get("remediation_summary_max_chars", 280))
    suffix = str(profile.get("remediation_summary_truncation_suffix", "… [truncated]"))
    tier1_ref_name = profile.get("tier_1_reference", {}).get("field_name", "tier_1_ref")

    # sha256 over the full unredacted finding — canonicalized.
    tier1_sha = _canonical_hash(finding)

    redacted: Dict[str, Any] = {}
    for field in retain:
        if field == tier1_ref_name:
            # The tier_1_ref field is auto-added below; skip if a
            # caller inadvertently placed it in the input.
            continue
        if field not in finding:
            continue
        value = finding[field]
        if field == "remediation_summary":
            value = _truncate_summary(value, max_chars, suffix)
        redacted[field] = value

    # Attach the sha256 back-reference (ADR-045 D1).
    redacted[tier1_ref_name] = tier1_sha

    # Sanity check: ensure no strip-field accidentally survived via
    # the caller naming it in retain_fields.
    strip_fields = profile.get("strip_fields") or []
    leaked = retain_set & set(strip_fields)
    if leaked:
        raise ValueError(
            f"Redaction profile names {sorted(leaked)} in both retain_fields "
            "and strip_fields. The profile is inconsistent; refuse to "
            "redact until this is fixed (ADR-045 D6)."
        )

    return redacted


def redact_findings(
    findings: Iterable[Dict[str, Any]],
    profile: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Apply :func:`redact_finding` to an iterable of findings."""
    return [redact_finding(f, profile) for f in findings]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scan-finding redaction pipeline stage (ADR-045)")
    parser.add_argument(
        "--input",
        type=pathlib.Path,
        required=True,
        help="Path to a JSON file containing a list of normalized findings.",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        required=True,
        help="Path to write the redacted (Tier-2) findings JSON.",
    )
    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help=(
            "Override the redaction profile path (defaults to canon at "
            "src/uiao/canon/redaction-profile.yaml). Tests only; production "
            "should never override."
        ),
    )
    args = parser.parse_args(argv)

    try:
        profile = load_profile(args.profile)
    except (FileNotFoundError, ValueError) as exc:
        print(f"::error::Failed to load redaction profile: {exc}", file=sys.stderr)
        return 2

    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"::error::Could not read input findings: {exc}", file=sys.stderr)
        return 2

    if not isinstance(raw, list):
        print("::error::Input JSON must be a top-level list of findings.", file=sys.stderr)
        return 2

    redacted = redact_findings(raw, profile)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"Redacted {len(redacted)} findings → {args.output} "
        f"(profile version {profile.get('profile-version', 'unknown')})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
