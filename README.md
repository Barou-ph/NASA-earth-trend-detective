# Earth Trend Detective (NASA Space Apps 2026)

**Turns NASA satellite and model data into a one-page brief for urban planners and environmental consultants:
what is getting worse, how far to trust each finding, and which directions to consider.**
Details of who it is for, the problem and who pays (hypotheses to validate): [docs/audience.md](docs/audience.md).

    pip install -r requirements.txt
    uvicorn backend.main:app --reload      # open http://127.0.0.1:8000

## What you see
Two pages in one orbital HUD (layout after `UI.html`), switch with the top tabs or the browser back button (`#/` and `#/detail`):
- **Home**: what changed most in the **last 7 days** across the world: the latest 7 days with data versus the normal for the same time of year (earlier years), 22 cities x the NASA POWER indicators with fresh daily data
  (cards with a 30-day sparkline, final 7 days shaded; FDR-passing first; filter All / Rising / Falling / Vietnam / World). One week, not a climate trend; indicators whose data lags more than 10 days (e.g. cloud amount) are skipped.
  The server computes them in the background at start-up (a few minutes on a fresh day), so cards appear as cities finish. Click a card to open it on the detail page.
- **Detail** (2D satellite map, Esri imagery): one dot per city for the indicator you came with (size = size of change, orange = rising, blue = falling, pulsing = still significant when comparing 22 cities).
  **Hover a city for the weekly picture**: the last 30 days with the final 7 days vs normal, plus the 52-week trend. There is no indicator tab here: pick the indicator on the home page or in the lab.

- **City brief** drawer (printable / copyable): trusted findings with an **evidence trust score** (5 checks, traffic light), "worth watching", directions to consider, caveats.
- **Analysis lab** drawer: trend + confidence band, data-quality panel, automatic VI/EN summary, lag, unusual months, variable scan, city ranking + compare, CSV upload; **glossary** drawer.

## How trust is built in
- Trend tests: OLS slope + 95% CI and t-test (lag-1 autocorrelation-adjusted), Mann-Kendall, Sen slope; significant only if both tests agree.
- Many cities or variables tested at once: Benjamini-Hochberg FDR (`q`).
- **Evidence trust score** (`evidence`): strong / moderate / weak / none from five checks (both tests significant, survives outlier removal, same direction in both halves, holds on yearly means, enough data).
  A finding that only just survives FDR (`q >= 0.01`) is capped at moderate.
- Missing months are never interpolated; outliers are flagged, not deleted. Report: [docs/data-quality.md](docs/data-quality.md).
- The suggestions are directions to consider from a rule table in `backend/main.py` (`ACTION_RULES`), not policy advice.

## Reference
- API contract (frozen field names, JSON examples): [docs/api-contract.md](docs/api-contract.md)
- Endpoints: `/api/variables` `/api/cities` `/api/presets` `/api/analyze` `/api/summary` `/api/brief` `/api/globe` `/api/weekly` `/api/highlights` `/api/lag` `/api/anomaly` `/api/ranking` `/api/scan` `/api/grid` `POST /api/upload`
- Add variables in `backend/variables.json`, cities in `backend/cities.json`. NASA POWER responses are cached in `backend/cache/`.
- Data: `python scripts/prepare_hcm_data.py` cleans `nasa_data/data/raw` into `backend/presets/`. Presets: drop `hcm_aod.csv` / `hcm_no2.csv` (Giovanni CSV) into `backend/presets/`, no code change needed.
- Frontend files: `index.html`, `style.css`, `app.js` (lab), `brief.js` (brief, texts), `hud.js` (drawers, layout), `explore.js` (detail map, routing), `home.js` (home page). Leaflet, Plotly and fonts load from CDNs; Esri satellite tiles are used for the map.
- Frontend without a backend: set `USE_MOCK = true` in `frontend/app.js` or open `/?mock=1` (files in `frontend/mock/`, regenerate with `python scripts/make_mocks.py`).

Not built yet: district-level numbers (needs MODIS land-surface temperature and NDVI), validation against ground PM2.5, and a green-space scenario calculator.

Deploy (Render): `render.yaml` is included; connect the repository on render.com and it builds with `pip install -r requirements.txt`
and starts `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Not deployed yet.

Tests (statistics are cross-checked against statsmodels and brute-force Mann-Kendall / Theil-Sen):

    pip install -r requirements-dev.txt
    python -m pytest -q
