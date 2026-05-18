param(
    [string]$OutputRoot = "C:\Users\whale\git\uiao\phase2\diagrams\domains"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Generates the per-domain PUML diagram pack for the UIAO Phase 2 substrate.
# Each diagram maps 1:1 to a Phase 2 domain spec (UIAO_P2_201..207) under
# phase2/domains/. See phase2/UIAO_Phase2_Index.md for the canonical IDs.

function Write-UIAOIdentityDiagram {
    param([string]$Root)
    $path = Join-Path $Root 'identity\ID-201-A01.puml'
    $puml = @'
@startuml
title ID-201-A01 - Identity Source-of-Truth

rectangle "HR System\n(Authoritative Person Data)" as HR
rectangle "Identity Platform\n(Authoritative Identity)" as IDP
rectangle "Attribute Governance Engine" as ATTR
rectangle "Lifecycle Orchestrator" as LCO
rectangle "Identity Sync Fabric" as SYNC
rectangle "Access Platform" as ACCESS
rectangle "App Integration\n(SSO / SCIM)" as APPS
rectangle "Governance OS" as GOV

HR --> IDP : Authoritative attributes\n(HR -> Identity)
IDP --> ATTR : Attribute evaluation\n& normalization
IDP --> LCO : Lifecycle events\n(joiner/mover/leaver)
IDP --> SYNC : Downstream identity\nprojection

SYNC --> ACCESS : Identity -> Roles/Groups
SYNC --> APPS : Identity -> App identities\n(SCIM / SSO)
IDP --> GOV : Identity state & risk\nfor policy evaluation

cloud "Drift Detection Engine" as DRIFT
DRIFT .. HR : Attribute mismatch
DRIFT .. IDP : Lifecycle mismatch
DRIFT .. SYNC : Projection failures
DRIFT .. GOV : Governance escalation

@enduml
'@
    $puml | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

function Write-UIAODeviceDiagram {
    param([string]$Root)
    $path = Join-Path $Root 'device\DV-202-A01.puml'
    $puml = @'
@startuml
title DV-202-A01 - Device Compliance Flow

actor "User" as USER
rectangle "Device" as DEV
rectangle "Enrollment Service" as ENR
rectangle "Compliance Engine" as COMP
rectangle "Device Posture Evaluator" as POST
rectangle "Access Platform" as ACCESS
rectangle "Governance OS" as GOV

USER --> DEV : Sign-in / Use device
DEV --> ENR : Enrollment request
ENR --> COMP : Register device\n& baseline policies
COMP --> POST : Evaluate posture\n(OS, patch, config)

POST --> COMP : Compliance result\n(Compliant / Non-compliant)
COMP --> ACCESS : Device posture claim\nfor Conditional Access
ACCESS --> GOV : Policy decision\n(Allow / Block / Require MFA)

cloud "Device Drift Detection" as DDRIFT
DDRIFT .. DEV : Config drift
DDRIFT .. COMP : Policy drift
DDRIFT .. GOV : Escalation & remediation

@enduml
'@
    $puml | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

function Write-UIAOAccessDiagram {
    param([string]$Root)
    $path = Join-Path $Root 'access\AC-203-A01.puml'
    $puml = @'
@startuml
title AC-203-A01 - Access Control Plane

rectangle "Identity Platform" as IDP
rectangle "Device Compliance\n& Posture" as DEV
rectangle "Access Platform" as ACCESS
rectangle "Role Model" as ROLES
rectangle "Permission Model" as PERM
rectangle "Conditional Access Engine" as CA
rectangle "Governance OS" as GOV
rectangle "Apps" as APPS

IDP --> ACCESS : Identity claims\n(user, groups, attributes)
DEV --> ACCESS : Device posture\n(compliant / non-compliant)

ACCESS --> ROLES : Resolve roles
ROLES --> PERM : Resolve permissions
ACCESS --> CA : Evaluate Conditional Access
CA --> GOV : Policy evaluation\n& enforcement

ACCESS --> APPS : Tokens / Assertions\n(SSO / API access)

cloud "Access Drift Engine" as ADRIFT
ADRIFT .. ROLES : Role drift
ADRIFT .. PERM : Permission drift
ADRIFT .. GOV : Escalation & remediation

@enduml
'@
    $puml | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

function Write-UIAOGovernanceDiagram {
    param([string]$Root)
    $path = Join-Path $Root 'governance\GV-204-A01.puml'
    $puml = @'
@startuml
title GV-204-A01 - Governance Enforcement Map

rectangle "Governance OS" as GOV {
  rectangle "Policy Engine" as POL
  rectangle "Drift Engine" as DRIFT
  rectangle "Impact Engine" as IMP
  rectangle "Exception Engine" as EXC
}

rectangle "Identity Domain" as ID
rectangle "Device Domain" as DEV
rectangle "Access Domain" as ACC
rectangle "HR Domain" as HR
rectangle "App Integration Domain" as APP
rectangle "Network Domain" as NET

HR --> ID : HR -> Identity rules
ID --> ACC : Identity -> Access rules
DEV --> ACC : Device -> Access rules
ACC --> APP : Access -> App rules

POL --> ID
POL --> DEV
POL --> ACC
POL --> HR
POL --> APP
POL --> NET

DRIFT --> IMP : Drift -> Impact classification
IMP --> POL : Policy updates / enforcement
EXC --> POL : Approved exceptions\n(scoped, time-bound)

cloud "Audit & Logging" as AUD
GOV --> AUD : Decisions, drift, impact,\nexceptions, enforcement

@enduml
'@
    $puml | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

function Write-UIAOHRDiagram {
    param([string]$Root)
    $path = Join-Path $Root 'hr\HR-205-A02.puml'
    $puml = @'
@startuml
title HR-205-A02 - HR -> Identity Flow

rectangle "HR System" as HR
rectangle "HR Trigger Engine" as HRT
rectangle "HR Attribute Governance" as HRA
rectangle "Identity Platform" as IDP
rectangle "Lifecycle Orchestrator" as LCO
rectangle "Access Platform" as ACCESS
rectangle "Governance OS" as GOV

HR --> HRT : Events\n(Hire, Move, Terminate)
HRT --> HRA : Validate attributes\n& apply HR rules
HRA --> IDP : Create / Update identity
IDP --> LCO : Lifecycle state change

LCO --> ACCESS : Update roles / groups
IDP --> GOV : Identity state & HR context\nfor policy evaluation

cloud "HR Drift Detection" as HDRIFT
HDRIFT .. HR : Attribute drift
HDRIFT .. HRA : Rule drift
HDRIFT .. GOV : Escalation

@enduml
'@
    $puml | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

function Write-UIAOAppIntDiagram {
    param([string]$Root)
    $path = Join-Path $Root 'appint\AP-206-A01.puml'
    $puml = @'
@startuml
title AP-206-A01 - App Integration Architecture

rectangle "Identity Platform" as IDP
rectangle "Access Platform" as ACCESS
rectangle "App Integration Service" as AIS
rectangle "SCIM Provisioning" as SCIM
rectangle "SSO / Federation" as SSO
rectangle "Applications" as APPS
rectangle "Governance OS" as GOV

IDP --> AIS : Identity & attributes
ACCESS --> AIS : Roles & permissions

AIS --> SCIM : Provision / deprovision\napp identities
AIS --> SSO : Configure SSO\n(SAML / OIDC)

SCIM --> APPS : Create / update / delete\napp accounts
SSO --> APPS : Tokens / assertions\nfor sign-in

GOV --> AIS : App policies\n(onboarding, data, risk)
AIS --> GOV : App inventory, drift,\npolicy compliance

cloud "App Drift Engine" as ADRIFT
ADRIFT .. SCIM : Provisioning drift
ADRIFT .. SSO : SSO config drift
ADRIFT .. GOV : Escalation & remediation

@enduml
'@
    $puml | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

function Write-UIAONetworkDiagram {
    param([string]$Root)
    $path = Join-Path $Root 'network\NW-207-A01.puml'
    $puml = @'
@startuml
title NW-207-A01 - Zero Trust Network

rectangle "User" as USER
rectangle "Device" as DEV
rectangle "Network Edge" as EDGE
rectangle "Zero Trust Gateway" as ZTG
rectangle "Network Segmentation\n& Policy Engine" as SEG
rectangle "Access Platform" as ACCESS
rectangle "Apps / Services" as APPS
rectangle "Governance OS" as GOV

USER --> DEV
DEV --> EDGE : Connect
EDGE --> ZTG : Enforce TLS / inspection
ZTG --> SEG : Evaluate network policy\n(segment, zone, sensitivity)

SEG --> ACCESS : Network posture claim\n(location, segment, risk)
ACCESS --> APPS : Access decision\n(allow / deny / step-up)

GOV --> SEG : Network policies\n(segments, zones, rules)
SEG --> GOV : Policy compliance,\nviolations, drift

cloud "Network Drift Engine" as NDRIFT
NDRIFT .. SEG : Segmentation drift
NDRIFT .. EDGE : Edge config drift
NDRIFT .. GOV : Escalation

@enduml
'@
    $puml | Set-Content -LiteralPath $path -Encoding ASCII -Force
}

function Invoke-UIAOPhase2Diagrams {
    param([string]$Root)

    $paths = @(
        "$Root\identity",
        "$Root\device",
        "$Root\access",
        "$Root\governance",
        "$Root\hr",
        "$Root\appint",
        "$Root\network"
    )

    foreach ($p in $paths) {
        if (-not (Test-Path -LiteralPath $p)) {
            New-Item -ItemType Directory -Path $p -Force | Out-Null
        }
    }

    Write-Host "Generating Phase 2 domain diagrams..." -ForegroundColor Cyan

    Write-UIAOIdentityDiagram   -Root $Root
    Write-UIAODeviceDiagram     -Root $Root
    Write-UIAOAccessDiagram     -Root $Root
    Write-UIAOGovernanceDiagram -Root $Root
    Write-UIAOHRDiagram         -Root $Root
    Write-UIAOAppIntDiagram     -Root $Root
    Write-UIAONetworkDiagram    -Root $Root

    Write-Host "Phase 2 domain diagrams written to $Root" -ForegroundColor Green
}

Invoke-UIAOPhase2Diagrams -Root $OutputRoot
