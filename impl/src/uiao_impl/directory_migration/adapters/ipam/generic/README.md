# Generic IPAM Adapter

**Status:** Placeholder | **Adapter Type:** ipam

## Purpose

Provides a vendor-neutral IPAM adapter implementation for any RFC-compliant IPAM system
exposing a REST API. Use this adapter when the deployment does not use InfoBlox or BlueCat.

## Requirements

- Must satisfy all capabilities defined in `ipam-adapter-interface.md`
- - Must provide a conforming `adapter-manifest.json`
  - - Must support DNS, DHCP, and IP address management governance
    - - Must support side-by-side operation with AD-integrated DNS during hybrid window
     
      - ## Status
     
      - This adapter is a scaffold. Implementation details will be added as vendor-neutral
      - patterns are validated against the IPAM Adapter Interface contract.
      - 
