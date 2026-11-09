"""Offline tests for the episode data pipeline (no network)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from build_episodes import (  # noqa: E402
    SERIES,
    build_episode,
    load_windows,
    parse_fred_csv,
    trailing_average,
    window_stats,
)
from validate_episodes import check_episode  # noqa: E402

CSV = """observation_date,DGS10
2023-03-07,3.97
2023-03-08,3.98
2023-03-09,
2023-03-10,3.70
2023-03-13,.
2023-03-14,3.64
2023-03-15,3.51
2023-03-16,3.58
"""

DEFN = {"id": "bank-run-2023", "name": "Bank run", "kind": "game",
        "start": "2023-03-08", "end": "2023-03-15", "tags": ["bank-run"]}


def fake_fetcher(available: dict[str, list[tuple[str, float]]]):
    return lambda series_id: available.get(series_id, [])


def full_history(value: float = 4.0) -> list[tuple[str, float]]:
    days = ["2022-03-08", "2022-09-01", "2023-03-07", "2023-03-08", "2023-03-10", "2023-03-15"]
    return [(d, value + i * 0.01) for i, d in enumerate(days)]


class ParseTests(unittest.TestCase):
    def test_skips_blanks_and_dots(self):
        obs = parse_fred_csv(CSV)
        self.assertEqual([d for d, _ in obs],
                         ["2023-03-07", "2023-03-08", "2023-03-10", "2023-03-14", "2023-03-15", "2023-03-16"])

    def test_rejects_headerless_input(self):
        with self.assertRaises(ValueError):
            parse_fred_csv("")


class WindowTests(unittest.TestCase):
    def test_start_end_min_max(self):
        stats = window_stats(parse_fred_csv(CSV), "2023-03-08", "2023-03-15")
        self.assertEqual(stats["start"], {"date": "2023-03-08", "value": 3.98})
        self.assertEqual(stats["end"], {"date": "2023-03-15", "value": 3.51})
        self.assertEqual(stats["min"], {"date": "2023-03-15", "value": 3.51})
        self.assertEqual(stats["max"], {"date": "2023-03-08", "value": 3.98})
        self.assertEqual(stats["observations"], 4)

    def test_empty_window(self):
        self.assertIsNone(window_stats(parse_fred_csv(CSV), "2024-01-01", "2024-02-01"))

    def test_trailing_average_excludes_start_day(self):
        obs = [("2022-03-01", 9.0), ("2022-03-10", 1.0), ("2023-01-01", 3.0), ("2023-03-08", 100.0)]
        self.assertAlmostEqual(trailing_average(obs, "2023-03-08"), 2.0)


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.available = {s.id: full_history() for s in SERIES}

    def test_complete_episode_validates(self):
        doc = build_episode(DEFN, fake_fetcher(self.available))
        errors, gaps = check_episode(doc)
        self.assertEqual(errors, [])
        self.assertEqual(gaps, [])
        self.assertEqual(doc["window"]["calendar_days"], 7)
        self.assertAlmostEqual(doc["window"]["dt_years"], 7 / 365, places=6)
        self.assertIn("slope_2s10s_bp", doc["derived"])

    def test_missing_required_series_is_reported_not_fatal(self):
        del self.available["SP500"]
        doc = build_episode(DEFN, fake_fetcher(self.available))
        errors, gaps = check_episode(doc)
        self.assertEqual(errors, [])
        self.assertEqual(gaps, ["SP500"])
        self.assertIn("note", doc["missing"][0])

    def test_fallback_series_is_recorded(self):
        self.available["DTWEXM"] = self.available.pop("DTWEXBGS")
        doc = build_episode(DEFN, fake_fetcher(self.available))
        self.assertEqual(doc["substitutions"], {"DTWEXBGS": "DTWEXM"})
        self.assertEqual(doc["series"]["DTWEXBGS"]["source"], "FRED:DTWEXM")


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.doc = build_episode(DEFN, fake_fetcher({s.id: full_history() for s in SERIES}))

    def test_catches_unsorted_path(self):
        self.doc["series"]["DGS10"]["daily"].reverse()
        errors, _ = check_episode(self.doc)
        self.assertTrue(any("strictly increasing" in e for e in errors))

    def test_catches_silently_dropped_required_series(self):
        del self.doc["series"]["DGS2"]
        errors, _ = check_episode(self.doc)
        self.assertTrue(any("DGS2" in e for e in errors))

    def test_flags_partial_coverage_of_a_required_series(self):
        sp = self.doc["series"]["SP500"]
        sp["daily"] = sp["daily"][-1:]
        sp["start"] = sp["end"] = sp["min"] = sp["max"] = {"date": sp["daily"][0][0], "value": sp["daily"][0][1]}
        sp["observations"] = 1
        long_window = dict(DEFN, start="2023-03-01")
        self.doc["window"].update(start=long_window["start"], calendar_days=14, dt_years=round(14 / 365, 6))
        for sid, series in self.doc["series"].items():
            if sid != "SP500":
                series["daily"].insert(0, ["2023-03-01", series["daily"][0][1]])
                series["observations"] += 1
                series["start"] = {"date": "2023-03-01", "value": series["daily"][0][1]}
        errors, gaps = check_episode(self.doc)
        self.assertEqual(errors, [])
        self.assertTrue(any(g.startswith("SP500 (partial") for g in gaps))

    def test_catches_bad_dt_years(self):
        self.doc["window"]["dt_years"] = 1.0
        errors, _ = check_episode(self.doc)
        self.assertTrue(any("dt_years" in e for e in errors))


class WindowFileTests(unittest.TestCase):
    def test_windows_are_well_formed(self):
        windows = load_windows()
        self.assertEqual(sum(w["kind"] == "game" for w in windows), 9)
        self.assertEqual(sum(w["kind"] == "practice" for w in windows), 5)
        for w in windows:
            self.assertLess(w["start"], w["end"], w["id"])


if __name__ == "__main__":
    unittest.main()
