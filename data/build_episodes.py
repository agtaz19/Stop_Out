#!/usr/bin/env python3
"""Build Stop-Out episode data files from FRED.

For every window in data/episode_windows.json this writes
data/episodes/<id>.json with, for each series: the start and end values,
the lowest and highest values inside the window (with dates), and the full
daily path. The engine uses the path for worst-point margin checks.

Standard library only. Downloads go through FRED's public CSV endpoint and
are cached under data/cache/ so a rebuild does not refetch.

    python3 data/build_episodes.py                # build every window
    python3 data/build_episodes.py --only bank-run-2023
    python3 data/build_episodes.py --offline      # use the cache only
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.request
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Iterable

SCHEMA_VERSION = 1
DATA_DIR = Path(__file__).resolve().parent
WINDOWS_FILE = DATA_DIR / "episode_windows.json"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={id}&cosd={start}"
HISTORY_START = "1990-01-01"
TRAILING_DAYS = 365

Observation = tuple[str, float]
SeriesFetcher = Callable[[str], list[Observation]]


@dataclass(frozen=True)
class SeriesSpec:
    id: str
    label: str
    unit: str
    required: bool
    fallbacks: tuple[str, ...] = field(default_factory=tuple)
    note: str = ""


SERIES: tuple[SeriesSpec, ...] = (
    SeriesSpec("DGS3MO", "3-month Treasury bill", "percent", True),
    SeriesSpec("DGS2", "2-year Treasury", "percent", True),
    SeriesSpec("DGS5", "5-year Treasury", "percent", True),
    SeriesSpec("DGS10", "10-year Treasury", "percent", True),
    SeriesSpec("DGS30", "30-year Treasury", "percent", True),
    SeriesSpec("VIXCLS", "VIX", "index", True),
    SeriesSpec(
        "SP500",
        "S&P 500 (price)",
        "index",
        True,
        note="FRED carries only about the last 10 years and has licensing limits; "
        "a total-return source is still to be chosen.",
    ),
    SeriesSpec("DFF", "Effective fed funds", "percent", False),
    SeriesSpec("DFII10", "10-year TIPS real yield", "percent", False),
    SeriesSpec("T10YIE", "10-year breakeven inflation", "percent", False),
    SeriesSpec("DTWEXBGS", "Broad dollar index", "index", False, fallbacks=("DTWEXM",)),
)


# --- Parsing and statistics -------------------------------------------------


def parse_fred_csv(text: str) -> list[Observation]:
    """Parse a FRED graph CSV into (date, value) pairs, skipping blanks and '.'."""
    reader = csv.reader(io.StringIO(text))
    header = next(reader, None)
    if not header or len(header) < 2:
        raise ValueError("FRED CSV has no header row")
    out: list[Observation] = []
    for row in reader:
        if len(row) < 2:
            continue
        day, raw = row[0].strip(), row[1].strip()
        if not raw or raw == ".":
            continue
        date.fromisoformat(day)  # validates the date
        out.append((day, float(raw)))
    out.sort(key=lambda o: o[0])
    return out


def window_slice(points: Iterable[Observation], start: str, end: str) -> list[Observation]:
    return [p for p in points if start <= p[0] <= end]


def window_stats(points: list[Observation], start: str, end: str) -> dict | None:
    """Start, end, min, and max inside [start, end], plus the daily path.

    Start is the first observation on or after `start`; end is the last on or
    before `end`. Returns None when the window holds no observations.
    """
    inside = window_slice(points, start, end)
    if not inside:
        return None
    low = min(inside, key=lambda o: (o[1], o[0]))
    high = max(inside, key=lambda o: (o[1], o[0]))
    point = lambda o: {"date": o[0], "value": o[1]}  # noqa: E731
    return {
        "start": point(inside[0]),
        "end": point(inside[-1]),
        "min": point(low),
        "max": point(high),
        "observations": len(inside),
        "daily": [[d, v] for d, v in inside],
    }


def trailing_average(points: list[Observation], before: str, days: int = TRAILING_DAYS) -> float | None:
    """Mean of observations in [before - days, before)."""
    cutoff = (date.fromisoformat(before) - timedelta(days=days)).isoformat()
    values = [v for d, v in points if cutoff <= d < before]
    return sum(values) / len(values) if values else None


# --- Episode assembly -------------------------------------------------------


def build_episode(defn: dict, fetch: SeriesFetcher) -> dict:
    start, end = defn["start"], defn["end"]
    days = (date.fromisoformat(end) - date.fromisoformat(start)).days
    if days <= 0:
        raise ValueError(f"{defn['id']}: end must be after start")

    series: dict[str, dict] = {}
    missing: list[dict] = []
    substitutions: dict[str, str] = {}
    histories: dict[str, list[Observation]] = {}

    for spec in SERIES:
        stats = None
        used = spec.id
        for candidate in (spec.id, *spec.fallbacks):
            history = fetch(candidate)
            stats = window_stats(history, start, end)
            if stats is not None:
                used = candidate
                histories[spec.id] = history
                break
        if stats is None:
            entry = {"id": spec.id, "required": spec.required, "reason": "no observations in window"}
            if spec.note:
                entry["note"] = spec.note
            missing.append(entry)
            continue
        if used != spec.id:
            substitutions[spec.id] = used
        series[spec.id] = {
            "label": spec.label,
            "unit": spec.unit,
            "source": f"FRED:{used}",
            **stats,
        }

    derived: dict[str, object] = {}
    if "DGS10" in histories:
        avg = trailing_average(histories["DGS10"], series["DGS10"]["start"]["date"])
        derived["dgs10_trailing_1y_avg"] = None if avg is None else round(avg, 4)
    if "DGS2" in series and "DGS10" in series:
        derived["slope_2s10s_bp"] = {
            edge: round((series["DGS10"][edge]["value"] - series["DGS2"][edge]["value"]) * 100, 2)
            for edge in ("start", "end")
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "id": defn["id"],
        "name": defn["name"],
        "kind": defn["kind"],
        "tags": list(defn.get("tags", [])),
        "window": {
            "start": start,
            "end": end,
            "calendar_days": days,
            "dt_years": round(days / 365, 6),
        },
        "series": series,
        "missing": missing,
        "substitutions": substitutions,
        "derived": derived,
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "builder": "data/build_episodes.py",
    }


# --- FRED access -------------------------------------------------------------


def make_fred_fetcher(cache_dir: Path, offline: bool) -> SeriesFetcher:
    cache_dir.mkdir(parents=True, exist_ok=True)
    memo: dict[str, list[Observation]] = {}

    def fetch(series_id: str) -> list[Observation]:
        if series_id in memo:
            return memo[series_id]
        path = cache_dir / f"{series_id}.csv"
        if path.exists():
            text = path.read_text()
        elif offline:
            raise FileNotFoundError(f"{series_id} is not cached and --offline was given")
        else:
            url = FRED_CSV_URL.format(id=series_id, start=HISTORY_START)
            with urllib.request.urlopen(url, timeout=60) as resp:
                text = resp.read().decode("utf-8")
            path.write_text(text)
        memo[series_id] = parse_fred_csv(text)
        return memo[series_id]

    return fetch


def load_windows(path: Path = WINDOWS_FILE) -> list[dict]:
    doc = json.loads(path.read_text())
    ids = [e["id"] for e in doc["episodes"]]
    if len(ids) != len(set(ids)):
        raise ValueError("episode ids must be unique")
    return doc["episodes"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", help="episode ids to build (default: all)")
    parser.add_argument("--out", type=Path, default=DATA_DIR / "episodes")
    parser.add_argument("--cache", type=Path, default=DATA_DIR / "cache")
    parser.add_argument("--offline", action="store_true", help="use cached CSVs only")
    args = parser.parse_args(argv)

    windows = load_windows()
    if args.only:
        unknown = set(args.only) - {w["id"] for w in windows}
        if unknown:
            parser.error(f"unknown episode ids: {', '.join(sorted(unknown))}")
        windows = [w for w in windows if w["id"] in args.only]

    fetch = make_fred_fetcher(args.cache, args.offline)
    args.out.mkdir(parents=True, exist_ok=True)
    for defn in windows:
        episode = build_episode(defn, fetch)
        (args.out / f"{defn['id']}.json").write_text(json.dumps(episode, indent=1) + "\n")
        gaps = ", ".join(m["id"] for m in episode["missing"]) or "none"
        subs = ", ".join(f"{k}->{v}" for k, v in episode["substitutions"].items()) or "none"
        print(f"{defn['id']:<28} {episode['window']['calendar_days']:>4}d  missing: {gaps}  substituted: {subs}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
