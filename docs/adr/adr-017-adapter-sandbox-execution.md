---
title: "ADR-017: Adapter Sandbox Execution"
adr: "ADR-017"
status: ACCEPTED
date: "2026-02-12"
deciders: ["UIAO Governance Board"]
---

# ADR-017: Adapter Sandbox Execution

## Status

ACCEPTED

## Context

Adapters run third-party or mission partner code that integrates with external systems. Without sandbox isolation, a malicious or buggy adapter could access other adapters' data, exhaust host resources, or make unauthorized network connections.

## Decision

All adapters execute in isolated sandboxes with: process isolation (dedicated PID namespace), network isolation (default-deny outbound), filesystem isolation (read-only shared schemas, ephemeral writable scratch space), and resource limits (CPU and memory quotas from registration schema). Sandbox escapes are classified as CRITICAL drift events and trigger immediate adapter suspension. See Appendix A-02 for the full sandbox specification.

## Consequences

**Positive:**
- Adapter failures and misbehavior are contained within their sandbox
- Network default-deny prevents unauthorized data exfiltration
- Sandbox resource limits prevent denial-of-service by misbehaving adapters

**Negative:**
- Sandbox infrastructure adds operational complexity and overhead
- Adapters have limited access to shared resources — some legitimate integrations may require explicit sandbox rule exceptions (governed by Governance Plane)
