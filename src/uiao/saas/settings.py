"""
uiao.saas.settings
------------------
Environment-driven configuration for the UIAO Azure SaaS runtime.

All settings are read from ``UIAO_SAAS_*`` environment variables (the
container injects these from Key Vault references / Container Apps secrets).
Every field has a safe default so importing the package and constructing the
ASGI app never fails on a fresh machine — misconfiguration surfaces as a
runtime 401/403, not an import crash.
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SaasSettings(BaseSettings):
    """Configuration for the multi-tenant SaaS control + data plane."""

    model_config = SettingsConfigDict(
        env_prefix="UIAO_SAAS_",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Identity / Entra multi-tenant app registration -------------------
    #: The UIAO multi-tenant app registration (application/client) ID that
    #: customer tenants grant admin consent to.
    app_client_id: str = Field(default="")
    #: The publisher (home) tenant that owns the multi-tenant app + control
    #: plane. Control-plane admin tokens must originate from this tenant.
    publisher_tenant_id: str = Field(default="")
    #: The audience (``aud``) inbound data-plane tokens must carry — the
    #: Application ID URI of the UIAO API (e.g. ``api://uiao``).
    api_audience: str = Field(default="")
    #: Comma-separated allowlist of customer tenant GUIDs permitted to
    #: authenticate. ``"*"`` accepts any tenant that has a registered,
    #: ACTIVE :class:`~uiao.saas.tenant.Tenant` record (the normal SaaS
    #: case — the tenant registry is the gate, not a static allowlist).
    allowed_issuer_tenants: str = Field(default="*")
    #: Sovereign cloud — ``commercial`` (also GCC-Moderate per ADR-033),
    #: ``gcc-high`` or ``dod``. Selects login / Graph / ARM endpoints.
    cloud: str = Field(default="commercial")

    # --- Data plane backing stores ---------------------------------------
    #: SQLAlchemy async URL for the tenant registry + evidence state, e.g.
    #: ``postgresql+asyncpg://user@host/uiao``. Empty → in-memory registry
    #: (dev/test only; not durable).
    database_url: str = Field(default="")
    #: When true the Postgres connection authenticates with a Microsoft Entra
    #: access token (passwordless, ADR-116) instead of a password embedded in
    #: ``database_url``. The Container App's managed identity must be bound as
    #: the server's Entra administrator.
    database_use_entra_auth: bool = Field(default=False)
    #: Entra principal name to connect as when ``database_use_entra_auth`` is
    #: set — typically the managed identity's name. If empty, the user encoded
    #: in ``database_url`` is used.
    database_entra_user: str = Field(default="")
    #: When true the Postgres connection authenticates with an AWS RDS IAM
    #: token (passwordless, ADR-117) instead of a password. The ECS task role
    #: must hold ``rds-db:connect`` on the database user. Mutually exclusive
    #: with ``database_use_entra_auth``.
    database_use_aws_iam_auth: bool = Field(default=False)
    #: AWS region for RDS IAM token signing + the per-tenant stamp clients.
    aws_region: str = Field(default="")
    #: S3 bucket holding per-tenant evidence-bundle prefixes (AWS stamp).
    aws_s3_bucket: str = Field(default="")
    #: Secrets Manager name prefix for per-tenant secret scopes (AWS stamp).
    aws_secrets_prefix: str = Field(default="uiao")
    #: Azure Key Vault URI for per-tenant secrets (client secrets / certs).
    key_vault_uri: str = Field(default="")
    #: Azure Blob Storage account URL for evidence bundles / artifacts.
    storage_account_url: str = Field(default="")

    # --- Operational toggles ---------------------------------------------
    #: When true the control-plane provisioning endpoints are exposed.
    provisioning_enabled: bool = Field(default=True)
    #: When true, per-tenant request-rate limiting is enforced on the data
    #: plane using the per-plan quota table (:mod:`uiao.saas.quotas`).
    rate_limiting_enabled: bool = Field(default=True)
    #: Length of the rate-limit window in seconds.
    rate_limit_window_seconds: int = Field(default=60)
    #: When set, rate limiting uses a **shared Redis store** for a
    #: globally-exact limit across replicas (ADR-118) instead of the in-process
    #: per-replica limiter. E.g. ``redis://uiao-cache:6379/0``. Requires the
    #: ``[redis]`` extra.
    rate_limit_redis_url: str = Field(default="")
    #: When true, control-plane lifecycle actions are written to the audit
    #: trail and the ``GET /control/v1/audit`` endpoint is exposed.
    audit_enabled: bool = Field(default=True)
    #: When true, tenant onboarding **executes** the Azure resource stamp
    #: (Postgres schema / Blob container / Key Vault scope) via the
    #: AzureStampExecutor. Default false → plans the stamp without touching
    #: Azure (dry-run), even when backing resources are configured.
    stamp_execution_enabled: bool = Field(default=False)
    #: When true (dev/test ONLY) inbound tokens are accepted without JWKS
    #: signature verification. Never enable in production.
    insecure_allow_unsigned_tokens: bool = Field(default=False)
    #: Paths exempt from tenant resolution (health probes, docs, control
    #: plane). Comma-separated path prefixes.
    public_path_prefixes: str = Field(
        default="/healthz,/readyz,/health,/api/docs,/api/redoc,/api/openapi.json,/control",
    )

    # --- Derived helpers --------------------------------------------------
    def allowed_tenants(self) -> set[str] | None:
        """Return the explicit issuer allowlist, or ``None`` for ``"*"``."""
        value = self.allowed_issuer_tenants.strip()
        if not value or value == "*":
            return None
        return {t.strip() for t in value.split(",") if t.strip()}

    def public_prefixes(self) -> tuple[str, ...]:
        """Return the request-path prefixes exempt from tenant resolution."""
        return tuple(p.strip() for p in self.public_path_prefixes.split(",") if p.strip())

    def has_database(self) -> bool:
        """True when a durable Postgres registry is configured."""
        return bool(self.database_url.strip())


__all__ = ["SaasSettings"]
