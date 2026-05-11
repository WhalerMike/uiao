# RFC-0026 forum engagement draft

**Status:** Pre-posting draft. Not yet posted to FedRAMP/community Discussion #130.
**Target forum:** [FedRAMP/community Discussion #130 — RFC-0026 (CA-7 Continuous Monitoring Expectations)](https://github.com/FedRAMP/community/discussions/130)
**Authored:** 2026-05-11
**Author:** WhalerMike (UIAO maintainer)
**Tone steer to author:** professional, not promotional. State facts + ask questions. Substrate-is-OSS framing rather than vendor positioning. Open the door for community input on specific open items rather than declaring positions.

---

## Pre-posting checklist (for the maintainer before pasting to the forum)

- [ ] Verify all referenced canon paths and ADR numbers are current as of post date
- [ ] Confirm the "Pathway 2 at effective date, pre-wired Pathway 1 as gated migration" claim still matches ADR-043 D1
- [ ] Confirm the enforcement-clock dates (2026-06-30, 2026-12-31, 2027-01-01, 2027-04-01, 2027-06-01) are current per Notice 0009
- [ ] Confirm the open-items list reflects actual unresolved questions (vs. ones since resolved in PRs)
- [ ] Decide whether to post under the WhalerMike handle or a project-specific identity
- [ ] Sanity-check the tone: no marketing language, no claims of features that haven't shipped

---

## Draft comment (for paste into GitHub Discussions)

---

## UIAO substrate — operational pathway plan for RFC-0026

Sharing an OSS-substrate response to RFC-0026 in case it helps the forum's working-through of CA-7 implementation patterns. UIAO is an open-source FedRAMP-Moderate reference architecture (Apache 2.0, GitHub: `WhalerMike/uiao`); this comment summarizes how the substrate's canon currently addresses both RFC-0026 requirements, where it has chosen Pathway 1 vs. Pathway 2, and the open questions where community input would be useful.

### Canon position

The substrate's canon decision is recorded in [ADR-043](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/adr/adr-043-fedramp-rfc-0026-ca7-integration.md) with operational mechanics in [UIAO_132](https://github.com/WhalerMike/uiao/blob/main/src/uiao/canon/specs/fedramp-rfc-0026-ca7-integration.md). Both landed 2026-04-21 (commit `93c0e122`); both are governed under the canon-change protocol.

Summary of ADR-043 D1: **Pathway 2 on both RV5-CA07-VLN and RV5-CA07-CCM at the effective date (2026-06-30); pre-wire Pathway 1 as a gated migration.** Rationale: Pathway 2 satisfies the explicit text of RFC-0026 with documented, testable mechanics today; Pathway 1 (VDR / CCM Balance Improvement Release) is the future-state path whose ingest contracts and trust-center API surface are still stabilizing.

### Operational mechanics

| RFC-0026 requirement | Substrate mechanism | Cadence |
|---|---|---|
| **RV5-CA07-VLN** — Vulnerability Reporting | Pathway 2: monthly OS / DB / Web / Container / Service Config scan adapter runs (`vuln-scan`, `patch-state`, `stig-compliance`, `scubagear` per `src/uiao/canon/adapter-registry.yaml`) + monthly POA&M assembly + annual IA-scan synthesis | Monthly (POA&M) + annual (IA scan) |
| **RV5-CA07-CCM** — Collaborative Continuous Monitoring | Pathway 2: monthly open ConMon cadence per the Rev5 Playbook; meeting cadence + agenda template held in `src/uiao/canon/compliance/reference/fedramp-rfc-0026/` | Monthly |
| **Pre-wired Pathway 1 (gated)** | VDR Balance Improvement Release adapter slot reserved in `modernization-registry.yaml`; activation gated on trust-center API contract stabilization | Continuous (when activated) |

The substrate's [evidence-as-byproduct claim](https://github.com/WhalerMike/uiao/blob/main/docs/customer-documents/whitepapers/federal-ssot-alignment.qmd) is that the POA&M, SSP narrative, and IA-scan synthesis emitted under Pathway 2 are produced deterministically from continuous adapter runs — not assembled retrospectively. The OSCAL output is byte-identical for the same `(tenant-state, canon-version, adapter-version)` triple per ADR-006.

### Roadmap

A public roadmap at [`docs/docs/uiao-rfc-0026-roadmap.qmd`](https://github.com/WhalerMike/uiao/blob/main/docs/docs/uiao-rfc-0026-roadmap.qmd) sequences eight enhancements (E1–E8) by enforcement-clock risk × implementation cost. Two design memos with all open questions resolved (Status: DRAFT — implementation PRs unblocked):

- **E1 — Connect.gov POA&M submission automation:** [design memo](https://github.com/WhalerMike/uiao/blob/main/docs/docs/uiao-rfc-0026-e1-connect-gov-design.qmd). Target delivery: 2026-10-31 (60-day buffer before 2027-01-01 enforcement). Decision: operator-in-the-loop with signed submission bundle (Option C); REST/SFTP variants deferred to a future trust-center adapter.
- **E5 — Multi-agency artifact distribution layer:** [design memo](https://github.com/WhalerMike/uiao/blob/main/docs/docs/uiao-rfc-0026-e5-multi-agency-design.qmd). Target delivery: 2026-11-30.

### Open questions where community input would help

Posting these because we'd rather hear the forum's thinking now than ship into an interpretation that diverges from how other agencies are implementing:

1. **Trust-center API ingest surface** — RFC-0026's Pathway 1 references FedRAMP-compatible trust centers for OSCAL ingest. UIAO_132 currently treats this as a separate future-enhancement slot (not part of Pathway 1 activation). Is the forum's working interpretation that "Pathway 1" includes trust-center ingest, or that trust-center ingest is a third operational mode parallel to the two pathways?
2. **Connect.gov portal mechanics** — E1's resolved-questions table chose operator-in-the-loop portal upload (Q1.1 Option C) on the basis that the public-doc surface for Connect.gov is portal-shaped and zero of 100+ Rev5 authorizations had used OSCAL ingest as of 2025. Has anyone in the forum shipped an automated Connect.gov submission they can describe at the contract-mechanics level?
3. **CCM cadence under Pathway 2** — the Rev5 Playbook says "monthly," but the playbook's text describes a meeting structure rather than a deliverable contract. UIAO is treating the cadence as monthly meeting + monthly deliverable (POA&M reconciliation, evidence drift summary, KSI report). Is that the right read, or does the forum interpret "CCM cadence" as just meeting cadence with deliverables left to AO discretion?
4. **GCC-Moderate boundary effects on continuous-monitoring evidence** — UIAO has documented a three-way compliance conflict ([B.1.1](https://github.com/WhalerMike/uiao/blob/main/docs/customer-documents/compliance/boundary-authorization/B1-1-gcc-moderate-three-way-conflict.qmd)) between TIC 3.0, the CISA ZTMM, and FedRAMP 20x continuous-monitoring assumptions for agencies running M365 GCC-Moderate on Azure Commercial infrastructure. Is the forum aware of this conflict shape, and is there a coordinated response in the RFC-0026 working group?

### How to engage

UIAO_132 and ADR-043 are open canon — changes follow the canon-change protocol in `CONTRIBUTING.md`. Issues and PRs welcome at [`WhalerMike/uiao`](https://github.com/WhalerMike/uiao). For substrate-architecture questions, [`AGENTS.md`](https://github.com/WhalerMike/uiao/blob/main/AGENTS.md) is the maintainer-and-agent entry point.

Happy to refine any of the above based on forum input. The substrate's posture is that the RFC-0026 implementation pattern should converge across agencies; that requires community alignment, not vendor positioning.

---

## What this draft is NOT

- Not a vendor pitch. UIAO is open-source; the substrate-is-OSS framing is the authentic posture and the only one that survives federal-forum scrutiny.
- Not a final commitment on any open question. The four open questions above are the substrate's current best read; community input may shift any of them.
- Not a marketing artifact. Phrases like "next-generation," "industry-leading," "the only," and similar promotional language are deliberately absent.
- Not a substitute for actually engaging the forum. This is a draft to be edited by the maintainer before posting, and the engagement is a multi-comment conversation, not a single post.

## Suggested forum-engagement follow-through

After the initial post:

1. **Watch the thread for 7 days** for responses to the four open questions
2. **Respond to each substantive reply** with substrate-canon references when applicable, or "we'll incorporate that feedback into UIAO_132 v0.3" when the feedback warrants a canon change
3. **Open a UIAO_132 v0.3 PR** if community input materially shifts any of the four open questions; cite the forum discussion in the PR description for provenance
4. **Cross-link** the resulting canon change back to the original forum comment so the substrate's evolution is publicly traceable

## Provenance

This draft references:

- `src/uiao/canon/adr/adr-043-fedramp-rfc-0026-ca7-integration.md`
- `src/uiao/canon/specs/fedramp-rfc-0026-ca7-integration.md` (UIAO_132)
- `src/uiao/canon/compliance/reference/fedramp-rfc-0026/README.md`
- `docs/docs/uiao-rfc-0026-roadmap.qmd`
- `docs/docs/uiao-rfc-0026-e1-connect-gov-design.qmd`
- `docs/docs/uiao-rfc-0026-e5-multi-agency-design.qmd`
- `docs/customer-documents/whitepapers/federal-ssot-alignment.qmd`
- `docs/customer-documents/compliance/boundary-authorization/B1-1-gcc-moderate-three-way-conflict.qmd`

All references are verified to exist on `main` as of 2026-05-11.
