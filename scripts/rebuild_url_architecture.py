# -*- coding: utf-8 -*-
"""Rebuild SILO URLs and GEO paths. One-shot: refuses to run twice."""
from __future__ import annotations

import csv
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from metro_okrugs import GROUPS, NOTES, OKRUG_NEIGHBORS, OKRUGS, assignment

ROOT = Path(__file__).resolve().parents[1]
ARCH = ROOT / "profilactica_final_architecture.csv"
GEO = ROOT / "profilactica_geo_pages.csv"
MASTER = ROOT / "profilactica_geo_master_lists.csv"
REL = ROOT / "profilactica_geo_relationships.csv"
NEI = ROOT / "profilactica_geo_okrug_neighbors.csv"
MAP = ROOT / "profilactica_url_rearchitecture_map.csv"
CANON = ROOT / "profilactica_canonical_urls.csv"
DATA = ROOT / "assets" / "data"

ARCH_FIELDS = ["silo", "page", "url", "parent", "priority", "status", "geo_policy", "notes"]
GEO_FIELDS = [
    "service",
    "service_name",
    "geo_type",
    "geo_name",
    "geo_slug",
    "tier",
    "proposed_url",
    "priority",
    "action",
]
MAP_FIELDS = [
    "page",
    "old_plan_url",
    "new_url",
    "old_parent",
    "new_parent",
    "silo",
    "entity_type",
    "geo_enabled",
    "geo_region",
    "geo_type",
    "geo_slug",
    "priority",
    "notes",
]

PROMOTIONS = [
    (
        "/uslugi/narkologicheskaya-pomosh/narkolog-na-dom/",
        "/uslugi/narkolog-na-dom/",
        "Нарколог на дом",
        "Самостоятельная пользовательская задача: выезд нарколога. Это не формат хаба «Наркологическая помощь» и не дубль вывода из запоя, капельницы или кодирования.",
    ),
    (
        "/uslugi/lechenie-alkogolizma/vyvod-iz-zapoya/",
        "/uslugi/vyvod-iz-zapoya/",
        "Вывод из запоя",
        "Самостоятельная острая задача, а не сегмент лечения алкоголизма. Форматы на дому и в стационаре остаются дочерними.",
    ),
    (
        "/uslugi/lechenie-alkogolizma/kapelnitsy/",
        "/uslugi/kapelnitsy/",
        "Капельницы и детокс",
        "Самостоятельная задача детокса и капельницы. Алкогольная детоксикация, похмелье и абстинентный синдром остаются внутри этого SILO. Детоксикация от наркотиков не переносится, чтобы не дублировать SILO.",
    ),
    (
        "/uslugi/lechenie-alkogolizma/kodirovanie/",
        "/uslugi/kodirovanie/",
        "Кодирование",
        "Самостоятельная коммерческая задача. Методы, препараты и раскодирование остаются дочерними. ГЕО только у общего хаба кодирования.",
    ),
    (
        "/uslugi/lechenie-narkomanii/snyatie-lomki/",
        "/uslugi/snyatie-lomki/",
        "Снятие ломки",
        "Самостоятельная острая задача, аналог вывода из запоя. Форматы на дому и в стационаре остаются дочерними. УБОД остаётся внутри детоксикации от наркотиков. Отдельная ГЕО-матрица не создаётся.",
    ),
]

HUB_REWRITES = {
    "/uslugi/lechenie-narkomanii/mo/": "/uslugi/lechenie-narkomanii/moskovskaya-oblast/",
    "/uslugi/reabilitaciya/mo/": "/uslugi/reabilitaciya/moskovskaya-oblast/",
}

HUB_PAGE_NAMES = {
    "/uslugi/lechenie-narkomanii/moskovskaya-oblast/": "Лечение наркомании — Московская область",
    "/uslugi/reabilitaciya/moskovskaya-oblast/": "Реабилитация — Московская область",
}

SILO_ORDER = [
    "Наркологическая помощь",
    "Нарколог на дом",
    "Вывод из запоя",
    "Капельницы и детокс",
    "Кодирование",
    "Лечение алкоголизма",
    "Снятие ломки",
    "Лечение наркомании",
    "Другие зависимости",
    "Реабилитация",
    "Психиатрия",
    "Психотерапия и психология",
    "Помощь родственникам",
    "Диагностика",
    "Восстановительная терапия",
    "Trust / выбор",
]

GEO_OWNERS = {
    "narkolog-na-dom": {
        "base": "/uslugi/narkolog-na-dom/",
        "silo": "Нарколог на дом",
        "service_name": "Нарколог на дом",
        "types": {"metro", "okrug", "mo"},
        "mo": "all",
    },
    "vyvod-iz-zapoya": {
        "base": "/uslugi/vyvod-iz-zapoya/na-domu/",
        "silo": "Вывод из запоя",
        "service_name": "Вывод из запоя на дому",
        "types": {"metro", "okrug", "mo"},
        "mo": "all",
    },
    "ot-zapoya-i-alkogolya": {
        "base": "/uslugi/kapelnitsy/ot-zapoya-i-alkogolya/",
        "silo": "Капельницы и детокс",
        "service_name": "Капельница от запоя и алкоголя на дому",
        "types": {"metro", "okrug", "mo"},
        "mo": "all",
    },
    "kodirovanie": {
        "base": "/uslugi/kodirovanie/",
        "silo": "Кодирование",
        "service_name": "Кодирование от алкоголизма",
        "types": {"metro", "okrug", "mo"},
        "mo": "all",
    },
    "psihiatr-na-dom": {
        "base": "/uslugi/psihiatriya/psihiatr-na-dom/",
        "silo": "Психиатрия",
        "service_name": "Психиатр на дом",
        "types": {"okrug", "mo"},
        "mo": "all",
    },
    "lechenie-alkogolizma": {
        "base": "/uslugi/lechenie-alkogolizma/na-domu/",
        "silo": "Лечение алкоголизма",
        "service_name": "Лечение алкоголизма на дому",
        "types": {"mo"},
        "mo": "tier-1",
    },
    "lechenie-narkomanii": {
        "base": "/uslugi/lechenie-narkomanii/",
        "silo": "Лечение наркомании",
        "service_name": "Лечение наркомании",
        "types": {"mo"},
        "mo": "tier-1",
    },
    "reabilitaciya": {
        "base": "/uslugi/reabilitaciya/",
        "silo": "Реабилитация",
        "service_name": "Реабилитация зависимых",
        "types": {"mo"},
        "mo": "tier-1",
    },
}

NEW_TREE = """/uslugi/
├── narkologicheskaya-pomosh/
│   ├── konsultaciya-narkologa/
│   ├── psihiatr-narkolog/
│   ├── stacionar/
│   ├── gospitalizaciya/
│   └── chastnyj-vytrezvitel/
│
├── narkolog-na-dom/
│   ├── moskva/
│   └── moskovskaya-oblast/
│
├── vyvod-iz-zapoya/
│   ├── na-domu/
│   │   ├── moskva/
│   │   └── moskovskaya-oblast/
│   └── v-stacionare/
│
├── kapelnitsy/
│   ├── ot-zapoya-i-alkogolya/
│   │   ├── moskva/
│   │   └── moskovskaya-oblast/
│   ├── ot-pohmelya/
│   └── abstinentnyj-sindrom/
│
├── kodirovanie/
│   ├── moskva/
│   ├── moskovskaya-oblast/
│   ├── na-domu/
│   ├── metod-dovzhenko/
│   ├── ukol/
│   ├── preparaty/
│   └── raskodirovanie/
│
├── lechenie-alkogolizma/
│   ├── na-domu/
│   │   └── moskovskaya-oblast/
│   ├── v-stacionare/
│   ├── ambulatorno/
│   ├── zhenskij-alkogolizm/
│   ├── pivnoj-alkogolizm/
│   └── bez-kodirovaniya/
│
├── snyatie-lomki/
│   ├── na-domu/
│   └── v-stacionare/
│
├── lechenie-narkomanii/
│   ├── moskovskaya-oblast/
│   ├── detoksikaciya/
│   │   └── ubod/
│   ├── v-stacionare/
│   └── geroin/
│
├── drugie-zavisimosti/
│   ├── igromaniya/
│   ├── stavki/
│   ├── kompyuternaya/
│   ├── internet/
│   ├── nikotinovaya/
│   ├── toksikomaniya/
│   └── lekarstvennaya/
│       ├── pregabalin/
│       ├── benzodiazepiny/
│       ├── fenazepam/
│       ├── tramadol/
│       ├── kodein/
│       └── antidepressanty/
│
├── reabilitaciya/
│   ├── moskovskaya-oblast/
│   ├── alkogolizm/
│   ├── narkomaniya/
│   ├── igromaniya/
│   ├── 12-shagov/
│   └── resocializaciya/
│
├── psihiatriya/
│   ├── konsultaciya/
│   ├── psihiatr-na-dom/
│   │   ├── moskva/
│   │   └── moskovskaya-oblast/
│   ├── stacionar/
│   ├── trevozhnye-i-stressovye-rasstrojstva/
│   ├── rasstrojstva-nastroeniya/
│   ├── psihoticheskie-rasstrojstva/
│   ├── rasstrojstva-lichnosti-i-povedeniya/
│   ├── rasstrojstva-pishchevogo-povedeniya/
│   ├── kognitivnye-i-organicheskie/
│   └── rasstrojstva-sna/
│
├── psihoterapiya-i-psihologiya/
├── pomoshch-rodstvennikam/
├── diagnostika/
└── vosstanovitelnaya-terapiya/"""

OLD_TREE_START = "/uslugi/\n├── narkologicheskaya-pomosh/\n│   ├── narkolog-na-dom/"
TREE_END = "└── vosstanovitelnaya-terapiya/"

OLD_GEO = """/uslugi/narkologicheskaya-pomosh/narkolog-na-dom/metro/belorusskaya/
/uslugi/narkologicheskaya-pomosh/narkolog-na-dom/okrug/cao/
/uslugi/narkologicheskaya-pomosh/narkolog-na-dom/mo/korolev/"""

NEW_GEO = """/uslugi/vyvod-iz-zapoya/na-domu/
/uslugi/vyvod-iz-zapoya/na-domu/moskva/
/uslugi/vyvod-iz-zapoya/na-domu/moskva/belorusskaya/
/uslugi/vyvod-iz-zapoya/na-domu/moskva/vao/
/uslugi/vyvod-iz-zapoya/na-domu/moskovskaya-oblast/
/uslugi/vyvod-iz-zapoya/na-domu/moskovskaya-oblast/himki/"""

OLD_MODEL = """/uslugi/lechenie-alkogolizma/
/uslugi/lechenie-alkogolizma/kodirovanie/
/uslugi/lechenie-alkogolizma/kodirovanie/metod-dovzhenko/"""

NEW_MODEL = """/uslugi/vyvod-iz-zapoya/
/uslugi/vyvod-iz-zapoya/na-domu/
/uslugi/kodirovanie/
/uslugi/kodirovanie/ukol/
/uslugi/lechenie-alkogolizma/zhenskij-alkogolizm/"""

FORBIDDEN_URL = re.compile(r"/(?:metro|okrug|mo)(?:/|$)")
SITE_URL = re.compile(r"/(?:uslugi|o-klinike|pomoshch|ceny|vrachi)/[a-z0-9\-/]*")


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def parent_path(url: str) -> str:
    parts = [part for part in url.strip("/").split("/") if part]
    if len(parts) <= 1:
        return "/"
    return "/" + "/".join(parts[:-1]) + "/"


def rewrite_prefix(value: str) -> str:
    for old, new, _silo, _reason in PROMOTIONS:
        if value.startswith(old):
            return new + value[len(old) :]
    return value


def silo_for(url: str, current: str) -> str:
    matches = [(new, silo) for _old, new, silo, _reason in PROMOTIONS if url.startswith(new)]
    if not matches:
        return current
    new, silo = max(matches, key=lambda item: len(item[0]))
    return silo


def reason_for(url: str) -> str:
    for _old, new, _silo, reason in PROMOTIONS:
        if url == new:
            return reason
    return ""


def join_notes(*parts: str) -> str:
    items = []
    for part in parts:
        text = (part or "").strip()
        if text and text not in items:
            items.append(text)
    return " ".join(items)


def geo_url(base: str, geo_type: str, slug: str) -> str:
    if geo_type in {"metro", "okrug"}:
        return f"{base}moskva/{slug}/"
    if geo_type == "mo":
        return f"{base}moskovskaya-oblast/{slug}/"
    raise ValueError(geo_type)


def hub_url(base: str, region: str) -> str:
    return f"{base}{region}/"


def is_hub(url: str) -> bool:
    return url.rstrip("/").endswith("/moskva") or url.rstrip("/").endswith("/moskovskaya-oblast")


def transform_architecture(rows):
    transformed = []
    originals = []
    for row in rows:
        old_url = row["url"]
        old_parent = row["parent"]
        notes = row["notes"].replace("/kodirovanie/", "/uslugi/kodirovanie/")
        url = HUB_REWRITES.get(rewrite_prefix(old_url), rewrite_prefix(old_url))
        parent = rewrite_prefix(old_parent)
        parent = HUB_REWRITES.get(parent, parent)
        if reason_for(url):
            parent = "/uslugi/"
        if not (parent or "").strip():
            parent = "/"
        silo = silo_for(url, row["silo"])
        page = HUB_PAGE_NAMES.get(url, row["page"])
        extra = reason_for(url)
        if url in HUB_PAGE_NAMES:
            extra = join_notes(
                extra,
                "Индексируемый GEO-хаб Московской области. Технический каталог области убран из URL. Это родитель городских страниц.",
            )
        transformed.append(
            {
                "silo": silo,
                "page": page,
                "url": url,
                "parent": parent,
                "priority": row["priority"],
                "status": row["status"],
                "geo_policy": row["geo_policy"],
                "notes": join_notes(notes, extra),
            }
        )
        originals.append((old_url, old_parent))
    return transformed, originals


def add_hubs(rows):
    existing = {row["url"] for row in rows}
    by_url = {row["url"]: row for row in rows}
    out = []
    for row in rows:
        out.append(row)
        owner = next((item for item in GEO_OWNERS.values() if item["base"] == row["url"]), None)
        if not owner:
            continue
        regions = []
        if "metro" in owner["types"] or "okrug" in owner["types"]:
            regions.append("moskva")
        if "mo" in owner["types"]:
            regions.append("moskovskaya-oblast")
        for region in regions:
            url = hub_url(owner["base"], region)
            if url in existing:
                continue
            title = "Москва" if region == "moskva" else "Московская область"
            note = (
                "Индексируемый GEO-хаб. Родитель станций метро и административных округов. Станция и округ — параллельные URL, округ не становится родителем станции."
                if region == "moskva"
                else "Индексируемый GEO-хаб. Родитель городов Московской области. Станции метро и округа Москвы сюда не входят."
            )
            if owner["mo"] == "tier-1" and region == "moskovskaya-oblast":
                note += " Только 30 городов tier-1."
            hub = {
                "silo": owner["silo"],
                "page": f"{owner['service_name']} — {title}",
                "url": url,
                "parent": owner["base"],
                "priority": row["priority"],
                "status": row["status"],
                "geo_policy": f"Хаб ГЕО: {title}",
                "notes": note,
            }
            out.append(hub)
            existing.add(url)
            by_url[url] = hub
    order = {name: index for index, name in enumerate(SILO_ORDER)}
    indexed = list(enumerate(out))
    indexed.sort(key=lambda item: (order.get(item[1]["silo"], 99), item[0]))
    return [row for _index, row in indexed]


def transform_geo(rows, master_mo_tier):
    rewritten = []
    for row in rows:
        owner = GEO_OWNERS.get(row["service"])
        if owner is None:
            raise SystemExit(f"GEO service is not allowed: {row['service']}")
        if row["geo_type"] not in owner["types"]:
            raise SystemExit(f"GEO type {row['geo_type']} is not allowed for {row['service']}")
        if row["geo_type"] == "mo" and owner["mo"] == "tier-1":
            if master_mo_tier.get(row["geo_slug"]) != "tier-1":
                raise SystemExit(f"non tier-1 city on limited service: {row['service']} {row['geo_slug']}")
        old = row["proposed_url"]
        new = geo_url(owner["base"], row["geo_type"], row["geo_slug"])
        rewritten.append(
            {
                **row,
                "service_name": owner["service_name"],
                "proposed_url": new,
                "_old": old,
            }
        )
    return rewritten


def write_relationships(master):
    mapping = assignment()
    metros = [row for row in master if row["geo_type"] == "metro"]
    missing = [row["slug"] for row in metros if row["slug"] not in mapping]
    extra = sorted(set(mapping) - {row["slug"] for row in metros})
    if missing or extra:
        raise SystemExit(f"metro assignment mismatch missing={missing} extra={extra}")
    rows = []
    for row in metros:
        slug = row["slug"]
        okrug_slug = mapping[slug]
        rows.append(
            {
                "metro_name": row["name"],
                "metro_slug": slug,
                "okrug_name": OKRUGS[okrug_slug],
                "okrug_slug": okrug_slug,
                "canonical_okrug": OKRUGS[okrug_slug],
                "notes": NOTES.get(slug, ""),
            }
        )
    write_csv(
        REL,
        ["metro_name", "metro_slug", "okrug_name", "okrug_slug", "canonical_okrug", "notes"],
        rows,
    )
    write_csv(
        NEI,
        ["okrug_slug", "neighbor_okrug_slug", "rank", "kind", "notes"],
        [
            {
                "okrug_slug": left,
                "neighbor_okrug_slug": right,
                "rank": str(rank),
                "kind": kind,
                "notes": "ЗелАО — анклав без общей границы; для перелинковки оставлена одна связанная страница СЗАО."
                if kind == "practical"
                else "",
            }
            for left, right, rank, kind in OKRUG_NEIGHBORS
        ],
    )
    return rows


def arch_entity(row):
    if is_hub(row["url"]):
        return "geo-hub"
    if row["silo"].startswith("Trust"):
        return "trust"
    if row["parent"] == "/uslugi/":
        return "silo-root"
    return "child"


def geo_enabled_arch(row):
    if is_hub(row["url"]):
        return "yes"
    return "yes" if row["url"] in {item["base"] for item in GEO_OWNERS.values()} else "no"


def hub_geo_fields(url):
    if url.rstrip("/").endswith("/moskva"):
        return "moskva", "hub", "moskva"
    if url.rstrip("/").endswith("/moskovskaya-oblast"):
        return "moskovskaya-oblast", "hub", "moskovskaya-oblast"
    return "", "", ""


def build_map(arch_rows, originals, geo_rows):
    rows = [
        {
            "page": "Главная",
            "old_plan_url": "/",
            "new_url": "/",
            "old_parent": "",
            "new_parent": "",
            "silo": "Сайт",
            "entity_type": "structural",
            "geo_enabled": "no",
            "geo_region": "",
            "geo_type": "",
            "geo_slug": "",
            "priority": "",
            "notes": "Корень сайта. Единственная страница карты без родителя.",
        },
        {
            "page": "Услуги",
            "old_plan_url": "/uslugi/",
            "new_url": "/uslugi/",
            "old_parent": "/",
            "new_parent": "/",
            "silo": "Каталог",
            "entity_type": "structural",
            "geo_enabled": "no",
            "geo_region": "",
            "geo_type": "",
            "geo_slug": "",
            "priority": "",
            "notes": "Каталог услуг. Родитель SILO первого уровня. Не отдельная коммерческая посадочная семантического ядра.",
        },
    ]
    for row, (old_url, old_parent) in zip(arch_rows, originals, strict=True):
        region, geo_type, geo_slug = hub_geo_fields(row["url"])
        old_parent_value = old_parent or "/"
        if not old_parent.strip():
            old_parent_value = "/"
        rows.append(
            {
                "page": row["page"],
                "old_plan_url": old_url,
                "new_url": row["url"],
                "old_parent": old_parent_value,
                "new_parent": row["parent"],
                "silo": row["silo"],
                "entity_type": arch_entity(row),
                "geo_enabled": geo_enabled_arch(row),
                "geo_region": region,
                "geo_type": geo_type,
                "geo_slug": geo_slug,
                "priority": row["priority"],
                "notes": row["notes"],
            }
        )
    # Hubs inserted after the paired originals, so zip above is wrong if len differs.
    return rows


def build_map_fixed(arch_rows, paired_originals, geo_rows):
    """paired_originals aligns with architecture rows before hub insertion."""
    original_by_new = {}
    # Recompute pairing by walking promotions on stored originals inside notes? 
    # The caller passes a list of (old_url, old_parent) only for pre-hub rows.
    pre_hub = [row for row in arch_rows if row["url"] not in {item["url"] for item in []}]
    return build_map(pre_hub, paired_originals, geo_rows)


def assemble_map(base_rows, base_originals, final_rows, geo_rows):
    original_by_old = {old: parent for old, parent in base_originals}
    new_by_old_url = {}
    for row, (old_url, _parent) in zip(base_rows, base_originals, strict=True):
        new_by_old_url[row["url"]] = (old_url, original_by_old[old_url])

    rows = [
        {
            "page": "Главная",
            "old_plan_url": "/",
            "new_url": "/",
            "old_parent": "",
            "new_parent": "",
            "silo": "Сайт",
            "entity_type": "structural",
            "geo_enabled": "no",
            "geo_region": "",
            "geo_type": "",
            "geo_slug": "",
            "priority": "",
            "notes": "Корень сайта. Единственная страница карты без родителя.",
        },
        {
            "page": "Услуги",
            "old_plan_url": "/uslugi/",
            "new_url": "/uslugi/",
            "old_parent": "/",
            "new_parent": "/",
            "silo": "Каталог",
            "entity_type": "structural",
            "geo_enabled": "no",
            "geo_region": "",
            "geo_type": "",
            "geo_slug": "",
            "priority": "",
            "notes": "Каталог услуг. Родитель SILO первого уровня. Не отдельная коммерческая посадочная семантического ядра.",
        },
    ]
    for row in final_rows:
        if row["url"] in new_by_old_url:
            old_url, old_parent = new_by_old_url[row["url"]]
            old_parent_value = old_parent if old_parent.strip() else "/"
            note = row["notes"]
        else:
            old_url = ""
            old_parent_value = ""
            note = join_notes(row["notes"], "Новый индексируемый GEO-хаб. В прежней схеме отдельной страницы региона не было.")
        region, geo_type, geo_slug = hub_geo_fields(row["url"])
        rows.append(
            {
                "page": row["page"],
                "old_plan_url": old_url,
                "new_url": row["url"],
                "old_parent": old_parent_value,
                "new_parent": row["parent"],
                "silo": row["silo"],
                "entity_type": arch_entity(row),
                "geo_enabled": geo_enabled_arch(row),
                "geo_region": region,
                "geo_type": geo_type,
                "geo_slug": geo_slug,
                "priority": row["priority"],
                "notes": note,
            }
        )
    for row in geo_rows:
        owner = GEO_OWNERS[row["service"]]
        if row["geo_type"] in {"metro", "okrug"}:
            region = "moskva"
            parent = hub_url(owner["base"], "moskva")
        else:
            region = "moskovskaya-oblast"
            parent = hub_url(owner["base"], "moskovskaya-oblast")
        rows.append(
            {
                "page": f"{row['service_name']} — {row['geo_name']}",
                "old_plan_url": row["_old"],
                "new_url": row["proposed_url"],
                "old_parent": parent_path(row["_old"]),
                "new_parent": parent,
                "silo": owner["silo"],
                "entity_type": row["geo_type"] if row["geo_type"] != "mo" else "city",
                "geo_enabled": "yes",
                "geo_region": region,
                "geo_type": row["geo_type"],
                "geo_slug": row["geo_slug"],
                "priority": row["priority"],
                "notes": "Технический каталог metro, okrug или mo убран из публичного URL."
                if row["geo_type"] in {"metro", "okrug", "mo"}
                else "",
            }
        )
    return rows


def md_cell(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")


def markdown_table(headers, records):
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for record in records:
        lines.append("| " + " | ".join(md_cell(record[key]) for key in record) + " |")
    return "\n".join(lines)


def replace_once(text, old, new, label):
    count = text.count(old)
    if count == 0:
        raise SystemExit(f"pattern not found: {label}")
    return text.replace(old, new)


def replace_tree(text):
    if OLD_TREE_START not in text:
        return text
    start = text.find(OLD_TREE_START)
    end = text.find(TREE_END, start)
    if end < 0:
        raise SystemExit("tree end not found")
    end += len(TREE_END)
    return text[:start] + NEW_TREE + text[end:]


def patch_text(text, arch_count_line):
    text = text.replace("\r\n", "\n")
    while OLD_TREE_START in text:
        text = replace_tree(text)
    if OLD_GEO in text:
        text = text.replace(OLD_GEO, NEW_GEO)
    if OLD_MODEL in text:
        text = text.replace(OLD_MODEL, NEW_MODEL)
    text = text.replace(
        "а не десятки независимых URL непосредственно в `/uslugi/`.",
        "Самостоятельная задача пользователя стоит на первом уровне `/uslugi/`. Метод, препарат и сегмент остаются внутри своего SILO. Каталог при этом не становится плоским списком.",
    )
    text = text.replace(
        "а не десятки независимых URL непосредственно в <code>/uslugi/</code>.",
        "Самостоятельная задача пользователя стоит на первом уровне <code>/uslugi/</code>. Метод, препарат и сегмент остаются внутри своего SILO. Каталог при этом не становится плоским списком.",
    )
    principle = "Один запрос — один основной URL."
    addition = " Самостоятельная коммерческая задача — отдельный SILO первого уровня. Метод, формат, препарат, сегмент и диагноз остаются дочерними страницами своего SILO."
    if principle in text and addition not in text:
        text = text.replace(principle, principle + addition)
    geo_note = (
        "Станция метро и административный округ стоят непосредственно под хабом Москвы. "
        "Город Московской области стоит под хабом области. "
        "В хлебных крошках нет пунктов «Метро», «Округа» и «Города». "
        "Хаб Москвы создаётся только если у услуги есть станции или округа. "
        "У лечения алкоголизма на дому, лечения наркомании и реабилитации есть только хаб Московской области.\n\n"
    )
    for heading in ("## Основная матрица — 4 услуги", "## Основная матрица - 4 услуги", "<h3>Основная матрица - 4 услуги</h3>"):
        token = heading
        if token in text and "административный округ стоят непосредственно" not in text.split(token)[0][-400:]:
            text = text.replace(token, geo_note + token, 1)
    text = text.replace(
        "- Лечение алкоголизма: 30 основных городов МО = 30 страниц.",
        "- Лечение алкоголизма на дому: 30 основных городов МО = 30 страниц. У общего хаба лечения алкоголизма своей GEO-матрицы нет.",
    )
    text = text.replace(
        "<li>Лечение алкоголизма: 30 основных городов МО = 30 страниц.</li>",
        "<li>Лечение алкоголизма на дому: 30 основных городов МО = 30 страниц. У общего хаба лечения алкоголизма своей GEO-матрицы нет.</li>",
    )
    text = text.replace(
        "| Лечение алкоголизма | 0 | 0 | 30 | 30 |",
        "| Лечение алкоголизма на дому | 0 | 0 | 30 | 30 |",
    )
    text = text.replace(
        "| Лечение алкоголизма | Города МО | 30 |",
        "| Лечение алкоголизма на дому | Города МО | 30 |",
    )
    text = re.sub(
        r"Полная таблица содержит \*\*\d+ страниц\*\*: \d+ P0, \d+ P1 и \d+ условных P2\.",
        arch_count_line,
        text,
    )
    text = re.sub(
        r"\d+ страниц архитектуры уже приведены",
        arch_count_line.split("**")[1].split()[0] + " страниц архитектуры уже приведены"
        if False
        else None or "PLACEHOLDER",
        text,
    )
    return text


def patch_docs(arch_rows):
    counts = Counter(row["priority"] for row in arch_rows)
    total = len(arch_rows)
    sentence = (
        f"Полная таблица содержит **{total} страниц**: {counts['P0']} P0, {counts['P1']} P1 и {counts['P2']} условных P2."
    )
    files = [
        ROOT / "profilactica_competitor_report_content.md",
        ROOT / "konkurentnyy-analiz.md",
        ROOT / "index.html",
        ROOT / "profilactica_coding_agent_tz.md",
    ]
    for path in files:
        text = path.read_text(encoding="utf-8")
        text = text.replace("\r\n", "\n")
        while OLD_TREE_START in text:
            text = replace_tree(text)
        text = text.replace(OLD_GEO, NEW_GEO)
        text = text.replace(OLD_MODEL, NEW_MODEL)
        text = text.replace(
            "а не десятки независимых URL непосредственно в `/uslugi/`.",
            "Самостоятельная задача пользователя стоит на первом уровне `/uslugi/`. Метод, препарат и сегмент остаются внутри своего SILO. Каталог при этом не становится плоским списком.",
        )
        text = text.replace(
            "а не десятки независимых URL непосредственно в <code>/uslugi/</code>.",
            "Самостоятельная задача пользователя стоит на первом уровне <code>/uslugi/</code>. Метод, препарат и сегмент остаются внутри своего SILO. Каталог при этом не становится плоским списком.",
        )
        principle = "Один запрос — один основной URL."
        addition = " Самостоятельная коммерческая задача — отдельный SILO первого уровня. Метод, формат, препарат, сегмент и диагноз остаются дочерними страницами своего SILO."
        if principle in text and addition.strip() not in text:
            text = text.replace(principle, principle + addition)
        if "административный округ стоят непосредственно" not in text:
            note = (
                "Станция метро и административный округ стоят непосредственно под хабом Москвы. "
                "Город Московской области стоит под хабом области. "
                "В хлебных крошках нет пунктов «Метро», «Округа» и «Города». "
                "Хаб Москвы создаётся только если у услуги есть станции или округа. "
                "У лечения алкоголизма на дому, лечения наркомании и реабилитации есть только хаб Московской области.\n\n"
            )
            for heading in (
                "## Основная матрица — 4 услуги",
                "<h3>Основная матрица - 4 услуги</h3>",
            ):
                if heading in text:
                    text = text.replace(heading, note + heading, 1)
                    break
        text = text.replace(
            "- Лечение алкоголизма: 30 основных городов МО = 30 страниц.",
            "- Лечение алкоголизма на дому: 30 основных городов МО = 30 страниц. У общего хаба лечения алкоголизма своей GEO-матрицы нет.",
        )
        text = text.replace(
            "<li>Лечение алкоголизма: 30 основных городов МО = 30 страниц.</li>",
            "<li>Лечение алкоголизма на дому: 30 основных городов МО = 30 страниц. У общего хаба лечения алкоголизма своей GEO-матрицы нет.</li>",
        )
        text = text.replace(
            "| Лечение алкоголизма | 0 | 0 | 30 | 30 |",
            "| Лечение алкоголизма на дому | 0 | 0 | 30 | 30 |",
        )
        text = text.replace(
            "| Лечение алкоголизма | Города МО | 30 |",
            "| Лечение алкоголизма на дому | Города МО | 30 |",
        )
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
        text = text.replace(
            "- 175 страниц в финальной архитектуре;",
            f"- {total} страниц в финальной архитектуре;",
        )
        text = text.replace(
            "3. Все 175 строк архитектуры загружаются.",
            f"3. Все {total} строк архитектуры загружаются.",
        )
        path.write_text(text, encoding="utf-8", newline="\n")

    report = ROOT / "profilactica_competitor_report_content.md"
    report_text = report.read_text(encoding="utf-8")
    extra = (
        "- `profilactica_geo_relationships.csv` — станция метро → один канонический округ Москвы.\n"
        "- `profilactica_geo_okrug_neighbors.csv` — соседние округа для перелинковки.\n"
        "- `profilactica_url_rearchitecture_map.csv` — old plan URL → canonical URL для переноса конфигурации. Это не таблица 301.\n"
        "- `profilactica_canonical_urls.csv` — все canonical URL новой архитектуры.\n"
    )
    needle = "- `profilactica_geo_master_lists.csv` — 215 метро/узлов, 12 округов, 50 городов МО.\n"
    if "profilactica_url_rearchitecture_map.csv" not in report_text:
        report_text = report_text.replace(needle, needle + extra)
        report.write_text(report_text, encoding="utf-8", newline="\n")

    tz = ROOT / "profilactica_coding_agent_tz.md"
    tz_text = tz.read_text(encoding="utf-8")
    tz_needle = "- `profilactica_geo_master_lists.csv`\n"
    tz_extra = (
        "- `profilactica_geo_relationships.csv`\n"
        "- `profilactica_geo_okrug_neighbors.csv`\n"
        "- `profilactica_url_rearchitecture_map.csv`\n"
        "- `profilactica_canonical_urls.csv`\n"
    )
    if "profilactica_url_rearchitecture_map.csv" not in tz_text:
        tz_text = tz_text.replace(tz_needle, tz_needle + tz_extra)
    rule = (
        "\nПубличный URL не содержит каталогов metro, okrug и mo. "
        "Станции и округа: `{услуга}/moskva/{slug}/`. Города: `{услуга}/moskovskaya-oblast/{slug}/`. "
        "Связь станции с округом берётся из `profilactica_geo_relationships.csv`. "
        "`profilactica_url_rearchitecture_map.csv` — карта переноса конфигурации, не таблица 301.\n"
    )
    anchor = "Источник: `geo-pages.csv` и `geo-master.csv`.\n"
    if "Публичный URL не содержит каталогов" not in tz_text:
        tz_text = tz_text.replace(anchor, anchor + rule)
    tz.write_text(tz_text, encoding="utf-8", newline="\n")

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
    text = (
        text[:start]
        + "### Полный каталог финальной архитектуры\n\n"
        + arch_md
        + "\n"
        + text[end:]
    )
    inter = (ROOT / "profilactica_interlinking.md").read_text(encoding="utf-8")
    start = text.find("# Полная схема внутренней перелинковки")
    end = text.find("\n# 11. Обязательные блоки")
    if start < 0 or end < 0:
        raise SystemExit("interlinking markers missing")
    text = text[:start] + inter.strip() + "\n" + text[end:]
    analysis.write_text(text, encoding="utf-8", newline="\n")


def patch_geo_table(geo_rows):
    analysis = ROOT / "konkurentnyy-analiz.md"
    text = analysis.read_text(encoding="utf-8")
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
    payload["geoMaster"] = MASTER.read_text(encoding="utf-8")
    embed_path.write_text(prefix + json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    shutil.copy2(ARCH, DATA / "architecture.csv")
    shutil.copy2(GEO, DATA / "geo-pages.csv")
    shutil.copy2(MASTER, DATA / "geo-master.csv")


def main():
    current = read_csv(ARCH)
    if any(row["url"] == "/uslugi/vyvod-iz-zapoya/" for row in current) and not any(
        row["url"].startswith("/uslugi/lechenie-alkogolizma/vyvod-iz-zapoya/") for row in current
    ):
        raise SystemExit("architecture is already rebuilt; refusing to run twice")

    master = read_csv(MASTER)
    mo_tier = {row["slug"]: row["tier"] for row in master if row["geo_type"] == "mo"}
    relationships = write_relationships(master)

    base_rows, originals = transform_architecture(current)
    final_rows = add_hubs(base_rows)
    if len({row["url"] for row in final_rows}) != len(final_rows):
        raise SystemExit("duplicate architecture URL after rebuild")

    geo_in = read_csv(GEO)
    geo_rows = transform_geo(geo_in, mo_tier)
    public_geo = [{key: row[key] for key in GEO_FIELDS} for row in geo_rows]

    write_csv(ARCH, ARCH_FIELDS, final_rows)
    write_csv(GEO, GEO_FIELDS, public_geo)

    # Pair originals with base rows, then map final rows by URL.
    pre_pairs = {row["url"]: originals[index] for index, row in enumerate(base_rows)}
    map_rows = assemble_map(base_rows, originals, final_rows, geo_rows)
    # assemble_map already zips base_rows with originals. pre_pairs kept for sanity.
    if len(pre_pairs) != len(base_rows):
        raise SystemExit("lost original URL pairing")
    write_csv(MAP, MAP_FIELDS, map_rows)
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
            for row in map_rows
        ],
    )
    patch_docs(final_rows)
    patch_geo_table(geo_rows)
    refresh_embed()
    print(f"architecture {len(final_rows)}")
    print(f"geo {len(geo_rows)}")
    print(f"relationships {len(relationships)}")
    print(f"map {len(map_rows)}")
    print("ambiguous", sum(1 for row in relationships if row["notes"]))


if __name__ == "__main__":
    main()
