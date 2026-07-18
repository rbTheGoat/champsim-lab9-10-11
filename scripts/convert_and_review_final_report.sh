#!/usr/bin/env bash

set -euo pipefail

INPUT_MD="reports/final_assignment_report.md"
OUTPUT_DIR="submission"
DOCX_OUTPUT="$OUTPUT_DIR/computer_architecture_labs_9_10_11_report.docx"
PDF_OUTPUT="$OUTPUT_DIR/computer_architecture_labs_9_10_11_report.pdf"
REVIEW_DIR="$OUTPUT_DIR/review_pages"
CHECK_REPORT="$OUTPUT_DIR/final_conversion_check.txt"

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

require_command() {
    local command_name="$1"

    command -v "$command_name" >/dev/null 2>&1 \
        || fail "Missing command '$command_name'. Install the required packages first."
}

echo "============================================================"
echo "FINAL REPORT CONVERSION"
echo "============================================================"

require_command python3
require_command pandoc
require_command libreoffice
require_command pdftoppm
require_command pdfinfo
require_command unzip

[[ -f "$INPUT_MD" ]] \
    || fail "Missing $INPUT_MD"

if grep -q '\[ENTER NAME\]\|\[ENTER ID\]' "$INPUT_MD"; then
    fail "Replace [ENTER NAME] and [ENTER ID] in $INPUT_MD before conversion."
fi

mkdir -p "$OUTPUT_DIR"
rm -rf "$REVIEW_DIR"
mkdir -p "$REVIEW_DIR"

# Validate all local Markdown image references before conversion.
python3 - "$INPUT_MD" <<'PY'
from pathlib import Path
import re
import sys

markdown_path = Path(sys.argv[1]).resolve()
text = markdown_path.read_text(encoding="utf-8", errors="replace")

references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
missing = []

for raw_reference in references:
    reference = raw_reference.strip().split()[0].strip("<>")

    if (
        reference.startswith("http://")
        or reference.startswith("https://")
        or reference.startswith("data:")
    ):
        continue

    image_path = (markdown_path.parent / reference).resolve()

    if not image_path.is_file():
        missing.append((reference, image_path))

print(f"Markdown image references: {len(references)}")

if missing:
    print("Missing image files:", file=sys.stderr)
    for reference, image_path in missing:
        print(f"  {reference} -> {image_path}", file=sys.stderr)
    raise SystemExit(1)

print("All local Markdown images exist.")
PY

rm -f "$DOCX_OUTPUT" "$PDF_OUTPUT"

echo
echo "Creating DOCX..."

pandoc "$INPUT_MD" \
    --from=gfm \
    --to=docx \
    --standalone \
    --toc \
    --toc-depth=3 \
    --number-sections \
    --resource-path="reports:.:results" \
    --output="$DOCX_OUTPUT"

[[ -s "$DOCX_OUTPUT" ]] \
    || fail "DOCX generation failed: $DOCX_OUTPUT is missing or empty."

echo "Creating PDF through LibreOffice..."

LO_PROFILE=$(mktemp -d)
trap 'rm -rf "$LO_PROFILE"' EXIT

libreoffice \
    -env:UserInstallation="file://$LO_PROFILE" \
    --headless \
    --convert-to pdf \
    --outdir "$OUTPUT_DIR" \
    "$DOCX_OUTPUT" \
    >/tmp/champsim_report_libreoffice.log 2>&1

[[ -s "$PDF_OUTPUT" ]] \
    || {
        cat /tmp/champsim_report_libreoffice.log >&2 || true
        fail "PDF conversion failed: $PDF_OUTPUT is missing or empty."
    }

echo "Rendering every PDF page for visual review..."

pdftoppm \
    -png \
    -r 150 \
    "$PDF_OUTPUT" \
    "$REVIEW_DIR/page" \
    >/dev/null

page_png_count=$(
    find "$REVIEW_DIR" \
        -maxdepth 1 \
        -type f \
        -name "page-*.png" \
        | wc -l
)

pdf_page_count=$(
    pdfinfo "$PDF_OUTPUT" \
        | awk -F: '/^Pages:/ { gsub(/[[:space:]]/, "", $2); print $2 }'
)

[[ -n "$pdf_page_count" ]] \
    || fail "Could not determine PDF page count."

[[ "$page_png_count" == "$pdf_page_count" ]] \
    || fail \
        "Rendered page count ($page_png_count) does not match PDF page count ($pdf_page_count)."

embedded_image_count=$(
    unzip -l "$DOCX_OUTPUT" \
        | awk '/word\/media\// { count++ } END { print count + 0 }'
)

docx_size=$(
    stat -c '%s' "$DOCX_OUTPUT"
)

pdf_size=$(
    stat -c '%s' "$PDF_OUTPUT"
)

{
    echo "FINAL REPORT CONVERSION CHECK"
    echo "Generated: $(date -Is)"
    echo
    echo "Input Markdown: $INPUT_MD"
    echo "DOCX: $DOCX_OUTPUT"
    echo "PDF: $PDF_OUTPUT"
    echo
    echo "DOCX size bytes: $docx_size"
    echo "PDF size bytes: $pdf_size"
    echo "Embedded DOCX images: $embedded_image_count"
    echo "PDF pages: $pdf_page_count"
    echo "Rendered review PNGs: $page_png_count"
    echo
    echo "Automated conversion checks: PASS"
    echo
    echo "Manual review still required:"
    echo "1. Inspect every PNG under $REVIEW_DIR."
    echo "2. Check the title page and student details."
    echo "3. Check the table of contents."
    echo "4. Check that tables do not overflow or split badly."
    echo "5. Check every graph and caption."
    echo "6. Check page breaks around major sections."
    echo "7. Open the final PDF once in a normal PDF viewer."
} | tee "$CHECK_REPORT"

echo
echo "============================================================"
echo "CONVERSION COMPLETE"
echo "DOCX: $DOCX_OUTPUT"
echo "PDF:  $PDF_OUTPUT"
echo "Review pages: $REVIEW_DIR"
echo "Check report: $CHECK_REPORT"
echo "============================================================"
