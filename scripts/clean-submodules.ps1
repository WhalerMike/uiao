Write-Host "Scanning for stray submodules..."

# Get submodule list (if any)
 = git submodule status 2>

if (0 -ne 0 -or  -eq  -or .Trim() -eq "") {
    Write-Host "No submodules detected."
    exit 0
}

 =  -split "
" | ForEach-Object {
    ( -split " ")[1]
}

foreach ( in ) {
    Write-Host "Removing submodule: "
    git rm -f 
    Remove-Item -Recurse -Force  -ErrorAction SilentlyContinue
}

git add .
git commit -m "Auto-clean stray submodules"
Write-Host "Submodule cleanup complete."
