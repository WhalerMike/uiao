#!/usr/bin/env python3
"""
generate_images.py — Consume image-manifest.json (from aggregate_prompts.py)
and materialize per-adapter PNG illustrations into each adapter's images/
folder.

Design goals:
  * Deterministic: same manifest + same cache → zero work, exit 0.
  * Incremental: only regenerate images whose content-hash changed
    vs. the persisted cache (default: data/image-cache.json).
  * Pluggable backend: the actual image model call is isolated in
    `render_image(...)` so Step 2 can swap in the real provider without
    touching the orchestration / cache / reporting logic.
  * CI-safe: by default uses a stub backend that writes a placeholder PNG
    (1x1 transparent, plus a sidecar .txt containing the prompt) so the
    pipeline can be exercised end-to-end in CI without network / API keys.

USAGE (typical):
    python tools/generate_images.py \\
        --manifest data/image-manifest.json \\
        --cache    data/image-cache.json \\
        --docs-root .

Flags:
    --backend {stub,real}       Choose image generation backend (default: stub)
    --force                     Ignore cache; regenerate every entry
    --dry-run                   Report planned actions without writing
    --verbose                   Per-entry status on stderr

Exit codes:
    0  — all entries either up-to-date or regenerated successfully
    1  — at least one entry failed to render (partial success; cache updated
         for successes only)
    2  — fatal (manifest missing / unreadable, cache unreadable, etc.)
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ------------------------------------------------------------------
# Minimal 1x1 transparent PNG — used by the stub backend so CI has a
# deterministic binary output without invoking any external service.
# ------------------------------------------------------------------
_STUB_PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000d49444154789c6300010000000500010d0a2db40000000049454e44"
    "ae426082"
)


@dataclass
class RenderResult:
    ok: bool
    backend: str
    bytes_written: int
    message: str = ""


@dataclass
class GenerateReport:
    manifest_path: str
    cache_path: str
    docs_root: str
    total_entries: int = 0
    skipped_unchanged: int = 0
    rendered: int = 0
    failed: int = 0
    dry_run: bool = False
    errors: list[str] = field(default_factory=list)

    def exit_code(self) -> int:
        return 1 if self.failed else 0


# ------------------------------------------------------------------
# Backends
# ------------------------------------------------------------------

def render_stub(prompt: str, out_path: Path) -> RenderResult:
    """Stub backend — deterministic, offline, CI-friendly.

    Writes a 1x1 PNG placeholder plus a sidecar `.prompt.txt` containing
    the prompt body. Swap for `render_real` in Step 2.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(_STUB_PNG_BYTES)
    sidecar = out_path.with_suffix(out_path.suffix + ".prompt.txt")
    sidecar.write_text(prompt.strip() + "\n", encoding="utf-8")
    return RenderResult(ok=True, backend="stub", bytes_written=len(_STUB_PNG_BYTES))


def render_real(prompt: str, out_path: Path) -> RenderResult:
    """Real-backend placeholder.

    Intentionally not wired up in this step. Step 2 will replace the body
    with a call to the chosen image provider and write the returned PNG
    bytes to `out_path`. Until then, this errors out loudly if selected.
    """
    return RenderResult(
        ok=False,
        backend="real",
        bytes_written=0,
        message="real backend not implemented yet — scheduled for Step 2",
    )


BACKENDS: dict[str, Callable[[str, Path], RenderResult]] = {
    "stub": render_stub,
    "real": render_real,
}


# ------------------------------------------------------------------
# Cache I/O
# ------------------------------------------------------------------

def load_cache(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        entries = raw.get("entries", {}) if isinstance(raw, dict) else {}
        return {str(k): str(v) for k, v in entries.items()}
    except Exception:
        return {}


def save_cache(path: Path, cache: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema-version": "1.0",
        "entries": dict(sorted(cache.items())),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


# ------------------------------------------------------------------
# Core orchestration
# ------------------------------------------------------------------

def process_entry(
    entry: dict,
    docs_root: Path,
    cache: dict[str, str],
    backend_fn: Callable[[str, Path], RenderResult],
    force: bool,
    dry_run: bool,
    report: GenerateReport,
    verbose: bool,
) -> None:
    target_rel = entry["target_path"]
    content_hash = entry["content_hash"]
    prompt = entry["prompt"]
    out_path = docs_root / target_rel

    cached_hash = cache.get(target_rel)
    already_exists = out_path.is_file()
    needs_render = force or (cached_hash != content_hash) or (not already_exists)

    if not needs_render:
        report.skipped_unchanged += 1
        if verbose:
            print(f"  skip   {target_rel} (hash match)", file=sys.stderr)
        return

    if dry_run:
        report.rendered += 1
        if verbose:
            print(f"  PLAN   {target_rel} (would render)", file=sys.stderr)
        return

    try:
        result = backend_fn(prompt, out_path)
    except Exception as exc:
        report.failed += 1
        msg = f"render crashed for {target_rel}: {exc}"
        report.errors.append(msg)
        if verbose:
            print(f"  FAIL   {msg}", file=sys.stderr)
        return

    if not result.ok:
        report.failed += 1
        msg = f"render failed for {target_rel}: {result.message}"
        report.errors.append(msg)
        if verbose:
            print(f"  FAIL   {msg}", file=sys.stderr)
        return

    cache[target_rel] = content_hash
    report.rendered += 1
    if verbose:
        print(
            f"  ok     {target_rel} ({result.backend}, {result.bytes_written}B)",
            file=sys.stderr,
        )


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--manifest", default="data/image-manifest.json",
                    help="Path to image manifest (from aggregate_prompts.py)")
    ap.add_argument("--cache", default="data/image-cache.json",
                    help="Path to persistent hash cache")
    ap.add_argument("--docs-root", default=".",
                    help="Root of uiao-docs repo (default: cwd)")
    ap.add_argument("--backend", choices=sorted(BACKENDS.keys()), default="stub",
                    help="Image generation backend (default: stub)")
    ap.add_argument("--force", action="store_true",
                    help="Ignore cache; regenerate every entry")
    ap.add_argument("--dry-run", action="store_true",
                    help="Report planned actions without writing")
    ap.add_argument("--verbose", action="store_true",
                    help="Per-entry status on stderr")
    args = ap.parse_args()

    docs_root = Path(args.docs_root).resolve()
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = docs_root / manifest_path
    cache_path = Path(args.cache)
    if not cache_path.is_absolute():
        cache_path = docs_root / cache_path

    if not manifest_path.is_file():
        print(f"FATAL: manifest not found: {manifest_path}", file=sys.stderr)
        return 2

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"FATAL: manifest unreadable: {exc}", file=sys.stderr)
        return 2

    entries = manifest.get("entries", []) if isinstance(manifest, dict) else []
    cache = load_cache(cache_path)
    backend_fn = BACKENDS[args.backend]

    report = GenerateReport(
        manifest_path=str(manifest_path),
        cache_path=str(cache_path),
        docs_root=str(docs_root),
        total_entries=len(entries),
        dry_run=args.dry_run,
    )

    for entry in entries:
        process_entry(
            entry=entry,
            docs_root=docs_root,
            cache=cache,
            backend_fn=backend_fn,
            force=args.force,
            dry_run=args.dry_run,
            report=report,
            verbose=args.verbose,
        )

    if not args.dry_run:
        save_cache(cache_path, cache)

    print(f"generate_images.py — backend={args.backend}"
          f"{' (dry-run)' if args.dry_run else ''}", file=sys.stderr)
    print(f"  manifest:          {args.manifest}", file=sys.stderr)
    print(f"  cache:             {args.cache}", file=sys.stderr)
    print(f"  total entries:     {report.total_entries}", file=sys.stderr)
    print(f"  skipped unchanged: {report.skipped_unchanged}", file=sys.stderr)
    print(f"  rendered:          {report.rendered}", file=sys.stderr)
    print(f"  failed:            {report.failed}", file=sys.stderr)
    if report.errors:
        print(f"  errors:", file=sys.stderr)
        for e in report.errors:
            print(f"    - {e}", file=sys.stderr)

    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
