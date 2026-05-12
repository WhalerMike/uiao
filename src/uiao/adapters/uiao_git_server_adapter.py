"""
UIAO Self-Hosted Git Server (Windows Server 2025 + IIS + Gitea) Adapter.

Conformance class, read-only, telemetry mission-class. Observes the
canonical UIAO Git substrate (per ADR-041) and emits three evidence
files:

    git-server-health.json    -- service liveness, version, uptime
    git-tls-inventory.json    -- certificate chain, expiry, cipher posture
    git-repo-inventory.json   -- org/repo enumeration, commit-signing posture

Classification (per src/uiao/canon/adapter-registry.yaml):

    id:               uiao-git-server
    class:            conformance
    mission-class:    telemetry
    runner-class:     on-prem-self-hosted
    tenancy:          per-customer

The adapter is data-shape-first: its public methods accept already-fetched
JSON payloads from the Gitea REST API rather than performing network I/O
themselves. The thin HTTP wrapper that produces those payloads lives in
the build-guide PowerShell (Phase 14.4 -- "UIAO_163 drift reporter") and
in any future CLI command; keeping the adapter itself I/O-free is what
lets the test suite assert behavior deterministically without a live
Gitea instance.

Build-guide cross-reference: docs/customer-documents/platform/platform-server-build.qmd
v1.3 Phases 4 (Gitea install), 6 (LDAPS auth), 8 (mirror), 9 (hooks),
14.4 (drift reporting).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .database_base import (
    ClaimObject,
    ClaimSet,
    ConnectionProvenance,
    DatabaseAdapterBase,
    DriftReport,
    EvidenceObject,
    QueryProvenance,
    SchemaMappingObject,
)


class UiaoGitServerAdapter(DatabaseAdapterBase):
    """UIAO Self-Hosted Git Server adapter -- conformance / telemetry."""

    ADAPTER_ID: str = "uiao-git-server"

    # Evidence-file names the adapter is contracted to produce (matches the
    # `outputs:` block of the registry entry).
    EVIDENCE_OUTPUTS = (
        "git-server-health.json",
        "git-tls-inventory.json",
        "git-repo-inventory.json",
    )

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config or {})
        self._endpoint: str = self._config.get("endpoint", "https://git.uiao.corp.contoso.com")
        self._tls_version: str = self._config.get("tls_version", "TLSv1.3")
        self._mtls_enabled: bool = bool(self._config.get("mtls_enabled", False))

    # ------------------------------------------------------------------
    # 2.1 Connection & Identity
    # ------------------------------------------------------------------

    def connect(self) -> ConnectionProvenance:
        return ConnectionProvenance(
            identity=f"uiao-git-server:{self._endpoint}",
            auth_method=self._config.get("auth_method", "token"),
            endpoint=self._endpoint,
            tls_version=self._tls_version,
            mtls_enabled=self._mtls_enabled,
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.2 Schema discovery & canonical mapping
    # ------------------------------------------------------------------

    def discover_schema(self) -> SchemaMappingObject:
        vendor_schema: Dict[str, Any] = {
            # /api/v1/version
            "gitea_version": "string",
            # /api/v1/repos -- per-repo shape
            "repo.id": "int",
            "repo.full_name": "string",
            "repo.default_branch": "string",
            "repo.private": "bool",
            "repo.archived": "bool",
            "repo.size_kb": "int",
            "repo.has_signed_commits": "bool",
            # /api/v1/admin/cron + service-health probe
            "service.uptime_seconds": "int",
            "service.health": "string",
            # /api/v1/admin/orgs/{org}/teams
            "team.name": "string",
            "team.permission": "string",
            # TLS certificate metadata (gathered out-of-band)
            "tls.subject": "string",
            "tls.issuer": "string",
            "tls.not_after": "datetime",
            "tls.sha256_fingerprint": "string",
            "tls.cipher_suite": "string",
        }
        canonical_schema: Dict[str, Any] = {
            "identity": "uiao-git-server:<endpoint>",
            "control_ids": ["CM-2", "CM-3", "AU-2", "SC-12", "SC-13"],
            "evidence.source": "uiao-git-server",
            "outputs": list(self.EVIDENCE_OUTPUTS),
        }
        return SchemaMappingObject(
            vendor_schema=vendor_schema,
            canonical_schema=canonical_schema,
            mapping_rules={
                "repo.full_name": "identity suffix for repo-inventory claims",
                "tls.not_after": "expiry drift signal",
                "service.health": "operational drift signal",
            },
            unmapped_fields=[
                "repo.fork",
                "repo.template",
                "team.includes_all_repositories",
            ],
            version_hash=self._hash({"vendor": vendor_schema, "canonical": canonical_schema}),
        )

    # ------------------------------------------------------------------
    # 2.3 Query normalization & deterministic extraction
    # ------------------------------------------------------------------

    def execute_query(self, canonical_query: Dict[str, Any]) -> QueryProvenance:
        scope = canonical_query.get("from", "service-health")
        endpoint_map = {
            "service-health": "/api/v1/version",
            "tls-inventory": "/api/v1/settings/ui",  # adapter pulls cert OOB
            "repo-inventory": "/api/v1/repos/search?limit=50",
            "team-inventory": "/api/v1/orgs/{org}/teams",
            "access-audit": "/api/v1/admin/cron",
        }
        path = endpoint_map.get(scope, "/api/v1/version")
        vendor_query = f"GET {self._endpoint}{path}"
        return QueryProvenance(
            canonical_query=canonical_query,
            vendor_query=vendor_query,
            execution_plan_hash=self._hash(vendor_query),
            row_count=0,
            timestamp=self._now(),
        )

    # ------------------------------------------------------------------
    # 2.4 Data normalization & claim construction
    # ------------------------------------------------------------------

    def normalize(self, raw_rows: List[Dict[str, Any]]) -> ClaimSet:
        """Normalize Gitea repo objects into ClaimObjects.

        Each row is expected to be a repo object from /api/v1/repos/search.
        Empty / unknown fields default safely so the adapter never raises
        on partial payloads.
        """
        claims: List[ClaimObject] = []
        for repo in raw_rows:
            full_name = repo.get("full_name") or repo.get("name") or "unknown"
            claim_id = f"uiao-git-server:{self._endpoint}:{full_name}"
            claims.append(
                ClaimObject(
                    claim_id=claim_id,
                    entity=f"git-repository:{full_name}",
                    fields={
                        "identity": claim_id,
                        "full_name": full_name,
                        "default_branch": repo.get("default_branch", "main"),
                        "private": bool(repo.get("private", True)),
                        "archived": bool(repo.get("archived", False)),
                        "size_kb": int(repo.get("size", 0)),
                        "has_signed_commits": bool(repo.get("has_signed_commits", False)),
                    },
                    source=self.ADAPTER_ID,
                    provenance_hash=self._hash(repo),
                )
            )
        return ClaimSet(claims=claims, source_reference=self._endpoint)

    # ------------------------------------------------------------------
    # 2.5 Drift detection & version integrity
    # ------------------------------------------------------------------

    def detect_drift(self) -> DriftReport:
        return DriftReport(
            drift_type="uiao-git-server-posture",
            severity="info",
            first_observed=self._now(),
            last_observed=self._now(),
            details={
                "message": (
                    "Drift detection scaffold -- compare current service "
                    "health, TLS posture, and repo inventory against the "
                    "ADR-041 baseline."
                ),
                "adapter": self.ADAPTER_ID,
                "endpoint": self._endpoint,
            },
            remediation=(
                "Reconcile drift via the Phase 14.4 UIAO_163 reporter: "
                "Submit-DriftReport -Engine UIAO_163 -Payload @{ ... }."
            ),
        )

    # ------------------------------------------------------------------
    # Adapter-specific helpers — each shapes one of the three evidence
    # outputs declared in the registry.
    # ------------------------------------------------------------------

    def shape_service_health(self, version_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return the git-server-health.json data shape.

        Args:
            version_payload: Parsed response from `GET /api/v1/version`,
                optionally augmented with health + uptime fields from
                the runbook's own probe.
        """
        v = version_payload or {}
        return {
            "adapter_id": self.ADAPTER_ID,
            "endpoint": self._endpoint,
            "gitea_version": v.get("version", "unknown"),
            "service_health": v.get("health", "unknown"),
            "uptime_seconds": int(v.get("uptime_seconds", 0)),
            "timestamp": self._now().isoformat(),
        }

    def shape_tls_inventory(self, cert_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return the git-tls-inventory.json data shape.

        Args:
            cert_payload: Parsed certificate metadata gathered out-of-band
                (e.g. via `Get-ChildItem Cert:\\LocalMachine\\My` on the
                build host, or `openssl s_client -connect ... | openssl x509`).
        """
        c = cert_payload or {}
        return {
            "adapter_id": self.ADAPTER_ID,
            "endpoint": self._endpoint,
            "subject": c.get("subject", ""),
            "issuer": c.get("issuer", ""),
            "not_after": c.get("not_after", ""),
            "sha256_fingerprint": c.get("sha256_fingerprint", ""),
            "tls_version": self._tls_version,
            "cipher_suite": c.get("cipher_suite", ""),
            "mtls_enabled": self._mtls_enabled,
            "timestamp": self._now().isoformat(),
        }

    def shape_repo_inventory(self, repos_payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Return the git-repo-inventory.json data shape.

        Args:
            repos_payload: Parsed response from `GET /api/v1/repos/search`
                (Gitea returns `{"data": [ ... ], "ok": true}`).
        """
        data = (repos_payload or {}).get("data", [])
        claim_set = self.normalize(data)
        signed_count = sum(1 for r in data if r.get("has_signed_commits", False))
        return {
            "adapter_id": self.ADAPTER_ID,
            "endpoint": self._endpoint,
            "repo_count": len(data),
            "signed_commits_repos": signed_count,
            "claims": claim_set.to_dict(),
            "timestamp": self._now().isoformat(),
        }

    def emit_evidence(
        self,
        version_payload: Optional[Dict[str, Any]] = None,
        cert_payload: Optional[Dict[str, Any]] = None,
        repos_payload: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Dict[str, Any]]:
        """Produce all three evidence outputs in one call.

        Returns a dict keyed by `EVIDENCE_OUTPUTS` filenames; callers
        write each value to disk as JSON.
        """
        return {
            "git-server-health.json": self.shape_service_health(version_payload),
            "git-tls-inventory.json": self.shape_tls_inventory(cert_payload),
            "git-repo-inventory.json": self.shape_repo_inventory(repos_payload),
        }

    # ------------------------------------------------------------------
    # 2.6 Evidence packaging & KSI integration
    # ------------------------------------------------------------------

    def generate_evidence_bundle(
        self,
        version_payload: Optional[Dict[str, Any]] = None,
        cert_payload: Optional[Dict[str, Any]] = None,
        repos_payload: Optional[Dict[str, Any]] = None,
    ) -> EvidenceObject:
        """Bundle all three evidence outputs into a single EvidenceObject."""
        conn = self.connect()
        outputs = self.emit_evidence(version_payload, cert_payload, repos_payload)
        claim_set = self.normalize((repos_payload or {}).get("data", []))
        return EvidenceObject(
            ksi_id="KSI-CM-02-uiao-git-server",
            source=self.ADAPTER_ID,
            timestamp=self._now(),
            raw_data={
                "connection": conn.to_dict(),
                "outputs": outputs,
            },
            normalized_data=claim_set.to_dict(),
            provenance={
                "adapter_id": self.ADAPTER_ID,
                "endpoint": self._endpoint,
                "hash": self._hash(outputs),
                "timestamp": self._now().isoformat(),
            },
            freshness_valid=True,
        )

    # ------------------------------------------------------------------
    # Convenience entry point used by `python -m uiao.adapters.conformance_check`.
    # ------------------------------------------------------------------

    def collect_and_align(self) -> Dict[str, Any]:
        claim_set = self.normalize([])
        return {
            "vendor": "Gitea",
            "adapter_id": self.ADAPTER_ID,
            "endpoint": self._endpoint,
            "claims": claim_set.to_dict(),
            "metadata": {
                "source": "uiao-git-server",
                "outputs": list(self.EVIDENCE_OUTPUTS),
                "last_collected": self._now().isoformat(),
            },
        }
