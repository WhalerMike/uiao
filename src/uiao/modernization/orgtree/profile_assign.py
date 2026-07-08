"""Profile-driven OrgPath planner — the cross-vendor write planner.

Turns a :class:`~uiao.modernization.orgtree.binding_profiles.BindingProfile`
plus a principal's derived facet values into a flat list of
:class:`~uiao.modernization.orgtree.types.FacetOperation`, routed by the
profile's per-facet locators rather than by the hardcoded Microsoft
``extensionAttribute`` slots.

This is the cross-vendor counterpart to
:class:`~uiao.modernization.orgtree.device_orgpath.DeviceOrgPathPlanner`:
the device planner knows the Entra/Arc slot table; this planner knows
nothing but the codebook (for value validation) and the binding profile
(for locators). Point it at the ``okta`` profile and it plans Okta
custom-attribute writes; point it at ``ldap`` and it plans directory
attribute writes; point it at ``vmware``'s ``enforcement`` plane and it
plans NSX security-tag writes — all from the same code, because the
profile is the only vendor-specific input.

Per ADR-098 / UIAO_193 the planner honors the binding profile's contract:

* only ``writable`` bindings produce ``write`` operations;
* ``reserved`` codebook facets and values that are not active in the
  codebook are skipped (they would land as drift), exactly as the device
  planner does;
* when a plane's bindings plus its ``priority`` overflow rule cannot store
  every supplied facet, the overflow casualties are emitted as ``op``
  ``"uncaptured"`` operations (value preserved, no locator) so the drift
  engine can surface them as ``DRIFT-IDENTITY`` rather than dropping them
  silently.

The planner is dependency-free and dry-run by nature: it produces
operations, it does not execute them. Execution is the transports'
job (see ``okta_transport`` / ``ldap_transport``), wired in by the
caller.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from uiao.modernization.orgtree.binding_profiles import BindingProfile
from uiao.modernization.orgtree.codebook import Codebook, load_codebook
from uiao.modernization.orgtree.types import FacetOperation


class BindingProfilePlanner:
    """Plan per-facet writes for one binding profile + plane."""

    def __init__(self, profile: BindingProfile, codebook: Codebook | None = None) -> None:
        self.profile = profile
        self.codebook = codebook or load_codebook()

    def _ordered_facets_for_plane(self, plane: str, supplied: Mapping[str, str]) -> tuple[list[str], list[str]]:
        """Split supplied facets into (captured, uncaptured) for one plane.

        ``captured`` are facets the profile binds on the plane, in binding
        order, after applying a ``priority`` overflow rule when the plane
        is the constrained one. ``uncaptured`` are supplied facets the
        plane's storage cannot hold — surfaced as drift, never dropped.
        """
        bound = [f for f in self.profile.facets_for_plane(plane) if f in supplied]
        overflow = self.profile.overflow
        ov_plane = None
        if overflow is not None:
            ov_plane = overflow.plane or (self.profile.planes[0] if len(self.profile.planes) == 1 else None)
        if overflow is None or overflow.rule != "priority" or ov_plane != plane:
            return bound, []

        # priority: keep ordering ∩ bound up to the native key budget; the
        # remainder of bound facets past the budget are uncaptured.
        max_keys = None
        constraints = self.profile.constraints
        if isinstance(constraints, Mapping):
            raw = constraints.get("max_keys")
            if isinstance(raw, int):
                max_keys = raw
        prioritized = [f for f in overflow.ordering if f in bound]
        tail = [f for f in bound if f not in prioritized]
        ranked = prioritized + tail
        if max_keys is None or len(ranked) <= max_keys:
            return ranked, []
        return ranked[:max_keys], ranked[max_keys:]

    def _with_derived_path(self, facet_values: Mapping[str, str], plane: str) -> Mapping[str, str]:
        """Recompute the ADR-127 derived OrgPath when the profile binds it.

        The inheritance layer is derived data — never hand-authored — so a
        caller-supplied value for the derived facet is always discarded.
        When the profile binds the facet on this plane AND the caller
        supplied at least one hierarchy facet, the recomputed path is
        injected (a partial assignment that never mentions the hierarchy
        cannot clear a previously stamped path). Profiles that do not bind
        the facet just have the caller value dropped, so it can neither be
        written nor surface as an ``uncaptured`` finding.
        """
        derived_name = self.codebook.derived_path_facet_name()
        if derived_name is None or derived_name not in {*facet_values, *self.profile.facets_for_plane(plane)}:
            return facet_values
        merged = {k: v for k, v in facet_values.items() if k != derived_name}
        if derived_name in self.profile.facets_for_plane(plane):
            layer = (self.codebook.hybrid or {}).get("inheritance_layer") or {}
            if any(name in merged for name in layer.get("derived_from", ())):
                merged[derived_name] = self.codebook.derive_org_path(merged)
        return merged

    def plan_principal(
        self,
        principal_id: str,
        facet_values: Mapping[str, str],
        *,
        plane: str = "identity",
    ) -> list[FacetOperation]:
        """Plan one principal's writes on one plane."""
        if plane not in self.profile.planes:
            raise ValueError(
                f"profile '{self.profile.profile_id}' does not bind plane '{plane}' "
                f"(declares {', '.join(self.profile.planes)})"
            )
        facet_values = self._with_derived_path(facet_values, plane)
        captured, uncaptured = self._ordered_facets_for_plane(plane, facet_values)
        ops: list[FacetOperation] = []
        for facet_name in captured:
            value = facet_values[facet_name]
            facet = self.codebook.facet(facet_name)
            if facet.kind == "reserved":
                continue
            if not facet.is_active(value):
                # Would land as Value Drift — skip the write, as the device planner does.
                continue
            binding = next(b for b in self.profile.bindings_for_plane(plane) if b.facet == facet_name)
            if not binding.writable:
                continue
            ops.append(
                FacetOperation(
                    facet=facet_name,
                    attribute=binding.locator,
                    op="write",
                    value=value,
                    target=principal_id,
                    metadata={
                        "profile": self.profile.profile_id,
                        "plane": plane,
                        "locator_kind": binding.locator_kind,
                    },
                )
            )
        for facet_name in uncaptured:
            ops.append(
                FacetOperation(
                    facet=facet_name,
                    attribute="",
                    op="uncaptured",
                    value=facet_values[facet_name],
                    target=principal_id,
                    metadata={
                        "profile": self.profile.profile_id,
                        "plane": plane,
                        "reason": "overflow",
                    },
                )
            )
        return ops

    def plan(
        self,
        principals: Iterable[tuple[str, Mapping[str, str]]],
        *,
        plane: str = "identity",
    ) -> list[FacetOperation]:
        """Plan many principals on one plane — flat list of all operations."""
        all_ops: list[FacetOperation] = []
        for principal_id, facet_values in principals:
            all_ops.extend(self.plan_principal(principal_id, facet_values, plane=plane))
        return all_ops
