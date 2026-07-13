<!-- authorities:book-net-enforce — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| SC-8 † | Transmission Confidentiality and Integrity | IPsec/MACsec overlay on customer-premises transport (function: network-layer encryption) | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; EO 14028 | Network | KSI-CNA | No |
| SC-8(1) | Cryptographic Protection | FIPS 140-3 validated cipher suite on the overlay | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5 | Network | KSI-CNA | No |
| AC-19 | Access Control for Mobile Devices | NAC posture gating at the access layer | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; OMB M-22-09 | Endpoint | KSI-IAM | No |
| IA-3 † | Device Identification and Authentication | 802.1X authenticator + NAC at the port (function: device identity at the edge) | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; NIST SP 800-207; CISA ZTMM v2.0 | Network | KSI-IAM | No |
| AC-17 | Remote Access | Vendor ZTNA/remote-access gateway (function: per-session remote access) | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; OMB M-22-09; CISA ZTMM v2.0 | Network | KSI-CNA | No |
| AC-4 | Information Flow Enforcement | Application-aware flow policy at the NGFW/SASE PEP | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; NIST SP 800-207; CISA TIC 3.0 | Network | KSI-CNA | No |
| SC-7 | Boundary Protection | NGFW boundary enforcement at the customer-owned edge (function: distributed policy enforcement point) | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; CISA TIC 3.0; NIST SP 800-207 | Network | KSI-CNA | No |
| SC-7(8) | Route Traffic to Authenticated Proxy Servers | Forced-proxy egress through the SASE/SWG enforcement point | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; CISA TIC 3.0 | Network | KSI-CNA | No |
| SI-4 | System Monitoring | Network detection/telemetry export from the enforcement substrate to the evidence contract | NIAP CC + DISA STIG + FIPS 140-3 + DoDIN APL | NIST SP 800-53 Rev 5; OMB M-21-31 | Telemetry | KSI-MLA | No |

: Authorities Closed Here — Network Enforcement Substrate (Cisco/Palo Alto/Juniper) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

