"""
uiao.saas.asgi
-------------
Container entrypoint for the UIAO Azure SaaS runtime.

``uvicorn uiao.saas.asgi:app`` boots the existing ``uiao.api`` data plane
with the SaaS control plane + tenant-resolution middleware attached. All
configuration comes from ``UIAO_SAAS_*`` / ``UIAO_ENTRA_*`` environment
variables, which Azure Container Apps injects from Key Vault references and
secrets (see ``deploy/azure/``).

Importing this module is side-effect-safe: it builds the app object but does
not open any network connections until uvicorn invokes the lifespan at
serve time.
"""

from __future__ import annotations

from .app import build_saas_app

app = build_saas_app()

__all__ = ["app"]
