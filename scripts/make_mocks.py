"""Regenerate frontend/mock/*.json from a running backend (default http://127.0.0.1:8000).
Real NASA POWER numbers for HCMC; the upload/AOD/NO2 mocks use a synthetic CSV (no real file yet).
Usage: python scripts/make_mocks.py [base_url]"""
import io, json, pathlib, sys, math
import numpy as np, requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
OUT = pathlib.Path(__file__).resolve().parent.parent / "frontend" / "mock"; OUT.mkdir(parents=True, exist_ok=True)

def rnd(x, d=7):
    if isinstance(x, float): return float(f"{x:.{d}g}") if x else 0.0
    if isinstance(x, list): return [rnd(i, d) for i in x]
    if isinstance(x, dict): return {k: (v if k in ("t",) and False else rnd(v, d)) for k, v in x.items()}
    return x

def save(name, data):
    (OUT / f"{name}.json").write_text(json.dumps(rnd(data), ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("wrote", name)

def get(path, **kw):
    r = requests.get(BASE + path, params=kw, timeout=300); r.raise_for_status(); return r.json()

save("variables", get("/api/variables")); save("cities", get("/api/cities"))
presets = get("/api/presets")
for p in presets: p["available"] = True                      # mock mode pretends the crawl is done
save("presets", presets)
save("analyze", get("/api/analyze", city="hcm", var="T2M"))
save("lag", get("/api/lag", city="hcm", a="T2M", b="RH2M"))
save("anomaly", get("/api/anomaly", city="hcm", var="T2M"))
save("ranking", get("/api/ranking", var="CLOUD_AMT", region="all"))     # shows opposite trends
save("scan", get("/api/scan", city="hcm"))
save("summary", get("/api/summary", city="hcm", var="T2M", b="RH2M"))
save("grid", get("/api/grid", lat=10.78, lon=106.7, var="T2M"))

# upload: synthetic Giovanni-like CSV pushed through the real endpoint
rng = np.random.default_rng(1); lines = ["# synthetic sample (mock only)", "Time,mean_AOD"]
for y in range(2005, 2025):
    for m in range(1, 13):
        lines.append(f"{y}-{m:02d}-01T00:00:00Z,{0.3 + 0.1 * math.sin(2 * math.pi * m / 12) + 0.004 * (y - 2005) + rng.normal(0, .03):.4f}")
r = requests.post(BASE + "/api/upload", params={"name": "AOD (mock)"}, files={"file": ("aod_mock.csv", "\n".join(lines))}, timeout=60)
r.raise_for_status(); save("upload", r.json())
