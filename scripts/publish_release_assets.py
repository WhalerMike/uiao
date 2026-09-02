#!/usr/bin/env python3
"""Publish download-kit assets to a rolling GitHub release, within the API's limits.

Why this exists instead of softprops/action-gh-release's own upload
-------------------------------------------------------------------
That action uploads with `Promise.all(files.map(uploadFile))` -- every asset
concurrently -- and with `overwrite_files` each asset is a DELETE followed by
an UPLOAD. This repo publishes ~104 assets, so a deploy fired roughly 208
content-generating requests within about fifteen seconds.

GitHub's documented secondary rate limits are:

  * no more than 80 content-generating requests per minute,
  * no more than 500 content-generating requests per hour,
  * no more than 100 concurrent requests.

The concurrent burst breached the first and third by roughly an order of
magnitude. It did not fail every time -- secondary limits are enforced with
some slack -- which is why this survived as long as it did, and why the
failures looked random. On 2026-08-31 it failed with:

    You have exceeded a secondary rate limit.

The site itself was never at risk (the publish step is `continue-on-error`
precisely so a Releases API problem cannot take the Pages deploy with it), but
the download assets go stale until a deploy gets through.

So: upload serially, pace the writes against a sliding window sized from the
documented per-minute budget, and back off and retry when GitHub says to. The
run gets slower -- a few minutes rather than fifteen seconds -- which is the
correct trade for a step that publishes ~1 GB of assets and whose failure mode
is stale public downloads.

`gh` does the actual transfer so that asset naming, MIME types and multipart
upload stay identical to what the action produced: both hand GitHub the bare
basename and let the server normalise it. That matters because the published
Download page links assets by their normalised names.

Usage:
    python scripts/publish_release_assets.py --tag downloads-latest \
        --title "Download Kits — latest" --body-file notes.md FILE [FILE ...]
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import subprocess
import sys
import time
from pathlib import Path

# GitHub's documented ceiling is 80 content-generating requests per minute.
# Sit deliberately under it: the same account also spends this budget on the
# web UI and on any other workflow running at the same time, and a deploy that
# takes an extra minute costs far less than one that leaves the downloads
# stale.
DEFAULT_WRITES_PER_MINUTE = 55

# Backoff schedule for a rate-limited or 5xx-failed asset. GitHub asks callers
# to "wait a few minutes"; these are minutes, not seconds, on purpose.
RETRY_WAITS_SECONDS = (60, 180, 420)

# Substrings that mark a failure as worth retrying rather than fatal. Matched
# case-insensitively against gh's stderr.
RETRYABLE_MARKERS = (
    "secondary rate limit",
    "rate limit",
    "abuse detection",
    "was submitted too quickly",
    "server error",
    "bad gateway",
    "service unavailable",
    "timeout",
    "timed out",
    "connection reset",
    "unexpected eof",
    "unicorn",
)


class RateLimiter:
    """Sliding-window limiter over content-generating requests.

    Tracks the timestamp of each write in the last 60 seconds and blocks until
    admitting `cost` more would stay within `per_minute`. A sliding window
    rather than a fixed delay because the writes are not uniform: deleting an
    asset is quick, uploading a 400 MB zip is not, and a fixed sleep would
    either throttle the slow ones needlessly or let a run of fast ones burst.
    """

    def __init__(self, per_minute: int, sleep=time.sleep, clock=time.monotonic) -> None:
        if per_minute < 1:
            raise ValueError("per_minute must be >= 1")
        self.per_minute = per_minute
        self._sleep = sleep
        self._clock = clock
        self._writes: collections.deque[float] = collections.deque()

    def _evict(self, now: float) -> None:
        while self._writes and now - self._writes[0] >= 60.0:
            self._writes.popleft()

    def acquire(self, cost: int) -> float:
        """Block until `cost` writes fit in the window. Returns seconds slept."""
        if cost > self.per_minute:
            # A single asset can never cost more than the whole budget today
            # (delete + upload = 2), but do not deadlock if that ever changes.
            cost = self.per_minute
        slept = 0.0
        while True:
            now = self._clock()
            self._evict(now)
            if len(self._writes) + cost <= self.per_minute:
                break
            # Wait until the oldest write ages out of the window.
            wait = 60.0 - (now - self._writes[0]) + 0.05
            self._sleep(wait)
            slept += wait
        return slept

    def record(self, cost: int) -> None:
        now = self._clock()
        self._evict(now)
        self._writes.extend([now] * cost)


def is_retryable(stderr: str) -> bool:
    low = stderr.lower()
    return any(marker in low for marker in RETRYABLE_MARKERS)


def run_gh(args: list[str], dry_run: bool = False) -> tuple[int, str, str]:
    if dry_run:
        print(f"    [dry-run] gh {' '.join(args)}")
        return 0, "", ""
    try:
        proc = subprocess.run(["gh", *args], capture_output=True, text=True)
    except FileNotFoundError:
        # Not retryable, and worth saying plainly: every GitHub-hosted runner
        # ships gh, so this means the step is running somewhere that does not.
        return 127, "", "gh: command not found (the GitHub CLI is required to publish release assets)"
    return proc.returncode, proc.stdout, proc.stderr


def existing_assets(tag: str, repo: str | None, dry_run: bool) -> set[str] | None:
    """Names already on the release, or None if the release does not exist yet.

    A read, so it costs nothing against the content-creation budget. Used to
    price each asset correctly: replacing one costs two writes (delete +
    upload), adding a new one costs a single write.
    """
    args = ["release", "view", tag, "--json", "assets"]
    if repo:
        args += ["--repo", repo]
    rc, out, err = run_gh(args, dry_run)
    if dry_run:
        return set()
    if rc != 0:
        if "release not found" in err.lower() or "not found" in err.lower():
            return None
        raise RuntimeError(f"could not read release {tag}: {err.strip()}")
    try:
        data = json.loads(out)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"could not parse release JSON for {tag}: {exc}") from exc
    return {a["name"] for a in data.get("assets", [])}


def ensure_release(tag: str, title: str, body: str, repo: str | None, exists: bool, dry_run: bool) -> None:
    """Create the rolling release, or refresh its title and notes in place.

    Never deletes and recreates it: `downloads-latest` is a single rolling
    release whose URL the Download page links, and recreating it would churn
    the tag and momentarily 404 every asset.
    """
    verb = "edit" if exists else "create"
    args = [
        "release",
        verb,
        tag,
        "--title",
        title,
        "--notes",
        body,
    ]
    if not exists:
        args += ["--latest=false"]
    if repo:
        args += ["--repo", repo]
    rc, _, err = run_gh(args, dry_run)
    if rc != 0:
        raise RuntimeError(f"could not {verb} release {tag}: {err.strip()}")


def upload_asset(tag: str, path: Path, repo: str | None, dry_run: bool) -> tuple[bool, str]:
    args = ["release", "upload", tag, str(path), "--clobber"]
    if repo:
        args += ["--repo", repo]
    rc, _, err = run_gh(args, dry_run)
    return rc == 0, err


def publish(
    tag: str,
    title: str,
    body: str,
    files: list[Path],
    repo: str | None,
    per_minute: int,
    dry_run: bool,
) -> int:
    present = existing_assets(tag, repo, dry_run)
    ensure_release(tag, title, body, repo, exists=present is not None, dry_run=dry_run)
    present = present or set()

    limiter = RateLimiter(per_minute)
    total = len(files)
    writes = sum(2 if f.name in present else 1 for f in files)
    print(
        f"Publishing {total} asset(s) to {tag}: ~{writes} content-generating "
        f"request(s), paced at {per_minute}/min (GitHub's documented limit is 80)."
    )

    failed: list[tuple[str, str]] = []
    started = time.monotonic()

    for i, path in enumerate(files, 1):
        cost = 2 if path.name in present else 1
        waited = limiter.acquire(cost)
        if waited > 0.5:
            print(f"    paced: waited {waited:.0f}s to stay within the write budget")

        ok, err = upload_asset(tag, path, repo, dry_run)
        limiter.record(cost)

        attempt = 0
        while not ok and attempt < len(RETRY_WAITS_SECONDS) and is_retryable(err):
            wait = RETRY_WAITS_SECONDS[attempt]
            attempt += 1
            print(
                f"    {path.name}: retryable failure, waiting {wait}s "
                f"(attempt {attempt}/{len(RETRY_WAITS_SECONDS)}) -- {err.strip().splitlines()[-1][:160]}"
            )
            if not dry_run:
                time.sleep(wait)
            # The rejected attempt still reached GitHub, so it stays counted
            # against the window -- deliberately conservative, since a retry
            # that ignored its own failed attempts would creep over budget
            # exactly when the API has already said we are over it.
            limiter.acquire(cost)
            ok, err = upload_asset(tag, path, repo, dry_run)
            limiter.record(cost)

        if ok:
            print(f"  [{i}/{total}] {path.name}")
        else:
            print(f"  [{i}/{total}] FAILED {path.name}: {err.strip()[:400]}", file=sys.stderr)
            failed.append((path.name, err.strip()[:400]))

    elapsed = time.monotonic() - started
    print(f"Done in {elapsed:.0f}s: {total - len(failed)}/{total} asset(s) published.")

    if failed:
        print(f"::error::{len(failed)} release asset(s) failed to publish.", file=sys.stderr)
        for name, err in failed:
            print(f"  {name}: {err}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="+", type=Path, help="asset files to publish")
    ap.add_argument("--tag", required=True, help="release tag, e.g. downloads-latest")
    ap.add_argument("--title", required=True, help="release title")
    ap.add_argument("--body-file", type=Path, help="file holding the release notes")
    ap.add_argument("--repo", help="owner/repo (defaults to the current repository)")
    ap.add_argument(
        "--writes-per-minute",
        type=int,
        default=int(os.environ.get("RELEASE_WRITES_PER_MINUTE", DEFAULT_WRITES_PER_MINUTE)),
        help=f"content-generating requests per minute (default {DEFAULT_WRITES_PER_MINUTE}; GitHub's limit is 80)",
    )
    ap.add_argument("--dry-run", action="store_true", help="print what would run, call nothing")
    args = ap.parse_args()

    files = [f for f in args.files if f.is_file()]
    missing = [f for f in args.files if not f.is_file()]
    for f in missing:
        print(f"::warning::no such asset, skipping: {f}", file=sys.stderr)
    if not files:
        print("::error::no asset files matched; refusing to publish an empty release.", file=sys.stderr)
        return 1

    body = args.body_file.read_text(encoding="utf8") if args.body_file else ""

    try:
        return publish(
            tag=args.tag,
            title=args.title,
            body=body,
            files=files,
            repo=args.repo,
            per_minute=args.writes_per_minute,
            dry_run=args.dry_run,
        )
    except RuntimeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
