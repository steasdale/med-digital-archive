#!/usr/bin/env bash
# -------------------------------------------------------------
# abm_download.sh
# Downloads 711 JPEG images from arquivo-abm.madeira.gov.pt
# Source list: rgdc1_urls.txt  (tab-separated: URL <TAB> filename)
# Output dir : abm_rgdc1/
# -------------------------------------------------------------

URLS_FILE="rgdc1_urls.txt"
OUT_DIR="abm_rgdc1"
SLEEP_SEC=1

mkdir -p "$OUT_DIR"

total=$(wc -l < "$URLS_FILE")
count=0
skipped=0
failed=0

while IFS=$'\t' read -r url filename; do
    count=$((count + 1))
    outfile="$OUT_DIR/$filename"

    if [[ -f "$outfile" ]]; then
        echo "[$count/$total] SKIP (exists): $filename"
        skipped=$((skipped + 1))
        continue
    fi

    echo "[$count/$total] Downloading: $filename"
    curl -L --silent --show-error \
         --retry 3 --retry-delay 5 \
         --output "$outfile" \
         "$url"

    if [[ $? -ne 0 ]]; then
        echo "  ERROR: failed to download $filename"
        failed=$((failed + 1))
        rm -f "$outfile"   # remove partial file
    fi

    sleep "$SLEEP_SEC"

done < "$URLS_FILE"

echo ""
echo "Done. Downloaded: $((count - skipped - failed))  Skipped: $skipped  Failed: $failed"
