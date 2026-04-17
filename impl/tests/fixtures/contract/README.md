# `impl/tests/fixtures/contract/` — Tier-2 Contract Fixtures

Per [UIAO_131 §3.2](../../../../core/canon/specs/adapter-test-strategy.md),
tier-2 tests are **contract tests against recorded fixtures**. Every
fixture in this tree encodes an expected vendor request/response pair
that the adapter must handle correctly — including the **absence**
of a capability in a particular cloud variant (e.g., the
[FINDING-001 INR unavailability](../../../../docs/findings/fedramp-gcc-moderate-informed-network-routing.md)
in GCC-Moderate).

## Directory layout

One subdirectory per adapter. Adapters match entries in
[`core/canon/modernization-registry.yaml`](../../../../core/canon/modernization-registry.yaml)
and [`core/canon/adapter-registry.yaml`](../../../../core/canon/adapter-registry.yaml).

```
contract/
├── bluecat-address-manager/   # Tier-1 excluded per UIAO_131 §5.1; tier-2 only
├── cyberark/
├── entra-id/
├── infoblox/                  # Tier-1 excluded per UIAO_131 §5.1; tier-2 only
├── m365/
├── palo-alto/
├── scuba/
├── scubagear/
├── service-now/
└── terraform/
```

`mainframe` is omitted — tier-3 reference-deployment only per UIAO_131 §5.1.

## Fixture contract

Every fixture file is YAML and carries these required keys:

```yaml
adapter: "<adapter-name>"               # matches registry id
operation: "<operation-name>"           # e.g., list_users, get_policy
cloud_variant:                          # optional; some fixtures are cloud-specific
  - commercial                          # WW Commercial Microsoft cloud
  - gcc-moderate                        # federal GCC-Moderate
  - gcc-high                            # not in UIAO scope — kept for negative assertions
  - govcloud-east                       # AWS
  - govcloud-west
  - onprem                              # self-hosted appliance

request:
  method: GET | POST | PUT | DELETE | PATCH
  url: "https://<host>/<path>"
  headers: {}                           # redact bearer tokens: "Authorization: Bearer <TOKEN>"
  body: null                            # or string/object

response:
  status: 200                           # or actual status (including 404, 403, etc.)
  headers: {}
  body: null                            # or parsed structure

expected_behavior:                      # what the adapter MUST do on this response
  - "…"

provenance:                             # REQUIRED
  source: "microsoft-learn" | "vendor-docs" | "live-capture" | "agency-sanitized" | "finding-<id>"
  url: "https://…"                      # when source is a public doc
  accessed: "YYYY-MM-DD"
  captured_by: "<human name or adapter-test-run-id>"
  sanitization: "<what was redacted / replaced>"
```

## Source classes (provenance)

1. **`microsoft-learn`** — transcribed from Microsoft Learn. Authoritative
   for Microsoft cloud feature availability. Example: the request/response
   that proves INR is unavailable in GCC-Moderate for FINDING-001.
2. **`vendor-docs`** — transcribed from the vendor's public API docs,
   Swagger / OpenAPI schema, or a published integration guide.
3. **`live-capture`** — captured from a live test run (Tier-1 evidence).
   Sensitive values replaced with placeholders. Must cite the adapter's
   tier-1 target (M365 Developer Program, ServiceNow Dev Instance, etc.).
4. **`agency-sanitized`** — captured during a Tier-3 reference deployment
   at a partner agency's non-production tenant. Agency consent required
   before sanitized version lands here. Never land raw agency data.
5. **`finding-<id>`** — codifies a governance finding (e.g., `finding-001`
   for the FedRAMP-INR constraint). These fixtures prove the adapter
   handles the constraint gracefully.

## Sanitization rules (hard requirements)

Before committing a live-capture or agency-sanitized fixture:

1. **Replace all tenant IDs / org IDs** with `<TENANT_ID>`,
   `<ORG_ID>`, etc.
2. **Replace all user principals / email addresses** with
   `user<N>@example.com`.
3. **Replace all object GUIDs** with `<OBJECT_ID_NN>` referencing a
   local id-table at the top of the file.
4. **Replace all bearer tokens, API keys, client secrets** with
   `<TOKEN>`, `<API_KEY>`, `<SECRET>`.
5. **Strip all IP addresses** from network-layer fixtures unless
   they're documented RFC 5737 / RFC 3849 ranges (`192.0.2.*`,
   `2001:db8::/32`).
6. **Preserve the structure, not the data.** Field names, types,
   counts, and response shape are the signal; specific values are
   noise for contract tests.

A pre-commit hook enforces (1) and (4) mechanically; (2), (3), (5),
(6) require reviewer judgment.

## Running tier-2 tests

From `impl/`:

```bash
pytest tests/contract/ -v                    # all tier-2 contract tests
pytest tests/contract/ -k entra_id           # one adapter
pytest tests/contract/test_<adapter>_contract.py -v
```

Tier-2 runs on every PR via `pytest.yml`. Zero network calls —
deterministic, fast, always runs.

## Relationship to other tiers

| Tier | Source | Fixture home | CI |
|---|---|---|---|
| **1** — Live commercial | Vendor dev program (M365 Dev, ServiceNow Dev, etc.) | `impl/tests/integration/fixtures/tier1/` (not here) | Nightly or manual |
| **2** — Contract | This directory | Here | Every PR |
| **3** — Reference deployment | Agency GCC-M tenant | Evidence bundle in agency's own repo, not committed upstream | Quarterly, per agency |

## Adding a fixture

1. Identify the adapter + operation the fixture tests.
2. Determine the cloud variant(s) the fixture applies to.
3. Choose the provenance source class (above).
4. Capture or transcribe the request/response pair.
5. Sanitize per rules above.
6. Save as `contract/<adapter>/<operation>[-<cloud-variant>].yaml`.
7. Add a matching test case to `impl/tests/contract/test_<adapter>_contract.py`.
8. `pytest tests/contract/ -k <adapter>` — must pass.
9. Commit in a PR touching only the fixture + its test. CI green.

## Empty-adapter convention

When no fixtures exist yet for an adapter, its subdirectory contains
only a `.gitkeep` file so the directory persists in the tree. This
signals "adapter registered, tier-2 fixtures pending" rather than
"no adapter."

## Cross-references

- [UIAO_131 Adapter Test Strategy](../../../../core/canon/specs/adapter-test-strategy.md) — authorizing spec
- [UIAO_121 Adapter Conformance Test Plan — Template](../../../../core/canon/specs/adapter-conformance-test-plan-template.md)
- [UIAO_123 Adapter Integration Test Plan — Canonical Template](../../../../core/canon/specs/adapter-integration-test-plan.md)
- [Academy — Contributor tier-1 setup](../../../../docs/academy/contributor-tier-1-setup.qmd) — where fixtures are captured
- [FINDING-001 — FedRAMP-INR](../../../../docs/findings/fedramp-gcc-moderate-informed-network-routing.md) — first fixture provenance class
