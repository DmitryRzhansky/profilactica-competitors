"""Проверки минимального генератора GEO-запросов."""

from __future__ import annotations

import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generate_geo_queries import (  # noqa: E402
    ConfigError,
    GeoInputError,
    GeoRecord,
    comparison_key,
    dedupe_queries,
    generate_rows,
    load_geos,
    main,
    render_query,
)
from config.services import SERVICES  # noqa: E402

MASTER = ROOT / "profilactica_geo_master_lists.csv"

METRO_BEL = GeoRecord("metro", "Белорусская", "belorusskaya", "core-215")
MO_KOROLEV = GeoRecord("mo", "Королёв", "korolev", "tier-1")
MO_STUPINO = GeoRecord("mo", "Ступино", "stupino", "tier-2")
OKRUG_CAO = GeoRecord("okrug", "ЦАО", "cao", "core-12")

FORBIDDEN_MODIFIERS = (
    "цена",
    "стоимость",
    "анонимно",
    "круглосуточно",
    "недорого",
    "вызвать",
)


def queries_for(rows, service_id: str) -> list[str]:
    return [row.query for row in rows if row.service_id == service_id]


class TemplateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metro_rows = generate_rows([METRO_BEL], validate_mo_limits=False)
        self.mo_rows = generate_rows([MO_KOROLEV], validate_mo_limits=False)

    def test_metro_narkolog_two_queries(self) -> None:
        self.assertEqual(
            queries_for(self.metro_rows, "narkolog-na-dom"),
            [
                "нарколог белорусская",
                "нарколог метро белорусская",
            ],
        )

    def test_mo_narkolog_one_query(self) -> None:
        self.assertEqual(
            queries_for(self.mo_rows, "narkolog-na-dom"),
            ["нарколог королёв"],
        )

    def test_psihiatr_metro_zero(self) -> None:
        self.assertEqual(queries_for(self.metro_rows, "psihiatr-na-dom"), [])

    def test_lechenie_alkogolizma_metro_zero(self) -> None:
        self.assertEqual(queries_for(self.metro_rows, "lechenie-alkogolizma"), [])

    def test_lechenie_alkogolizma_mo_one(self) -> None:
        self.assertEqual(
            queries_for(self.mo_rows, "lechenie-alkogolizma"),
            ["лечение алкоголизма королёв"],
        )

    def test_lechenie_narkomanii_mo_one(self) -> None:
        self.assertEqual(
            queries_for(self.mo_rows, "lechenie-narkomanii"),
            ["лечение наркомании королёв"],
        )

    def test_reabilitaciya_mo_three(self) -> None:
        self.assertEqual(
            queries_for(self.mo_rows, "reabilitaciya"),
            [
                "реабилитация зависимых королёв",
                "реабилитация алкоголиков королёв",
                "реабилитация наркоманов королёв",
            ],
        )

    def test_reabilitaciya_metro_zero(self) -> None:
        self.assertEqual(queries_for(self.metro_rows, "reabilitaciya"), [])

    def test_forbidden_modifiers_absent(self) -> None:
        rows = generate_rows(
            [METRO_BEL, MO_KOROLEV, OKRUG_CAO],
            validate_mo_limits=False,
        )
        for row in rows:
            tokens = set(row.query.split())
            for modifier in FORBIDDEN_MODIFIERS:
                self.assertNotIn(modifier, tokens)
            plain = render_query(row.query_base, row.geo_name, with_metro=False)
            with_metro = render_query(row.query_base, row.geo_name, with_metro=True)
            if row.geo_type == "metro" and SERVICES[row.service_id]["metro_variant"]:
                self.assertIn(row.query, {plain, with_metro})
            else:
                self.assertEqual(row.query, plain)
                self.assertNotIn(" метро ", f" {row.query} ")

    def test_okrug_has_no_metro_variant(self) -> None:
        rows = generate_rows([OKRUG_CAO], validate_mo_limits=False)
        self.assertEqual(queries_for(rows, "narkolog-na-dom"), ["нарколог цао"])
        self.assertEqual(queries_for(rows, "psihiatr-na-dom"), ["психиатр цао"])
        self.assertEqual(queries_for(rows, "lechenie-alkogolizma"), [])

    def test_tier2_only_for_broad_services(self) -> None:
        rows = generate_rows([MO_STUPINO], validate_mo_limits=False)
        self.assertEqual(queries_for(rows, "narkolog-na-dom"), ["нарколог ступино"])
        self.assertEqual(queries_for(rows, "psihiatr-na-dom"), ["психиатр ступино"])
        self.assertEqual(queries_for(rows, "lechenie-alkogolizma"), [])
        self.assertEqual(queries_for(rows, "lechenie-narkomanii"), [])
        self.assertEqual(queries_for(rows, "reabilitaciya"), [])

    def test_korolev_service_set(self) -> None:
        rows = generate_rows([MO_KOROLEV], validate_mo_limits=False)
        self.assertEqual(
            [row.query for row in rows],
            [
                "нарколог королёв",
                "вывод из запоя королёв",
                "капельница королёв",
                "кодирование королёв",
                "психиатр королёв",
                "лечение алкоголизма королёв",
                "лечение наркомании королёв",
                "реабилитация зависимых королёв",
                "реабилитация алкоголиков королёв",
                "реабилитация наркоманов королёв",
            ],
        )

    def test_extra_mask_does_not_need_generator_change(self) -> None:
        services = {
            "custom": {
                "name": "Custom",
                "queries": ["альфа", "бета"],
                "geo_types": ["mo"],
                "metro_variant": False,
            }
        }
        rows = generate_rows(
            [MO_KOROLEV],
            services=services,
            validate_mo_limits=False,
        )
        self.assertEqual(
            [row.query for row in rows],
            ["альфа королёв", "бета королёв"],
        )

    def test_whitespace_and_yo_are_normalized_for_dedupe(self) -> None:
        rows = generate_rows(
            [
                GeoRecord("mo", "  Королёв  ", "korolev", "tier-1"),
                GeoRecord("mo", "Королев", "korolev-ye", "tier-1"),
            ],
            service_id="narkolog-na-dom",
            validate_mo_limits=False,
        )
        self.assertEqual(
            [row.query for row in rows],
            ["нарколог королёв", "нарколог королев"],
        )
        unique, removed = dedupe_queries([row.query for row in rows])
        self.assertEqual(unique, ["нарколог королёв"])
        self.assertEqual(removed, 1)
        self.assertEqual(comparison_key("Королёв"), comparison_key("королев"))

    def test_csv_keeps_original_geo_spelling(self) -> None:
        rows = generate_rows(
            [METRO_BEL],
            service_id="narkolog-na-dom",
            validate_mo_limits=False,
        )
        self.assertEqual(rows[0].geo_name, "Белорусская")
        self.assertEqual(rows[0].query, "нарколог белорусская")
        self.assertTrue(rows[0].query.startswith("нарколог "))


class InputTests(unittest.TestCase):
    def test_missing_column(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "geo.csv"
            path.write_text("geo_type,name,slug\nmetro,А,a\n", encoding="utf-8")
            with self.assertRaises(GeoInputError) as caught:
                load_geos(path)
        self.assertIn("tier", str(caught.exception))

    def test_empty_required_value(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "geo.csv"
            path.write_text(
                "geo_type,name,slug,tier\nmetro,,aeroport,core-215\n",
                encoding="utf-8",
            )
            with self.assertRaises(GeoInputError) as caught:
                load_geos(path)
        self.assertIn("name", str(caught.exception))
        self.assertIn("2", str(caught.exception))

    def test_duplicate_slug(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "geo.csv"
            path.write_text(
                "geo_type,name,slug,tier\n"
                "metro,А,aeroport,core-215\n"
                "metro,Б,aeroport,core-215\n",
                encoding="utf-8",
            )
            with self.assertRaises(GeoInputError) as caught:
                load_geos(path)
        self.assertIn("aeroport", str(caught.exception))

    def test_unknown_geo_type_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "geo.csv"
            path.write_text(
                "geo_type,name,slug,tier\n"
                "legacy,Село,selo,old\n"
                "metro,Аэропорт,aeroport,core-215\n",
                encoding="utf-8",
            )
            loaded = load_geos(path)
        self.assertEqual(loaded.skipped_unknown, 1)
        self.assertEqual(len(loaded.geos), 1)
        self.assertEqual(loaded.geos[0].slug, "aeroport")

    def test_missing_file(self) -> None:
        with self.assertRaises(GeoInputError) as caught:
            load_geos(ROOT / "no-such-geo.csv")
        self.assertIn("Не найден входной файл", str(caught.exception))

    def test_mo_limit_mismatch_is_explicit(self) -> None:
        with self.assertRaises(GeoInputError) as caught:
            generate_rows(
                [MO_KOROLEV],
                service_id="reabilitaciya",
                validate_mo_limits=True,
            )
        message = str(caught.exception)
        self.assertIn("mo_limit=30", message)
        self.assertIn("tier-1", message)
        self.assertIn(": 1", message)

    def test_unknown_service(self) -> None:
        with self.assertRaises(ConfigError):
            generate_rows([], service_id="missing", validate_mo_limits=False)


class MasterFileTests(unittest.TestCase):
    def test_full_generation_matches_geo_rules(self) -> None:
        loaded = load_geos(MASTER)
        geos = loaded.geos
        metro = sum(1 for geo in geos if geo.geo_type == "metro")
        okrug = sum(1 for geo in geos if geo.geo_type == "okrug")
        mo = sum(1 for geo in geos if geo.geo_type == "mo")
        core = sum(
            1 for geo in geos if geo.geo_type == "mo" and geo.tier == "tier-1"
        )
        self.assertEqual(loaded.skipped_unknown, 0)
        self.assertEqual((metro, okrug, mo, core), (215, 12, 50, 30))

        rows = generate_rows(geos, validate_mo_limits=True)
        counts = {service_id: 0 for service_id in SERVICES}
        for row in rows:
            counts[row.service_id] += 1

        broad = metro * 2 + okrug + mo
        self.assertEqual(counts["narkolog-na-dom"], broad)
        self.assertEqual(counts["vyvod-iz-zapoya"], broad)
        self.assertEqual(counts["kapelnica-na-dom"], broad)
        self.assertEqual(counts["kodirovanie"], broad)
        self.assertEqual(counts["psihiatr-na-dom"], okrug + mo)
        self.assertEqual(counts["lechenie-alkogolizma"], core)
        self.assertEqual(counts["lechenie-narkomanii"], core)
        self.assertEqual(counts["reabilitaciya"], core * 3)
        self.assertEqual(len(rows), broad * 4 + (okrug + mo) + core * 2 + core * 3)

        limited = {
            "lechenie-alkogolizma",
            "lechenie-narkomanii",
            "reabilitaciya",
        }
        for row in rows:
            self.assertEqual(row.query, row.query.lower())
            self.assertFalse(row.query.startswith(row.geo_name.lower() + " "))
            self.assertTrue(row.query.startswith(row.query_base + " "))
            tokens = set(row.query.split())
            for modifier in FORBIDDEN_MODIFIERS:
                self.assertNotIn(modifier, tokens)
            if row.service_id in limited:
                self.assertEqual(row.geo_type, "mo")
                self.assertEqual(row.tier, "tier-1")
            if row.service_id == "psihiatr-na-dom":
                self.assertNotEqual(row.geo_type, "metro")
            if row.geo_type != "metro":
                self.assertNotIn(" метро ", f" {row.query} ")
            if "метро" in row.query.split():
                self.assertEqual(row.geo_type, "metro")
                self.assertEqual(
                    row.query,
                    render_query(row.query_base, row.geo_name, with_metro=True),
                )

        rehab = queries_for(rows, "reabilitaciya")
        index = rehab.index("реабилитация зависимых королёв")
        self.assertEqual(
            rehab[index : index + 3],
            [
                "реабилитация зависимых королёв",
                "реабилитация алкоголиков королёв",
                "реабилитация наркоманов королёв",
            ],
        )
        self.assertLess(
            rehab.index("реабилитация зависимых балашиха"),
            index,
        )
        self.assertIn("нарколог ступино", queries_for(rows, "narkolog-na-dom"))
        self.assertNotIn("лечение алкоголизма ступино", queries_for(rows, "lechenie-alkogolizma"))

        grouped: dict[str, list] = {}
        for row in rows:
            grouped.setdefault(comparison_key(row.query), []).append(row)
        collisions = {key: items for key, items in grouped.items() if len(items) > 1}
        self.assertEqual(len(collisions), 4)
        for items in collisions.values():
            self.assertEqual(len(items), 2)
            self.assertEqual({item.geo_slug for item in items}, {"kotelniki"})
            self.assertEqual({item.geo_type for item in items}, {"metro", "mo"})
            self.assertNotIn("метро", items[0].query.split())

        unique, removed = dedupe_queries([row.query for row in rows])
        self.assertEqual(removed, 4)
        self.assertEqual(len(unique), len(rows) - 4)
        self.assertIn("нарколог котельники", unique)
        self.assertIn("нарколог метро котельники", unique)

    def test_cli_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), redirect_stderr(stderr):
                code = main(["--input", str(MASTER), "--output-dir", directory])
            self.assertEqual(code, 0, stderr.getvalue())
            output = Path(directory)
            report = stdout.getvalue()
            self.assertIn("Metro: 215", report)
            self.assertIn("Okrug: 12", report)
            self.assertIn("MO: 50", report)
            self.assertIn("MO core (tier-1): 30", report)
            self.assertIn("Services loaded: 8", report)
            self.assertIn("Query masks loaded: 10", report)
            self.assertIn("Реабилитация: 90", report)
            self.assertIn("30 GEO", report)
            self.assertIn("3 query masks", report)
            self.assertIn("90 queries", report)
            self.assertIn("Duplicates removed: 4", report)
            self.assertIn("Total unique Wordstat queries: 2176", report)

            wordstat = (output / "wordstat_queries.txt").read_text(encoding="utf-8")
            lines = wordstat.splitlines()
            self.assertEqual(len(lines), 2176)
            self.assertEqual(len(lines), len({comparison_key(line) for line in lines}))
            self.assertTrue(all(lines))
            self.assertNotIn("\n\n", wordstat)
            for line in lines:
                self.assertEqual(line, line.strip().lower())
                self.assertNotIn("  ", line)
                self.assertNotRegex(line, r"[!\[\]+\"]")

            self.assertEqual(
                lines[:2],
                ["нарколог аэропорт", "нарколог метро аэропорт"],
            )

            rehab_lines = (output / "queries_reabilitaciya.txt").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(len(rehab_lines), 90)
            rehab_index = rehab_lines.index("реабилитация зависимых королёв")
            self.assertEqual(
                rehab_lines[rehab_index : rehab_index + 3],
                [
                    "реабилитация зависимых королёв",
                    "реабилитация алкоголиков королёв",
                    "реабилитация наркоманов королёв",
                ],
            )

            narkolog_lines = (output / "queries_narkolog-na-dom.txt").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertIn("нарколог ступино", narkolog_lines)
            self.assertEqual(narkolog_lines.count("нарколог котельники"), 1)
            self.assertIn("нарколог метро котельники", narkolog_lines)
            self.assertEqual(len(narkolog_lines), 215 * 2 + 12 + 50 - 1)

            with (output / "geo_queries.csv").open(encoding="utf-8", newline="") as handle:
                table = list(csv.DictReader(handle))
            self.assertEqual(
                list(table[0].keys()),
                [
                    "service_id",
                    "service_name",
                    "query_base",
                    "geo_type",
                    "geo_name",
                    "geo_slug",
                    "tier",
                    "query",
                ],
            )
            bel = [
                row
                for row in table
                if row["service_id"] == "narkolog-na-dom"
                and row["geo_slug"] == "belorusskaya"
            ]
            self.assertEqual(
                [row["query"] for row in bel],
                ["нарколог белорусская", "нарколог метро белорусская"],
            )
            self.assertEqual(bel[0]["geo_name"], "Белорусская")
            self.assertEqual(bel[0]["tier"], "core-215")
            kotelniki = [
                row for row in table if row["query"] == "нарколог котельники"
            ]
            self.assertEqual(
                [(row["geo_type"], row["geo_slug"]) for row in kotelniki],
                [("metro", "kotelniki"), ("mo", "kotelniki")],
            )

            metro_lines = (output / "queries_metro.txt").read_text(encoding="utf-8").splitlines()
            okrug_lines = (output / "queries_okrug.txt").read_text(encoding="utf-8").splitlines()
            mo_lines = (output / "queries_mo.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(metro_lines), 4 * 215 * 2)
            self.assertEqual(len(okrug_lines), 5 * 12)
            self.assertEqual(len(mo_lines), 4 * 50 + 50 + 30 + 30 + 90)

    def test_cli_filters(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "--service",
                        "kapelnica-na-dom",
                        "--geo-type",
                        "mo",
                        "--input",
                        str(MASTER),
                        "--output-dir",
                        directory,
                    ]
                )
            self.assertEqual(code, 0)
            output = Path(directory)
            lines = (output / "wordstat_queries.txt").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 50)
            self.assertTrue(all(line.startswith("капельница ") for line in lines))
            self.assertFalse((output / "queries_metro.txt").exists())
            self.assertFalse((output / "queries_narkolog-na-dom.txt").exists())
            self.assertIn("Капельница: 50", stdout.getvalue())
            self.assertIn("Services loaded: 1", stdout.getvalue())

    def test_cli_unknown_service(self) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = main(["--service", "missing"])
        self.assertEqual(code, 1)
        self.assertIn("Неизвестная услуга", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
