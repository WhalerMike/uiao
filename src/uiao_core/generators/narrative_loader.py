"""Control-library narrative loader.

Scans ``data/control-library/*.yml``, renders Jinja2 templates in each
``narrative`` field using a context built from ``load_context()``, and
returns a dict keyed by control ID ready for injection into the OSCAL SSP.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from jinja2 import BaseLoader, Environment, Undefined

from uiao_core.utils.context import get_settings, load_context


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


def _flatten_parameters(context: dict[str, Any]) -> dict[str, str]:
    """Flatten the nested ``parameters`` structure from ``data/parameters.yml``.

    ``parameters.yml`` is a dict of categories (identity, overlay, …), each
    containing a list of items with ``id`` and ``value`` keys.  We turn this
    into a simple ``{param_id: value_str}`` lookup so Jinja2 templates can
    reference ``{{ parameters['account-creation-window'] }}``.

    Also accepts items from control-library YAML ``parameters`` lists (which
    have their own ``id``/``value`` structure) so that self-referential
    templates resolve correctly.
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


def _render_narrative(raw: str, org_name: str, parameters: dict[str, str]) -> str:
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
    except Exception:
        return raw


def _normalise_implemented_by(raw: Any) -> list[dict[str, Any]]:
    """Normalise both ``implemented_by`` schema variants into a uniform list.

    Variant A – simple string list::

        implemented_by:
          - IdentityProvider
          - HRSystem

    Variant B – typed-object list::

        implemented_by:
          - type: NetworkOverlay
            description: …

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
            # Support both "type" and "abstract-type" keys (schema variants)
            item_type = item.get("type") or item.get("abstract-type", "")
            result.append({"type": str(item_type), "description": item.get("description", "")})
    return result


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
        * ``status`` – implementation status string
        * ``narrative`` – Jinja2-rendered narrative string
        * ``implemented_by`` – normalised list of ``{type, description}`` dicts
        * ``evidence`` – raw evidence list from the YAML
        * ``parameters`` – raw parameters list from the YAML
        * ``related_controls`` – list of related control IDs (may be empty)
    """
    if data_dir is None:
        settings = get_settings()
        data_dir = settings.data_dir

    control_lib_dir = Path(data_dir) / "control-library"
    if not control_lib_dir.exists():
        return {}

    if context is None:
        context = load_context(data_dir=data_dir)

    flat_params = _flatten_parameters(context)

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

    for yml_file in sorted(control_lib_dir.glob("*.yml")):
        try:
            with yml_file.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
        except Exception:
            continue

        if not isinstance(data, dict):
            continue

        # Support both "control_id" and "control-id" key spellings.
        ctrl_id: str = str(data.get("control_id") or data.get("control-id", "")).strip().upper()
        if not ctrl_id:
            continue

        raw_narrative: str = str(data.get("narrative", ""))
        rendered = _render_narrative(raw_narrative, org_name, flat_params)

        # Support both "implemented_by" and "implemented-by" spellings.
        raw_impl = data.get("implemented_by") or data.get("implemented-by") or []

        result[ctrl_id] = {
            "control_id": ctrl_id,
            "title": str(data.get("title", "")),
            "status": str(data.get("status", "implemented")),
            "narrative": rendered,
            "implemented_by": _normalise_implemented_by(raw_impl),
            "evidence": data.get("evidence", []),
            "parameters": data.get("parameters", []),
            "related_controls": data.get("related_controls", []),
        }

    return result
