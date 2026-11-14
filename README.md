# Earth Trend Detective (NASA Space Apps 2026)
Backend FastAPI + frontend Leaflet/Plotly. Data: NASA POWER monthly point API (no key) and Giovanni CSV files.

    pip install -r requirements.txt
    uvicorn backend.main:app --reload      # open http://127.0.0.1:8000

Screens: variable + city/map picker, **automatic VI/EN summary** (rule-based, from the same numbers as the charts), **"Run the HCMC case"** button, trend chart with confidence band and VI/EN verdict,
lag chart (with the "correlation ≠ causation" warning), unusual-months chart, city ranking (Vietnam + 10 world cities, FDR-corrected) + compare, a variable scan, a **data-quality panel** (gaps, outliers, what was dropped), a glossary, an **opposite-trend demo** (cloud cover), CSV upload.

- API contract (frozen field names, JSON examples): [docs/api-contract.md](docs/api-contract.md)
- Endpoints: `/api/variables` `/api/cities` `/api/presets` `/api/analyze` `/api/summary` `/api/lag` `/api/anomaly` `/api/ranking` `/api/scan` `/api/grid` `POST /api/upload`
- Stats: OLS slope + 95% CI (lag-1 autocorrelation-adjusted), Mann-Kendall (Kendall tau), Sen slope.
- Add variables in `backend/variables.json`, cities in `backend/cities.json`. NASA POWER responses are cached in `backend/cache/`.
- Data quality: `python scripts/prepare_hcm_data.py` cleans `nasa_data/data/raw` into `backend/presets/` and writes [docs/data-quality.md](docs/data-quality.md) (what is missing or abnormal, how it was handled, and how sensitive the conclusions are).
- Presets: drop `hcm_aod.csv` / `hcm_no2.csv` (Giovanni CSV) into `backend/presets/`, no code change needed. Raw crawls go to `data/raw/`.
- Frontend without a backend: set `USE_MOCK = true` in `frontend/app.js` or open `/?mock=1` (files in `frontend/mock/`, regenerate with `python scripts/make_mocks.py`).

Deploy (Render): `render.yaml` is included; connect the repository on render.com and it builds with `pip install -r requirements.txt`
and starts `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`. Not deployed yet.

Tests (statistics are cross-checked against statsmodels and brute-force Mann-Kendall / Theil-Sen):

    pip install -r requirements-dev.txt
    python -m pytest -q
