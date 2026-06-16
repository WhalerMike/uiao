Write-Host "Scanning for stray submodules..."

# Get submodule list (if any)
$status = git submodule status 2>$null

if ($LASTEXITCODE -ne 0 -or $null -eq $status -or $status.Trim() -eq "") {
    Write-Host "No submodules detected."
    exit 0
}

$submodules = $status -split "`n" | ForEach-Object {
    ($_ -split " ")[1]
}

foreach ($sub in $submodules) {
    Write-Host "Removing submodule: $sub"
    git rm -f $sub
    Remove-Item -Recurse -Force $sub -ErrorAction SilentlyContinue
}

git add .
git commit -m "Auto-clean stray submodules"
Write-Host "Submodule cleanup complete."
