#!/usr/bin/env bash
# Make print, archive and preview versions of a PDF with Ghostscript.
#   scripts/variants.sh cv.pdf  ->  cv_print.pdf, cv_archive.pdf, cv_preview.png
set -euo pipefail

pdf=${1:?usage: variants.sh file.pdf}
base=${pdf%.pdf}
command -v gs >/dev/null || { echo "Ghostscript (gs) is needed for variants"; exit 1; }

# Greyscale, for printing
gs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 \
   -sColorConversionStrategy=Gray -dProcessColorModel=/DeviceGray \
   -sOutputFile="${base}_print.pdf" "$pdf"

# PDF/A-2b, for archiving
gs -q -dNOPAUSE -dBATCH -dSAFER -dPDFA=2 -dPDFACompatibilityPolicy=1 \
   -sColorConversionStrategy=RGB -sDEVICE=pdfwrite \
   -sOutputFile="${base}_archive.pdf" "$pdf"

# First page as a PNG, for link previews
gs -q -dNOPAUSE -dBATCH -dSAFER -sDEVICE=png16m -r150 -dFirstPage=1 -dLastPage=1 \
   -sOutputFile="${base}_preview.png" "$pdf"

echo "Made ${base}_print.pdf, ${base}_archive.pdf and ${base}_preview.png"
