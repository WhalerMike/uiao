#!/bin/bash

# UDC Professional Compiler
# Optimized for FedRAMP 20x Phase 2 Document Quality

BUILD_DIR="build"
OUTPUT_DIR="docs/artifacts"
mkdir -p "$OUTPUT_DIR"

echo "Starting High-Quality Compilation..."

# Find all processed templates under build/ (covers build/templates/ and any
# tagged files outside src/templates/ that generate_diagrams.py mirrors under build/)
while read -r template; do
    # Derive relative path from build/ to preserve directory structure and avoid
    # filename collisions when files in different subdirectories share a basename
    relpath="${template#"$BUILD_DIR/"}"
    reldir="$(dirname "$relpath")"
    filename="$(basename "$relpath" .md)"
    outdir="$OUTPUT_DIR/$reldir"
    mkdir -p "$outdir"
    echo "Processing: $relpath"

    # PDF Generation with XeLaTeX for better typography and embedded resources
    pandoc "$template" \
        --from markdown+gfm_auto_identifiers \
        --to pdf \
        --pdf-engine=xelatex \
        --embed-resources \
        --standalone \
        --toc \
        --number-sections \
        -V colorlinks=true \
        -V linkcolor=blue \
        -V geometry:margin=1in \
        -V mainfont="Noto Sans" \
        -V fontsize=11pt \
        -o "$outdir/$filename.pdf"

    # Professional DOCX with embedded resources
    pandoc "$template" \
        --from markdown \
        --to docx \
        --embed-resources \
        -o "$outdir/$filename.docx"

    # Clean HTML for the dashboard
    pandoc "$template" \
        --from markdown \
        --to html \
        --embed-resources \
        --standalone \
        --template=scripts/html_template.html \
        -o "$outdir/$filename.html"
done < <(find "$BUILD_DIR" -name "*.md")

echo "All documents compiled. Check $OUTPUT_DIR for the new files."
