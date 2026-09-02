"""Tests for scripts/publish_release_assets.py.

The point of that script is to keep the download-kit publish inside GitHub's
secondary rate limits, so these tests pin the two things that decide whether it
does: how the sliding-window limiter paces writes, and which gh failures are
worth retrying. Both run on a fake clock, so the suite stays fast even though
the real script deliberately sleeps for minutes.
"""

from __future__ import annotations

import publish_release_assets as pra
import pytest


class FakeClock:
    """Monotonic clock plus sleep, so pacing is testable without waiting."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def make_limiter(per_minute: int) -> tuple[pra.RateLimiter, FakeClock]:
    clock = FakeClock()
    return pra.RateLimiter(per_minute, sleep=clock.sleep, clock=clock.time), clock


class TestRateLimiter:
    def test_admits_up_to_budget_without_sleeping(self):
        limiter, clock = make_limiter(10)
        for _ in range(5):
            assert limiter.acquire(2) == 0.0
            limiter.record(2)
        assert clock.slept == []

    def test_blocks_once_the_window_is_full(self):
        limiter, clock = make_limiter(10)
        for _ in range(5):
            limiter.acquire(2)
            limiter.record(2)
        # The 6th pair does not fit; it must wait for the first to age out.
        waited = limiter.acquire(2)
        assert waited > 0
        assert clock.slept, "expected the limiter to sleep once the window filled"

    def test_window_slides_so_old_writes_stop_counting(self):
        limiter, clock = make_limiter(10)
        limiter.acquire(10)
        limiter.record(10)
        clock.now += 61  # everything ages out
        assert limiter.acquire(10) == 0.0

    def test_sustained_rate_stays_within_budget(self):
        """The property that actually matters: never more than N writes/60s."""
        per_minute = 8
        limiter, clock = make_limiter(per_minute)
        admitted: list[float] = []
        for _ in range(40):
            limiter.acquire(2)
            limiter.record(2)
            admitted.extend([clock.now, clock.now])
        for i, t in enumerate(admitted):
            window = [x for x in admitted[: i + 1] if t - x < 60.0]
            assert len(window) <= per_minute, f"{len(window)} writes inside one 60s window"

    def test_rejects_a_nonsense_budget(self):
        with pytest.raises(ValueError):
            pra.RateLimiter(0)

    def test_cost_larger_than_budget_does_not_deadlock(self):
        limiter, _ = make_limiter(1)
        limiter.acquire(5)  # clamped, must return rather than spin
        limiter.record(1)


class TestIsRetryable:
    def test_detects_the_real_secondary_rate_limit_message(self):
        # Verbatim from the 2026-08-31 failure on main (run 33402423145).
        msg = "You have exceeded a secondary rate limit. Please wait a few minutes before you try again."
        assert pra.is_retryable(msg)

    @pytest.mark.parametrize(
        "msg",
        [
            "API rate limit exceeded",
            "You have triggered an abuse detection mechanism",
            "was submitted too quickly",
            "502 Bad Gateway",
            "503 Service Unavailable",
            "500 Internal Server Error: server error",
            "unexpected EOF",
            "connection reset by peer",
            "Unicorn! (GitHub 500 page)",
        ],
    )
    def test_detects_transient_failures(self, msg):
        assert pra.is_retryable(msg)

    @pytest.mark.parametrize(
        "msg",
        [
            "release not found",
            "HTTP 422: Validation Failed",
            "could not open file: no such file or directory",
            "HTTP 401: Bad credentials",
        ],
    )
    def test_leaves_real_errors_alone(self, msg):
        assert not pra.is_retryable(msg)


class GhRecorder:
    """Stands in for run_gh, recording calls and replaying scripted results."""

    def __init__(self, assets=(), upload_results=None):
        self.calls: list[list[str]] = []
        self._assets = list(assets)
        self._upload_results = dict(upload_results or {})
        self.upload_attempts: dict[str, int] = {}

    def __call__(self, args, dry_run=False):
        self.calls.append(args)
        if args[:2] == ["release", "view"]:
            import json

            return 0, json.dumps({"assets": [{"name": n} for n in self._assets]}), ""
        if args[:2] in (["release", "edit"], ["release", "create"]):
            return 0, "", ""
        if args[:2] == ["release", "upload"]:
            name = args[3].rsplit("/", 1)[-1]
            self.upload_attempts[name] = self.upload_attempts.get(name, 0) + 1
            outcomes = self._upload_results.get(name)
            if outcomes:
                rc, err = outcomes.pop(0)
                return rc, "", err
            return 0, "", ""
        raise AssertionError(f"unexpected gh call: {args}")


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(pra.time, "sleep", lambda _s: None)


def write_files(tmp_path, names):
    out = []
    for n in names:
        p = tmp_path / n
        p.write_bytes(b"x")
        out.append(p)
    return out


class TestPublish:
    def test_publishes_every_asset_and_reports_success(self, tmp_path, monkeypatch, no_sleep):
        gh = GhRecorder(assets=["a.zip"])
        monkeypatch.setattr(pra, "run_gh", gh)
        files = write_files(tmp_path, ["a.zip", "b.docx"])

        rc = pra.publish(
            tag="downloads-latest",
            title="t",
            body="b",
            files=files,
            repo=None,
            per_minute=80,
            dry_run=False,
        )
        assert rc == 0
        uploads = [c for c in gh.calls if c[:2] == ["release", "upload"]]
        assert len(uploads) == 2
        # --clobber is what makes the publish idempotent against a rolling tag.
        assert all("--clobber" in c for c in uploads)

    def test_edits_an_existing_release_rather_than_recreating_it(self, tmp_path, monkeypatch, no_sleep):
        gh = GhRecorder(assets=["a.zip"])
        monkeypatch.setattr(pra, "run_gh", gh)
        pra.publish("downloads-latest", "t", "b", write_files(tmp_path, ["a.zip"]), None, 80, False)
        verbs = [c[1] for c in gh.calls if c[0] == "release"]
        assert "edit" in verbs and "create" not in verbs

    def test_creates_the_release_when_absent(self, tmp_path, monkeypatch, no_sleep):
        def gh(args, dry_run=False):
            if args[:2] == ["release", "view"]:
                return 1, "", "release not found"
            return 0, "", ""

        calls = []

        def recording(args, dry_run=False):
            calls.append(args)
            return gh(args, dry_run)

        monkeypatch.setattr(pra, "run_gh", recording)
        pra.publish("downloads-latest", "t", "b", write_files(tmp_path, ["a.zip"]), None, 80, False)
        create = [c for c in calls if c[:2] == ["release", "create"]]
        assert create, "expected the release to be created when it does not exist"
        assert "--latest=false" in create[0]

    def test_retries_a_rate_limited_asset_then_succeeds(self, tmp_path, monkeypatch, no_sleep):
        gh = GhRecorder(
            assets=[],
            upload_results={"a.zip": [(1, "You have exceeded a secondary rate limit.")]},
        )
        monkeypatch.setattr(pra, "run_gh", gh)
        rc = pra.publish("t", "t", "b", write_files(tmp_path, ["a.zip"]), None, 80, False)
        assert rc == 0
        assert gh.upload_attempts["a.zip"] == 2

    def test_gives_up_after_the_backoff_schedule_and_fails_the_step(self, tmp_path, monkeypatch, no_sleep):
        limit = [(1, "You have exceeded a secondary rate limit.")] * 10
        gh = GhRecorder(assets=[], upload_results={"a.zip": limit})
        monkeypatch.setattr(pra, "run_gh", gh)
        rc = pra.publish("t", "t", "b", write_files(tmp_path, ["a.zip"]), None, 80, False)
        assert rc == 1
        assert gh.upload_attempts["a.zip"] == 1 + len(pra.RETRY_WAITS_SECONDS)

    def test_does_not_retry_a_genuine_error(self, tmp_path, monkeypatch, no_sleep):
        gh = GhRecorder(assets=[], upload_results={"a.zip": [(1, "HTTP 422: Validation Failed")]})
        monkeypatch.setattr(pra, "run_gh", gh)
        rc = pra.publish("t", "t", "b", write_files(tmp_path, ["a.zip"]), None, 80, False)
        assert rc == 1
        assert gh.upload_attempts["a.zip"] == 1, "a validation error must not be retried"

    def test_one_failure_does_not_abandon_the_remaining_assets(self, tmp_path, monkeypatch, no_sleep):
        gh = GhRecorder(assets=[], upload_results={"a.zip": [(1, "HTTP 422: Validation Failed")]})
        monkeypatch.setattr(pra, "run_gh", gh)
        files = write_files(tmp_path, ["a.zip", "b.zip", "c.zip"])
        rc = pra.publish("t", "t", "b", files, None, 80, False)
        assert rc == 1
        assert gh.upload_attempts.get("b.zip") == 1
        assert gh.upload_attempts.get("c.zip") == 1
