"""Entra ID dynamic-group provisioning adapter (MOD_B / ADR-036).

Change-making modernization adapter. Reads the canonical library from
``uiao.modernization.orgtree.dynamic_groups`` and reconciles the tenant
state against it via Microsoft Graph.

Verbs
-----
* :meth:`EntraDynamicGroupsAdapter.plan` — compare desired vs actual,
  produce an ordered list of ``create`` / ``update`` / ``delete-phantom``
  operations. No API calls for write.
* :meth:`EntraDynamicGroupsAdapter.apply` — execute a plan. ``dry_run=True``
  by default; set ``dry_run=False`` to issue ``POST /groups`` /
  ``PATCH /groups/{id}`` against Graph.
* :meth:`EntraDynamicGroupsAdapter.reconcile` — plan + apply in one call.

Design notes
------------
* Tenant state comes from ``EntraCollector`` when wired in, but can also be
  injected directly (``current_tenant_state=...``) to keep tests offline.
* ``delete-phantom`` is **never** auto-applied; phantom groups become drift
  findings for governance review (MOD_B §Drift: "No — investigate, then
  delete or canonize"). The canon only auto-remediates ``create`` and
  ``update``.
* Rule normalisation is intentionally strict — the canonical rule string
  and the tenant rule must compare byte-for-byte. Trivial whitespace
  differences are drift until reconciled upstream in the library.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from uiao.modernization.orgtree import (
    DynamicGroupLibrary,
    DynamicGroupSpec,
)
from uiao.modernization.orgtree.dynamic_groups import (
    default_dynamic_group_library,
)

logger = logging.getLogger(__name__)


OP_CREATE = "create"
OP_UPDATE = "update"
OP_DELETE_PHANTOM = "delete-phantom"

OPS_AUTO_APPLIED = frozenset({OP_CREATE, OP_UPDATE})


@dataclass
class PlannedOperation:
    op: str
    group_name: str
    reason: str
    canonical_spec: Optional[DynamicGroupSpec] = None
    tenant_state: Optional[Dict[str, Any]] = None


@dataclass
class DynamicGroupPlan:
    generated_at: str
    total_canonical: int
    total_tenant: int
    operations: List[PlannedOperation] = field(default_factory=list)

    def by_op(self, op: str) -> List[PlannedOperation]:
        return [o for o in self.operations if o.op == op]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_canonical": self.total_canonical,
            "total_tenant": self.total_tenant,
            "operations": [
                {
                    "op": o.op,
                    "group_name": o.group_name,
                    "reason": o.reason,
                    "canonical_rule": (o.canonical_spec.rule if o.canonical_spec else None),
                    "tenant_rule": ((o.tenant_state or {}).get("membershipRule") if o.tenant_state else None),
                }
                for o in self.operations
            ],
        }


@dataclass
class OperationResult:
    op: str
    group_name: str
    status: str  # "skipped-dry-run" | "written" | "failed" | "skipped-manual"
    detail: str = ""


@dataclass
class DynamicGroupReport:
    generated_at: str
    dry_run: bool
    results: List[OperationResult] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.status == "written")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "failed")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "dry_run": self.dry_run,
            "succeeded": self.succeeded,
            "failed": self.failed,
            "results": [r.__dict__ for r in self.results],
        }


class EntraDynamicGroupsAdapter:
    """Modernization adapter: provision OrgTree-* dynamic groups in Entra."""

    ADAPTER_ID = "entra-dynamic-groups"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        library: Optional[DynamicGroupLibrary] = None,
    ) -> None:
        self._config = config or {}
        self._library = library or default_dynamic_group_library()

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------
    def plan(
        self,
        current_tenant_state: Optional[List[Dict[str, Any]]] = None,
    ) -> DynamicGroupPlan:
        """Compare canonical library vs tenant state, produce operations.

        ``current_tenant_state`` is a list of group objects as returned by
        Microsoft Graph ``GET /groups`` — each entry must expose at minimum
        ``displayName`` and ``membershipRule``. If ``None``, the adapter
        treats the tenant as empty (everything becomes a ``create``).
        """
        tenant = current_tenant_state or []
        tenant_by_name: Dict[str, Dict[str, Any]] = {
            g.get("displayName", ""): g
            for g in tenant
            if isinstance(g.get("displayName"), str) and g["displayName"].startswith("OrgTree-")
        }

        plan = DynamicGroupPlan(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_canonical=len(self._library.groups),
            total_tenant=len(tenant_by_name),
        )

        for spec in self._library.groups.values():
            tenant_group = tenant_by_name.get(spec.name)
            if tenant_group is None:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_CREATE,
                        group_name=spec.name,
                        reason="Missing in tenant — canonical definition exists",
                        canonical_spec=spec,
                    )
                )
                continue
            tenant_rule = tenant_group.get("membershipRule", "")
            if tenant_rule != spec.rule:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_UPDATE,
                        group_name=spec.name,
                        reason=(f"Rule drift: canonical != tenant. canonical='{spec.rule}' tenant='{tenant_rule}'"),
                        canonical_spec=spec,
                        tenant_state=tenant_group,
                    )
                )

        canonical_names = set(self._library.groups.keys())
        for name, tenant_group in tenant_by_name.items():
            if name not in canonical_names:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_DELETE_PHANTOM,
                        group_name=name,
                        reason=(
                            "Phantom group — OrgTree- prefix but not in canonical "
                            "library. Governance review required; NOT auto-applied."
                        ),
                        tenant_state=tenant_group,
                    )
                )
        return plan

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------
    def apply(
        self,
        plan: DynamicGroupPlan,
        dry_run: bool = True,
    ) -> DynamicGroupReport:
        """Execute a plan. ``dry_run=True`` returns without calling Graph.

        Operations in :data:`OPS_AUTO_APPLIED` (``create``, ``update``) are
        executed; ``delete-phantom`` is always reported as ``skipped-manual``
        per the MOD_B auto-remediate policy.
        """
        report = DynamicGroupReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            dry_run=dry_run,
        )
        for op in plan.operations:
            if op.op == OP_DELETE_PHANTOM:
                report.results.append(
                    OperationResult(
                        op=op.op,
                        group_name=op.group_name,
                        status="skipped-manual",
                        detail="Phantom group — governance review required (MOD_B).",
                    )
                )
                continue
            if dry_run:
                report.results.append(
                    OperationResult(
                        op=op.op,
                        group_name=op.group_name,
                        status="skipped-dry-run",
                        detail="Dry run — no Graph API call issued.",
                    )
                )
                continue
            # dry_run=False: attempt a real write.
            try:
                self._execute(op)
                report.results.append(
                    OperationResult(
                        op=op.op,
                        group_name=op.group_name,
                        status="written",
                    )
                )
            except Exception as exc:  # pragma: no cover - network path
                logger.exception("Apply failed for %s", op.group_name)
                report.results.append(
                    OperationResult(
                        op=op.op,
                        group_name=op.group_name,
                        status="failed",
                        detail=str(exc),
                    )
                )
        return report

    def reconcile(
        self,
        current_tenant_state: Optional[List[Dict[str, Any]]] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Plan + apply in one call. Returns combined artefact dict."""
        plan = self.plan(current_tenant_state=current_tenant_state)
        report = self.apply(plan, dry_run=dry_run)
        return {"plan": plan.to_dict(), "report": report.to_dict()}

    # ------------------------------------------------------------------
    # Graph API I/O (only exercised with dry_run=False)
    # ------------------------------------------------------------------
    def _execute(self, op: PlannedOperation) -> None:
        """Issue the Graph API call for an approved operation.

        Kept small and deliberately dependency-injectable: callers that
        need to wire in a specific HTTP client or retry policy can override
        this method on a subclass.
        """
        spec = op.canonical_spec
        if spec is None:
            raise ValueError(f"Cannot execute {op.op} without canonical_spec")
        client = self._graph_client()
        if client is None:
            raise RuntimeError(
                "Graph client not configured — provide tenant_id, client_id, "
                "client_secret in adapter config, or override _graph_client()."
            )
        body = spec.to_graph_body()
        base_url = self._config.get("api_base_url", "https://graph.microsoft.com/v1.0")
        if op.op == OP_CREATE:
            resp = client.post(f"{base_url}/groups", json=body)
            resp.raise_for_status()
        elif op.op == OP_UPDATE:
            group_id = (op.tenant_state or {}).get("id")
            if not group_id:
                raise ValueError(f"Cannot UPDATE {op.group_name} without tenant group id")
            patch_body = {
                "membershipRule": body["membershipRule"],
                "membershipRuleProcessingState": body["membershipRuleProcessingState"],
                "description": body["description"],
            }
            resp = client.patch(f"{base_url}/groups/{group_id}", json=patch_body)
            resp.raise_for_status()
        else:
            raise ValueError(f"Unsupported op for Graph execution: {op.op}")

    def _graph_client(self):  # type: ignore[no-untyped-def]  # pragma: no cover - network path
        """Return an httpx client authenticated against Graph, or ``None``.

        Mirrors :class:`uiao.collectors.entra.entra_collector.EntraCollector`
        so Phase 2 reuses the Phase 1 token-acquisition pattern when we
        bridge the two adapters in Phase 3.
        """
        try:
            import httpx  # type: ignore
            from azure.identity import ClientSecretCredential  # type: ignore
        except ImportError:
            return None

        tenant_id = self._config.get("tenant_id")
        client_id = self._config.get("client_id")
        client_secret = self._config.get("client_secret")
        if not all([tenant_id, client_id, client_secret]):
            return None

        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )

        class _Auth(httpx.Auth):
            def __init__(self, cred):  # type: ignore[no-untyped-def]
                self.cred = cred
                self.token = None

            def auth_flow(self, request):  # type: ignore[no-untyped-def]
                if self.token is None:
                    tok = self.cred.get_token("https://graph.microsoft.com/.default")
                    self.token = tok.token
                request.headers["Authorization"] = f"Bearer {self.token}"
                yield request

        return httpx.Client(auth=_Auth(credential), timeout=30.0)
