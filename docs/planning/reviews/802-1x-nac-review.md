---
document_id: REVIEW-802-1X-NAC
title: "Review — 802.1X / NAC references across the UIAO corpus"
status: draft
reviewer: "Claude (claude/review-802-11x-nac-RcySF)"
review_date: 2026-05-07
scope:
  - src/uiao/canon/data/control-library/{ac,ia,sa,sc,pe}/
  - src/uiao/modernization/directory-migration/
  - docs/modernization/
  - docs/customer-documents/modernization/
  - docs/narrative/
  - docs/planning/customer-documents-taxonomy.md
  - docs/docs/system-architecture.qmd
---

# Review — 802.1X / NAC references across the UIAO corpus

## 0. Scope and method

Inventoried every reference to `802.1X`, `802.1x`, `NAC`, `Network Admission
Control`, `Network Access Control`, and `MAB` / `MAC Authentication Bypass`
across the repository. Read each hit in context (control YAMLs, adapter
interfaces, customer-facing Quarto docs, narrative docs, and the migration
adapter registry). Findings below are grouped by category and ranked by
severity.

The literal string `802.11x` does not appear in the codebase — the branch
name's `802-11x` is a typo for `802-1x`. The IEEE standard is **802.1X**
(uppercase X).

Counts:

| Token        | Occurrences |
|--------------|-------------|
| `802.1X`     | 30          |
| `802.1x`     |  9          |
| `NAC` (word) |  2 (PE-3(1).yml, system-architecture.qmd) |

---

## 1. Findings — high severity (architectural / correctness)

### 1.1 The 802.1X authentication server is missing from `implemented_by` in AC-18 and IA-3

802.1X is a three-party protocol: supplicant, authenticator, authentication
server. The control YAMLs name the supplicant tooling (Intune for cert
provisioning, Entra ID for cert issuance) and the authenticator (Cisco
Catalyst), but **omit the AAA / RADIUS server entirely**.

- `src/uiao/canon/data/control-library/ac/AC-18.yml:11-15` — `implemented_by:
  entra-id, intune-mdm, cisco-catalyst, palo-alto-ngfw`. No RADIUS server.
- `src/uiao/canon/data/control-library/ia/IA-3.yml:11-15` — `implemented_by:
  entra-id, intune-mdm, cisco-catalyst, infoblox-ipam`. No RADIUS server.

The narrative in `IA-3.yml:42` states "Cisco Catalyst network infrastructure
enforces 802.1X authentication" — but Catalyst is the *authenticator*, not the
*authentication server*. Without ISE / NPS / Entra-RADIUS in the
`implemented_by` list, the control claim is structurally incomplete.

This is inconsistent with the modernization view, which lists the AAA tier
explicitly:

- `docs/modernization/adapters.qmd:134` — "Registered implementations: NPS
  (migration source), Cisco ISE, Aruba ClearPass, Entra RADIUS Proxy"
- `docs/customer-documents/modernization/client-server-to-hybrid-cloud/01-platform-foundation.qmd:175`
  — "Cisco ISE / NPS | Read-write | DM_030 | RADIUS policy, 802.1X,
  device-posture"

**Recommendation:** Add `cisco-ise` (and/or `nps`, depending on whether the
control narrative is post-migration or hybrid) to `implemented_by` in both
AC-18 and IA-3. Add a corresponding evidence artefact (e.g.
`cisco-ise-radius-authentication-logs`).

### 1.2 IA-3 attributes IoT MAC-bypass authentication to Infoblox

`src/uiao/canon/data/control-library/ia/IA-3.yml:28`:

> "802.1X with Entra ID device certificates; MAC-based fallback for IoT via
> Infoblox"

Infoblox is IPAM. It does not perform RADIUS authentication. MAC
Authentication Bypass (MAB) is a feature of the AAA server (Cisco ISE / NPS),
which *may* consult an Infoblox MAC reservation table as one input. The
PARAM is misleading.

The narrative two paragraphs down is correct: "authenticated via MAC
Authentication Bypass (MAB) with Infoblox-managed address reservations
**and placed into restricted network segments enforced by Cisco Catalyst
VLAN policies**" — but this still elides the AAA server.

**Recommendation:** Reword PARAM `ia_3_device_authentication_method` to
attribute the auth decision to ISE/NPS, with Infoblox as the MAC
inventory source.

### 1.3 SA-4(10) couples PIV authentication to wired 802.1X without justification

`src/uiao/canon/data/control-library/sa/SA-4(10).yml:62-64`:

> "Cisco ISE integrates with the PIV certificate validation chain to enforce
> 802.1X authentication for network access, requiring valid PIV certificate
> presentation for privileged workstations."

PIV is a smartcard-borne *user* credential. Wired 802.1X is normally machine
authentication using a *device* certificate (sometimes EAP-Chaining for
both). Requiring "PIV certificate presentation" at the L2 port for every
privileged workstation session is unusual and creates a hard dependency:
unplug the smartcard, lose the network. The control narrative does not
address whether this is supplicant-initiated EAP-TLS with the smartcard, or
some other mechanism, and the source documents (e.g. SP 800-157, SP 800-73)
that would justify this design are not cited.

**Recommendation:** Either (a) clarify the supplicant configuration and cite
the standards basis, or (b) remove the PIV-at-L2 claim and route SA-4(10)'s
PIV evidence through IA-2(11)/(12) (logical access) instead of network
admission.

### 1.4 PE-3(1) integrates physical badge readers with "Cisco ISE NAC" — uses retired product naming

`src/uiao/canon/data/control-library/pe/PE-3(1).yml:28` writes "Cisco ISE
NAC" and at line 47 expands it to "Cisco ISE Network Admission Control."

- "Network Admission Control" was Cisco's pre-2015 product family
  (NAC Appliance / NAC Framework), now end-of-life.
- "Cisco ISE" (Identity Services Engine) is the current product. Cisco
  positions it as their "Network Access Control" platform — different
  expansion from "Network Admission Control."

Conflating the two names is technically wrong and risks an audit finding
that ISE is being mis-described.

The integration claim itself is also strong: badge readers do not natively
publish session events to ISE. A typical implementation correlates badge
events through the SIEM (Sentinel here) and triggers Conditional Access via
risk signals. PE-3(1).status is `not-implemented`, which softens the claim,
but the design-of-record should still be reachable.

**Recommendation:** Replace "Cisco ISE NAC" / "Cisco ISE Network Admission
Control" with "Cisco ISE (Identity Services Engine), the network access
control platform." Describe the badge-to-ISE bridge in design terms (e.g.
"Sentinel correlates badge events; ISE consumes pxGrid risk attributes")
or explicitly mark the integration aspirational.

### 1.5 `cisco-ise` and `cisco-catalyst` are referenced as adapters but not registered

Six control YAMLs name `cisco-ise` and/or `cisco-catalyst` in `implemented_by`,
but neither id appears in the modernization or directory-migration adapter
registries:

- `src/uiao/modernization/directory-migration/migration-adapter-registry.yaml`
  registers RADIUS implementations as `nps`, `cisco-ise`, `aruba-clearpass`,
  `entra-radius` (under the `radius` adapter, not as standalone adapters).
- No `adapter-manifest.json` exists for either `cisco-ise` or
  `cisco-catalyst`. (`grep -r adapter-manifest` returns only IPAM,
  active_directory, and gcc_boundary_probe.)
- `docs/customer-documents/adapter-specs/` has folders for many vendors but
  no `cisco-ise` or `cisco-catalyst`.

This breaks the canon principle that every `implemented_by` token resolves
to a registered adapter with a manifest and trust-anchor declaration (see
the DRIFT-IDENTITY walker gate, commit `01863ea` / UIAO_110).

**Recommendation:** Either (a) register `cisco-ise` and `cisco-catalyst` as
first-class adapters with manifests under
`src/uiao/adapters/network/`, or (b) replace the control-library
`implemented_by` tokens with the registered RADIUS-implementation ids
(`cisco-ise` already exists nested under DM_030 — but the schema flattening
needs to be explicit) and add a Catalyst adapter or rename references to
the existing network/SD-WAN adapter.

---

## 2. Findings — medium severity (terminology / consistency)

### 2.1 Inconsistent casing: `802.1X` vs `802.1x`

30 hits use the IEEE-canonical `802.1X` (capital X). 9 hits in
`docs/customer-documents/modernization/pki-modernization.qmd` use lowercase
`802.1x`:

```
pki-modernization.qmd:439, 445, 453, 632, 642, 894, 1075, 1280, 1318
```

**Recommendation:** Normalize to `802.1X` throughout the corpus. The IEEE
standard title is "IEEE Std 802.1X" with capital X.

### 2.2 NAC expansion inconsistency

The acronym "NAC" appears twice and expands two different ways:

- `src/uiao/canon/data/control-library/pe/PE-3(1).yml:47` —
  "Cisco ISE Network Admission Control"
- `docs/docs/system-architecture.qmd:120` — "Cisco ISE (NAC)" (no
  expansion; reader infers "Network Access Control" from context)

There is no single canonical expansion in the repo. Combined with finding
1.4, this should be normalized.

**Recommendation:** Pick one expansion. Cisco's current usage is
"Network Access Control" (the security category) for ISE. Update PE-3(1)
and add the expansion to `system-architecture.qmd` on first use.

### 2.3 IA-3 narrative omits the supplicant configuration source

IA-3 says device certificates are issued by Entra ID and deployed by Intune
SCEP, but does not name the **supplicant** (the OS-side 802.1X client) or the
**Wi-Fi/wired profile** that wires the cert to the EAP method. AC-18 has the
same gap. IA-5(2):54-65 *does* name SCEP profile deployment correctly; AC-18
and IA-3 should cross-reference IA-5(2) for the supplicant deployment story.

**Recommendation:** Add a one-sentence supplicant pointer in AC-18 and IA-3
narratives ("Intune deploys 802.1X supplicant configuration profiles
(Wi-Fi / Wired) referencing the SCEP-issued device certificate; see
**IA-5(2)**.").

---

## 3. Findings — low severity (cross-references / structure)

### 3.1 G.6 (RADIUS / 802.1X modernization) has no customer-doc landing page

- `docs/planning/customer-documents-taxonomy.md:143` declares
  "G.6 RADIUS/802.1X modernization."
- `docs/customer-documents/modernization/network-transformation/index.qmd:26`
  references "G.6 RADIUS / 802.1X modernization — see DM_030 (§D.5)" —
  a text reference, not a link.
- The other G.x leaves (G.1, G.5) link to concrete docs
  (`modernization-specs/sdwan/sdwan.md`,
  `adapter-specs/palo-alto/palo-alto.qmd`).
- No `docs/customer-documents/modernization/network-transformation/g6-*.qmd`
  or equivalent exists.

The customer-facing taxonomy advertises G.6 as a deliverable, but no
deliverable exists. The internal `radius-adapter-interface.md` (DM_030) is
not exposed through a customer-facing page.

**Recommendation:** Either create a customer-doc stub (`g6-radius-802-1x.qmd`)
that surfaces the DM_030 adapter interface, or de-list G.6 from the
taxonomy until the doc lands.

### 3.2 The `radius-adapter-interface.md` lacks a registered Cisco-ISE manifest path

`migration-adapter-registry.yaml:54-62` registers four implementations under
the `radius` adapter (`nps`, `cisco-ise`, `aruba-clearpass`, `entra-radius`)
but `src/uiao/modernization/directory-migration/adapters/radius/` contains
only `radius-adapter-interface.md` — no per-vendor manifest files.

By contrast, the IPAM adapter (`adapters/ipam/`) has both `infoblox/` and
`bluecat/` subdirectories with `adapter-manifest.json` files. RADIUS should
follow the same pattern for symmetry.

**Recommendation:** Add `adapters/radius/{nps,cisco-ise,aruba-clearpass,
entra-radius}/adapter-manifest.json` stubs (DRAFT status), matching the IPAM
pattern.

### 3.3 IA-3 evidence id uses a different separator than its sibling YAMLs

`src/uiao/canon/data/control-library/ia/IA-3.yml:20` —
`cisco-catalyst-802-1x-device-authentication-logs` uses `-1x-` (lowercase x
plus hyphen). Surrounding evidence ids and other 802.1X-bearing strings use
either `802.1X` or no number at all. This evidence id will not match a
text search for `802.1X`.

**Recommendation:** Rename to `cisco-catalyst-802-1X-device-authentication-logs`
or `cisco-catalyst-radius-authentication-logs`.

### 3.4 Status mismatch: AC-18 / IA-3 marked `implemented`, dependents marked `not-implemented`

| Control     | Status            | Notes |
|-------------|-------------------|-------|
| AC-18       | implemented       | But authentication server unmodeled (1.1) |
| IA-3        | implemented       | Same as AC-18 |
| IA-5(2)     | not-implemented   | The cert lifecycle that AC-18/IA-3 depend on |
| SC-7(5)     | not-implemented   | Default-deny posture cited by IA-3 |
| SA-4(10)    | not-implemented   | PIV product procurement |
| PE-3(1)     | not-implemented   | Physical-logical bridge cited by ISE |

A control cannot be `implemented` if a control it materially depends on is
`not-implemented`. AC-18 and IA-3 inherit IA-5(2)'s certificate machinery; if
IA-5(2) is not implemented, the assertion that AC-18 is implemented is
inconsistent.

**Recommendation:** Either downgrade AC-18 / IA-3 to `partial` /
`compensating-control`, or upgrade IA-5(2) once the PKI lift is real. The
inconsistency is the ASMS thing an auditor will ask about.

---

## 4. Quick-fix summary (smallest deltas to land first)

In priority order:

1. **(1.2) IA-3 PARAM rewording** — one line in `IA-3.yml:28`. Move MAB
   attribution from Infoblox to ISE/NPS; keep Infoblox as the MAC reservation
   source.
2. **(2.1) Casing normalization** — sed-level change in
   `pki-modernization.qmd` (9 occurrences) from `802.1x` → `802.1X`.
3. **(1.4) PE-3(1) terminology fix** — replace "Cisco ISE NAC" /
   "Cisco ISE Network Admission Control" with "Cisco ISE (Identity Services
   Engine), Cisco's NAC platform" and pick one expansion of "NAC."
4. **(3.3) Evidence id rename** — `IA-3.yml:20` rename
   `802-1x` → `802-1X` (or drop the suffix entirely).
5. **(3.1) G.6 customer doc stub** — add a one-page `g6-radius-802-1x.qmd`
   that points to DM_030. Closes the taxonomy promise.

The structural items (1.1, 1.5, 3.4) require coordinated changes across
the control library, adapter registry, and `implemented_by` schema, and
should be planned as a single PR rather than incremental fixes.

---

## 5. Files inventoried

- `src/uiao/canon/data/control-library/ac/AC-18.yml`
- `src/uiao/canon/data/control-library/ia/IA-3.yml`
- `src/uiao/canon/data/control-library/ia/IA-5(2).yml`
- `src/uiao/canon/data/control-library/sa/SA-4(10).yml`
- `src/uiao/canon/data/control-library/sc/SC-7(5).yml`
- `src/uiao/canon/data/control-library/pe/PE-3(1).yml`
- `src/uiao/modernization/directory-migration/README.md`
- `src/uiao/modernization/directory-migration/adapters/radius/radius-adapter-interface.md`
- `src/uiao/modernization/directory-migration/migration-adapter-registry.yaml`
- `docs/modernization/adapters.qmd`
- `docs/modernization/directory-migration.qmd`
- `docs/customer-documents/modernization/network-transformation/index.qmd`
- `docs/customer-documents/modernization/access-plane/conditional-access-library.qmd`
- `docs/customer-documents/modernization/pki-modernization.qmd`
- `docs/customer-documents/modernization/client-server-to-hybrid-cloud/{00-introduction,01-platform-foundation,07-compute-objects}.qmd`
- `docs/customer-documents/modernization/uiao-modernization-program/07-client-server-to-hybrid-cloud-ref.qmd`
- `docs/narrative/governance-os-directory-migration.md`
- `docs/planning/customer-documents-taxonomy.md`
- `docs/docs/system-architecture.qmd`
