# Merge Articles into Book - Run locally with Word installed
$word = New-Object -ComObject Word.Application
$word.Visible = $true

# Path to your OneDrive synced folder - adjust if different
$base = "$env:USERPROFILE\OneDrive\Documents"
$articleFolder = "$base\Application_Aware_Networking_White_Paper_by_Mike\Article Series"

# Open the book document (saved to root Documents by Word Online)
$bookPath = Get-ChildItem "$base\Book of Articles*" | Select-Object -First 1
$bookDoc = $word.Documents.Open($bookPath.FullName)

# Move to end of document
$range = $bookDoc.Content
$range.Collapse(0)  # Collapse to end

# Insert each article with a page break before it
$articles = Get-ChildItem "$articleFolder\Article*.docx" | Sort-Object Name
foreach ($article in $articles) {
    Write-Host "Inserting: $($article.Name)"
    $range.InsertBreak(7)  # Page break
    $range = $bookDoc.Content
    $range.Collapse(0)
    $range.InsertFile($article.FullName)
    $range = $bookDoc.Content
    $range.Collapse(0)
}

# Save to Article Series folder
$outputPath = "$articleFolder\Book of Articles - Application Aware Networking.docx"
$bookDoc.SaveAs2($outputPath)
Write-Host "Book saved to: $outputPath"

# Optional: Update Table of Contents if you add a proper auto-TOC later
# $bookDoc.TablesOfContents | ForEach-Object { $_.Update() }

# Cleanup
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
