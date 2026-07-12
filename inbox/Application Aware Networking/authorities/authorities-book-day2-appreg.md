<!-- authorities:book-day2-appreg — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| AC-6 | Least Privilege | Scoped admin consent; over-broad/privileged scopes gated by a security approver; orphaned/expired app registrations flagged for attestation | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Identity | KSI-IAM | No |
| IA-5(2) | Public Key-Based Authentication | App-registration credentials issued as short-lived certs (ACME) with mandatory expiry and automated rotation — no long-lived secrets in config | FedRAMP Moderate | NIST SP 800-53 Rev 5; EO 14028 | Identity | KSI-IAM | No |
| SC-17 | Public Key Infrastructure Certificates | Certificate issuance and rotation for service principals via the governed catalog | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Identity | KSI-IAM | No |

: Authorities Closed Here — App Registration Governance (request · consent · secret/cert lifecycle) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

