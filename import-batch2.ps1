# import-batch2.ps1
# Target: Re-introduce deleted controls and add AC anchors at Gold Standard.

$controlsDir = "data/control-library"
if (!(Test-Path $controlsDir)) { New-Item -ItemType Directory -Path $controlsDir }

$batch2 = @(
    @{
        id = "AC-1"
        title = "Access Control Policy and Procedures"
        content = @"
control-id: AC-1
title: Access Control Policy and Procedures
status: implemented
implemented-by:
  - azure-entra-id
  - sharepoint-online
narrative: |
  **Policy Establishment and Governance**
  The organization maintains a formal Access Control Policy that defines the purpose, scope, roles, and responsibilities for account management and access enforcement. This policy is reviewed annually and updated to reflect changes in federal mandates or organizational posture.

  **Procedural Implementation**
  Access control procedures are operationalized via Azure Entra ID and documented in the SharePoint Intranet. These procedures provide step-by-step guidance for provisioning, deprovisioning, and auditing access across the cloud environment.
parameters:
  policy-review-frequency: "365 days"
  procedures-location: "SharePoint Security Portal"
evidence:
  - type: document
    ref: access-control-policy-v1.pdf
related_controls:
  - PL-2
  - PM-1
"@
    },
    @{
        id = "AC-4"
        title = "Information Flow Enforcement"
        content = @"
control-id: AC-4
title: Information Flow Enforcement
status: implemented
implemented-by:
  - azure-firewall
  - azure-nsg
narrative: |
  **Traffic Inspection and Flow Control**
  The system enforces information flow control via Azure Firewall and Network Security Groups (NSGs). All traffic crossing system boundaries is inspected for compliance with approved protocols and port requirements.

  **Logical Segmentation**
  Data flow between web, application, and database tiers is restricted via micro-segmentation. "Deny-all" is the default posture, ensuring only explicitly permitted traffic traverses the internal network boundaries.
parameters:
  inspection-type: "Stateful Packet Inspection"
  default-posture: "Deny-by-Default"
evidence:
  - type: configuration
    ref: firewall-rule-set-export
related_controls:
  - SC-7
  - AC-17
"@
    },
    @{
        id = "AC-17"
        title = "Remote Access"
        content = @"
control-id: AC-17
title: Remote Access
status: implemented
implemented-by:
  - azure-vpn-gateway
  - azure-conditional-access
narrative: |
  **Authorized Remote Access Entry Points**
  All remote access is routed through the Azure VPN Gateway or ZTNA endpoints. Connections require phishing-resistant MFA and are restricted to managed, compliant devices.

  **Session Monitoring**
  Remote sessions are monitored in real-time by Microsoft Sentinel. Unauthorized or anomalous connection attempts trigger automated alerts and session termination.
parameters:
  vpn-encryption: "AES-256 / TLS 1.2+"
  mfa-requirement: "FIDO2 / WHfB"
evidence:
  - type: logs
    ref: vpn-connection-audit-logs
related_controls:
  - IA-2
  - AC-3
"@
    },
    @{
        id = "IA-8"
        title = "Identification and Authentication (Non-Organizational Users)"
        content = @"
control-id: IA-8
title: Identification and Authentication (Non-Organizational Users)
status: implemented
implemented-by:
  - azure-ad-b2b
  - entra-id-governance
narrative: |
  **External Identity Federation**
  Access for non-organizational users (guests/partners) is managed via Entra ID B2B. External users must authenticate via their home identity provider or a one-time passcode, subject to MFA.

  **Access Reviews**
  External guest access is reviewed monthly. Accounts that have not been active for the defined duration are automatically disabled to prevent persistent external footprint.
parameters:
  guest-inactivity-limit: "30 days"
  review-frequency: "Monthly"
evidence:
  - type: report
    ref: guest-access-review-logs
related_controls:
  - AC-2
  - IA-2
"@
    },
    @{
        id = "SC-8"
        title = "Transmission Confidentiality and Integrity"
        content = @"
control-id: SC-8
title: Transmission Confidentiality and Integrity
status: implemented
implemented-by:
  - azure-front-door
  - azure-application-gateway
narrative: |
  **Encryption in Transit**
  The system protects the confidentiality and integrity of information in transit using TLS 1.2 or higher. Certificates are managed via Azure Key Vault to ensure cryptographic standards are maintained.

  **FIPS 140-2 Validation**
  All cryptographic modules used for data transmission are FIPS 140-2 validated, ensuring compliance with federal security requirements for protecting sensitive information across public and private networks.
parameters:
  min-tls-version: "TLS 1.2"
  cipher-suite: "ECDHE-ECDSA-AES256-GCM-SHA384"
evidence:
  - type: configuration
    ref: ssl-policy-export
related_controls:
  - SC-7
  - SC-13
"@
    }
)

Write-Host "Re-introducing 5 Gold Standard controls for Batch 2..." -ForegroundColor Cyan
foreach ($c in $batch2) {
    $path = Join-Path $controlsDir "$($c.id).yml"
    $c.content | Out-File -FilePath $path -Encoding utf8
    Write-Host "Created: $($c.id).yml" -ForegroundColor Green
}

Write-Host "`nBatch 2 complete. Ready for git commit." -ForegroundColor Yellow