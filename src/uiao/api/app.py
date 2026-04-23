"""
impl/src/uiao/impl/api/app.py
------------------------------
UIAO AD Survey API — FastAPI application

Hosted via IIS HttpPlatformHandler on Windows Server 2026.
Entrypoint: deploy/windows-server/run.py (uvicorn)

Auth model:
  Inbound  : Windows Authentication (Kerberos via IIS Negotiate)
  Outbound : MSAL client credentials token for Microsoft Graph API
"""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from .auth.entra_token import EntraTokenProvider
from .routes import auditor, health, orgpath, survey


# ------------------------------------------------------------------
# Application lifespan: initialise shared resources once at startup
# ------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialise Entra token provider (validates env vars at startup,
    # not at first request — surfaces misconfiguration immediately)
    token_provider = EntraTokenProvider.from_environment()
    app.state.token_provider = token_provider

    # Warm the token cache so first real request isn't delayed
    await token_provider.warm_cache()

    yield  # server is live

    # Cleanup (if needed)


# ------------------------------------------------------------------
# Application instance
# ------------------------------------------------------------------
app = FastAPI(
    title="UIAO AD Survey API",
    description=(
        "Active Directory forest archaeological survey and OrgPath "
        "assignment adapter for the UIAO Governance OS. "
        "Canon reference: Appendix F, Appendix C."
    ),
    version="0.1.0",
    docs_url="/api/docs",  # Swagger UI
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ------------------------------------------------------------------
# Middleware
# ------------------------------------------------------------------

# Restrict host header to expected server name
_allowed_hosts = os.environ.get("UIAO_API_ALLOWED_HOSTS", "*").split(",")
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)


# ------------------------------------------------------------------
# Global exception handler — return structured JSON, never stack traces
# ------------------------------------------------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": str(exc) if os.environ.get("UIAO_DEBUG") else "An internal error occurred. Check server logs.",
            "path": str(request.url.path),
        },
    )


# ------------------------------------------------------------------
# Routers
# ------------------------------------------------------------------
app.include_router(health.router, tags=["Health"])
app.include_router(survey.router, prefix="/api/v1/survey", tags=["AD Survey"])
app.include_router(orgpath.router, prefix="/api/v1/orgpath", tags=["OrgPath"])
app.include_router(auditor.router, prefix="/api/auditor", tags=["Auditor API"])
