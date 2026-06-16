"""
uiao.service.windows_service
-----------------------------
Windows Service wrapper for the UIAO governance API (uiao.api.app).

Registers as the 'UIAOService' Windows service. Appears in Services.msc,
responds to sc.exe start/stop/query, and survives without IIS running.
IIS remains the TLS terminator and Windows Auth layer — the service binds
to a fixed loopback port that the IIS reverse proxy forwards to.

Usage (run as Administrator):
    python -m uiao.service install    # register service (use --startup=auto)
    python -m uiao.service start      # start immediately
    python -m uiao.service stop       # graceful stop
    python -m uiao.service remove     # unregister
    python -m uiao.service debug      # run interactively (Ctrl+C to stop)

Port: UIAO_SERVICE_PORT env var (default 8001). IIS web.config must
      proxy to the same port (replace %HTTP_PLATFORM_PORT% with this value
      and remove the httpPlatform handler — see deploy/windows-server/).

Requires: pip install "uiao[api,service]"
"""

from __future__ import annotations

import logging
import os
import sys
import threading

logger = logging.getLogger(__name__)

SERVICE_NAME = "UIAOService"
SERVICE_DISPLAY_NAME = "UIAO Governance API"
SERVICE_DESCRIPTION = (
    "UIAO organizational governance API. Provides the OrgPath web console, "
    "AD assessment endpoints, and drift reporting. Reverse-proxied by IIS."
)

# ---------------------------------------------------------------------------
# Guard: pywin32 is only available on Windows and only in the [service] extra.
# Importing this module on Linux/macOS (e.g. in CI) must not crash.
# ---------------------------------------------------------------------------
try:
    import win32event
    import win32service
    import win32serviceutil

    _WIN32_AVAILABLE = True
except ImportError:
    _WIN32_AVAILABLE = False


def _get_port() -> int:
    return int(os.environ.get("UIAO_SERVICE_PORT", "8001"))


def _get_log_level() -> str:
    return os.environ.get("UIAO_LOG_LEVEL", "info").lower()


# ---------------------------------------------------------------------------
# Uvicorn runner — runs in a daemon thread; stopped via a threading.Event
# ---------------------------------------------------------------------------


def _run_uvicorn(stop_event: threading.Event) -> None:
    """Start uvicorn; block until stop_event is set, then initiate shutdown."""
    import uvicorn  # lazy — guarded by [api] extra

    port = _get_port()
    log_level = _get_log_level()

    config = uvicorn.Config(
        "uiao.api.app:app",
        host="127.0.0.1",  # loopback only — IIS handles external TLS
        port=port,
        workers=1,
        log_level=log_level,
        access_log=False,  # IIS W3C logs are authoritative
        proxy_headers=True,
        forwarded_allow_ips="127.0.0.1",
    )
    server = uvicorn.Server(config)

    # Poll stop_event every second; when set, tell uvicorn to exit cleanly.
    def _watch_stop() -> None:
        stop_event.wait()
        server.handle_exit(sig=None, frame=None)  # type: ignore[arg-type]

    watcher = threading.Thread(target=_watch_stop, daemon=True)
    watcher.start()

    server.run()  # blocks until handle_exit() is called


# ---------------------------------------------------------------------------
# Windows Service class — only defined when pywin32 is available
# ---------------------------------------------------------------------------

if _WIN32_AVAILABLE:

    class UIAOService(win32serviceutil.ServiceFramework):
        _svc_name_ = SERVICE_NAME
        _svc_display_name_ = SERVICE_DISPLAY_NAME
        _svc_description_ = SERVICE_DESCRIPTION

        def __init__(self, args: list[str]) -> None:
            super().__init__(args)
            self._stop_event = win32event.CreateEvent(None, 0, 0, None)
            self._thread_stop = threading.Event()
            self._thread: threading.Thread | None = None

        def SvcDoRun(self) -> None:
            """Called by the SCM when the service starts."""
            import servicemanager  # pywin32

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )
            self._thread = threading.Thread(
                target=_run_uvicorn,
                args=(self._thread_stop,),
                daemon=True,
                name="uvicorn-main",
            )
            self._thread.start()

            # Block until SCM sends a stop signal.
            win32event.WaitForSingleObject(self._stop_event, win32event.INFINITE)

        def SvcStop(self) -> None:
            """Called by the SCM when the service is asked to stop."""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self._thread_stop.set()
            win32event.SetEvent(self._stop_event)
            if self._thread:
                self._thread.join(timeout=15)


# ---------------------------------------------------------------------------
# __main__ — delegate to win32serviceutil for install/start/stop/remove/debug
# ---------------------------------------------------------------------------


def main() -> None:
    if not _WIN32_AVAILABLE:
        print(
            "pywin32 is not installed. Install it with:\n"
            '    pip install "uiao[service]"\n'
            "The [service] extra is only meaningful on Windows.",
            file=sys.stderr,
        )
        sys.exit(1)

    if len(sys.argv) == 1:
        # No arguments — running from SCM directly (normal service start).
        import servicemanager

        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(UIAOService)  # type: ignore[name-defined]
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(UIAOService)  # type: ignore[name-defined]


if __name__ == "__main__":
    main()
