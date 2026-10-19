#!/usr/bin/env bash
# pares_batch.sh — bulk-download images from PARES (Portal de Archivos Españoles)
#
# PARES is not IIIF: each image is served whole (max ~1100x1500 JPEG) by
# ViewImage.do, and the server only returns it to a client holding a session
# cookie from the catalogue page. This script gets that cookie, then walks a
# urls_*.txt file ("# [NNNN] label" line, then URL) and saves each image.
#
# Usage:
#   ./pares_batch.sh urls_ACA_Reg3298.txt [OUTDIR] [PREFIX] [FIRST] [LAST]
#
#   OUTDIR  default: ./ACA_Reg3298
#   PREFIX  default: ACA_Reg3298   -> ACA_Reg3298_0014_1r.jpg
#   FIRST/LAST  image-number range to fetch (default 1..827). Images
#           415-827 look like a duplicate pass of 2-414, so "1 414" is
#           probably all you need.
#
# Example (first pass only):
#   ./pares_batch.sh urls_ACA_Reg3298.txt ACA_Reg3298 ACA_Reg3298 1 414

set -u

URLFILE="${1:?usage: $0 urls_file [outdir] [prefix] [first] [last]}"
OUTDIR="${2:-ACA_Reg3298}"
PREFIX="${3:-ACA_Reg3298}"
FIRST="${4:-1}"
LAST="${5:-827}"

SHOW_URL="https://pares.cultura.gob.es/ParesBusquedas20/catalogo/show/13114935"
UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0 Safari/537.36"
SLEEP=1
COOKIES="$OUTDIR/.pares_cookies.txt"
LOG="$OUTDIR/download_log.txt"

mkdir -p "$OUTDIR"

new_session() {
  rm -f "$COOKIES"
  curl -sS -L -A "$UA" -c "$COOKIES" -b "$COOKIES" -o /dev/null "$SHOW_URL"
}

# Turn a PARES label into a filename-safe slug:
#   "Carátula" -> "Caratula", "Hoja de cortesí" -> "Hoja_de_cortesia",
#   "3bis r" -> "3bis_r", "Ar en blanco" -> "Ar_en_blanco"
slugify() {
  local s="$1"
  s="${s//Hoja de cortesí/Hoja de cortesia}"   # PARES truncates this label
  s="${s//á/a}"; s="${s//é/e}"; s="${s//í/i}"; s="${s//ó/o}"; s="${s//ú/u}"
  s="${s//Á/A}"; s="${s//É/E}"; s="${s//Í/I}"; s="${s//Ó/O}"; s="${s//Ú/U}"
  s="${s//ñ/n}"; s="${s//Ñ/N}"
  s="${s// /_}"
  s="$(printf '%s' "$s" | tr -cd 'A-Za-z0-9_.-')"
  printf '%s' "$s"
}

is_jpeg() {  # non-trivial size and starts with FF D8
  [ -s "$1" ] || return 1
  [ "$(wc -c < "$1")" -gt 5000 ] || return 1
  [ "$(od -An -tx1 -N2 "$1" | tr -d ' \n')" = "ffd8" ]
}

fetch() {  # url dest -> 0 on success
  local url="$1" dest="$2" tmp="$2.part"
  curl -sS -L -A "$UA" -b "$COOKIES" -c "$COOKIES" \
       -e "$SHOW_URL" --retry 3 --retry-delay 5 \
       -o "$tmp" "$url" || { rm -f "$tmp"; return 1; }
  if is_jpeg "$tmp"; then mv -f "$tmp" "$dest"; return 0; fi
  rm -f "$tmp"; return 1
}

echo "Starting session..."
new_session

ok=0; skip=0; fail=0; label=""; num=""
while IFS= read -r line <&3; do
  line="${line%$'\r'}"
  if [[ "$line" =~ ^#\ \[([0-9]+)\]\ (.*)$ ]]; then
    num="${BASH_REMATCH[1]}"; label="${BASH_REMATCH[2]}"; continue
  fi
  [[ "$line" == http* ]] || continue
  [ -n "$num" ] || continue
  n=$((10#$num))
  if [ "$n" -lt "$FIRST" ] || [ "$n" -gt "$LAST" ]; then num=""; continue; fi

  dest="$OUTDIR/${PREFIX}_${num}_$(slugify "$label").jpg"
  if [ -s "$dest" ]; then skip=$((skip+1)); num=""; continue; fi

  if fetch "$line" "$dest"; then
    ok=$((ok+1)); echo "[$num] OK    $(basename "$dest")"
  else
    # Session may have expired: renew once and retry
    echo "[$num] retrying with a new session..."
    new_session; sleep 3
    if fetch "$line" "$dest"; then
      ok=$((ok+1)); echo "[$num] OK    $(basename "$dest")"
    else
      fail=$((fail+1)); echo "[$num] FAIL  $label" | tee -a "$LOG"
    fi
  fi
  num=""
  sleep "$SLEEP"
done 3< "$URLFILE"

echo
echo "Done. Downloaded: $ok   Skipped (already present): $skip   Failed: $fail"
[ "$fail" -gt 0 ] && echo "Failures listed in $LOG — rerun the same command to retry them."
