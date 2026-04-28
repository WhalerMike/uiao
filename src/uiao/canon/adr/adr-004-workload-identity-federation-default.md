---
adr_id: adr-004
title: "Workload Identity Federation as Default for External Integrations"
status: ACCEPTED
decided: 2026-04-28
deciders: Michael Stratton
updated: 2026-04-28
next_review: 2026-11-01
review_trigger: Microsoft Ignite 2026; any Entra ID workload identity announcement
impact: UIAO_IDT_002 Spec 3 (Service Account to Workload Identity Mapping)
supersedes: null
superseded_by: null
classification: Controlled
boundary: GCC-Moderate
---

# ADR-004: Workload Identity Federation as Default for External Integrations

## Status

**ACCEPTED** — April 28, 2026

## Context

AD service accounts used for external platform integrations (CI/CD pipelines, infrastructure-as-code tools, container orchestration, cross-cloud access) typically store long-lived credentials — passwords or client secrets — in the external platform's secret store. These credentials must be rotated, can leak, and represent a persistent attack surface.

UIAO Spec 3 (Service Account to Workload Identity Mapping) must define the canonical target identity type for each class of service account. For external platform integrations, the decision is between:

1. **App Registration + Client Secret** — traditional approach; secret stored in external platform, rotated on schedule
2. **App Registration + Certificate** — improved; certificate-based auth, still requires credential management
3. **Workload Identity Federation (WIF)** — secretless; external platform issues OIDC token, exchanged for Entra ID access token via federated trust

## Decision

**Workload Identity Federation is the default target for all external platform integrations. Service accounts authenticating from platforms that support OIDC token issuance must use WIF. Client secrets are prohibited for new integrations. Certificate-based auth is permitted only when the external platform lacks OIDC issuer capability.**

## Rationale

1. **Zero stored secrets.** WIF uses OIDC token exchange — the external platform issues a short-lived JWT, Entra ID validates it against a configured federated credential, and issues an Azure access token. No secrets, certificates, or credentials are stored anywhere. From Microsoft Learn: federated credentials eliminate the need to manage secrets and certificates entirely.

2. **All major external platforms support OIDC.** GitHub Actions, Terraform Cloud, GitLab CI, Jenkins (with OIDC plugin), Kubernetes (native service account token projection), AWS (via STS), and GCP (via Workload Identity) all support OIDC token issuance. The ecosystem is mature.

3. **Short-lived tokens reduce blast radius.** OIDC tokens and the resulting Azure access tokens are valid for minutes, not months. A compromised CI/CD pipeline yields a token that expires before an attacker can establish persistence.

4. **Subject claim mapping provides granular trust.** WIF federated credentials can restrict trust to specific repositories, branches, environments, and workflow runs. For example: only the `main` branch of `org/infra-deploy` in the `production` environment can authenticate. This is more granular than any secret-based approach.

5. **Eliminates rotation overhead.** Secret rotation for service accounts is operationally expensive and error-prone. With WIF, there is nothing to rotate — the trust relationship is configuration, not a credential.

## Supported Platform Matrix

| External Platform | OIDC Issuer | Subject Claim Example | WIF Supported |
|---|---|---|---|
| GitHub Actions | `https://token.actions.githubusercontent.com` | `repo:org/repo:ref:refs/heads/main` | Yes |
| Terraform Cloud | `https://app.terraform.io` | `organization:org:project:proj:workspace:ws:run_phase:apply` | Yes |
| GitLab CI | `https://gitlab.com` | `project_path:group/project:ref_type:branch:ref:main` | Yes |
| Kubernetes (AKS) | Cluster OIDC issuer URL | `system:serviceaccount:namespace:sa-name` | Yes |
| Kubernetes (non-AKS) | Cluster OIDC issuer URL | `system:serviceaccount:namespace:sa-name` | Yes (requires OIDC discovery endpoint) |
| AWS (cross-cloud) | `https://sts.amazonaws.com` | AWS role ARN | Yes |
| GCP (cross-cloud) | `https://accounts.google.com` | GCP service account email | Yes |
| Jenkins | `https://jenkins.example.com` (with OIDC plugin) | Configurable | Yes (requires OIDC plugin) |
| Azure DevOps | `https://vstoken.dev.azure.com/{tenant}` | Service connection ID | Yes |

## Consequences

### Positive
- Eliminates all stored secrets for external platform integrations
- Removes secret rotation as an operational requirement
- Short-lived tokens (minutes) vs. long-lived secrets (months/years) — dramatically reduced attack surface
- Granular trust scoping via subject claims (repo, branch, environment)
- Auditable — every token exchange is logged in Entra ID sign-in logs
- No credential to leak — even if the external platform is compromised, there is no persistent credential to exfiltrate

### Negative
- **Federated credential configuration required per trust relationship** — each repo/workspace/service account needs a corresponding federated credential in Entra ID (max 20 per app registration as of April 2026)
- **OIDC issuer must be reachable from Entra ID** — Entra ID must be able to fetch the OIDC discovery document from the external platform's issuer URL
- **Not all legacy platforms support OIDC** — older CI/CD systems, custom automation scripts, and legacy batch systems may lack OIDC capability (these use certificate auth per the decision hierarchy)
- **Debugging token exchange failures is harder** — OIDC claim mismatches produce opaque errors; requires understanding of JWT claims and federated credential matching rules
- **20 federated credential limit per app registration** — organizations with many repos/pipelines may need multiple app registrations to stay under the limit

### Decision Hierarchy for External Integrations

```
Does the platform support OIDC token issuance?
├── YES → Workload Identity Federation (MANDATORY)
└── NO
    ├── Can the platform manage X.509 certificates?
    │   ├── YES → App Registration + Certificate Auth (PERMITTED)
    │   └── NO → App Registration + Client Secret (EXCEPTION ONLY — requires ADR amendment with justification)
    └── Is this a temporary/migration scenario?
        └── YES → Client Secret with 90-day expiry + Key Vault rotation (TIME-BOUND EXCEPTION)
```

## Verification Sources

| Source | URL | Last Verified |
|---|---|---|
| Microsoft Learn — Workload identity federation | https://learn.microsoft.com/en-us/entra/workload-id/workload-identity-federation | 2026-04-28 |
| GitHub Docs — Configuring OIDC in Azure | https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-azure | 2026-04-28 |
| Microsoft Learn — GitHub Actions WIF with Terraform | https://learn.microsoft.com/en-us/samples/azure-samples/github-terraform-oidc-ci-cd/github-terraform-oidc-ci-cd/ | 2026-04-28 |

## Review Triggers

This ADR must be re-evaluated when any of the following occur:

- [ ] Microsoft increases the 20 federated credential limit per app registration
- [ ] Microsoft introduces managed identity support for non-Azure external platforms
- [ ] A major platform drops or changes its OIDC issuer implementation
- [ ] Entra ID adds native CI/CD integration that replaces WIF (e.g., GitHub-native Entra connector)
- [ ] Conditional Access for workload identities adds WIF-specific policy controls
- [ ] Microsoft Ignite 2026 (November) — scheduled review
- [ ] Microsoft Build 2027 (May) — scheduled review

## Related Documents

- UIAO_IDT_001 — Identity & Directory Transformation Inventory (Transformation #7: SQL Server Authentication, implied for external auth)
- UIAO_IDT_002 — Spec 3: Service Account to Workload Identity Mapping (D2.4: Workload Identity Federation Pattern)
- ADR-002 — Arc-Enabled Servers (Arc managed identities complement WIF for server-side workloads)
