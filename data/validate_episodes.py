#!/usr/bin/env python3
"""Check built episode files against the schema and report data gaps.

    python3 data/validate_episodes.py               # check data/episodes/*.json
    python3 data/validate_episodes.py --strict      # also fail on gaps in required series

Exit codes: 0 all files valid; 1 a schema error; 2 a required series is
missing (only with --strict).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(DATA_DIR))
from build_episodes import SCHEMA_VERSION, SERIES  # noqa: E402

REQUIRED_SERIES = {s.id for s in SERIES if s.required}
TOP_KEYS = {
    "schema_version": int,
    "id": str,
    "name": str,
    "kind": str,
    "tags": list,
    "window": dict,
    "series": dict,
    "missing": list,
    "substitutions": dict,
    "derived": dict,
    "built_at": str,
    "builder": str,
}
POINT_KEYS = ("start", "end", "min", "max")
# A required series whose first or last observation sits more than this many
# calendar days inside the window covers only part of it (weekends and
# holidays alone never exceed 4 days).
COVERAGE_SLACK_DAYS = 5


def _is_date(value: object) -> bool:
    try:
        date.fromisoformat(str(value))
        return True
    except ValueError:
        return False


def check_episode(doc: dict) -> tuple[list[str], list[str]]:
    """Return (schema errors, required-series gaps) for one episode file."""
    errors: list[str] = []
    for key, kind in TOP_KEYS.items():
        if key not in doc:
            errors.append(f"missing key '{key}'")
        elif not isinstance(doc[key], kind):
            errors.append(f"'{key}' should be {kind.__name__}")
    if errors:
        return errors, []

    if doc["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version {doc['schema_version']} != {SCHEMA_VERSION}")
    if doc["kind"] not in ("game", "practice"):
        errors.append(f"kind '{doc['kind']}' is not game or practice")

    win = doc["window"]
    start, end = win.get("start"), win.get("end")
    if not (_is_date(start) and _is_date(end)) or not start < end:
        errors.append("window start/end must be ISO dates with start < end")
    else:
        days = (date.fromisoformat(end) - date.fromisoformat(start)).days
        if win.get("calendar_days") != days:
            errors.append("window.calendar_days does not match the dates")
        if abs(win.get("dt_years", -1) - days / 365) > 1e-5:
            errors.append("window.dt_years does not equal calendar_days / 365")

    for sid, s in doc["series"].items():
        prefix = f"series {sid}"
        for k in POINT_KEYS:
            p = s.get(k)
            if not isinstance(p, dict) or not _is_date(p.get("date")) or not isinstance(p.get("value"), (int, float)):
                errors.append(f"{prefix}: '{k}' must be {{date, value}}")
        daily = s.get("daily")
        if not isinstance(daily, list) or not daily:
            errors.append(f"{prefix}: daily path is empty")
            continue
        dates = [d for d, _ in daily]
        if dates != sorted(dates) or len(dates) != len(set(dates)):
            errors.append(f"{prefix}: daily dates must be strictly increasing")
        if start and end and (dates[0] < start or dates[-1] > end):
            errors.append(f"{prefix}: daily path falls outside the window")
        if s.get("observations") != len(daily):
            errors.append(f"{prefix}: observations count does not match daily path")
        values = [v for _, v in daily]
        if s.get("min", {}).get("value") != min(values) or s.get("max", {}).get("value") != max(values):
            errors.append(f"{prefix}: min/max do not match the daily path")
        if s.get("start", {}).get("date") != dates[0] or s.get("end", {}).get("date") != dates[-1]:
            errors.append(f"{prefix}: start/end do not match the daily path")

    listed_missing = {m.get("id") for m in doc["missing"]}
    for sid in REQUIRED_SERIES:
        if sid not in doc["series"] and sid not in listed_missing:
            errors.append(f"required series {sid} is neither present nor listed as missing")
    gaps = sorted(REQUIRED_SERIES & listed_missing)
    if not errors and start and end:
        for sid in sorted(REQUIRED_SERIES & set(doc["series"])):
            first = doc["series"][sid]["start"]["date"]
            last = doc["series"][sid]["end"]["date"]
            late = (date.fromisoformat(first) - date.fromisoformat(start)).days
            early = (date.fromisoformat(end) - date.fromisoformat(last)).days
            if late > COVERAGE_SLACK_DAYS or early > COVERAGE_SLACK_DAYS:
                gaps.append(f"{sid} (partial: {first} to {last})")
    return errors, gaps


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--strict", action="store_true", help="fail when a required series is missing")
    args = parser.parse_args(argv)

    paths = args.paths or sorted((DATA_DIR / "episodes").glob("*.json"))
    if not paths:
        print("no episode files found; run data/build_episodes.py first")
        return 1

    any_errors = any_gaps = False
    for path in paths:
        doc = json.loads(path.read_text())
        errors, gaps = check_episode(doc)
        status = "FAIL" if errors else ("GAPS" if gaps else "ok")
        detail = "; ".join(errors) if errors else (f"missing required: {', '.join(gaps)}" if gaps else "")
        print(f"{status:<5} {path.stem:<28} {detail}")
        any_errors |= bool(errors)
        any_gaps |= bool(gaps)

    if any_errors:
        return 1
    if any_gaps and args.strict:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
