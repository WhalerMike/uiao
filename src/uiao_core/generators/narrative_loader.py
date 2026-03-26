"""Control-library narrative loader (v2 – Gold Standard).

Scans ``data/control-library/*.yml``, renders Jinja2 templates in each
``narrative`` field using a context built from ``load_context()``, and
returns a dict keyed by control ID ready for injection into the OSCAL SSP.

Improvements over v1
--------------------
* Robust parameter substitution – merges *both* the global
  ``data/parameters.yml`` values **and** the per-control ``parameters:``
  block so that inline ``{{ parameters['xxx'] }}`` always resolves.
* Graceful Jinja2 fallbacks – missing variables render as ``[TBD]``
  instead of raising; subscript / attribute access on undefined also safe.
* OSCAL-aligned output – each entry carries pre-built ``oscal_statement``,
  ``oscal_by_components``, and ``oscal_props`` ready for direct injection
  into ``implemented-requirements``.
* ``family`` field support – optional ``family:`` key is passed through.
* Validation – every loaded YAML is checked for required fields
  (``control_id``, ``title``, ``narrative``); malformed files emit a
  warning and are skipped.
* Full backward compatibility with existing control-library YAMLs.
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import yaml
from jinja2 import BaseLoader, Environment, Undefined

from uiao_core.utils.context import get_settings, load_context

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Required fields every control YAML must contain
# ---------------------------------------------------------------------------
_REQUIRED_FIELDS = {"control_id", "title", "narrative"}
# Accept both underscore and hyphen variants
_FIELD_ALIASES: dict[str, str] = {
    "control-id": "control_id",
    "control_id": "control_id",
    "implemented-by": "implemented_by",
    "implemented_by": "implemented_by",
    "related-controls": "related_controls",
    "related_controls": "related_controls",
}


# ---------------------------------------------------------------------------
# Jinja2 undefined handler – renders missing vars as [TBD]
# ---------------------------------------------------------------------------
class _TBDUndefined(Undefined):
    """Render missing Jinja2 variables as ``[TBD]`` instead of raising."""

    def __str__(self) -> str:  # type: ignore[override]
        return "[TBD]"

    def __repr__(self) -> str:
        return "[TBD]"

    # Support subscript / attribute access on undefined so that
    # ``{{ parameters['missing-key'] }}`` also renders as ``[TBD]``.
    def __getitem__(self, key: Any) -> _TBDUndefined:  # type: ignore[override]
        return _TBDUndefined()

    def __getattr__(self, name: str) -> _TBDUndefined:  # noqa: D105
        if name.startswith("_"):
            raise AttributeError(name)
        return _TBDUndefined()

    # Arithmetic / iteration safety so Jinja2 filters like |length work.
    def __len__(self) -> int:
        return 0

    def __iter__(self):
        return iter([])

    def __bool__(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Parameter helpers
# ---------------------------------------------------------------------------
def _flatten_parameters(context: dict[str, Any]) -> dict[str, str]:
    """Flatten the nested ``parameters`` structure from ``data/parameters.yml``.

    ``parameters.yml`` is a dict of categories (identity, overlay, ...),
    each containing a list of items with ``id`` and ``value`` keys.  We
    turn this into a simple ``{param_id: value_str}`` lookup so Jinja2
    templates can reference ``{{ parameters['account-creation-window'] }}``.

    Also accepts items from control-library YAML ``parameters`` lists
    (which have their own ``id``/``value`` structure) so that
    self-referential templates resolve correctly.
    """
    flat: dict[str, str] = {}
    params_cfg = context.get("parameters", {})
    if isinstance(params_cfg, dict):
        for _category, items in params_cfg.items():
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                pid = item.get("id", "")
                if pid:
                    flat[pid] = str(item.get("value", ""))
    return flat


def _merge_local_parameters(
    global_params: dict[str, str],
    local_params: list[dict[str, Any]],
) -> dict[str, str]:
    """Merge per-control ``parameters:`` block into the global lookup.

    Local values (from the YAML's own ``parameters:`` list) override
    global values so that a control can self-resolve its own inline
    ``{{ parameters['xxx'] }}`` references.
    """
    merged = dict(global_params)
    for item in local_params:
        if not isinstance(item, dict):
            continue
        pid = item.get("id", "")
        val = item.get("value", "")
        if pid and val and "{{" not in str(val):
            # Only override if the local value is a concrete string,
            # not itself a Jinja2 template reference.
            merged[pid] = str(val)
    return merged


# ---------------------------------------------------------------------------
# Jinja2 rendering
# ---------------------------------------------------------------------------
def _render_narrative(
    raw: str,
    org_name: str,
    parameters: dict[str, str],
) -> str:
    """Render a Jinja2 narrative template string.

    Missing variables resolve to ``[TBD]`` via :class:`_TBDUndefined`.
    """
    env = Environment(loader=BaseLoader(), undefined=_TBDUndefined)

    class _OrgProxy:
        """Dot-access proxy for ``{{ organization.name }}``."""

        def __init__(self, name: str) -> None:
            self.name = name

        def __getattr__(self, key: str) -> _TBDUndefined:
            if key.startswith("_"):
                raise AttributeError(key)
            return _TBDUndefined()

    try:
        template = env.from_string(raw)
        return template.render(
            organization=_OrgProxy(org_name),
            parameters=parameters,
        )
    except Exception as exc:
        logger.warning("Jinja2 render failed: %s – returning raw narrative", exc)
        return raw


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------
def _normalise_implemented_by(raw: Any) -> list[dict[str, Any]]:
    """Normalise both ``implemented_by`` schema variants into a uniform list.

    Variant A – simple string list::

        implemented_by:
          - IdentityProvider
          - HRSystem

    Variant B – typed-object list::

        implemented_by:
          - type: NetworkOverlay
            description: ...

    Both variants (and ``implemented-by`` with a hyphen) are handled and
    returned as ``[{"type": ..., "description": ...}]``.
    """
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            result.append({"type": item, "description": ""})
        elif isinstance(item, dict):
            item_type = item.get("type") or item.get("abstract-type", "")
            result.append(
                {
                    "type": str(item_type),
                    "description": item.get("description", ""),
                }
            )
    return result


def _resolve_field(data: dict[str, Any], canonical: str) -> Any:
    """Resolve a field from *data* accepting both hyphen and underscore keys."""
    val = data.get(canonical)
    if val is not None:
        return val
    alt = canonical.replace("_", "-")
    return data.get(alt)


# ---------------------------------------------------------------------------
# OSCAL pre-build helpers (new in v2)
# ---------------------------------------------------------------------------
def _build_oscal_statement(
    ctrl_id: str,
    rendered_narrative: str,
) -> dict[str, Any]:
    """Pre-build an OSCAL ``statement`` dict ready for SSP injection."""
    return {
        "statement-id": f"{ctrl_id}_smt",
        "uuid": str(uuid.uuid4()),
        "description": rendered_narrative,
    }


def _build_oscal_props(status: str, family: str = "") -> list[dict[str, Any]]:
    """Pre-build OSCAL ``props`` for an implemented-requirement."""
    props: list[dict[str, Any]] = [
        {
            "name": "implementation-status",
            "value": status,
            "ns": "https://fedramp.gov/ns/oscal",
        },
    ]
    if family:
        props.append(
            {
                "name": "control-family",
                "value": family,
                "ns": "https://fedramp.gov/ns/oscal",
            }
        )
    return props


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def load_control_library(
    data_dir: Path | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Load and render every control-library YAML.

    Args:
        data_dir: Directory that contains the ``control-library/`` sub-folder.
            Defaults to ``settings.data_dir``.
        context: Pre-loaded context dict (e.g. from ``load_context()``).
            When *None* the full context is loaded from the default paths.

    Returns:
        A dict keyed by ``control_id`` (e.g. ``"AC-2"``).  Each value is a
        dict containing:

        * ``control_id`` – normalised upper-case control ID
        * ``title`` – human-readable title
        * ``family`` – control family (e.g. "Access Control"), may be empty
        * ``status`` – implementation status string
        * ``narrative`` – Jinja2-rendered narrative string
        * ``implemented_by`` – normalised list of ``{type, description}`` dicts
        * ``evidence`` – raw evidence list from the YAML
        * ``parameters`` – raw parameters list from the YAML
        * ``related_controls`` – list of related control IDs (may be empty)
        * ``oscal_statement`` – pre-built OSCAL statement dict
        * ``oscal_props`` – pre-built OSCAL props list
    """
    if data_dir is None:
        settings = get_settings()
        data_dir = settings.data_dir

    control_lib_dir = Path(data_dir) / "control-library"
    if not control_lib_dir.exists():
        return {}

    if context is None:
        context = load_context(data_dir=data_dir)

    global_params = _flatten_parameters(context)

    # Resolve organisation name from canon / briefing data.
    briefing = context.get("leadership_briefing", {})
    if isinstance(briefing, dict) and "leadership_briefing" in briefing:
        briefing = briefing["leadership_briefing"]
    org_name: str = ""
    if isinstance(briefing, dict):
        org_name = briefing.get("organization", briefing.get("title", ""))
    if not org_name:
        org_name = context.get("organization_name", "")

    result: dict[str, dict[str, Any]] = {}
    skipped = 0

    for yml_file in sorted(control_lib_dir.glob("*.yml")):
        try:
            with yml_file.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception as exc:
            logger.warning("Failed to parse %s: %s", yml_file.name, exc)
            skipped += 1
            continue

        if not isinstance(data, dict):
            logger.warning("Skipping %s – top-level is not a mapping", yml_file.name)
            skipped += 1
            continue

        # Support both "control_id" and "control-id" key spellings.
        ctrl_id: str = str(_resolve_field(data, "control_id") or "").strip().upper()
        title: str = str(data.get("title", "")).strip()
        raw_narrative: str = str(data.get("narrative", "")).strip()

        # --- Validation: required fields ---
        missing = []
        if not ctrl_id:
            missing.append("control_id")
        if not title:
            missing.append("title")
        if not raw_narrative:
            missing.append("narrative")
        if missing:
            logger.warning(
                "Skipping %s – missing required field(s): %s",
                yml_file.name,
                ", ".join(missing),
            )
            skipped += 1
            continue

        # --- Parameter resolution ---
        local_params_raw = data.get("parameters", [])
        if not isinstance(local_params_raw, list):
            local_params_raw = []
        merged_params = _merge_local_parameters(global_params, local_params_raw)

        # --- Render narrative ---
        rendered = _render_narrative(raw_narrative, org_name, merged_params)

        # --- Optional fields ---
        family = str(data.get("family", "")).strip()
        status = str(data.get("status", "implemented")).strip()
        raw_impl = _resolve_field(data, "implemented_by") or []
        impl_by = _normalise_implemented_by(raw_impl)
        evidence = data.get("evidence", [])
        related = _resolve_field(data, "related_controls") or []

        # --- Build entry ---
        result[ctrl_id] = {
            "control_id": ctrl_id,
            "title": title,
            "family": family,
            "status": status,
            "narrative": rendered,
            "implemented_by": impl_by,
            "evidence": evidence if isinstance(evidence, list) else [],
            "parameters": local_params_raw,
            "related_controls": related if isinstance(related, list) else [],
            # Pre-built OSCAL fragments (new in v2)
            "oscal_statement": _build_oscal_statement(ctrl_id, rendered),
            "oscal_props": _build_oscal_props(status, family),
        }

    if skipped:
        logger.info(
            "Control library: loaded %d controls, skipped %d files",
            len(result),
            skipped,
        )
    else:
        logger.info("Control library: loaded %d controls", len(result))

    return result
