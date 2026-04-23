"""RFC-0026 Pathway-1 migration readiness check (enhancement E8).

Compares today's date against FedRAMP Notice 0009 mandatory adoption
dates for the VDR and CCM Balance Improvement Releases, cross-references
each adapter's current `status` in
`src/uiao/canon/adapter-registry.yaml`, and flags any pathway whose
status is still `reserved` within the configured lead window.

Design goals:
    * Pure stdlib + PyYAML. Intentionally self-contained so it can run
      on the `conmon-aggregate.yml` runner with only `pip install
      --quiet pyyaml`.
    * The source of truth for mandatory dates is the adapter stub
      module (`uiao.adapters.vdr_adapter`, `uiao.adapters.ccm_bir_adapter`),
      *not* the registry free-text. The registry `notes` block carries
      the same dates for human readers; schema constraint
      (`additionalProperties: false`) prevents a structured top-level
      field today. ADR-043 §change-log 0.2 documents this.
    * Outputs a JSON summary to stdout or to `--output`. Exit code is 0
      unless `--fail-on-breach` is passed AND at least one pathway is
      inside its lead window while still reserved.

Usage:
    python scripts/conmon/migration_readiness.py \\
        --registry src/uiao/canon/adapter-registry.yaml \\
        --output exports/conmon/migration-readiness.json \\
        [--now 2027-02-01T00:00:00Z]       # optional override
        [--fail-on-breach]                  # exit 1 on active breach

Roadmap: docs/docs/uiao-rfc-0026-roadmap.md § E8.
"""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import pathlib
import sys
from typing import Any, Dict, Iterable, List, Optional

import yaml

# The two adapter stubs that own their own MANDATORY_ADOPTION_DATE +
# READINESS_LEAD_DAYS constants. If a future Pathway-1 adapter is
# added, extend this list rather than duplicating dates into this
# script.
_PATHWAY_1_STUB_SPECS = (
    {
        "adapter_id": "vdr-bir",
        "module_path": "uiao.adapters.vdr_adapter",
        "requirement": "RV5-CA07-VLN",
        "notice_0009_ref": "VDR BIR adoption",
    },
    {
        "adapter_id": "ccm-bir",
        "module_path": "uiao.adapters.ccm_bir_adapter",
        "requirement": "RV5-CA07-CCM",
        "notice_0009_ref": "CCM BIR adoption",
    },
)


@dataclasses.dataclass
class PathwayReadiness:
    adapter_id: str
    requirement: str
    notice_0009_ref: str
    mandatory_by: str
    lead_days: int
    registry_status: Optional[str]
    breach: bool
    breach_window_opened_at: Optional[str]
    days_until_mandatory: Optional[int]
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return dataclasses.asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_iso_date(s: str) -> dt.date:
    """Accept 'YYYY-MM-DD' or a full ISO-8601 timestamp; return a date."""
    s = s.strip()
    if "T" in s:
        # Python 3.11+ accepts trailing Z; older runners need replace
        s_clean = s.replace("Z", "+00:00")
        return dt.datetime.fromisoformat(s_clean).date()
    return dt.date.fromisoformat(s)


def _load_registry(path: pathlib.Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict) or "adapters" not in data:
        raise ValueError(f"Registry {path} does not look like an adapter-registry document (missing 'adapters' key).")
    return data


def _registry_status_for(registry: Dict[str, Any], adapter_id: str) -> Optional[str]:
    for entry in registry.get("adapters", []):
        if isinstance(entry, dict) and entry.get("id") == adapter_id:
            status = entry.get("status")
            return str(status) if status is not None else None
    return None


def _load_stub_constants(module_path: str) -> Dict[str, Any]:
    """Import a Pathway-1 adapter stub and extract its readiness constants.

    The constants live on the module, not in the registry, because the
    adapter-registry schema is strict (additionalProperties: false).
    """
    import importlib

    mod = importlib.import_module(module_path)
    try:
        mandatory_by = str(mod.MANDATORY_ADOPTION_DATE)
        lead_days = int(mod.READINESS_LEAD_DAYS)
        adapter_id = str(mod.ADAPTER_ID)
    except AttributeError as exc:
        raise ValueError(
            f"Stub module {module_path} is missing a required readiness "
            f"constant (MANDATORY_ADOPTION_DATE, READINESS_LEAD_DAYS, "
            f"ADAPTER_ID)."
        ) from exc
    return {
        "adapter_id": adapter_id,
        "mandatory_by": mandatory_by,
        "lead_days": lead_days,
    }


# ---------------------------------------------------------------------------
# Core evaluator
# ---------------------------------------------------------------------------


def evaluate_pathway_readiness(
    registry: Dict[str, Any],
    *,
    now: dt.date,
    stub_specs: Iterable[Dict[str, Any]] = _PATHWAY_1_STUB_SPECS,
) -> List[PathwayReadiness]:
    """Evaluate each Pathway-1 stub against the registry + a reference date.

    Returns one :class:`PathwayReadiness` per stub. A ``breach=True``
    result means: today is inside the lead window AND the registry
    still shows ``status: reserved``. Anything outside the lead window
    is reported with ``breach=False`` regardless of status so callers
    can build a calendar view without filtering.
    """
    results: List[PathwayReadiness] = []

    for spec in stub_specs:
        stub = _load_stub_constants(spec["module_path"])
        adapter_id = spec["adapter_id"]
        if stub["adapter_id"] != adapter_id:
            raise ValueError(
                f"Stub module {spec['module_path']} declares ADAPTER_ID="
                f"{stub['adapter_id']!r} but spec expects {adapter_id!r}; "
                "keep the two in sync."
            )

        mandatory = _parse_iso_date(stub["mandatory_by"])
        lead_days = stub["lead_days"]
        window_opens = mandatory - dt.timedelta(days=lead_days)
        days_until = (mandatory - now).days
        registry_status = _registry_status_for(registry, adapter_id)

        inside_window = now >= window_opens
        is_reserved = registry_status == "reserved"
        breach = inside_window and is_reserved

        if breach:
            reason = (
                f"Inside {lead_days}-day lead window for {spec['notice_0009_ref']} "
                f"({mandatory.isoformat()}): registry still reports status="
                f"{registry_status!r}. Migration must start."
            )
        elif inside_window and registry_status is None:
            reason = (
                f"Inside lead window and adapter {adapter_id!r} is not in the "
                f"registry at all. Either register it or remove the stub."
            )
            breach = True
        elif inside_window:
            reason = f"Inside lead window; registry status={registry_status!r} is progressing — no action required."
        else:
            reason = f"Outside {lead_days}-day lead window (opens {window_opens.isoformat()}); monitoring only."

        results.append(
            PathwayReadiness(
                adapter_id=adapter_id,
                requirement=spec["requirement"],
                notice_0009_ref=spec["notice_0009_ref"],
                mandatory_by=mandatory.isoformat(),
                lead_days=lead_days,
                registry_status=registry_status,
                breach=breach,
                breach_window_opened_at=window_opens.isoformat() if inside_window else None,
                days_until_mandatory=days_until,
                reason=reason,
            )
        )

    return results


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_output(results: List[PathwayReadiness], *, now: dt.date) -> Dict[str, Any]:
    return {
        "evaluated_at": now.isoformat(),
        "any_breach": any(r.breach for r in results),
        "pathways": [r.to_dict() for r in results],
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="RFC-0026 Pathway-1 migration readiness check (E8)")
    parser.add_argument(
        "--registry",
        type=pathlib.Path,
        default=pathlib.Path("src/uiao/canon/adapter-registry.yaml"),
        help="Path to adapter-registry.yaml",
    )
    parser.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Write JSON result here instead of stdout.",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="Override the reference date (ISO-8601). Defaults to UTC today.",
    )
    parser.add_argument(
        "--fail-on-breach",
        action="store_true",
        help="Exit 1 if any pathway is inside its lead window while reserved.",
    )
    args = parser.parse_args(argv)

    now = _parse_iso_date(args.now) if args.now else dt.datetime.now(dt.timezone.utc).date()

    try:
        registry = _load_registry(args.registry)
    except (OSError, yaml.YAMLError, ValueError) as exc:
        print(f"::error::Could not read registry {args.registry}: {exc}", file=sys.stderr)
        return 2

    results = evaluate_pathway_readiness(registry, now=now)
    payload = _build_output(results, now=now)
    rendered = json.dumps(payload, indent=2, sort_keys=True)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)

    if args.fail_on_breach and payload["any_breach"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
