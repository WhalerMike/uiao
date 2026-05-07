"""Tests for UIAO_119 v2 wave 3 — orchestrator plane selection through flags."""

from __future__ import annotations

from uiao.governance.feature_flags import FeatureFlag, FeatureFlagRegistry
from uiao.governance.tenancy import (
    Environment,
    Tenant,
    TenantClass,
    TenantContext,
)
from uiao.orchestrator.orchestrator import (
    PLANE_FLAGS,
    PLANES_ALL,
    select_planes,
)


# ---------------------------------------------------------------------------
# select_planes — back-compat
# ---------------------------------------------------------------------------


class TestSelectPlanesBackCompat:
    def test_no_flags_returns_input_unchanged(self):
        assert select_planes(PLANES_ALL) == PLANES_ALL

    def test_no_tenant_context_returns_input_unchanged(self):
        flags = FeatureFlagRegistry()
        assert select_planes(PLANES_ALL, flags=flags) == PLANES_ALL

    def test_empty_request_stays_empty(self):
        assert select_planes([]) == []
        assert (
            select_planes(
                [],
                flags=FeatureFlagRegistry(),
                tenant_context=TenantContext(),
            )
            == []
        )


# ---------------------------------------------------------------------------
# select_planes — flag-driven filtering
# ---------------------------------------------------------------------------


class TestSelectPlanesFiltering:
    def _flags_for(self, **plane_settings) -> FeatureFlagRegistry:
        """Helper: build a FeatureFlagRegistry where each plane's flag is
        either enabled-everywhere or disabled-everywhere."""
        registry: dict[str, FeatureFlag] = {}
        for plane, flag_name in PLANE_FLAGS.items():
            enabled = plane_settings.get(plane, True)
            envs = frozenset({Environment.DEV, Environment.STAGE, Environment.PROD}) if enabled else frozenset()
            classes = (
                frozenset(
                    {
                        TenantClass.INTERNAL,
                        TenantClass.CANARY,
                        TenantClass.STANDARD,
                        TenantClass.REGULATED,
                    }
                )
                if enabled
                else frozenset()
            )
            registry[flag_name] = FeatureFlag(
                name=flag_name,
                enabled_environments=envs,
                enabled_tenant_classes=classes,
            )
        return FeatureFlagRegistry(flags=registry)

    def test_all_enabled_returns_all_planes(self):
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        flags = self._flags_for()  # all enabled by default
        assert select_planes(PLANES_ALL, flags=flags, tenant_context=ctx) == PLANES_ALL

    def test_disabled_plane_dropped(self):
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        flags = self._flags_for(plane4=False)
        assert select_planes(PLANES_ALL, flags=flags, tenant_context=ctx) == [
            "plane1",
            "plane2",
            "plane3",
        ]

    def test_multiple_disabled_planes_dropped(self):
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        flags = self._flags_for(plane2=False, plane4=False)
        assert select_planes(PLANES_ALL, flags=flags, tenant_context=ctx) == [
            "plane1",
            "plane3",
        ]

    def test_unknown_plane_kept(self):
        # A plane not in PLANE_FLAGS is treated as caller-defined; it
        # passes through the filter without consulting any flag.
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        flags = self._flags_for()
        out = select_planes(
            ["plane1", "plane99-future", "plane4"],
            flags=flags,
            tenant_context=ctx,
        )
        assert out == ["plane1", "plane99-future", "plane4"]

    def test_tenant_class_gate_applied(self):
        # When a Tenant is supplied, the class gate runs. A flag enabled
        # only for INTERNAL drops the plane for a STANDARD tenant.
        flag = FeatureFlag(
            name=PLANE_FLAGS["plane4"],
            enabled_environments=frozenset({Environment.PROD}),
            enabled_tenant_classes=frozenset({TenantClass.INTERNAL}),
        )
        flags = FeatureFlagRegistry(flags={flag.name: flag})
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)

        # Standard tenant — plane4 dropped.
        standard = Tenant(id="acme", tenant_class=TenantClass.STANDARD)
        assert "plane4" not in select_planes(
            PLANES_ALL,
            flags=flags,
            tenant_context=ctx,
            tenant=standard,
        )
        # Internal tenant — plane4 kept.
        internal = Tenant(id="acme-internal", tenant_class=TenantClass.INTERNAL)
        assert "plane4" in select_planes(
            PLANES_ALL,
            flags=flags,
            tenant_context=ctx,
            tenant=internal,
        )

    def test_preserves_input_order(self):
        # select_planes must not reorder; planes have a strict execution
        # order (plane1 → plane2 → plane3 → plane4) and the orchestrator
        # iterates in the order returned.
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        flags = self._flags_for()
        # Caller passes a non-canonical order — sandbox-style preview
        # of "what if I run plane3 before plane1?" — and select_planes
        # honors it.
        out = select_planes(
            ["plane3", "plane1", "plane4", "plane2"],
            flags=flags,
            tenant_context=ctx,
        )
        assert out == ["plane3", "plane1", "plane4", "plane2"]


# ---------------------------------------------------------------------------
# Live canon smoke — every PLANE_FLAGS entry resolves to a canonical flag
# ---------------------------------------------------------------------------


class TestLiveCanonSmoke:
    def test_every_plane_flag_in_canon(self):
        from uiao.governance.feature_flags import load_canonical_flags

        registry = load_canonical_flags()
        for plane, flag_name in PLANE_FLAGS.items():
            flag = registry.get(flag_name)
            assert flag is not None, f"plane {plane!r} maps to missing canon flag {flag_name!r}"
            assert flag.spec_ref, f"plane flag {flag_name!r} missing spec_ref in canon"

    def test_canonical_flags_default_enables_every_plane(self):
        # Default canon enables all four planes for every environment +
        # tenant class — back-compat run-all behavior.
        from uiao.governance.feature_flags import load_canonical_flags

        registry = load_canonical_flags()
        ctx = TenantContext(tenant_id="acme", environment=Environment.PROD)
        tenant = Tenant(id="acme", tenant_class=TenantClass.STANDARD)
        out = select_planes(PLANES_ALL, flags=registry, tenant_context=ctx, tenant=tenant)
        assert out == PLANES_ALL
