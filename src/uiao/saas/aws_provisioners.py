"""
uiao.saas.aws_provisioners
-------------------------
AWS-backed :class:`~uiao.saas.azure_stamp.Provisioner` implementations and the
:func:`build_stamp_executor` factory (ADR-117) — the AWS analogue of
:mod:`uiao.saas.azure_provisioners`.

Gated behind the ``[aws]`` extra (SQLAlchemy async + asyncpg + boto3) and only
imported by :func:`build_stamp_executor`, which is itself only called when
``UIAO_SAAS_STAMP_EXECUTION_ENABLED`` is set. The rest of ``uiao.saas`` — and
the blocking CI test job — never needs these dependencies.

boto3 clients use the default credential chain, so on ECS/Fargate they
transparently assume the task role and locally fall back to the developer's
``AWS_PROFILE`` / environment credentials. The synchronous boto3 calls are run
off the event loop via :func:`asyncio.to_thread`.
"""

from __future__ import annotations

import asyncio

import boto3
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .aws_stamp import AwsStampExecutor, require_safe_namespace


class PostgresSchemaProvisioner:
    """Create / archive a per-tenant Postgres schema (RDS).

    Identical SQL to the Azure provisioner — the schema-isolation plane is
    cloud-neutral — but kept local so the ``[aws]`` path never imports the
    Azure SDK.
    """

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


class S3PrefixProvisioner:
    """Create / archive a per-tenant S3 key prefix via a marker object."""

    def __init__(self, bucket: str, *, region: str = "", client=None) -> None:  # type: ignore[no-untyped-def]
        self._bucket = bucket
        self._client = client or boto3.client("s3", region_name=region or None)

    async def create(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        await asyncio.to_thread(self._client.put_object, Bucket=self._bucket, Key=f"{ns}/.uiao-provisioned", Body=b"1")

    async def archive(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        # Retain evidence; drop a marker object rather than deleting the prefix.
        await asyncio.to_thread(self._client.put_object, Bucket=self._bucket, Key=f"{ns}/.uiao-archived", Body=b"1")


class SecretsManagerScopeProvisioner:
    """Establish / revoke a per-tenant Secrets Manager scope marker."""

    def __init__(self, prefix: str = "uiao", *, region: str = "", client=None) -> None:  # type: ignore[no-untyped-def]
        self._prefix = prefix.rstrip("/")
        self._client = client or boto3.client("secretsmanager", region_name=region or None)

    def _name(self, ns: str) -> str:
        return f"{self._prefix}/{ns}/provisioned"

    async def create(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        await asyncio.to_thread(self._client.create_secret, Name=self._name(ns), SecretString="1")

    async def archive(self, namespace: str) -> None:
        ns = require_safe_namespace(namespace)
        await asyncio.to_thread(
            self._client.delete_secret,
            SecretId=self._name(ns),
            RecoveryWindowInDays=7,
        )


def build_stamp_executor(settings) -> AwsStampExecutor | None:  # type: ignore[no-untyped-def]
    """Build an :class:`AwsStampExecutor` from ``settings``.

    Returns ``None`` if no backing resources are configured at all (so the
    caller falls back to the dry-run executor).
    """
    region = getattr(settings, "aws_region", "").strip()
    schema = s3 = secrets = None

    if getattr(settings, "database_url", "").strip():
        schema = PostgresSchemaProvisioner(settings.database_url)

    bucket = getattr(settings, "aws_s3_bucket", "").strip()
    if bucket:
        s3 = S3PrefixProvisioner(bucket, region=region)

    prefix = getattr(settings, "aws_secrets_prefix", "").strip()
    if prefix:
        secrets = SecretsManagerScopeProvisioner(prefix, region=region)

    if schema is None and s3 is None and secrets is None:
        return None
    return AwsStampExecutor(schema=schema, bucket=s3, secrets=secrets)


__all__ = [
    "PostgresSchemaProvisioner",
    "S3PrefixProvisioner",
    "SecretsManagerScopeProvisioner",
    "build_stamp_executor",
]
