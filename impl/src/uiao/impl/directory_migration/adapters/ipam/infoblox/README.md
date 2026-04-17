# InfoBlox NIOS Adapter

**Adapter ID:** `infoblox-nios-8x`
**Type:** IPAM
**Status:** Registered  Federal Preferred

## Overview
InfoBlox NIOS is the named IPAM solution in uiao-core for federal deployments. This adapter implements the IPAM Adapter Interface (`../ipam-adapter-interface.md`) for InfoBlox NIOS version 8.x and above.

## FedRAMP Authorization
- **FedRAMP Authorized:** Yes
- **Impact Level:** Moderate
- **CDM Integrated:** Yes

## Capabilities
All capabilities defined in the IPAM Adapter Interface are supported:
- DNS Record Governance
- DHCP Governance
- IP Address Management
- Side-by-side AD operation
- Event stream integration

## Configuration
See `adapter-manifest.json` for the machine-readable adapter registration.

## References
- IPAM Adapter Interface: `../ipam-adapter-interface.md`
- UIAO Core Doc 13: FIMF Adapter Registry