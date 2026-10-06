"""Минимальные GEO-запросы для проверки частотности в Wordstat.

Скрипт читает master CSV, подставляет маски услуг и сохраняет запросы.
К Wordstat он не обращается и частотность не собирает.
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
from dataclasses import dataclass
from pathlib import Path

from config.services import CORE_MO_TIER, KNOWN_GEO_TYPES, SERVICES

ROOT = Path(__file__).resolve().parent
DEFAULT_INPUT = ROOT / "profilactica_geo_master_lists.csv"
DEFAULT_OUTPUT = ROOT / "output"

REQUIRED_COLUMNS = ("geo_type", "name", "slug", "tier")
CSV_COLUMNS = (
    "service_id",
    "service_name",
    "query_base",
    "geo_type",
    "geo_name",
    "geo_slug",
    "tier",
    "query",
)


class GeoInputError(Exception):
    """Входной CSV неполный или не сходится с правилами отбора GEO."""


class ConfigError(Exception):
    """Ошибка конфигурации услуг или аргументов запуска."""


@dataclass(frozen=True)
class GeoRecord:
    geo_type: str
    name: str
    slug: str
    tier: str


@dataclass(frozen=True)
class GeoLoadResult:
    geos: list[GeoRecord]
    skipped_unknown: int


@dataclass(frozen=True)
class QueryRow:
    service_id: str
    service_name: str
    query_base: str
    geo_type: str
    geo_name: str
    geo_slug: str
    tier: str
    query: str


def normalize_query(text: str) -> str:
    """Нижний регистр и один пробел между словами. Буква ё сохраняется."""
    return " ".join(text.split()).lower()


def comparison_key(query: str) -> str:
    """Ключ дедупликации: ё и е считаются одной буквой."""
    return normalize_query(query).replace("ё", "е")


def clean_cell(value: str | None) -> str:
    if value is None:
        return ""
    return " ".join(value.split())


def validate_services(services: dict) -> None:
    if not isinstance(services, dict) or not services:
        raise ConfigError("Конфигурация услуг пуста.")

    allowed = ", ".join(KNOWN_GEO_TYPES)
    for service_id, spec in services.items():
        if not isinstance(service_id, str) or not service_id.strip():
            raise ConfigError("В конфигурации есть пустой service_id.")
        if not isinstance(spec, dict):
            raise ConfigError(f"{service_id}: описание услуги должно быть словарём.")

        name = spec.get("name")
        if not isinstance(name, str) or not name.strip():
            raise ConfigError(f"{service_id}: укажите непустое поле name.")

        queries = spec.get("queries")
        if not isinstance(queries, list) or len(queries) == 0:
            raise ConfigError(
                f"{service_id}: queries должен быть непустым списком масок."
            )
        for query in queries:
            if not isinstance(query, str) or not query.strip():
                raise ConfigError(f"{service_id}: в queries есть пустая маска.")

        geo_types = spec.get("geo_types")
        if not isinstance(geo_types, list) or len(geo_types) == 0:
            raise ConfigError(
                f"{service_id}: geo_types должен быть непустым списком."
            )
        for geo_type in geo_types:
            if geo_type not in KNOWN_GEO_TYPES:
                raise ConfigError(
                    f"{service_id}: неизвестный geo_type «{geo_type}». "
                    f"Допустимые: {allowed}."
                )

        metro_variant = spec.get("metro_variant")
        if not isinstance(metro_variant, bool):
            raise ConfigError(
                f"{service_id}: metro_variant должен быть True или False."
            )
        if metro_variant and "metro" not in geo_types:
            raise ConfigError(
                f"{service_id}: metro_variant=True, но metro нет в geo_types."
            )

        if "mo_limit" not in spec or spec["mo_limit"] is None:
            continue
        limit = spec["mo_limit"]
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ConfigError(
                f"{service_id}: mo_limit должен быть целым числом больше нуля."
            )
        if "mo" not in geo_types:
            raise ConfigError(
                f"{service_id}: задан mo_limit, но mo нет в geo_types."
            )


def load_geos(path: Path) -> GeoLoadResult:
    """Читает master CSV. Строки с неизвестным geo_type пропускаются."""
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise GeoInputError(f"Не найден входной файл: {path}") from exc
    except UnicodeDecodeError as exc:
        raise GeoInputError(
            f"Файл {path} не удалось прочитать как UTF-8."
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise GeoInputError(f"Файл {path} пуст или не содержит заголовок CSV.")

    fieldnames = [clean_cell(name) for name in reader.fieldnames]
    reader.fieldnames = fieldnames
    missing = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
    if missing:
        raise GeoInputError(
            "В CSV нет обязательных колонок: "
            + ", ".join(missing)
            + ". Ожидаются: "
            + ", ".join(REQUIRED_COLUMNS)
            + "."
        )

    geos: list[GeoRecord] = []
    seen: set[tuple[str, str]] = set()
    skipped_unknown = 0

    for line_no, row in enumerate(reader, start=2):
        geo_type = clean_cell(row.get("geo_type")).lower()
        name = clean_cell(row.get("name"))
        slug = clean_cell(row.get("slug"))
        tier = clean_cell(row.get("tier"))
        values = {
            "geo_type": geo_type,
            "name": name,
            "slug": slug,
            "tier": tier,
        }
        for column, value in values.items():
            if not value:
                raise GeoInputError(
                    f"Строка {line_no}: пустое значение в колонке {column}."
                )

        if geo_type not in KNOWN_GEO_TYPES:
            skipped_unknown += 1
            continue

        key = (geo_type, slug)
        if key in seen:
            raise GeoInputError(
                f"Строка {line_no}: GEO {geo_type}/{slug} уже встречался в файле. "
                "Оставьте одну строку на пару geo_type + slug."
            )
        seen.add(key)
        geos.append(GeoRecord(geo_type=geo_type, name=name, slug=slug, tier=tier))

    return GeoLoadResult(geos=geos, skipped_unknown=skipped_unknown)


def geo_matches(geo: GeoRecord, spec: dict) -> bool:
    if geo.geo_type not in spec["geo_types"]:
        return False
    limit = spec.get("mo_limit")
    if geo.geo_type == "mo" and limit is not None:
        return geo.tier.lower() == CORE_MO_TIER
    return True


def assert_mo_limits(
    geos: list[GeoRecord],
    services: dict,
    service_ids: list[str],
) -> None:
    core_count = sum(
        1
        for geo in geos
        if geo.geo_type == "mo" and geo.tier.lower() == CORE_MO_TIER
    )
    for service_id in service_ids:
        limit = services[service_id].get("mo_limit")
        if limit is None:
            continue
        if core_count == limit:
            continue
        raise GeoInputError(
            f"Услуга {service_id}: в конфигурации mo_limit={limit}, "
            f"а в CSV городов с geo_type=mo и tier={CORE_MO_TIER}: {core_count}. "
            "Основные города выбираются по tier. "
            "Проверьте колонку tier или значение mo_limit."
        )


def render_query(query_base: str, geo_name: str, with_metro: bool) -> str:
    geo = normalize_query(geo_name)
    if with_metro:
        return normalize_query(f"{query_base} метро {geo}")
    return normalize_query(f"{query_base} {geo}")


def active_service_ids(services: dict, service_id: str | None) -> list[str]:
    if service_id is None:
        return list(services)
    if service_id not in services:
        known = ", ".join(services)
        raise ConfigError(
            f"Неизвестная услуга: {service_id}. Допустимые: {known}."
        )
    return [service_id]


def generate_rows(
    geos: list[GeoRecord],
    services: dict | None = None,
    service_id: str | None = None,
    geo_type: str | None = None,
    validate_mo_limits: bool = True,
) -> list[QueryRow]:
    """Собирает строки итогового CSV.

    Порядок: услуга, затем GEO в порядке master CSV, затем маски.
    Для метро вторая строка — вариант со словом «метро».
    """
    catalog = SERVICES if services is None else services
    validate_services(catalog)
    if geo_type is not None and geo_type not in KNOWN_GEO_TYPES:
        allowed = ", ".join(KNOWN_GEO_TYPES)
        raise ConfigError(
            f"Неизвестный geo-type: {geo_type}. Допустимые: {allowed}."
        )

    service_ids = active_service_ids(catalog, service_id)
    if validate_mo_limits:
        assert_mo_limits(geos, catalog, service_ids)

    rows: list[QueryRow] = []
    for current_id in service_ids:
        spec = catalog[current_id]
        masks = [normalize_query(query) for query in spec["queries"]]
        for geo in geos:
            if geo_type is not None and geo.geo_type != geo_type:
                continue
            if not geo_matches(geo, spec):
                continue
            for mask in masks:
                rows.append(
                    QueryRow(
                        service_id=current_id,
                        service_name=spec["name"],
                        query_base=mask,
                        geo_type=geo.geo_type,
                        geo_name=geo.name,
                        geo_slug=geo.slug,
                        tier=geo.tier,
                        query=render_query(mask, geo.name, with_metro=False),
                    )
                )
                if spec["metro_variant"] and geo.geo_type == "metro":
                    rows.append(
                        QueryRow(
                            service_id=current_id,
                            service_name=spec["name"],
                            query_base=mask,
                            geo_type=geo.geo_type,
                            geo_name=geo.name,
                            geo_slug=geo.slug,
                            tier=geo.tier,
                            query=render_query(mask, geo.name, with_metro=True),
                        )
                    )
    return rows


def dedupe_queries(queries: list[str]) -> tuple[list[str], int]:
    seen: set[str] = set()
    unique: list[str] = []
    removed = 0
    for query in queries:
        key = comparison_key(query)
        if key in seen:
            removed += 1
            continue
        seen.add(key)
        unique.append(query)
    return unique, removed


def format_report(
    geos: list[GeoRecord],
    services: dict,
    service_ids: list[str],
    rows: list[QueryRow],
    duplicates_removed: int,
    unique_total: int,
    skipped_unknown: int,
    output_dir: Path,
) -> str:
    counts = {
        geo_type: sum(1 for geo in geos if geo.geo_type == geo_type)
        for geo_type in KNOWN_GEO_TYPES
    }
    core_count = sum(
        1
        for geo in geos
        if geo.geo_type == "mo" and geo.tier.lower() == CORE_MO_TIER
    )
    by_service: dict[str, list[QueryRow]] = {service_id: [] for service_id in service_ids}
    for row in rows:
        by_service[row.service_id].append(row)

    lines = [
        "GEO loaded:",
        f"Metro: {counts['metro']}",
        f"Okrug: {counts['okrug']}",
        f"MO: {counts['mo']}",
        f"MO core ({CORE_MO_TIER}): {core_count}",
    ]
    if skipped_unknown:
        lines.append(f"Skipped unknown geo_type: {skipped_unknown}")

    masks_loaded = sum(len(services[service_id]["queries"]) for service_id in service_ids)
    lines.extend(
        [
            "",
            f"Services loaded: {len(service_ids)}",
            f"Query masks loaded: {masks_loaded}",
            "",
            "Generated:",
        ]
    )

    for service_id in service_ids:
        spec = services[service_id]
        service_rows = by_service[service_id]
        lines.append(f"{spec['name']}: {len(service_rows)}")
        if len(spec["queries"]) > 1:
            geo_count = len({(row.geo_type, row.geo_slug) for row in service_rows})
            mask_count = len({row.query_base for row in service_rows})
            lines.append(f"{spec['name']}:")
            lines.append(f"{geo_count} GEO")
            lines.append(f"{mask_count} query masks")
            lines.append(f"{len(service_rows)} queries")

    lines.extend(
        [
            "",
            f"Duplicates removed: {duplicates_removed}",
            f"Total unique Wordstat queries: {unique_total}",
            "",
            f"Output: {output_dir}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_query_file(path: Path, queries: list[str]) -> None:
    unique, _removed = dedupe_queries(queries)
    payload = "\n".join(unique)
    if unique:
        payload += "\n"
    path.write_text(payload, encoding="utf-8", newline="\n")


def write_csv(path: Path, rows: list[QueryRow]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "service_id": row.service_id,
                    "service_name": row.service_name,
                    "query_base": row.query_base,
                    "geo_type": row.geo_type,
                    "geo_name": row.geo_name,
                    "geo_slug": row.geo_slug,
                    "tier": row.tier,
                    "query": row.query,
                }
            )


def write_outputs(
    output_dir: Path,
    rows: list[QueryRow],
    service_ids: list[str],
    geo_type: str | None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.glob("queries_*.txt"):
        path.unlink()

    write_csv(output_dir / "geo_queries.csv", rows)
    write_query_file(output_dir / "wordstat_queries.txt", [row.query for row in rows])

    for service_id in service_ids:
        write_query_file(
            output_dir / f"queries_{service_id}.txt",
            [row.query for row in rows if row.service_id == service_id],
        )

    geo_types = [geo_type] if geo_type else list(KNOWN_GEO_TYPES)
    for current_type in geo_types:
        write_query_file(
            output_dir / f"queries_{current_type}.txt",
            [row.query for row in rows if row.geo_type == current_type],
        )


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (OSError, ValueError):
                continue


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Минимальный набор запросов «услуга + GEO» для проверки частотности."
        )
    )
    parser.add_argument(
        "--service",
        help="Одна услуга, например narkolog-na-dom или reabilitaciya.",
    )
    parser.add_argument(
        "--geo-type",
        help="Один тип GEO: metro, okrug или mo.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Master CSV с колонками geo_type, name, slug, tier.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Каталог для CSV и TXT. По умолчанию output/.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = parse_args(argv)
    try:
        validate_services(SERVICES)
        if args.geo_type is not None and args.geo_type not in KNOWN_GEO_TYPES:
            allowed = ", ".join(KNOWN_GEO_TYPES)
            raise ConfigError(
                f"Неизвестный geo-type: {args.geo_type}. Допустимые: {allowed}."
            )

        loaded = load_geos(args.input)
        service_ids = active_service_ids(SERVICES, args.service)
        rows = generate_rows(
            loaded.geos,
            services=SERVICES,
            service_id=args.service,
            geo_type=args.geo_type,
            validate_mo_limits=True,
        )
        unique, removed = dedupe_queries([row.query for row in rows])
        write_outputs(args.output_dir, rows, service_ids, args.geo_type)
        report = format_report(
            geos=loaded.geos,
            services=SERVICES,
            service_ids=service_ids,
            rows=rows,
            duplicates_removed=removed,
            unique_total=len(unique),
            skipped_unknown=loaded.skipped_unknown,
            output_dir=args.output_dir,
        )
    except (GeoInputError, ConfigError, OSError) as exc:
        sys.stderr.write(f"{exc}\n")
        return 1

    sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
