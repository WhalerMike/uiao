"""Live-path demonstration for the reporting-egress actuator (ADR-128).

Spins up a local HTTP server and drives the one wired destination
(``cisa-sbom``) through the full gated path to a real ``SUBMITTED`` result.
Proves that:

    * an unconfigured driver (no endpoint) still blocks a live submission, and
    * a configured driver + live + approval transmits and returns the server's
      receipt.

Uses only the standard library (``http.server``) — no network egress, no new
dependency.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

from uiao.reporting_egress import (
    Approval,
    Destination,
    Disposition,
    Submission,
    submit,
)
from uiao.reporting_egress.drivers import CisaSbomDriver


class _Handler(BaseHTTPRequestHandler):
    received: dict = {}

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        length = int(self.headers.get("Content-Length", "0"))
        _Handler.received = {
            "body": self.rfile.read(length),
            "artifact_type": self.headers.get("X-UIAO-Artifact-Type"),
            "path": self.path,
        }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"accepted","id":"CISA-RCPT-42"}')

    def log_message(self, *args: object) -> None:  # silence test server logs
        return


def _approval() -> Approval:
    return Approval(
        approver="jane.isso",
        approved_at="2026-07-09T10:48:00+00:00",
        operation="submit:cisa-sbom",
    )


@pytest.fixture()
def test_server():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/bod-26-04/sbom"
    finally:
        server.shutdown()
        server.server_close()


def test_default_driver_unconfigured_blocks(tmp_path: Path) -> None:
    """With no endpoint the driver is unconfigured -> live submit is blocked."""
    artifact = tmp_path / "sbom.json"
    artifact.write_text('{"bomFormat": "CycloneDX"}', encoding="utf-8")
    drv = CisaSbomDriver()  # no endpoint, no env
    assert drv.configured is False
    result = submit(
        Submission(Destination.CISA_SBOM, artifact, "cyclonedx-sbom"),
        live=True,
        approval=_approval(),
        driver=drv,
    )
    assert result.disposition is Disposition.BLOCKED
    assert "not configured" in result.reason.lower()


def test_live_submit_against_test_server(tmp_path: Path, test_server: str) -> None:
    """Configured driver + live + approval transmits and returns the receipt."""
    artifact = tmp_path / "sbom.json"
    artifact.write_text('{"bomFormat": "CycloneDX", "version": 1}', encoding="utf-8")

    drv = CisaSbomDriver(endpoint=test_server)
    assert drv.configured is True

    result = submit(
        Submission(Destination.CISA_SBOM, artifact, "cyclonedx-sbom"),
        live=True,
        approval=_approval(),
        driver=drv,
    )

    assert result.disposition is Disposition.SUBMITTED
    assert result.transmitted
    assert result.receipt is not None
    assert result.receipt["status"] == 200
    assert "CISA-RCPT-42" in result.receipt["response"]
    assert result.approver == "jane.isso"

    # The server actually received the artifact bytes and the type header.
    assert _Handler.received["artifact_type"] == "cyclonedx-sbom"
    assert b"CycloneDX" in _Handler.received["body"]
    assert _Handler.received["path"] == "/bod-26-04/sbom"
