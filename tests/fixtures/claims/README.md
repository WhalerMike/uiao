# `tests/fixtures/claims/` — Externally-sourced claims the corpus must agree with

A **claim record** pins one factual statement about a vendor product or a
federal framework that published documents in this repository rely on, together
with the citation it was read from. A matching test under `tests/` asserts that
every document stating the claim states it the same way.

This tree exists for a failure mode the other gates do not catch. Tier-2
contract fixtures (`../contract/`) pin how an *adapter* must behave against a
recorded vendor response, and `tests/contract/test_fixture_schema.py` validates
their shape. Neither notices when a *prose* claim in a whitepaper drifts from
the source it was read from, or when a correction lands in one document and not
the four others repeating it.

## When a claim belongs here

All three must hold:

1. **It came from outside the repository** — a vendor doc, a federal catalog —
   so it can change without any commit touching this repo.
2. **More than one published document states it**, which is what makes silent
   divergence possible.
3. **Getting it wrong changes a conclusion**, not just a sentence.

A claim asserted in exactly one document does not need a record: the document
is its own single source of truth. Add the record when the second document
repeats it.

## Record contract

```yaml
claim_id: <kebab-case>
subject: "<one line: what this claim is about>"
<claim body>                 # shape is per-claim; the test that reads it defines it
provenance:
  primary:
    url: "https://…"
    accessed: "YYYY-MM-DD"
    read: firsthand | secondary
    captured_by: "<who or which PR read it>"
asserted_against:            # the documents the test checks
  …
```

`read: secondary` is permitted and is a standing invitation to upgrade it —
three errors in this corpus trace to claims assembled from search summaries
rather than read from source. Record what is true, then improve it.

## Adding one

1. Write the record here, citing the source you actually read.
2. Write `tests/test_<claim>.py` asserting the documents against it.
3. Make the test fail first — flip a value in the record and confirm CI would
   have caught the drift. A pinning test that has never failed is not pinning
   anything.
4. `pytest tests/test_<claim>.py -v`, then commit record and test together.

## Current records

| Record | Claim | Source read |
|---|---|---|
| `entra-tenant-restrictions-v2-enforcement-paths.yaml` | The three enforcement paths for a cross-tenant access policy, and what each covers | Microsoft Learn, firsthand |
