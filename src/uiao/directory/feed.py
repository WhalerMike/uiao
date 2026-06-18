"""Snapshot feeds for the Active Governance Directory (ADR-100).

The AGD's Directory Information Tree is a *projection* of a principal
snapshot (``{principal_id, principal_type, attributes}`` where ``attributes``
maps ``extensionAttributeN`` slots to values). The :mod:`uiao.directory.dit`
builder consumes exactly that shape.

Out of the box the CLI fed the builder a *hand-authored* snapshot file. This
module wires the AGD to a **real OrgPath producer** instead: the output of
``uiao orgtree assess`` (the AD-survey → facet assessment, a list of
``FacetAssignmentResult`` dicts keyed by facet *name*). It converts each
assessment record into the slot-keyed snapshot shape using the Codebook
(UIAO_151) facet→``extensionAttribute`` binding, so the projection traces to
governed assessment output rather than a static file.

Pure (no I/O): callers read the JSON and pass the parsed payload in.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from uiao.modernization.orgtree.codebook import Codebook, default_codebook

# The assessment emits "user" / "device"; the DIT projects user / device /
# servicePrincipal. Map the assessment vocabulary onto the projection's.
_TYPE_MAP = {"user": "user", "device": "device", "servicePrincipal": "servicePrincipal"}


class FeedError(ValueError):
    """Raised when an assessment payload cannot be converted to a snapshot."""


def principals_from_assessment(
    results: Any,
    *,
    codebook: Codebook | None = None,
) -> list[dict]:
    """Convert ``uiao orgtree assess`` output into AGD snapshot principals.

    ``results`` is the parsed ``assess --out`` JSON: a list of
    ``{target_id, target_type, facet_values, findings}`` records (or a dict
    wrapping that list under ``"results"``). Each record's ``facet_values``
    (facet *name* → value) is re-keyed onto the facet's ``extensionAttributeN``
    slot via the Codebook, producing the ``{principal_id, principal_type,
    attributes}`` shape :func:`uiao.directory.dit.build_directory` consumes.

    Records with an empty ``target_id`` are skipped (no DN to project);
    empty/blank facet values and facets absent from the Codebook are dropped
    (an absent value is not a governed assertion).
    """
    cb = codebook or default_codebook()
    if isinstance(results, Mapping):
        results = results.get("results", [])
    if not isinstance(results, list):
        raise FeedError("assessment payload must be a JSON list (or an object with a 'results' list)")

    principals: list[dict] = []
    for record in results:
        if not isinstance(record, Mapping):
            raise FeedError(f"assessment record must be an object, got {type(record).__name__}")
        target_id = str(record.get("target_id") or "").strip()
        if not target_id:
            continue
        ptype = _TYPE_MAP.get(str(record.get("target_type", "user")), "user")
        facet_values = record.get("facet_values") or {}
        if not isinstance(facet_values, Mapping):
            raise FeedError(f"facet_values for '{target_id}' must be an object")

        attributes: dict[str, str] = {}
        for facet_name, value in facet_values.items():
            if value in (None, ""):
                continue
            if not cb.has_facet(str(facet_name)):
                continue
            attributes[cb.facet(str(facet_name)).attribute] = str(value)

        principals.append({"principal_id": target_id, "principal_type": ptype, "attributes": attributes})
    return principals
