"""The gated submission engine for the reporting-egress actuator (ADR-128).

The single public entry point is :func:`submit`. Its contract encodes the
ADR-128 invariants directly:

    * ``live=False`` (the default) -> ``PLANNED`` (dry-run; nothing transmits).
    * ``live=True`` without a valid ``Approval`` -> ``BLOCKED`` (L3 gate).
    * ``live=True`` + approval, driver ``configured=False`` -> ``BLOCKED``
      ("endpoint not configured"; the scaffold never simulates a send).
    * ``live=True`` + approval + configured driver + clean validation
      -> ``SUBMITTED`` (the only path that transmits).

There is no code path that transmits without both a live flag and an approval
token — i.e. no autonomous (L4) submission (ADR-128 §3).
"""

from __future__ import annotations

from uiao.reporting_egress.drivers import EgressDriver, get_driver
from uiao.reporting_egress.models import (
    Approval,
    Disposition,
    Submission,
    SubmissionResult,
)


def submit(
    submission: Submission,
    *,
    live: bool = False,
    approval: Approval | None = None,
    driver: EgressDriver | None = None,
) -> SubmissionResult:
    """Plan or perform a gated outward submission.

    Args:
        submission: what to send, and where.
        live: if False (default), validate and plan only — never transmit.
        approval: the L3 human-approval token; required for any live send.
        driver: optional driver override (test/injection); defaults to the
            registered driver for ``submission.destination``.

    Returns:
        A :class:`SubmissionResult` — always returned, never raised, so callers
        get an auditable disposition for every attempt.
    """
    drv = driver if driver is not None else get_driver(submission.destination)
    problems = tuple(drv.validate(submission))

    # --- Dry-run (default): validate and plan, transmit nothing. -----------
    if not live:
        reason = "dry-run: validated, not transmitted" if not problems else "dry-run: validation problems found"
        return SubmissionResult(
            destination=submission.destination,
            disposition=Disposition.PLANNED,
            reason=reason,
            artifact_path=submission.artifact_path,
            problems=problems,
        )

    # --- L3 gate: a live submission requires a valid human approval. -------
    if approval is None or not approval.is_valid():
        return SubmissionResult(
            destination=submission.destination,
            disposition=Disposition.BLOCKED,
            reason="L3 human approval required for a live submission",
            artifact_path=submission.artifact_path,
            problems=problems,
        )

    # --- Refuse to send a malformed artifact. ------------------------------
    if problems:
        return SubmissionResult(
            destination=submission.destination,
            disposition=Disposition.BLOCKED,
            reason="submission failed validation",
            artifact_path=submission.artifact_path,
            problems=problems,
            approver=approval.approver,
        )

    # --- No live endpoint wired -> block, never simulate a send. -----------
    if not drv.configured:
        return SubmissionResult(
            destination=submission.destination,
            disposition=Disposition.BLOCKED,
            reason=("destination endpoint not configured (scaffold — no live endpoint wired; ADR-128 §6)"),
            artifact_path=submission.artifact_path,
            approver=approval.approver,
        )

    # --- The only transmitting path: live + approved + configured + clean. -
    receipt = drv.transmit(submission)
    return SubmissionResult(
        destination=submission.destination,
        disposition=Disposition.SUBMITTED,
        reason="submitted to configured live endpoint",
        artifact_path=submission.artifact_path,
        receipt=receipt,
        approver=approval.approver,
    )
