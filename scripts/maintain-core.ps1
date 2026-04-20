Write-Host "=== UIAO Core Maintenance Orchestrator ==="

Write-Host "[1] Ensuring Git config..."
git config core.autocrlf false
git config core.eol lf

Write-Host "[2] Ensuring .gitignore contains .claude/..."
$gitignorePath = ".gitignore"
if (Test-Path $gitignorePath) {
    $content = Get-Content $gitignorePath
    if ($content -notcontains ".claude/") {
        Add-Content $gitignorePath "`n# Ignore Claude artifacts`n.claude/`n"
        git add .gitignore
        git commit -m "core: ensure .claude/ is ignored"
    }
}

Write-Host "[3] Removing Claude artifacts..."
Remove-Item -Recurse -Force .claude -ErrorAction SilentlyContinue

Write-Host "[4] Cleaning stray submodules..."
.\scripts\clean-submodules.ps1

Write-Host "[5] Ensuring .gitattributes exists..."
$gitattributes = ".gitattributes"
if (!(Test-Path $gitattributes)) {
    @"
* text=auto
*.md text eol=lf
*.yml text eol=lf
*.yaml text eol=lf
*.json text eol=lf
*.ps1 text eol=lf
*.py text eol=lf
"@ | Out-File $gitattributes -Encoding utf8

    git add .gitattributes
    git commit -m "core: add .gitattributes for line-ending normalization"
}

Write-Host "[6] Auto-committing core changes..."
git add src/ -A 2>$null
git add infra/ -A 2>$null
git add docs/ -A 2>$null
git add config/ -A 2>$null
git add data/ -A 2>$null
git add *.md
git add *.ps1
git add *.py

if (!(git diff --cached --quiet)) {
    git commit -m "core: auto-commit maintenance updates"
    git push
}

Write-Host "=== Core Maintenance Complete ==="
