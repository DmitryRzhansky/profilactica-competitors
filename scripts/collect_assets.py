# -*- coding: utf-8 -*-
"""Download Chart.js, competitor favicons and desktop screenshots."""
from __future__ import annotations

import io
import json
import re
import shutil
import ssl
import time
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "assets" / "vendor" / "chartjs"
DATA = ROOT / "assets" / "data"
COMP = ROOT / "assets" / "competitors"
CTX = ssl.create_default_context()

CHART_URL = "https://cdn.jsdelivr.net/npm/chart.js@4.4.8/dist/chart.umd.min.js"

SCREENSHOTS = [
    {
        "domain": "verimed.ru",
        "url": "https://verimed.ru/uslugi/narkologiya",
        "file": "silo.webp",
        "fallbacks": ["https://verimed.ru/uslugi/narkologiya/narkologicheskaya-pomosh", "https://verimed.ru/"],
    },
    {
        "domain": "alcomed.ru",
        "url": "https://alcomed.ru/uslugi/vyvod-iz-zapoya",
        "file": "trust.webp",
        "fallbacks": ["https://alcomed.ru/uslugi/narcolog", "https://alcomed.ru/stacionar", "https://alcomed.ru/"],
    },
    {
        "domain": "alcoclinic.ru",
        "url": "https://www.alcoclinic.ru/uslugi/kodirovanie-ot-alkogolizma",
        "file": "methods.webp",
        "fallbacks": ["https://www.alcoclinic.ru/uslugi/kodirovanie-ot-alkogolizma/preparat-esperal", "https://www.alcoclinic.ru/"],
    },
    {
        "domain": "ne-zavisimost.ru",
        "url": "https://ne-zavisimost.ru/gruppa-dlya-rodstvennikov-zavisimyh",
        "file": "journey.webp",
        "fallbacks": [
            "https://ne-zavisimost.ru/reabilitaciya-alko/post-reabilitacionnaya-programma",
            "https://ne-zavisimost.ru/reabilitaciya-alko",
            "https://ne-zavisimost.ru/",
        ],
    },
    {
        "domain": "trezviy-kurs.clinic",
        "url": "https://trezviy-kurs.clinic/metro/narkolog-na-dom/belorusskaya.html",
        "file": "geo.webp",
        "fallbacks": ["https://trezviy-kurs.clinic/metro/narkolog-na-dom/aeroport.html", "https://trezviy-kurs.clinic/"],
    },
    {
        "domain": "klinika-korsakov.ru",
        "url": "https://klinika-korsakov.ru/ambulatornaya_programma",
        "file": "psy.webp",
        "fallbacks": ["https://klinika-korsakov.ru/stati/psixiatriya/page2", "https://klinika-korsakov.ru/"],
    },
    {
        "domain": "narkolog24.clinic",
        "url": "https://narkolog24.clinic/service/vyvod-iz-zapoya/narkolog-na-dom",
        "file": "commercial.webp",
        "fallbacks": ["https://narkolog24.clinic/tseny", "https://narkolog24.clinic/service/vyvod-iz-zapoya", "https://narkolog24.clinic/"],
    },
]

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


class IconParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag != "link":
            return
        d = {k.lower(): v for k, v in attrs}
        rel = (d.get("rel") or "").lower()
        href = d.get("href")
        if href and any(x in rel for x in ("icon", "shortcut", "apple-touch")):
            self.hrefs.append((rel, href, d.get("sizes") or ""))


def fetch(url: str, timeout: int = 25) -> bytes:
    req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urlopen(req, timeout=timeout, context=CTX) as resp:
        return resp.read(), resp.geturl(), resp.headers.get("Content-Type", "")


def fetch_ok(url: str):
    try:
        body, final, ctype = fetch(url)
        return body, final, ctype
    except Exception as exc:
        print("  fetch fail", url, exc)
        return None, None, None


def guess_ext(url: str, ctype: str, body: bytes) -> str:
    path = urlparse(url).path.lower()
    for ext in (".png", ".ico", ".svg", ".webp", ".jpg", ".jpeg", ".gif"):
        if path.endswith(ext):
            return ext
    ctype = (ctype or "").lower()
    if "svg" in ctype:
        return ".svg"
    if "png" in ctype:
        return ".png"
    if "webp" in ctype:
        return ".webp"
    if "jpeg" in ctype or "jpg" in ctype:
        return ".jpg"
    if "icon" in ctype:
        return ".ico"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if body[:4] == b"\x00\x00\x01\x00" or body[:4] == b"\x00\x00\x02\x00":
        return ".ico"
    if body[:3] == b"GIF":
        return ".gif"
    if body[:4] == b"<svg" or body.lstrip().startswith(b"<svg"):
        return ".svg"
    return ".ico"


def save_favicon(domain: str) -> None:
    dest_dir = COMP / domain
    dest_dir.mkdir(parents=True, exist_ok=True)
    existing = list(dest_dir.glob("favicon.*"))
    if existing:
        print("favicon exists", domain, existing[0].name)
        return
    home = f"https://{domain}/"
    body, final, _ = fetch_ok(home)
    candidates = []
    if body:
        parser = IconParser()
        try:
            parser.feed(body.decode("utf-8", errors="ignore"))
        except Exception:
            pass
        base = final or home
        for rel, href, sizes in parser.hrefs:
            candidates.append(urljoin(base, href))
    candidates.append(urljoin(home, "/favicon.ico"))
    seen = set()
    for href in candidates:
        if href in seen:
            continue
        seen.add(href)
        data, final, ctype = fetch_ok(href)
        if not data or len(data) < 32:
            continue
        ext = guess_ext(final or href, ctype, data)
        path = dest_dir / f"favicon{ext}"
        path.write_bytes(data)
        print("favicon saved", domain, path.name, len(data))
        return
    print("favicon missing", domain)


def dismiss_overlays(page) -> None:
    selectors = [
        "button:has-text('Принять')",
        "button:has-text('Согласен')",
        "button:has-text('Согласна')",
        "button:has-text('Accept')",
        "button:has-text('OK')",
        "[class*='cookie'] button",
        ".cookie-accept",
        "#cookie-accept",
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel).first
            if loc.count() and loc.is_visible(timeout=400):
                loc.click(timeout=800)
                time.sleep(0.3)
        except Exception:
            pass


def screenshot_one(page, item: dict) -> bool:
    dest_dir = COMP / item["domain"] / "screenshots"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / item["file"]
    urls = [item["url"], *item.get("fallbacks", [])]
    for url in urls:
        try:
            print("screenshot", item["domain"], url)
            resp = page.goto(url, wait_until="domcontentloaded", timeout=45000)
            status = resp.status if resp else 0
            if status >= 400:
                print("  status", status)
                continue
            page.wait_for_timeout(2200)
            dismiss_overlays(page)
            page.wait_for_timeout(400)
            page.screenshot(path=str(dest), type="webp", quality=82, full_page=False)
            print("  saved", dest, dest.stat().st_size)
            return True
        except Exception as exc:
            print("  fail", url, exc)
    print("screenshot missing", item["domain"])
    return False


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    VENDOR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "profilactica_report_data.json", DATA / "report-data.json")
    shutil.copy2(ROOT / "profilactica_final_architecture.csv", DATA / "architecture.csv")
    shutil.copy2(ROOT / "profilactica_geo_pages.csv", DATA / "geo-pages.csv")
    shutil.copy2(ROOT / "profilactica_geo_master_lists.csv", DATA / "geo-master.csv")

    chart = VENDOR / "chart.umd.min.js"
    if not chart.exists() or chart.stat().st_size < 10000:
        print("download Chart.js")
        data, _, _ = fetch(CHART_URL, timeout=60)
        chart.write_bytes(data)
    print("Chart.js", chart.stat().st_size)

    for item in SCREENSHOTS:
        save_favicon(item["domain"])

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 900},
            user_agent=UA,
            locale="ru-RU",
        )
        page.set_extra_http_headers({"Accept-Language": "ru-RU,ru;q=0.9"})
        for item in SCREENSHOTS:
            screenshot_one(page, item)
        browser.close()
    print("done")


if __name__ == "__main__":
    main()
