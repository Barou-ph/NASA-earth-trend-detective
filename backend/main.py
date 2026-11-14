"""Earth Trend Detective API. Run: uvicorn backend.main:app --reload"""
import json, math, pathlib, concurrent.futures as cf
import numpy as np, pandas as pd, requests
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from scipy import stats

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "cache"; CACHE.mkdir(exist_ok=True)
URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
VARS = json.load(open(ROOT / "variables.json", encoding="utf-8"))
app = FastAPI(title="Earth Trend Detective")

def fetch(lat, lon, par, y0, y1):
    f = CACHE / f"{par}_{lat:.2f}_{lon:.2f}_{y0}_{y1}.json"
    if f.exists():
        d = json.load(open(f))
    else:
        r = requests.get(URL, params=dict(parameters=par, community="AG", longitude=lon,
                         latitude=lat, start=y0, end=y1, format="JSON"), timeout=60)
        if r.status_code != 200:
            raise HTTPException(502, f"NASA POWER error {r.status_code}")
        d = r.json()["properties"]["parameter"][par]
        json.dump(d, open(f, "w"))
    rows = [(int(k[:4]) + (int(k[4:]) - .5) / 12, int(k[4:]), v)
            for k, v in d.items() if k[4:] != "13" and v > -990]
    return pd.DataFrame(rows, columns=["t", "m", "v"])

def analyze(df, deseason=True, annual=False):
    d = df.copy()
    if deseason:
        d["v"] -= d.groupby("m")["v"].transform("mean")
    if annual:
        d["y"] = d.t.astype(int)
        g = d.groupby("y").v.agg(["mean", "count"]); g = g[g["count"] >= 6]
        d = pd.DataFrame({"t": g.index + .5, "v": g["mean"].values})
    n = len(d)
    if n < 8:
        raise HTTPException(422, "Need at least 8 data points")
    t, v = d.t.values, d.v.values
    lr = stats.linregress(t, v)
    res = v - (lr.intercept + lr.slope * t)
    r1 = float(np.corrcoef(res[:-1], res[1:])[0, 1])
    neff = max(3.0, n * (1 - r1) / (1 + r1)) if r1 > 0 else float(n)   # autocorrelation-adjusted
    se = lr.stderr * math.sqrt((n - 2) / (neff - 2))
    p_t = float(2 * stats.t.sf(abs(lr.slope / se), neff - 2)); tc = stats.t.ppf(.975, neff - 2)
    tau, p_mk = stats.kendalltau(t, v); sen = stats.theilslopes(v, t)[0]
    return dict(n=n, slope=lr.slope, ci=[lr.slope - tc * se, lr.slope + tc * se], p_t=p_t,
                p_mk=float(p_mk), tau=float(tau), sen=float(sen), r1=r1, n_eff=neff,
                total=lr.slope * (t[-1] - t[0]), span=float(t[-1] - t[0]),
                sig=bool(p_t < .05 and p_mk < .05),
                t=t.tolist(), v=v.tolist(), fit=[lr.intercept + lr.slope * t[0], lr.intercept + lr.slope * t[-1]])

def verdict(a, meta, name):
    u, dr = meta["unit"], ("increasing" if a["slope"] > 0 else "decreasing")
    drv = "tăng" if a["slope"] > 0 else "giảm"
    s, tot, sp = f"{a['slope']:.3g}", f"{a['total']:.3g}", f"{a['span']:.0f}"
    if a["sig"]:
        return dict(en=f"{name['en']} shows a significant {dr} trend: {s} {u}/year ({tot} {u} over {sp} years). Both the t-test (autocorrelation-adjusted) and Mann-Kendall give p<0.05.",
                    vi=f"{name['vi']} có xu hướng {drv} đáng kể: {s} {u}/năm ({tot} {u} trong {sp} năm). Cả t-test (đã hiệu chỉnh tự tương quan) lẫn Mann-Kendall đều có p<0,05.")
    return dict(en=f"No significant trend for {name['en']} (slope {s} {u}/year; at least one test has p≥0.05). A longer record may change this.",
                vi=f"Chưa có xu hướng đáng kể cho {name['vi']} (độ dốc {s} {u}/năm; ít nhất một kiểm định có p≥0,05). Chuỗi dài hơn có thể thay đổi kết quả.")

def meta_of(var):
    m = next((x for x in VARS if x["id"] == var), None)
    if not m: raise HTTPException(404, "Unknown variable")
    return m

@app.get("/api/variables")
def variables(): return VARS

@app.get("/api/analyze")
def api_analyze(lat: float, lon: float, var: str, start: int = 2000, end: int = 2024,
                deseason: bool = True, annual: bool = False):
    m = meta_of(var); a = analyze(fetch(lat, lon, var, start, end), deseason, annual)
    a["verdict"] = verdict(a, m, m["name"]); return a

@app.get("/api/grid")
def api_grid(lat: float, lon: float, var: str, start: int = 2000, end: int = 2024, step: float = 1.0):
    """3x3 grid around the point -> trend per cell (the 'where' of the challenge)."""
    meta_of(var); pts = [(lat + i * step, lon + j * step) for i in (-1, 0, 1) for j in (-1, 0, 1)]
    def one(p):
        try:
            a = analyze(fetch(p[0], p[1], var, start, end), True, True)
            return dict(lat=p[0], lon=p[1], slope=a["slope"], p=a["p_t"], sig=a["p_t"] < .05 and a["p_mk"] < .05)
        except Exception:
            return None
    with cf.ThreadPoolExecutor(3) as ex:
        return [r for r in ex.map(one, pts) if r]

app.mount("/", StaticFiles(directory=ROOT.parent / "frontend", html=True), name="web")
