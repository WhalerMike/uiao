<#
.SYNOPSIS
    UIAO Spec 2 — D1.7: HR Connector Comparison Matrix
.DESCRIPTION
    Generates a structured comparison matrix evaluating three HR-to-Entra ID
    provisioning approaches for federal GCC-Moderate environments:

    1. Workday Inbound Provisioning Connector (Entra ID native)
    2. Oracle HCM Inbound Provisioning Connector (Entra ID native)
    3. API-Driven Inbound Provisioning (HR-agnostic, ADR-003 canonical)

    Evaluation dimensions:
    - Attribute support (OrgPath, worker type, UPN generation)
    - JML lifecycle coverage (Joiner, Mover, Leaver workflows)
    - Provisioning expression support (transformations, functions)
    - GCC-Moderate availability and FedRAMP authorization status
    - Administrative Unit and dynamic group compatibility
    - Hybrid coexistence (AD writeback, Entra Connect interaction)
    - OPM HRIS procurement context (Workday/Accenture vs Oracle/Deloitte
      as finalists — GAO protests from IBM and EconSys, decision expected
      early June 2026)
    - Extensibility and custom attribute mapping
    - Error handling, quarantine, and audit capabilities
    - Cost model (licensing, implementation, ongoing operations)

    Outputs: JSON (full comparison matrix) + CSV (summary) + Markdown report

    Ref: UIAO_136 Spec 2, Phase 1, Deliverable D1.7
         ADR-003 (API-Driven Inbound Provisioning)
         ADR-048 (extensionAttribute1 = OrgPath)
         Feeds: D2.1 (Target State Architecture), D2.2 (Provisioning Runbook)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.EXAMPLE
    .\Spec2-D1.7-New-HRConnectorComparisonMatrix.ps1
    .\Spec2-D1.7-New-HRConnectorComparisonMatrix.ps1 -OutputPath C:\exports
.NOTES
    No AD or Entra ID connectivity required — generates reference matrix
    from canonical UIAO specifications and Microsoft documentation.
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output"
)

$ErrorActionPreference = "Stop"

# ── Output setup ──
if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outPrefix = "UIAO_Spec2_D1.7_HRConnectorComparison_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " UIAO Spec 2 — D1.7: HR Connector Comparison Matrix" -ForegroundColor Cyan
Write-Host " Ref: UIAO_136 / ADR-003 / ADR-048" -ForegroundColor DarkCyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ═══════════════════════════════════════════════════════════════
# SECTION 1: Define Connector Profiles
# ═══════════════════════════════════════════════════════════════

Write-Host "[1/6] Building connector profiles..." -ForegroundColor Yellow

$connectors = @(
    @{
        ConnectorId       = "WORKDAY"
        Name              = "Workday Inbound Provisioning"
        Vendor            = "Microsoft (native Entra ID connector)"
        Type              = "Native SaaS Connector"
        HRSystem          = "Workday HCM"
        GCCModerate       = "Available"
        FedRAMPStatus     = "Workday Government Cloud — FedRAMP Moderate authorized"
        ProvisioningAgent = "Entra Provisioning Agent (on-premises for AD writeback)"
        GraphAPIBased     = $false
        Description       = "Purpose-built connector consuming Workday Web Services (WWS) API. Reads worker data from Workday and provisions/updates/deprovisions users in Entra ID or on-premises AD."
    },
    @{
        ConnectorId       = "ORACLE_HCM"
        Name              = "Oracle HCM Inbound Provisioning"
        Vendor            = "Microsoft (native Entra ID connector)"
        Type              = "Native SaaS Connector"
        HRSystem          = "Oracle Cloud HCM (Fusion)"
        GCCModerate       = "Available"
        FedRAMPStatus     = "Oracle Cloud for Government — FedRAMP Moderate authorized"
        ProvisioningAgent = "Entra Provisioning Agent (on-premises for AD writeback)"
        GraphAPIBased     = $false
        Description       = "Purpose-built connector consuming Oracle HCM REST API (ATOM feeds). Reads worker data from Oracle Cloud HCM and provisions/updates/deprovisions users in Entra ID or on-premises AD."
    },
    @{
        ConnectorId       = "API_DRIVEN"
        Name              = "API-Driven Inbound Provisioning"
        Vendor            = "Microsoft (Entra ID platform capability)"
        Type              = "HR-Agnostic API Endpoint"
        HRSystem          = "Any (HR-agnostic per ADR-003)"
        GCCModerate       = "Available"
        FedRAMPStatus     = "Part of Entra ID — inherits M365 GCC FedRAMP Moderate"
        ProvisioningAgent = "None required — direct Graph API calls"
        GraphAPIBased     = $true
        Description       = "Canonical UIAO approach (ADR-003). Exposes /bulkUpload Graph API endpoint. Any HR system, middleware, or automation can push CSV/SCIM payloads. Decouples identity provisioning from HR vendor selection."
    }
)

Write-Host "  Built $($connectors.Count) connector profiles" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 2: Attribute Support Matrix
# ═══════════════════════════════════════════════════════════════

Write-Host "[2/6] Building attribute support matrix..." -ForegroundColor Yellow

$attributeCategories = @(
    @{
        Category = "Core Identity Attributes"
        Attributes = @(
            @{ Attribute = "userPrincipalName"; Workday = "Expression (Fn)"; OracleHCM = "Expression (Fn)"; APIDriven = "Pre-computed by caller"; Notes = "UPN generation per Spec2-D1.5 rules" },
            @{ Attribute = "mailNickname"; Workday = "Expression (Fn)"; OracleHCM = "Expression (Fn)"; APIDriven = "Pre-computed by caller"; Notes = "Alias for Exchange mailbox" },
            @{ Attribute = "displayName"; Workday = "Direct map + Expression"; OracleHCM = "Direct map + Expression"; APIDriven = "Pre-computed by caller"; Notes = "Last, First or First Last" },
            @{ Attribute = "givenName"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "" },
            @{ Attribute = "surname"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "" },
            @{ Attribute = "employeeId"; Workday = "Direct map (Worker_ID)"; OracleHCM = "Direct map (PersonNumber)"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "Correlation anchor" },
            @{ Attribute = "employeeType"; Workday = "Direct map (Worker_Type)"; OracleHCM = "Direct map (WorkerType)"; APIDriven = "Pre-computed by caller"; Notes = "Maps to D1.6 worker taxonomy" },
            @{ Attribute = "department"; Workday = "Direct map (Organization)"; OracleHCM = "Direct map (DepartmentName)"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "" },
            @{ Attribute = "jobTitle"; Workday = "Direct map (Job_Profile)"; OracleHCM = "Direct map (JobName)"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "" },
            @{ Attribute = "manager"; Workday = "Direct map (Manager ref)"; OracleHCM = "Direct map (ManagerId)"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "Resolved to Entra objectId" },
            @{ Attribute = "companyName"; Workday = "Direct map (Company)"; OracleHCM = "Direct map (LegalEntityName)"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "" }
        )
    },
    @{
        Category = "Location Attributes"
        Attributes = @(
            @{ Attribute = "city"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "" },
            @{ Attribute = "state"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "" },
            @{ Attribute = "country"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "ISO 3166-1 alpha-2" },
            @{ Attribute = "streetAddress"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "" },
            @{ Attribute = "postalCode"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "" },
            @{ Attribute = "officeLocation"; Workday = "Expression"; OracleHCM = "Expression"; APIDriven = "Pre-computed"; Notes = "Physical office/building" },
            @{ Attribute = "usageLocation"; Workday = "Expression (country → ISO)"; OracleHCM = "Expression (country → ISO)"; APIDriven = "Pre-computed"; Notes = "Required for M365 licensing" }
        )
    },
    @{
        Category = "OrgPath Attributes (ADR-048)"
        Attributes = @(
            @{ Attribute = "extensionAttribute1 (OrgPath)"; Workday = "Expression (complex)"; OracleHCM = "Expression (complex)"; APIDriven = "Pre-computed by OrgPath calculator"; Notes = "CORP/REGION/STATE/CITY/DEPT — canonical per ADR-048" },
            @{ Attribute = "extensionAttribute2 (OrgPath Depth)"; Workday = "Expression (Fn)"; OracleHCM = "Expression (Fn)"; APIDriven = "Pre-computed by OrgPath calculator"; Notes = "Numeric depth level for hierarchy queries" },
            @{ Attribute = "extensionAttribute3-5 (Reserved)"; Workday = "Not mapped (reserved)"; OracleHCM = "Not mapped (reserved)"; APIDriven = "Not mapped (reserved)"; Notes = "Reserved per ADR-048" }
        )
    },
    @{
        Category = "Contact Attributes"
        Attributes = @(
            @{ Attribute = "mobilePhone"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "MFA registration" },
            @{ Attribute = "businessPhones"; Workday = "Direct map"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "" },
            @{ Attribute = "otherMails"; Workday = "Direct map (personal email)"; OracleHCM = "Direct map"; APIDriven = "Direct map"; Notes = "SSPR recovery" }
        )
    },
    @{
        Category = "Lifecycle Attributes"
        Attributes = @(
            @{ Attribute = "accountEnabled"; Workday = "Expression (status → bool)"; OracleHCM = "Expression (status → bool)"; APIDriven = "Pre-computed by caller"; Notes = "Active = true, Leave/Term = false" },
            @{ Attribute = "employeeHireDate"; Workday = "Direct map (Hire_Date)"; OracleHCM = "Direct map (StartDate)"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "Pre-hire provisioning trigger" },
            @{ Attribute = "employeeLeaveDateTime"; Workday = "Direct map (Termination_Date)"; OracleHCM = "Direct map (ActualTerminationDate)"; APIDriven = "Direct map (CSV/SCIM)"; Notes = "Leaver workflow trigger" }
        )
    }
)

$totalAttributes = ($attributeCategories | ForEach-Object { $_.Attributes.Count } | Measure-Object -Sum).Sum
Write-Host "  Mapped $totalAttributes attributes across $($attributeCategories.Count) categories" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 3: JML Lifecycle Comparison
# ═══════════════════════════════════════════════════════════════

Write-Host "[3/6] Building JML lifecycle comparison..." -ForegroundColor Yellow

$jmlComparison = @(
    @{
        LifecycleEvent = "Pre-Hire (account creation before start date)"
        Workday        = @{
            Support     = "Native"
            Mechanism   = "Scheduled provisioning based on Hire_Date. Connector polls Workday on schedule. Account created with accountEnabled=false until start date."
            Limitations = "Polling interval (default 40 min) means near-real-time is not possible. Custom provisioning expressions needed for pre-hire logic."
        }
        OracleHCM      = @{
            Support     = "Native"
            Mechanism   = "Scheduled provisioning based on StartDate. Connector polls Oracle HCM ATOM feed. Similar pre-hire workflow."
            Limitations = "Same polling interval constraints. ATOM feed may have propagation delays from Oracle side."
        }
        APIDriven      = @{
            Support     = "Full control"
            Mechanism   = "Caller pushes CSV/SCIM to /bulkUpload when pre-hire conditions are met. Immediate processing — no polling delay."
            Limitations = "Caller must implement pre-hire date logic. More development effort but maximum control."
        }
    },
    @{
        LifecycleEvent = "Joiner (new hire activation on start date)"
        Workday        = @{
            Support     = "Native"
            Mechanism   = "Status change in Workday triggers attribute update. Connector sets accountEnabled=true, assigns attributes."
            Limitations = "Relies on correct Workday status transitions. Custom attribute flows require expression authoring."
        }
        OracleHCM      = @{
            Support     = "Native"
            Mechanism   = "ATOM feed publishes active worker record. Connector sets accountEnabled=true, assigns attributes."
            Limitations = "ATOM feed ordering may cause attribute update delays in high-volume environments."
        }
        APIDriven      = @{
            Support     = "Full control"
            Mechanism   = "Caller sends updated CSV/SCIM with active status. All attributes pre-computed including OrgPath, UPN, worker type."
            Limitations = "Caller must compute all transformations. Schema normalizer layer required (per ADR-003 architecture)."
        }
    },
    @{
        LifecycleEvent = "Mover (department/location/role change)"
        Workday        = @{
            Support     = "Native"
            Mechanism   = "Worker attribute changes detected on next poll cycle. Changed attributes flow through provisioning expressions."
            Limitations = "OrgPath recalculation requires complex provisioning expression. Manager chain changes may lag."
        }
        OracleHCM      = @{
            Support     = "Native"
            Mechanism   = "ATOM feed publishes updated worker data. Changed attributes flow through provisioning expressions."
            Limitations = "Same OrgPath expression complexity. Transfer between legal entities may require manual intervention."
        }
        APIDriven      = @{
            Support     = "Full control"
            Mechanism   = "Caller pushes updated attributes with recalculated OrgPath. OrgPath calculator runs outside Entra."
            Limitations = "Caller must detect changes and recompute. Advantage: OrgPath logic is in maintainable code, not provisioning expressions."
        }
    },
    @{
        LifecycleEvent = "Leaver (termination/offboarding)"
        Workday        = @{
            Support     = "Native"
            Mechanism   = "Termination in Workday → connector sets accountEnabled=false. Can trigger license removal via Lifecycle Workflows."
            Limitations = "Hard delete requires manual process or Lifecycle Workflow automation. Grace period management is external."
        }
        OracleHCM      = @{
            Support     = "Native"
            Mechanism   = "Termination in Oracle HCM → connector sets accountEnabled=false. Similar Lifecycle Workflow integration."
            Limitations = "Same as Workday — soft disable is automatic, hard delete requires additional automation."
        }
        APIDriven      = @{
            Support     = "Full control"
            Mechanism   = "Caller sends termination update. Can set exact disable date, trigger immediate or scheduled disable."
            Limitations = "Caller must implement termination date logic and grace periods. Full flexibility but more implementation work."
        }
    },
    @{
        LifecycleEvent = "Rehire (returning employee)"
        Workday        = @{
            Support     = "Native"
            Mechanism   = "Workday rehire event → connector matches existing Entra user by employeeId, re-enables account."
            Limitations = "May create duplicate if correlation attribute changed. Pre-existing attributes may not reset cleanly."
        }
        OracleHCM      = @{
            Support     = "Native"
            Mechanism   = "Oracle rehire event → connector matches existing Entra user, re-enables account."
            Limitations = "Same correlation challenges. PersonNumber must remain consistent across employment periods."
        }
        APIDriven      = @{
            Support     = "Full control"
            Mechanism   = "Caller pushes rehire with same employeeId. Correlation and attribute reset fully controlled."
            Limitations = "Caller must implement rehire detection and attribute reconciliation logic."
        }
    },
    @{
        LifecycleEvent = "Conversion (contractor → employee, intern → FTE)"
        Workday        = @{
            Support     = "Limited"
            Mechanism   = "Worker type change in Workday flows through. employeeType attribute updated. OrgPath may need recalculation."
            Limitations = "Complex: may require UPN change (different domain), license swap, group membership changes. Not all handled by connector alone."
        }
        OracleHCM      = @{
            Support     = "Limited"
            Mechanism   = "WorkerType change in Oracle flows through. Similar constraints to Workday."
            Limitations = "Same complexity — conversion often requires manual coordination with license and access changes."
        }
        APIDriven      = @{
            Support     = "Full control"
            Mechanism   = "Caller pushes all updated attributes atomically — new worker type, new OrgPath, new UPN if needed."
            Limitations = "Most control but most development effort. Advantage: all conversion logic in one place."
        }
    }
)

Write-Host "  Analyzed $($jmlComparison.Count) lifecycle events across 3 connectors" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 4: Feature Comparison Matrix
# ═══════════════════════════════════════════════════════════════

Write-Host "[4/6] Building feature comparison matrix..." -ForegroundColor Yellow

$featureComparison = @(
    # ── Provisioning Capabilities ──
    @{ Category = "Provisioning"; Feature = "Entra ID cloud-only provisioning"; Workday = "Yes"; OracleHCM = "Yes"; APIDriven = "Yes"; Weight = "Critical" },
    @{ Category = "Provisioning"; Feature = "On-premises AD writeback"; Workday = "Yes (via Provisioning Agent)"; OracleHCM = "Yes (via Provisioning Agent)"; APIDriven = "Yes (via Provisioning Agent)"; Weight = "Critical" },
    @{ Category = "Provisioning"; Feature = "Hybrid coexistence (AD + Entra ID)"; Workday = "Yes — dual provisioning"; OracleHCM = "Yes — dual provisioning"; APIDriven = "Yes — dual provisioning"; Weight = "Critical" },
    @{ Category = "Provisioning"; Feature = "Bulk initial load"; Workday = "Yes (full sync)"; OracleHCM = "Yes (full sync)"; APIDriven = "Yes (CSV bulk upload)"; Weight = "High" },
    @{ Category = "Provisioning"; Feature = "Incremental delta sync"; Workday = "Yes (polling-based)"; OracleHCM = "Yes (ATOM feed delta)"; APIDriven = "Yes (caller-controlled)"; Weight = "High" },
    @{ Category = "Provisioning"; Feature = "Real-time provisioning (<5 min)"; Workday = "No (40 min default poll)"; OracleHCM = "No (40 min default poll)"; APIDriven = "Yes (immediate on push)"; Weight = "Medium" },
    @{ Category = "Provisioning"; Feature = "On-demand provisioning (single user)"; Workday = "Yes (portal trigger)"; OracleHCM = "Yes (portal trigger)"; APIDriven = "Yes (single SCIM call)"; Weight = "Medium" },

    # ── Expression & Transformation ──
    @{ Category = "Expressions"; Feature = "Built-in provisioning expressions"; Workday = "Yes — 25+ functions"; OracleHCM = "Yes — 25+ functions"; APIDriven = "N/A — caller pre-computes"; Weight = "High" },
    @{ Category = "Expressions"; Feature = "Custom expression authoring"; Workday = "Yes (Entra expression builder)"; OracleHCM = "Yes (Entra expression builder)"; APIDriven = "N/A — arbitrary code"; Weight = "Medium" },
    @{ Category = "Expressions"; Feature = "OrgPath calculation complexity"; Workday = "High — nested Switch/Join in expression"; OracleHCM = "High — nested Switch/Join in expression"; APIDriven = "Low — OrgPath calculator in code (per D1.2)"; Weight = "Critical" },
    @{ Category = "Expressions"; Feature = "UPN collision resolution"; Workday = "Limited — expression-based counters"; OracleHCM = "Limited — expression-based counters"; APIDriven = "Full — code-based resolution (per D1.5)"; Weight = "High" },
    @{ Category = "Expressions"; Feature = "Diacritic transliteration"; Workday = "Manual expression per character"; OracleHCM = "Manual expression per character"; APIDriven = "Full — 80+ transliterations in code (per D1.5)"; Weight = "Medium" },

    # ── Monitoring & Operations ──
    @{ Category = "Operations"; Feature = "Provisioning logs in Entra portal"; Workday = "Yes"; OracleHCM = "Yes"; APIDriven = "Yes"; Weight = "Critical" },
    @{ Category = "Operations"; Feature = "Quarantine mode (auto-pause on errors)"; Workday = "Yes (built-in)"; OracleHCM = "Yes (built-in)"; APIDriven = "Yes (built-in for /bulkUpload)"; Weight = "High" },
    @{ Category = "Operations"; Feature = "Audit log retention"; Workday = "30 days (Entra provisioning logs)"; OracleHCM = "30 days (Entra provisioning logs)"; APIDriven = "30 days (Entra provisioning logs)"; Weight = "Medium" },
    @{ Category = "Operations"; Feature = "Graph API for provisioning status"; Workday = "Yes (provisioningObjectSummary)"; OracleHCM = "Yes (provisioningObjectSummary)"; APIDriven = "Yes (provisioningObjectSummary)"; Weight = "Medium" },
    @{ Category = "Operations"; Feature = "Email notifications on failure"; Workday = "Yes (configurable)"; OracleHCM = "Yes (configurable)"; APIDriven = "Yes (configurable)"; Weight = "Low" },

    # ── GCC & Compliance ──
    @{ Category = "Compliance"; Feature = "GCC-Moderate availability"; Workday = "Yes"; OracleHCM = "Yes"; APIDriven = "Yes (inherits Entra)"; Weight = "Critical" },
    @{ Category = "Compliance"; Feature = "FedRAMP Moderate authorization"; Workday = "Workday Govt Cloud authorized"; OracleHCM = "Oracle Govt Cloud authorized"; APIDriven = "Inherits M365 GCC authorization"; Weight = "Critical" },
    @{ Category = "Compliance"; Feature = "Data residency (US sovereign)"; Workday = "Workday Govt Cloud — US only"; OracleHCM = "Oracle Govt Cloud — US only"; APIDriven = "Inherits M365 GCC — US only"; Weight = "Critical" },
    @{ Category = "Compliance"; Feature = "FIPS 140-2 encryption in transit"; Workday = "Yes (TLS 1.2+)"; OracleHCM = "Yes (TLS 1.2+)"; APIDriven = "Yes (Graph API TLS 1.2+)"; Weight = "High" },

    # ── Architecture & Extensibility ──
    @{ Category = "Architecture"; Feature = "HR vendor independence"; Workday = "No — Workday only"; OracleHCM = "No — Oracle HCM only"; APIDriven = "Yes — any HR system (ADR-003)"; Weight = "Critical" },
    @{ Category = "Architecture"; Feature = "Schema normalizer layer"; Workday = "Not needed (direct mapping)"; OracleHCM = "Not needed (direct mapping)"; APIDriven = "Required (custom middleware)"; Weight = "High" },
    @{ Category = "Architecture"; Feature = "Multi-HR-system federation"; Workday = "One Workday tenant only"; OracleHCM = "One Oracle tenant only"; APIDriven = "Unlimited sources via API"; Weight = "High" },
    @{ Category = "Architecture"; Feature = "Custom worker type taxonomy"; Workday = "Limited to Workday types"; OracleHCM = "Limited to Oracle types"; APIDriven = "Full — canonical types per D1.6"; Weight = "Medium" },
    @{ Category = "Architecture"; Feature = "Migration path if HR vendor changes"; Workday = "Replace entire connector"; OracleHCM = "Replace entire connector"; APIDriven = "Update schema normalizer only"; Weight = "Critical" }
)

$categories = $featureComparison | Group-Object Category
foreach ($cat in $categories) {
    Write-Host "  $($cat.Name): $($cat.Count) features evaluated" -ForegroundColor DarkGreen
}

# ═══════════════════════════════════════════════════════════════
# SECTION 5: OPM Procurement Context
# ═══════════════════════════════════════════════════════════════

Write-Host "[5/6] Adding OPM procurement context..." -ForegroundColor Yellow

$procurementContext = @{
    Program           = "OPM Human Resources Information Technology (HRIT) Modernization"
    Status            = "Final evaluation — decision expected early June 2026"
    Finalists         = @(
        @{
            Vendor     = "Workday"
            Integrator = "Accenture Federal Services"
            Platform   = "Workday Government Cloud (FedRAMP Moderate)"
            Notes      = "Strong federal track record. Cloud-native HCM. Extensive Entra ID integration ecosystem."
        },
        @{
            Vendor     = "Oracle"
            Integrator = "Deloitte Consulting"
            Platform   = "Oracle Cloud HCM for Government (FedRAMP Moderate)"
            Notes      = "Deep ERP integration. Comprehensive HCM suite. Oracle Govt Cloud data residency."
        }
    )
    Protests          = @(
        @{ Protester = "IBM"; Status = "GAO protest filed"; Resolution = "Pending" },
        @{ Protester = "EconSys (now Axiom)"; Status = "GAO protest filed"; Resolution = "Pending" }
    )
    UIAOImplication   = "ADR-003 (API-Driven Inbound Provisioning) was specifically designed to decouple UIAO identity provisioning from the OPM HR vendor decision. Regardless of whether OPM selects Workday or Oracle, the UIAO provisioning architecture remains unchanged — only the schema normalizer layer adapts to the winning vendor's data model."
    Recommendation    = "Implement API-driven inbound provisioning as the canonical approach. If the selected HR vendor is Workday or Oracle, the native connector can run IN PARALLEL as an accelerator during initial deployment, with API-driven as the long-term strategic path."
}

Write-Host "  OPM context: $($procurementContext.Finalists.Count) finalists, $($procurementContext.Protests.Count) protests" -ForegroundColor Green

# ═══════════════════════════════════════════════════════════════
# SECTION 6: UIAO Strategic Assessment
# ═══════════════════════════════════════════════════════════════

$strategicAssessment = @{
    CanonicalApproach   = "API-Driven Inbound Provisioning (ADR-003)"
    Rationale           = @(
        "HR vendor independence — OPM decision does not affect identity architecture",
        "OrgPath calculation in maintainable code rather than provisioning expressions",
        "UPN generation with full diacritic transliteration (80+ characters) — impractical in provisioning expressions",
        "Worker type taxonomy enforcement at the schema normalizer layer",
        "Multi-source federation capability for contractor/vendor/volunteer populations",
        "Real-time provisioning capability (no 40-minute polling delay)",
        "Custom collision resolution with database-backed uniqueness checks",
        "Testable — schema normalizer is unit-testable code, provisioning expressions are not",
        "Auditable — full transformation pipeline visible in code, not buried in connector config"
    )
    HybridStrategy      = "Deploy native Workday/Oracle connector for basic attribute sync during initial rollout. Run API-driven provisioning in parallel for OrgPath, UPN, and worker type. Transition fully to API-driven once schema normalizer is validated."
    RiskMitigation      = @(
        "If OPM decision is delayed beyond June 2026 — API-driven approach is unaffected",
        "If GAO sustains protests — API-driven approach is unaffected",
        "If winning vendor changes connector capabilities — API-driven approach is unaffected",
        "If UIAO expands to multi-agency — API-driven handles heterogeneous HR systems natively"
    )
}

# ═══════════════════════════════════════════════════════════════
# OUTPUT: Assemble and Export
# ═══════════════════════════════════════════════════════════════

Write-Host "[6/6] Exporting comparison matrix..." -ForegroundColor Yellow

$results = @{
    Metadata = @{
        GeneratedAt   = (Get-Date -Format "o")
        Generator     = "Spec2-D1.7-New-HRConnectorComparisonMatrix.ps1"
        UIAORef       = "UIAO_136 Spec 2, Phase 1, D1.7"
        ADRRef        = @("ADR-003", "ADR-048")
        Description   = "HR Connector Comparison Matrix — Workday vs Oracle HCM vs API-Driven Inbound"
    }
    Connectors         = $connectors
    AttributeSupport   = $attributeCategories
    JMLLifecycle       = $jmlComparison
    FeatureComparison  = $featureComparison
    OPMProcurement     = $procurementContext
    StrategicAssessment = $strategicAssessment
}

# ── JSON export ──
$jsonPath = Join-Path $OutputPath "${outPrefix}.json"
$results | ConvertTo-Json -Depth 10 | Set-Content -Path $jsonPath -Encoding UTF8
Write-Host "  JSON: $jsonPath" -ForegroundColor Green

# ── CSV export (feature comparison summary) ──
$csvPath = Join-Path $OutputPath "${outPrefix}_features.csv"
$csvData = foreach ($f in $featureComparison) {
    [PSCustomObject]@{
        Category  = $f.Category
        Feature   = $f.Feature
        Weight    = $f.Weight
        Workday   = $f.Workday
        OracleHCM = $f.OracleHCM
        APIDriven = $f.APIDriven
    }
}
$csvData | Export-Csv -Path $csvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $csvPath" -ForegroundColor Green

# ── CSV export (attribute support) ──
$attrCsvPath = Join-Path $OutputPath "${outPrefix}_attributes.csv"
$attrCsvData = foreach ($cat in $attributeCategories) {
    foreach ($a in $cat.Attributes) {
        [PSCustomObject]@{
            Category  = $cat.Category
            Attribute = $a.Attribute
            Workday   = $a.Workday
            OracleHCM = $a.OracleHCM
            APIDriven = $a.APIDriven
            Notes     = $a.Notes
        }
    }
}
$attrCsvData | Export-Csv -Path $attrCsvPath -NoTypeInformation -Encoding UTF8
Write-Host "  CSV:  $attrCsvPath" -ForegroundColor Green

# ── Markdown report ──
$mdPath = Join-Path $OutputPath "${outPrefix}_report.md"
$md = @"
# UIAO Spec 2 — D1.7: HR Connector Comparison Matrix

> Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
> Ref: UIAO_136 Spec 2, Phase 1, D1.7 | ADR-003 | ADR-048

---

## Executive Summary

Three HR-to-Entra ID provisioning approaches were evaluated for UIAO GCC-Moderate
deployment. **API-Driven Inbound Provisioning (ADR-003) is the canonical UIAO approach**
because it provides HR vendor independence, superior OrgPath calculation capabilities,
and immunity to the pending OPM HRIT vendor decision.

## Connector Profiles

| Connector | HR System | GCC-Moderate | Type |
|---|---|---|---|
| Workday Inbound | Workday HCM | Available | Native SaaS Connector |
| Oracle HCM Inbound | Oracle Cloud HCM | Available | Native SaaS Connector |
| API-Driven Inbound | Any (HR-agnostic) | Available | Platform API Endpoint |

## Feature Comparison (Critical Items)

| Feature | Workday | Oracle HCM | API-Driven |
|---|---|---|---|

"@

$criticalFeatures = $featureComparison | Where-Object { $_.Weight -eq "Critical" }
foreach ($f in $criticalFeatures) {
    $md += "| $($f.Feature) | $($f.Workday) | $($f.OracleHCM) | $($f.APIDriven) |`n"
}

$md += @"

## OPM Procurement Context

- **Status:** $($procurementContext.Status)
- **Finalists:** Workday/Accenture, Oracle/Deloitte
- **Protests:** IBM and EconSys (GAO)
- **UIAO Impact:** $($procurementContext.UIAOImplication)

## UIAO Strategic Recommendation

**Canonical Approach:** $($strategicAssessment.CanonicalApproach)

**Hybrid Strategy:** $($strategicAssessment.HybridStrategy)

### Rationale

"@

foreach ($r in $strategicAssessment.Rationale) {
    $md += "- $r`n"
}

$md += @"

### Risk Mitigation

"@

foreach ($r in $strategicAssessment.RiskMitigation) {
    $md += "- $r`n"
}

Set-Content -Path $mdPath -Value $md -Encoding UTF8
Write-Host "  MD:   $mdPath" -ForegroundColor Green

# ── Console Dashboard ──
Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " HR CONNECTOR COMPARISON — DASHBOARD" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

Write-Host "`n  CANONICAL APPROACH: " -NoNewline
Write-Host "API-Driven Inbound Provisioning (ADR-003)" -ForegroundColor Green

Write-Host "`n  ┌─────────────────────────────────────────────────────────────┐"
Write-Host "  │ FEATURE COVERAGE (Critical Items)                           │"
Write-Host "  ├──────────────────────────────┬──────┬──────┬───────────────┤"
Write-Host "  │ Feature                      │  WD  │  ORA │  API-Driven   │"
Write-Host "  ├──────────────────────────────┼──────┼──────┼───────────────┤"

foreach ($f in $criticalFeatures) {
    $wd  = if ($f.Workday -match "^Yes|^Native") { " Yes " } elseif ($f.Workday -match "^No") { "  No " } else { " Ltd " }
    $ora = if ($f.OracleHCM -match "^Yes|^Native") { " Yes " } elseif ($f.OracleHCM -match "^No") { "  No " } else { " Ltd " }
    $api = if ($f.APIDriven -match "^Yes|^Full|^Inherits") { "     Yes     " } elseif ($f.APIDriven -match "^No") { "      No     " } else { "    Varies   " }

    $label = $f.Feature.PadRight(28).Substring(0, 28)
    Write-Host "  │ $label │$wd│$ora│$api│"
}

Write-Host "  └──────────────────────────────┴──────┴──────┴───────────────┘"

Write-Host "`n  OPM PROCUREMENT:" -ForegroundColor Yellow
Write-Host "    Finalists: Workday/Accenture | Oracle/Deloitte"
Write-Host "    Decision:  Early June 2026 (pending GAO protests)"
Write-Host "    UIAO Impact: " -NoNewline
Write-Host "NONE — API-driven is vendor-independent" -ForegroundColor Green

Write-Host "`n  OUTPUT FILES:" -ForegroundColor Yellow
Write-Host "    JSON:     $jsonPath" -ForegroundColor DarkGray
Write-Host "    CSV:      $csvPath" -ForegroundColor DarkGray
Write-Host "    CSV:      $attrCsvPath" -ForegroundColor DarkGray
Write-Host "    Markdown: $mdPath" -ForegroundColor DarkGray

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host " D1.7 Complete — feeds D2.1 (Target State) and D2.2 (Runbook)" -ForegroundColor Green
Write-Host "================================================================`n" -ForegroundColor Cyan
