"""The tenant restrictions v2 enforcement-path claim must not drift.

File: tests/test_tenant_restrictions_v2_claim.py

This claim has been wrong in this repository once already. Before #1516,
`tic3-sdwan-vs-dia.qmd` 5.5 said tenant restrictions v2 "is enforced by header
injection at an in-path proxy", and concluded a proxy-bypassed flow cannot
carry it. That is the *v1* model. The error had already propagated into the
SC-7(4) exception memo before it was caught.

It is load-bearing rather than editorial. The whole Optimize inspection
exemption turns on whether giving up the in-path proxy gives up tenant
restrictions. If it does, the exemption punctures a control with no
compensation and the memo should not be signed. If it does not -- because two
of the three enforcement paths need no proxy -- the control moves to the
endpoint and the exemption is defensible with a stated precondition.

Five published documents now state some part of this. Nothing made them agree.
`tests/fixtures/claims/entra-tenant-restrictions-v2-enforcement-paths.yaml` is
the single record; these tests assert the documents against it.

Two things learned writing this, both preserved as design constraints:

* The `.qmd` sources are hard-wrapped, so "Group Policy" is split across a
  newline in `attachment-a-site-register.qmd`. Every check here flattens
  whitespace first; a line-oriented grep silently under-reports.
* A correct document contains the incorrect claim *as a quoted foil* -- the
  whitepaper and the index both state the intuitive wrong answer in order to
  refute it. A blacklist of wrong phrasings would fail on exactly the documents
  that got it right. So the dependency check below demands a *retraction in the
  same paragraph* rather than forbidding the phrasing.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
RECORD_PATH = REPO_ROOT / "tests" / "fixtures" / "claims" / "entra-tenant-restrictions-v2-enforcement-paths.yaml"

# Phrasings that assert v2 *depends* on an in-path proxy. Stating one of these
# is fine -- as a foil -- but only alongside the retraction.
DEPENDENCY_PHRASINGS = (
    "requires a proxy",
    "requires an in-path proxy",
    "needs a proxy",
    "needs an in-path proxy",
    "depends on the proxy",
    "is enforced by header injection",
)
RETRACTION_MARKERS = ("v1", "wrong")


@pytest.fixture(scope="module")
def record() -> dict:
    return yaml.safe_load(RECORD_PATH.read_text(encoding="utf-8"))


def flatten(text: str) -> str:
    """Strip markdown emphasis and collapse whitespace, so hard wrapping and
    bolding cannot hide a phrase from a substring check."""
    return re.sub(r"\s+", " ", re.sub(r"[*_`]", "", text)).strip().lower()


def doc(rel: str) -> str:
    path = REPO_ROOT / rel
    assert path.is_file(), f"{rel}: named in the claim record but not on disk"
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# The record itself
# --------------------------------------------------------------------------


def test_record_declares_exactly_three_paths(record) -> None:
    """Microsoft documents three. A fourth appearing without a citation, or a
    third quietly dropped, is the drift this file exists to catch."""
    assert len(record["paths"]) == 3, (
        f"the record declares {len(record['paths'])} enforcement paths. If Microsoft "
        "has changed the set, update provenance.primary.accessed in the same commit "
        "and re-read the source -- do not adjust the count alone."
    )


def test_path_ids_are_unique(record) -> None:
    ids = [p["id"] for p in record["paths"]]
    assert len(ids) == len(set(ids)), f"duplicate path ids in the record: {ids}"


def test_exactly_one_path_requires_a_proxy(record) -> None:
    """The load-bearing asymmetry: two of three paths need no proxy, which is
    why an inspection exemption does not destroy the control."""
    proxied = [p["id"] for p in record["paths"] if p["requires_proxy"]]
    assert proxied == ["corporate-proxy-header-injection"], (
        f"paths requiring a proxy: {proxied}. Exactly one should -- header injection. "
        "If this changed, the exemption argument in the SC-7(4) memo needs re-examining, "
        "not just this record."
    )


def test_exactly_one_path_reaches_the_data_plane(record) -> None:
    """Windows Group Policy alone carries data-plane protection. Global Secure
    Access reaches it for Graph only; proxy injection not at all."""
    full = [p["id"] for p in record["paths"] if p["data_plane"] == "yes"]
    assert full == ["windows-group-policy"], f"paths with full data-plane coverage: {full}"


def test_provenance_is_complete_and_dated(record) -> None:
    """An undated citation is drift-prone -- the contract README's own words."""
    primary = record["provenance"]["primary"]
    assert primary["url"].startswith("https://")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", primary["accessed"]), (
        f"accessed={primary['accessed']!r} is not an ISO date"
    )
    assert primary["read"] in {"firsthand", "secondary"}


# --------------------------------------------------------------------------
# The memo's table -- the one place the full claim is tabulated
# --------------------------------------------------------------------------


def parse_table(text: str, header: str) -> list[list[str]]:
    """Return the data rows of the markdown table introduced by `header`."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == header.strip():
            rows = []
            for row in lines[i + 2 :]:  # skip the |---| separator
                if not row.strip().startswith("|"):
                    break
                rows.append([c.strip() for c in row.strip().strip("|").split("|")])
            return rows
    pytest.fail(f"table header not found: {header!r}")


def test_memo_table_matches_the_record(record) -> None:
    """Every cell of the memo's enforcement-path table, against the record.

    This is the assertion with teeth: flipping a Yes to a No in the table --
    the edit that would quietly reverse the memo's conclusion -- fails here.
    """
    spec = record["asserted_against"]["table"]
    rows = parse_table(doc(spec["path"]), spec["header"])
    assert len(rows) == len(record["paths"]), (
        f"{spec['path']}: table has {len(rows)} rows, record has {len(record['paths'])} paths"
    )

    for path in record["paths"]:
        matching = [r for r in rows if path["label_contains"].lower() in flatten(r[0])]
        assert len(matching) == 1, (
            f"{spec['path']}: expected exactly one table row naming {path['label_contains']!r}, found {len(matching)}"
        )
        label, proxy, auth, data = (flatten(c) for c in matching[0])
        expected_proxy = "yes" if path["requires_proxy"] else "no"
        assert proxy == expected_proxy, (
            f"{spec['path']}: row {label!r} says proxy required={proxy!r}, record says {expected_proxy!r}"
        )
        assert auth == path["authentication_plane"], (
            f"{spec['path']}: row {label!r} authentication plane={auth!r}, record says {path['authentication_plane']!r}"
        )
        assert data == path["data_plane"], (
            f"{spec['path']}: row {label!r} data plane={data!r}, record says {path['data_plane']!r}"
        )


# --------------------------------------------------------------------------
# The prose documents
# --------------------------------------------------------------------------


def prose_paths(record) -> list[str]:
    return record["asserted_against"]["prose"]


def test_every_asserted_document_exists(record) -> None:
    for rel in [record["asserted_against"]["table"]["path"], *prose_paths(record)]:
        assert (REPO_ROOT / rel).is_file(), f"{rel}: listed in the record, missing on disk"


def test_prose_documents_still_state_the_claim(record) -> None:
    """Each prose document must still name at least one enforcement path.

    Deliberately weak in two ways. `attachment-a-site-register.qmd` names only
    the Group Policy path, because a site checklist has no reason to enumerate
    options the agency cannot use -- so the check is per-document existence, not
    per-document completeness. And it matches on `prose_names` rather than the
    table label, because running text says "the Group Policy path" where the
    memo's table says "Windows Group Policy on corporate-owned devices".
    """
    aliases = [n for p in record["paths"] for n in p["prose_names"]]
    for rel in prose_paths(record):
        flat = flatten(doc(rel))
        assert any(a in flat for a in aliases), (
            f"{rel}: names no tenant-restrictions enforcement path. Either the claim was "
            "removed from this document -- in which case drop it from asserted_against.prose "
            "in the record -- or a rewrite lost it."
        )


def test_global_secure_access_is_never_offered_without_its_federal_limit(record) -> None:
    """Naming GSA as a path without saying it is unavailable federally would let
    an agency plan around an option it cannot use.

    The crosswalk records it as non-FIPS in GCC Moderate and unavailable in GCC
    High and DoD, which is what makes Group Policy the only path here rather
    than the preferred one.
    """
    for rel in prose_paths(record):
        flat = flatten(doc(rel))
        if "global secure access" in flat:
            assert "non-fips" in flat, (
                f"{rel}: names Global Secure Access as an enforcement path but never states "
                "its federal availability limit. See "
                "docs/customer-documents/learning/entra-security-baseline-federal-crosswalk.qmd."
            )


def test_a_proxy_dependency_claim_is_always_retracted_in_place(record) -> None:
    """Asserting v2 depends on a proxy is permitted only as a refuted foil.

    Both the whitepaper and the index state the intuitive wrong answer before
    correcting it -- that is good writing, not drift. What must never happen is
    the assertion standing unretracted, which is exactly the state #1516 found.
    So the rule is paragraph-local: say it, and retract it in the same breath.
    """
    for rel in [record["asserted_against"]["table"]["path"], *prose_paths(record)]:
        for para in re.split(r"\n\s*\n", doc(rel)):
            flat = flatten(para)
            if "tenant restrictions v2" not in flat and "tenant restrictions" not in flat:
                continue
            hit = next((p for p in DEPENDENCY_PHRASINGS if p in flat), None)
            if hit is None:
                continue
            assert any(m in flat for m in RETRACTION_MARKERS), (
                f"{rel}: a paragraph states {hit!r} of tenant restrictions without "
                f"retracting it in the same paragraph (no {RETRACTION_MARKERS} present).\n"
                "Proxy enforcement is the v1 model. Under v2 it is one path of three.\n"
                f"Paragraph: {flat[:300]}..."
            )
