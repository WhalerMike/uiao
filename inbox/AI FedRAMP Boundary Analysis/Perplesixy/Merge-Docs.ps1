# Merge-Docs.ps1 — place in the folder with your .docx files and run

$targetName = "AI FedRAMP Bounary Analysis Perplexity.docx"
$targetFile = Join-Path $PSScriptRoot $targetName

if (-not (Test-Path $targetFile)) {
    Write-Host "Target file not found: $targetName" -ForegroundColor Red
    exit
}

$sourceFiles = Get-ChildItem -Path $PSScriptRoot -Filter "*.docx" |
    Where-Object { $_.Name -ne $targetName } |
    Sort-Object CreationTime

Write-Host "Files will be appended in this order:" -ForegroundColor Cyan
$sourceFiles | ForEach-Object { Write-Host "  $($_.CreationTime) - $($_.Name)" }
Write-Host "`nTarget: $targetName" -ForegroundColor Yellow
Read-Host "`nPress Enter to proceed or Ctrl+C to cancel"

$word = New-Object -ComObject Word.Application
$word.Visible = $false

try {
    $targetDoc = $word.Documents.Open($targetFile)
    $range = $targetDoc.Content
    $range.Collapse(0)

    foreach ($file in $sourceFiles) {
        Write-Host "Appending: $($file.Name)" -ForegroundColor Green
        $range.InsertBreak(7)
        $range = $targetDoc.Content
        $range.Collapse(0)
        $range.InsertFile($file.FullName)
        $range = $targetDoc.Content
        $range.Collapse(0)
    }

    $targetDoc.Save()
    $targetDoc.Close()
    Write-Host "`nDone! All files merged into $targetName" -ForegroundColor Cyan
}
catch {
    Write-Host "Error: $_" -ForegroundColor Red
}
finally {
    $word.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
