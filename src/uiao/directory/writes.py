"""Write translation for the Active Governance Directory (ADR-109).

ADR-109 lets the AGD accept LDAP writes, but only as **governed intent**: a
``modify`` at the edge is never applied to the projection (there is no
store, ADR-100 §3). Instead it is translated into the control plane's native
unit of work — the per-facet :class:`~uiao.modernization.orgtree.types.FacetOperation`
(ADR-084) — validated against the Codebook, and routed through the
modernization adapters' ``apply`` seam **dry-run by default** (ADR-040).

Only the governed ``uiaoOrgPath<Facet>`` attributes (the ``ldap`` binding
profile, UIAO_193) are writable; a write to anything else is refused
(ADR-109 §2). OrgPath facets are single-valued, so a multi-valued change is
refused rather than partially honored. This module does no I/O and holds no
provider credentials — the actual apply is an injected callable.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from uiao.directory.protocol import ModifyOp, ModifyRequest
from uiao.modernization.orgtree.binding_profiles import BindingProfile, load_binding_profile
from uiao.modernization.orgtree.codebook import Codebook, default_codebook
from uiao.modernization.orgtree.types import FacetOperation

_IDENTITY_PLANE = "identity"


@dataclass(frozen=True)
class WritePlan:
    """The translation of one ModifyRequest.

    ``operations`` is the governed change-set (empty on refusal); ``refusal``
    is the human-readable reason the write was not translatable (``None`` when
    the plan is valid).
    """

    operations: tuple[FacetOperation, ...] = ()
    refusal: str | None = None

    @property
    def refused(self) -> bool:
        return self.refusal is not None


@dataclass(frozen=True)
class RouteResult:
    """The outcome of routing a write through :class:`WriteRouter`."""

    applied: bool
    refused: bool
    message: str
    plan: WritePlan


def _locator_to_facet(profile: BindingProfile) -> dict[str, str]:
    """Reverse the identity-plane bindings: ``uiaoOrgPath<Facet>`` -> facet name."""
    return {b.locator.lower(): b.facet for b in profile.bindings_for_plane(_IDENTITY_PLANE)}


def translate_modify(
    req: ModifyRequest,
    *,
    codebook: Codebook | None = None,
    profile: BindingProfile | None = None,
) -> WritePlan:
    """Translate a ModifyRequest into a governed :class:`WritePlan` (ADR-109)."""
    cb = codebook or default_codebook()
    prof = profile or load_binding_profile("ldap")
    locator_map = _locator_to_facet(prof)

    operations: list[FacetOperation] = []
    for change in req.changes:
        facet_name = locator_map.get(change.attribute.lower())
        if facet_name is None:
            return WritePlan(refusal=f"attribute '{change.attribute}' is not a governed OrgPath facet")
        facet = cb.facet(facet_name)
        if change.operation == ModifyOp.DELETE:
            operations.append(
                FacetOperation(facet=facet_name, attribute=facet.attribute, op="remove", value=None, target=req.object)
            )
            continue
        # add / replace: single-valued, Codebook-validated.
        if len(change.values) != 1:
            return WritePlan(refusal=f"facet '{facet_name}' is single-valued (got {len(change.values)} values)")
        value = change.values[0]
        if not facet.is_valid_value(value):
            return WritePlan(refusal=f"value '{value}' is not valid for facet '{facet_name}'")
        operations.append(
            FacetOperation(facet=facet_name, attribute=facet.attribute, op="write", value=value, target=req.object)
        )
    return WritePlan(operations=tuple(operations))


@dataclass
class WriteRouter:
    """Routes a translated write to the control plane (dry-run by default).

    With ``dry_run=True`` (the default) or no ``apply_fn``, a valid write is
    accepted and its plan returned but **not** applied — the ADR-109 §3
    governed-intent default. Actuation requires both ``dry_run=False`` and an
    injected ``apply_fn`` (the seam to the modernization adapters' ``apply``).
    """

    codebook: Codebook | None = None
    profile: BindingProfile | None = None
    dry_run: bool = True
    apply_fn: Callable[[tuple[FacetOperation, ...]], None] | None = None

    def route(self, req: ModifyRequest) -> RouteResult:
        plan = translate_modify(req, codebook=self.codebook, profile=self.profile)
        if plan.refused:
            return RouteResult(applied=False, refused=True, message=plan.refusal or "refused", plan=plan)
        count = len(plan.operations)
        if self.dry_run or self.apply_fn is None:
            return RouteResult(
                applied=False,
                refused=False,
                message=f"dry-run: {count} facet operation(s) planned, not applied",
                plan=plan,
            )
        self.apply_fn(plan.operations)
        return RouteResult(applied=True, refused=False, message=f"applied {count} facet operation(s)", plan=plan)
