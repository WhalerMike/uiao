"""The OrgPath narrative image manifest must match the chapters it registers.

The manifest records, per figure, what that figure was generated from — its
prompt body is the chapter's ``fig-alt`` text. Nothing regenerated it when a
chapter changed, so it drifted silently: when the gate was added it was missing
76 chapters, and 23 stored prompt bodies still described figures in the retired
composite-path notation those figures had already been re-authored away from.

A workflow enforces this too; the test is here so a regression fails ``pytest``
in the same run that introduced it, rather than only at push time.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "rebuild_orgpath_image_manifest",
    Path(__file__).parent.parent / "scripts" / "rebuild_orgpath_image_manifest.py",
)
rebuild = importlib.util.module_from_spec(_SPEC)
assert _SPEC.loader is not None
_SPEC.loader.exec_module(rebuild)


def test_manifest_is_current() -> None:
    """Regenerate with: python scripts/rebuild_orgpath_image_manifest.py --write"""
    assert rebuild.main(["--check"]) == 0, (
        "image-prompts.manifest.yaml no longer matches its chapters — "
        "run scripts/rebuild_orgpath_image_manifest.py --write and commit"
    )
