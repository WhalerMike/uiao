# UIAO Release Engineering & Distribution Layer

## Overview

The UIAO Release Engineering & Distribution Layer defines how UIAO is versioned, built, released, distributed, upgraded, and supported across Commercial Cloud and GCC-Moderate. This is the layer that turns UIAO from "a system that works" into a system that ships.

---

## 1. Release Channels

UIAO ships through four release channels, each with strict guarantees.

### 1.1 Stable Channel

- Updated monthly
- Fully tested
- Golden-file validated
- Spec-pinned
- Recommended for enterprises

### 1.2 LTS (Long-Term Support) Channel

- Updated annually
- Security patches only
- No breaking changes
- Required for GCC-Moderate

### 1.3 Edge Channel

- Updated weekly
- Experimental features
- New control packs
- New KSI rules
- Not for production

### 1.4 FIPS-Aligned Channel

- Cryptographic primitives restricted to FIPS-validated algorithms
- Required for federal environments
- Mirrors Stable with additional constraints

---

## 2. Versioning Strategy

UIAO uses multi-axis semantic versioning:

```
UIAO_VERSION = CORE.MODULE.SPEC
```

| Axis | Trigger |
|------|---------|
| CORE | Major architectural changes, breaking changes, new planes or data models |
| MODULE | New features, new control packs, new enforcement adapters |
| SPEC | Spec changes, schema updates, KSI semantics updates |

Example: `3.2.5` where CORE=3, MODULE=2, SPEC=5

Spec version increments force golden-file regeneration.

---

## 3. Artifact Signing & Verification

All UIAO artifacts are signed and verifiable.

### 3.1 Signed Artifacts

- Python wheels
- Control packs
- KSI rule bundles
- Evidence schemas
- OSCAL fragments
- Plugin manifests

### 3.2 Signing Keys

- Ed25519 for speed and security
- Rotated annually
- Stored in HSM/KMS

### 3.3 Verification

Every artifact includes:
- Signature
- Hash
- Spec version
- Build metadata

CI rejects unsigned or mismatched artifacts.

---

## 4. Distribution Model

UIAO supports three distribution modes.

### 4.1 Commercial Cloud Distribution

- PyPI private index
- Container registry
- Plugin marketplace
- Automatic updates (opt-in)

### 4.2 GCC-Moderate Distribution

- No marketplace
- No automatic updates
- Signed tarballs
- Offline control pack bundles
- Evidence schemas bundled with release

### 4.3 Air-Gap Distribution

- Full release bundle
- No external dependencies
- All schemas, rules, packs included
- Offline verification tools

This ensures UIAO can run in fully disconnected environments.

---

## 5. Upgrade Paths

UIAO defines three upgrade paths.

### 5.1 Forward-Compatible Upgrades

Allowed when:
- CORE unchanged
- MODULE increments
- SPEC increments

Evidence and OSCAL regenerate automatically.

### 5.2 Backward-Compatible Upgrades

Allowed when:
- SPEC unchanged
- MODULE increments
- Control packs remain compatible

Golden-file tests ensure safety.

### 5.3 Cross-Version Upgrades

Allowed only when:
- CORE increments
- Migration scripts provided
- Evidence re-normalized
- KSI re-evaluated
- OSCAL regenerated

This is the rare path.

---

## 6. Compatibility Guarantees

UIAO guarantees compatibility across four dimensions.

### 6.1 Spec Compatibility

- SPEC increments may break compatibility
- SPEC decrements never allowed

### 6.2 Control Pack Compatibility

- Control packs declare compatible KSI and OSCAL versions
- CI enforces compatibility matrix

### 6.3 Plugin Compatibility

Plugins must declare:
- Supported UIAO versions
- Supported control packs
- Supported evidence schemas

Plugins failing certification are quarantined.

### 6.4 Evidence Compatibility

Evidence bundles include:
- Schema version
- Hash
- Provenance manifest

Older evidence can be re-normalized.

---

## 7. Release Governance

UIAO releases follow a strict governance model.

### 7.1 Release Approvals

Every release requires:
- Engineering approval
- Security approval
- Spec approval
- Control pack approval

### 7.2 Freeze Windows

- 7-day freeze before Stable release
- 30-day freeze before LTS release

### 7.3 Rollback Protocol

Rollback requires:
1. Revert artifacts
2. Revert control packs
3. Revert KSI rules
4. Re-run golden-file tests
5. Re-publish previous release

### 7.4 Release Notes

Each release includes:
- Breaking changes
- Spec changes
- Control pack changes
- Plugin compatibility changes
- Migration instructions

---

## Summary: What This Layer Provides

| Component | Purpose |
|-----------|--------|
| Release Channels | Stable, LTS, Edge, FIPS-Aligned with strict guarantees |
| Versioning Strategy | Multi-axis semantic versioning tied to spec changes |
| Artifact Signing | Ed25519 signatures with HSM/KMS key management |
| Distribution Model | Commercial, GCC-Moderate, and air-gap distribution modes |
| Upgrade Paths | Forward, backward, and cross-version upgrade protocols |
| Compatibility Guarantees | Spec, control pack, plugin, and evidence compatibility |
| Release Governance | Approvals, freeze windows, rollback, and release notes |

This layer makes UIAO deployable, upgradable, certifiable, and safe for regulated environments.

---

## Next Layer

The next layer is the **UIAO Runtime Optimization & Performance Engineering Layer**, covering:
- Pipeline performance
- Evidence ingestion scaling
- KSI evaluation optimization
- Drift engine performance
- OSCAL generation optimization
- Caching strategy
- Memory model
