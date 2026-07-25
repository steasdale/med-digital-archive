#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# dezoomify_batch_notariorum.sh
# Batch-download images from notariorumitinera.eu using dezoomify-rs.
#
# Reads a tab-separated file:  URL<TAB>label
# (as produced by scrape_notariorum.py)
#
# Usage (WSL or Git Bash on Windows):
#   bash dezoomify_batch_notariorum.sh [urls_file] [output_dir]
#
# Defaults:
#   urls_file  = urls_notariorum_191131.txt  (same folder as this script)
#   output_dir = ./notariorum_output/
#
# Place dezoomify-rs.exe in the same folder as this script.
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Locate dezoomify-rs binary
if command -v dezoomify-rs &>/dev/null; then
  DEZOOM="dezoomify-rs"
elif [ -f "$SCRIPT_DIR/dezoomify-rs.exe" ]; then
  DEZOOM="$SCRIPT_DIR/dezoomify-rs.exe"
elif [ -f "$SCRIPT_DIR/dezoomify-rs" ]; then
  DEZOOM="$SCRIPT_DIR/dezoomify-rs"
else
  echo "ERROR: dezoomify-rs not found. Place dezoomify-rs.exe in the same folder as this script."
  exit 1
fi

# Path conversion: wslpath for WSL, cygpath for Git Bash, plain path otherwise
win_path() {
  if command -v wslpath &>/dev/null; then
    wslpath -w "$1"
  elif command -v cygpath &>/dev/null; then
    cygpath -w "$1"
  else
    echo "$1"
  fi
}

URLS_FILE="${1:-$SCRIPT_DIR/combined_408_section_prefixed.txt}"
OUTPUT_DIR="${2:-$SCRIPT_DIR/notariorum_output}"

if [ ! -f "$URLS_FILE" ]; then
  echo "ERROR: URL file not found: $URLS_FILE"
  exit 1
fi

mkdir -p "$OUTPUT_DIR"
echo "Output directory: $OUTPUT_DIR"
echo "Reading URLs from: $URLS_FILE"
echo ""

SUCCESS=0
FAIL=0
SKIP=0

# Read from file descriptor 3 so dezoomify-rs cannot consume stdin (fd 0)
while IFS=$'\t' read -r URL LABEL <&3 || [ -n "$URL" ]; do
  # Strip Windows carriage returns
  URL="${URL%$'\r'}"
  LABEL="${LABEL%$'\r'}"

  # Skip blank or comment lines
  [[ -z "$URL" || "$URL" == \#* ]] && continue

  OUT_FILE="$OUTPUT_DIR/${LABEL}.jpg"

  if [ -f "$OUT_FILE" ]; then
    echo "SKIP [$LABEL] already exists"
    SKIP=$((SKIP + 1))
    continue
  fi

  WIN_OUT_FILE="$(win_path "$OUT_FILE")"

  echo "Downloading [$LABEL]..."
  if "$DEZOOM" --largest "$URL" "$WIN_OUT_FILE"; then
    echo "  OK -> ${LABEL}.jpg"
    SUCCESS=$((SUCCESS + 1))
  else
    echo "  FAILED: $URL" >&2
    FAIL=$((FAIL + 1))
  fi

  sleep 1

done 3< "$URLS_FILE"

echo ""
echo "------------------------------"
echo "Finished: $SUCCESS downloaded, $SKIP skipped, $FAIL failed"
echo "Output: $OUTPUT_DIR"
