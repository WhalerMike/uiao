"""OrgTree canon + codebook loader.

Narrative canon lives in MOD_A..MOD_Z markdown files in this directory; the
executable canon is :mod:`uiao.modernization.orgtree.codebook`, which loads
``canon/data/orgpath/codebook.yaml`` and validates it against
``schemas/orgpath/codebook.schema.json``.
"""

from .codebook import (
    Codebook,
    CodebookEntry,
    CodebookValidationError,
    DeprecatedEntry,
    load_codebook,
)

__all__ = [
    "Codebook",
    "CodebookEntry",
    "CodebookValidationError",
    "DeprecatedEntry",
    "load_codebook",
]
