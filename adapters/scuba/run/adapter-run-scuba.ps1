param(
    [Parameter(Mandatory = $true)]
        [string] $OutputDirectory
        )

        # Ensure output directories exist
        $rawDir        = Join-Path $OutputDirectory "raw"
        $normalizedDir = Join-Path $OutputDirectory "normalized"
        $reportsDir    = Join-Path $OutputDirectory "reports"

        New-Item -ItemType Directory -Force -Path $rawDir        | Out-Null
        New-Item -ItemType Directory -Force -Path $normalizedDir | Out-Null
        New-Item -ItemType Directory -Force -Path $reportsDir    | Out-Null

        # 1. Run SCuBA / ScubaGear (placeholder - replace with actual command)
        $rawFile = Join-Path $rawDir "ScubaResults.json"
        Write-Host "Running SCuBA assessment..."
        # Example:
        # pwsh -File .\ScubaGear.ps1 -OutputPath $rawFile

        # 2. Normalize SCuBA output
        $normalizedFile = Join-Path $normalizedDir "ScubaResults.normalized.json"
        Write-Host "Normalizing SCuBA output..."
        pwsh ./uiao-core/adapters/scuba/transforms/normalize.ps1 `
             -InputPath $rawFile `
                  -OutputPath $normalizedFile

                  # 3. Evaluate KSI rules
                  $reportFile = Join-Path $reportsDir "ScubaResults.report.json"
                  Write-Host "Evaluating KSI rules..."
                  pwsh ./uiao-core/ksi/evaluations/evaluate-ksi.ps1 `
                       -InputPath $normalizedFile `
                            -OutputPath $reportFile

                            Write-Host "adapter-run-scuba completed."
                            Write-Host "Raw:        $rawFile"
                            Write-Host "Normalized: $normalizedFile"
                            Write-Host "Report:     $reportFile"
