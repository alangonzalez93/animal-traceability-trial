"""
Generates static CSV fixtures for tests and manual FE testing.

Fixed UUIDs so the files are stable across runs:
  - 1 field:  FIELD_ID
  - 10 lots:  LOT_IDS

Usage:
    uv run python tests/fixtures/generate.py

The generated files are committed to the repo. Re-run only if you need
to change the shape of the data.
"""

import csv
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

FIELD_ID = "c0ffee00-0000-0000-0000-000000000001"
LOT_IDS = [f"10000000-0000-0000-0000-{i:012d}" for i in range(1, 11)]
LOT_NAMES = [f"Lot-{i:02d}" for i in range(1, 11)]

BREEDS = ["ANGUS", "HEREFORD", "BRAHMAN", "LIMOUSIN", "SHORTHORN", "CRIOLLO"]
CATEGORIES = ["CALF", "STEER", "COW", "BULL", "HEIFER"]
BASE_BIRTH = date(2019, 1, 1)
OCCURRED_AT = "2025-01-01T00:00:00Z"

# 4 weigh dates, ~45 days apart, between 2026-01-01 and 2026-06-10
WEIGH_DATES = [
    datetime(2026, 1, 15, tzinfo=timezone.utc),
    datetime(2026, 3, 1, tzinfo=timezone.utc),
    datetime(2026, 4, 15, tzinfo=timezone.utc),
    datetime(2026, 6, 1, tzinfo=timezone.utc),
]

OUT = Path(__file__).parent


def generate_animals(n: int = 1200) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        birth = BASE_BIRTH + timedelta(days=random.randint(0, 365 * 4))
        rows.append({
            "tag_number": f"TAG-{i:05d}",
            "breed": random.choice(BREEDS),
            "category": random.choice(CATEGORIES),
            "birth_date": str(birth),
            "lot_id": random.choice(LOT_IDS),
            "occurred_at": OCCURRED_AT,
        })
    return rows


LOW_ADG_LOTS = {
    "10000000-0000-0000-0000-000000000004",
    "10000000-0000-0000-0000-000000000005",
}


def generate_weight_events(animals: list[dict]) -> list[dict]:
    """4 weight measurements per animal, 30 days apart.
    Lots 4 and 5 use a low ADG (0.05–0.15 kg/day); others use 0.6–1.1 kg/day.
    """
    random.seed(42)
    rows = []
    for animal in animals:
        tag = animal["tag_number"]
        low = animal["lot_id"] in LOW_ADG_LOTS
        base_weight = random.uniform(180.0, 240.0)
        adg = random.uniform(0.05, 0.15) if low else random.uniform(0.6, 1.1)
        for i, weigh_date in enumerate(WEIGH_DATES):
            weight = round(base_weight + adg * i * 30, 1)
            rows.append({
                "tag_number": tag,
                "occurred_at": weigh_date.isoformat(),
                "weight_kg": str(weight),
            })
    return rows


def generate_vaccination_events(tag_numbers: list[str]) -> list[dict]:
    """One vaccination per animal."""
    return [
        {
            "tag_number": tag,
            "occurred_at": "2026-01-10T00:00:00+00:00",
            "vaccine_name": random.choice(["FMD", "IBR", "BVD", "Leptospira"]),
        }
        for tag in tag_numbers
    ]


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    animals = generate_animals(50_000)
    tag_numbers = [a["tag_number"] for a in animals]

    write_csv(OUT / "animals.csv", animals)
    print(f"✓ animals.csv          — {len(animals)} rows")

    weight_events = generate_weight_events(animals)
    write_csv(OUT / "events_weight.csv", weight_events)
    print(f"✓ events_weight.csv    — {len(weight_events)} rows  (4 per animal)")

    vacc_events = generate_vaccination_events(tag_numbers)
    write_csv(OUT / "events_vaccination.csv", vacc_events)
    print(f"✓ events_vaccination.csv — {len(vacc_events)} rows  (1 per animal)")
