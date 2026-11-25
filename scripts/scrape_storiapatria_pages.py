#!/usr/bin/env python3
"""
Download all page images of a storiapatriagenova.it record (BD_vs_OA.aspx) by using
the page's own "Vai a pagina" (go to page) button, so no METS file is needed.

For each page it asks the server for page N, reads the image filename from the viewer
iframe, then downloads the JPEG. Rerun the same command to resume after interruption.

Usage:
  python scrape_storiapatria_pages.py "<record page URL>" <PREFIX> [--out DIR] [--list-only] [--sleep 1]

Example (Ricci 77, 1028 images):
  python scrape_storiapatria_pages.py "https://www.storiapatriagenova.it/BD_vs_OA.aspx?Id_Oggetto_Archivistico=38&Id_Progetto=2" Ricci77
"""
from concurrent.futures import ThreadPoolExecutor
import argparse, html, http.cookiejar, json, os, re, sys, time, urllib.parse, urllib.request

P = "ctl00$PlaceHolderMain$TemplateElemArch$"
SITE = "https://www.storiapatriagenova.it"

# No cookie jar on purpose: ASP.NET handles requests from one session one at a time,
# and these pages work without a session, so parallel lookups stay parallel.
opener = urllib.request.build_opener()
opener.addheaders = [("User-Agent", "Mozilla/5.0 (research download)")]


def req(url, data=None, retries=4):
    for attempt in range(1, retries + 1):
        try:
            body = urllib.parse.urlencode(data).encode() if data is not None else None
            with opener.open(url, body, timeout=60) as r:
                return r.read()
        except Exception as e:
            if attempt == retries:
                raise
            print(f"   retry {attempt} ({e})", file=sys.stderr)
            time.sleep(5 * attempt)


def hidden_fields(page):
    fields = {}
    for m in re.finditer(r'<input[^>]+type="hidden"[^>]*>', page):
        tag = m.group(0)
        name = re.search(r'name="([^"]+)"', tag)
        val = re.search(r'value="([^"]*)"', tag)
        if name:
            fields[html.unescape(name.group(1))] = html.unescape(val.group(1)) if val else ""
    return fields


def image_path(page):
    m = re.search(r'iFrameRisorsa"[^>]*src="[^"]*FIF=([^"]+)"', page) or re.search(r'FIF=([^"&]+)', page)
    return html.unescape(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("prefix")
    ap.add_argument("--out", default=None)
    ap.add_argument("--list-only", action="store_true")
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--workers", type=int, default=4, help="parallel page lookups (default 4)")
    a = ap.parse_args()

    out = a.out or a.prefix
    os.makedirs(out, exist_ok=True)
    state_file = os.path.join(out, f"{a.prefix}_pages.json")
    pages = json.load(open(state_file)) if os.path.exists(state_file) else {}

    first = req(a.url).decode("utf-8", "replace")
    tot = re.search(r'TextBoxPagineTot"[^>]*value="/(\d+)"', first) or re.search(r'value="/(\d+)"', first)
    if not tot:
        sys.exit("Could not find the page count on the record page.")
    total = int(tot.group(1))
    base_fields = hidden_fields(first)
    print(f"{total} images in this record; {len(pages)} already listed.")

    # 1) list image filenames (the server takes several seconds per page, so use a few workers)
    def lookup(n):
        data = dict(base_fields)
        data[P + "TextBoxPagina"] = str(n)
        data[P + "ButtonVaiPagina"] = "Vai a pagina"
        try:
            page = req(a.url, data).decode("utf-8", "replace")
        except Exception as e:
            return n, None
        time.sleep(0.3)
        return n, image_path(page)

    todo = [n for n in range(1, total + 1) if str(n) not in pages]
    done = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, path in ex.map(lookup, todo):
            done += 1
            if path:
                pages[str(n)] = path
            else:
                print(f"  page {n}: no image found (rerun to retry)")
            if done % 25 == 0 or done == len(todo):
                json.dump(pages, open(state_file, "w"), indent=0)
                print(f"  listed {len(pages)}/{total}")
    json.dump(pages, open(state_file, "w"), indent=0)

    with open(os.path.join(out, f"urls_{a.prefix}.txt"), "w") as uf:
        for n in sorted(pages, key=int):
            uf.write(f"# {a.prefix}_{int(n):05d}\n{SITE}{pages[n]}\n")
    if len(pages) < total:
        sys.exit(f"Only {len(pages)}/{total} pages listed; rerun to continue.")
    if a.list_only:
        print(f"Wrote urls_{a.prefix}.txt")
        return

    # 2) download images
    failed = []
    for n in sorted(pages, key=int):
        name = f"{a.prefix}_{int(n):05d}.jpg"
        dest = os.path.join(out, name)
        if os.path.exists(dest) and os.path.getsize(dest) > 0:
            continue
        try:
            blob = req(SITE + pages[n])
        except Exception as e:
            print(f"[{n}/{total}] FAILED {name}: {e}")
            failed.append(n)
            continue
        with open(dest + ".part", "wb") as fh:
            fh.write(blob)
        os.replace(dest + ".part", dest)
        print(f"[{n}/{total}] {name}  {len(blob)//1024} KB")
        time.sleep(a.sleep)

    print(f"\nDone. {total - len(failed)}/{total} OK." + (" Rerun to retry failures." if failed else ""))


if __name__ == "__main__":
    main()
