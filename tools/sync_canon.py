#!/usr/bin/env python3
"""
sync_canon.py — UIAO canon → uiao-docs synchronizer

Propagates adapter-registry canon from `uiao-core` into the customer-documentation
tree in `uiao-docs`. Operates in two complementary modes:

  --check-only   Validate registries against schema, scan the docs tree, and
                 report drift (additive, orphan, status-mismatch). Never writes.
                 Exit code 1 on drift, 0 on clean, 2 on schema error.

  --scaffold     Run the check, then create missing adapter folders and seed
                 them with governance frontmatter derived from the registry
                 entry. Never deletes anything. Updates stale frontmatter
                 on existing docs.

  (no flag)      Equivalent to `--scaffold` but exits non-zero if ANY write
                 actually occurred (so CI can distinguish "clean sync" from
                 "we scaffolded new adapter docs — please review this PR").

The tool is deterministic: given the same registries + docs tree, it produces
the same output. Idempotent: running it twice in a row produces no change.

USAGE (typical CI invocation):
    python tools/sync_canon.py \\
        --core-root /path/to/uiao-core \\
        --docs-root /path/to/uiao-docs \\
        --scaffold --json > sync-report.json

Canon is authoritative; the docs tree is derived. If this tool writes, the
registries are the source of truth and the docs tree catches up.

See uiao-core/ARCHITECTURE.md §4 for the three-layer sync defense in depth.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml jsonschema", file=sys.stderr)
    sys.exit(2)

try:
    from jsonschema import Draft7Validator
except ImportError:
    print("ERROR: jsonschema not installed. Run: pip install pyyaml jsonschema", file=sys.stderr)
    sys.exit(2)


# ------------------------------------------------------------------
# Constants — paths relative to the two repo roots
# ------------------------------------------------------------------

REGISTRY_FILES = [
    ("canon/modernization-registry.yaml", "modernization"),
    ("canon/adapter-registry.yaml", "conformance"),
]
SCHEMA_FILE = "schemas/adapter-registry/adapter-registry.schema.json"

# Trees in uiao-docs that mirror per-adapter canon
ADAPTER_DOC_TREES = [
    ("docs/customer-documents/adapter-technical-specifications", "ats", "Adapter Technical Specification"),
    ("docs/customer-documents/adapter-validation-suites",       "avs", "Adapter Validation Suite"),
]

FRONTMATTER_MARKER = "---"


# ------------------------------------------------------------------
# Report dataclasses
# ------------------------------------------------------------------

@dataclass
class DriftItem:
    kind: str          # "additive" | "orphan" | "status-mismatch" | "schema-error"
    adapter_id: str | None
    path: str
    detail: str


@dataclass
class ScaffoldAction:
    kind: str          # "created-folder" | "created-file" | "updated-frontmatter"
    path: str
    detail: str


@dataclass
class SyncReport:
    core_root: str
    docs_root: str
    mode: str
    schema_ok: bool
    registries_loaded: int
    adapters_total: int
    drift: list[DriftItem] = field(default_factory=list)
    actions: list[ScaffoldAction] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        if not self.schema_ok:
            return 2
        if self.mode == "check-only" and self.drift:
            return 1
        if self.mode == "scaffold" and self.actions:
            # CI wants a non-zero signal when scaffolding happened so a PR
            # gets opened. Orphan/status drift that we didn't remediate also
            # still counts as drift.
            return 1
        remaining_drift = [d for d in self.drift if d.kind != "additive"]
        if remaining_drift:
            return 1
        return 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "core_root": self.core_root,
            "docs_root": self.docs_root,
            "mode": self.mode,
            "schema_ok": self.schema_ok,
            "registries_loaded": self.registries_loaded,
            "adapters_total": self.adapters_total,
            "drift": [dataclasses.asdict(d) for d in self.drift],
            "actions": [dataclasses.asdict(a) for a in self.actions],
            "exit_code": self.exit_code,
        }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def load_registries(core_root: Path, report: SyncReport) -> list[dict[str, Any]]:
    """Load registries, validate against schema, and return the merged adapter list."""
    schema_path = core_root / SCHEMA_FILE
    if not schema_path.is_file():
        report.schema_ok = False
        report.drift.append(DriftItem("schema-error", None, str(schema_path), "Schema file not found"))
        return []

    with schema_path.open() as f:
        schema = json.load(f)
    validator = Draft7Validator(schema)

    adapters: list[dict[str, Any]] = []
    for rel_path, expected_class in REGISTRY_FILES:
        reg_path = core_root / rel_path
        if not reg_path.is_file():
            report.drift.append(
                DriftItem("schema-error", None, str(reg_path), f"Registry file missing (expected class={expected_class})")
            )
            report.schema_ok = False
            continue

        with reg_path.open() as f:
            data = yaml.safe_load(f)

        # Validate
        errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))
        if errors:
            report.schema_ok = False
            for e in errors:
                err_path = "/".join(str(x) for x in e.absolute_path) or "<root>"
                report.drift.append(
                    DriftItem("schema-error", None, f"{rel_path}:{err_path}", e.message)
                )
            continue

        # Cross-check registry-class matches file's stated purpose
        actual_class = data.get("registry-class")
        if actual_class != expected_class:
            report.drift.append(
                DriftItem(
                    "schema-error",
                    None,
                    str(reg_path),
                    f"registry-class mismatch: expected '{expected_class}', got '{actual_class}'",
                )
            )
            report.schema_ok = False
            continue

        for a in data.get("adapters", []):
            # Stamp the registry-class onto each adapter for downstream use
            a["_source_registry"] = rel_path
            adapters.append(a)

        report.registries_loaded += 1

    report.adapters_total = len(adapters)
    return adapters


def parse_frontmatter(path: Path) -> dict[str, Any] | None:
    """Return the YAML frontmatter dict if present, else None."""
    if not path.is_file():
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    if not text.startswith(FRONTMATTER_MARKER):
        return None
    # Split on the second --- marker
    rest = text[len(FRONTMATTER_MARKER):]
    end = rest.find("\n" + FRONTMATTER_MARKER)
    if end < 0:
        return None
    fm_text = rest[:end]
    try:
        return yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None


def render_frontmatter(adapter: dict[str, Any], doc_kind: str, doc_title: str) -> str:
    """Produce YAML frontmatter block for a scaffolded adapter doc."""
    fm = {
        "title": f"{adapter['name']} — {doc_title}",
        "doc-type": doc_kind,  # "ats" or "avs"
        "adapter-id": adapter["id"],
        "adapter-class": adapter["class"],
        "mission-class": adapter["mission-class"],
        "status": adapter["status"],
        "phase": adapter.get("phase"),
        "gcc-boundary": adapter["gcc-boundary"],
        "canon-source": adapter["_source_registry"],
        "derived-from": "uiao-core/canon (sync_canon.py)",
        "generated": date.today().isoformat(),
    }
    # Drop None values for a clean block
    fm = {k: v for k, v in fm.items() if v is not None}
    yaml_block = yaml.safe_dump(fm, sort_keys=False, default_flow_style=False, allow_unicode=True).rstrip()
    return f"---\n{yaml_block}\n---\n"


def render_placeholder_body(adapter: dict[str, Any], doc_kind: str, doc_title: str) -> str:
    """Produce a minimal placeholder body so the doc renders but flags as a stub."""
    controls = ", ".join(f"`{c}`" for c in adapter.get("controls", [])) or "_(none declared)_"
    scope = ", ".join(f"`{s}`" for s in adapter.get("scope", [])) or "_(not yet defined)_"
    notes = adapter.get("notes", "").strip() or "_(none)_"

    return f"""# {adapter['name']} — {doc_title}

> **Status:** `{adapter['status']}` · **Class:** `{adapter['class']}` · **Mission:** `{adapter['mission-class']}` · **Phase:** `{adapter.get('phase', 'unspecified')}`
>
> **Canon source:** `{adapter['_source_registry']}` (sync_canon.py)
>
> **This document is a scaffold.** Replace the TODO sections with authored content. The frontmatter and this header are regenerated from canon and must not be hand-edited.

## Overview

_TODO — Author an overview of the {adapter['name']} adapter's role in the UIAO governance perimeter. Do not contradict canon._

## Scope

Target surfaces / subsystems: {scope}

## Controls

NIST SP 800-53 Rev 5 controls this adapter supports: {controls}

## Operational profile

- **Runtime:** `{adapter.get('runtime', 'TBD')}` (pin: `{adapter.get('runtime-version', 'TBD')}`)
- **Runner class:** `{adapter.get('runner-class', 'TBD')}`
- **Tenancy:** `{adapter.get('tenancy', 'TBD')}`
- **Evidence class:** `{adapter.get('evidence-class', 'TBD')}`
- **Retention:** `{adapter.get('retention-years', 'TBD')}` year(s)

## Canon invariants

- `gcc-boundary: {adapter['gcc-boundary']}`
- `ssot-mutation: never`
- `certificate-anchored: true`
- `object-identity-only: true`

## Notes from canon

{notes}

## References

{chr(10).join(f'- {r}' for r in adapter.get('references', []))}

---

*This scaffold was generated by `uiao-core/tools/sync_canon.py`. See `uiao-core/ARCHITECTURE.md` §4 for the cross-repo sync contract.*
"""


def render_image_prompts(adapter: dict[str, Any], doc_kind: str) -> str:
    """Seed an IMAGE-PROMPTS.md sibling file."""
    return f"""# Image Prompts — {adapter['name']} ({doc_kind.upper()})

> Scaffold generated by `sync_canon.py`. Add one prompt per `[IMAGE-NN:]` or
> `[DIAGRAM-NN:]` placeholder in the companion document. When images are
> produced they land in `./images/`.

## IMAGE-01

_TODO — describe the intended first illustration for this document._

"""


def compute_frontmatter_hash(fm: dict[str, Any]) -> str:
    """Stable hash of the auto-generated frontmatter fields for drift detection."""
    # Only hash the registry-derived fields; ignore user-added keys
    subset = {k: fm.get(k) for k in (
        "adapter-id", "adapter-class", "mission-class", "status", "phase",
        "gcc-boundary", "canon-source"
    )}
    return hashlib.sha256(json.dumps(subset, sort_keys=True).encode()).hexdigest()[:12]


# ------------------------------------------------------------------
# Core scanner
# ------------------------------------------------------------------

def scan_and_sync(adapters: list[dict[str, Any]], docs_root: Path, report: SyncReport, write: bool) -> None:
    adapter_ids = {a["id"]: a for a in adapters}
    id_pattern = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$")

    for rel_tree, kind, doc_title in ADAPTER_DOC_TREES:
        tree = docs_root / rel_tree
        if not tree.is_dir():
            if write:
                tree.mkdir(parents=True, exist_ok=True)
                report.actions.append(ScaffoldAction("created-folder", str(tree), "doc tree root"))
            else:
                report.drift.append(
                    DriftItem("additive", None, str(tree), f"Doc tree missing (would create)")
                )
                continue

        # 1. Scan existing folders → detect orphans + status drift
        for child in sorted(tree.iterdir()):
            if not child.is_dir():
                continue
            folder_id = child.name
            if folder_id.startswith("_"):
                # _template, _assets, _tools — reserved, skip
                continue
            if not id_pattern.match(folder_id):
                report.drift.append(
                    DriftItem("orphan", folder_id, str(child), "Folder name fails adapter id pattern")
                )
                continue
            if folder_id not in adapter_ids:
                report.drift.append(
                    DriftItem(
                        "orphan",
                        folder_id,
                        str(child),
                        f"Folder present in docs tree but no adapter with id='{folder_id}' in any registry",
                    )
                )
                continue

            # Status drift check
            adapter = adapter_ids[folder_id]
            primary = child / f"{kind}-{folder_id}.md"
            fm = parse_frontmatter(primary)
            if fm is None:
                # File either empty or lacks frontmatter — treat as additive
                report.drift.append(
                    DriftItem(
                        "additive",
                        folder_id,
                        str(primary),
                        "Primary doc missing or lacks frontmatter (would regenerate)",
                    )
                )
                if write:
                    primary.write_text(
                        render_frontmatter(adapter, kind, doc_title)
                        + "\n"
                        + render_placeholder_body(adapter, kind, doc_title),
                        encoding="utf-8",
                    )
                    report.actions.append(ScaffoldAction("created-file", str(primary), "ATS/AVS scaffold"))
            else:
                drifted_fields = []
                for key, canon_key in (
                    ("adapter-class", "class"),
                    ("mission-class", "mission-class"),
                    ("status", "status"),
                    ("phase", "phase"),
                    ("gcc-boundary", "gcc-boundary"),
                ):
                    expected = adapter.get(canon_key)
                    actual = fm.get(key)
                    if expected is not None and actual != expected:
                        drifted_fields.append(f"{key}: '{actual}' → '{expected}'")
                if drifted_fields:
                    detail = "; ".join(drifted_fields)
                    report.drift.append(
                        DriftItem("status-mismatch", folder_id, str(primary), detail)
                    )
                    if write:
                        # Regenerate the frontmatter block, preserve body
                        text = primary.read_text(encoding="utf-8")
                        body_start = text.find("\n---", len(FRONTMATTER_MARKER))
                        body = text[body_start + len("\n---"):] if body_start > 0 else "\n"
                        new_fm = render_frontmatter(adapter, kind, doc_title)
                        primary.write_text(new_fm + body, encoding="utf-8")
                        report.actions.append(
                            ScaffoldAction("updated-frontmatter", str(primary), detail)
                        )

        # 2. Walk registries → detect additives (adapter with no folder)
        for adapter in adapters:
            folder = tree / adapter["id"]
            primary = folder / f"{kind}-{adapter['id']}.md"
            prompts = folder / "IMAGE-PROMPTS.md"
            images = folder / "images"
            gitkeep = images / ".gitkeep"

            created_any = False
            if not folder.is_dir():
                report.drift.append(
                    DriftItem("additive", adapter["id"], str(folder), f"Folder missing for adapter (would create)")
                )
                if write:
                    folder.mkdir(parents=True, exist_ok=True)
                    report.actions.append(
                        ScaffoldAction("created-folder", str(folder), f"adapter={adapter['id']}")
                    )
                    created_any = True

            if write and folder.is_dir():
                if not primary.exists() or primary.stat().st_size == 0:
                    primary.write_text(
                        render_frontmatter(adapter, kind, doc_title)
                        + "\n"
                        + render_placeholder_body(adapter, kind, doc_title),
                        encoding="utf-8",
                    )
                    report.actions.append(ScaffoldAction("created-file", str(primary), "ATS/AVS scaffold"))
                    created_any = True
                if not prompts.exists():
                    prompts.write_text(render_image_prompts(adapter, kind), encoding="utf-8")
                    report.actions.append(ScaffoldAction("created-file", str(prompts), "image prompts scaffold"))
                    created_any = True
                if not images.is_dir():
                    images.mkdir(parents=True, exist_ok=True)
                    report.actions.append(ScaffoldAction("created-folder", str(images), "images dir"))
                    created_any = True
                if not gitkeep.exists():
                    gitkeep.write_text("", encoding="utf-8")
                    report.actions.append(ScaffoldAction("created-file", str(gitkeep), ".gitkeep"))


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Sync uiao-core adapter canon into uiao-docs customer-documentation tree")
    ap.add_argument("--core-root", type=Path, required=True, help="Path to uiao-core repo root")
    ap.add_argument("--docs-root", type=Path, required=True, help="Path to uiao-docs repo root")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--check-only", action="store_true", help="Report drift; never write")
    mode.add_argument("--scaffold", action="store_true", help="Report drift AND write missing scaffolding")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON report on stdout")
    args = ap.parse_args()

    if not args.core_root.is_dir():
        print(f"ERROR: --core-root {args.core_root} is not a directory", file=sys.stderr)
        return 2
    if not args.docs_root.is_dir():
        print(f"ERROR: --docs-root {args.docs_root} is not a directory", file=sys.stderr)
        return 2

    # Mode resolution: default = scaffold (writes)
    if args.check_only:
        mode_name = "check-only"
        write = False
    else:
        mode_name = "scaffold"
        write = True

    report = SyncReport(
        core_root=str(args.core_root),
        docs_root=str(args.docs_root),
        mode=mode_name,
        schema_ok=True,
        registries_loaded=0,
        adapters_total=0,
    )

    adapters = load_registries(args.core_root, report)
    if report.schema_ok and adapters:
        scan_and_sync(adapters, args.docs_root, report, write)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        # Human-readable summary
        print(f"sync_canon.py — mode={report.mode}")
        print(f"  core: {report.core_root}")
        print(f"  docs: {report.docs_root}")
        print(f"  schema-ok: {report.schema_ok}")
        print(f"  registries loaded: {report.registries_loaded}")
        print(f"  adapters total: {report.adapters_total}")
        print(f"  drift items: {len(report.drift)}")
        for d in report.drift:
            print(f"    [{d.kind:15s}] {d.adapter_id or '-':15s} {d.detail}")
        print(f"  scaffold actions: {len(report.actions)}")
        for a in report.actions:
            print(f"    [{a.kind:22s}] {a.path}  ({a.detail})")
        print(f"  exit-code: {report.exit_code}")

    return report.exit_code


if __name__ == "__main__":
    sys.exit(main())
