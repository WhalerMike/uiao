<!-- authorities:book-evidence-fabric — generated from aan-compliance-spine.yml; do not hand-edit -->
| Control | Title | Closing mechanism (function, not product) | Accreditation gate | Authority drivers | Evidence slot | FedRAMP 20x KSI | Tool-attestable? |
|---|---|---|---|---|---|---|---|
| AU-12 | Audit Record Generation | Enterprise-wide audit generation spanning every CSP, NEM appliance, and OS agent | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-21-31 | Telemetry | KSI-MLA | No |
| AU-12(1) † | System-Wide / Time-Correlated Audit Trail | Cross-surface correlation keyed to authoritative asset identity (IPAM/DDI) + time — the join that makes one compliance picture | FedRAMP Moderate | NIST SP 800-53 Rev 5; CISA BOD 23-01 | Telemetry | KSI-MLA | No |
| AU-3 † | Content of Audit Records | Unified machine-readable evidence-record contract every native stack emits (the coordination mechanism) | FedRAMP Moderate | NIST SP 800-53 Rev 5; OMB M-21-31 | Telemetry | KSI-MLA | No |
| AU-6(1) | Automated Process Integration | Automated aggregation + analysis across CSP/NEM/OS sources into one lake (Sentinel default; Splunk alternative) | FedRAMP Moderate | NIST SP 800-53 Rev 5; NIST SP 800-137 | Telemetry | KSI-MLA | No |
| CA-7 | Continuous Monitoring | The telemetry→evidence→CDM→KSI pipeline; ServiceNow coordinates workflow, CMDB reconciled to IPAM/DDI | FedRAMP Moderate | NIST SP 800-53 Rev 5; NIST SP 800-137; CISA CDM; FedRAMP 20x KSIs | Telemetry | KSI-MLA | No |
| SI-4(16) | Correlate Monitoring Information | Correlation of monitoring data across vendor/surface boundaries in the unified fabric | FedRAMP Moderate | NIST SP 800-53 Rev 5 | Telemetry | KSI-MLA | No |

: Authorities Closed Here — Multi-Cloud Evidence Fabric (telemetry → CDM → KSI) († = Closure-Necessity anchor: no alternate closure path) {.striped .hover}

