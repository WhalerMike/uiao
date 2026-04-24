Write-Host "[core] Cleaning stray submodules..."

$submodules = git submodule status 2>&1

if ($submodules -match "fatal" -or $submodules.Trim() -eq "") {
    Write-Host "[core] No submodules detected."
    exit 0
}

$paths = $submodules -split "`n" | ForEach-Object {
    ($_ -split " ")[1]
}

foreach ($path in $paths) {
    if ($path -and $path.Trim() -ne "") {
        Write-Host "[core] Removing submodule: $path"
        git rm -f $path
        Remove-Item -Recurse -Force $path -ErrorAction SilentlyContinue
    }
}

git add .
git commit -m "core: auto-clean stray submodules"

Write-Host "[core] Submodule cleanup complete."
