"""Поисковые маски и правила GEO.

Маски лежат в ``queries`` списком даже у услуг с одной формулировкой:
новую маску можно добавить сюда, не меняя генератор.

``mo_limit`` — контроль, а не срез. Для таких услуг берутся только
города ``geo_type=mo`` с ``tier == CORE_MO_TIER``. Число найденных
городов должно совпасть с ``mo_limit``. Первые N строк CSV не используются.
"""

from __future__ import annotations

# Основные города МО в profilactica_geo_master_lists.csv.
CORE_MO_TIER = "tier-1"

KNOWN_GEO_TYPES = ("metro", "okrug", "mo")

SERVICES: dict[str, dict] = {
    "narkolog-na-dom": {
        "name": "Нарколог на дом",
        "queries": [
            "нарколог",
        ],
        "geo_types": ["metro", "okrug", "mo"],
        "metro_variant": True,
    },
    "vyvod-iz-zapoya": {
        "name": "Вывод из запоя",
        "queries": [
            "вывод из запоя",
        ],
        "geo_types": ["metro", "okrug", "mo"],
        "metro_variant": True,
    },
    "kapelnica-na-dom": {
        "name": "Капельница",
        "queries": [
            "капельница",
        ],
        "geo_types": ["metro", "okrug", "mo"],
        "metro_variant": True,
    },
    "kodirovanie": {
        "name": "Кодирование",
        "queries": [
            "кодирование",
        ],
        "geo_types": ["metro", "okrug", "mo"],
        "metro_variant": True,
    },
    "psihiatr-na-dom": {
        "name": "Психиатр",
        "queries": [
            "психиатр",
        ],
        "geo_types": ["okrug", "mo"],
        "metro_variant": False,
    },
    "lechenie-alkogolizma": {
        "name": "Лечение алкоголизма",
        "queries": [
            "лечение алкоголизма",
        ],
        "geo_types": ["mo"],
        "metro_variant": False,
        "mo_limit": 30,
    },
    "lechenie-narkomanii": {
        "name": "Лечение наркомании",
        "queries": [
            "лечение наркомании",
        ],
        "geo_types": ["mo"],
        "metro_variant": False,
        "mo_limit": 30,
    },
    "reabilitaciya": {
        "name": "Реабилитация",
        "queries": [
            "реабилитация зависимых",
            "реабилитация алкоголиков",
            "реабилитация наркоманов",
        ],
        "geo_types": ["mo"],
        "metro_variant": False,
        "mo_limit": 30,
    },
}
