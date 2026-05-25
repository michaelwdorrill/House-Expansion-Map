"""Canonical data-source definitions for the pipeline.

Everything here is open data, fetched over HTTPS. We deliberately use
GitHub-hosted mirrors so the pipeline runs in network-restricted
environments (census.gov / dataverse.harvard.edu are often blocked).

For full tract/precinct fidelity, swap COUNTY_* sources for Census
TIGER tracts + VEST precinct results and run in an environment with
access to those hosts (see .github/workflows/build-data.yml).
"""

# County geometry (TopoJSON: counties + states, keyed by FIPS) -- Vega datasets.
GEOMETRY_US_10M = (
    "https://raw.githubusercontent.com/vega/vega-datasets/main/data/us-10m.json"
)

# County population by 5-digit FIPS (2019 Census estimates) -- JHU CSSE lookup.
COUNTY_POPULATION = (
    "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/"
    "csse_covid_19_data/UID_ISO_FIPS_LookUp_Table.csv"
)

# Current congressional district boundaries (119th Congress) -- Census TIGER.
# This is the ACTUAL (gerrymandered) district map, used to build the real-lines
# baseline that the neutral splitline scenarios are compared against. census.gov
# is blocked in sandboxed dev environments, so this only resolves on an
# unrestricted network (the GitHub Actions runner -- see build-data.yml).
CD_BOUNDARIES = (
    "https://www2.census.gov/geo/tiger/TIGER2024/CD/tl_2024_us_cd119.zip"
)

# County-level presidential results by FIPS -- tonmcg.
COUNTY_RESULTS = {
    "PRES16": (
        "https://raw.githubusercontent.com/tonmcg/"
        "US_County_Level_Election_Results_08-24/master/"
        "2016_US_County_Level_Presidential_Results.csv"
    ),
    "PRES20": (
        "https://raw.githubusercontent.com/tonmcg/"
        "US_County_Level_Election_Results_08-24/master/"
        "2020_US_County_Level_Presidential_Results.csv"
    ),
    "PRES24": (
        "https://raw.githubusercontent.com/tonmcg/"
        "US_County_Level_Election_Results_08-24/master/"
        "2024_US_County_Level_Presidential_Results.csv"
    ),
}

# Human-readable provenance, surfaced in the methodology tab.
CITATIONS = [
    {
        "name": "County & state boundaries (us-10m TopoJSON)",
        "source": "Vega Datasets (derived from US Census TIGER/Line)",
        "url": "https://github.com/vega/vega-datasets",
    },
    {
        "name": "County population (2019 estimates)",
        "source": "JHU CSSE UID_ISO_FIPS lookup table (US Census Population Estimates)",
        "url": "https://github.com/CSSEGISandData/COVID-19",
    },
    {
        "name": "County presidential results 2016 / 2020 / 2024",
        "source": "tonmcg/US_County_Level_Election_Results_08-24",
        "url": "https://github.com/tonmcg/US_County_Level_Election_Results_08-24",
    },
    {
        "name": "Apportionment populations (2020 Census)",
        "source": "US Census Bureau, 2020 Census Apportionment",
        "url": "https://www.census.gov/data/tables/2020/dec/2020-apportionment-data.html",
    },
    {
        "name": "Current congressional districts (119th Congress)",
        "source": "US Census Bureau, TIGER/Line 2024 (tl_2024_us_cd119)",
        "url": "https://www2.census.gov/geo/tiger/TIGER2024/CD/",
    },
]
