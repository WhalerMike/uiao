#!/bin/bash

# UDC Professional Compiler
# Optimized for FedRAMP 20x Phase 2 Document Quality

INPUT_DIR="build/templates"
OUTPUT_DIR="docs/artifacts"
mkdir -p "$OUTPUT_DIR"

echo "Starting High-Quality Compilation..."

# Find all processed templates
find "$INPUT_DIR" -name "*.md" | while read -r template; do
    filename=$(basename "$template" .md)
    echo "Processing: $filename"

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
        -o "$OUTPUT_DIR/$filename.pdf"

    # Professional DOCX with embedded resources
    pandoc "$template" \
        --from markdown \
        --to docx \
        --embed-resources \
        -o "$OUTPUT_DIR/$filename.docx"

    # Clean HTML for the dashboard
    pandoc "$template" \
        --from markdown \
        --to html \
        --embed-resources \
        --standalone \
        --template=scripts/html_template.html \
        -o "$OUTPUT_DIR/$filename.html"
done

echo "All documents compiled. Check $OUTPUT_DIR for the new files."
