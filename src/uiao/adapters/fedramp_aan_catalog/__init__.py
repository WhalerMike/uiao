"""FedRAMP AAN Evidence Catalog — Conformance Adapter.

Maps the Federal Application-Aware Networking (AAN) series artifacts
(Parts 1–13) to their governing NIST SP 800-53 Rev 5 controls and
FedRAMP 20x KSI categories across the six active Conformance Adapter
surface slots.

Surface slots (control-planes.yml):
  1  identity   Parts 3, 4, 7          KSI-IAM
  2  addressing Part 1                 KSI-PIY / KSI-CNA
  3  network    Parts 2, 6             KSI-CNA
  4  telemetry  Parts 8, 9, 10         KSI-MLA
  5  endpoint   Parts 7, 8             KSI-PIY
  6  security   Parts 8, 10, 12, 13    KSI-CMT / KSI-SCR

Evidence binding files live in mappings/slot-0N-*.yaml.
Registry entry: src/uiao/canon/adapter-registry.yaml — id: fedramp-aan-catalog

Canon references:
    - inbox/Application Aware Networking/ (AAN document series)
    - src/uiao/canon/data/control-planes.yml (slot definitions)
    - src/uiao/adapters/fedramp_cr26_catalog/mappings/ksi-mapping.yaml (KSI rules)
    - inbox/Application Aware Networking/federal-aan-conmon-gap-roadmap.md (roadmap)
"""

ADAPTER_ID: str = "fedramp-aan-catalog"
STATUS: str = "active"
SURFACE_SLOTS_BOUND: tuple[int, ...] = (1, 2, 3, 4, 5, 6)
