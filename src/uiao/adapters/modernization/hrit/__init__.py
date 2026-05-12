"""
hrit/__init__.py
----------------
UIAO Modernization Adapter: Federal HRIT Record Inventory.

Phase-tagged interface stub for inbound HR provisioning surveys —
companion to the AD survey (PR #395 `spn_inventory`) and PKI inventory
(PR #429 `certificate_inventory`) starters. Surveys canonical HR
records (per Spec2-D1.1) emitted by a federal HR system of record
and produces an HRRecordInventory artifact with drift findings for
records that cannot be bound to a verified organizational position.

Adapter registration
--------------------
  adapter_id:    hrit-record-inventory-v1
  class:         modernization
  mission_class: identity
  canon_ref:     Spec2-D1.1 Canonical HR Attribute Schema (UIAO_136 family)
                 Spec2-D6.1 Federal HRIT Integration Runbook

This package ships the **interface stub** today — the dataclasses and
extraction contract that match the Spec2-D1.1 canonical schema. Live
NFC EmpowHR / Treasury HR Connect / DCPDS / DOI IBC adapter
implementations are deferred to a future PR; the contract is exercised
today against synthetic input following the PR #395 + PR #429 pattern.
"""

from __future__ import annotations

from .inventory import (
    HRIT_DISCOVERY_DCPDS,
    HRIT_DISCOVERY_DOI_IBC,
    HRIT_DISCOVERY_NFC_EMPOWHR,
    HRIT_DISCOVERY_TREASURY_HR_CONNECT,
    HRIT_DISCOVERY_USA_STAFFING,
    HRIT_PHASE_POST_MIGRATION,
    HRIT_PHASE_PRE_MIGRATION,
    HRIT_PHASE_UNSPECIFIED,
    HRRecord,
    HRRecordInventory,
    extract_hrit_record_inventory,
)

__all__ = [
    "HRIT_DISCOVERY_DCPDS",
    "HRIT_DISCOVERY_DOI_IBC",
    "HRIT_DISCOVERY_NFC_EMPOWHR",
    "HRIT_DISCOVERY_TREASURY_HR_CONNECT",
    "HRIT_DISCOVERY_USA_STAFFING",
    "HRIT_PHASE_POST_MIGRATION",
    "HRIT_PHASE_PRE_MIGRATION",
    "HRIT_PHASE_UNSPECIFIED",
    "HRRecord",
    "HRRecordInventory",
    "extract_hrit_record_inventory",
]

# Adapter manifest — consumed by modernization-registry.yaml validation
ADAPTER_ID = "hrit-record-inventory-v1"
ADAPTER_CLASS = "modernization"
MISSION_CLASS = "identity"
