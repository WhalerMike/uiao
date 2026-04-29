"""
deploy/windows-server/run.py
-----------------------------
Uvicorn entrypoint launched by IIS HttpPlatformHandler.

IIS sets %HTTP_PLATFORM_PORT% to a dynamic port number.
This script reads that port and starts uvicorn bound to it.
IIS then reverse-proxies all HTTPS traffic to this port.

Key points:
  - workers=1: HttpPlatformHandler manages one Python process.
    If you need multiple workers, use multiple IIS app pools.
  - host="127.0.0.1": Only accept connections from IIS on loopback.
    Never bind to 0.0.0.0 — the TLS and auth layer is IIS.
  - access_log=False: IIS W3C logs are the authoritative access log.
    Uvicorn access log would duplicate with slightly different format.
"""

import os
import sys

# Ensure the impl package is importable
# (when running from C:\inetpub\uiao-api, the symlink/copy of impl is at
# C:\srv\uiao\impl — add it to sys.path)
workspace = os.environ.get("UIAO_WORKSPACE_ROOT", r"C:\srv\uiao")
impl_src = os.path.join(workspace, "impl", "src")
if impl_src not in sys.path:
    sys.path.insert(0, impl_src)

import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("UIAO_API_PORT", os.environ.get("HTTP_PLATFORM_PORT", "8000")))
    log_level = os.environ.get("UIAO_LOG_LEVEL", "info").lower()

    uvicorn.run(
        "uiao.impl.api.app:app",
        host="127.0.0.1",   # loopback only — IIS handles external TLS
        port=port,
        workers=1,
        log_level=log_level,
        access_log=False,   # IIS W3C logs are authoritative
        proxy_headers=True, # Trust X-Forwarded-* from IIS
        forwarded_allow_ips="127.0.0.1",
    )
