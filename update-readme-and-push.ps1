# ================================================
# update-readme-and-push.ps1
# Simple version - no here-strings
# ================================================

Write-Host "=== UIAO-Core README Updater & Pusher ===" -ForegroundColor Cyan

Set-Location "C:\Users\whale\uiao-core"

# Backup
Copy-Item "README.md" "README.md.backup" -Force
Write-Host "✅ Backed up README.md" -ForegroundColor Green

# Write new README
$readmeContent = "# UIAO-Core`n`n"
$readmeContent += "**Unified Identity-Addressing-Overlay Architecture**  `n"
$readmeContent += "Modernizing federal systems with machine-readable Zero Trust and FedRAMP compliance automation.`n`n"
$readmeContent += "---`n`n"
$readmeContent += "## Modernization Atlas`n`n"
$readmeContent += "![Unified Zero Trust Architecture & Automation](assets/images/modernization-atlas-unified-zero-trust-architecture-and-automation.png)`n`n"
$readmeContent += "![Mission Success](assets/images/modernization-atlas-mission-success.png)`n`n"
$readmeContent += "### Core Identity Lifecycle`n"
$readmeContent += "![Joiner / Mover / Leaver - Identity Core](assets/images/uiao-joiner-mover-leaver-identity-core.png)`n`n"
$readmeContent += "### Legacy vs Modernized State`n"
$readmeContent += "![Legacy vs Modernized Comparison](assets/images/uiao-core-legacy-vs-modernized-comparison.png)`n`n"
$readmeContent += "---`n`n"
$readmeContent += "## Key Architecture Views`n`n"
$readmeContent += "![Unified Architecture Flow](assets/images/uiao-core-unified-architecture-flow.png)`n`n"
$readmeContent += "![Mission-to-Tech Mapping](assets/images/uiao-core-mission-to-tech-mapping.png)`n`n"
$readmeContent += "![Regional Scaling Model](assets/images/uiao-core-regional-scaling-model.png)`n`n"
$readmeContent += "![O-Pillar INR Fabric - US View](assets/images/uiao-o-pillar-inr-fabric-us-map.png)`n`n"
$readmeContent += "![Visibility & Telemetry](assets/images/modernization-atlas-visibility-and-telemetry-eyes-and-ears.png)`n`n"
$readmeContent += "![Actionable Intelligence Dashboard](assets/images/modernization-atlas-actionable-intelligence-dashboard.png)`n`n"
$readmeContent += "---`n`n"
$readmeContent += "## Features`n`n"
$readmeContent += "- Single source of truth YAML canon → OSCAL artifacts`n"
$readmeContent += "- Vendor-neutral abstraction layer`n"
$readmeContent += "- Automated SSP, POA&M and leadership briefings`n"
$readmeContent += "- FedRAMP Rev 5 ready`n`n"
$readmeContent += "## Quick Start`n`n"
$readmeContent += "```powershell`n"
$readmeContent += "git clone https://github.com/WhalerMike/uiao-core.git`n"
$readmeContent += "cd uiao-core`n"
$readmeContent += "````n`n"
$readmeContent += "Made for federal Zero Trust and compliance modernization"

Set-Content -Path "README.md" -Value $readmeContent -Encoding UTF8
Write-Host "✅ Updated README.md with new images" -ForegroundColor Green

# Git
git add README.md
git commit -m "docs(readme): update README with 15 new Modernization Atlas diagrams"
git push

Write-Host "`n🎉 Done! Check https://github.com/WhalerMike/uiao-core" -ForegroundColor Green