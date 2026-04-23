# E5 Design Memo — Multi-Agency Artifact Distribution Layer

**Roadmap entry:** [`docs/docs/uiao-rfc-0026-roadmap.md`](uiao-rfc-0026-roadmap.md) § E5
**Canon refs:** UIAO_132 §3.2 / §3.3; ADR-043 D3
**Status:** **DRAFT — all six open questions resolved; implementation PR unblocked**
**Date:** 2026-04-23
**Target delivery:** 2026-11-30 (60-day buffer before 2027-01-01 enforcement)

---

## Resolved decisions (from review)

| Question | Decision | Rationale |
|---|---|---|
| **Q2.1** — Field set | **Ship the schema as drafted.** Proposed fields cover the RFC-0026 + UIAO_132 surface; extension fields (e.g. `cmmc-level`, `region`, `ato-expiry-date`) are deferred to focused follow-up PRs as concrete need emerges. | User selected default. Schema's `additionalProperties: false` keeps the registry strict; extending is a one-line PR when warranted. |
| **Q2.2** — Agency ID convention | **Department-abbrev + sub-org kebab-case (e.g. `treasury-ocio`, `dhs-cisa`).** Matches the existing `adapter-registry.yaml` convention for short stable IDs. | User selected default (option a). Concise, stable, matches kebab-case canon pattern. |
| **Q2.3** — KSI subscription model | **Default to all-KSIs but allow per-agency subsetting** via the `ksi-subscription` field. Agencies that omit the field receive the full KSI surface; agencies that declare a subset receive only those. | User selected default (option b). Flexible without forcing per-agency curation on day one. |
| **Q2.4** — `data-classification` differentiation | **Moderate-only profile day one.** `data-classification` field exists in the schema (future-proof hook), but the redaction profile (E7) treats Moderate and High identically until a real High-classification agency onboards and a follow-up ADR amends the profile. | User selected default (option a). Avoids day-one over-engineering; the hook is in the schema so the future split is a focused change. |
| **Q2.5** — Canon placement | **`src/uiao/canon/agency-customer-registry.yaml`** alongside `adapter-registry.yaml`. Agency customers are first-class canon citizens. | User selected default (option a). |
| **Q2.6** — Schema enforcement timing | **Blocking from day one.** Schema validator gates every PR from PR-1 of the registry. Matches every other UIAO registry's enforcement posture. | User selected default (option a). Soft-warning mode would create a window where invalid entries land silently. |

---

## Why this memo exists

RFC-0026 RV5-CA07-CCM obliges a CSP with multiple agency ATOs to demonstrate that ConMon artifacts were *made available* to every agency customer, regardless of whether those agencies actually consume them. The RFC forum thread (FedRAMP community discussion #130) converged on *"facilitate and document"* as the correct framing — the CSP's obligation is to distribute, not to guarantee consumption.

Today UIAO has no mechanism to (a) enumerate who its agency customers are, (b) record that distribution happened, or (c) produce a machine-tractable evidence trail of the distribution events. This memo proposes the registry schema, the distribution receipt format, and the workflow integration points needed to close that gap before the enforcement clock.

Implementation requires your review of this schema because the list of fields per agency is a CSP-specific policy decision, not a FedRAMP-mandated one.

---

## Goal

**Given:** a POA&M + OSCAL drop produced by `conmon-aggregate.yml`.

**Produce:** one signed distribution receipt per registered agency customer, recording that the artifact bundle was made available to that agency via that agency's declared delivery channel.

**Definition of done:**

1. `src/uiao/canon/agency-customer-registry.yaml` exists and passes schema validation in CI
2. `conmon-aggregate.yml` iterates the registry on every run and emits one receipt per agency at `evidence/distribution/<agency-id>/<yyyy-mm>/receipt.json`
3. Every receipt is HMAC-SHA256 signed with the same key chain that signs the underlying evidence pack (so the audit trail is cryptographically linked, not just temporally)
4. Missing distribution for any registered agency opens a `conmon-cure`-labelled issue within 24 hours
5. New agency ATO triggers an onboarding PR against the registry (E6 depends on this shape)

---

## Proposed registry shape

### `src/uiao/canon/agency-customer-registry.yaml` (proposed)

```yaml
# yaml-language-server: $schema=../schemas/agency-customer-registry/agency-customer-registry.schema.json
#
# UIAO Agency Customer Registry
# =============================
# Records the set of federal agency customers with an active UIAO ATO
# and the distribution channel UIAO uses to make monthly ConMon
# artifacts available to each. Feeds `conmon-aggregate.yml` on every
# run; absence from this registry means an agency does NOT receive
# ConMon evidence and is NOT part of the RV5-CA07-CCM surface.
#
# Canon invariants (proposed):
#   * agency-id: NIST SP 800-63A-shaped short code; never renamed once
#     assigned (retire via status=retired + successor)
#   * delivery-channel: one of connect-gov-folder | oscal-feed | sftp-drop |
#     email-notification — determines the receipt format
#   * conmon-agreement-date: YYYY-MM-DD — anchors the "CCM obligation
#     started on date X" question raised by acloudcj in RFC-0026 #130
#   * data-classification: one of moderate | high — pins the evidence
#     redaction profile (couples to E7 once that lands)
#
# Pair document: ADR-043 D3; UIAO_132 §3.2 / §3.3

schema-version: "1.0.0"
updated: "2026-04-23"
registry-class: agency-customer

agencies:

  - id: example-agency-alpha
    name: Example Agency Alpha (SAMPLE ONLY — REPLACE)
    status: active
    ato-date: "2026-01-15"
    conmon-agreement-date: "2026-01-15"
    data-classification: moderate
    delivery-channel: connect-gov-folder
    connect-gov:
      csp-folder: "uiao/shared/alpha/"
      # Shape fully defined once E1 Option confirmed
    contacts:
      primary:
        role: ConMon Lead
        org-reference: "AGENCY-ALPHA-CONMON"  # org identity only — no PII
      escalation:
        role: ISSO
        org-reference: "AGENCY-ALPHA-ISSO"
    ksi-subscription:
      - KSI-AC-02
      - KSI-AC-06
      - KSI-AU-02
      - KSI-AU-06
    notes: >-
      Sample entry. Real agency onboarding PR lands via E6 workflow
      and replaces this stub.
```

### Proposed JSON schema (adapter-registry pattern)

Key schema rules mirror `adapter-registry.schema.json`:

- `agency-id` is `^[a-z][a-z0-9-]*[a-z0-9]$` (kebab-case, stable)
- `status` enum: `active | onboarding | retired`
- `delivery-channel` enum tied to the receipt format (see below)
- `data-classification` enum: `moderate | high`
- `conmon-agreement-date` and `ato-date` are both `format: date`
- `contacts.{primary,escalation}` — **no PII**: `org-reference` is an org-identity code, not a person name. Matches UIAO's `object-identity-only: true` canon invariant
- `additionalProperties: false` at every level

## Distribution receipt format

One receipt per agency per aggregate run, at:

```
evidence/distribution/<agency-id>/<yyyy-mm>/receipt.json
```

### Proposed receipt shape

```json
{
  "receipt_version": "1.0.0",
  "emitted_at": "2027-02-01T09:00:00Z",
  "agency_id": "example-agency-alpha",
  "reporting_month": "2027-01",
  "source_artifacts": {
    "poam_csv_sha256": "…",
    "summary_json_sha256": "…",
    "oscal_ssp_json_sha256": "…",
    "oscal_sar_json_sha256": "…",
    "oscal_poam_json_sha256": "…"
  },
  "delivery": {
    "channel": "connect-gov-folder",
    "destination": "uiao/shared/alpha/2027-01/",
    "confirmation": {
      "mode": "server-response | synthesized | operator-attest",
      "server_response_ref": "connect-gov-receipt-…",
      "confirmed_at": "2027-02-01T09:00:00Z"
    }
  },
  "signature": {
    "alg": "HMAC-SHA256",
    "key_id": "uiao-evidence-v1",
    "value": "…"
  },
  "chain_parent_sha256": "…"
}
```

`chain_parent_sha256` links each receipt to the aggregate-run evidence pack, so an auditor can walk from any agency receipt back to the single source-of-truth month's evidence bundle.

## Workflow integration (conmon-aggregate.yml)

One new step after the existing aggregate run:

```yaml
      - name: Distribute to agency customers (RFC-0026 E5)
        id: distribute
        run: |
          python scripts/conmon/distribute.py \
            --aggregate-dir exports/conmon \
            --registry src/uiao/canon/agency-customer-registry.yaml \
            --evidence-root evidence/distribution \
            --hmac-key-id ${{ secrets.UIAO_EVIDENCE_HMAC_KEY_ID }}
```

The script:
- Reads each `active`-status agency
- For each, renders the delivery-channel-specific action (Connect.gov folder copy, OSCAL feed update, SFTP put, etc.)
- Writes the signed receipt
- On any per-agency failure, emits a payload to `exports/conmon/conmon-distribution-issues.json` for a subsequent `actions/github-script@v7` step to file as a `conmon-cure` issue (matching the existing SLA-breach pattern)

Delivery-channel coupling: `connect-gov-folder` reuses whatever E1 ships; `oscal-feed`/`sftp-drop`/`email-notification` are separate transport implementations. No transport work is blocked on E5 itself — the registry + receipt format are transport-agnostic.

---

## Open questions for the user

1. ~~**Field set.**~~ **RESOLVED — ship as drafted.** See "Resolved decisions" at the top.
2. ~~**Agency IDs.**~~ **RESOLVED — department-abbrev + sub-org kebab-case.**
3. ~~**KSI subscription model.**~~ **RESOLVED — default to all-KSIs; per-agency subsetting allowed via the field.**
4. ~~**`data-classification`.**~~ **RESOLVED — Moderate-only profile day one; field present as future-proof hook.**
5. ~~**Canon placement.**~~ **RESOLVED — `src/uiao/canon/agency-customer-registry.yaml`.**
6. ~~**Schema enforcement timing.**~~ **RESOLVED — blocking from day one.**

**All six E5 open questions are resolved.** The implementation PR is unblocked and can start once you merge this design-draft PR.

---

## What this memo does *not* propose

- **Not promoting canon.** The registry file shown above is illustrative. It's *not* committed in this PR.
- **Not implementing delivery transports.** Each `delivery-channel` needs its own transport adapter, which lives in follow-up PRs after E1 lands.
- **Not filling in a real agency list.** That's your call — I can't enumerate your customers.
- **Not touching UIAO_132.** The canon doc will be updated once the registry shape is approved.

---

## Task breakdown (maps to roadmap)

| Roadmap task | This memo resolves | Implementation PR follows |
|---|---|---|
| T5.1 Create `agency-customer-registry.yaml` | Proposed schema | Actual file + schema JSON |
| T5.2 Fields (agency-id, contact, channel, dates) | Proposed | Commit after review |
| T5.3 `conmon-aggregate.yml` iteration + HMAC receipts | Designed integration point | Script + workflow step |
| T5.4 Receipts under `evidence/distribution/<agency-id>/<yyyy-mm>/` | Receipt format proposed | Writer lives in `scripts/conmon/distribute.py` |
| T5.5 CI schema validation | Schema pattern matches adapter-registry | Schema file + `schema-validation` workflow path update |
| T5.6 Cross-reference to UIAO_132 §3.2 / §3.3 | Noted; deferred to canon PR | Paired canon edit |
