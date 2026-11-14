# Earth Trend Detective (NASA Space Apps 2026)
Backend FastAPI + frontend Leaflet/Plotly. Data: NASA POWER monthly point API (no key).

    pip install -r requirements.txt
    uvicorn backend.main:app --reload      # open http://127.0.0.1:8000

- `GET /api/variables` · `GET /api/analyze?lat&lon&var&start&end&deseason&annual` · `GET /api/grid?...` (3×3 trend map)
- Stats: OLS slope + 95% CI (lag-1 autocorrelation-adjusted), Mann-Kendall (Kendall tau), Sen slope.
- Add variables in `backend/variables.json`. Responses are cached in `backend/cache/`.
