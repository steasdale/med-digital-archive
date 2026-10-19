#!/usr/bin/env bash
# digitarq_download.sh — bulk-download full-resolution scans from digitarq.arquivos.pt (ANTT)
#
# Digitarq is NOT IIIF: each scan is served whole as a JPEG from
#   /rdigital/dissemination?fileId=<id>
# (the server mislabels it as image/tiff, but the bytes are JPEG).
# The file list comes from the public JSON API:
#   /api/rdigital/<docId>?max=<n>
# No login or session cookie is needed.
#
# Usage:
#   ./digitarq_download.sh <docId or fileViewer URL> [output_dir]
# Example:
#   ./digitarq_download.sh 0908545459cc44a39014db3093930173
#   -> ./PT-TT-CHR-I-0003/PT-TT-CHR-I-0003_m0001.jpg ... _m0184.jpg

set -euo pipefail

BASE="https://digitarq.arquivos.pt"
ARG="${1:?Usage: $0 <docId or fileViewer URL> [output_dir]}"

# Accept a bare docId or a full fileViewer/documentDetails URL
DOC_ID=$(echo "$ARG" | grep -oE '[0-9a-f]{32}' | head -n1)
[[ -n "$DOC_ID" ]] || { echo "Could not find a 32-char docId in: $ARG" >&2; exit 1; }

echo "Fetching file list for $DOC_ID ..."
LIST=$(curl -sS --fail --retry 3 "$BASE/api/rdigital/$DOC_ID?max=5000" | python3 -c '
import sys, json
d = json.load(sys.stdin)
res = [r for r in d["results"] if r.get("type") == "IMAGE"]
print("API reports total:", d.get("total", len(res)), file=sys.stderr)
for r in res:
    print(r["id"] + "\t" + r["name"])
')

COUNT=$(printf '%s\n' "$LIST" | grep -c . || true)
echo "Images in list: $COUNT"
[[ "$COUNT" -gt 0 ]] || { echo "No images found." >&2; exit 1; }

# Default output folder = register code taken from the first filename (e.g. PT-TT-CHR-I-0003)
FIRST=$(printf '%s\n' "$LIST" | head -n1 | cut -f2)
OUT="${2:-${FIRST%_m*}}"
mkdir -p "$OUT"
printf '%s\n' "$LIST" > "$OUT/_filelist.tsv"
echo "Saving to: $OUT"

ok=0; skip=0; fail=0; i=0
while IFS=$'\t' read -r FID NAME <&3; do
  i=$((i+1))
  DEST="$OUT/$NAME"
  if [[ -s "$DEST" ]]; then
    skip=$((skip+1)); continue
  fi
  printf '[%d/%d] %s ... ' "$i" "$COUNT" "$NAME"
  if curl -sS --fail --retry 5 --retry-delay 3 \
          -o "$DEST.part" "$BASE/rdigital/dissemination?fileId=$FID"; then
    # sanity check: JPEG magic bytes FF D8
    if [[ "$(head -c2 "$DEST.part" | od -An -tx1 | tr -d ' \n')" == "ffd8" ]]; then
      mv "$DEST.part" "$DEST"; ok=$((ok+1)); echo "ok"
    else
      mv "$DEST.part" "$DEST.bad"; fail=$((fail+1)); echo "NOT A JPEG (saved as .bad)"
    fi
  else
    rm -f "$DEST.part"; fail=$((fail+1)); echo "FAILED"
  fi
  sleep 1
done 3< "$OUT/_filelist.tsv"

echo
echo "Done. downloaded=$ok skipped(existing)=$skip failed=$fail  (expected $COUNT)"
[[ $fail -eq 0 ]] || echo "Re-run the same command to retry the failures."
