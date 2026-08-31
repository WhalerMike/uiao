"""The assemble job's sparse checkout must carry every script it invokes.

The `assemble` job in .github/workflows/quarto.yml checks the repo out into
`_repo/` with `sparse-checkout` and `sparse-checkout-cone-mode: false`, so a
path that is not listed is simply not on disk. Referencing an unlisted script
therefore fails at run time with::

    python3: can't open file '.../_repo/scripts/publish_release_assets.py':
    [Errno 2] No such file or directory

and it fails *only* on main: the assemble job runs on push to main and on
manual dispatch, never on a pull request, so nothing catches it before merge.
That is exactly how #1471 shipped a broken publish step -- the local
simulation had copied the script into `_repo/scripts/` by hand, which quietly
supplied the one thing the real job would not have.

This test closes that gap by deriving both sides from the workflow itself:
every `_repo/scripts/<name>` a step actually invokes must appear in the
sparse-checkout list.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "quarto.yml"

# `_repo/scripts/foo.py`, however it is quoted or continued across lines.
_REPO_SCRIPT = re.compile(r"_repo/(scripts/[A-Za-z0-9_./-]+\.py)")


@pytest.fixture(scope="module")
def workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def assemble(workflow) -> dict:
    job = workflow["jobs"].get("assemble")
    assert job, "quarto.yml no longer has an `assemble` job; update this test"
    return job


def sparse_paths(assemble: dict) -> set[str]:
    """Paths the assemble job's sparse checkout puts on disk under _repo/."""
    for step in assemble["steps"]:
        with_ = step.get("with") or {}
        if "sparse-checkout" in with_:
            return {
                line.strip()
                for line in str(with_["sparse-checkout"]).splitlines()
                if line.strip() and not line.strip().startswith("#")
            }
    pytest.fail("no sparse-checkout step found in the assemble job")


def invoked_scripts(assemble: dict) -> set[str]:
    """Every _repo/scripts/... path any run step in the job actually invokes."""
    found: set[str] = set()
    for step in assemble["steps"]:
        found.update(_REPO_SCRIPT.findall(step.get("run") or ""))
    return found


def test_the_job_invokes_some_scripts(assemble):
    """Guard the guard: a regex that silently matches nothing proves nothing."""
    assert invoked_scripts(assemble), "found no _repo/scripts/... invocations — regex likely stale"


def test_every_invoked_script_is_in_the_sparse_checkout(assemble):
    listed = sparse_paths(assemble)
    missing = sorted(s for s in invoked_scripts(assemble) if s not in listed)
    assert not missing, (
        "these scripts are invoked by the assemble job but are not in its "
        "sparse-checkout list, so they will not exist on disk at run time: "
        f"{missing}"
    )


def test_the_sparse_checkout_is_non_cone(assemble):
    """The file-level entries above only behave that way in non-cone mode."""
    for step in assemble["steps"]:
        with_ = step.get("with") or {}
        if "sparse-checkout" in with_:
            assert with_.get("sparse-checkout-cone-mode") is False, (
                "cone mode would reinterpret the file-level paths as directories; this test's premise no longer holds"
            )
            return


def test_publish_script_specifically_is_present(assemble):
    """The regression that motivated this test, pinned by name."""
    assert "scripts/publish_release_assets.py" in sparse_paths(assemble)
