"""
pki/__init__.py
---------------
UIAO Modernization Adapter: PKI / Certificate Services.

Registers this adapter with the UIAO substrate. Modernization-class
adapter that surveys the certificate estate during AD → Entra ID
migration; companion to the (conformance-class) OCSP/CRL telemetry
adapter at ``src/uiao/adapters/pkica_adapter.py``.

Adapter registration
--------------------
  adapter_id:    pki-certificate-inventory-v1
  class:         modernization
  mission_class: identity
  canon_ref:     ``src/uiao/modernization/directory-migration/adapters/pki/pki-adapter-interface.md`` (DM_020)

This package currently ships the **interface stub** for the modernization
adapter — the dataclasses and extraction contract that match the canon
markdown specification. Live ADCS / DigiCert / Entrust / Entra-CBA
connection logic is deferred to a future PR; the contract is exercised
today against synthetic input.

The interface stub pattern mirrors the SPN inventory shape introduced
in PR #395 (``active_directory/survey.py::extract_spn_inventory``):

  - Typed dataclasses match the canon contract.
  - Extraction function takes a list of synthetic records + OrgPath
    indices, emits a phase-tagged inventory + drift findings.
  - No live external-system access in any test path.
"""

from __future__ import annotations

from .inventory import (
    PKI_DISCOVERY_AD_OBJECTS,
    PKI_DISCOVERY_OCSP,
    PKI_DISCOVERY_TEMPLATES,
    PKI_PHASE_POST_MIGRATION,
    PKI_PHASE_PRE_MIGRATION,
    PKI_PHASE_UNSPECIFIED,
    CertificateInventory,
    CertificateRecord,
    extract_certificate_inventory,
)

__all__ = [
    "CertificateInventory",
    "CertificateRecord",
    "PKI_DISCOVERY_AD_OBJECTS",
    "PKI_DISCOVERY_OCSP",
    "PKI_DISCOVERY_TEMPLATES",
    "PKI_PHASE_POST_MIGRATION",
    "PKI_PHASE_PRE_MIGRATION",
    "PKI_PHASE_UNSPECIFIED",
    "extract_certificate_inventory",
]

# Adapter manifest — consumed by modernization-registry.yaml validation
ADAPTER_ID = "pki-certificate-inventory-v1"
ADAPTER_CLASS = "modernization"
MISSION_CLASS = "identity"
