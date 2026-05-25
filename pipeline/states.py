"""State reference data: FIPS, USPS abbreviation, 2020 apportionment population.

Apportionment populations are the official 2020 Census figures used to
apportion the 435 seats (resident population + overseas federal personnel).
Source: US Census Bureau, 2020 Census Apportionment.
DC and territories are excluded (no voting House representation).
"""
from __future__ import annotations

# name: (fips, usps, apportionment_population_2020)
STATES: dict[str, tuple[str, str, int]] = {
    "Alabama": ("01", "AL", 5030053),
    "Alaska": ("02", "AK", 736081),
    "Arizona": ("04", "AZ", 7158923),
    "Arkansas": ("05", "AR", 3013756),
    "California": ("06", "CA", 39576757),
    "Colorado": ("08", "CO", 5782171),
    "Connecticut": ("09", "CT", 3608298),
    "Delaware": ("10", "DE", 990837),
    "Florida": ("12", "FL", 21570527),
    "Georgia": ("13", "GA", 10725274),
    "Hawaii": ("15", "HI", 1460137),
    "Idaho": ("16", "ID", 1841377),
    "Illinois": ("17", "IL", 12822739),
    "Indiana": ("18", "IN", 6790280),
    "Iowa": ("19", "IA", 3192406),
    "Kansas": ("20", "KS", 2940865),
    "Kentucky": ("21", "KY", 4509342),
    "Louisiana": ("22", "LA", 4661468),
    "Maine": ("23", "ME", 1363582),
    "Maryland": ("24", "MD", 6185278),
    "Massachusetts": ("25", "MA", 7033469),
    "Michigan": ("26", "MI", 10084442),
    "Minnesota": ("27", "MN", 5709752),
    "Mississippi": ("28", "MS", 2963914),
    "Missouri": ("29", "MO", 6160281),
    "Montana": ("30", "MT", 1085407),
    "Nebraska": ("31", "NE", 1963333),
    "Nevada": ("32", "NV", 3108462),
    "New Hampshire": ("33", "NH", 1379089),
    "New Jersey": ("34", "NJ", 9294493),
    "New Mexico": ("35", "NM", 2120220),
    "New York": ("36", "NY", 20215751),
    "North Carolina": ("37", "NC", 10453948),
    "North Dakota": ("38", "ND", 779702),
    "Ohio": ("39", "OH", 11808848),
    "Oklahoma": ("40", "OK", 3963516),
    "Oregon": ("41", "OR", 4241507),
    "Pennsylvania": ("42", "PA", 13011844),
    "Rhode Island": ("44", "RI", 1098163),
    "South Carolina": ("45", "SC", 5124712),
    "South Dakota": ("46", "SD", 887770),
    "Tennessee": ("47", "TN", 6916897),
    "Texas": ("48", "TX", 29183290),
    "Utah": ("49", "UT", 3275252),
    "Vermont": ("50", "VT", 643503),
    "Virginia": ("51", "VA", 8654542),
    "Washington": ("53", "WA", 7715946),
    "West Virginia": ("54", "WV", 1795045),
    "Wisconsin": ("55", "WI", 5897473),
    "Wyoming": ("56", "WY", 577719),
}

FIPS_TO_NAME: dict[str, str] = {fips: name for name, (fips, _u, _p) in STATES.items()}
FIPS_TO_USPS: dict[str, str] = {fips: usps for _n, (fips, usps, _p) in STATES.items()}

# Total apportionment population of the 50 states.
TOTAL_APPORTIONMENT_POP: int = sum(p for _f, _u, p in STATES.values())

# Smallest state population -> the divisor used by the "Wyoming Rule".
SMALLEST_STATE_POP: int = min(p for _f, _u, p in STATES.values())
