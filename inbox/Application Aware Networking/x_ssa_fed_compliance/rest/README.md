# Outbound REST messages — `x_ssa_fed_compliance`

Two `sys_rest_message` records, exported per tenant into the update set (the
XML is environment-specific — endpoint host, credential alias, MID sysid):

| Record | Endpoint | Auth | Used by |
|---|---|---|---|
| `x_ssa_fed_compliance.graph` | `https://graph.microsoft.com${path}` | OAuth 2.0 credential alias → app registration (READ-only scopes) | `ComplianceIngest.ingestM365` |
| `x_ssa_fed_compliance.arm` | `https://management.azure.com${path}` | OAuth 2.0 credential alias → scoped service principal / MI | `ComplianceIngest.ingestAzure` |

Both: `use_mid_server = <in-boundary MID>`, GET method named `get` with a
`${path}` string parameter. GCC Moderate rides the commercial endpoints —
graph.microsoft.com / management.azure.com serve that boundary; GCC High and
DoD are not in scope for this series.

Least privilege is structural, not aspirational: the Graph app registration
holds Policy.Read.All, Directory.Read.All, SecurityEvents.Read.All (and the
narrow task-creation scope) — `ComplianceGate` refuses to run if it detects a
`*.ReadWrite.*` grant over the governed surfaces.
