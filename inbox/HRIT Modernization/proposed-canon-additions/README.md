# Proposed Canon Additions — HRIT IAM Gap Closure

> **Status:** DRAFT — `inbox/` content, not canon. Each ADR is independently
> mergeable; the bundle as a whole closes the four gaps identified in
> [`../HRIT-IAM-Findings.md`](../HRIT-IAM-Findings.md) §9.
>
> **Created:** 2026-05-04
>
> **Source mandate:** OPM Federal HRIT Modernization Solicitation 24322626R0007 (Amd 4).

---

## What this bundle is

Four ADR drafts — labeled **ADR-A** through **ADR-D** — that propose canon
additions required to model the OPM Federal HRIT Modernization IAM contract.
These are drafts because canon edits flow through the canon-change process
declared in `AGENTS.md` Operating Rule and repo invariant **I5**:

> **I5. Canon changes flow through the canon-change process.**
> Adding, modifying, retiring, or superseding anything under
> `src/uiao/canon/` requires:
> - A new `UIAO_NNN` allocation in `document-registry.yaml` (for new docs)
> - A new ADR in `src/uiao/canon/adr/` (for doctrinal changes)
> - Governance review

These drafts have **not** been allocated UIAO_NNN or ADR-NNN identifiers —
that allocation happens at canon-merge time by the registry steward.

---

## The four ADRs

| File | Closes gap | Touched canon on merge |
|---|---|---|
| [`ADR-A-saml-trust-anchor.md`](ADR-A-saml-trust-anchor.md) | SAML as a third trust-anchor type alongside mTLS and OIDC/JWT | `specs/application-identity-model.md` (UIAO_129 §2 binding #4); `schemas/adapter-registry.schema.json` |
| [`ADR-B-piv-usaccess-adapter.md`](ADR-B-piv-usaccess-adapter.md) | PIV / USAccess as the federal-personnel trust-anchor authority | `adapter-registry.yaml` (new `piv-usaccess` reserved slot) |
| [`ADR-C-opm-azure-apim-adapter.md`](ADR-C-opm-azure-apim-adapter.md) | OPM-hosted Azure APIM as a named Authority-Plane component | `modernization-registry.yaml` (new `opm-azure-apim` reserved slot); UIAO_129 §3; UIAO_130 §2 |
| [`ADR-D-single-ato-reciprocity.md`](ADR-D-single-ato-reciprocity.md) | Multi-tenant single-ATO model formalized as canon spec | New `specs/single-ato-reciprocity-model.md` (UIAO_NNN allocation); UIAO_112 cross-ref |

## Dependency order

ADR-A is the only one with no dependencies on the others. ADR-B and ADR-C
both reference ADR-A. ADR-D references all three. Suggested merge order:

```
ADR-A → ADR-B → ADR-C → ADR-D
```

But each can be reviewed and merged independently of the others — the
references are non-blocking citations, not hard dependencies.

---

## What changes if all four merge

After merge, the canon will be able to express the full HRIT IAM contract
end-to-end:

1. **OPM Entra ID** as the federal IdP — already canonized via `entra-id`
   adapter (no change needed).
2. **SAML federation** as the bid-window contractual trust-anchor type —
   ADR-A.
3. **PIV / USAccess** as the federal-personnel credential authority —
   ADR-B.
4. **OPM Azure APIM** as the centralized API-gateway enforcement surface —
   ADR-C.
5. **Single OPM ATO with per-agency reciprocity** as the authorization model
   — ADR-D.

Combined with existing canon (`entra-id`, `cyberark`, `terraform`,
`infoblox`, `service-now`, the OrgTree UIAO_151–UIAO_164 stack, Spec2-D3.x
HR-driven IAM), UIAO would have **complete contractual coverage** of the
HRIT 24322626R0007 IAM mandate.

---

## What this bundle does NOT do

- **Does not modify** `src/uiao/canon/` or any of the registries. That is a
  governance-board action, not an inbox-draft action.
- **Does not allocate** UIAO_NNN identifiers or ADR-NNN numbers. Those are
  registry-steward decisions at merge time.
- **Does not implement** any adapter code. Each adapter slot is `reserved`
  status; activation requires its own per-adapter ADR (modeled on
  ADR-035) per the three-stage lifecycle: canon → docs → impl.
- **Does not write per-agency runbooks.** A separate
  Federal-HRIT-Integration-Runbook (Spec2-D6.x candidate, mentioned in
  HRIT-IAM-Findings §11) would name USAccess, NFC EmpowHR, Treasury HR
  Connect, DCPDS, USA Staffing, GRB, eOPF as concrete instances of the
  Spec2-D3.1 pattern. That is a follow-up, not part of this bundle.

---

## Companion document

[`../HRIT-IAM-Findings.md`](../HRIT-IAM-Findings.md) is the full analysis
of the HRIT IAM contract that produced these four gap-closure proposals.
Read it first if you want the contractual context behind each ADR.

## Canon files referenced (post-merge targets)

| Canon file | Currently | After merge |
|---|---|---|
| `src/uiao/canon/specs/application-identity-model.md` | UIAO_129 v1.0 | v1.1 (SAML added; APIM enforcement clarified) |
| `src/uiao/canon/specs/application-identity-onboarding-runbook.md` | UIAO_130 v1.0 | v1.1 (APIM in Authority Plane preconditions) |
| `src/uiao/canon/specs/single-ato-reciprocity-model.md` | (does not exist) | **NEW** — UIAO_NNN |
| `src/uiao/canon/adapter-registry.yaml` | 16 entries | 17 entries (`piv-usaccess` reserved) |
| `src/uiao/canon/modernization-registry.yaml` | 19 entries | 20 entries (`opm-azure-apim` reserved) |
| `src/uiao/schemas/adapter-registry/adapter-registry.schema.json` | trust-anchor enum: `mtls`, `oidc` | adds `saml` |
| `src/uiao/canon/document-registry.yaml` | current allocation | +1 UIAO_NNN; +4 ADR-NNN |
| `src/uiao/canon/specs/Spec2-D3.1-APIDrivenInboundProvisioningArchitecture.md` | §11 references HRIT Req #5 | Optional follow-up: cross-ref the four new ADRs in §11 |
