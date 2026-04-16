UIAO Adapter Development Guide

**Document ID:** UIAO_ADG_001

**Version:** 1.0.0

**Classification:** Controlled

**Date:** 2026-04-11

1\. Overview

Adapters are the primary mechanism for ingesting compliance data from external sources into the UIAO pipeline. Each adapter transforms source-specific data into NormalizedClaim objects that flow through the 4-plane pipeline. This guide covers the adapter interface, implementation patterns, testing requirements, and distribution options.

2\. Adapter Interface

2.1 ComplianceAdapter ABC

from abc import ABC, abstractmethod from typing import Any class ComplianceAdapter(ABC): \"\"\"Base class for all UIAO compliance data adapters.\"\"\" \@abstractmethod def ingest(self, source_path: str) -\> dict\[str, Any\]: \"\"\" Load raw data from the source. Args: source_path: Path to the source data file or URL. Returns: Raw data dictionary. Raises: FileNotFoundError: If source_path does not exist. ValueError: If source data is malformed. \"\"\" \... \@abstractmethod def normalize(self, raw_data: dict\[str, Any\]) -\> list\[\"NormalizedClaim\"\]: \"\"\" Convert raw data to NormalizedClaim objects. Args: raw_data: Output from ingest(). Returns: List of NormalizedClaim objects. Raises: ValueError: If data cannot be normalized. \"\"\" \... \@abstractmethod def validate(self, claims: list\[\"NormalizedClaim\"\]) -\> bool: \"\"\" Validate normalized claims for completeness and correctness. Args: claims: List of NormalizedClaim objects. Returns: True if all claims are valid. Raises: ValidationError: If any claim is invalid. \"\"\" \... \@abstractmethod def metadata(self) -\> dict\[str, str\]: \"\"\" Return adapter metadata. Returns: Dict with keys: name, version, author, description, source_type. \"\"\" \... \@abstractmethod def capabilities(self) -\> list\[str\]: \"\"\" Return list of supported products/features. Returns: List of product short codes this adapter can process. \"\"\" \...

2.2 NormalizedClaim Contract

  --------------------------------------------------------------------------------------------
  **Field**          **Type**      **Required**   **Description**
  ------------------ ------------- -------------- --------------------------------------------
  claim_id           str           Yes            Unique claim identifier (DNS-style)

  source             str           Yes            Source adapter name

  product            str           Yes            Product short code

  rule_id            str           Yes            Source rule identifier

  result             str           Yes            pass, fail, warn, error, not_applicable

  severity           str           Yes            critical, high, medium, low, informational

  title              str           Yes            Short finding title

  description        str           Yes            Full finding description

  control_mappings   list\[str\]   Yes            NIST 800-53 control identifiers

  collected_at       str           Yes            ISO 8601 timestamp of data collection
  --------------------------------------------------------------------------------------------

2.3 Claim ID Convention

Claim IDs follow a DNS-style naming convention:

{source}.{product}.{rule_id}

Examples:

- scuba.exo.MS.EXO.1.1v1

- qualys.vmdr.QID-12345

- defender.vuln.CVE-2026-1234

- csv.generic.CUSTOM-001

  -----------------------------------------------------------------------
  **Segment**   **Description**                 **Format**
  ------------- ------------------------------- -------------------------
  source        Adapter name                    lowercase, alphanumeric

  product       Product short code              lowercase, alphanumeric

  rule_id       Source-native rule identifier   Preserved from source
  -----------------------------------------------------------------------

3\. Step-by-Step Example: Qualys VMDR Adapter

3.1 Project Structure

src/uiao_core/adapters/qualys_vmdr/ ├── \_\_init\_\_.py ├── adapter.py ├── mappings.py └── README.md

3.2 Implementation

\# src/uiao_core/adapters/qualys_vmdr/adapter.py import json from datetime import datetime, timezone from typing import Any from uiao_core.abstractions import ComplianceAdapter from uiao_core.models import NormalizedClaim QUALYS_SEVERITY_MAP = { 1: \"informational\", 2: \"low\", 3: \"medium\", 4: \"high\", 5: \"critical\", } QUALYS_STATUS_MAP = { \"ACTIVE\": \"fail\", \"FIXED\": \"pass\", \"RE-OPENED\": \"fail\", \"NEW\": \"fail\", } class QualysVMDRAdapter(ComplianceAdapter): \"\"\"Adapter for Qualys VMDR vulnerability scan data.\"\"\" def ingest(self, source_path: str) -\> dict\[str, Any\]: with open(source_path, \"r\") as f: data = json.load(f) if \"HOST_LIST_VM_DETECTION_OUTPUT\" not in data: raise ValueError(\"Invalid Qualys VMDR export format\") return data def normalize(self, raw_data: dict\[str, Any\]) -\> list\[NormalizedClaim\]: claims = \[\] hosts = raw_data\[\"HOST_LIST_VM_DETECTION_OUTPUT\"\]\[\"RESPONSE\"\]\[\"HOST_LIST\"\]\[\"HOST\"\] if isinstance(hosts, dict): hosts = \[hosts\] for host in hosts: detections = host.get(\"DETECTION_LIST\", {}).get(\"DETECTION\", \[\]) if isinstance(detections, dict): detections = \[detections\] for det in detections: qid = det\[\"QID\"\] severity = int(det.get(\"SEVERITY\", 2)) status = det.get(\"STATUS\", \"ACTIVE\") claim = NormalizedClaim( claim_id=f\"qualys.vmdr.QID-{qid}\", source=\"qualys\", product=\"vmdr\", rule_id=f\"QID-{qid}\", result=QUALYS_STATUS_MAP.get(status, \"fail\"), severity=QUALYS_SEVERITY_MAP.get(severity, \"medium\"), title=det.get(\"TITLE\", f\"Qualys QID {qid}\"), description=det.get(\"RESULTS\", \"No description available\"), control_mappings=self.\_map_controls(qid), collected_at=datetime.now(timezone.utc).isoformat(), ) claims.append(claim) return claims def validate(self, claims: list\[NormalizedClaim\]) -\> bool: for claim in claims: if not claim.claim_id.startswith(\"qualys.vmdr.\"): raise ValueError(f\"Invalid claim_id prefix: {claim.claim_id}\") if claim.result not in (\"pass\", \"fail\", \"warn\", \"error\", \"not_applicable\"): raise ValueError(f\"Invalid result: {claim.result}\") return True def metadata(self) -\> dict\[str, str\]: return { \"name\": \"qualys-vmdr\", \"version\": \"1.0.0\", \"author\": \"UIAO Team\", \"description\": \"Qualys VMDR vulnerability scanner adapter\", \"source_type\": \"vulnerability_scan\", } def capabilities(self) -\> list\[str\]: return \[\"vmdr\"\] def \_map_controls(self, qid: str) -\> list\[str\]: \"\"\"Map Qualys QID to NIST 800-53 controls.\"\"\" \# Simplified mapping - production would use a full lookup table return \[\"SI-2\", \"RA-5\"\]

3.3 Severity Mapping Tables

**Qualys Severity Mapping:**

  --------------------------------------
  **Qualys Level**   **UIAO Severity**
  ------------------ -------------------
  1                  informational

  2                  low

  3                  medium

  4                  high

  5                  critical
  --------------------------------------

**Defender Severity Mapping:**

  ----------------------------------------
  **Defender Level**   **UIAO Severity**
  -------------------- -------------------
  Informational        informational

  Low                  low

  Medium               medium

  High                 high

  Critical             critical
  ----------------------------------------

**Generic CSV Severity Mapping:**

  --------------------------------------------
  **CSV Value**            **UIAO Severity**
  ------------------------ -------------------
  1, info, informational   informational

  2, low                   low

  3, med, medium           medium

  4, high                  high

  5, crit, critical        critical
  --------------------------------------------

3.4 Status Mapping

  ------------------------------------------------------------
  **UIAO Result**   **Definition**
  ----------------- ------------------------------------------
  pass              Control requirement is met

  fail              Control requirement is not met

  warn              Control is partially met or needs review

  error             Assessment could not determine status

  not_applicable    Control does not apply to this context
  ------------------------------------------------------------

4\. Registration

4.1 YAML Registration

\# config/adapters.yaml adapters: qualys_vmdr: module: uiao_core.adapters.qualys_vmdr.adapter class: QualysVMDRAdapter enabled: true priority: 5

4.2 Entry Point Registration

\# pyproject.toml \[project.entry-points.\"uiao_core.adapters\"\] qualys_vmdr = \"uiao_core.adapters.qualys_vmdr.adapter:QualysVMDRAdapter\"

5\. Testing Requirements

5.1 Required Test Scenarios

  ---------------------------------------------------------------------------------------
  **\#**   **Scenario**                                         **Tier**   **Required**
  -------- ---------------------------------------------------- ---------- --------------
  1        Valid input produces correct NormalizedClaim count   T1         Yes

  2        Each claim has valid claim_id format                 T1         Yes

  3        Severity mapping is correct for all levels           T1         Yes

  4        Status mapping is correct for all values             T1         Yes

  5        Missing optional fields handled gracefully           T1         Yes

  6        Malformed input raises ValueError                    T1         Yes

  7        Empty input produces empty claim list                T1         Yes

  8        File not found raises FileNotFoundError              T1         Yes

  9        Metadata returns all required fields                 T1         Yes

  10       Capabilities returns non-empty list                  T1         Yes

  11       Deterministic output for same input                  T5         Yes

  12       Integration with Plane 1 transformer                 T2         Yes

  13       Large dataset performance (\< 5s for 10K findings)   T1         Recommended

  14       Control mapping coverage for all QIDs                T1         Recommended
  ---------------------------------------------------------------------------------------

5.2 Test Template

\"\"\"Tests for Qualys VMDR Adapter.\"\"\" import json import pytest from uiao_core.adapters.qualys_vmdr.adapter import QualysVMDRAdapter \@pytest.fixture def adapter(): return QualysVMDRAdapter() \@pytest.fixture def sample_data(): return { \"HOST_LIST_VM_DETECTION_OUTPUT\": { \"RESPONSE\": { \"HOST_LIST\": { \"HOST\": { \"IP\": \"10.0.0.1\", \"DETECTION_LIST\": { \"DETECTION\": \[ { \"QID\": \"12345\", \"SEVERITY\": \"4\", \"STATUS\": \"ACTIVE\", \"TITLE\": \"Test Vulnerability\", \"RESULTS\": \"Found on port 443\", } \] }, } } } } } def test_normalize_valid_data(adapter, sample_data): claims = adapter.normalize(sample_data) assert len(claims) == 1 assert claims\[0\].claim_id == \"qualys.vmdr.QID-12345\" assert claims\[0\].severity == \"high\" assert claims\[0\].result == \"fail\" def test_normalize_empty_detections(adapter): data = { \"HOST_LIST_VM_DETECTION_OUTPUT\": { \"RESPONSE\": {\"HOST_LIST\": {\"HOST\": {\"IP\": \"10.0.0.1\"}}} } } claims = adapter.normalize(data) assert len(claims) == 0 def test_ingest_invalid_format(adapter, tmp_path): bad_file = tmp_path / \"bad.json\" bad_file.write_text(\'{\"invalid\": \"data\"}\') with pytest.raises(ValueError): adapter.ingest(str(bad_file)) def test_metadata_complete(adapter): meta = adapter.metadata() assert \"name\" in meta assert \"version\" in meta assert \"author\" in meta def test_deterministic_output(adapter, sample_data): claims_1 = adapter.normalize(sample_data) claims_2 = adapter.normalize(sample_data) assert claims_1 == claims_2

6\. Performance Guidelines

  -------------------------------------------
  **Metric**                     **Target**
  ------------------------------ ------------
  Ingest time (1K findings)      \< 1s

  Normalize time (1K findings)   \< 2s

  Validate time (1K claims)      \< 1s

  Memory usage (10K findings)    \< 100MB
  -------------------------------------------

**Performance tips:**

- Use streaming JSON parsing for files \> 100MB

- Pre-compile regex patterns used in normalization

- Cache control mapping lookups

- Use \_\_slots\_\_ on high-volume data classes

7\. Distribution Options

7.1 Built-in Adapter

Place adapter code under src/uiao_core/adapters/ and register in config/adapters.yaml. This is the preferred method for adapters maintained by the core team.

7.2 Plugin Package

\# pyproject.toml for external adapter package \[project\] name = \"uiao-adapter-qualys\" version = \"1.0.0\" dependencies = \[\"uiao-core\>=2.0.0\"\] \[project.entry-points.\"uiao_core.adapters\"\] qualys_vmdr = \"uiao_adapter_qualys.adapter:QualysVMDRAdapter\"

8\. Pre-Submission Checklist

57. Adapter implements all 5 ComplianceAdapter methods

58. All 12 required test scenarios pass

59. Deterministic output verified

60. Severity mapping table documented

61. Status mapping table documented

62. Claim ID follows DNS-style convention

63. Control mappings reference valid NIST 800-53 identifiers

64. Metadata includes all required fields

65. Performance targets met

66. README.md included with usage instructions

67. Registered in config/adapters.yaml or via entry point

68. No external network calls during normalize() or validate()

69. Error handling follows UIAO error code conventions

70. Code passes ruff check with zero errors

Document Revision History

  ---------------------------------------------------------------
  **Version**   **Date**     **Author**         **Description**
  ------------- ------------ ------------------ -----------------
  1.0.0         2026-04-11   Michael Stratton   Initial release

  ---------------------------------------------------------------

> **

> **SSOT Reference:** See /ssot/UIAO-SSOT.md
