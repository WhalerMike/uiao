"""Single source for the OSCAL version UIAO declares on emitted artifacts.

Derived from compliance-trestle — the library the trestle-validated emitters
check their payloads against — so the declared ``oscal-version`` can never
disagree with the models used to validate it. Before this constant existed,
one package's emitters declared three different versions (1.0.4, 1.1.2, and
trestle's actual pin) across a single authorization package's documents.
"""

from __future__ import annotations

from trestle.oscal import OSCAL_VERSION

__all__ = ["OSCAL_VERSION"]
