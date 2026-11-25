#!/usr/bin/env python3
"""
Download all page images for a storiapatriagenova.it "Biblioteca Digitale" object
by reading its METS XML (the file linked as "Mets-Ecomic" on the record page).

Images are plain JPEGs named by their MD5 hash, sitting in the same folder as the METS.
Each download is verified against the MD5 checksum in the METS.

Usage:
  python3 scrape_storiapatria.py <METS_URL_or_local_path> <PREFIX> [--out DIR] [--group USE] [--list-only]

Example (Molfino 439):
  python3 scrape_storiapatria.py \
    "https://www.storiapatriagenova.it/Docs/Biblioteca_Digitale/OA/Comune_di_Genova/Manoscritti/Molfino/439/439.xml" \
    Molfino439 --out Molfino439
"""
import argparse, hashlib, os, re, sys, time, urllib.request, urllib.parse
import xml.etree.ElementTree as ET

NS = {"mets": "http://www.loc.gov/METS/", "xlink": "http://www.w3.org/1999/xlink"}
HREF = "{http://www.w3.org/1999/xlink}href"
UA = {"User-Agent": "Mozilla/5.0 (research download; contact via storiapatriagenova.it)"}


def fetch(url, retries=4):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:
            if attempt == retries:
                raise
            wait = 5 * attempt
            print(f"   retry {attempt}/{retries - 1} in {wait}s ({e})", file=sys.stderr)
            time.sleep(wait)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mets")
    ap.add_argument("prefix", help="register identifier prepended to filenames, e.g. Molfino439")
    ap.add_argument("--out", default=None)
    ap.add_argument("--group", default=None, help="fileGrp USE value to download (default: largest group)")
    ap.add_argument("--list-only", action="store_true", help="write urls file and exit")
    ap.add_argument("--sleep", type=float, default=1.0)
    a = ap.parse_args()

    # Normalise the odd %5C (backslash) URL the site links to into forward slashes
    src = urllib.parse.unquote(a.mets).replace("\\", "/") if a.mets.startswith("http") else a.mets
    src = src.replace("OA//", "OA/")
    if src.startswith("http"):
        print(f"Fetching METS: {src}")
        data = fetch(src)
        base = src.rsplit("/", 1)[0] + "/"
    else:
        data = open(src, "rb").read()
        base = None

    out = a.out or a.prefix
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"{a.prefix}_mets.xml"), "wb") as fh:
        fh.write(data)

    head = data[:2000].decode("utf-8", "replace").lower()
    if "<mets" not in data[:200000].decode("utf-8", "replace").lower():
        print("\nThe server did not return a METS file (probably an error page / wrong URL).")
        print(f"Saved what it returned as {out}/{a.prefix}_mets.xml for inspection.")
        print("Copy the real 'Mets-Ecomic' link from the record page and rerun.")
        if "<html" in head or "<!doctype" in head:
            print("(It looks like an HTML page.)")
        sys.exit(1)

    items = []
    try:
        root = ET.fromstring(data)
        groups = root.findall(".//mets:fileSec//mets:fileGrp", NS)
        print("fileGrps found:")
        usable = []
        for g in groups:
            files = g.findall("mets:file", NS)
            if files:
                usable.append(g)
            print(f"  USE={g.get('USE')!r:20} files={len(files)}")
        if a.group:
            grp = next(g for g in usable if g.get("USE") == a.group)
        else:
            grp = max(usable, key=lambda g: len(g.findall("mets:file", NS)))
        for f in grp.findall("mets:file", NS):
            loc = f.find("mets:FLocat", NS)
            href = loc.get(HREF).lstrip("./")
            items.append((int(f.get("SEQ", "0")), href, (f.get("CHECKSUM") or "").lower()))
        print(f"Using group USE={grp.get('USE')!r}")
    except ET.ParseError as e:
        # Malformed XML (e.g. unescaped '&' in metadata): fall back to text matching
        print(f"METS is not well-formed XML ({e}); falling back to text matching.")
        text = data.decode("utf-8", "replace")
        seen = set()
        for m in re.finditer(r"<mets:file\b([^>]*)>(.*?)</mets:file>", text, re.S):
            attrs, body = m.group(1), m.group(2)
            href = re.search(r'xlink:href="([^"]+)"', body)
            if not href:
                continue
            href = href.group(1).lstrip("./")
            if href in seen:
                continue
            seen.add(href)
            seq = re.search(r'\bSEQ="(\d+)"', attrs)
            md5 = re.search(r'\bCHECKSUM="([0-9a-fA-F]+)"', attrs)
            items.append((int(seq.group(1)) if seq else len(items) + 1, href,
                          md5.group(1).lower() if md5 else ""))
    items.sort()
    print(f"{len(items)} images listed")
    if not items:
        print("No image entries found; check the saved METS file.")
        sys.exit(1)

    if base is None:
        base = input("METS was local; enter image base URL (folder containing the .jpg files): ").rstrip("/") + "/"

    # urls file in the usual '# label' + URL format, for the record
    with open(os.path.join(out, f"urls_{a.prefix}.txt"), "w") as uf:
        for i, (seq, href, _) in enumerate(items, 1):
            uf.write(f"# {a.prefix}_{i:05d} (SEQ {seq})\n{base}{href}\n")
    if a.list_only:
        print(f"Wrote urls_{a.prefix}.txt")
        return

    failed = []
    for i, (seq, href, md5) in enumerate(items, 1):
        name = f"{a.prefix}_{i:05d}.jpg"
        path = os.path.join(out, name)
        if os.path.exists(path) and os.path.getsize(path) > 0:
            continue
        url = base + href
        try:
            blob = fetch(url)
        except Exception as e:
            print(f"[{i}/{len(items)}] FAILED {name}: {e}")
            failed.append(url)
            continue
        if md5 and hashlib.md5(blob).hexdigest() != md5:
            print(f"[{i}/{len(items)}] checksum mismatch {name} (saved anyway as .badmd5)")
            path += ".badmd5"
        with open(path + ".part", "wb") as fh:
            fh.write(blob)
        os.replace(path + ".part", path)
        print(f"[{i}/{len(items)}] {name}  {len(blob)//1024} KB")
        time.sleep(a.sleep)

    print(f"\nDone. {len(items) - len(failed)}/{len(items)} OK.")
    if failed:
        with open(os.path.join(out, "failed.txt"), "w") as fh:
            fh.write("\n".join(failed) + "\n")
        print("Failed URLs in failed.txt — just rerun the same command to retry.")


if __name__ == "__main__":
    main()
