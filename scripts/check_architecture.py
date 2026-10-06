# -*- coding: utf-8 -*-
"""Integrity checks for the rebuilt profilactica URL architecture."""
from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN = re.compile(r"/(?:metro|okrug|mo)(?:/|$)")
MOSKVA_LOCATION = re.compile(r"^/uslugi(?:/[a-z0-9-]+)+/moskva/[a-z0-9-]+/$")
MO_LOCATION = re.compile(r"^/uslugi(?:/[a-z0-9-]+)+/moskovskaya-oblast/[a-z0-9-]+/$")
SITE_URL = re.compile(r"/(?:uslugi|o-klinike|pomoshch|ceny|vrachi)/[a-z0-9\-/]*")
FENCE = re.compile(r"```text\n(.*?)```", re.S)
PRE = re.compile(r"<pre[^>]*>\s*<code>(.*?)</code>\s*</pre>", re.S)

ALLOWED_GEO = {
    "narkolog-na-dom": {"metro", "okrug", "mo"},
    "vyvod-iz-zapoya": {"metro", "okrug", "mo"},
    "ot-zapoya-i-alkogolya": {"metro", "okrug", "mo"},
    "kodirovanie": {"metro", "okrug", "mo"},
    "psihiatr-na-dom": {"okrug", "mo"},
    "lechenie-alkogolizma": {"mo"},
    "lechenie-narkomanii": {"mo"},
    "reabilitaciya": {"mo"},
}


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def fail(errors, message):
    errors.append(message)


def check():
    errors = []
    arch = read_csv(ROOT / "profilactica_final_architecture.csv")
    geo = read_csv(ROOT / "profilactica_geo_pages.csv")
    rel = read_csv(ROOT / "profilactica_geo_relationships.csv")
    mapping = read_csv(ROOT / "profilactica_url_rearchitecture_map.csv")
    canon = read_csv(ROOT / "profilactica_canonical_urls.csv")
    master = read_csv(ROOT / "profilactica_geo_master_lists.csv")

    urls = [row["new_url"] for row in mapping]
    if len(urls) != len(set(urls)):
        dupes = [url for url, count in Counter(urls).items() if count > 1]
        fail(errors, f"duplicate new_url: {dupes[:8]}")

    by_url = {row["new_url"]: row for row in mapping}
    empty_parents = [row["new_url"] for row in mapping if not row["new_parent"]]
    if empty_parents != ["/"]:
        fail(errors, f"pages without parent: {empty_parents}")
    for row in mapping:
        if row["new_url"] == "/":
            continue
        if not row["new_parent"]:
            fail(errors, f"missing parent: {row['new_url']}")
        elif row["new_parent"] not in by_url:
            fail(errors, f"parent does not exist: {row['new_url']} -> {row['new_parent']}")

    for row in mapping:
        seen = []
        current = row["new_url"]
        while current:
            if current in seen:
                fail(errors, f"cycle at {row['new_url']}: {' -> '.join(seen)}")
                break
            seen.append(current)
            current = by_url[current]["new_parent"]
            if len(seen) > 12:
                fail(errors, f"parent chain too deep: {row['new_url']}")
                break

    for row in mapping:
        if row["new_url"] != row["old_plan_url"] and FORBIDDEN.search(row["new_url"]):
            fail(errors, f"forbidden segment in new_url: {row['new_url']}")
        if FORBIDDEN.search(row["new_url"]):
            fail(errors, f"forbidden segment in canonical url: {row['new_url']}")

    for row in arch:
        if FORBIDDEN.search(row["url"]) or FORBIDDEN.search(row["parent"]):
            fail(errors, f"forbidden segment in architecture: {row['url']} parent {row['parent']}")
    for row in geo:
        if FORBIDDEN.search(row["proposed_url"]):
            fail(errors, f"forbidden segment in geo: {row['proposed_url']}")

    metro_slugs = {row["slug"] for row in master if row["geo_type"] == "metro"}
    okrug_slugs = {row["slug"] for row in master if row["geo_type"] == "okrug"}
    city_slugs = {row["slug"] for row in master if row["geo_type"] == "mo"}
    if metro_slugs & okrug_slugs:
        fail(errors, f"metro/okrug slug collision: {metro_slugs & okrug_slugs}")

    for row in geo:
        url = row["proposed_url"]
        if row["geo_type"] in {"metro", "okrug"}:
            if not MOSKVA_LOCATION.match(url):
                fail(errors, f"moscow geo not under /moskva/: {url}")
            slug = url.rstrip("/").split("/")[-1]
            if row["geo_type"] == "metro" and slug not in metro_slugs:
                fail(errors, f"unknown metro slug: {url}")
            if row["geo_type"] == "okrug" and slug not in okrug_slugs:
                fail(errors, f"unknown okrug slug: {url}")
        elif row["geo_type"] == "mo":
            if not MO_LOCATION.match(url):
                fail(errors, f"city not under /moskovskaya-oblast/: {url}")
            if url.rstrip("/").split("/")[-1] not in city_slugs:
                fail(errors, f"unknown city slug: {url}")
        else:
            fail(errors, f"unexpected geo type: {row['geo_type']}")
        allowed = ALLOWED_GEO.get(row["service"])
        if allowed is None or row["geo_type"] not in allowed:
            fail(errors, f"geo not allowed: {row['service']} {row['geo_type']}")

    intent = defaultdict(list)
    for row in geo:
        intent[(row["service"], row["geo_type"], row["geo_slug"])].append(row["proposed_url"])
    for key, values in intent.items():
        if len(set(values)) != 1:
            fail(errors, f"duplicate service location: {key}")

    by_station = defaultdict(list)
    for row in rel:
        by_station[row["metro_slug"]].append(row["okrug_slug"])
    for slug, okrugs in by_station.items():
        if len(okrugs) != 1:
            fail(errors, f"station without one canonical okrug: {slug} {okrugs}")
    if len(rel) != len(metro_slugs):
        fail(errors, f"relationship count {len(rel)} != metro {len(metro_slugs)}")
    stations_by_okrug = defaultdict(set)
    for row in rel:
        stations_by_okrug[row["okrug_slug"]].add(row["metro_slug"])
    if "belorusskaya" in stations_by_okrug["vao"]:
        fail(errors, "VAO includes Belorusskaya")
    if stations_by_okrug["belorusskaya"] if False else stations_by_okrug.get("cao") and "belorusskaya" not in stations_by_okrug["cao"]:
        fail(errors, "Belorusskaya is not in CAO")
    for slug in metro_slugs:
        owners = [okrug for okrug, stations in stations_by_okrug.items() if slug in stations]
        if len(owners) != 1:
            fail(errors, f"station okrug count {slug}: {owners}")

    arch_urls = {row["url"] for row in arch}
    for row in geo:
        parent = mapping_parent(mapping, row["proposed_url"])
        if parent not in arch_urls:
            fail(errors, f"geo parent is not an architecture page: {row['proposed_url']} -> {parent}")
        if row["geo_type"] in {"metro", "okrug"} and not parent.endswith("/moskva/"):
            fail(errors, f"moscow page parent is not moskva hub: {row['proposed_url']}")
        if row["geo_type"] == "mo" and not parent.endswith("/moskovskaya-oblast/"):
            fail(errors, f"city parent is not oblast hub: {row['proposed_url']}")

    canon_urls = [row["url"] for row in canon]
    if canon_urls != urls:
        fail(errors, "canonical list does not match map order/content")

    inter = (ROOT / "profilactica_interlinking.md").read_text(encoding="utf-8")
    if FORBIDDEN.search(inter):
        fail(errors, "interlinking contains a technical geo catalog URL")
    old_bits = [
        "lechenie-alkogolizma/vyvod-iz-zapoya",
        "lechenie-alkogolizma/kodirovanie",
        "lechenie-alkogolizma/kapelnitsy",
        "narkologicheskaya-pomosh/narkolog-na-dom",
        "lechenie-narkomanii/snyatie-lomki",
    ]
    for bit in old_bits:
        if bit in inter:
            fail(errors, f"interlinking still describes old nesting: {bit}")
    for match in SITE_URL.finditer(inter):
        url = match.group(0)
        if not url.endswith("/"):
            url += "/"
        if url not in by_url:
            fail(errors, f"interlinking URL is not canonical: {url}")

    for path in [
        ROOT / "profilactica_competitor_report_content.md",
        ROOT / "konkurentnyy-analiz.md",
        ROOT / "index.html",
    ]:
        text = path.read_text(encoding="utf-8")
        blocks = FENCE.findall(text) + PRE.findall(text)
        for block in blocks:
            if FORBIDDEN.search(block):
                fail(errors, f"old geo catalog in example: {path.name}")
            for match in SITE_URL.finditer(block):
                url = match.group(0)
                if not url.endswith("/"):
                    url += "/"
                if url not in by_url:
                    fail(errors, f"example URL missing from CSV: {path.name} {url}")

    required = [
        "/uslugi/vyvod-iz-zapoya/",
        "/uslugi/vyvod-iz-zapoya/na-domu/moskva/belorusskaya/",
        "/uslugi/vyvod-iz-zapoya/na-domu/moskva/vao/",
        "/uslugi/vyvod-iz-zapoya/na-domu/moskovskaya-oblast/himki/",
        "/uslugi/kodirovanie/ukol/",
        "/uslugi/kodirovanie/preparaty/esperal/",
        "/uslugi/lechenie-alkogolizma/zhenskij-alkogolizm/",
        "/uslugi/lechenie-narkomanii/detoksikaciya/ubod/",
        "/uslugi/snyatie-lomki/",
        "/uslugi/narkolog-na-dom/",
    ]
    for url in required:
        if url not in by_url:
            fail(errors, f"required URL missing: {url}")

    services_with_moscow = {row["service"] for row in geo if row["geo_type"] in {"metro", "okrug"}}
    services_with_mo = {row["service"] for row in geo if row["geo_type"] == "mo"}
    hub_urls = {row["url"] for row in arch if row["url"].rstrip("/").endswith("/moskva") or row["url"].rstrip("/").endswith("/moskovskaya-oblast")}
    for service, spec in {
        "narkolog-na-dom": "/uslugi/narkolog-na-dom/",
        "vyvod-iz-zapoya": "/uslugi/vyvod-iz-zapoya/na-domu/",
        "ot-zapoya-i-alkogolya": "/uslugi/kapelnitsy/ot-zapoya-i-alkogolya/",
        "kodirovanie": "/uslugi/kodirovanie/",
        "psihiatr-na-dom": "/uslugi/psihiatriya/psihiatr-na-dom/",
    }.items():
        if service in services_with_moscow and spec + "moskva/" not in hub_urls:
            fail(errors, f"missing moscow hub: {service}")
    for service, spec in {
        "lechenie-alkogolizma": "/uslugi/lechenie-alkogolizma/na-domu/",
        "lechenie-narkomanii": "/uslugi/lechenie-narkomanii/",
        "reabilitaciya": "/uslugi/reabilitaciya/",
    }.items():
        if spec + "moskva/" in hub_urls:
            fail(errors, f"unexpected moscow hub: {service}")
        if service in services_with_mo and spec + "moskovskaya-oblast/" not in hub_urls:
            fail(errors, f"missing oblast hub: {service}")

    print(f"architecture {len(arch)}")
    print(f"geo {len(geo)}")
    print(f"map {len(mapping)}")
    print(f"relationships {len(rel)}")
    print(f"ambiguous {sum(1 for row in rel if row['notes'].strip())}")
    print(f"errors {len(errors)}")
    for message in errors:
        print("ERROR", message)
    return 1 if errors else 0


def mapping_parent(mapping, url):
    for row in mapping:
        if row["new_url"] == url:
            return row["new_parent"]
    return ""


if __name__ == "__main__":
    sys.exit(check())
