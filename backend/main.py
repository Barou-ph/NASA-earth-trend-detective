"""Earth Trend Detective API. Run: uvicorn backend.main:app --reload
Contract: docs/api-contract.md (field names are frozen; only add, never rename)."""
import csv, io, json, math, pathlib, concurrent.futures as cf
import numpy as np, pandas as pd, requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from scipy import stats

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "cache"; CACHE.mkdir(exist_ok=True)
PRESET_DIR = ROOT / "presets"
URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
MAX_UPLOAD = 5 * 1024 * 1024
LAGS = [0, 1, 2, 3]

def _load(name):
    return json.load(open(ROOT / name, encoding="utf-8"))

VARS = _load("variables.json")
CITIES = _load("cities.json")
PRESETS = _load("presets/presets.json")
app = FastAPI(title="Earth Trend Detective")

# ---------------------------------------------------------------- data access
def fetch(lat, lon, par, y0, y1):
    """Monthly series from NASA POWER (cached on disk). Columns: t (decimal year), m (month), v."""
    f = CACHE / f"{par}_{lat:.2f}_{lon:.2f}_{y0}_{y1}.json"
    d = None
    if f.exists():
        try: d = json.load(open(f))
        except ValueError: d = None                      # corrupt cache -> refetch
    if d is None:
        try:
            r = requests.get(URL, params=dict(parameters=par, community="AG", longitude=lon,
                             latitude=lat, start=y0, end=y1, format="JSON"), timeout=60)
        except requests.RequestException as e:
            raise HTTPException(502, f"Cannot reach NASA POWER: {e.__class__.__name__}")
        if r.status_code != 200:
            raise HTTPException(502, f"NASA POWER error {r.status_code}")
        try: d = r.json()["properties"]["parameter"][par]
        except (KeyError, ValueError):
            raise HTTPException(502, "Unexpected NASA POWER response")
        json.dump(d, open(f, "w"))
    rows = [(int(k[:4]) + (int(k[4:]) - .5) / 12, int(k[4:]), v)
            for k, v in d.items() if k[4:] != "13" and v > -990]
    return pd.DataFrame(rows, columns=["t", "m", "v"])

def parse_series_csv(raw: bytes, min_days: int | None = None):
    """Giovanni-style CSV: '#' lines skipped, first column = time, last column = value.
    Header/metadata lines that do not parse are ignored. Fill values (<= -990, NaN) are dropped.
    Sub-monthly (e.g. daily) data is averaged per month; a month needs >= min_days valid days
    (default 10 for daily-like data, 1 otherwise). What was dropped is reported in df.attrs["parse"]."""
    try: text = raw.decode("utf-8-sig")
    except UnicodeDecodeError: text = raw.decode("latin-1")
    times, vals, info = [], [], dict(rows_numeric=0, fill_dropped=0, bad_dates=0, sub_monthly=False, min_days=1, months_dropped=0)
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 2 or row[0].lstrip().startswith("#") or row[0].rstrip().endswith(":"): continue   # comment / "Key:," metadata line
        try: x = float(row[-1])
        except ValueError: continue                       # header line
        info["rows_numeric"] += 1
        if not math.isfinite(x) or x <= -990:             # fill values (-9999, -3.4e38 ...)
            info["fill_dropped"] += 1; continue
        times.append(row[0].strip()); vals.append(x)
    ts = pd.to_datetime(pd.Series(times, dtype="object"), errors="coerce", utc=True) if times else pd.Series([], dtype="datetime64[ns, UTC]")
    d = pd.DataFrame({"ts": ts, "v": vals})
    info["bad_dates"] = int(d.ts.isna().sum()); d = d.dropna()
    if d.empty:
        raise HTTPException(422, "No valid rows found: need a time column first and a numeric value column last")
    d["y"], d["m"] = d.ts.dt.year, d.ts.dt.month
    g = d.groupby(["y", "m"], as_index=False).v.agg(v="mean", n="count").sort_values(["y", "m"])
    info["sub_monthly"] = bool(len(d) >= 90 and g.n.median() >= 8)
    info["min_days"] = int(min_days if min_days is not None else (10 if info["sub_monthly"] else 1))
    keep = g.n >= info["min_days"]; info["months_dropped"] = int((~keep).sum()); g = g[keep]
    if g.empty:
        raise HTTPException(422, f"No month has at least {info['min_days']} valid values")
    out = pd.DataFrame({"t": g.y + (g.m - .5) / 12, "m": g.m.astype(int), "v": g.v}).reset_index(drop=True)
    out.attrs["parse"] = info
    return out

def find_preset(pid):
    return next((p for p in PRESETS if p["id"] == pid), None)

def preset_file(p):
    return PRESET_DIR / p["file"]

def get_series(src, lat, lon, y0, y1):
    """src = POWER variable id or a CSV preset id. Returns (df, meta{id, unit, name})."""
    p = find_preset(src)
    if p and p["kind"] == "csv":
        f = preset_file(p)
        if not f.exists():
            raise HTTPException(404, f"Preset data not found: put {p['file']} in backend/presets/")
        df = parse_series_csv(f.read_bytes())
        return df, dict(id=p["id"], unit=p.get("unit", ""), name=p["name"])
    m = meta_of(src)
    return fetch(lat, lon, src, y0, y1), m

def meta_of(var):
    m = next((x for x in VARS if x["id"] == var), None)
    if not m: raise HTTPException(404, f"Unknown variable: {var}")
    return m

def resolve_point(city, lat, lon):
    if city:
        c = next((x for x in CITIES if x["id"] == city), None)
        if not c: raise HTTPException(404, f"Unknown city: {city}")
        return c["lat"], c["lon"]
    if lat is None or lon is None:
        raise HTTPException(422, "Provide city, or lat and lon")
    return lat, lon

def _f(x):
    x = float(x)
    return x if math.isfinite(x) else None

# ------------------------------------------------------------------ statistics
def deseasonalize(d):
    if d.groupby("m").v.count().max() < 2:
        raise HTTPException(422, "Need at least 2 years of data to remove the seasonal cycle")
    d = d.copy(); d["v"] -= d.groupby("m")["v"].transform("mean"); return d

def analyze(df, deseason=True, annual=False):
    d = df.copy()
    if deseason:
        d = deseasonalize(d)
    if annual:
        d["y"] = d.t.astype(int)
        g = d.groupby("y").v.agg(["mean", "count"]); g = g[g["count"] >= 6]
        d = pd.DataFrame({"t": g.index + .5, "v": g["mean"].values})
    n = len(d)
    if n < 8:
        raise HTTPException(422, "Need at least 8 data points")
    t, v = d.t.values.astype(float), d.v.values.astype(float)
    lr = stats.linregress(t, v)
    res = v - (lr.intercept + lr.slope * t)
    r1 = float(np.corrcoef(res[:-1], res[1:])[0, 1]) if res.std() > 1e-12 else 0.0
    if not math.isfinite(r1): r1 = 0.0
    neff = max(3.0, n * (1 - r1) / (1 + r1)) if r1 > 0 else float(n)   # autocorrelation-adjusted
    se = float(lr.stderr) * math.sqrt((n - 2) / (neff - 2))
    if se > 1e-12:
        p_t = float(2 * stats.t.sf(abs(lr.slope / se), neff - 2))
    else:                                                 # perfectly flat or perfectly linear
        p_t = 1.0 if abs(lr.slope) < 1e-12 else 0.0
    tc = stats.t.ppf(.975, neff - 2)
    tau, p_mk = stats.kendalltau(t, v)
    tau, p_mk = (0.0, 1.0) if not math.isfinite(tau) else (float(tau), float(p_mk))
    sen = stats.theilslopes(v, t)[0]
    return dict(n=n, slope=float(lr.slope), ci=[float(lr.slope - tc * se), float(lr.slope + tc * se)], p_t=p_t,
                p_mk=p_mk, tau=tau, sen=float(sen), r1=r1, n_eff=float(neff),
                total=float(lr.slope * (t[-1] - t[0])), span=float(t[-1] - t[0]),
                sig=bool(p_t < .05 and p_mk < .05),
                t=t.tolist(), v=v.tolist(),
                fit=[float(lr.intercept + lr.slope * t[0]), float(lr.intercept + lr.slope * t[-1])])

def verdict(a, unit, name):
    u = f" {unit}" if unit else ""
    dr, drv = ("increasing", "tăng") if a["slope"] > 0 else ("decreasing", "giảm")
    s, tot, sp = f"{a['slope']:.3g}", f"{a['total']:.3g}", f"{a['span']:.0f}"
    if a["sig"]:
        return dict(en=f"{name['en']} shows a significant {dr} trend: {s}{u}/year ({tot}{u} over {sp} years). Both the t-test (autocorrelation-adjusted) and Mann-Kendall give p<0.05.",
                    vi=f"{name['vi']} có xu hướng {drv} đáng kể: {s}{u}/năm ({tot}{u} trong {sp} năm). Cả t-test (đã hiệu chỉnh tự tương quan) lẫn Mann-Kendall đều có p<0,05.")
    return dict(en=f"No significant trend for {name['en']} (slope {s}{u}/year; at least one test has p≥0.05). A longer record may change this.",
                vi=f"Chưa có xu hướng đáng kể cho {name['vi']} (độ dốc {s}{u}/năm; ít nhất một kiểm định có p≥0,05). Chuỗi dài hơn có thể thay đổi kết quả.")

def _ar1(x):
    if len(x) < 3 or x.std() < 1e-12: return 0.0
    r = float(np.corrcoef(x[:-1], x[1:])[0, 1]); return r if math.isfinite(r) else 0.0

def lagged_corr(a, b, lag):
    """r(a[t], b[t+lag]) with p-value using an effective sample size (Bretherton et al. 1999)."""
    x, y = a[: len(a) - lag] if lag else a, b[lag:]
    n = len(x)
    if n < 8 or x.std() < 1e-12 or y.std() < 1e-12:
        return 0.0, 1.0, n
    r = float(np.corrcoef(x, y)[0, 1])
    rr = _ar1(x) * _ar1(y)
    neff = min(float(n), max(3.0, n * (1 - rr) / (1 + rr))) if rr > 0 else float(n)
    if abs(r) >= 1 - 1e-12: return r, 0.0, n
    tt = r * math.sqrt((neff - 2) / (1 - r * r))
    return r, float(2 * stats.t.sf(abs(tt), neff - 2)), n

def _k(df):
    return (df.t.astype(int) * 12 + df.m - 1).values

def _robust_z(df):
    """Robust z-score of each value against the median/MAD of its own calendar month."""
    g = df.groupby("m").v
    med, mad = g.transform("median"), g.transform(lambda s: (s - s.median()).abs().median()) * 1.4826
    return ((df.v - med) / mad.where(mad > 1e-12)).fillna(0.0)

def data_quality(df):
    """Missing / abnormal-value report for a monthly series. Nothing is removed or imputed here:
    gaps are left as gaps (the statistics tolerate them) and outliers are flagged, not deleted,
    because a real event (e.g. 2015 haze) cannot be told from an artefact without ground truth."""
    d = df.sort_values("t").reset_index(drop=True); k = _k(d)
    expected = int(k.max() - k.min() + 1); present = set(k.tolist()); valid = len(present)
    miss = [i for i in range(int(k.min()), int(k.max()) + 1) if i not in present]
    longest = cur = 0; prev = None
    for i in miss:
        cur = cur + 1 if prev is not None and i == prev + 1 else 1; longest = max(longest, cur); prev = i
    by_month = {str(m): sum(1 for i in miss if i % 12 + 1 == m) for m in range(1, 13)}
    rz = _robust_z(d); mask = rz.abs() > 3.5
    outl = [dict(t=float(t_), v=float(v_), z=float(z_)) for t_, v_, z_ in
            sorted(zip(d.t[mask], d.v[mask], rz[mask]), key=lambda x: -abs(x[2]))[:8]]
    q = dict(span=[int(d.t.min()), int(d.t.max())], n_expected=expected, n_valid=valid, n_missing=expected - valid,
             coverage=valid / expected, longest_gap=longest, missing_by_month=by_month, n_outliers=int(mask.sum()), outliers=outl,
             parse=df.attrs.get("parse"))
    notes = []
    def note(level, vi, en): notes.append(dict(level=level, vi=vi, en=en))
    pm = " ".join(str(m) for m, c in sorted(by_month.items(), key=lambda x: -x[1])[:3] if c)
    if q["n_missing"] == 0:
        note("ok", f"Đủ {valid} tháng liên tục, không thiếu tháng nào.", f"All {valid} months present, no gaps.")
    else:
        pct = 100 * (1 - q["coverage"])
        note("warn" if q["coverage"] < .9 else "info",
             f"Thiếu {q['n_missing']}/{expected} tháng ({pct:.0f}%), khoảng trống dài nhất {longest} tháng. Các tháng thiếu không được nội suy.",
             f"{q['n_missing']} of {expected} months are missing ({pct:.0f}%), longest gap {longest} months. Missing months are not interpolated.")
        top3 = sum(sorted(by_month.values(), reverse=True)[:3])
        if q["n_missing"] >= 5 and top3 / q["n_missing"] > .6:
            note("warn", f"Dữ liệu thiếu dồn vào các tháng {pm} (thường do mây dày hoặc điều kiện quan sát kém khiến vệ tinh không đo được), nên các tháng đó có thể thiên về những ngày quang đãng.",
                 f"Gaps cluster in calendar months {pm} (typically cloud cover or poor viewing conditions preventing the satellite from measuring), so those months may lean towards clear-sky days.")
    if q["n_outliers"]:
        note("info", f"{q['n_outliers']} tháng lệch mạnh khỏi mức bình thường của cùng tháng (|z| robust > 3,5). Được giữ lại và đánh dấu vì có thể là sự kiện thật (ví dụ khói cháy rừng).",
             f"{q['n_outliers']} months deviate strongly from the usual level of the same calendar month (robust |z| > 3.5). They are kept and flagged because they may be real events (e.g. smoke haze).")
    if valid < 120:
        note("warn", f"Chuỗi chỉ có {valid} tháng (< 10 năm): kết luận về xu hướng kém chắc chắn.", f"Only {valid} months (< 10 years): trend conclusions are weak.")
    pr = q["parse"]
    if pr:
        if pr["fill_dropped"]: note("info", f"Đã loại {pr['fill_dropped']} dòng giá trị thiếu (fill value).", f"Dropped {pr['fill_dropped']} fill-value rows.")
        if pr["bad_dates"]: note("warn", f"Bỏ {pr['bad_dates']} dòng không đọc được thời gian.", f"Skipped {pr['bad_dates']} rows with unreadable dates.")
        if pr["sub_monthly"]:
            note("info", f"Dữ liệu theo ngày được lấy trung bình theo tháng; tháng có dưới {pr['min_days']} ngày hợp lệ bị bỏ ({pr['months_dropped']} tháng).",
                 f"Daily data was averaged per month; months with fewer than {pr['min_days']} valid days were dropped ({pr['months_dropped']} months).")
    q["notes"] = notes
    return q

def bh_adjust(ps):
    """Benjamini-Hochberg false-discovery-rate adjusted p-values (q-values)."""
    n = len(ps); order = sorted(range(n), key=lambda i: ps[i]); q = [1.0] * n; prev = 1.0
    for rank in range(n, 0, -1):
        i = order[rank - 1]; prev = min(prev, ps[i] * n / rank); q[i] = prev
    return q

def lag_calc(da, db, detrend=True):
    da, db = deseasonalize(da), deseasonalize(db)
    if detrend:       # remove each series' own linear trend so a shared drift is not mistaken for co-variation
        for d_ in (da, db):
            if len(d_) >= 3: d_["v"] = d_.v - np.polyval(np.polyfit(d_.t.values, d_.v.values, 1), d_.t.values)
    j = pd.DataFrame({"k": _k(da), "a": da.v.values}).merge(pd.DataFrame({"k": _k(db), "b": db.v.values}), on="k")
    if j.empty: raise HTTPException(422, "The two series do not overlap in time")
    # lags are counted in calendar months: put both on a full month grid, gaps stay NaN and are dropped per pair
    grid = pd.DataFrame({"k": np.arange(j.k.min(), j.k.max() + 1)}).merge(j, on="k", how="left")
    x, y = grid.a.values, grid.b.values
    r, p, ns = [], [], []
    for L in LAGS:
        xs, ys = (x[: len(x) - L] if L else x), y[L:]
        ok = np.isfinite(xs) & np.isfinite(ys)
        if ok.sum() < 8: raise HTTPException(422, "Need at least 8 overlapping months for every lag")
        ri, pi, ni = lagged_corr(xs[ok], ys[ok], 0)
        r.append(ri); p.append(pi); ns.append(ni)
    best = max(range(len(LAGS)), key=lambda i: abs(r[i]))
    return dict(lags=LAGS, r=r, p=p, n=ns, best_lag=LAGS[best], sig=bool(p[best] < .05), detrended=bool(detrend),
                caveat=dict(
                    vi="Tương quan có độ trễ chỉ cho thấy hai chuỗi biến động cùng nhau, không chứng minh nhân quả: có thể do yếu tố thứ ba hoặc do trùng hợp.",
                    en="A lagged correlation only shows that two series move together; it does not prove causation. A third factor or coincidence may explain it."))

def anomaly_rows(df):
    if df.groupby("m").v.count().min() < 5:
        raise HTTPException(422, "Need at least 5 years of data for every calendar month")
    q = df.groupby("m").v.quantile([.05, .95]).unstack()
    out = []
    for t, mo, v in zip(df.t, df.m, df.v):
        lo_, hi_ = float(q.loc[mo, .05]), float(q.loc[mo, .95])
        out.append(dict(t=float(t), v=float(v), p05=lo_, p95=hi_,
                        flag="high" if v > hi_ else "low" if v < lo_ else None))
    return out

def ranking_rows(var, start, end, region="all"):
    meta_of(var)
    cs = [c for c in CITIES if region == "all" or c.get("region") == region]
    def one(c):
        try:
            a = analyze(fetch(c["lat"], c["lon"], var, start, end), True, True)
            return dict(city=c["id"], name=c["name"], region=c.get("region", "vn"), lat=c["lat"], lon=c["lon"], slope=a["slope"],
                        p=a["p_t"], p_mk=a["p_mk"], sig=bool(a["p_t"] < .05 and a["p_mk"] < .05))
        except Exception:
            return None
    with cf.ThreadPoolExecutor(4) as ex:
        rows = [r for r in ex.map(one, cs) if r]
    # many cities tested at once: Benjamini-Hochberg q-value on the more conservative of the two p-values
    for r, q in zip(rows, bh_adjust([max(r["p"], r["p_mk"]) for r in rows])): r["q"] = q; r["sig_fdr"] = bool(q < .05)
    return sorted(rows, key=lambda r: -r["slope"])

def scan_rows(la, lo, start, end, city=None):
    """Every available variable at one place -> which ones are trending (de-seasoned monthly data)."""
    srcs = [(v["id"], "power") for v in VARS] + [(p["id"], "preset") for p in PRESETS
            if p["kind"] == "csv" and preset_file(p).exists() and city is not None and p.get("city") == city]
    def one(src):
        sid, kind = src
        try:
            df, m = get_series(sid, la, lo, start, end)
            a = analyze(df, True, False)
            sd = float(np.std(a["v"])) or 1.0
            return dict(var=sid, kind=kind, topic=m.get("topic", ""), name=m["name"], unit=m["unit"], slope=a["slope"], total=a["total"],
                        effect_sd=a["total"] / sd, tau=a["tau"], p=a["p_t"], p_mk=a["p_mk"], sig=a["sig"], n=a["n"], span=a["span"])
        except Exception:
            return None
    with cf.ThreadPoolExecutor(4) as ex:
        rows = [r for r in ex.map(one, srcs) if r]
    for r, q in zip(rows, bh_adjust([max(r["p"], r["p_mk"]) for r in rows])): r["q"] = q; r["sig_fdr"] = bool(q < .05)
    return sorted(rows, key=lambda r: (not r["sig_fdr"], not r["sig"], -abs(r["effect_sd"])))

MONTHS_EN = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

def summarize(df, unit, name, place=None, lag=None, rank=None):
    """Plain-language findings (VI/EN) built only from the numbers behind the charts: rule-based, no AI model.
    lag = (name_b, lag_calc result) or None; rank = (position, total, row) or None."""
    u = f" {unit}" if unit else ""
    g = lambda x: f"{x:.3g}"
    out, facts = [], {}
    def add(kind, tone, vi, en): out.append(dict(kind=kind, tone=tone, vi=vi, en=en))

    a = analyze(df, True, False)
    vd = verdict(a, unit, name)
    up = a["slope"] > 0
    add("trend", ("up" if up else "down") if a["sig"] else "flat", vd["vi"], vd["en"])
    facts.update(slope=a["slope"], ci=a["ci"], p_t=a["p_t"], p_mk=a["p_mk"], sig=a["sig"], total=a["total"], n=a["n"])

    yr = df.assign(y=df.t.astype(int)).groupby("y").v.agg(["mean", "count"])
    ann = yr[yr["count"] >= 6]["mean"]
    if len(ann) >= 10:                                    # first vs last block of years (raw values)
        k = min(10, len(ann) // 2); first, last = ann.iloc[:k], ann.iloc[-k:]
        d = float(last.mean() - first.mean())
        facts.update(block_diff=d, block_years=k, first_mean=float(first.mean()), last_mean=float(last.mean()))
        add("change", "up" if d > 0 else "down",
            f"Trung bình {k} năm gần nhất ({last.index[0]}–{last.index[-1]}) {'cao' if d > 0 else 'thấp'} hơn {k} năm đầu ({first.index[0]}–{first.index[-1]}) {g(abs(d))}{u}: {g(last.mean())} so với {g(first.mean())}{u}.",
            f"The latest {k} years ({last.index[0]}–{last.index[-1]}) average {g(abs(d))}{u} {'higher' if d > 0 else 'lower'} than the first {k} ({first.index[0]}–{first.index[-1]}): {g(last.mean())} vs {g(first.mean())}{u}.")
    if len(ann) >= 3:
        hi, lo = int(ann.idxmax()), int(ann.idxmin()); facts.update(max_year=hi, min_year=lo)
        add("extreme", "info",
            f"Năm có trung bình cao nhất là {hi} ({g(ann.max())}{u}); thấp nhất là {lo} ({g(ann.min())}{u}).",
            f"The highest yearly mean was in {hi} ({g(ann.max())}{u}); the lowest in {lo} ({g(ann.min())}{u}).")
    clim = df.groupby("m").v.mean()
    if len(clim) == 12 and clim.max() - clim.min() > 1e-12:
        mh, ml = int(clim.idxmax()), int(clim.idxmin()); facts.update(peak_month=mh, low_month=ml)
        add("season", "info",
            f"Theo mùa, giá trị thường cao nhất vào tháng {mh} ({g(clim.max())}{u}) và thấp nhất vào tháng {ml} ({g(clim.min())}{u}).",
            f"Seasonally, values usually peak in {MONTHS_EN[mh - 1]} ({g(clim.max())}{u}) and bottom out in {MONTHS_EN[ml - 1]} ({g(clim.min())}{u}).")
    try: rows = anomaly_rows(df)
    except HTTPException: rows = None
    if rows:
        hi_, lo_ = [r for r in rows if r["flag"] == "high"], [r for r in rows if r["flag"] == "low"]
        cut = rows[-1]["t"] - 5
        hr, lr_ = sum(r["t"] > cut for r in hi_), sum(r["t"] > cut for r in lo_)
        facts.update(n_high=len(hi_), n_low=len(lo_), n_high_recent=hr, n_low_recent=lr_)
        share = 5 / max(5.0, rows[-1]["t"] - rows[0]["t"])           # what "evenly spread" would give
        skew = bool(hi_) and hr / len(hi_) > 2 * share or bool(lo_) and lr_ / len(lo_) > 2 * share
        vi = f"Có {len(hi_)} tháng cao bất thường và {len(lo_)} tháng thấp bất thường (ngoài dải 5–95% của cùng tháng). Trong 5 năm gần nhất: {hr} tháng cao, {lr_} tháng thấp."
        en = f"{len(hi_)} months were unusually high and {len(lo_)} unusually low (outside the 5–95% band of the same calendar month). In the last 5 years: {hr} high, {lr_} low."
        fl = [r for r in rows if r["flag"]]
        if fl:
            r = fl[-1]; mo, y = int(round((r["t"] - int(r["t"])) * 12 + .5)), int(r["t"])
            vi += f" Gần nhất: {mo:02d}/{y} ({'cao' if r['flag'] == 'high' else 'thấp'}, {g(r['v'])}{u})."
            en += f" Most recent: {MONTHS_EN[mo - 1]} {y} ({r['flag']}, {g(r['v'])}{u})."
        add("anomaly", "warn" if skew else "info", vi, en)
    if lag:
        nb, l = lag; i = l["lags"].index(l["best_lag"]); r = l["r"][i]; k = l["best_lag"]
        facts.update(best_lag=k, lag_r=r, lag_sig=l["sig"])
        st = ("mạnh", "strong") if abs(r) >= .6 else ("vừa", "moderate") if abs(r) >= .3 else ("yếu", "weak")
        if l["sig"]:
            add("lag", "info",
                f"{name['vi']} và {nb['vi']} có tương quan {'thuận' if r > 0 else 'nghịch'} mức {st[0]} (r = {r:.2f}), rõ nhất " +
                (f"khi {nb['vi']} đi sau {k} tháng" if k else "trong cùng tháng") + ". Điều này không chứng minh nhân quả.",
                f"{name['en']} and {nb['en']} show a {st[1]} {'positive' if r > 0 else 'negative'} correlation (r = {r:.2f}), clearest " +
                (f"when {nb['en']} follows by {k} month{'s' if k > 1 else ''}" if k else "within the same month") + ". This does not prove causation.")
        else:
            add("lag", "flat",
                f"Chưa thấy liên hệ có ý nghĩa thống kê giữa {name['vi']} và {nb['vi']} (|r| lớn nhất = {abs(r):.2f} ở độ trễ {k} tháng).",
                f"No statistically significant link between {name['en']} and {nb['en']} (largest |r| = {abs(r):.2f} at a lag of {k} months).")
    if rank:
        pos, total, row = rank; facts.update(rank=pos, rank_total=total)
        add("rank", "info",
            f"{row['name']['vi']} xếp thứ {pos}/{total} thành phố theo độ dốc xu hướng ({g(row['slope'])}{u}/năm, tính trên trung bình năm; 1 = tăng nhanh nhất).",
            f"{row['name']['en']} ranks {pos} of {total} cities by trend slope ({g(row['slope'])}{u}/year on yearly means; 1 = fastest increase).")
    k = _k(df); missing = int(k.max() - k.min() + 1 - len(set(k.tolist()))); facts.update(missing_months=missing, r1=a["r1"], n_eff=a["n_eff"])
    if a["r1"] > .3 or missing:
        vi, en = [], []
        if a["r1"] > .3:
            vi.append(f"Các tháng liền nhau phụ thuộc nhau (r₁ = {a['r1']:.2f}), nên {a['n']} điểm chỉ tương đương khoảng {a['n_eff']:.0f} điểm độc lập; khoảng tin cậy đã tính đến điều này.")
            en.append(f"Neighbouring months are correlated (r₁ = {a['r1']:.2f}), so {a['n']} points are worth about {a['n_eff']:.0f} independent ones; the confidence interval already accounts for this.")
        if missing:
            vi.append(f"Chuỗi thiếu {missing} tháng."); en.append(f"{missing} months are missing from the record.")
        add("quality", "warn" if missing > .1 * len(df) else "info", " ".join(vi), " ".join(en))

    at = dict(vi=f" tại {place['vi']}", en=f" in {place['en']}") if place else dict(vi="", en="")
    if a["sig"]:
        head = dict(vi=f"{name['vi']}{at['vi']} đang {'tăng' if up else 'giảm'} {g(abs(a['slope']))}{u}/năm.",
                    en=f"{name['en']}{at['en']} is {'rising' if up else 'falling'} by {g(abs(a['slope']))}{u} per year.")
    else:
        head = dict(vi=f"{name['vi']}{at['vi']}: chưa có xu hướng rõ ràng.", en=f"{name['en']}{at['en']}: no clear trend yet.")
    return dict(headline=head, bullets=out, facts=facts, period=[int(df.t.min()), int(df.t.max())],
                yearly=dict(y=[int(i) for i in ann.index], v=[float(x) for x in ann.values]),   # raw yearly means for the summary chart
                text={L: " ".join([head[L]] + [b[L] for b in out[1:]]) for L in ("vi", "en")})

# ------------------------------------------------------------------- endpoints
@app.get("/api/summary")
def api_summary(var: str, city: str | None = None, lat: float | None = None, lon: float | None = None,
                b: str | None = None, start: int = 2000, end: int = 2024, rank: bool = True):
    """Automatic VI/EN summary of trend, change, extremes, season, anomalies, lag (if b) and city rank."""
    pv = find_preset(var) or {}
    is_csv = pv.get("kind") == "csv"
    la, lo = (0.0, 0.0) if is_csv else resolve_point(city, lat, lon)
    df, m = get_series(var, la, lo, start, end)
    c = next((x for x in CITIES if x["id"] == (pv.get("city") if is_csv else city)), None)
    place = c["name"] if c else None if is_csv else dict(vi=f"điểm {la:.2f}, {lo:.2f}", en=f"point {la:.2f}, {lo:.2f}")
    lag = None
    if b and b != var:
        try:
            if (find_preset(b) or {}).get("kind") != "csv" and is_csv: la, lo = resolve_point(city or pv.get("city"), lat, lon)
            dbb, mb = get_series(b, la, lo, start, end); lag = (mb["name"], lag_calc(df, dbb))
        except HTTPException: lag = None                  # the summary still works without the second series
    rk = None
    if rank and city and not is_csv:
        rows = ranking_rows(var, start, end, next((x.get("region", "all") for x in CITIES if x["id"] == city), "all"))
        i = next((i for i, r in enumerate(rows) if r["city"] == city), None)
        if i is not None and len(rows) > 1: rk = (i + 1, len(rows), rows[i])
    s = summarize(df, m["unit"], m["name"], place, lag, rk)
    return dict(var=var, b=b if lag else None, city=city, unit=m["unit"], name=m["name"], place=place, **s)

@app.get("/api/variables")
def variables(): return VARS

@app.get("/api/cities")
def cities(): return CITIES

@app.get("/api/presets")
def presets():
    out = []
    for p in PRESETS:
        q = {k: p[k] for k in ("id", "kind", "city", "var", "title") if k in p}
        q["available"] = p["kind"] != "csv" or preset_file(p).exists()
        for k in ("name", "desc", "unit", "topic"):
            if k in p: q[k] = p[k]
        out.append(q)
    return out

@app.get("/api/analyze")
def api_analyze(city: str | None = None, lat: float | None = None, lon: float | None = None,
                var: str | None = None, preset: str | None = None, start: int = 2000, end: int = 2024,
                deseason: bool = True, annual: bool = False):
    if preset:
        p = find_preset(preset)
        if not p: raise HTTPException(404, f"Unknown preset: {preset}")
        city, var = p.get("city", city), p["var"]
    if not var: raise HTTPException(422, "Provide var (or preset)")
    la, lo = (0.0, 0.0) if (find_preset(var) or {}).get("kind") == "csv" else resolve_point(city, lat, lon)
    df, m = get_series(var, la, lo, start, end)
    a = analyze(df, deseason, annual)
    a["verdict"] = verdict(a, m["unit"], m["name"]); a["source"] = var; a["quality"] = data_quality(df)
    return a

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

@app.get("/api/lag")
def api_lag(a: str, b: str, city: str | None = None, lat: float | None = None, lon: float | None = None,
            start: int = 2000, end: int = 2024, detrend: bool = True):
    """Cross-correlation of de-seasoned anomalies; positive lag = b follows a by that many months."""
    csv_only = all((find_preset(x) or {}).get("kind") == "csv" for x in (a, b))
    la, lo = (0.0, 0.0) if csv_only else resolve_point(city, lat, lon)
    (da, ma), (db, mb) = get_series(a, la, lo, start, end), get_series(b, la, lo, start, end)
    return dict(a=a, b=b, **lag_calc(da, db, detrend))

@app.get("/api/anomaly")
def api_anomaly(var: str, city: str | None = None, lat: float | None = None, lon: float | None = None,
                start: int = 2000, end: int = 2024):
    """Each month vs the 5th/95th percentile of the same calendar month across years."""
    csv_src = (find_preset(var) or {}).get("kind") == "csv"
    la, lo = (0.0, 0.0) if csv_src else resolve_point(city, lat, lon)
    df, m = get_series(var, la, lo, start, end)
    out = anomaly_rows(df)
    return dict(var=var, unit=m["unit"], months=out, n_flagged=sum(1 for o in out if o["flag"]))

@app.get("/api/ranking")
def api_ranking(var: str, start: int = 2000, end: int = 2024, region: str = "all"):
    if region not in ("all", "vn", "world"): raise HTTPException(422, "region must be all, vn or world")
    return ranking_rows(var, start, end, region)

@app.get("/api/scan")
def api_scan(city: str | None = None, lat: float | None = None, lon: float | None = None, start: int = 2000, end: int = 2024):
    """Which variables are trending at this place? One row per variable, strongest evidence first."""
    la, lo = resolve_point(city, lat, lon)
    return scan_rows(la, lo, start, end, city)

@app.post("/api/upload")
async def api_upload(file: UploadFile = File(...), deseason: bool = True, annual: bool = False,
                     name: str | None = None, unit: str = "", min_days: int | None = None):
    raw = await file.read(MAX_UPLOAD + 1)
    if len(raw) > MAX_UPLOAD: raise HTTPException(413, "File too large (max 5 MB)")
    nm = name or pathlib.Path(file.filename or "upload").stem
    df = parse_series_csv(raw, min_days)
    a = analyze(df, deseason, annual)
    a["verdict"] = verdict(a, unit, dict(vi=nm, en=nm)); a["source"] = "upload"; a["quality"] = data_quality(df)
    return a

app.mount("/", StaticFiles(directory=ROOT.parent / "frontend", html=True), name="web")
