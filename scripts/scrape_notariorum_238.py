#!/usr/bin/env python3
"""
Scrapes all image hashes for all 6 series plus root page of register 238
from notariorumitinera.eu. Outputs urls_238_all.txt for dezoomify_batch_notariorum.sh

NOTE: Only 6 series found in page links (expected 7) — add series 7 to SERIES
if its Id_Oggetto_Archivistico is found.

SETUP: pip install requests
USAGE: python scrape_notariorum_238.py
"""

import requests, re, time, sys, os

ID_PROGETTO   = "40"
COMBINED_FILE = "urls_238_all.txt"
SLEEP_SEC     = 1.5
RETRY_MAX     = 5
RETRY_SLEEP   = 15

SESSION_COOKIE = "itvug5felcqgo2js1snj4xnk"

SERIES = [
    ("172916",  0),  # root page (6 images)
    ("172924",  1),
    ("173279",  2),
    ("173373",  3),
    ("173466",  4),
    ("173469",  5),
    ("173474",  6),
]

BASE     = "https://notariorumitinera.eu"
PATH_RE  = re.compile(r'viewer\.html\?FIF=([^"]+)/([a-f0-9]{32})\.tif', re.IGNORECASE)
TOTAL_RE = re.compile(r'TextBoxPagineTot[^>]*value="/(\d+)"', re.IGNORECASE)

def extract_field(html, name):
    m = re.search(r'<input[^>]+name="' + re.escape(name) + r'"[^>]+value="([^"]*)"', html)
    if not m:
        m = re.search(r'<input[^>]+value="([^"]*)"[^>]+name="' + re.escape(name) + r'"', html)
    return m.group(1) if m else ""

def extract_path_and_hash(html):
    m = PATH_RE.search(html)
    return (m.group(1), m.group(2)) if m else (None, None)

def extract_total(html):
    m = TOTAL_RE.search(html)
    return int(m.group(1)) if m else None

def post_with_retry(session, url, data):
    for attempt in range(1, RETRY_MAX + 1):
        try:
            resp = session.post(url, data=data, timeout=30)
            resp.raise_for_status()
            return resp
        except (requests.ConnectionError, requests.Timeout) as e:
            if attempt == RETRY_MAX:
                raise
            print("  Connection error ({}/{}): {}".format(attempt, RETRY_MAX, e))
            print("  Waiting {} seconds...".format(RETRY_SLEEP))
            time.sleep(RETRY_SLEEP)

def scrape_series(session, id_oggetto, series_num):
    progress_file = "urls_238_series_{:02d}.txt".format(series_num)
    if os.path.exists(progress_file):
        print("  Loading saved progress from {}".format(progress_file))
        entries = []
        with open(progress_file) as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) == 2:
                    entries.append((parts[0], parts[1]))
        print("  Loaded {} entries".format(len(entries)))
        return entries

    page_url = "{}/NI_vs_OA.aspx?Id_Oggetto_Archivistico={}&Id_Progetto={}".format(
        BASE, id_oggetto, ID_PROGETTO)
    resp = session.get(page_url, timeout=30)
    if resp.status_code == 403:
        print("ERROR 403 — session expired. Re-run with a fresh cookie.")
        sys.exit(1)
    resp.raise_for_status()
    html = resp.text

    register_path, first_hash = extract_path_and_hash(html)
    if not register_path:
        print("  ERROR: No image path found for series {:02d}".format(series_num))
        return []
    total = extract_total(html)
    if not total:
        print("  ERROR: No total found for series {:02d}".format(series_num))
        return []

    print("  Path: {} | Total: {}".format(register_path, total))
    iip_base = "{}/IIPServer/fcgi/iipsrv.fcgi?FIF={}/{{hash}}.tif".format(BASE, register_path)
    hashes = [first_hash]
    print("  [1/{}] {}".format(total, first_hash))

    for i in range(1, total):
        form_data = {
            "__LASTFOCUS": "",
            "__VIEWSTATE": extract_field(html, "__VIEWSTATE"),
            "__VIEWSTATEGENERATOR": extract_field(html, "__VIEWSTATEGENERATOR"),
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__EVENTVALIDATION": extract_field(html, "__EVENTVALIDATION"),
            "ctl00$PlaceHolderMain$TemplateElemArch$TextBoxPagina": str(i),
            "ctl00$PlaceHolderMain$TemplateElemArch$TextBoxPagineTot": "/{}".format(total),
            "ctl00$PlaceHolderMain$TemplateElemArch$ButtonAvanti": ">",
            "ctl00$PlaceHolderMain$TemplateElemArch$HiddenFieldRisorsaCorrente": str(i - 1),
        }
        time.sleep(SLEEP_SEC)
        try:
            resp = post_with_retry(session, page_url, form_data)
        except Exception as e:
            print("\nFATAL on series {:02d} page {}: {}".format(series_num, i + 1, e))
            entries = [(iip_base.format(hash=h), "s{:02d}_{:04d}".format(series_num, idx + 1))
                       for idx, h in enumerate(hashes)]
            with open(progress_file, "w") as f:
                for url, label in entries:
                    f.write("{}\t{}\n".format(url, label))
            print("Saved {} entries to {}. Re-run after refreshing SESSION_COOKIE.".format(
                len(hashes), progress_file))
            sys.exit(1)
        html = resp.text
        _, h = extract_path_and_hash(html)
        if not h:
            print("  WARNING: No hash on page {}, stopping early.".format(i + 1))
            break
        hashes.append(h)
        print("  [{}/{}] {}".format(i + 1, total, h))

    entries = [(iip_base.format(hash=h), "s{:02d}_{:04d}".format(series_num, idx + 1))
               for idx, h in enumerate(hashes)]
    with open(progress_file, "w") as f:
        for url, label in entries:
            f.write("{}\t{}\n".format(url, label))
    return entries

def main():
    if SESSION_COOKIE == "PASTE_YOUR_SESSION_ID_HERE":
        print("ERROR: Paste your ASP.NET_SessionId cookie value into the script first.")
        sys.exit(1)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,it;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    })
    session.cookies.set("ASP.NET_SessionId", SESSION_COOKIE, domain="notariorumitinera.eu")

    all_entries = []
    for id_oggetto, series_num in SERIES:
        print("\n=== Series {:02d} (Id={}) ===".format(series_num, id_oggetto))
        entries = scrape_series(session, id_oggetto, series_num)
        all_entries.extend(entries)
        print("  Series {:02d} done: {} images".format(series_num, len(entries)))

    print("\nWriting {} total URLs to {}...".format(len(all_entries), COMBINED_FILE))
    with open(COMBINED_FILE, "w") as f:
        for url, label in all_entries:
            f.write("{}\t{}\n".format(url, label))
    print("Done! Run:")
    print("  bash dezoomify_batch_notariorum.sh {} notariorum_238_output".format(COMBINED_FILE))

if __name__ == "__main__":
    main()
