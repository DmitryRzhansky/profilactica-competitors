# -*- coding: utf-8 -*-
"""Remove the /moskva/ hub. Stations and okrugs hang off the service page."""
from __future__ import annotations

import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "profilactica_final_architecture.csv"
GEO = ROOT / "profilactica_geo_pages.csv"
MAP = ROOT / "profilactica_url_rearchitecture_map.csv"
CANON = ROOT / "profilactica_canonical_urls.csv"
DATA = ROOT / "assets" / "data"

PARENTS = {
    "/uslugi/narkolog-na-dom/",
    "/uslugi/vyvod-iz-zapoya/na-domu/",
    "/uslugi/kapelnitsy/ot-zapoya-i-alkogolya/",
    "/uslugi/kodirovanie/",
    "/uslugi/psihiatriya/psihiatr-na-dom/",
}
PSYCHIATRIST = "/uslugi/psihiatriya/psihiatr-na-dom/"
NOTE = (
    "Эта страница — родитель станций метро и округов Москвы. "
    "Отдельная страница Москвы не создаётся. "
    "Города Московской области стоят под moskovskaya-oblast."
)
NOTE_PSY = (
    "Эта страница — родитель округов Москвы. "
    "Отдельная страница Москвы не создаётся. "
    "Города Московской области стоят под moskovskaya-oblast."
)

OLD_EXAMPLE = """/uslugi/vyvod-iz-zapoya/na-domu/
/uslugi/vyvod-iz-zapoya/na-domu/moskva/
/uslugi/vyvod-iz-zapoya/na-domu/moskva/belorusskaya/
/uslugi/vyvod-iz-zapoya/na-domu/moskva/vao/
/uslugi/vyvod-iz-zapoya/na-domu/moskovskaya-oblast/
/uslugi/vyvod-iz-zapoya/na-domu/moskovskaya-oblast/himki/"""
NEW_EXAMPLE = """/uslugi/kodirovanie/
/uslugi/kodirovanie/belorusskaya/
/uslugi/kodirovanie/vao/
/uslugi/kodirovanie/moskovskaya-oblast/
/uslugi/kodirovanie/moskovskaya-oblast/himki/
/uslugi/vyvod-iz-zapoya/na-domu/belorusskaya/
/uslugi/vyvod-iz-zapoya/na-domu/vao/
/uslugi/vyvod-iz-zapoya/na-domu/moskovskaya-oblast/himki/"""
OLD_PROSE = (
    "Станция метро и административный округ стоят непосредственно под хабом Москвы. "
    "Город Московской области стоит под хабом области. "
    "В хлебных крошках нет пунктов «Метро», «Округа» и «Города». "
    "Хаб Москвы создаётся только если у услуги есть станции или округа. "
    "У лечения алкоголизма на дому, лечения наркомании и реабилитации есть только хаб Московской области."
)
NEW_PROSE = (
    "Станции метро и округа Москвы — прямые дочерние страницы услуги, без отдельного хаба Москвы. "
    "Города Московской области стоят под хабом области. "
    "В хлебных крошках нет пунктов «Метро», «Округа», «Города» и «Москва». "
    "У лечения алкоголизма на дому, лечения наркомании и реабилитации есть только хаб Московской области, "
    "потому что метро и округа для них не предусмотрены."
)
OLD_TZ = (
    "Станции и округа: `{услуга}/moskva/{slug}/`. Города: `{услуга}/moskovskaya-oblast/{slug}/`."
)
NEW_TZ = (
    "Станции и округа: `{услуга}/{slug}/` прямо под страницей услуги. "
    "Города: `{услуга}/moskovskaya-oblast/{slug}/`."
)
TREES = [
    (
        "├── narkolog-na-dom/\n│   ├── moskva/\n│   └── moskovskaya-oblast/",
        "├── narkolog-na-dom/\n│   ├── belorusskaya/\n│   ├── vao/\n│   └── moskovskaya-oblast/",
    ),
    (
        "│   ├── na-domu/\n│   │   ├── moskva/\n│   │   └── moskovskaya-oblast/",
        "│   ├── na-domu/\n│   │   ├── belorusskaya/\n│   │   ├── vao/\n│   │   └── moskovskaya-oblast/",
    ),
    (
        "│   ├── ot-zapoya-i-alkogolya/\n│   │   ├── moskva/\n│   │   └── moskovskaya-oblast/",
        "│   ├── ot-zapoya-i-alkogolya/\n│   │   ├── belorusskaya/\n│   │   ├── vao/\n│   │   └── moskovskaya-oblast/",
    ),
    (
        "├── kodirovanie/\n│   ├── moskva/\n│   ├── moskovskaya-oblast/",
        "├── kodirovanie/\n│   ├── belorusskaya/\n│   ├── vao/\n│   ├── moskovskaya-oblast/",
    ),
    (
        "│   ├── psihiatr-na-dom/\n│   │   ├── moskva/\n│   │   └── moskovskaya-oblast/",
        "│   ├── psihiatr-na-dom/\n│   │   ├── vao/\n│   │   └── moskovskaya-oblast/",
    ),
]


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return reader.fieldnames, list(reader)


def write_csv(path: Path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def is_hub(url: str) -> bool:
    return bool(url) and url.rstrip("/").endswith("/moskva")


def strip_moskva(url: str) -> str:
    return (url or "").replace("/moskva/", "/")


def md_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")


def markdown_table(headers, records):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append("| " + " | ".join(md_cell(record[key]) for key in headers) + " |")
    return "\n".join(lines)


def require(text: str, old: str, label: str) -> str:
    count = text.count(old)
    if count == 0:
        raise SystemExit(f"pattern not found: {label}")
    return text.replace(old, "")


def transform():
    arch_fields, arch = read_csv(ARCH)
    geo_fields, geo = read_csv(GEO)
    map_fields, mapping = read_csv(MAP)

    children = defaultdict(set)
    for row in arch:
        if is_hub(row["url"]) or not row["parent"]:
            continue
        children[row["parent"]].add(row["url"].rstrip("/").rsplit("/", 1)[-1])

    collisions = []
    for row in geo:
        if row["geo_type"] not in {"metro", "okrug"}:
            continue
        new_url = strip_moskva(row["proposed_url"])
        parent = new_url[: new_url.rstrip("/").rfind("/") + 1]
        if row["geo_slug"] in children[parent]:
            collisions.append(f"{new_url} collides under {parent}")
    if collisions:
        raise SystemExit("slug collision:\n" + "\n".join(collisions[:20]))

    kept = []
    for row in arch:
        if is_hub(row["url"]):
            continue
        if row["url"] in PARENTS:
            extra = NOTE_PSY if row["url"] == PSYCHIATRIST else NOTE
            if extra not in row["notes"]:
                row["notes"] = (row["notes"].rstrip() + " " + extra).strip()
        kept.append(row)
    if len(kept) != len(arch) - 5:
        raise SystemExit(f"expected to drop 5 hubs, dropped {len(arch) - len(kept)}")

    for row in geo:
        row["proposed_url"] = strip_moskva(row["proposed_url"])

    map_kept = []
    for row in mapping:
        if is_hub(row["new_url"]):
            continue
        row["new_url"] = strip_moskva(row["new_url"])
        row["new_parent"] = strip_moskva(row["new_parent"])
        map_kept.append(row)
    urls = [row["new_url"] for row in map_kept]
    dupes = [url for url, count in Counter(urls).items() if count > 1]
    if dupes:
        raise SystemExit(f"duplicate new_url after strip: {dupes[:8]}")

    write_csv(ARCH, arch_fields, kept)
    write_csv(GEO, geo_fields, geo)
    write_csv(MAP, map_fields, map_kept)
    write_csv(
        CANON,
        ["url", "entity_type", "silo", "page"],
        [
            {
                "url": row["new_url"],
                "entity_type": row["entity_type"],
                "silo": row["silo"],
                "page": row["page"],
            }
            for row in map_kept
        ],
    )
    return kept, geo


def patch_docs(arch_rows):
    counts = Counter(row["priority"] for row in arch_rows)
    total = len(arch_rows)
    sentence = (
        f"Полная таблица содержит **{total} страниц**: "
        f"{counts['P0']} P0, {counts['P1']} P1 и {counts['P2']} условных P2."
    )
    content_files = [
        ROOT / "profilactica_competitor_report_content.md",
        ROOT / "konkurentnyy-analiz.md",
        ROOT / "index.html",
    ]
    for path in content_files:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        for old, new in TREES:
            if text.count(old) != 1:
                raise SystemExit(f"{path.name}: tree fragment count {text.count(old)} for {old[:40]!r}")
            text = text.replace(old, new)
        if OLD_EXAMPLE not in text:
            raise SystemExit(f"{path.name}: geo example missing")
        text = text.replace(OLD_EXAMPLE, NEW_EXAMPLE)
        if OLD_PROSE not in text:
            raise SystemExit(f"{path.name}: geo prose missing")
        text = text.replace(OLD_PROSE, NEW_PROSE)
        text = re.sub(
            r"Полная таблица содержит \*\*\d+ страниц\*\*: \d+ P0, \d+ P1 и \d+ условных P2\.",
            sentence,
            text,
        )
        text = re.sub(
            r"\d+ страниц архитектуры уже приведены",
            f"{total} страниц архитектуры уже приведены",
            text,
        )
        path.write_text(text, encoding="utf-8", newline="\n")

    tz = ROOT / "profilactica_coding_agent_tz.md"
    tz_text = tz.read_text(encoding="utf-8").replace("\r\n", "\n")
    if OLD_TZ not in tz_text:
        raise SystemExit("tz url rule missing")
    tz_text = tz_text.replace(OLD_TZ, NEW_TZ)
    tz_text = tz_text.replace(
        "- 189 страниц в финальной архитектуре;",
        f"- {total} страниц в финальной архитектуре;",
    )
    tz_text = tz_text.replace(
        "3. Все 189 строк архитектуры загружаются.",
        f"3. Все {total} строк архитектуры загружаются.",
    )
    tz.write_text(tz_text, encoding="utf-8", newline="\n")


def patch_analysis(arch_rows, geo_rows):
    analysis = ROOT / "konkurentnyy-analiz.md"
    text = analysis.read_text(encoding="utf-8")
    arch_md = markdown_table(
        ["SILO", "Страница", "URL", "Родитель", "Приоритет", "Статус", "ГЕО-политика", "Примечания"],
        [
            {
                "SILO": row["silo"],
                "Страница": row["page"],
                "URL": row["url"],
                "Родитель": row["parent"],
                "Приоритет": row["priority"],
                "Статус": row["status"],
                "ГЕО-политика": row["geo_policy"],
                "Примечания": row["notes"],
            }
            for row in arch_rows
        ],
    )
    start = text.find("### Полный каталог финальной архитектуры")
    end = text.find("\n# 7. Какие новые")
    if start < 0 or end < 0:
        raise SystemExit("architecture table markers missing")
    text = text[:start] + "### Полный каталог финальной архитектуры\n\n" + arch_md + "\n" + text[end:]

    inter = (ROOT / "profilactica_interlinking.md").read_text(encoding="utf-8")
    start = text.find("# Полная схема внутренней перелинковки")
    end = text.find("\n# 11. Обязательные блоки")
    if start < 0 or end < 0:
        raise SystemExit("interlinking markers missing")
    text = text[:start] + inter.strip() + "\n" + text[end:]

    table = markdown_table(
        ["Услуга", "Тип", "Локация", "Slug", "Tier", "Приоритет", "Действие", "URL"],
        [
            {
                "Услуга": row["service_name"],
                "Тип": row["geo_type"],
                "Локация": row["geo_name"],
                "Slug": row["geo_slug"],
                "Tier": row["tier"],
                "Приоритет": row["priority"],
                "Действие": row["action"],
                "URL": row["proposed_url"],
            }
            for row in geo_rows
        ],
    )
    start = text.find("## Полный каталог запланированных ГЕО URL")
    end = text.find("\n## Сводный список локаций")
    if start < 0 or end < 0:
        raise SystemExit("geo table markers missing")
    heading = f"## Полный каталог запланированных ГЕО URL ({len(geo_rows)} URL)"
    text = text[:start] + heading + "\n\n" + table + "\n" + text[end:]
    analysis.write_text(text, encoding="utf-8", newline="\n")


def refresh_embed():
    embed_path = DATA / "embedded.js"
    raw = embed_path.read_text(encoding="utf-8")
    prefix = "window.__REPORT_EMBED__ = "
    if not raw.startswith(prefix):
        raise SystemExit("unexpected embedded.js prefix")
    payload = json.loads(raw[len(prefix) :].strip().rstrip(";"))
    payload["architecture"] = ARCH.read_text(encoding="utf-8")
    payload["geoPages"] = GEO.read_text(encoding="utf-8")
    payload["geoMaster"] = (ROOT / "profilactica_geo_master_lists.csv").read_text(encoding="utf-8")
    embed_path.write_text(prefix + json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    shutil.copy2(ARCH, DATA / "architecture.csv")
    shutil.copy2(GEO, DATA / "geo-pages.csv")
    shutil.copy2(ROOT / "profilactica_geo_master_lists.csv", DATA / "geo-master.csv")


def main():
    arch_rows, geo_rows = transform()
    patch_docs(arch_rows)
    patch_analysis(arch_rows, geo_rows)
    refresh_embed()
    print(f"architecture {len(arch_rows)}")
    print(f"geo {len(geo_rows)}")
    print("p0", sum(1 for row in arch_rows if row["priority"] == "P0"))


if __name__ == "__main__":
    main()
