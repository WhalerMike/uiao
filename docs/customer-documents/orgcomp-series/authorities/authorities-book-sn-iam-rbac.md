<!-- authorities:book-sn-iam-rbac — generated from orgcomp-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| AC-2 | Account Management | SailPoint ISC Governance (CIEM) findings on Azure RBAC and AWS IAM — over-privileged and idle entitlements — raised as ServiceNow remediation tasks; native IAM console actuates the revocation/rescoping, ServiceNow tracks to closure | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-22-09 | Identity | KSI-IAM | No |
| AC-3 | Access Enforcement | Over-broad Azure RBAC/AWS IAM policy bindings surfaced by SailPoint ISC Governance become ServiceNow Change tasks with owner and approval before rescoping; the native role/policy binding remains the enforcement point the agency controls | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Identity | KSI-IAM | No |
| AC-6 | Least Privilege | SailPoint CIEM identifies entitlements idle 90+ days on Azure RBAC and AWS IAM; ServiceNow raises a scoped-SLA remediation task tracked to closure with re-test evidence | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-22-09 | Identity | KSI-IAM | No |

: Authorities Closed Here — Native Cloud IAM/RBAC Access-Governance Automation († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}
