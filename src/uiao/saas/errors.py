"""
uiao.saas.errors
---------------
RFC 9457 *Problem Details* (``application/problem+json``) for the SaaS planes.

Every error the SaaS data plane and control plane emit is rendered as a
machine-readable problem document so clients can branch on a stable shape
instead of scraping prose. The document carries the standard members
(``type``, ``title``, ``status``, ``detail``, ``instance``) plus two UIAO
extensions:

* ``error`` — a stable machine code (e.g. ``tenant_not_onboarded``,
  ``rate_limited``). Clients branch on this, never on ``title``/``detail``.
* ``tenant`` — the resolved tenant id, when one is known.

:func:`problem_response` builds the response for the data-plane middleware
(which sits *below* FastAPI's exception handling); :func:`install_problem_handlers`
registers handlers so control-plane ``HTTPException``\\s and unhandled errors
render in the same shape. Both paths therefore produce identical documents.

Pure stdlib + Starlette — no ``[saas]`` dependency.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import JSONResponse

#: The media type mandated by RFC 9457 for problem documents.
PROBLEM_MEDIA_TYPE = "application/problem+json"

#: Default ``type`` URI. RFC 9457 permits ``about:blank`` when there is no
#: dedicated human-readable type page; the ``error`` extension carries the
#: machine code instead.
DEFAULT_TYPE = "about:blank"

#: Reason-phrase titles for the statuses the SaaS planes emit. ``title`` is a
#: human-readable summary that, per RFC 9457, should not change between
#: occurrences of the same ``type``.
_TITLES: dict[int, str] = {
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden",
    404: "Not Found",
    409: "Conflict",
    422: "Unprocessable Entity",
    429: "Too Many Requests",
    500: "Internal Server Error",
    503: "Service Unavailable",
}


class ProblemDetail(BaseModel):
    """An RFC 9457 problem document (used for OpenAPI response schemas)."""

    type: str = Field(default=DEFAULT_TYPE, description="Problem type URI.")
    title: str = Field(description="Short, human-readable summary of the problem type.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(default="", description="Human-readable explanation specific to this occurrence.")
    instance: str = Field(default="", description="URI reference identifying this occurrence (the request path).")
    error: str = Field(default="", description="Stable machine-readable error code; branch on this.")
    tenant: str | None = Field(default=None, description="Resolved tenant id, when known.")


def title_for(status_code: int) -> str:
    """Return the canonical title for ``status_code`` (falls back to 'Error')."""
    return _TITLES.get(status_code, "Error")


def problem_dict(
    status_code: int,
    *,
    code: str = "",
    detail: str = "",
    instance: str = "",
    title: str | None = None,
    type_: str = DEFAULT_TYPE,
    **extensions: Any,
) -> dict[str, Any]:
    """Build a problem-document body as a plain dict (handlers + responses)."""
    body: dict[str, Any] = {
        "type": type_,
        "title": title or title_for(status_code),
        "status": status_code,
    }
    if detail:
        body["detail"] = detail
    if instance:
        body["instance"] = instance
    if code:
        body["error"] = code
    for key, value in extensions.items():
        if value is not None:
            body[key] = value
    return body


def problem_response(
    status_code: int,
    *,
    code: str = "",
    detail: str = "",
    instance: str = "",
    title: str | None = None,
    type_: str = DEFAULT_TYPE,
    headers: dict[str, str] | None = None,
    **extensions: Any,
) -> JSONResponse:
    """Return a ``application/problem+json`` :class:`JSONResponse`."""
    body = problem_dict(
        status_code,
        code=code,
        detail=detail,
        instance=instance,
        title=title,
        type_=type_,
        **extensions,
    )
    return JSONResponse(
        status_code=status_code,
        content=body,
        media_type=PROBLEM_MEDIA_TYPE,
        headers=headers,
    )


def install_problem_handlers(app: Any) -> None:
    """Register problem+json exception handlers on a FastAPI/Starlette app.

    Converts ``HTTPException`` (raised by the control-plane routes and FastAPI
    dependencies) into the same problem document the data-plane middleware
    emits, so the whole SaaS surface speaks one error dialect. The handler is
    idempotent — re-attaching ``attach_saas`` does not stack handlers.
    """
    from starlette.exceptions import HTTPException as StarletteHTTPException

    async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # ``detail`` may already be a machine code from the route; otherwise
        # synthesise one from the status so clients always get an ``error``.
        detail = exc.detail if isinstance(exc.detail, str) else ""
        code = _code_for_status(exc.status_code)
        return problem_response(
            exc.status_code,
            code=code,
            detail=detail,
            instance=request.url.path,
            headers=dict(exc.headers or {}),
        )

    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)


def _code_for_status(status_code: int) -> str:
    """Map a status to a default machine code used when a route lacks one."""
    return {
        400: "bad_request",
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
        429: "rate_limited",
        503: "unavailable",
    }.get(status_code, "error")


__all__ = [
    "PROBLEM_MEDIA_TYPE",
    "ProblemDetail",
    "problem_dict",
    "problem_response",
    "install_problem_handlers",
    "title_for",
]
