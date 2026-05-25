# House-Expansion-Map

An interactive visualizer for expanding the US House of Representatives. Pick a House size
(or people-per-representative) and the map redraws congressional districts nationwide &mdash;
staying inside state lines, balanced by population, and colored by partisan lean &mdash; with
live summaries of the partisan balance and how far the result departs from proportionality.

The premise: smaller districts are harder to gerrymander safely, and every seat is a smaller
slice of a larger chamber, so a gerrymander's grip on power shrinks as the House grows. At the
435-seat stop you can toggle between the **actual current districts** (119th Congress) and a
neutral redraw to see today's real distortion; the **Lessons** tab walks through what the
results say about expansion and gerrymandering, including the per-seat power (1/N) dilution.

**Live site:** served from `docs/` via GitHub Pages.

## How it works

1. **Apportionment** &mdash; seats are split among the 50 states with the Huntington&ndash;Hill
   method (the real method). At N=435 it reproduces the actual 2020 apportionment exactly.
2. **Districting** &mdash; within each state, a *shortest-splitline variant* recursively bisects
   the population along its principal axis. It never looks at votes, so maps are partisan-blind.
3. **Partisan lean** &mdash; each redrawn district sums presidential votes from the units inside
   it. A multi-cycle blend (2016+2020+2024) is the default; single cycles are selectable.
4. **Metrics** &mdash; seats-vs-proportional and the efficiency gap quantify distortion.

See the **"How it works"** tab in the app for the full methodology and source links.

## Architecture

GitHub Pages is static-only, so all heavy computation happens **offline** in a Python pipeline
that emits static files; the browser only recomputes ratings/summaries (instant) and swaps
scenario files when the slider moves.

```
pipeline/            offline build (Python)
  sources.py         data source URLs + citations
  download.py        fetch raw data -> data/raw/
  states.py          FIPS / USPS / 2020 apportionment populations
  apportion.py       Huntington-Hill
  units.py           county geometry + population + votes (joined on FIPS)
  districting.py     equal-area county subdivision + splitline bisection
  realmap.py         actual 119th-Congress districts (TIGER) + areal vote join
  build.py           generate per-scenario GeoJSON -> docs/data/
docs/                static site (GitHub Pages root)
  index.html app.js styles.css
  vendor/d3.min.js
  data/manifest.json  scenario-<N>.json  states.geojson
tests/               apportionment validation
```

## Data resolution & honesty

This build uses **counties** as the population unit (open data reachable from sandboxed
environments). Counties larger than a district are split into equal-area pieces assuming
uniform density. Districts land within a few percent of equal population; boundaries follow
county-piece edges, not real precinct lines. For full fidelity, swap in Census tracts / VEST
precincts and run `.github/workflows/build-data.yml` on a GitHub runner (unrestricted network).

Sources: county/state geometry (Vega Datasets, from Census TIGER), county population (JHU CSSE,
from Census estimates), county presidential results 2016/2020/2024 (tonmcg), 2020 apportionment
populations (US Census), and current congressional-district boundaries (Census TIGER 2024
`tl_2024_us_cd119`, fetched only by the build Action since census.gov is blocked in sandboxes).

The real-districts baseline uses the actual gerrymandered map but apportions county votes onto
districts by area (counties split across districts), so single-district lean is an estimate, not
a precinct-exact figure. `tl_2024_us_cd119` reflects the 119th Congress as convened; mid-cycle
maps redrawn after that need a newer boundary file dropped into the same pipeline step.

## Build locally

```bash
pip install -r pipeline/requirements.txt
cd pipeline && python download.py && python build.py   # writes docs/data/
python tests/test_apportion.py                          # validation
cd docs && python -m http.server 8000                   # open http://localhost:8000
```

## Deploy

Either enable **Settings &rarr; Pages &rarr; Deploy from branch &rarr; `/docs`**, or use the
included `pages.yml` workflow (Settings &rarr; Pages &rarr; GitHub Actions).
