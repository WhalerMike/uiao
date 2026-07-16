<!-- authorities:book-01 — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| SC-20 † | Secure Name/Address Resolution Service (Authoritative Source) | Authoritative DNSSEC-signing resolver (naming plane) | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Network | KSI-CNA | No |
| SC-21 † | Secure Name/Address Resolution Service (Recursive or Caching Resolver) | Recursive DNSSEC validation + protective-DNS RPZ | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA TIC 3.0 | Network | KSI-CNA | No |

: Authorities Closed Here — Cloud Landing Zone, IPAM/DDI, FedRAMP († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

**Closure-Necessity — alternate-path rebuttals (†).** For each necessity anchor, the strongest alternative a reviewer might propose and the specific reason it fails to close the control:

- **SC-20** — Strongest alternative: "Managed cloud DNS with DNSSEC toggled on." Fails SC-20 unless that service is the authoritative signing resolver for your zone — SC-20 requires originating authoritative data-origin authentication for names you are authoritative for; a forwarding or non-authoritative resolver cannot sign responses for your namespace.
- **SC-21** — Strongest alternative: "Endpoint DNS-over-HTTPS or a firewall URL filter." Fails SC-21 because it operates above resolution and does not validate DNSSEC signatures; a forged response to a non-validating recursive resolver still succeeds. Only a validating recursive resolver, plus protective-DNS RPZ policy, closes SC-21.
