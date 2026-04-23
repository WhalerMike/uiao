"""Entra ID Administrative Unit + scoped-role provisioning adapter.

Phase 3 (MOD_D / ADR-037). Reconciles the tenant against the canonical
delegation matrix (AUs, built-in roles, role assignments) loaded from
``uiao.modernization.orgtree.admin_units``.

Verbs
-----
* :meth:`EntraAdminUnitsAdapter.plan` — diff canon vs tenant; produce a
  list of ``au-create`` / ``au-update`` / ``au-delete-phantom`` /
  ``role-create`` / ``role-delete-unscoped`` / ``role-delete-phantom``
  operations. Zero network calls.
* :meth:`EntraAdminUnitsAdapter.apply` — execute approved operations.
  Dry-run by default. On ``dry_run=False`` issues:
    - ``POST /directoryAdministrativeUnits``
    - ``PATCH /directoryAdministrativeUnits/{id}``
    - ``POST /roleManagement/directory/roleAssignments``
* :meth:`EntraAdminUnitsAdapter.reconcile` — plan + apply → artefact.

Critical policy (MOD_D §Drift Detection Rules)
----------------------------------------------
* ``role-delete-unscoped`` is **never** auto-applied. A tenant-wide
  (directoryScopeId=/) role assignment is a potential privilege
  escalation — the adapter reports it as ``skipped-manual`` and routes
  to governance review (MOD_E Workflow 5). This matches the MOD_D rule
  "Auto-Remediate: No — investigate (potential privilege escalation)".
* ``au-delete-phantom`` and ``role-delete-phantom`` are also never
  auto-applied; phantoms are governance findings.
* Only ``au-create``, ``au-update``, and ``role-create`` are executed
  by ``apply(dry_run=False)``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from uiao.modernization.orgtree import (
    AdministrativeUnit,
    DelegationMatrix,
    RoleAssignment,
)
from uiao.modernization.orgtree.admin_units import default_delegation_matrix

logger = logging.getLogger(__name__)


OP_AU_CREATE = "au-create"
OP_AU_UPDATE = "au-update"
OP_AU_DELETE_PHANTOM = "au-delete-phantom"
OP_ROLE_CREATE = "role-create"
OP_ROLE_DELETE_UNSCOPED = "role-delete-unscoped"
OP_ROLE_DELETE_PHANTOM = "role-delete-phantom"

OPS_AUTO_APPLIED = frozenset({OP_AU_CREATE, OP_AU_UPDATE, OP_ROLE_CREATE})
OPS_GOVERNANCE_REVIEW = frozenset(
    {
        OP_AU_DELETE_PHANTOM,
        OP_ROLE_DELETE_UNSCOPED,
        OP_ROLE_DELETE_PHANTOM,
    }
)


@dataclass
class PlannedOperation:
    op: str
    target: str
    reason: str
    canonical_au: Optional[AdministrativeUnit] = None
    canonical_assignment: Optional[RoleAssignment] = None
    tenant_state: Optional[Dict[str, Any]] = None


@dataclass
class DelegationPlan:
    generated_at: str
    total_canonical_aus: int
    total_canonical_assignments: int
    total_tenant_aus: int
    total_tenant_assignments: int
    operations: List[PlannedOperation] = field(default_factory=list)

    def by_op(self, op: str) -> List[PlannedOperation]:
        return [o for o in self.operations if o.op == op]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "total_canonical_aus": self.total_canonical_aus,
            "total_canonical_assignments": self.total_canonical_assignments,
            "total_tenant_aus": self.total_tenant_aus,
            "total_tenant_assignments": self.total_tenant_assignments,
            "operations": [
                {
                    "op": o.op,
                    "target": o.target,
                    "reason": o.reason,
                }
                for o in self.operations
            ],
        }


@dataclass
class OperationResult:
    op: str
    target: str
    status: str  # skipped-dry-run | written | failed | skipped-manual
    detail: str = ""


@dataclass
class DelegationReport:
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


class EntraAdminUnitsAdapter:
    """Modernization adapter: provision AUs + scoped role assignments."""

    ADAPTER_ID = "entra-admin-units"

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        matrix: Optional[DelegationMatrix] = None,
    ) -> None:
        self._config = config or {}
        self._matrix = matrix or default_delegation_matrix()

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------
    def plan(
        self,
        current_tenant_aus: Optional[List[Dict[str, Any]]] = None,
        current_tenant_role_assignments: Optional[List[Dict[str, Any]]] = None,
        principal_id_resolver: Optional[Dict[str, str]] = None,
    ) -> DelegationPlan:
        """Diff canon vs tenant state; return an ordered operations list.

        Parameters
        ----------
        current_tenant_aus:
            List of Graph ``administrativeUnit`` objects. Each entry must
            expose ``id``, ``displayName``, ``membershipRule``, and
            ``isMemberManagementRestricted``.
        current_tenant_role_assignments:
            List of Graph ``unifiedRoleAssignment`` objects with ``id``,
            ``roleDefinitionId``, ``principalId``, and ``directoryScopeId``.
        principal_id_resolver:
            Optional map ``{group displayName → group id}`` used to match
            tenant role_assignments against canonical ones. When a
            principal can't be resolved, the corresponding canonical
            assignment is still planned as ``role-create`` (caller will
            resolve at apply time).
        """
        tenant_aus = current_tenant_aus or []
        tenant_assignments = current_tenant_role_assignments or []
        resolver = principal_id_resolver or {}

        tenant_au_by_name: Dict[str, Dict[str, Any]] = {
            a.get("displayName", ""): a
            for a in tenant_aus
            if isinstance(a.get("displayName"), str) and a["displayName"].startswith("AU-ORG")
        }

        plan = DelegationPlan(
            generated_at=datetime.now(timezone.utc).isoformat(),
            total_canonical_aus=len(self._matrix.administrative_units),
            total_canonical_assignments=len(self._matrix.role_assignments),
            total_tenant_aus=len(tenant_au_by_name),
            total_tenant_assignments=len(tenant_assignments),
        )

        # ---- Administrative Units ----
        for au in self._matrix.administrative_units.values():
            tenant_au = tenant_au_by_name.get(au.name)
            if tenant_au is None:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_AU_CREATE,
                        target=au.name,
                        reason="Missing in tenant — canonical AU exists",
                        canonical_au=au,
                    )
                )
                continue
            reasons: List[str] = []
            if tenant_au.get("membershipRule") != au.membership_rule:
                reasons.append(
                    f"Rule drift: canonical='{au.membership_rule}' tenant='{tenant_au.get('membershipRule')}'"
                )
            if not bool(tenant_au.get("isMemberManagementRestricted")):
                reasons.append(
                    "isMemberManagementRestricted=False — MOD_D mandates "
                    "Restricted Management for every AU in the matrix"
                )
            if reasons:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_AU_UPDATE,
                        target=au.name,
                        reason="; ".join(reasons),
                        canonical_au=au,
                        tenant_state=tenant_au,
                    )
                )

        canonical_au_names = self._matrix.au_names
        for name, tenant_au in tenant_au_by_name.items():
            if name not in canonical_au_names:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_AU_DELETE_PHANTOM,
                        target=name,
                        reason=(
                            "Phantom AU — AU-ORG prefix but not in MOD_D matrix. "
                            "Governance review required; NOT auto-applied."
                        ),
                        tenant_state=tenant_au,
                    )
                )

        # ---- Role Assignments ----
        # Build the set of (roleDefinitionId, principalId, directoryScopeId)
        # tuples both canon and tenant expose.
        au_id_by_name = {a.get("displayName"): a.get("id") for a in tenant_aus}

        canonical_assignment_triples: Dict[Tuple[str, str, str], RoleAssignment] = {}
        unresolved_canonical: List[RoleAssignment] = []
        for ra in self._matrix.role_assignments:
            template_id = self._matrix.role_template_id(ra.role)
            principal_id = resolver.get(ra.principal_group)
            au_id = au_id_by_name.get(ra.au_scope)
            if not (template_id and principal_id and au_id):
                # Cannot form a tuple yet — still plan a create; apply will
                # re-resolve at write time.
                unresolved_canonical.append(ra)
                continue
            triple = (
                template_id,
                principal_id,
                f"/administrativeUnits/{au_id}",
            )
            canonical_assignment_triples[triple] = ra

        tenant_triples = {
            (
                t.get("roleDefinitionId", ""),
                t.get("principalId", ""),
                t.get("directoryScopeId", ""),
            ): t
            for t in tenant_assignments
        }

        for triple, ra in canonical_assignment_triples.items():
            if triple not in tenant_triples:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_ROLE_CREATE,
                        target=f"{ra.role}@{ra.au_scope} -> {ra.principal_group}",
                        reason="Missing in tenant — canonical assignment exists",
                        canonical_assignment=ra,
                    )
                )

        # Everything in the canon that couldn't be triple-resolved still
        # plans a create — caller resolves at write time.
        for ra in unresolved_canonical:
            plan.operations.append(
                PlannedOperation(
                    op=OP_ROLE_CREATE,
                    target=f"{ra.role}@{ra.au_scope} -> {ra.principal_group}",
                    reason=(
                        "Missing in tenant — canonical assignment exists (principal or AU id not resolved at plan time)"
                    ),
                    canonical_assignment=ra,
                )
            )

        for triple, tenant_ra in tenant_triples.items():
            if triple in canonical_assignment_triples:
                continue
            scope = triple[2]
            if scope in ("/", ""):
                plan.operations.append(
                    PlannedOperation(
                        op=OP_ROLE_DELETE_UNSCOPED,
                        target=f"assignment:{tenant_ra.get('id', '<unknown>')}",
                        reason=(
                            "Tenant-wide role assignment (directoryScopeId=/) — "
                            "MOD_D §Governance Rule 4 prohibits unscoped role "
                            "assignments. Investigate; NOT auto-applied."
                        ),
                        tenant_state=tenant_ra,
                    )
                )
            else:
                plan.operations.append(
                    PlannedOperation(
                        op=OP_ROLE_DELETE_PHANTOM,
                        target=f"assignment:{tenant_ra.get('id', '<unknown>')}",
                        reason=(
                            "Phantom role assignment — not in MOD_D matrix. "
                            "Potential privilege escalation; NOT auto-applied."
                        ),
                        tenant_state=tenant_ra,
                    )
                )

        return plan

    # ------------------------------------------------------------------
    # Apply
    # ------------------------------------------------------------------
    def apply(
        self,
        plan: DelegationPlan,
        dry_run: bool = True,
    ) -> DelegationReport:
        report = DelegationReport(
            generated_at=datetime.now(timezone.utc).isoformat(),
            dry_run=dry_run,
        )
        for op in plan.operations:
            if op.op in OPS_GOVERNANCE_REVIEW:
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="skipped-manual",
                        detail=("MOD_D §Drift: governance review required; never auto-applied."),
                    )
                )
                continue
            if dry_run:
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="skipped-dry-run",
                        detail="Dry run — no Graph API call issued.",
                    )
                )
                continue
            try:
                self._execute(op)
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="written",
                    )
                )
            except Exception as exc:  # pragma: no cover - network path
                logger.exception("Apply failed for %s", op.target)
                report.results.append(
                    OperationResult(
                        op=op.op,
                        target=op.target,
                        status="failed",
                        detail=str(exc),
                    )
                )
        return report

    def reconcile(
        self,
        current_tenant_aus: Optional[List[Dict[str, Any]]] = None,
        current_tenant_role_assignments: Optional[List[Dict[str, Any]]] = None,
        principal_id_resolver: Optional[Dict[str, str]] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        plan = self.plan(
            current_tenant_aus=current_tenant_aus,
            current_tenant_role_assignments=current_tenant_role_assignments,
            principal_id_resolver=principal_id_resolver,
        )
        report = self.apply(plan, dry_run=dry_run)
        return {"plan": plan.to_dict(), "report": report.to_dict()}

    # ------------------------------------------------------------------
    # Graph API I/O (only exercised with dry_run=False)
    # ------------------------------------------------------------------
    def _execute(self, op: PlannedOperation) -> None:
        """Issue the Graph API call for an approved operation."""
        client = self._graph_client()
        if client is None:
            raise RuntimeError(
                "Graph client not configured — provide tenant_id, client_id, "
                "client_secret in adapter config, or override _graph_client()."
            )
        base_url = self._config.get("api_base_url", "https://graph.microsoft.com/v1.0")
        if op.op == OP_AU_CREATE:
            if op.canonical_au is None:
                raise ValueError("au-create requires canonical_au")
            resp = client.post(
                f"{base_url}/directory/administrativeUnits",
                json=op.canonical_au.to_graph_body(),
            )
            resp.raise_for_status()
        elif op.op == OP_AU_UPDATE:
            if op.canonical_au is None or not op.tenant_state:
                raise ValueError("au-update requires canonical_au + tenant_state")
            au_id = op.tenant_state.get("id")
            if not au_id:
                raise ValueError(f"Cannot UPDATE AU {op.target} without id")
            body = op.canonical_au.to_graph_body()
            patch = {
                "description": body["description"],
                "isMemberManagementRestricted": body["isMemberManagementRestricted"],
                "membershipRule": body["membershipRule"],
                "membershipRuleProcessingState": body["membershipRuleProcessingState"],
            }
            resp = client.patch(
                f"{base_url}/directory/administrativeUnits/{au_id}",
                json=patch,
            )
            resp.raise_for_status()
        elif op.op == OP_ROLE_CREATE:
            if op.canonical_assignment is None:
                raise ValueError("role-create requires canonical_assignment")
            # Resolution pulled from config at write time — subclasses may
            # override to fetch from tenant.
            raise RuntimeError(
                "role-create requires subclass override of _execute or "
                "pre-resolved principal/AU ids — Phase 3 ships the planning "
                "surface; wiring the resolver is part of Phase 3.5."
            )
        else:
            raise ValueError(f"Unsupported op for Graph execution: {op.op}")

    def _graph_client(self):  # pragma: no cover - network path
        """Return an httpx client authenticated against Graph, or ``None``.

        Mirrors :class:`uiao.adapters.entra_dynamic_groups`.
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
            def __init__(self, cred):
                self.cred = cred
                self.token = None

            def auth_flow(self, request):
                if self.token is None:
                    tok = self.cred.get_token("https://graph.microsoft.com/.default")
                    self.token = tok.token
                request.headers["Authorization"] = f"Bearer {self.token}"
                yield request

        return httpx.Client(auth=_Auth(credential), timeout=30.0)
