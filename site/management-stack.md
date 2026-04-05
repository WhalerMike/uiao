---
title: "UIAO Management Stack"
version: "1.0"
classification: "CUI/FOUO"
---

# UIAO Management Stack

**Version 1.0**

---

## 1. Overview

The UIAO Management Stack defines the FedRAMP-authorized platforms that provide incident lifecycle management, endpoint configuration enforcement, and continuous authorization support. These platforms operate alongside the core UIAO vendor stack (Cisco, Infoblox, Microsoft Identity) to deliver a complete operational management capability.

The following diagram shows how the management stack integrates with the broader UIAO architecture through the telemetry and identity planes.

<img src="assets/images/mermaid/diagram_1.png" alt="diagram_1" />

---



---



---

## 4. Vendor Logic Processing

The following diagram illustrates how the UIAO data layer processes management stack configurations through the Jinja2 rendering pipeline to produce vendor-specific outputs.

<img src="assets/images/mermaid/diagram_2.png" alt="diagram_2" />

---

*Generated from UIAO data layer — Management Stack v1.0*