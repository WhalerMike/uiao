"""OrgTree canon + codebook loader.

Per ADR-078, the OrgTree corpus was reset to Model C (15-facet multi-
attribute) and the speculative Model A consumer modules (admin-units,
device-planes, dynamic-groups, policy-targets, drift-engine-config)
plus their adapter wrappers were retired. The Model C consumer
rebuilds will land in a follow-up Phase 5 PR.

The surviving module here is :mod:`~uiao.modernization.orgtree.codebook`
which loads ``canon/data/orgpath/codebook.yaml`` (UIAO_151) and
validates it against ``schemas/orgpath/codebook.schema.json``. The
loader exposes a per-facet :class:`Codebook` / :class:`Facet` /
:class:`FacetValue` API.
"""

from .codebook import (
    Codebook,
    CodebookValidationError,
    DeprecatedFacetValue,
    Facet,
    FacetValue,
    load_codebook,
)

__all__ = [
    "Codebook",
    "CodebookValidationError",
    "DeprecatedFacetValue",
    "Facet",
    "FacetValue",
    "load_codebook",
]
