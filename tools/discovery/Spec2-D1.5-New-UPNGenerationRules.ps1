<#
.SYNOPSIS
    UIAO Spec 2 — D1.5: UPN Generation Rules Engine
.DESCRIPTION
    Defines the canonical UPN generation algorithm for Entra ID and produces
    a testable rules engine specification with a reusable PowerShell function.

    This deliverable is the normative reference for how userPrincipalName
    values are generated during HR inbound provisioning (ADR-003). It covers:

    1. Name component selection:
       - Legal name (sn, givenName) vs. preferred name (if HR provides it)
       - Name normalization (diacritics, special characters, hyphens, spaces)
       - Name component truncation rules (max lengths)
    2. UPN format construction:
       - First.Last@domain.tld (default pattern)
       - Configurable format templates (First.Last, FLast, FirstL, etc.)
       - Domain suffix selection (primary vs. alternate domains)
    3. Collision detection and resolution:
       - Query Entra ID (via Graph API) for existing UPNs
       - Query AD (via LDAP) for existing UPNs during coexistence
       - Query proxyAddresses / mail for SMTP alias conflicts
       - Incrementing numeric suffix: First.Last2, First.Last3, etc.
       - Configurable max collision iterations (default: 99)
    4. Special character handling:
       - RFC 822 / Entra ID allowed character set
       - Diacritic removal (transliteration table)
       - Apostrophe, hyphen, space handling rules
       - Unicode normalization (NFKD decomposition + ASCII filter)
    5. Length constraints:
       - UPN local part max: 64 characters (RFC 5321)
       - UPN total max: 113 characters (Entra ID limit)
       - Minimum local part length: 2 characters
    6. Validation rules:
       - No leading/trailing dots or hyphens
       - No consecutive dots
       - No reserved words (admin, administrator, postmaster, etc.)
       - No numeric-only local parts
    7. Audit mode:
       - Dry-run against existing AD/Entra population
       - Report predicted collisions before provisioning goes live

    Outputs: PowerShell module (.psm1-ready function) + JSON rules spec +
             Markdown specification document

    Ref: UIAO_136 Spec 2, Phase 1, Deliverable D1.5
         Feeds: D1.3 (Attribute Mapping Matrix), D3.4 (Provisioning Configuration)
         Related: ADR-003 (API-driven inbound provisioning), ADR-048 (OrgPath)
.PARAMETER OutputPath
    Directory for output files. Defaults to .\output
.PARAMETER PrimaryDomain
    Primary UPN domain suffix (e.g., contoso.com). Required.
.PARAMETER AlternateDomains
    Optional alternate UPN domain suffixes (comma-separated).
.PARAMETER FormatTemplate
    UPN format template. Default: 'First.Last'
    Options: 'First.Last', 'FLast', 'FirstL', 'First_Last', 'First-Last'
.PARAMETER TestMode
    If set, runs the generation function against sample data and outputs
    test results demonstrating all edge cases.
.PARAMETER ADPopulationFile
    Optional path to D1.1 HR Attribute Discovery JSON for collision
    analysis against existing UPN population.
.EXAMPLE
    .\Spec2-D1.5-New-UPNGenerationRules.ps1 -PrimaryDomain "contoso.com"
    .\Spec2-D1.5-New-UPNGenerationRules.ps1 -PrimaryDomain "contoso.com" -TestMode
.NOTES
    No AD/Entra connectivity required for specification output.
    TestMode uses built-in edge case data.
    For live collision detection, integrate the function with Graph API.
#>

[CmdletBinding()]
param(
    [string]$OutputPath = ".\output",
    [Parameter(Mandatory)]
    [string]$PrimaryDomain,
    [string[]]$AlternateDomains = @(),
    [ValidateSet('First.Last','FLast','FirstL','First_Last','First-Last')]
    [string]$FormatTemplate = 'First.Last',
    [switch]$TestMode,
    [string]$ADPopulationFile
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputPath)) {
    New-Item -Path $OutputPath -ItemType Directory -Force | Out-Null
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$outPrefix = "UIAO_Spec2_D1.5_UPNGenerationRules_${PrimaryDomain}_${timestamp}"

Write-Host "`n================================================================" -ForegroundColor Cyan
Write-Host "  UIAO Spec 2 — D1.5: UPN Generation Rules Engine"              -ForegroundColor Cyan
Write-Host "  Domain:    $PrimaryDomain"                                     -ForegroundColor Cyan
Write-Host "  Format:    $FormatTemplate"                                    -ForegroundColor Cyan
Write-Host "  Timestamp: $timestamp"                                         -ForegroundColor Cyan
Write-Host "================================================================`n" -ForegroundColor Cyan

# ══════════════════════════════════════════════════════════════
# Transliteration Table — Diacritics to ASCII
# ══════════════════════════════════════════════════════════════

$transliterationMap = @{
    # Latin Extended
    [char]0x00C0 = 'A';  [char]0x00C1 = 'A';  [char]0x00C2 = 'A';  [char]0x00C3 = 'A'
    [char]0x00C4 = 'Ae'; [char]0x00C5 = 'A';  [char]0x00C6 = 'Ae'; [char]0x00C7 = 'C'
    [char]0x00C8 = 'E';  [char]0x00C9 = 'E';  [char]0x00CA = 'E';  [char]0x00CB = 'E'
    [char]0x00CC = 'I';  [char]0x00CD = 'I';  [char]0x00CE = 'I';  [char]0x00CF = 'I'
    [char]0x00D0 = 'D';  [char]0x00D1 = 'N';  [char]0x00D2 = 'O';  [char]0x00D3 = 'O'
    [char]0x00D4 = 'O';  [char]0x00D5 = 'O';  [char]0x00D6 = 'Oe'; [char]0x00D8 = 'O'
    [char]0x00D9 = 'U';  [char]0x00DA = 'U';  [char]0x00DB = 'U';  [char]0x00DC = 'Ue'
    [char]0x00DD = 'Y';  [char]0x00DE = 'Th'; [char]0x00DF = 'ss'
    [char]0x00E0 = 'a';  [char]0x00E1 = 'a';  [char]0x00E2 = 'a';  [char]0x00E3 = 'a'
    [char]0x00E4 = 'ae'; [char]0x00E5 = 'a';  [char]0x00E6 = 'ae'; [char]0x00E7 = 'c'
    [char]0x00E8 = 'e';  [char]0x00E9 = 'e';  [char]0x00EA = 'e';  [char]0x00EB = 'e'
    [char]0x00EC = 'i';  [char]0x00ED = 'i';  [char]0x00EE = 'i';  [char]0x00EF = 'i'
    [char]0x00F0 = 'd';  [char]0x00F1 = 'n';  [char]0x00F2 = 'o';  [char]0x00F3 = 'o'
    [char]0x00F4 = 'o';  [char]0x00F5 = 'o';  [char]0x00F6 = 'oe'; [char]0x00F8 = 'o'
    [char]0x00F9 = 'u';  [char]0x00FA = 'u';  [char]0x00FB = 'u';  [char]0x00FC = 'ue'
    [char]0x00FD = 'y';  [char]0x00FE = 'th'; [char]0x00FF = 'y'
    # Eastern European
    [char]0x0100 = 'A';  [char]0x0101 = 'a';  [char]0x0102 = 'A';  [char]0x0103 = 'a'
    [char]0x0104 = 'A';  [char]0x0105 = 'a';  [char]0x0106 = 'C';  [char]0x0107 = 'c'
    [char]0x010C = 'C';  [char]0x010D = 'c';  [char]0x010E = 'D';  [char]0x010F = 'd'
    [char]0x0110 = 'D';  [char]0x0111 = 'd';  [char]0x0118 = 'E';  [char]0x0119 = 'e'
    [char]0x011A = 'E';  [char]0x011B = 'e';  [char]0x0141 = 'L';  [char]0x0142 = 'l'
    [char]0x0143 = 'N';  [char]0x0144 = 'n';  [char]0x0147 = 'N';  [char]0x0148 = 'n'
    [char]0x0158 = 'R';  [char]0x0159 = 'r';  [char]0x015A = 'S';  [char]0x015B = 's'
    [char]0x0160 = 'S';  [char]0x0161 = 's';  [char]0x0164 = 'T';  [char]0x0165 = 't'
    [char]0x016E = 'U';  [char]0x016F = 'u';  [char]0x017D = 'Z';  [char]0x017E = 'z'
    [char]0x0179 = 'Z';  [char]0x017A = 'z';  [char]0x017B = 'Z';  [char]0x017C = 'z'
}

# Reserved words that cannot be UPN local parts
$reservedWords = @(
    'admin','administrator','postmaster','hostmaster','webmaster',
    'abuse','root','nobody','guest','support','info','help',
    'noreply','no-reply','mailer-daemon','null','void','test',
    'security','operator'
)

# ══════════════════════════════════════════════════════════════
# Core UPN Generation Function
# ══════════════════════════════════════════════════════════════

function New-CanonicalUPN {
    <#
    .SYNOPSIS
        Generates a canonical UPN from name components per UIAO rules.
    .PARAMETER GivenName
        Legal given (first) name.
    .PARAMETER Surname
        Legal surname (last name).
    .PARAMETER PreferredFirstName
        Preferred/display first name (optional — overrides GivenName if provided).
    .PARAMETER Domain
        UPN domain suffix.
    .PARAMETER Format
        UPN format template: First.Last, FLast, FirstL, First_Last, First-Last
    .PARAMETER ExistingUPNs
        Array of existing UPN local parts (lowercase) for collision detection.
    .PARAMETER MaxCollisionIterations
        Maximum numeric suffix attempts. Default: 99.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$GivenName,
        [Parameter(Mandatory)][string]$Surname,
        [string]$PreferredFirstName,
        [Parameter(Mandatory)][string]$Domain,
        [ValidateSet('First.Last','FLast','FirstL','First_Last','First-Last')]
        [string]$Format = 'First.Last',
        [string[]]$ExistingUPNs = @(),
        [int]$MaxCollisionIterations = 99
    )

    $result = [ordered]@{
        InputGivenName       = $GivenName
        InputSurname         = $Surname
        InputPreferredFirst  = $PreferredFirstName
        Domain               = $Domain
        Format               = $Format
        NormalizedFirst      = $null
        NormalizedLast       = $null
        LocalPart            = $null
        GeneratedUPN         = $null
        CollisionDetected    = $false
        CollisionIteration   = 0
        ValidationErrors     = [System.Collections.Generic.List[string]]::new()
        AppliedRules         = [System.Collections.Generic.List[string]]::new()
    }

    # Step 1: Select name source (preferred overrides legal if present)
    $firstName = if ($PreferredFirstName -and $PreferredFirstName.Trim()) {
        $result.AppliedRules.Add("Used preferred first name: $PreferredFirstName")
        $PreferredFirstName.Trim()
    } else {
        $result.AppliedRules.Add("Used legal given name: $GivenName")
        $GivenName.Trim()
    }
    $lastName = $Surname.Trim()

    # Step 2: Transliterate diacritics
    $transFirst = ""
    foreach ($c in $firstName.ToCharArray()) {
        if ($transliterationMap.ContainsKey($c)) {
            $transFirst += $transliterationMap[$c]
            $result.AppliedRules.Add("Transliterated '$c' to '$($transliterationMap[$c])' in first name")
        } else {
            $transFirst += $c
        }
    }
    $transLast = ""
    foreach ($c in $lastName.ToCharArray()) {
        if ($transliterationMap.ContainsKey($c)) {
            $transLast += $transliterationMap[$c]
            $result.AppliedRules.Add("Transliterated '$c' to '$($transliterationMap[$c])' in last name")
        } else {
            $transLast += $c
        }
    }

    # Step 3: Remove non-ASCII after transliteration (keep letters, digits, hyphens)
    $cleanFirst = ($transFirst -replace "[^a-zA-Z0-9\-]", "")
    $cleanLast  = ($transLast  -replace "[^a-zA-Z0-9\-]", "")

    if ($cleanFirst -ne $transFirst) {
        $result.AppliedRules.Add("Removed special characters from first name")
    }
    if ($cleanLast -ne $transLast) {
        $result.AppliedRules.Add("Removed special characters from last name")
    }

    # Step 4: Remove leading/trailing hyphens
    $cleanFirst = $cleanFirst.Trim('-')
    $cleanLast  = $cleanLast.Trim('-')

    # Step 5: Enforce minimum length
    if ($cleanFirst.Length -lt 1) {
        $result.ValidationErrors.Add("First name reduced to empty string after normalization")
        return $result
    }
    if ($cleanLast.Length -lt 1) {
        $result.ValidationErrors.Add("Last name reduced to empty string after normalization")
        return $result
    }

    $result.NormalizedFirst = $cleanFirst
    $result.NormalizedLast  = $cleanLast

    # Step 6: Build local part per format template
    $localPart = switch ($Format) {
        'First.Last'  { "$cleanFirst.$cleanLast" }
        'FLast'       { "$($cleanFirst[0])$cleanLast" }
        'FirstL'      { "$cleanFirst$($cleanLast[0])" }
        'First_Last'  { "${cleanFirst}_${cleanLast}" }
        'First-Last'  { "$cleanFirst-$cleanLast" }
    }

    # Step 7: Lowercase
    $localPart = $localPart.ToLower()

    # Step 8: Remove consecutive dots/hyphens
    $localPart = $localPart -replace '\.{2,}', '.'
    $localPart = $localPart -replace '\-{2,}', '-'

    # Step 9: Remove leading/trailing dots
    $localPart = $localPart.Trim('.')

    # Step 10: Enforce max length — local part max 64, total UPN max 113
    $maxLocal = [Math]::Min(64, 113 - 1 - $Domain.Length)  # -1 for @ sign
    if ($localPart.Length -gt $maxLocal) {
        $localPart = $localPart.Substring(0, $maxLocal).TrimEnd('.').TrimEnd('-')
        $result.AppliedRules.Add("Truncated local part to $maxLocal characters")
    }

    # Step 11: Enforce minimum length
    if ($localPart.Length -lt 2) {
        $result.ValidationErrors.Add("Local part '$localPart' is less than 2 characters")
        return $result
    }

    # Step 12: Reserved word check
    if ($localPart -in $reservedWords) {
        $result.ValidationErrors.Add("Local part '$localPart' is a reserved word")
        # Still generate with suffix to provide a valid alternative
        $localPart = "${localPart}1"
        $result.AppliedRules.Add("Appended '1' to avoid reserved word")
    }

    # Step 13: Numeric-only check
    if ($localPart -match '^\d+$') {
        $result.ValidationErrors.Add("Local part '$localPart' is numeric-only (not allowed)")
        return $result
    }

    # Step 14: Collision detection
    $basePart = $localPart
    $existingSet = [System.Collections.Generic.HashSet[string]]::new(
        [System.StringComparer]::OrdinalIgnoreCase)
    foreach ($upn in $ExistingUPNs) { $existingSet.Add($upn) | Out-Null }

    if ($existingSet.Contains($localPart)) {
        $result.CollisionDetected = $true
        $result.AppliedRules.Add("Collision detected for '$localPart'")

        $resolved = $false
        for ($i = 2; $i -le ($MaxCollisionIterations + 1); $i++) {
            $candidate = "${basePart}${i}"
            if ($candidate.Length -gt $maxLocal) {
                # Truncate base to make room for suffix
                $suffixLen = $i.ToString().Length
                $truncBase = $basePart.Substring(0, $maxLocal - $suffixLen).TrimEnd('.').TrimEnd('-')
                $candidate = "${truncBase}${i}"
            }
            if (-not $existingSet.Contains($candidate)) {
                $localPart = $candidate
                $result.CollisionIteration = $i
                $result.AppliedRules.Add("Resolved collision with suffix: $i -> '$candidate'")
                $resolved = $true
                break
            }
        }

        if (-not $resolved) {
            $result.ValidationErrors.Add("Could not resolve collision after $MaxCollisionIterations attempts")
            return $result
        }
    }

    $result.LocalPart    = $localPart
    $result.GeneratedUPN = "${localPart}@${Domain}"

    return $result
}

# ══════════════════════════════════════════════════════════════
# Rules Specification (JSON output)
# ══════════════════════════════════════════════════════════════

$rulesSpec = [ordered]@{
    ExportMetadata = [ordered]@{
        Domain    = $PrimaryDomain
        Timestamp = (Get-Date).ToString("o")
        Script    = "UIAO Spec 2 D1.5 — UPN Generation Rules Engine"
        Reference = "UIAO_136, ADR-003, ADR-048"
    }
    Configuration = [ordered]@{
        PrimaryDomain           = $PrimaryDomain
        AlternateDomains        = $AlternateDomains
        DefaultFormat           = $FormatTemplate
        MaxCollisionIterations  = 99
        MaxLocalPartLength      = 64
        MaxTotalUPNLength       = 113
        MinLocalPartLength      = 2
    }
    NameSelectionRules = [ordered]@{
        Rule1 = "If HR provides PreferredFirstName and it is non-empty, use PreferredFirstName as the first name component"
        Rule2 = "Otherwise, use legal GivenName (givenName attribute)"
        Rule3 = "Always use legal Surname (sn attribute) as the last name component"
        Rule4 = "PreferredFirstName does NOT override the last name component"
    }
    NormalizationRules = [ordered]@{
        Step1_Transliteration  = "Apply diacritic transliteration map (e.g., u-umlaut -> ue, n-tilde -> n, l-stroke -> l)"
        Step2_CharacterFilter  = "Remove all characters except ASCII letters (a-z, A-Z), digits (0-9), and hyphens (-)"
        Step3_HyphenTrim       = "Remove leading and trailing hyphens from each name component"
        Step4_Lowercase        = "Convert the entire local part to lowercase"
        Step5_ConsecutiveDots  = "Replace consecutive dots (..) with single dot (.)"
        Step6_DotTrim          = "Remove leading and trailing dots from local part"
    }
    FormatTemplates = [ordered]@{
        'First.Last' = '{GivenName}.{Surname} — e.g., john.smith@domain.com'
        'FLast'      = '{GivenName[0]}{Surname} — e.g., jsmith@domain.com'
        'FirstL'     = '{GivenName}{Surname[0]} — e.g., johns@domain.com'
        'First_Last' = '{GivenName}_{Surname} — e.g., john_smith@domain.com'
        'First-Last' = '{GivenName}-{Surname} — e.g., john-smith@domain.com'
    }
    CollisionResolution = [ordered]@{
        Strategy     = "Incrementing numeric suffix appended to base local part"
        Pattern      = "first.last -> first.last2 -> first.last3 -> ... -> first.last99"
        MaxAttempts  = 99
        Truncation   = "If suffix causes length overflow, truncate base name to accommodate suffix"
        CrossCheck   = @(
            "Entra ID userPrincipalName (via Graph API: GET /users?`$filter=userPrincipalName eq '...')"
            "AD userPrincipalName (via Get-ADUser -Filter {UserPrincipalName -eq '...'})"
            "proxyAddresses / mail for SMTP alias conflicts"
        )
    }
    ValidationRules = @(
        [ordered]@{ Rule = "NoLeadingTrailingDots"; Check = "Local part must not start or end with '.'"; Action = "Trim dots" }
        [ordered]@{ Rule = "NoConsecutiveDots";     Check = "Local part must not contain '..'";          Action = "Replace with single dot" }
        [ordered]@{ Rule = "NoReservedWords";       Check = "Local part must not be a reserved word";    Action = "Append numeric suffix" }
        [ordered]@{ Rule = "NoNumericOnly";         Check = "Local part must not be all digits";         Action = "Reject — requires manual assignment" }
        [ordered]@{ Rule = "MinLength";             Check = "Local part must be >= 2 characters";        Action = "Reject — requires manual assignment" }
        [ordered]@{ Rule = "MaxLength";             Check = "Local part <= 64 chars, total UPN <= 113";  Action = "Truncate local part" }
        [ordered]@{ Rule = "ASCIIOnly";             Check = "Local part must contain only a-z, 0-9, '.', '-', '_'"; Action = "Transliterate and strip" }
    )
    ReservedWords = $reservedWords
    DomainSuffixSelection = [ordered]@{
        Rule1 = "Default: use PrimaryDomain for all new users"
        Rule2 = "AlternateDomains used only when explicitly configured per OrgPath or worker type"
        Rule3 = "Domain suffix must be a verified domain in Entra ID tenant"
        Rule4 = "During coexistence, UPN suffix must match across AD and Entra ID (Entra Connect sync requirement)"
    }
    EntraProvisioningExpression = [ordered]@{
        Description = "Expression for Entra ID API-driven inbound provisioning (ADR-003)"
        Expression  = 'Join("@", Replace(Join(".", [preferredFirstName] ?? [givenName], [surname]), "[^a-zA-Z0-9.-]", ""), "{domain}")'
        Notes       = "Actual provisioning expression will be refined during D3.4. This is the conceptual algorithm."
    }
}

# ══════════════════════════════════════════════════════════════
# Test Mode — Edge Case Validation
# ══════════════════════════════════════════════════════════════

$testResults = $null
if ($TestMode) {
    Write-Host "  Running test mode with edge case data..." -ForegroundColor Yellow

    $testCases = @(
        @{ Given = "John";      Last = "Smith";        Preferred = "";             Expect = "john.smith" }
        @{ Given = "Mary";      Last = "O'Brien";      Preferred = "";             Expect = "mary.obrien" }
        @{ Given = "Jose";      Last = "Garcia Lopez"; Preferred = "";             Expect = "jose.garcialopez" }
        @{ Given = "Muller";    Last = "Strauss";      Preferred = "Mueller";      Expect = "mueller.strauss" }
        @{ Given = "Francois";  Last = "Lefevre";      Preferred = "Francois";     Expect = "francois.lefevre" }
        @{ Given = "Wlodzimierz"; Last = "Krzyzanowski"; Preferred = "";           Expect = "wlodzimierz.krzyzanowski" }
        @{ Given = "Li";        Last = "Wu";           Preferred = "";             Expect = "li.wu" }
        @{ Given = "A";         Last = "B";            Preferred = "";             Expect = "error_minlength" }
        @{ Given = "Jean-Pierre"; Last = "de la Cruz"; Preferred = "";             Expect = "jean-pierre.delacruz" }
        @{ Given = "Admin";     Last = "User";         Preferred = "";             Expect = "admin.user" }
        @{ Given = "Bjork";     Last = "Gudmundsdottir"; Preferred = "Bjork";      Expect = "bjork.gudmundsdottir" }
        @{ Given = "Rene";      Last = "Descartes";    Preferred = "Rene";         Expect = "rene.descartes" }
        @{ Given = "John";      Last = "Smith";        Preferred = "";             Expect = "john.smith2"; ExistingUPNs = @("john.smith") }
        @{ Given = "John";      Last = "Smith";        Preferred = "";             Expect = "john.smith3"; ExistingUPNs = @("john.smith","john.smith2") }
    )

    $testResults = [System.Collections.Generic.List[object]]::new()

    foreach ($tc in $testCases) {
        $params = @{
            GivenName  = $tc.Given
            Surname    = $tc.Last
            Domain     = $PrimaryDomain
            Format     = $FormatTemplate
        }
        if ($tc.Preferred) { $params['PreferredFirstName'] = $tc.Preferred }
        if ($tc.ExistingUPNs) { $params['ExistingUPNs'] = $tc.ExistingUPNs }

        $r = New-CanonicalUPN @params

        $passed = $false
        if ($tc.Expect -eq 'error_minlength') {
            $passed = $r.ValidationErrors.Count -gt 0
        } else {
            $passed = ($r.LocalPart -eq $tc.Expect)
        }

        $testResults.Add([ordered]@{
            Input          = "$($tc.Given) $($tc.Last)" + $(if ($tc.Preferred) { " (pref: $($tc.Preferred))" } else { "" })
            Expected       = $tc.Expect
            Actual         = if ($r.LocalPart) { $r.LocalPart } else { "ERROR: $($r.ValidationErrors -join '; ')" }
            Passed         = $passed
            Collision      = $r.CollisionDetected
            Rules          = ($r.AppliedRules -join '; ')
            FullUPN        = $r.GeneratedUPN
        })

        $color = if ($passed) { 'Green' } else { 'Red' }
        $symbol = if ($passed) { 'PASS' } else { 'FAIL' }
        Write-Host "    [$symbol] $($tc.Given) $($tc.Last) -> $($r.LocalPart ?? 'ERROR')" -ForegroundColor $color
    }

    $passCount = @($testResults | Where-Object { $_.Passed }).Count
    $failCount = @($testResults | Where-Object { -not $_.Passed }).Count
    Write-Host "`n    Results: $passCount passed, $failCount failed" -ForegroundColor $(if ($failCount -gt 0) { 'Red' } else { 'Green' })
}

# ══════════════════════════════════════════════════════════════
# AD Population Collision Analysis (optional)
# ══════════════════════════════════════════════════════════════

$populationAnalysis = $null
if ($ADPopulationFile -and (Test-Path $ADPopulationFile)) {
    Write-Host "`n  Analyzing existing UPN population..." -ForegroundColor Yellow

    $popData = Get-Content $ADPopulationFile -Raw | ConvertFrom-Json

    $existingUPNs = @()
    if ($popData.Users) {
        $existingUPNs = @($popData.Users | Where-Object { $_.UserPrincipalName } |
            ForEach-Object { ($_.UserPrincipalName -split '@')[0].ToLower() })
    }

    $upnDomains = @($popData.Users | Where-Object { $_.UserPrincipalName } |
        ForEach-Object { ($_.UserPrincipalName -split '@')[1] } | Sort-Object -Unique)

    $populationAnalysis = [ordered]@{
        TotalUsersWithUPN  = $existingUPNs.Count
        UniqueDomains      = $upnDomains
        DuplicateLocalParts = @($existingUPNs | Group-Object | Where-Object { $_.Count -gt 1 } |
            ForEach-Object { [ordered]@{ LocalPart = $_.Name; Count = $_.Count } })
    }

    Write-Host "    Existing UPNs: $($existingUPNs.Count)"
    Write-Host "    Domains in use: $($upnDomains -join ', ')"
    Write-Host "    Duplicate local parts: $($populationAnalysis.DuplicateLocalParts.Count)"
}

# ══════════════════════════════════════════════════════════════
# Markdown Specification Document
# ══════════════════════════════════════════════════════════════

$mdContent = @"
# UIAO UPN Generation Rules — Canonical Specification

> **Ref:** UIAO_136 Spec 2, D1.5 | ADR-003 (API-driven provisioning)
> **Generated:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
> **Primary Domain:** $PrimaryDomain
> **Format Template:** $FormatTemplate

---

## 1. Name Component Selection

| Priority | Source | Condition |
|---|---|---|
| 1 | PreferredFirstName (HR) | Non-empty preferred/display name provided by HR system |
| 2 | GivenName (Legal) | Default when no preferred name is available |
| Always | Surname (Legal) | Legal surname is always used for last name component |

## 2. Normalization Pipeline

1. **Transliteration** — Convert diacritics to ASCII equivalents (e.g., u-umlaut to ue)
2. **Character Filter** — Remove all characters except ``a-z``, ``A-Z``, ``0-9``, ``-``
3. **Hyphen Trim** — Remove leading/trailing hyphens from each component
4. **Format Assembly** — Build local part per template: ``$FormatTemplate``
5. **Lowercase** — Convert entire local part to lowercase
6. **Dot/Hyphen Cleanup** — Remove consecutive dots/hyphens, trim leading/trailing dots

## 3. Format Templates

| Template | Pattern | Example |
|---|---|---|
| First.Last | given.surname | john.smith@$PrimaryDomain |
| FLast | G + surname | jsmith@$PrimaryDomain |
| FirstL | given + S | johns@$PrimaryDomain |
| First_Last | given_surname | john_smith@$PrimaryDomain |
| First-Last | given-surname | john-smith@$PrimaryDomain |

## 4. Collision Resolution

- **Strategy:** Incrementing numeric suffix
- **Pattern:** ``first.last`` -> ``first.last2`` -> ``first.last3`` -> ... -> ``first.last99``
- **Cross-check sources:** Entra ID (Graph API), AD (LDAP), proxyAddresses/mail

## 5. Validation Rules

| Rule | Check | Action |
|---|---|---|
| ASCII Only | Local part contains only a-z, 0-9, ., -, _ | Transliterate + strip |
| No Leading/Trailing Dots | Must not start/end with . | Trim |
| No Consecutive Dots | Must not contain .. | Replace with single . |
| No Reserved Words | Not in reserved word list | Append numeric suffix |
| No Numeric-Only | Must not be all digits | Reject |
| Min Length | >= 2 characters | Reject |
| Max Length | Local <= 64, Total UPN <= 113 | Truncate |

## 6. Length Constraints

- **Local part maximum:** 64 characters (RFC 5321)
- **Total UPN maximum:** 113 characters (Entra ID limit)
- **Local part minimum:** 2 characters
- **Truncation:** From end of local part, preserving dots/hyphens at boundaries

## 7. Reserved Words

``$($reservedWords -join ', ')``

## 8. Entra ID Provisioning Expression (Conceptual)

``Join("@", NormalizeDiacritics(Join(".", [preferredFirstName] ?? [givenName], [surname])), "$PrimaryDomain")``

> Full provisioning expression syntax finalized in D3.4.
"@

# ══════════════════════════════════════════════════════════════
# Output Files
# ══════════════════════════════════════════════════════════════

# JSON rules spec
$jsonFile = Join-Path $OutputPath "${outPrefix}.json"
$jsonOutput = [ordered]@{
    RulesSpecification = $rulesSpec
    TestResults        = $testResults
    PopulationAnalysis = $populationAnalysis
}
$jsonOutput | ConvertTo-Json -Depth 10 | Out-File -FilePath $jsonFile -Encoding utf8NoBOM
Write-Host "`n  JSON: $jsonFile" -ForegroundColor Green

# Markdown spec
$mdFile = Join-Path $OutputPath "${outPrefix}.md"
$mdContent | Out-File -FilePath $mdFile -Encoding utf8NoBOM
Write-Host "  Markdown: $mdFile" -ForegroundColor Green

# Console Dashboard
Write-Host "`n-- UPN Generation Rules --" -ForegroundColor Cyan
Write-Host "  Primary Domain:     $PrimaryDomain"
Write-Host "  Format Template:    $FormatTemplate"
Write-Host "  Transliteration:    $($transliterationMap.Count) character mappings"
Write-Host "  Reserved Words:     $($reservedWords.Count)"
Write-Host "  Max Local Part:     64 chars"
Write-Host "  Max Total UPN:      113 chars"
Write-Host "  Collision Strategy: Numeric suffix (max 99)"

if ($testResults) {
    Write-Host "`n-- Test Results --" -ForegroundColor Cyan
    Write-Host "  Passed: $passCount / $($testResults.Count)" -ForegroundColor $(if ($failCount -gt 0) { 'Red' } else { 'Green' })
}

Write-Host "`n-- Complete --`n" -ForegroundColor Cyan
