"""
uiao.saas.provisioning
---------------------
The control-plane provisioning service — onboarding, suspension, resumption,
and deprovisioning of customer tenants ("stamps").

Following the same transport-free, dry-run-by-default doctrine as the OrgPath
governance runtime, the actual Azure resource work (creating a per-tenant
Postgres schema, Blob container, Key Vault secret scope, etc.) is delegated
to an injected :class:`StampExecutor`. The default :class:`NoOpStampExecutor`
only *plans* the stamp — it returns the steps it would take without touching
Azure — so the control plane is safe to exercise in CI and locally.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from .audit import AuditAction, AuditEvent, AuditOutcome, AuditSink, NullAuditSink
from .auth import ISSUER_V2_TEMPLATES
from .repository import TenantRepository
from .tenant import Tenant, TenantPlan, TenantStatus, derive_namespace, is_tenant_guid


@dataclass(frozen=True)
class StampStep:
    """A single planned (or executed) provisioning action."""

    action: str
    target: str
    detail: str = ""


@dataclass
class StampResult:
    """The outcome of a provisioning stamp."""

    tenant_id: str
    executed: bool
    steps: list[StampStep] = field(default_factory=list)


class StampExecutor(Protocol):
    """Executes the Azure-resource side of provisioning a tenant."""

    async def stamp(self, tenant: Tenant) -> StampResult: ...

    async def unstamp(self, tenant: Tenant) -> StampResult: ...


class NoOpStampExecutor:
    """Plans the stamp without touching Azure (dry-run default)."""

    async def stamp(self, tenant: Tenant) -> StampResult:
        ns = tenant.data_namespace
        steps = [
            StampStep("create-db-schema", ns, "Postgres schema for tenant-isolated state"),
            StampStep("create-blob-container", ns, "Evidence-bundle storage prefix"),
            StampStep("create-keyvault-scope", ns, "Per-tenant secret scope (client secret / cert)"),
            StampStep("register-graph-consent", tenant.tenant_id, "Verify admin-consent grant for Graph/ARM"),
        ]
        return StampResult(tenant_id=tenant.tenant_id, executed=False, steps=steps)

    async def unstamp(self, tenant: Tenant) -> StampResult:
        ns = tenant.data_namespace
        steps = [
            StampStep("archive-db-schema", ns, "Snapshot then drop tenant schema"),
            StampStep("archive-blob-container", ns, "Retain evidence per policy, revoke access"),
            StampStep("revoke-keyvault-scope", ns, "Delete per-tenant secrets"),
        ]
        return StampResult(tenant_id=tenant.tenant_id, executed=False, steps=steps)


@dataclass
class OnboardingResult:
    """Returned to the control-plane caller after onboarding a tenant."""

    tenant: Tenant
    stamp: StampResult
    admin_consent_url: str


class ProvisioningService:
    """Orchestrates the tenant lifecycle for the control plane."""

    def __init__(
        self,
        *,
        repository: TenantRepository,
        app_client_id: str = "",
        cloud: str = "commercial",
        executor: StampExecutor | None = None,
        audit: AuditSink | None = None,
    ) -> None:
        self._repo = repository
        self._app_client_id = app_client_id
        self._cloud = cloud
        self._executor: StampExecutor = executor or NoOpStampExecutor()
        self._audit: AuditSink = audit or NullAuditSink()

    async def _record(
        self,
        action: AuditAction,
        tenant_id: str,
        *,
        actor: str = "",
        outcome: AuditOutcome = AuditOutcome.SUCCESS,
        detail: str = "",
    ) -> None:
        await self._audit.record(
            AuditEvent(action=action, tenant_id=tenant_id, actor=actor, outcome=outcome, detail=detail)
        )

    def admin_consent_url(self, tenant_id: str) -> str:
        """Build the admin-consent URL a customer admin visits to grant access."""
        base = ISSUER_V2_TEMPLATES[self._cloud].split("/v2.0")[0].rsplit("/", 1)[0]
        return f"{base}/{tenant_id}/adminconsent?client_id={self._app_client_id}"

    async def onboard(
        self,
        *,
        tenant_id: str,
        display_name: str = "",
        plan: TenantPlan = TenantPlan.TRIAL,
        onboarded_by: str = "",
    ) -> OnboardingResult:
        """Onboard a new customer tenant (idempotent on tenant_id)."""
        if not is_tenant_guid(tenant_id):
            raise ValueError(f"{tenant_id!r} is not a valid Entra tenant GUID")

        existing = await self._repo.get(tenant_id)
        if existing is not None and existing.status is not TenantStatus.DEPROVISIONED:
            await self._record(
                AuditAction.ONBOARD,
                tenant_id,
                actor=onboarded_by,
                outcome=AuditOutcome.FAILURE,
                detail=f"already onboarded ({existing.status.value})",
            )
            raise ValueError(f"tenant {tenant_id} is already onboarded ({existing.status.value})")

        tenant = Tenant(
            tenant_id=tenant_id,
            display_name=display_name,
            plan=plan,
            cloud=self._cloud,
            data_namespace=derive_namespace(tenant_id),
            onboarded_by=onboarded_by,
            status=TenantStatus.PENDING,
        )
        await self._repo.upsert(tenant)

        stamp = await self._executor.stamp(tenant)
        # Promote to ACTIVE once the stamp planned/executed without error.
        active = tenant.with_status(TenantStatus.ACTIVE)
        await self._repo.upsert(active)
        await self._record(
            AuditAction.ONBOARD,
            tenant_id,
            actor=onboarded_by,
            detail=f"plan={plan.value} executed={stamp.executed}",
        )

        return OnboardingResult(
            tenant=active,
            stamp=stamp,
            admin_consent_url=self.admin_consent_url(tenant_id),
        )

    async def suspend(self, tenant_id: str, *, reason: str = "", actor: str = "") -> Tenant:
        tenant = await self._repo.set_status(tenant_id, TenantStatus.SUSPENDED, reason=reason)
        await self._record(AuditAction.SUSPEND, tenant_id, actor=actor, detail=reason)
        return tenant

    async def resume(self, tenant_id: str, *, actor: str = "") -> Tenant:
        tenant = await self._repo.set_status(tenant_id, TenantStatus.ACTIVE)
        await self._record(AuditAction.RESUME, tenant_id, actor=actor)
        return tenant

    async def deprovision(self, tenant_id: str, *, actor: str = "") -> StampResult:
        tenant = await self._repo.require(tenant_id)
        result = await self._executor.unstamp(tenant)
        await self._repo.set_status(tenant_id, TenantStatus.DEPROVISIONED)
        await self._record(AuditAction.DEPROVISION, tenant_id, actor=actor, detail=f"executed={result.executed}")
        return result


__all__ = [
    "ProvisioningService",
    "OnboardingResult",
    "StampExecutor",
    "StampResult",
    "StampStep",
    "NoOpStampExecutor",
]
