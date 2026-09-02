"""The day-2 figure exclude in link-check.yml must stay a hairline, not a hole.

`.github/workflows/link-check.yml` excludes
`servicenow-day2/servicenow-day2/figs/` from lychee. That doubled segment is an
artifact of Quarto's include semantics -- a fragment's relative path resolves
against the *including* document, so the kit fragments must write
`servicenow-day2/figs/...`, and lychee, checking each file standalone, doubles
the segment looking for a file that cannot exist.

The danger is not the exclude; it is the exclude quietly losing the doubling
and becoming `servicenow-day2/figs/`, which would suppress every kit figure
reference repo-wide -- including the ones cited from the wrapper `.qmd` files,
which resolve correctly today and are genuinely checkable. These tests pin the
narrow form, and pin that the `args` block stays comment-free: it is a YAML
folded scalar, so a `#` line inside it is not a comment, it is an argument
handed to lychee.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

WORKFLOW = Path(__file__).parent.parent / ".github" / "workflows" / "link-check.yml"

DOUBLED = "servicenow-day2/servicenow-day2/figs/"


@pytest.fixture(scope="module")
def lychee_args() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    for step in workflow["jobs"]["link-check"]["steps"]:
        if "lychee-action" in str(step.get("uses", "")):
            return str(step["with"]["args"])
    pytest.fail("no lychee-action step in link-check.yml; update this test")


def test_the_doubled_path_is_excluded(lychee_args):
    assert f"--exclude '{DOUBLED}'" in lychee_args


def test_the_exclude_is_not_widened_to_real_figure_paths(lychee_args):
    """`servicenow-day2/figs/` alone would blind the wrapper refs too."""
    for token in lychee_args.split():
        stripped = token.strip("'\"")
        if "servicenow-day2" in stripped and "figs" in stripped:
            assert stripped == DOUBLED, (
                f"the day-2 figure exclude reads {stripped!r}; only the doubled "
                f"{DOUBLED!r} is a resolution artifact. A narrower segment also "
                "suppresses the wrapper .qmd figure refs, which resolve correctly "
                "and must stay checked."
            )


def test_args_carry_no_yaml_comments(lychee_args):
    """`args:` is a folded scalar -- a `#` line there is an argument, not a note."""
    assert "#" not in lychee_args, (
        "a '#' reached the lychee argument string. The `args:` block is a YAML "
        "folded scalar, so comments inside it are folded into the command line. "
        "Put rationale in a comment above the step instead."
    )
