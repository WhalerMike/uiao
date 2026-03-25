# import-batch2-grok.ps1
# Grok-rewritten Batch 2 – Rich, consistent, templated narratives

$controlsDir = "data\control-library"

$batch2 = @(
    @{
        id = "AC-1"
        title = "Access Control Policy and Procedures"
        narrative = @"
{{ organization.name }} develops, disseminates, and maintains an Access Control Policy and associated procedures.

**Policy Governance**
The policy addresses purpose, scope, roles, responsibilities, and coordination among organizational entities. It is reviewed annually and updated to reflect changes in laws, directives, or system architecture.

**Procedural Implementation**
Procedures are implemented through Azure Entra ID Conditional Access, governance workflows, and documented in a central security portal. They cover the full lifecycle of access rights from provisioning to revocation.
"@
        implemented_by = @("azure-entra-id", "sharepoint-online")
        parameters = @{ "policy-review-frequency" = "365 days"; "procedures-location" = "SharePoint Security Portal" }
    },
    @{
        id = "AC-4"
        title = "Information Flow Enforcement"
        narrative = @"
{{ organization.name }} enforces approved authorizations for controlling the flow of information within the system and between connected systems.

**Enforcement Mechanisms**
Azure Firewall and Network Security Groups perform stateful packet inspection. Micro-segmentation enforces deny-by-default between web, application, and data tiers.

**Authorized Flows Only**
Only explicitly permitted information flows (by protocol, port, source, and destination) are allowed; all others are blocked.
"@
        implemented_by = @("azure-firewall", "azure-nsg")
        parameters = @{ "default-posture" = "Deny-by-Default"; "inspection-type" = "Stateful Packet Inspection" }
    },
    @{
        id = "AC-17"
        title = "Remote Access"
        narrative = @"
{{ organization.name }} establishes usage restrictions, configuration requirements, and monitoring for all remote access to the system.

**Secure Remote Access**
All remote connections route through Azure VPN Gateway or ZTNA endpoints and require phishing-resistant MFA plus device compliance validation via Intune.

**Monitoring and Termination**
Microsoft Sentinel monitors remote sessions in real time. Anomalous behavior triggers automated alerts and immediate session termination.
"@
        implemented_by = @("azure-vpn-gateway", "azure-conditional-access")
        parameters = @{ "mfa-requirement" = "FIDO2 / WHfB"; "vpn-encryption" = "AES-256 / TLS 1.2+" }
    },
    @{
        id = "IA-8"
        title = "Identification and Authentication (Non-Organizational Users)"
        narrative = @"
{{ organization.name }} uniquely identifies and authenticates non-organizational users (or processes acting on their behalf).

**External User Management**
Guest and partner access uses Entra ID B2B. Authentication occurs via the external user's home IdP or one-time passcode, always subject to organizational MFA and Conditional Access policies.

**Access Review**
Guest accounts are automatically reviewed monthly; inactive accounts exceeding the defined threshold are disabled.
"@
        implemented_by = @("azure-ad-b2b", "entra-id-governance")
        parameters = @{ "guest-inactivity-limit" = "30 days"; "review-frequency" = "Monthly" }
    },
    @{
        id = "SC-8"
        title = "Transmission Confidentiality and Integrity"
        narrative = @"
{{ organization.name }} protects the confidentiality and integrity of transmitted information.

**Encryption in Transit**
All data in transit uses TLS 1.2 or higher with approved cipher suites. Certificates are managed and rotated via Azure Key Vault.

**Cryptographic Compliance**
Only FIPS 140-validated modules are used, meeting federal requirements for protecting Controlled Unclassified Information (CUI) and other sensitive data.
"@
        implemented_by = @("azure-front-door", "azure-application-gateway")
        parameters = @{ "min-tls-version" = "TLS 1.2"; "cipher-suite" = "ECDHE-ECDSA-AES256-GCM-SHA384" }
    }
)

Write-Host "--- Grok Batch 2: Access Control Gold Standards ---" -ForegroundColor Cyan

foreach ($c in $batch2) {
    $yaml = "control-id: $($c.id)`n"
    $yaml += "title: $($c.title)`n"
    $yaml += "status: implemented`n"
    $yaml += "implemented-by:`n"
    foreach ($comp in $c.implemented_by) { $yaml += "  - $comp`n" }
    $yaml += "narrative: |`n$($c.narrative)`n"
    $yaml += "parameters:`n"
    foreach ($key in $c.parameters.Keys) {
        $yaml += "  $($key): `"$($c.parameters[$key])`"`n"
    }
    $yaml += "evidence:`n  - type: configuration`n    ref: $($c.id)-evidence`n"
    $yaml += "related_controls:`n  - AC-2`n  - AC-3`n"

    $file = Join-Path $controlsDir "$($c.id).yml"
    Set-Content -Path $file -Value $yaml -Encoding UTF8
    Write-Host "[OK] $($c.id).yml" -ForegroundColor Green
}

git add "$controlsDir/*.yml"
git commit -m "feat(control-library): Grok Batch 2 – Access Control Gold Standard narratives"
git pull --rebase origin main
git push origin main

Write-Host "`nGrok Batch 2 complete and pushed!" -ForegroundColor Green