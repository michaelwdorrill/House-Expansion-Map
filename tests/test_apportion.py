"""Validate Huntington-Hill against the real 2020 apportionment of 435 seats."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from apportion import apportion  # noqa: E402

# Official 2020 Census apportionment result (seats per state).
ACTUAL_2020 = {
    "Alabama": 7, "Alaska": 1, "Arizona": 9, "Arkansas": 4, "California": 52,
    "Colorado": 8, "Connecticut": 5, "Delaware": 1, "Florida": 28, "Georgia": 14,
    "Hawaii": 2, "Idaho": 2, "Illinois": 17, "Indiana": 9, "Iowa": 4, "Kansas": 4,
    "Kentucky": 6, "Louisiana": 6, "Maine": 2, "Maryland": 8, "Massachusetts": 9,
    "Michigan": 13, "Minnesota": 8, "Mississippi": 4, "Missouri": 8, "Montana": 2,
    "Nebraska": 3, "Nevada": 4, "New Hampshire": 2, "New Jersey": 12, "New Mexico": 3,
    "New York": 26, "North Carolina": 14, "North Dakota": 1, "Ohio": 15,
    "Oklahoma": 5, "Oregon": 6, "Pennsylvania": 17, "Rhode Island": 2,
    "South Carolina": 7, "South Dakota": 1, "Tennessee": 9, "Texas": 38, "Utah": 4,
    "Vermont": 1, "Virginia": 11, "Washington": 10, "West Virginia": 2,
    "Wisconsin": 8, "Wyoming": 1,
}


def test_reproduces_2020_apportionment():
    result = apportion(435)
    assert sum(result.values()) == 435
    mismatches = {s: (result[s], ACTUAL_2020[s]) for s in ACTUAL_2020 if result[s] != ACTUAL_2020[s]}
    assert not mismatches, f"seat mismatches (got, expected): {mismatches}"


def test_seat_count_scales():
    for n in (435, 573, 692, 1000, 1500):
        result = apportion(n)
        assert sum(result.values()) == n
        assert all(v >= 1 for v in result.values())


if __name__ == "__main__":
    test_reproduces_2020_apportionment()
    test_seat_count_scales()
    print("OK: Huntington-Hill reproduces the 2020 apportionment.")
