<!-- authorities:book-day2-helpdesk — generated from orgcomp-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| AC-2 | Account Management | Joiner/mover/leaver, guest invite, and license/group requests as governed ServiceNow catalog items over Entra (Graph via in-boundary MID); leaver de-provisioning evidenced | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-22-09 | Identity | KSI-IAM | No |
| AC-3 | Access Enforcement | Conditional Access exceptions issued only as governed catalog items with a mandatory expiry and a scheduled access review — an exception weakens a blocking enforcement control and is treated as such, never granted standing | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-22-09 | Identity | KSI-IAM | No |
| AC-6 | Least Privilege | Group and privileged-access requests time-bound and access-reviewed; no standing elevation granted by a helpdesk click | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-22-09 | Identity | KSI-IAM | No |
| IA-5 | Authenticator Management | Password reset, MFA-method reset, and account unlock as identity-verified catalog items (self-service via SSPR where policy allows; else approver-gated) | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Identity | KSI-IAM | No |

: Authorities Closed Here — Helpdesk & ITSM Catalog (Entra · M365 · Azure) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}
