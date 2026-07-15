#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# dezoomify_batch.sh
# Batch-download images from IIIF info.json endpoints using dezoomify-rs.
#
# Usage:
#   bash dezoomify_batch.sh [urls_file] [output_dir]
#
# urls_file defaults to urls.txt in the same folder as this script.
# output_dir defaults to ./dezoomify_output/
# Place dezoomify-rs.exe in the same folder as this script.
#
# urls.txt format: one info.json URL per line; lines starting with # are ignored.
# ---------------------------------------------------------------------------

set -euo pipefail

# Locate the binary — try bare name first, then .exe in the script's directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if command -v dezoomify-rs &>/dev/null; then
  DEZOOM="dezoomify-rs"
elif [ -f "$SCRIPT_DIR/dezoomify-rs.exe" ]; then
  DEZOOM="$SCRIPT_DIR/dezoomify-rs.exe"
elif [ -f "$SCRIPT_DIR/dezoomify-rs" ]; then
  DEZOOM="$SCRIPT_DIR/dezoomify-rs"
else
  echo "ERROR: dezoomify-rs not found. Place dezoomify-rs.exe in the same folder as this script." >&2
  echo "Download it from https://github.com/lovasoa/dezoomify-rs/releases" >&2
  exit 1
fi

URLS_FILE="${1:-$SCRIPT_DIR/urls.txt}"
OUTPUT_DIR="${2:-dezoomify_output}"

if [ ! -f "$URLS_FILE" ]; then
  echo "ERROR: URLs file not found: $URLS_FILE" >&2
  exit 1
fi

mkdir -p "$OUTPUT_DIR"

# Parse urls.txt into parallel arrays: URLS and LABELS.
# Expected format: optional "# <label>" comment line immediately before each URL.
# Lines that are blank or comments without a following URL are ignored.
URLS=()
LABELS=()
pending_label=""

while IFS= read -r line || [ -n "$line" ]; do
  # Strip leading/trailing whitespace
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" ]] && continue

  if [[ "$line" == \#* ]]; then
    # Store as pending label (strip leading "# ")
    pending_label="${line#\# }"
  else
    # It's a URL
    URLS+=("$line")
    LABELS+=("$pending_label")
    pending_label=""
  fi
done < "$URLS_FILE"

TOTAL=${#URLS[@]}

if [ "$TOTAL" -eq 0 ]; then
  echo "ERROR: No URLs found in $URLS_FILE" >&2
  exit 1
fi

echo "Loaded $TOTAL URL(s) from $URLS_FILE"
echo

SUCCESS=0
FAIL=0

for i in "${!URLS[@]}"; do
  URL="${URLS[$i]}"
  LABEL="${LABELS[$i]}"

  # UUID from URL
  UUID=$(echo "$URL" | grep -oE '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')

  # Folio suffix: extract the part after the last _ and before .tif
  # e.g. "BSG_1233_Masseria di Caffa_027r.tif" -> "027r"
  if [[ "$LABEL" =~ _([^_]+)\.tif$ ]]; then
    FOLIO="_fol_${BASH_REMATCH[1]}"
  else
    FOLIO=""
  fi

  OUTFILE="$OUTPUT_DIR/${UUID}${FOLIO}.jpg"

  echo "[$((i+1))/$TOTAL] $LABEL"
  echo "  -> $OUTFILE"

  if [ -f "$OUTFILE" ]; then
    echo "  Skipping (already exists)"
    ((SUCCESS++)) || true
    echo
    continue
  fi

  if "$DEZOOM" --largest "$URL" "$OUTFILE"; then
    echo "  Done"
    ((SUCCESS++)) || true
  else
    echo "  FAILED (exit $?)" >&2
    ((FAIL++)) || true
  fi

  sleep 1
  echo
done

echo "------------------------------"
echo "Finished: $SUCCESS succeeded, $FAIL failed"
echo "Output directory: $OUTPUT_DIR"
