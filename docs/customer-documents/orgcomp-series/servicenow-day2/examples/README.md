# Examples — Day-2 Operations app

Concrete, runnable examples that sit alongside the source. Today this holds the
SAM (SailPoint IGA) inbound-push contract; add sibling files here as other
surfaces (Graph, ARM, telephony) grow example fixtures worth shipping.

| File | What it shows |
|---|---|
| `sam-push-payloads.md` | The IIQ SDIM push contract explained field by field, the IIQ-attribute -> ServiceNow-field map, and a walkthrough of each sample payload below. |
| `payloads/sam-push-success-tier2.json` | A well-formed Tier-2 push (App Owner approval) — the happy path. |
| `payloads/sam-push-success-tier1.json` | A well-formed Tier-1 push (IGO final approval) — the highest approval chain. |
| `payloads/sam-push-success-tier3.json` | A well-formed Tier-3 push (Dept Owner only) — the lightest approval chain. |
| `payloads/sam-push-missing-fields.json` | Missing required fields — the endpoint refuses with 400 and names every missing field. |
| `payloads/sam-push-unresolvable-subject.json` | Well-formed but `requested_for` does not correlate to a reconciled identity — 422. |
| `payloads/sam-push-signed-jws.json` | The optional signed-push (JWS) mode shape, for a tenant that configures `x_fed_day2_ops.sam_jws_public_key`. |

These are documentation fixtures, not a client library — copy the JSON shape
into your IIQ SDIM field map or a REST client of your choice. The `_comment`
keys in the negative/optional examples are for this doc only; strip them
before sending a real push (the endpoint ignores unknown fields, so leaving
one in would not break anything, but it is not part of the contract).

See `../atf/atf-sam-*.xml` for the ATF suite these payloads back, and
`../KIT-USAGE-SAM-INTEGRATION.md` for the operational guide.
