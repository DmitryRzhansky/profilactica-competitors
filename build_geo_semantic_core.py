"""Собирает GEO-семантическое ядро в Excel по выгрузке Wordstat и master GEO."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill, numbers
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

# Как в референсе «Семантическое ядро»: Montserrat 11, зелёный accent4 (#34A853).
FONT_NAME = "Montserrat"
FONT_SIZE = 11
GREEN = "34A853"
WHITE = "FFFFFF"
BASE_FONT = Font(name=FONT_NAME, size=FONT_SIZE, bold=False, color="000000")
HEADER_FONT = Font(name=FONT_NAME, size=FONT_SIZE, bold=False, color=WHITE)
GREEN_FILL = PatternFill(fill_type="solid", fgColor=GREEN)
CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
LEFT_WRAP = Alignment(horizontal="left", vertical="center", wrap_text=True)
RIGHT_NUM = Alignment(horizontal="right", vertical="center")

from config.services import CORE_MO_TIER, SERVICES
from generate_geo_queries import (
    GeoRecord,
    comparison_key,
    generate_rows,
    load_geos,
    normalize_query,
)

ROOT = Path(__file__).resolve().parent
WS_SOURCE = Path(r"c:\Users\User\Downloads\WS_parsing_нарколог_аэропорт_2026-09-29-10-01-23.xlsx")
GEO_MASTER = ROOT / "profilactica_geo_master_lists.csv"
OUTPUT = ROOT / "output" / "GEO_semanticheskoe_yadro_Profilaktika.xlsx"

# Канонические названия посадочных (столбец «Услуга»).
SERVICE_TITLES: dict[str, str] = {
    "narkolog-na-dom": "Нарколог на дом",
    "vyvod-iz-zapoya": "Вывод из запоя на дому",
    "kapelnica-na-dom": "Капельница от запоя и алкоголя на дому",
    "kodirovanie": "Кодирование от алкоголизма",
    "psihiatr-na-dom": "Психиатр на дом",
    "lechenie-alkogolizma": "Лечение алкоголизма",
    "lechenie-narkomanii": "Лечение наркомании",
    "reabilitaciya": "Реабилитация зависимых",
}

# Базовые URL SILO.
SERVICE_URL_BASES: dict[str, str] = {
    "narkolog-na-dom": "/uslugi/narkologicheskaya-pomosh/narkolog-na-dom/",
    "vyvod-iz-zapoya": "/uslugi/lechenie-alkogolizma/vyvod-iz-zapoya/na-domu/",
    "kapelnica-na-dom": "/uslugi/lechenie-alkogolizma/kapelnitsy/ot-zapoya-i-alkogolya/",
    "kodirovanie": "/uslugi/lechenie-alkogolizma/kodirovanie/",
    "psihiatr-na-dom": "/uslugi/psihiatriya/psihiatr-na-dom/",
    "lechenie-alkogolizma": "/uslugi/lechenie-alkogolizma/",
    "lechenie-narkomanii": "/uslugi/lechenie-narkomanii/",
    "reabilitaciya": "/uslugi/reabilitaciya/",
}

# Имена листов Excel.
SHEET_NAMES: dict[str, str] = {
    "narkolog-na-dom": "Нарколог на дом",
    "vyvod-iz-zapoya": "Вывод из запоя",
    "kapelnica-na-dom": "Капельница на дому",
    "kodirovanie": "Кодирование",
    "psihiatr-na-dom": "Психиатр на дом",
    "lechenie-alkogolizma": "Лечение алкоголизма",
    "lechenie-narkomanii": "Лечение наркомании",
    "reabilitaciya": "Реабилитация",
}

EXPECTED_PAGES: dict[str, int] = {
    "narkolog-na-dom": 277,
    "vyvod-iz-zapoya": 277,
    "kapelnica-na-dom": 277,
    "kodirovanie": 277,
    "psihiatr-na-dom": 62,
    "lechenie-alkogolizma": 30,
    "lechenie-narkomanii": 30,
    "reabilitaciya": 30,
}

EXPECTED_QUERIES: dict[str, int] = {
    "narkolog-na-dom": 492,
    "vyvod-iz-zapoya": 492,
    "kapelnica-na-dom": 492,
    "kodirovanie": 492,
    "psihiatr-na-dom": 62,
    "lechenie-alkogolizma": 30,
    "lechenie-narkomanii": 30,
    "reabilitaciya": 90,
}

# Предложный падеж городов МО для конструкции «в {городе}».
CITY_PREPOSITIONAL: dict[str, str] = {
    "Балашиха": "Балашихе",
    "Подольск": "Подольске",
    "Химки": "Химках",
    "Мытищи": "Мытищах",
    "Королёв": "Королёве",
    "Люберцы": "Люберцах",
    "Красногорск": "Красногорске",
    "Электросталь": "Электростали",
    "Коломна": "Коломне",
    "Одинцово": "Одинцове",
    "Домодедово": "Домодедове",
    "Щёлково": "Щёлкове",
    "Серпухов": "Серпухове",
    "Раменское": "Раменском",
    "Долгопрудный": "Долгопрудном",
    "Пушкино": "Пушкине",
    "Реутов": "Реутове",
    "Жуковский": "Жуковском",
    "Ногинск": "Ногинске",
    "Сергиев Посад": "Сергиевом Посаде",
    "Воскресенск": "Воскресенске",
    "Орехово-Зуево": "Орехово-Зуеве",
    "Павловский Посад": "Павловском Посаде",
    "Лобня": "Лобне",
    "Ивантеевка": "Ивантеевке",
    "Клин": "Клину",
    "Егорьевск": "Егорьевске",
    "Дмитров": "Дмитрове",
    "Чехов": "Чехове",
    "Наро-Фоминск": "Наро-Фоминске",
    "Ступино": "Ступине",
    "Видное": "Видном",
    "Фрязино": "Фрязине",
    "Лыткарино": "Лыткарине",
    "Дзержинский": "Дзержинском",
    "Котельники": "Котельниках",
    "Истра": "Истре",
    "Дедовск": "Дедовске",
    "Солнечногорск": "Солнечногорске",
    "Апрелевка": "Апрелевке",
    "Кубинка": "Кубинке",
    "Руза": "Рузе",
    "Звенигород": "Звенигороде",
    "Можайск": "Можайске",
    "Луховицы": "Луховицах",
    "Кашира": "Кашире",
    "Протвино": "Протвине",
    "Дубна": "Дубне",
    "Черноголовка": "Черноголовке",
    "Волоколамск": "Волоколамске",
}


@dataclass(frozen=True)
class ClusterQuery:
    phrase: str
    ws: int


@dataclass
class LandingCluster:
    service_id: str
    title: str
    url: str
    geo_type: str
    geo_slug: str
    queries: list[ClusterQuery]


def load_ws_frequency(path: Path) -> dict[str, tuple[str, int]]:
    """Ключ comparison_key → (исходная фраза из выгрузки, WS)."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    result: dict[str, tuple[str, int]] = {}
    for phrase, freq in ws.iter_rows(min_row=2, values_only=True):
        if phrase is None:
            continue
        text = str(phrase).strip()
        if not text:
            continue
        key = comparison_key(text)
        value = 0 if freq is None else int(freq)
        if key in result and result[key][1] != value:
            raise ValueError(f"Конфликт WS для «{text}»: {result[key][1]} vs {value}")
        result[key] = (text, value)
    wb.close()
    return result


def page_title(service_id: str, geo: GeoRecord) -> str:
    base = SERVICE_TITLES[service_id]
    if geo.geo_type == "metro":
        return f"{base} у метро {geo.name}"
    if geo.geo_type == "okrug":
        return f"{base} в {geo.name}"
    if geo.geo_type == "mo":
        prep = CITY_PREPOSITIONAL.get(geo.name)
        if not prep:
            raise KeyError(f"Нет предложного падежа для города: {geo.name}")
        return f"{base} в {prep}"
    raise ValueError(f"Неизвестный geo_type: {geo.geo_type}")


def page_url(service_id: str, geo: GeoRecord) -> str:
    base = SERVICE_URL_BASES[service_id]
    return f"{base}{geo.geo_type}/{geo.slug}/"


def build_clusters(
    geos: list[GeoRecord],
    ws_map: dict[str, tuple[str, int]],
) -> dict[str, list[LandingCluster]]:
    """Группирует запросы в посадочные кластеры по услугам."""
    rows = generate_rows(geos)
    grouped: dict[tuple[str, str, str], LandingCluster] = {}
    order: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for row in rows:
        key = (row.service_id, row.geo_type, row.geo_slug)
        if key not in grouped:
            geo = GeoRecord(
                geo_type=row.geo_type,
                name=row.geo_name,
                slug=row.geo_slug,
                tier=row.tier,
            )
            grouped[key] = LandingCluster(
                service_id=row.service_id,
                title=page_title(row.service_id, geo),
                url=page_url(row.service_id, geo),
                geo_type=row.geo_type,
                geo_slug=row.geo_slug,
                queries=[],
            )
            order[row.service_id].append((row.geo_type, row.geo_slug))

        phrase_key = comparison_key(row.query)
        if phrase_key not in ws_map:
            raise KeyError(f"Запрос отсутствует в выгрузке WS: {row.query}")
        original, freq = ws_map[phrase_key]
        grouped[key].queries.append(ClusterQuery(phrase=original, ws=freq))

    result: dict[str, list[LandingCluster]] = {}
    for service_id, keys in order.items():
        result[service_id] = [grouped[(service_id, gt, slug)] for gt, slug in keys]
    return result


def style_header(ws: Worksheet) -> None:
    for col in range(1, 5):
        cell = ws.cell(1, col)
        cell.font = HEADER_FONT
        cell.fill = GREEN_FILL
        cell.alignment = CENTER


def style_separator_row(ws: Worksheet, row_idx: int) -> None:
    for col in range(1, 5):
        cell = ws.cell(row_idx, col)
        cell.value = None
        cell.font = BASE_FONT
        cell.fill = GREEN_FILL


def apply_data_font(ws: Worksheet, row_idx: int) -> None:
    for col in range(1, 5):
        cell = ws.cell(row_idx, col)
        cell.font = BASE_FONT


def write_sheet(ws: Worksheet, clusters: list[LandingCluster]) -> tuple[int, int]:
    ws.append(["Услуга", "Запросы", "WS", "URL"])
    style_header(ws)

    pages = 0
    queries = 0
    for index, cluster in enumerate(clusters):
        start_row = ws.max_row + 1
        for i, item in enumerate(cluster.queries):
            if i == 0:
                ws.append([cluster.title, item.phrase, item.ws, cluster.url])
            else:
                ws.append([None, item.phrase, item.ws, None])
            queries += 1
            row_idx = ws.max_row
            apply_data_font(ws, row_idx)

            ws.cell(row_idx, 2).number_format = numbers.FORMAT_TEXT
            ws.cell(row_idx, 2).alignment = LEFT_WRAP
            ws.cell(row_idx, 3).number_format = "0"
            ws.cell(row_idx, 3).alignment = RIGHT_NUM
            if i == 0:
                ws.cell(row_idx, 1).alignment = LEFT_WRAP
                ws.cell(row_idx, 4).number_format = numbers.FORMAT_TEXT
                ws.cell(row_idx, 4).alignment = LEFT_WRAP

        end_row = ws.max_row
        # Как в референсе: Услуга и URL объединяются на весь кластер.
        if end_row > start_row:
            ws.merge_cells(start_row=start_row, start_column=1, end_row=end_row, end_column=1)
            ws.merge_cells(start_row=start_row, start_column=4, end_row=end_row, end_column=4)
            ws.cell(start_row, 1).alignment = LEFT_WRAP
            ws.cell(start_row, 4).alignment = LEFT_WRAP

        pages += 1
        if index < len(clusters) - 1:
            ws.append([None, None, None, None])
            style_separator_row(ws, ws.max_row)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:D{ws.max_row}"
    # Ширины близки к референсу (Услуга / Запросы / WS / URL).
    widths = {1: 55, 2: 45, 3: 10, 4: 75}
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width
    return pages, queries


def has_cyrillic(text: str) -> bool:
    return bool(re.search(r"[А-Яа-яЁё]", text))


def validate(
    clusters_by_service: dict[str, list[LandingCluster]],
    ws_map: dict[str, tuple[str, int]],
) -> None:
    total_pages = 0
    total_queries = 0
    used_keys: list[str] = []
    errors: list[str] = []

    for service_id, clusters in clusters_by_service.items():
        pages = len(clusters)
        queries = sum(len(c.queries) for c in clusters)
        total_pages += pages
        total_queries += queries

        if pages != EXPECTED_PAGES[service_id]:
            errors.append(
                f"{service_id}: страниц {pages}, ожидалось {EXPECTED_PAGES[service_id]}"
            )
        if queries != EXPECTED_QUERIES[service_id]:
            errors.append(
                f"{service_id}: запросов {queries}, ожидалось {EXPECTED_QUERIES[service_id]}"
            )

        titles_seen: set[str] = set()
        urls_seen: set[str] = set()
        for cluster in clusters:
            if not cluster.title:
                errors.append(f"{service_id}: пустое название страницы")
            if not cluster.url:
                errors.append(f"{service_id}: пустой URL у «{cluster.title}»")
            if not cluster.url.endswith("/"):
                errors.append(f"URL без /: {cluster.url}")
            if has_cyrillic(cluster.url):
                errors.append(f"Кириллица в URL: {cluster.url}")
            if cluster.title in titles_seen:
                errors.append(f"Дубль названия: {cluster.title}")
            titles_seen.add(cluster.title)
            if cluster.url in urls_seen:
                errors.append(f"Дубль URL: {cluster.url}")
            urls_seen.add(cluster.url)
            if not cluster.queries:
                errors.append(f"Нет запросов у {cluster.title}")

            for item in cluster.queries:
                key = comparison_key(item.phrase)
                used_keys.append(key)
                if key not in ws_map:
                    errors.append(f"Придуманный запрос: {item.phrase}")
                else:
                    original, freq = ws_map[key]
                    if item.phrase != original:
                        errors.append(
                            f"Формулировка изменена: «{item.phrase}» != «{original}»"
                        )
                    if item.ws != freq:
                        errors.append(
                            f"WS изменён для «{item.phrase}»: {item.ws} != {freq}"
                        )

        # Котельники: метро + город для первых четырёх услуг.
        if service_id in (
            "narkolog-na-dom",
            "vyvod-iz-zapoya",
            "kapelnica-na-dom",
            "kodirovanie",
        ):
            has_metro = any(
                c.geo_type == "metro" and c.geo_slug == "kotelniki" for c in clusters
            )
            has_mo = any(
                c.geo_type == "mo" and c.geo_slug == "kotelniki" for c in clusters
            )
            if not has_metro or not has_mo:
                errors.append(f"{service_id}: Котельники должны быть и metro, и mo")

        if service_id == "reabilitaciya":
            if any(len(c.queries) != 3 for c in clusters):
                errors.append("Реабилитация: у каждой страницы должно быть 3 запроса")
            if pages != 30:
                errors.append("Реабилитация: ожидалось 30 страниц")

        if service_id == "psihiatr-na-dom":
            if any(c.geo_type == "metro" for c in clusters):
                errors.append("Психиатр: метро не должно присутствовать")

        if service_id in (
            "lechenie-alkogolizma",
            "lechenie-narkomanii",
            "reabilitaciya",
        ):
            if any(c.geo_type != "mo" for c in clusters):
                errors.append(f"{service_id}: допускаются только города МО")

    if total_pages != 1260:
        errors.append(f"Всего страниц {total_pages}, ожидалось 1260")
    if total_queries != 2180:
        errors.append(f"Всего запросов {total_queries}, ожидалось 2180")

    # Все исходные WS-фразы должны быть покрыты (с учётом 4 повторов Котельников).
    unique_used = set(used_keys)
    missing = set(ws_map) - unique_used
    extra = unique_used - set(ws_map)
    if missing:
        errors.append(f"Потеряно исходных запросов: {len(missing)}")
        for key in sorted(missing)[:10]:
            errors.append(f"  lost: {ws_map[key][0]}")
    if extra:
        errors.append(f"Лишние запросы: {len(extra)}")

    # Ровно 4 ключа используются дважды (базовые котельники без «метро»).
    from collections import Counter

    counts = Counter(used_keys)
    doubled = {k: v for k, v in counts.items() if v > 1}
    if len(doubled) != 4 or any(v != 2 for v in doubled.values()):
        errors.append(f"Ожидалось 4 двойных ключа Котельников, получено: {doubled}")

    if errors:
        raise RuntimeError("Проверка не пройдена:\n" + "\n".join(errors))


def ensure_city_cases(geos: list[GeoRecord]) -> None:
    cities = [g for g in geos if g.geo_type == "mo"]
    missing = [g.name for g in cities if g.name not in CITY_PREPOSITIONAL]
    if missing:
        raise KeyError("Нет падежей для: " + ", ".join(missing))


def main() -> None:
    geo_result = load_geos(GEO_MASTER)
    geos = geo_result.geos
    ensure_city_cases(geos)

    # Конфиг услуг должен совпасть с ожиданиями по GEO.
    for service_id, spec in SERVICES.items():
        assert service_id in SERVICE_TITLES
        assert service_id in SERVICE_URL_BASES
        assert service_id in SHEET_NAMES

    ws_map = load_ws_frequency(WS_SOURCE)
    if len(ws_map) != 2176:
        raise RuntimeError(f"В выгрузке WS ожидалось 2176 фраз, получено {len(ws_map)}")

    clusters_by_service = build_clusters(geos, ws_map)
    validate(clusters_by_service, ws_map)

    wb = openpyxl.Workbook()
    # Удаляем дефолтный лист после создания рабочих.
    default = wb.active
    wb.remove(default)

    summary_rows = []
    for service_id in SERVICES:
        sheet_name = SHEET_NAMES[service_id]
        ws = wb.create_sheet(sheet_name)
        pages, queries = write_sheet(ws, clusters_by_service[service_id])
        summary_rows.append((sheet_name, pages, queries))
        # Лишних столбцов быть не должно.
        if ws.max_column != 4:
            raise RuntimeError(f"{sheet_name}: столбцов {ws.max_column}, ожидалось 4")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUTPUT)

    print("OK:", OUTPUT)
    print(f"{'Лист':<28} {'Страниц':>8} {'Запросов':>10}")
    for name, pages, queries in summary_rows:
        print(f"{name:<28} {pages:>8} {queries:>10}")
    print(f"{'ИТОГО':<28} {sum(r[1] for r in summary_rows):>8} {sum(r[2] for r in summary_rows):>10}")


if __name__ == "__main__":
    main()
