param([string]$RepoRoot = "C:\Users\whale\git\uiao")

$InboxPath = Join-Path $RepoRoot "inbox"
Add-Type -AssemblyName System.IO.Compression.FileSystem

$ZipFiles = Get-ChildItem -Path $InboxPath -Filter "*.zip" | Sort-Object Name
Write-Host "Found $($ZipFiles.Count) ZIP files in inbox/" -ForegroundColor Cyan

$Report = @()

foreach ($Zip in $ZipFiles) {
    Write-Host "`nZIP: $($Zip.Name)" -ForegroundColor Yellow
    $Archive = [System.IO.Compression.ZipFile]::OpenRead($Zip.FullName)
    foreach ($Entry in $Archive.Entries | Sort-Object FullName) {
        if ($Entry.Name -eq "") { continue }
        $SizeKB = [math]::Round($Entry.Length/1KB, 1)
        Write-Host "  $($Entry.FullName)  ($SizeKB KB)"
        $Report += [PSCustomObject]@{
            Zip      = $Zip.Name
            FilePath = $Entry.FullName
            FileName = $Entry.Name
            SizeKB   = $SizeKB
        }
    }
    $Archive.Dispose()
}

Write-Host "`n-- BEGIN INVENTORY OUTPUT --"
Write-Host "Total ZIPs : $($ZipFiles.Count)"
Write-Host "Total files: $($Report.Count)"
Write-Host ""
$Report | Format-Table Zip, FilePath, SizeKB -AutoSize
Write-Host "-- END INVENTORY OUTPUT --"
