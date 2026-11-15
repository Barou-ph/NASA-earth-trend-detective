"""Earth Trend Detective API. Run: uvicorn backend.main:app --reload
Contract: docs/api-contract.md (field names are frozen; only add, never rename)."""
import csv, datetime, io, json, math, pathlib, threading, concurrent.futures as cf
import numpy as np, pandas as pd, requests
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.staticfiles import StaticFiles
from scipy import stats

ROOT = pathlib.Path(__file__).parent
CACHE = ROOT / "cache"; CACHE.mkdir(exist_ok=True)
PRESET_DIR = ROOT / "presets"
URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
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
        return df, dict(id=p["id"], unit=p.get("unit", ""), name=p["name"], topic=p.get("topic", ""))
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

LEVEL_RANK = {"strong": 3, "moderate": 2, "weak": 1, "none": 0}

def cap_evidence(rows):
    """Many variables are scanned at once: a trend that only just survives the FDR correction (q >= 0.01) is never called 'strong'."""
    for r in rows:
        ev = r["evidence"]
        if ev["level"] == "strong" and r["q"] >= .01:
            ev["level"] = "moderate"; ev["capped"] = True
    return rows

def evidence_for(df):
    """How far a monthly trend can be trusted: five independent checks, each pass/fail with a plain-language reason.
    strong = significant and >= 4 checks, moderate = significant and 3, weak = significant but <= 2, none = not significant."""
    try: base = analyze(df, True, False)
    except HTTPException: return None
    sign = 1 if base["slope"] > 0 else -1
    same = lambda a: a["slope"] * sign > 0
    def ok(fn):
        try: return bool(fn())
        except HTTPException: return False
    z = _robust_z(df); mid = df.t.median()
    k = _k(df); expected = int(k.max() - k.min() + 1); cov = len(set(k.tolist())) / expected
    checks = [
        (base["sig"], "Cả t-test và Mann-Kendall đều có ý nghĩa", "Both the t-test and Mann-Kendall are significant"),
        (ok(lambda: (lambda a: same(a) and a["sig"])(analyze(df[z.abs() <= 3.5], True, False))),
         "Vẫn đúng khi bỏ các tháng ngoại lai", "Still holds when outlier months are removed"),
        (ok(lambda: same(analyze(df[df.t <= mid], True, False)) and same(analyze(df[df.t > mid], True, False))),
         "Cùng chiều ở cả hai nửa giai đoạn", "Same direction in both halves of the period"),
        (ok(lambda: (lambda a: same(a) and a["p_mk"] < .05)(analyze(df, True, True))),
         "Vẫn có ý nghĩa khi dùng trung bình năm", "Still significant when yearly means are used"),
        (bool(cov >= .85 and expected >= 120), "Đủ dữ liệu (≥ 85% số tháng, ≥ 10 năm)", "Enough data (≥ 85% of months, ≥ 10 years)"),
    ]
    score = sum(1 for c in checks if c[0])
    level = "none" if not base["sig"] else "strong" if score >= 4 else "moderate" if score == 3 else "weak"
    return dict(level=level, score=score, of=len(checks), coverage=cov, capped=False,
                checks=[dict(id=i, passed=bool(c[0]), vi=c[1], en=c[2]) for i, c in enumerate(checks, 1)])

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
            ev = evidence_for(df) or dict(level="none", score=0, of=5, coverage=0.0, checks=[])
            return dict(var=sid, kind=kind, topic=m.get("topic", ""), name=m["name"], unit=m["unit"], slope=a["slope"], total=a["total"],
                        effect_sd=a["total"] / sd, tau=a["tau"], p=a["p_t"], p_mk=a["p_mk"], sig=a["sig"], n=a["n"], span=a["span"],
                        coverage=ev["coverage"], evidence=ev)
        except Exception:
            return None
    with cf.ThreadPoolExecutor(4) as ex:
        rows = [r for r in ex.map(one, srcs) if r]
    for r, q in zip(rows, bh_adjust([max(r["p"], r["p_mk"]) for r in rows])): r["q"] = q; r["sig_fdr"] = bool(q < .05)
    cap_evidence(rows)
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

def globe_rows(var, start, end):
    """Every city for one variable: the final trend plus the yearly anomaly series (for the 3D time-lapse)."""
    meta = meta_of(var)
    def one(c):
        try:
            df = fetch(c["lat"], c["lon"], var, start, end)
            a = analyze(df, True, True)
            am = analyze(df, True, False)                       # same definition of "change in SD" as scan / brief: monthly de-seasoned anomalies
            sd = float(np.std(am["v"])) or 1.0
            return dict(city=c["id"], name=c["name"], region=c.get("region", "vn"), lat=c["lat"], lon=c["lon"], slope=a["slope"],
                        p=a["p_t"], p_mk=a["p_mk"], sig=bool(a["p_t"] < .05 and a["p_mk"] < .05), effect_sd=am["total"] / sd,
                        years=[int(t_) for t_ in a["t"]], anom=a["v"])
        except Exception:
            return None
    with cf.ThreadPoolExecutor(4) as ex:
        rows = [r for r in ex.map(one, CITIES) if r]
    for r, q in zip(rows, bh_adjust([max(r["p"], r["p_mk"]) for r in rows])): r["q"] = q; r["sig_fdr"] = bool(q < .05)
    allyears = sorted({y for r in rows for y in r["years"]})
    for r in rows:                                  # align every city on the same year axis (None = no data that year)
        by = dict(zip(r.pop("years"), r["anom"])); r["anom"] = [by.get(y) for y in allyears]
    return dict(var=var, unit=meta["unit"], name=meta["name"], years=allyears, cities=rows)


# ------------------------------------------------------------------ weekly (recent weeks, hover on the map)
def fetch_daily(lat, lon, par, d0, d1):
    """Daily series from NASA POWER (cached on disk per day). Returns a pandas Series indexed by date; fill values dropped."""
    f = CACHE / f"daily_{par}_{lat:.2f}_{lon:.2f}_{d1.isoformat()}.json"
    d = None
    if f.exists():
        try: d = json.load(open(f))
        except ValueError: d = None
    if d is None:
        try:
            r = requests.get(DAILY_URL, params=dict(parameters=par, community="AG", longitude=lon, latitude=lat,
                             start=d0.strftime("%Y%m%d"), end=d1.strftime("%Y%m%d"), format="JSON"), timeout=90)
        except requests.RequestException as e:
            raise HTTPException(502, f"Cannot reach NASA POWER: {e.__class__.__name__}")
        if r.status_code != 200: raise HTTPException(502, f"NASA POWER error {r.status_code}")
        try: d = r.json()["properties"]["parameter"][par]
        except (KeyError, ValueError): raise HTTPException(502, "Unexpected NASA POWER response")
        json.dump(d, open(f, "w"))
    return pd.Series({pd.Timestamp(k): v for k, v in d.items() if v > -990}, dtype=float).sort_index()

def _trend_p(x, y):
    """OLS slope with a lag-1 autocorrelation-adjusted p-value (same correction as analyze)."""
    n = len(x); lr = stats.linregress(x, y); res = y - (lr.intercept + lr.slope * x)
    r1 = float(np.corrcoef(res[:-1], res[1:])[0, 1]) if res.std() > 1e-12 else 0.0
    if not math.isfinite(r1): r1 = 0.0
    neff = max(3.0, n * (1 - r1) / (1 + r1)) if r1 > 0 else float(n)
    se = float(lr.stderr) * math.sqrt((n - 2) / (neff - 2))
    p = float(2 * stats.t.sf(abs(lr.slope / se), neff - 2)) if se > 1e-12 else (1.0 if abs(lr.slope) < 1e-12 else 0.0)
    return float(lr.slope), p, float(neff)

def weekly_calc(s, weeks=52):
    """Last `weeks` weekly means vs the same ISO weeks of the earlier years (climatology), plus a short-term trend of the anomaly.
    Deliberately a short-term view: 52 weeks is not a climate trend."""
    if s.empty: raise HTTPException(502, "No daily data returned")
    w = s.resample("W-SUN").agg(["mean", "count"]); w = w[w["count"] >= 5]["mean"]
    if len(w) < weeks + 104: raise HTTPException(422, "Need at least 3 years of weekly data")
    recent, hist = w.iloc[-weeks:], w.iloc[:-weeks]
    woy = lambda idx: np.minimum(idx.isocalendar().week.values.astype(int), 52)
    clim = pd.Series(hist.values).groupby(woy(hist.index)).mean()
    c = np.array([clim.get(k, np.nan) for k in woy(recent.index)]); anom = recent.values - c; ok = np.isfinite(anom)
    if ok.sum() < 20: raise HTTPException(422, "Not enough weeks with a climatology to compare")
    x, y = np.arange(len(recent))[ok].astype(float), anom[ok]
    slope, p, neff = _trend_p(x, y)
    nz = lambda a: [None if not math.isfinite(v) else round(float(v), 4) for v in a]
    total = slope * (x[-1] - x[0]); sd = float(np.std(y)) or 1.0
    return dict(total=float(total), effect_sd=float(total / sd), weeks=[d.date().isoformat() for d in recent.index], v=nz(recent.values), clim=nz(c), anom=nz(anom),
                slope_week=slope, p=p, sig=bool(p < .05), n=int(ok.sum()), n_eff=neff, mean_anom=float(np.nanmean(anom)),
                last=dict(week=recent.index[-1].date().isoformat(), v=float(recent.values[-1]), clim=_f(c[-1]), anom=_f(anom[-1])),
                note=dict(vi="Đây là 52 tuần gần nhất so với cùng tuần của các năm trước: bức tranh ngắn hạn, không phải xu hướng khí hậu.",
                          en="This is the last 52 weeks versus the same weeks of earlier years: a short-term picture, not a climate trend."))


def recent7_calc(s, today=None, ctx_days=30):
    """The most recent 7 days with data vs the normal for the same time of year (daily climatology of the earlier data, smoothed over +-15 days).
    z = anomaly / sd of 7-day-mean anomalies in the same season (+-30 days around this date) in earlier years; p = how often a week that unusual happened then."""
    if s.empty or len(s) < 3 * 365: raise HTTPException(422, "Need at least 3 years of daily data")
    end = s.index.max(); win = s[s.index > end - pd.Timedelta(days=7)]
    if len(win) < 5: raise HTTPException(422, "Not enough recent days")
    hist = s[s.index <= end - pd.Timedelta(days=7)]
    doy = lambda idx: np.minimum(idx.dayofyear.values, 365)
    clim = hist.groupby(doy(hist.index)).mean().reindex(range(1, 366))
    ext = pd.concat([clim.iloc[-15:], clim, clim.iloc[:15]]).rolling(31, center=True, min_periods=10).mean().iloc[15:-15]; ext.index = range(1, 366)
    cl = lambda idx: ext.reindex(doy(idx)).values
    r7 = pd.Series(hist.values - cl(hist.index), index=hist.index).rolling(7, min_periods=5).mean()
    a_last = float(np.nanmean(win.values - cl(win.index)))
    end_doy = int(min(end.dayofyear, 365)); dd = ((doy(r7.index) - end_doy + 182) % 365) - 182
    pool = r7.values[(np.abs(dd) <= 30) & np.isfinite(r7.values)]
    if len(pool) < 50 or not math.isfinite(a_last): raise HTTPException(422, "Not enough earlier data for the same season")
    sd = float(np.std(pool)) or 1.0; p = float((1 + np.sum(np.abs(pool) >= abs(a_last))) / (len(pool) + 1))
    cx = s[s.index > end - pd.Timedelta(days=ctx_days)].reindex(pd.date_range(end - pd.Timedelta(days=ctx_days - 1), end))
    nz = lambda a: [None if not math.isfinite(v) else round(float(v), 4) for v in a]
    today = today or datetime.date.today()
    return dict(end=end.date().isoformat(), stale_days=(today - end.date()).days, n=int(len(win)), mean=float(win.mean()), clim=float(np.nanmean(cl(win.index))),
                anom=a_last, effect_sd=a_last / sd, p=p, sig=bool(p < .05), pool=int(len(pool)),
                days=dict(dates=[d.date().isoformat() for d in cx.index], v=nz(cx.values), clim=nz(cl(cx.index))),
                note=dict(vi="7 ngày gần nhất có dữ liệu so với mức thường lệ của đúng thời điểm này trong các năm trước. Chỉ là một tuần, không phải xu hướng khí hậu.",
                          en="The latest 7 days with data versus the normal for this time of year in earlier years. Just one week, not a climate trend."))

# ------------------------------------------------------------------ highlights (notable trends of the LAST 7 DAYS across all cities)
HL, HL_LOCK = {}, threading.Lock()

def week_row(c, var, r):
    m = meta_of(var)
    return dict(city=c["id"], place=c["name"], region=c.get("region", "vn"), lat=c["lat"], lon=c["lon"], var=var, topic=m.get("topic", ""), name=m["name"], unit=m["unit"],
                direction="up" if r["anom"] > 0 else "down", effect_sd=r["effect_sd"], anom=r["anom"], mean=r["mean"], clim=r["clim"], end=r["end"], p=r["p"], n=r["n"], spark=r["days"])

def city_week_rows(c, today):
    """The last 7 days (vs the normal for this time of year) of every POWER indicator at one city. Indicators whose daily data
    lags more than 10 days behind today (e.g. cloud amount) are skipped: they would not be 'the last 7 days'."""
    d0 = datetime.date(today.year - 5, 1, 1)
    def one(v):
        try:
            r = recent7_calc(fetch_daily(c["lat"], c["lon"], v["id"], d0, today), today)
            return week_row(c, v["id"], r) if r["stale_days"] <= 10 else None
        except Exception: return None
    with cf.ThreadPoolExecutor(4) as ex:
        return [r for r in ex.map(one, VARS) if r]

def pick_highlights(rows, limit=12, per_city=2):
    """Many city x indicator pairs are tested at once, so p-values get a Benjamini-Hochberg q. Only raw p < 0.05 pairs are candidates;
    FDR-surviving ones come first, then the biggest change. At most `per_city` per city so one place does not take the whole page."""
    rows = [dict(r) for r in rows]
    for r, q in zip(rows, bh_adjust([r["p"] for r in rows])): r["q"] = q; r["sig_fdr"] = bool(q < .05)
    seen, out = {}, []
    for r in sorted((r for r in rows if r["p"] < .05), key=lambda r: (not r["sig_fdr"], -abs(r["effect_sd"]))):
        if seen.get(r["city"], 0) >= per_city: continue
        seen[r["city"]] = seen.get(r["city"], 0) + 1; out.append(r)
        if len(out) >= limit: break
    return out

def _hl_worker(key, st):
    today = datetime.date.fromisoformat(key)
    for c in CITIES:
        try: rows = city_week_rows(c, today)
        except Exception: rows = []
        with HL_LOCK: st["rows"].extend(rows); st["done"] += 1
    st["finished"] = True
    try: json.dump(st["rows"], open(CACHE / f"highlights_7d_{key}.json", "w"))
    except OSError: pass

def hl_state():
    key = datetime.date.today().isoformat()
    with HL_LOCK:
        st = HL.get(key)
        if st: return key, st
        f = CACHE / f"highlights_7d_{key}.json"
        if f.exists():
            try:
                st = dict(rows=json.load(open(f)), done=len(CITIES), finished=True); HL[key] = st; return key, st
            except ValueError: pass
        st = HL[key] = dict(rows=[], done=0, finished=False)
    threading.Thread(target=_hl_worker, args=(key, st), daemon=True).start()
    return key, st

@app.on_event("startup")
def _warm():
    hl_state()                                              # compute in the background so the home page is ready when someone opens it

# Transparent rule table behind "directions to consider": (variables, direction, topic, vi, en). Not policy advice.
ACTION_RULES = [
    (("T2M", "TS", "T2M_MAX"), "up", "heat",
     "Nhiệt độ đang tăng: xem xét các biện pháp giảm nhiệt đô thị (cây xanh, mặt phủ phản xạ, mặt nước), bắt đầu từ khu dân cư đông và nhóm dễ tổn thương.",
     "Temperatures are rising: consider urban cooling measures (trees, reflective surfaces, water), starting with dense neighbourhoods and vulnerable groups."),
    (("T2M_MIN",), "up", "heat",
     "Đêm đang ấm lên: đánh giá nguy cơ sốc nhiệt ban đêm và ưu tiên không gian mát cho khu dân cư dày đặc.",
     "Nights are warming: assess night-time heat stress and prioritise cool spaces for dense neighbourhoods."),
    (("hcm_no2",), "up", "air",
     "NO₂ tăng: rà soát nguồn phát thải giao thông và công nghiệp, bổ sung trạm đo mặt đất để kiểm chứng.",
     "NO₂ is rising: review traffic and industrial emission sources and add ground monitors to verify."),
    (("hcm_aod",), "down", "air",
     "Bụi mịn AOD giảm: chưa thể suy ra PM2.5 mặt đất cũng giảm; cần đối chiếu bằng trạm đo trước khi kết luận.",
     "AOD is falling: this does not show ground-level PM2.5 is also falling; check against ground monitors before concluding."),
    (("hcm_aod",), "up", "air",
     "Bụi mịn AOD tăng: ưu tiên kiểm tra nguồn bụi, khói và đối chiếu với trạm đo PM2.5 mặt đất.",
     "AOD is rising: check dust and smoke sources and compare with ground PM2.5 monitors."),
    (("hcm_fire",), "up", "air",
     "Điểm cháy tăng: theo dõi nguồn khói lan tới thành phố, đặc biệt trong mùa khô.",
     "Fire detections are rising: track smoke reaching the city, especially in the dry season."),
    (("CLOUD_AMT",), "up", "energy",
     "Mây tăng: ảnh hưởng điện mặt trời và nhiệt độ ban ngày; tính đến khi quy hoạch năng lượng tái tạo.",
     "Cloud cover is rising: affects solar power and daytime temperature; account for it when planning renewables."),
    (("CLOUD_AMT",), "down", "energy",
     "Mây giảm: nắng nhiều hơn, tiềm năng điện mặt trời tăng nhưng nhu cầu che nắng và làm mát cũng tăng.",
     "Cloud cover is falling: more sun, higher solar potential but also higher shading and cooling demand."),
    (("ALLSKY_SFC_SW_DWN",), "down", "energy",
     "Bức xạ mặt trời giảm: tiềm năng điện mặt trời có thể giảm; kiểm tra trước khi thiết kế dự án năng lượng.",
     "Surface sunlight is falling: solar potential may fall; check before designing energy projects."),
    (("ALLSKY_SFC_SW_DWN",), "up", "energy",
     "Bức xạ mặt trời tăng: tiềm năng điện mặt trời tăng, đồng thời cần che nắng cho khu dân cư.",
     "Surface sunlight is rising: higher solar potential, and shading is needed for housing."),
    (("PRECTOTCORR",), "up", "water",
     "Mưa tăng: rà soát hệ thống thoát nước và nguy cơ ngập.", "Rainfall is rising: review drainage and flood risk."),
    (("PRECTOTCORR",), "down", "water",
     "Mưa giảm: lưu ý cấp nước và nguy cơ khô hạn.", "Rainfall is falling: note water supply and drought risk."),
    (("GWETROOT", "GWETTOP"), "down", "water",
     "Đất khô đi: ảnh hưởng cây xanh đô thị và nhu cầu tưới.", "Soils are drying: affects urban trees and irrigation needs."),
    (("WS2M",), "down", "wind",
     "Gió yếu đi: thông gió đô thị và khả năng phân tán ô nhiễm giảm; cân nhắc hành lang gió khi quy hoạch.",
     "Winds are weakening: urban ventilation and pollution dispersal drop; consider wind corridors in planning."),
    (("QV2M",), "up", "heat",
     "Không khí ẩm hơn: cảm giác nóng bức tăng khi nhiệt độ cao; cân nhắc chỉ số nóng-ẩm khi cảnh báo nhiệt.",
     "Air is more humid: heat feels worse at high temperatures; consider a heat index in heat warnings."),
    (("EVLAND", "EVPTRNS"), "up", "water",
     "Bốc hơi và thoát hơi tăng: nhu cầu nước của đất và cây tăng; xem cùng độ ẩm đất.",
     "Evaporation and transpiration are rising: soils and plants need more water; read with soil wetness."),
    (("EVLAND", "EVPTRNS"), "down", "water",
     "Bốc hơi và thoát hơi giảm: xem cùng độ ẩm đất và độ che phủ thực vật.",
     "Evaporation and transpiration are falling: read with soil wetness and vegetation cover."),
]
LEVEL_VI = {"strong": "mạnh", "moderate": "vừa", "weak": "yếu", "none": "chưa có"}
LEVEL_EN = {"strong": "strong", "moderate": "moderate", "weak": "weak", "none": "none"}

def action_for(r):
    d = "up" if r["slope"] > 0 else "down"
    for vars_, dire, topic, vi, en in ACTION_RULES:
        if r["var"] in vars_ and dire == d:
            return dict(topic=topic, var=r["var"], direction=d, vi=vi, en=en, level=r["evidence"]["level"])
    nm = r["name"]
    return dict(topic="other", var=r["var"], direction=d, level=r["evidence"]["level"],
                vi=f"{nm['vi']} đang {'tăng' if d == 'up' else 'giảm'}: theo dõi và đối chiếu với số liệu địa phương.",
                en=f"{nm['en']} is {'rising' if d == 'up' else 'falling'}: monitor and compare with local data.")

def build_brief(city, la, lo, start, end):
    """One-page decision brief for a place: what is trending (and how far to trust it), what to watch, directions to consider, caveats."""
    c = next((x for x in CITIES if x["id"] == city), None)
    place = c["name"] if c else dict(vi=f"điểm {la:.2f}, {lo:.2f}", en=f"point {la:.2f}, {lo:.2f}")
    rows = scan_rows(la, lo, start, end, city)
    if not rows: raise HTTPException(502, "No variable could be analysed for this place")
    keep = lambda r: dict(var=r["var"], kind=r["kind"], topic=r["topic"], name=r["name"], unit=r["unit"], direction="up" if r["slope"] > 0 else "down",
                          slope=r["slope"], total=r["total"], effect_sd=r["effect_sd"], p=r["p"], p_mk=r["p_mk"], q=r["q"], span=r["span"],
                          n=r["n"], coverage=r["coverage"], evidence=r["evidence"])
    trusted = sorted((r for r in rows if r["sig_fdr"]), key=lambda r: (-LEVEL_RANK[r["evidence"]["level"]], -abs(r["effect_sd"])))
    findings = [keep(r) for r in trusted[:6]]
    watch = [keep(r) for r in rows if not r["sig_fdr"] and abs(r["effect_sd"]) >= .5][:4]
    actions = [action_for(r) for r in trusted if LEVEL_RANK[r["evidence"]["level"]] >= 2][:6]
    caveats = [
        dict(vi="Số liệu NASA POWER là sản phẩm mô hình tái phân tích (độ phân giải khoảng nửa độ), không phải số đo tại thành phố; NO₂ và AOD là đo vệ tinh trên một vùng.",
             en="NASA POWER data is a reanalysis model product (about half-degree resolution), not a measurement at the city; NO₂ and AOD are satellite measurements over an area."),
        dict(vi="Các gợi ý chỉ là hướng nên xem xét theo bảng quy tắc công khai, không phải khuyến nghị chính sách. Tương quan không chứng minh nhân quả.",
             en="The suggestions are directions to consider from a public rule table, not policy recommendations. Correlation does not prove causation."),
    ]
    for r in trusted[:6]:
        if r["coverage"] < .9:
            pct = round(100 * (1 - r["coverage"]))
            caveats.append(dict(vi=f"{r['name']['vi']}: thiếu khoảng {pct}% số tháng; kết quả kém chắc hơn.", en=f"{r['name']['en']}: about {pct}% of months are missing; the result is less certain."))
    nfdr = len(trusted); lead = findings[0] if findings else None
    if lead:
        dv, de = ("tăng", "rising") if lead["direction"] == "up" else ("giảm", "falling")
        headline = dict(vi=f"{place['vi']}: {nfdr}/{len(rows)} chỉ số đang thay đổi đáng tin. Rõ nhất: {lead['name']['vi']} đang {dv}.",
                        en=f"{place['en']}: {nfdr} of {len(rows)} indicators are changing in a trustworthy way. Clearest: {lead['name']['en']} is {de}.")
    else:
        headline = dict(vi=f"{place['vi']}: chưa chỉ số nào có xu hướng đáng tin sau hiệu chỉnh nhiều phép thử.",
                        en=f"{place['en']}: no indicator shows a trustworthy trend after correcting for multiple tests.")
    return dict(city=city, place=place, period=[start, end], generated=datetime.date.today().isoformat(), n_vars=len(rows), n_trusted=nfdr,
                headline=headline, findings=findings, watch=watch, actions=actions, caveats=caveats)

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

@app.get("/api/globe")
def api_globe(var: str, start: int = 2000, end: int = 2024):
    """All cities for one variable, with yearly anomalies, for the 3D globe and its time-lapse."""
    return globe_rows(var, start, end)

@app.get("/api/weekly")
def api_weekly(var: str, city: str | None = None, lat: float | None = None, lon: float | None = None, weeks: int = 52):
    """Recent weekly means vs the same weeks of earlier years (for the hover card on the detail map)."""
    if (find_preset(var) or {}).get("kind") == "csv": raise HTTPException(422, "This indicator only has monthly data")
    meta = meta_of(var); la, lo = resolve_point(city, lat, lon)
    if not 20 <= weeks <= 104: raise HTTPException(422, "weeks must be between 20 and 104")
    today = datetime.date.today()
    s = fetch_daily(la, lo, var, datetime.date(today.year - 5, 1, 1), today)
    try: r7 = recent7_calc(s, today)
    except HTTPException: r7 = None
    return dict(var=var, unit=meta["unit"], name=meta["name"], recent=r7, **weekly_calc(s, weeks))

# ------------------------------------------------------------------ globe heatmap layers (NASA GIBS)
# The globe heatmap is a real global NASA product (monthly MERRA-2 / CERES maps served by GIBS), one per indicator.
# We only map an indicator when a GIBS layer measures the same quantity; the layer's own title and colour legend are shown to the user.
GIBS_CAPS = "https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/1.0.0/WMTSCapabilities.xml"
GIBS_WMS = "https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi"
GIBS_MAP = {
    "T2M": "MERRA2_2m_Air_Temperature_Monthly", "TS": "MERRA2_Surface_Skin_Temperature_Monthly",
    "PRECTOTCORR": "MERRA2_Precipitation_Bias_Corrected_Monthly", "GWETROOT": "MERRA2_Soil_Water_Root_Zone_Monthly",
    "WS2M": "MERRA2_Surface_Wind_Speed_Monthly", "ALLSKY_SFC_SW_DWN": "CERES_Combined_Surface_Shortwave_Flux_Down_All_Sky_Monthly",
    "EVLAND": "MERRA2_Evaporation_Land_Monthly", "QV2M": "MERRA2_Total_Precipitable_Water_Vapor_Monthly",
}
_GIBS_LOCK = threading.Lock()


def parse_gibs_layers(xml, layers):
    """Pick title, latest time and horizontal legend of the given layers out of the (large) GIBS capabilities document."""
    import re
    out = {}
    for lid in layers:
        i = xml.find(f"<ows:Identifier>{lid}</ows:Identifier>")
        if i < 0: continue
        a = xml.rfind("<Layer>", 0, i); b = xml.find("</Layer>", i); blk = xml[a:b]
        title = re.search(r"<ows:Title[^>]*>([^<]*)</ows:Title>", blk)
        default = re.search(r"<Default>([^<]*)</Default>", blk)
        legend = re.search(r"xlink:href='([^']*_H\.svg)'", blk)
        if not default: continue
        out[lid] = {"layer": lid, "title": title.group(1) if title else lid, "time": default.group(1)[:10],
                    "legend": legend.group(1) if legend else f"https://gibs.earthdata.nasa.gov/legends/{lid}_H.svg"}
    return out


def gibs_layers():
    f = CACHE / f"gibs_layers_{datetime.date.today().isoformat()}.json"
    with _GIBS_LOCK:
        if f.exists():
            try: return json.load(open(f, encoding="utf-8"))
            except ValueError: pass
        try:
            r = requests.get(GIBS_CAPS, timeout=90)
        except requests.RequestException as e:
            raise HTTPException(502, f"Cannot reach NASA GIBS: {e.__class__.__name__}")
        if r.status_code != 200: raise HTTPException(502, f"NASA GIBS error {r.status_code}")
        d = parse_gibs_layers(r.text, sorted(set(GIBS_MAP.values())))
        json.dump(d, open(f, "w", encoding="utf-8"))
        return d


@app.get("/api/heatlayers")
def heatlayers():
    """Per indicator: the NASA GIBS map layer to paint on the globe (WMS url template, latest time, title, legend). Indicators without a matching layer are absent."""
    d = gibs_layers()
    return {"wms": GIBS_WMS, "base": "BlueMarble_NextGeneration", "layers": {v: d[l] for v, l in GIBS_MAP.items() if l in d}}


# ------------------------------------------------------------------ seasonal cycle and its amplitude
def _period_cycle(d, years, min_per_month):
    """Calendar-month climatology of the given years. Amplitude = highest minus lowest month, only if >= 9 months have enough data."""
    x = d[d.y.isin(years)]
    g = x.groupby("m").v.agg(["mean", "count"])
    months = [dict(m=m, mean=_f(g.loc[m, "mean"]) if m in g.index and g.loc[m, "count"] >= min_per_month else None,
                   n=int(g.loc[m, "count"]) if m in g.index else 0) for m in range(1, 13)]
    ok = [(r["mean"], r["m"]) for r in months if r["mean"] is not None]
    amp = (max(ok)[0] - min(ok)[0]) if len(ok) >= 9 else None
    return dict(label=f"{years[0]}\u2013{years[-1]}", years=[int(years[0]), int(years[-1])], months=months, valid_months=len(ok), amp=_f(amp) if amp is not None else None,
                peak=max(ok)[1] if len(ok) >= 9 else None, trough=min(ok)[1] if len(ok) >= 9 else None)


def cycle_calc(df, min_months=9, min_per_month=3):
    """Seasonal cycle of one monthly series, to show how its swing changes: climatology of the early vs the late half of the years,
    and the yearly amplitude (highest minus lowest month of each year, years with >= min_months months) with a Mann-Kendall / Sen trend."""
    d = df.copy(); d["y"] = np.floor(d.t + 1e-9).astype(int)
    ys = sorted(d.y.unique())
    if len(ys) < 6: raise HTTPException(422, "Need at least 6 years of data to compare seasonal cycles")
    h = len(ys) // 2
    early, late = _period_cycle(d, ys[:h], min_per_month), _period_cycle(d, ys[len(ys) - h:], min_per_month)
    change = None
    if early["amp"] and late["amp"] is not None and early["amp"] > 1e-12: change = _f(100 * (late["amp"] - early["amp"]) / early["amp"])
    yearly = []
    for y in ys:
        x = d[d.y == y]
        yearly.append(dict(y=int(y), n=int(len(x)), mean=_f(x.v.mean()), amp=_f(x.v.max() - x.v.min()) if len(x) >= min_months else None))
    ya = [r for r in yearly if r["amp"] is not None]
    trend = None
    if len(ya) >= 6:
        yy, aa = np.array([r["y"] for r in ya], float), np.array([r["amp"] for r in ya])
        tau, pk = stats.kendalltau(yy, aa); sl = stats.theilslopes(aa, yy)[0]
        trend = dict(slope=_f(sl), tau=_f(tau), p=_f(pk), n=len(ya), sig=bool(pk < .05))
    return dict(early=early, late=late, amp_change_pct=change, yearly=yearly, amp_trend=trend)


@app.get("/api/cycle")
def api_cycle(vars: str = "T2M,hcm_aod,hcm_no2", city: str | None = None, lat: float | None = None, lon: float | None = None,
              start: int = 2004, end: int = 2025):
    """Seasonal-cycle amplitude of several indicators at one place (monthly or yearly view in the UI). Presets (AOD, NO2) exist only for their own city."""
    la, lo = resolve_point(city, lat, lon)
    items, skipped = [], []
    for v in [x.strip() for x in vars.split(",") if x.strip()][:6]:
        pr = find_preset(v)
        if pr and pr["kind"] == "csv" and pr.get("city") != city:
            skipped.append(dict(var=v, reason="no data for this place")); continue
        try:
            df, meta = get_series(v, la, lo, start, end)
            df = df[(df.t >= start) & (df.t < end + 1)].reset_index(drop=True)
            items.append(dict(var=v, unit=meta.get("unit", ""), name=meta["name"], **cycle_calc(df)))
        except HTTPException as e:
            skipped.append(dict(var=v, reason=str(e.detail)))
    if not items: raise HTTPException(422, "No indicator had enough data: " + "; ".join(x["reason"] for x in skipped))
    return dict(city=city, lat=la, lon=lo, start=start, end=end, items=items, skipped=skipped)


@app.get("/api/correlations")
def api_correlations():
    """Candidate correlations between variables of the HCMC case. Computed by the preprocessing module (scripts/prepare_hcm_data.py),
    not here: this endpoint only serves data/processed/correlations.json."""
    f = ROOT.parent / "data" / "processed" / "correlations.json"
    if not f.exists(): raise HTTPException(404, "correlations.json not found: run python scripts/prepare_hcm_data.py")
    return json.load(open(f, encoding="utf-8"))


@app.get("/api/highlights")
def api_highlights(limit: int = 12):
    """Notable changes of the LAST 7 DAYS (vs the normal for this time of year) across all cities and indicators. Computed in a background thread:
    poll until `finished` (items fill in as cities complete). One week, not a climate trend."""
    key, st = hl_state()
    with HL_LOCK: rows = list(st["rows"]); done = st["done"]
    return dict(as_of=key, done=done, total=len(CITIES), finished=bool(st["finished"]), tests=len(rows), items=pick_highlights(rows, max(1, min(limit, 40))))

@app.get("/api/brief")
def api_brief(city: str | None = None, lat: float | None = None, lon: float | None = None, start: int = 2000, end: int = 2024):
    """One-page decision brief for planners and consultants."""
    la, lo = resolve_point(city, lat, lon)
    return build_brief(city, la, lo, start, end)

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
    a["verdict"] = verdict(a, m["unit"], m["name"]); a["source"] = var; a["quality"] = data_quality(df); a["evidence"] = evidence_for(df)
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
    a["verdict"] = verdict(a, unit, dict(vi=nm, en=nm)); a["source"] = "upload"; a["quality"] = data_quality(df); a["evidence"] = evidence_for(df)
    return a

class NoCacheStatic(StaticFiles):
    """Browsers may keep serving an old app.js / home.js for hours; ask them to revalidate (ETag) on every load so a new version shows up at once."""
    async def get_response(self, path, scope):
        r = await super().get_response(path, scope); r.headers["Cache-Control"] = "no-cache"; return r

app.mount("/", NoCacheStatic(directory=ROOT.parent / "frontend", html=True), name="web")
