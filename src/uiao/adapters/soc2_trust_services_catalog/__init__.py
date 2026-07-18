"""SOC 2 Trust Services Criteria — Conformance Adapter (non-federal vertical).

This adapter pack is the second vertical on the UIAO substrate, and it exists
to make [ADR-085](../../canon/adr/adr-085-universal-enterprise-positioning.md)
concrete rather than aspirational: the **same** surface slots that carry the
federal FedRAMP / KSI evidence bindings (``fedramp_aan_catalog``) also carry a
commercial-regulated regime — SOC 2 Type II **Trust Services Criteria (TSC)** —
with **no change to the substrate, the canon, or the slot definitions**. Federal
is one vertical adapter pack; this is a second. Nothing here is federal-specific,
which is the whole point.

What this proves
----------------
The surface slots in ``src/uiao/canon/data/control-planes.yml`` (identity,
addressing, network, telemetry, endpoint, security) are regime-agnostic
evidence anchors. A federal reviewer reads slot 1 as ``IA-2 / AC-2`` (NIST) and
``KSI-IAM`` (FedRAMP 20x); a SOC 2 auditor reads the *same slot 1* as
``CC6.1–CC6.3`` (logical access). The substrate does not know or care which
framework is consuming its evidence — the vertical adapter pack supplies the
crosswalk.

Scope (honest)
--------------
This pack binds the **technical** Common Criteria that map to the substrate's
technical control planes:

  1  identity    CC6.1–CC6.3   logical access: identification, authn, RBAC
  2  addressing  CC6.1, CC7.1  system boundary + asset inventory
  3  network     CC6.6–CC6.7   boundary protection + transmission encryption
  4  telemetry   CC7.1–CC7.3   config-change detection, monitoring, event eval
  5  endpoint    CC6.8, CC7.1  unauthorized-software prevention, config baseline
  6  security    CC7.4, CC8.1  incident response + change management

SOC 2's governance / entity-level criteria (CC1 control environment, CC2
communication, CC3 risk assessment, CC4 monitoring, CC5 control activities, CC9
risk mitigation) are **process** controls that do not bind to a technical
surface slot; they are deliberately out of scope for this adapter, and each
mapping file states so. A real SOC 2 engagement layers those process controls on
top — they are not a substrate concern.

STATUS
------
``active`` — registered in ``adapter-registry.yaml`` and ADR-backed
(ADR-129, ACCEPTED). The two ADR-129 D3 conditions for promotion are met: an
operational conformance gate exists (``emit_evidence_bindings`` renders the
pack's declared ``soc2-evidence-bindings.json`` output, exercised by the
conformance suite that runs in the adapter-conformance CI gate), and ADR-129 is
ratified. "Active" here matches the federal pack's usage — operational and
CI-covered — not "has a paying customer"; a real SOC 2 engagement would deepen
the bindings' confidence, not change this status.

Registry admission (ADR-129 resolved the finding)
-------------------------------------------------
This pack surfaced a concrete obstruction when first authored: the registry
schema (``adapter-registry.schema.json``) makes ``gcc-boundary`` a *required*
field whose enum was federal-only (``gcc-moderate`` plus three named
commercial-product exceptions), with no value for a genuinely non-federal
vertical. The substrate was vertical-agnostic, but the *registry schema carried
residual federal coupling*. ADR-129 resolved it in lockstep with the schema
change ADR-085 D3 anticipated: it added ``commercial-general`` (the boundary for
non-federal, regime-scoped packs) and registered this pack. A *second* coupling
remains noted, not yet fixed: the registry's
``controls`` field is NIST-patterned and cannot hold SOC 2 Trust Services
Criteria, so the registry entry omits it and the criteria live in
``mappings/slot-0N-*.yaml``; the field's vertical-neutral redesign travels with
the deferred ``verticals-registry.yaml`` work.

References
----------
    Substrate (this adapter depends on these; none are federal-specific):
      - src/uiao/canon/data/control-planes.yml (the shared surface slots)
      - src/uiao/canon/adr/adr-085-universal-enterprise-positioning.md
    Companion vertical (same slots, different regime):
      - src/uiao/adapters/fedramp_aan_catalog/ (the federal vertical)
    External standard (mapped, not vendored):
      - AICPA Trust Services Criteria (2017, rev. 2022) — CC-series
"""

from __future__ import annotations

from pathlib import Path
from typing import cast

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

ADAPTER_ID: str = "soc2-trust-services-catalog"
STATUS: str = "active"
VERTICAL: str = "commercial-regulated"
STANDARD: str = "AICPA SOC 2 Type II — Trust Services Criteria (2017/2022)"
SURFACE_SLOTS_BOUND: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
# The registry's declared output (adapter-registry.yaml → outputs:).
EVIDENCE_BINDINGS_OUTPUT: str = "soc2-evidence-bindings.json"

_MAPPINGS_DIR = Path(__file__).with_name("mappings")


def mappings_dir() -> Path:
    """Directory holding the slot-0N-*.yaml evidence-binding files."""
    return _MAPPINGS_DIR


def mapping_files() -> list[Path]:
    """Every committed slot mapping file, sorted by slot number."""
    return sorted(_MAPPINGS_DIR.glob("slot-*.yaml"))


def load_slot_mapping(slot_id: int) -> dict:
    """Load and parse the mapping file for a given surface slot id (1-6)."""
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML required to load SOC 2 slot mappings")
    matches = sorted(_MAPPINGS_DIR.glob(f"slot-{slot_id:02d}-*.yaml"))
    if not matches:
        raise KeyError(f"no SOC 2 mapping file for surface slot {slot_id}")
    return cast(dict, yaml.safe_load(matches[0].read_text(encoding="utf-8")))


def emit_evidence_bindings() -> dict:
    """Render the adapter's declared output: the consolidated SOC 2 evidence-bindings.

    This is the pack's operational surface (ADR-129 D3): it deterministically
    consolidates the six per-slot mapping files into the single
    ``soc2-evidence-bindings.json`` structure the registry declares as this
    adapter's output, mirroring how the federal pack renders its evidence
    bindings. It is side-effect free — it returns the structure; the caller
    (a CI job, a report step) decides where to write it.

    Each slot contributes its TSC anchor, substrate source, and per-criterion
    bindings; the top level carries the sorted union of Trust Services Criteria
    the pack covers, so a consumer can answer "which criteria does this vertical
    bind, and to what substrate evidence?" without re-reading six files.
    """
    slots: list[dict] = []
    criteria: set[str] = set()
    for slot_id in SURFACE_SLOTS_BOUND:
        m = load_slot_mapping(slot_id)
        bindings = m.get("bindings", [])
        for b in bindings:
            criteria.add(b["tsc_criterion"])
        slots.append(
            {
                "slot_id": m["slot_id"],
                "slot": m["slot"],
                "tsc_anchor": m.get("tsc_anchor", ""),
                "substrate_source": m.get("substrate_source", ""),
                "bindings": bindings,
                "out_of_scope": m.get("out_of_scope", {}).get("note", ""),
            }
        )
    return {
        "adapter_id": ADAPTER_ID,
        "standard": STANDARD,
        "vertical": VERTICAL,
        "status": STATUS,
        "surface_slots_bound": list(SURFACE_SLOTS_BOUND),
        "criteria_covered": sorted(criteria),
        "criteria_count": len(criteria),
        "slots": slots,
    }
