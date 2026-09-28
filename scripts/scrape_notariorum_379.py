#!/usr/bin/env python3
"""
Scrapes all image hashes for all 62 series plus root page of register 379
from notariorumitinera.eu. Outputs a single combined tab-separated
urls_379_all.txt file compatible with dezoomify_batch_notariorum.sh

SETUP (run once):
    pip install requests

HOW TO GET YOUR SESSION COOKIE:
    1. Open any series page in Chrome
    2. Press F12 -> Application -> Cookies -> https://notariorumitinera.eu
    3. Copy the value of ASP.NET_SessionId
    4. Paste it into SESSION_COOKIE below

Usage:
    python scrape_notariorum_379.py
"""

import requests
import re
import time
import sys
import os

# == Configuration =============================================================
ID_PROGETTO   = "40"
COMBINED_FILE = "urls_379_all.txt"
SLEEP_SEC     = 1.5
RETRY_MAX     = 5
RETRY_SLEEP   = 15

# Paste your ASP.NET_SessionId cookie value here
SESSION_COOKIE = "l4cqtkfo4qtrrcrfowujeabn"

# Root page + all 62 series: (Id_Oggetto_Archivistico, series_number)
SERIES = [
    ("182302",  0),  # root page (5 images)
    ("182308",  1),
    ("182323",  2),
    ("182332",  3),
    ("182335",  4),
    ("182338",  5),
    ("182341",  6),
    ("182344",  7),
    ("182347",  8),
    ("182350",  9),
    ("182353", 10),
    ("182356", 11),
    ("182359", 12),
    ("182368", 13),
    ("182385", 14),
    ("182388", 15),
    ("182393", 16),
    ("182398", 17),
    ("182401", 18),
    ("182404", 19),
    ("182423", 20),
    ("182468", 21),
    ("182487", 22),
    ("182490", 23),
    ("182493", 24),
    ("182516", 25),
    ("182561", 26),
    ("182584", 27),
    ("182587", 28),
    ("182590", 29),
    ("182595", 30),
    ("182602", 31),
    ("182605", 32),
    ("182608", 33),
    ("182611", 34),
    ("182614", 35),
    ("182617", 36),
    ("182620", 37),
    ("182623", 38),
    ("182626", 39),
    ("182633", 40),
    ("182638", 41),
    ("182641", 42),
    ("182644", 43),
    ("182647", 44),
    ("182650", 45),
    ("182653", 46),
    ("182656", 47),
    ("182659", 48),
    ("182662", 49),
    ("182667", 50),
    ("182670", 51),
    ("182703", 52),
    ("182706", 53),
    ("182711", 54),
    ("182714", 55),
    ("182717", 56),
    ("182720", 57),
    ("182723", 58),
    ("182726", 59),
    ("182729", 60),
    ("182737", 61),
    ("182731", 62),
]
# ==============================================================================

BASE = "https://notariorumitinera.eu"

PATH_RE = re.compile(
    r'viewer\.html\?FIF=([^"]+)/([a-f0-9]{32})\.tif', re.IGNORECASE
)
TOTAL_RE = re.compile(
    r'TextBoxPagineTot[^>]*value="/(\d+)"', re.IGNORECASE
)

def extract_field(html, name):
    m = re.search(r'<input[^>]+name="' + re.escape(name) + r'"[^>]+value="([^"]*)"', html)
    if not m:
        m = re.search(r'<input[^>]+value="([^"]*)"[^>]+name="' + re.escape(name) + r'"', html)
    return m.group(1) if m else ""

def extract_path_and_hash(html):
    m = PATH_RE.search(html)
    if m:
        return m.group(1), m.group(2)
    return None, None

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
            print("  Connection error (attempt {}/{}): {}".format(attempt, RETRY_MAX, e))
            print("  Waiting {} seconds...".format(RETRY_SLEEP))
            time.sleep(RETRY_SLEEP)

def scrape_series(session, id_oggetto, series_num):
    progress_file = "urls_379_series_{:02d}.txt".format(series_num)

    if os.path.exists(progress_file):
        print("  Loading saved progress from {}".format(progress_file))
        entries = []
        with open(progress_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split("\t")
                    if len(parts) == 2:
                        entries.append((parts[0], parts[1]))
        print("  Loaded {} entries".format(len(entries)))
        return entries

    page_url = (
        "{}/NI_vs_OA.aspx?Id_Oggetto_Archivistico={}&Id_Progetto={}".format(
            BASE, id_oggetto, ID_PROGETTO
        )
    )

    resp = session.get(page_url, timeout=30)
    if resp.status_code == 403:
        print("ERROR 403 — session may have expired. Re-run with a fresh cookie.")
        sys.exit(1)
    resp.raise_for_status()
    html = resp.text

    register_path, first_hash = extract_path_and_hash(html)
    if not register_path:
        print("  ERROR: Could not find image path for series {:02d}".format(series_num))
        return []

    total = extract_total(html)
    if not total:
        print("  ERROR: Could not find total for series {:02d}".format(series_num))
        return []

    print("  Path: {} | Total: {}".format(register_path, total))

    iip_base = "{}/IIPServer/fcgi/iipsrv.fcgi?FIF={}/{{hash}}.tif".format(BASE, register_path)
    hashes = [first_hash]
    print("  [1/{}] {}".format(total, first_hash))

    for i in range(1, total):
        viewstate       = extract_field(html, "__VIEWSTATE")
        vsgenerator     = extract_field(html, "__VIEWSTATEGENERATOR")
        eventvalidation = extract_field(html, "__EVENTVALIDATION")

        form_data = {
            "__LASTFOCUS": "",
            "__VIEWSTATE": viewstate,
            "__VIEWSTATEGENERATOR": vsgenerator,
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "__EVENTVALIDATION": eventvalidation,
            "ctl00$PlaceHolderMain$TemplateElemArch$TextBoxPagina": str(i),
            "ctl00$PlaceHolderMain$TemplateElemArch$TextBoxPagineTot": "/{}".format(total),
            "ctl00$PlaceHolderMain$TemplateElemArch$ButtonAvanti": ">",
            "ctl00$PlaceHolderMain$TemplateElemArch$HiddenFieldRisorsaCorrente": str(i - 1),
        }

        time.sleep(SLEEP_SEC)

        try:
            resp = post_with_retry(session, page_url, form_data)
        except Exception as e:
            print("\nFATAL error on series {:02d} page {}: {}".format(series_num, i + 1, e))
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
            print("  WARNING: No hash on page {}, stopping series early.".format(i + 1))
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
        print("\n=== Series {:02d} (Id_Oggetto_Archivistico={}) ===".format(series_num, id_oggetto))
        entries = scrape_series(session, id_oggetto, series_num)
        all_entries.extend(entries)
        print("  Series {:02d} done: {} images".format(series_num, len(entries)))

    print("\nWriting {} total URLs to {}...".format(len(all_entries), COMBINED_FILE))
    with open(COMBINED_FILE, "w") as f:
        for url, label in all_entries:
            f.write("{}\t{}\n".format(url, label))

    print("Done! Run the batch downloader once:")
    print("  bash dezoomify_batch_notariorum.sh {} notariorum_379_output".format(COMBINED_FILE))

if __name__ == "__main__":
    main()
