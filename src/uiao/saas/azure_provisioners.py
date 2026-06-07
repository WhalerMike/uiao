"""
uiao.saas.azure_provisioners
---------------------------
Azure-backed :class:`~uiao.saas.azure_stamp.Provisioner` implementations and
the :func:`build_stamp_executor` factory (ADR-096).

Gated behind the ``[saas]`` extra (SQLAlchemy async + the Azure SDKs) and only
imported by :func:`build_stamp_executor`, which is itself only called when
``UIAO_SAAS_STAMP_EXECUTION_ENABLED`` is set. The rest of ``uiao.saas`` — and
the blocking CI test job — never needs these dependencies.

All three planes authenticate with a single ``DefaultAzureCredential`` so that
in Azure Container Apps they transparently use the workload's managed identity
(honouring ``AZURE_CLIENT_ID``), and locally fall back to the developer's
``az login`` / environment credential.
"""

from __future__ import annotations

import sqlalchemy as sa
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
from azure.storage.blob.aio import BlobServiceClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .azure_stamp import AzureStampExecutor, require_safe_namespace


class PostgresSchemaProvisioner:
    """Create / archive a per-tenant Postgres schema."""

    def __init__(self, database_url: str, *, engine: AsyncEngine | None = None) -> None:
        self._engine: AsyncEngine = engine or create_async_engine(database_url, pool_pre_ping=True)

    async def create(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        async with self._engine.begin() as conn:
            await conn.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{ns}"'))

    async def archive(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        # Non-destructive offboarding: rename rather than drop, so evidence is
        # retained per policy. Idempotent — no-op if already archived/absent.
        guarded_rename = (
            "DO $$ BEGIN "
            f"IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = '{ns}') THEN "
            f'EXECUTE \'ALTER SCHEMA "{ns}" RENAME TO "{ns}__archived"\'; '
            "END IF; END $$"
        )
        async with self._engine.begin() as conn:
            await conn.execute(sa.text(guarded_rename))

    async def dispose(self) -> None:
        await self._engine.dispose()


class BlobContainerProvisioner:
    """Create / delete a per-tenant Blob container."""

    def __init__(self, account_url: str, credential: DefaultAzureCredential) -> None:
        self._account_url = account_url
        self._credential = credential

    async def create(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        async with BlobServiceClient(self._account_url, credential=self._credential) as svc:
            container = svc.get_container_client(ns)
            if not await container.exists():
                await container.create_container()

    async def archive(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        async with BlobServiceClient(self._account_url, credential=self._credential) as svc:
            container = svc.get_container_client(ns)
            if await container.exists():
                # Mark archived; retain the data (do not delete evidence).
                await container.set_container_metadata({"uiao_status": "archived"})


class KeyVaultSecretProvisioner:
    """Establish / revoke a per-tenant Key Vault secret scope."""

    def __init__(self, vault_uri: str, credential: DefaultAzureCredential) -> None:
        self._vault_uri = vault_uri
        self._credential = credential

    async def create(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        async with SecretClient(self._vault_uri, credential=self._credential) as client:
            await client.set_secret(f"{ns}-provisioned", "1")

    async def archive(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        async with SecretClient(self._vault_uri, credential=self._credential) as client:
            await client.delete_secret(f"{ns}-provisioned")


def build_stamp_executor(settings) -> AzureStampExecutor | None:  # type: ignore[no-untyped-def]
    """Build an :class:`AzureStampExecutor` from ``settings``.

    Returns ``None`` if no backing resources are configured at all (so the
    caller falls back to the dry-run executor). A single shared
    ``DefaultAzureCredential`` is used for the Blob + Key Vault planes.
    """
    schema = container = secrets = None

    if getattr(settings, "database_url", "").strip():
        schema = PostgresSchemaProvisioner(settings.database_url)

    storage_url = getattr(settings, "storage_account_url", "").strip()
    vault_uri = getattr(settings, "key_vault_uri", "").strip()
    if storage_url or vault_uri:
        credential = DefaultAzureCredential()
        if storage_url:
            container = BlobContainerProvisioner(storage_url, credential)
        if vault_uri:
            secrets = KeyVaultSecretProvisioner(vault_uri, credential)

    if schema is None and container is None and secrets is None:
        return None
    return AzureStampExecutor(schema=schema, container=container, secrets=secrets)


__all__ = [
    "PostgresSchemaProvisioner",
    "BlobContainerProvisioner",
    "KeyVaultSecretProvisioner",
    "build_stamp_executor",
]
