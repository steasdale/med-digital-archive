#!/usr/bin/env python3
"""
Try likely METS filenames in a storiapatriagenova.it image folder and report any that exist.

Usage:
  python probe_mets.py <folder_url> <fondo> <number>
Example:
  python probe_mets.py "https://www.storiapatriagenova.it/Docs/Biblioteca_Digitale/OA/Comune_di_Genova/Manoscritti/Ricci/77/" Ricci 77
"""
import sys, time, urllib.request, urllib.error

folder, fondo, num = sys.argv[1].rstrip("/") + "/", sys.argv[2], sys.argv[3]
parent = folder.rstrip("/").rsplit("/", 1)[0] + "/"
n = num
variants = {n, n.zfill(3), n.zfill(4), str(int(n)) if n.isdigit() else n}
f_variants = {fondo, fondo.lower(), fondo.upper()}

names = set()
for v in variants:
    names |= {f"{v}.xml", f"{v}.XML", f"mets_{v}.xml", f"{v}_mets.xml", f"METS_{v}.xml"}
    for f in f_variants:
        names |= {f"{f}{v}.xml", f"{f}_{v}.xml", f"{f}-{v}.xml", f"{f} {v}.xml".replace(" ", "%20"),
                  f"{f}.{v}.xml"}
names |= {"mets.xml", "METS.xml", "Mets.xml", "index.xml", "metadata.xml"}

urls = [folder + nm for nm in sorted(names)]
urls += [parent + nm for nm in sorted(names) if not nm.startswith(("mets.", "METS.", "Mets.", "index", "metadata"))]

UA = {"User-Agent": "Mozilla/5.0"}
found = []
for i, u in enumerate(urls, 1):
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30) as r:
            head = r.read(4000).decode("utf-8", "replace")
        if "404%3b" in head or "<html" in head.lower():
            status = "not found"
        else:
            status = "FOUND"
            found.append(u)
    except urllib.error.HTTPError as e:
        status = f"HTTP {e.code}"
    except Exception as e:
        status = f"error: {e}"
    print(f"[{i}/{len(urls)}] {status:10} {u}")
    time.sleep(0.5)

print()
if found:
    print("Possible METS file(s):")
    for u in found:
        print("  ", u)
else:
    print("No METS found under any of the tried names.")
