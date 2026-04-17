<#
.SYNOPSIS
    Crawl the rendered UIAO Modernization Atlas site and report broken links.

.DESCRIPTION
    Starts at a root URL, follows every same-site HTML link up to MaxDepth,
    and HEAD-checks every link it finds (same-site or external). Reports any
    non-200 status codes.

    Complements the lychee workflow in .github/workflows/link-check.yml:
      - lychee scans the source Markdown / Quarto Markdown for link patterns
      - this script validates the rendered link graph on the live site
        (after Quarto rewrites .qmd → .html, after Pages URL-mangling)

    Run before shipping a PR that changes internal link structure.

.PARAMETER StartUrl
    The root URL to crawl. Defaults to the live UIAO docs site.

.PARAMETER MaxDepth
    Maximum crawl depth from the start URL. Defaults to 5.

.EXAMPLE
    pwsh scripts/check-links.ps1
    pwsh scripts/check-links.ps1 -StartUrl https://whalermike.github.io/uiao/ -MaxDepth 3
#>

param(
    [string]$StartUrl = "https://whalermike.github.io/uiao/docs/",
    [int]$MaxDepth = 5
)

Add-Type -AssemblyName System.Web

$UserAgent = "UIAO-LinkCheck/1.0 (+https://github.com/WhalerMike/uiao)"

$visitedPages = [System.Collections.Concurrent.ConcurrentDictionary[string, bool]]::new()
$checkedLinks = [System.Collections.Concurrent.ConcurrentDictionary[string, bool]]::new()
$results = [System.Collections.Concurrent.ConcurrentBag[psobject]]::new()

function Get-NormalizedUrl {
    param(
        [string]$BaseUrl,
        [string]$Href
    )

    if ([string]::IsNullOrWhiteSpace($Href)) { return $null }

    # Ignore anchors, mailto, javascript
    if ($Href.StartsWith("#") -or $Href.StartsWith("mailto:") -or $Href.StartsWith("javascript:")) {
        return $null
    }

    try {
        $uri = [Uri]::new($Href, [UriKind]::RelativeOrAbsolute)
        if (-not $uri.IsAbsoluteUri) {
            $base = [Uri]::new($BaseUrl)
            $uri = [Uri]::new($base, $Href)
        }
        return $uri.AbsoluteUri
    } catch {
        return $null
    }
}

function Test-Link {
    param(
        [string]$Url,
        [string]$SourcePage
    )

    if ($checkedLinks.ContainsKey($Url)) { return }

    $null = $checkedLinks.TryAdd($Url, $true)

    $statusCode = 0
    $note = ""

    # Try HEAD first. Some servers return 405 or 403 on HEAD even when GET works,
    # so fall back to GET (discarding the body) before calling it broken.
    try {
        $response = Invoke-WebRequest -Uri $Url -Method Head -UseBasicParsing `
            -UserAgent $UserAgent -TimeoutSec 15 -MaximumRedirection 5 -ErrorAction Stop
        $statusCode = [int]$response.StatusCode
    } catch {
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $statusCode = [int]$_.Exception.Response.StatusCode
        } else {
            $statusCode = 0
        }
    }

    if ($statusCode -in 0, 403, 405, 501) {
        # Retry with GET — some origins only honor GET.
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -UseBasicParsing `
                -UserAgent $UserAgent -TimeoutSec 30 -MaximumRedirection 5 -ErrorAction Stop
            $statusCode = [int]$response.StatusCode
            $note = "HEAD→GET fallback"
        } catch {
            if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
                $statusCode = [int]$_.Exception.Response.StatusCode
            }
            # leave statusCode as-is on total failure
            $note = "HEAD→GET failed"
        }
    }

    $results.Add([pscustomobject]@{
        Url        = $Url
        StatusCode = $statusCode
        SourcePage = $SourcePage
        Note       = $note
    })
}

function Invoke-PageCrawl {
    param(
        [string]$Url,
        [int]$Depth
    )

    if ($Depth -gt $MaxDepth) { return }
    if ($visitedPages.ContainsKey($Url)) { return }

    $null = $visitedPages.TryAdd($Url, $true)

    Write-Host "Crawling [$Depth]: $Url"

    try {
        $response = Invoke-WebRequest -Uri $Url -UseBasicParsing `
            -UserAgent $UserAgent -TimeoutSec 20 -MaximumRedirection 5 -ErrorAction Stop
    } catch {
        $results.Add([pscustomobject]@{
            Url        = $Url
            StatusCode = 0
            SourcePage = $Url
            Note       = "page fetch failed"
        })
        return
    }

    $links = @()
    if ($response.Links) {
        $links = $response.Links | ForEach-Object { $_.href } | Where-Object { $_ }
    }

    foreach ($href in $links) {
        $normalized = Get-NormalizedUrl -BaseUrl $Url -Href $href
        if (-not $normalized) { continue }

        # Always test the link
        Test-Link -Url $normalized -SourcePage $Url

        # Only recurse into same-site HTML pages under the start path
        $siteRoot = ([Uri]$StartUrl).GetLeftPart([System.UriPartial]::Path)
        if ($normalized.StartsWith($siteRoot) -and
            ($normalized.EndsWith(".html") -or $normalized -match "/$")) {

            Invoke-PageCrawl -Url $normalized -Depth ($Depth + 1)
        }
    }
}

Invoke-PageCrawl -Url $StartUrl -Depth 0

$results |
    Sort-Object StatusCode, Url |
    Tee-Object -Variable all |
    Format-Table -AutoSize

$broken = $all | Where-Object { $_.StatusCode -ne 200 }
if ($broken) {
    "`nBroken or suspicious links:" | Write-Host -ForegroundColor Yellow
    $broken | Format-Table -AutoSize
    exit 1
} else {
    "`nNo broken links detected." | Write-Host -ForegroundColor Green
    exit 0
}
