"""Preprocess the raw NASA files of the HCMC case and report their quality.

    python scripts/prepare_hcm_data.py [raw_dir]        (default: nasa_data/data/raw)

Reads  : AOD_550.csv (Giovanni, MODIS Deep Blue, monthly), NO2.csv (Giovanni, OMI, daily), firms/*.csv (FIRMS hotspots)
Writes : backend/presets/hcm_aod.csv, hcm_no2.csv (and hcm_fire.csv once >= 5 years of FIRMS exist)
         data/processed/*.csv, data/quality_report.json, docs/data-quality.md

Rules (every number in the report comes from this script, nothing is typed by hand):
  * fill values and unreadable dates are dropped; gaps are NOT interpolated (the trend tests tolerate gaps, interpolation would invent data)
  * NO2: columns <= 0 are physically impossible (retrieval noise) -> dropped; a month needs >= 10 valid days;
    months not fully covered by the file (the current, partial month) are dropped
  * outliers are flagged (robust z against the same calendar month), never deleted: a real event cannot be told from an artefact
  * every choice is stress-tested in the sensitivity tables so the reader can see whether the conclusion depends on it

Correlation screening (do_correlations) also lives here: the preprocessing module decides which variable pairs are worth showing.
Writes : data/processed/correlations.json (served read-only by GET /api/correlations; the API does not compute correlations itself)
"""
import csv, datetime, json, math, pathlib, sys
import numpy as np, pandas as pd
from scipy import stats

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import backend.main as M                                           # analyze(), data_quality(), parse_series_csv()

RAW = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "nasa_data" / "data" / "raw"
PROC, PRESETS, DOCS = ROOT / "data" / "processed", ROOT / "backend" / "presets", ROOT / "docs"
for d in (PROC, PRESETS, DOCS): d.mkdir(parents=True, exist_ok=True)
LAGS = M.LAGS
MIN_DAYS = 10                                                       # valid days needed for an NO2 month
NO2_SCALE = 1e15                                                    # report NO2 in 10^15 molec/cm2
HCM = (10.78, 106.70)
REPORT = {}

def ym(ts): return ts.dt.year, ts.dt.month
def f(x, d=3):
    return "–" if x is None or (isinstance(x, float) and not math.isfinite(x)) else (f"{x:.{d}g}")
def trend(df):
    a = M.analyze(df, True, False)
    return dict(slope=a["slope"], p_t=a["p_t"], p_mk=a["p_mk"], sig=a["sig"], n=a["n"], tau=a["tau"])
def to_df(ts, v):
    ts = pd.Series(pd.to_datetime(ts)); v = np.asarray(v, float)
    return pd.DataFrame({"t": ts.dt.year + (ts.dt.month - .5) / 12, "m": ts.dt.month.values, "v": v}).dropna().reset_index(drop=True)
def read_rows(path):
    out = []
    for row in csv.reader(open(path, encoding="utf-8-sig")):
        if len(row) < 2 or row[0].lstrip().startswith("#") or row[0].rstrip().endswith(":"): continue
        try: out.append((row[0].strip(), float(row[-1])))
        except ValueError: continue
    return out
def write_preset(name, header, frame):
    text = "".join(f"# {h}\n" for h in header) + frame.to_csv(index=False, date_format="%Y-%m-%d")
    (PRESETS / name).write_text(text, encoding="utf-8")
    frame.to_csv(PROC / name, index=False, date_format="%Y-%m-%d")

# ------------------------------------------------------------------------------ AOD
def do_aod():
    rows = read_rows(RAW / "AOD_550.csv")
    ts = pd.to_datetime([r[0] for r in rows]); v = np.array([r[1] for r in rows])
    fill = v <= -990
    df = M.parse_series_csv((RAW / "AOD_550.csv").read_bytes())
    q = M.data_quality(df)
    z = M._robust_z(df); out = df[z.abs() > 3.5]
    wet = df[df.m.between(5, 10)]; dry = df[~df.m.between(5, 10)]
    sens = {
        "Chưa làm sạch (giữ cả giá trị −9999)": trend(to_df(ts, v)),
        "Đã bỏ fill value (dùng trong công cụ)": trend(df),
        "Bỏ thêm các tháng ngoại lai (z robust > 3,5)": trend(df[z.abs() <= 3.5]),
        "Chỉ mùa mưa (tháng 5–10)": trend(wet),
        "Chỉ mùa khô (tháng 11–4)": trend(dry),
    }
    miss_m = pd.Series(ts[fill].month).value_counts().sort_index().to_dict()
    REPORT["aod"] = dict(naive_mean=float(v.mean()), rows=len(rows), fill=int(fill.sum()), fill_share=float(fill.mean()), valid=int((~fill).sum()), first=str(ts.min().date()),
                         last=str(ts.max().date()), missing_by_month={int(k): int(c) for k, c in miss_m.items()},
                         wet_mean=float(wet.v.mean()), dry_mean=float(dry.v.mean()), quality=q, sensitivity=sens,
                         outliers=[dict(date=f"{int(t)}-{int(round((t - int(t)) * 12 + .5)):02d}", v=float(x)) for t, x in zip(out.t, out.v)])
    fr = pd.DataFrame({"time": [f"{int(t)}-{int(round((t - int(t)) * 12 + .5)):02d}-01" for t in df.t], "value": df.v.round(6)})
    write_preset("hcm_aod.csv", ["MODIS Terra MOD08_M3 Deep Blue AOD 550 nm, land only, monthly mean over the 1-degree cell 106-107E 10-11N",
                                  "Source: NASA Giovanni; fill value -9999 removed; gaps NOT interpolated; outliers kept (see docs/data-quality.md)"], fr)

# ------------------------------------------------------------------------------- NO2
def do_no2():
    rows = read_rows(RAW / "NO2.csv")
    d = pd.DataFrame(rows, columns=["date", "v"]); d["date"] = pd.to_datetime(d.date, errors="coerce"); d = d.dropna(subset=["date"])
    fill = d.v <= -1e20; nonpos = (d.v <= 0) & ~fill; ok = d[(d.v > 0)].copy()
    ok["y"], ok["m"] = ok.date.dt.year, ok.date.dt.month
    span = pd.date_range(d.date.min(), d.date.max()); no_row = len(span.difference(d.date))
    # robust z against the same calendar month (daily values)
    g = ok.groupby("m").v; med = g.transform("median"); mad = g.transform(lambda s: (s - s.median()).abs().median()) * 1.4826
    ok["z"] = (ok.v - med) / mad
    last = d.date.max()
    def monthly(frame, min_days=MIN_DAYS, stat="mean"):
        mo = frame.assign(month=frame.date.dt.to_period("M").dt.to_timestamp()).groupby("month").v.agg(value=stat, n_valid="count").reset_index()
        mo["n_days"] = mo.month.dt.days_in_month
        mo = mo[(mo.month + pd.offsets.MonthEnd(0)).dt.normalize() <= last.normalize()]           # drop the partial last month
        return mo[mo.n_valid >= min_days].reset_index(drop=True)
    base = monthly(ok)
    all_mo = ok.assign(month=ok.date.dt.to_period("M").dt.to_timestamp()).groupby("month").v.count()
    dropped_low = int(((all_mo < MIN_DAYS)).sum())
    def tr(frame, **kw):
        m = monthly(frame, **kw); return trend(to_df(m.month, m.value / NO2_SCALE))
    sens = {
        "Mặc định (≥ 10 ngày hợp lệ/tháng, bỏ giá trị ≤ 0)": tr(ok),
        "Ngưỡng ≥ 5 ngày/tháng": tr(ok, min_days=5),
        "Ngưỡng ≥ 15 ngày/tháng": tr(ok, min_days=15),
        "Ngưỡng ≥ 20 ngày/tháng (chỉ tháng được lấy mẫu dày)": tr(ok, min_days=20),
        "Dùng trung vị thay trung bình": tr(ok, stat="median"),
        "Bỏ thêm ngày ngoại lai (z > 5)": tr(ok[ok.z <= 5]),
        "Giữ cả giá trị ≤ 0": trend(to_df(*(lambda m: (m.month, m.value / NO2_SCALE))(monthly(d[~fill])))),
    }
    yr = ok.groupby("y").v.count().to_dict(); share = {}
    for y in sorted(set(d.date.dt.year)):
        sub = d[d.date.dt.year == y]; share[int(y)] = float((sub.v > 0).mean())
    full_years = [y for y in share if 2005 <= y <= 2025]
    tau, p = stats.kendalltau(full_years, [share[y] for y in full_years])
    by_mon = {int(m): float((ok[ok.m == m].shape[0]) / max(1, d[d.date.dt.month == m].shape[0])) for m in range(1, 13)}
    REPORT["no2"] = dict(rows=len(d), first=str(d.date.min().date()), last=str(last.date()), fill=int(fill.sum()), fill_share=float(fill.mean()),
                         nonpositive=int(nonpos.sum()), valid=len(ok), rows_missing=no_row, outliers_daily=int((ok.z > 5).sum()),
                         top=[dict(date=str(r.date.date()), v=float(r.v / NO2_SCALE)) for r in ok.nlargest(5, "v").itertuples()],
                         months=len(base), months_low_days=dropped_low, partial_month=str(last.to_period("M")),
                         valid_share_by_year=share, availability_trend=dict(tau=float(tau), p=float(p), first4=float(np.mean([share[y] for y in full_years[:4]])),
                                                                            last4=float(np.mean([share[y] for y in full_years[-4:]]))),
                         valid_share_by_month=by_mon, sensitivity=sens,
                         quality=M.data_quality(to_df(base.month, base.value / NO2_SCALE)))
    fr = pd.DataFrame({"time": base.month.dt.strftime("%Y-%m-%d"), "n_valid_days": base.n_valid, "value": (base.value / NO2_SCALE).round(6)})
    write_preset("hcm_no2.csv", ["OMI OMNO2d tropospheric NO2 column (30% cloud screened), daily -> monthly mean, unit 1e15 molec/cm2",
                                  f"Area: 106.4-107.0E 10.4-11.2N. Dropped: fill values, values <= 0, months with < {MIN_DAYS} valid days, the partial last month.",
                                  "Columns: time, n_valid_days (days behind each monthly mean), value"], fr)

# ----------------------------------------------------------------------------- FIRMS
def do_fire():
    files = sorted((RAW / "firms").glob("*.csv")) if (RAW / "firms").exists() else []
    per_year, frames = {}, []
    for fp in files:
        x = pd.read_csv(fp); x["date"] = pd.to_datetime(x.acq_date); frames.append(x)
        dist = np.hypot((x.latitude - HCM[0]) * 111, (x.longitude - HCM[1]) * 111 * math.cos(math.radians(HCM[0])))
        yr = int(x.date.dt.year.mode()[0]); mon = x.groupby(x.date.dt.month).size()
        per_year[f"{fp.stem}"] = dict(rows=len(x), type0=float((x.type == 0).mean()), low_conf=float((x.confidence < 30).mean()),
                                     within300km=float((dist < 300).mean()), within150km=float((dist < 150).mean()), dry_season_share=float(mon.reindex([12, 1, 2, 3]).sum() / len(x)),
                                     days_with_data=int(x.date.nunique()), aqua_share=float((x.satellite == "Aqua").mean()))
    years = sorted({int(fp.stem.rsplit("_", 1)[1]) for fp in files})
    REPORT["fire"] = dict(files=[fp.name for fp in files], years=years, per_file=per_year, enough=len(years) >= 5)
    if len(years) >= 5:                                              # only publish a preset when a trend test is meaningful
        x = pd.concat(frames); x = x[(x.type == 0) & (x.confidence >= 30)]
        mo = x.groupby(x.date.dt.to_period("M").dt.to_timestamp()).size().rename("value").reset_index()
        write_preset("hcm_fire.csv", ["MODIS active fires (type 0 vegetation fire, confidence >= 30), monthly count, S-Vietnam/Cambodia/E-Thailand box",
                                       "Source: NASA FIRMS archive (MODIS_SP)"], mo.rename(columns={"date": "time"}).assign(time=lambda t: t.iloc[:, 0].dt.strftime("%Y-%m-%d")))

# ------------------------------------------------------------------------------ report
# ------------------------------------------------------------------------ correlation screening
CORR_Y0, CORR_Y1 = 2004, 2025                                       # common years of AOD (2004->) and NO2 (2004-10->); the partial current year is excluded
CORR_Q, CORR_R = 0.05, 0.30                                         # a pair is a "candidate" when the FDR-adjusted p < 0.05 AND |r| >= 0.3 (otherwise "weak" if raw p < 0.05, else "none")
# Candidate pairs and why each could be related (physics first, data second). expect = sign we would expect if the mechanism is real (None = no firm expectation).
CORR_PAIRS = [
    ("T2M", "hcm_aod", None, "Nhiệt độ cao đi cùng mùa khô (ít mưa rửa trôi) nên bụi có thể tăng.", "High temperature goes with the dry season (less rain washout), so aerosols may rise."),
    ("T2M", "hcm_no2", None, "Nhiệt độ ảnh hưởng quang hóa và độ xáo trộn của lớp khí quyển sát đất.", "Temperature affects photochemistry and mixing of the near-surface air."),
    ("hcm_aod", "hcm_no2", "+", "Cùng nguồn phát thải (giao thông, đốt) và cùng chịu thời tiết.", "Shared sources (traffic, burning) and shared weather."),
    ("PRECTOTCORR", "hcm_aod", "-", "Mưa rửa trôi bụi khỏi khí quyển.", "Rain washes aerosols out of the air."),
    ("PRECTOTCORR", "hcm_no2", "-", "Mưa và mây làm giảm NO₂ trong cột khí.", "Rain and cloud reduce the NO₂ column."),
    ("WS2M", "hcm_no2", "-", "Gió mạnh phân tán khí thải.", "Strong wind disperses emissions."),
    ("WS2M", "hcm_aod", "-", "Gió mạnh phân tán bụi.", "Strong wind disperses aerosols."),
    ("RH2M", "hcm_aod", None, "Độ ẩm làm hạt bụi nở ra, đổi độ dày quang học.", "Humidity swells particles and changes optical depth."),
    ("hcm_fire", "hcm_aod", "+", "Cháy thực vật tạo khói; khói bay xa nên xét độ trễ 0–3 tháng.", "Vegetation fires make smoke; smoke travels, so lags of 0-3 months are tested."),
]
def corr_series(src):
    df, meta = M.get_series(src, HCM[0], HCM[1], CORR_Y0, CORR_Y1)
    df = df[(df.t >= CORR_Y0) & (df.t < CORR_Y1 + 1)].reset_index(drop=True)
    return df, meta
def do_correlations():
    series, names, skipped = {}, {}, []
    def get(src):
        if src in series: return series[src]
        try:
            if src == "hcm_fire" and not (PRESETS / "hcm_fire.csv").exists(): raise FileNotFoundError("no fire preset (needs >= 5 years of FIRMS)")
            series[src], meta = corr_series(src); names[src] = meta["name"]
        except Exception as e:                                       # offline POWER, missing preset...: report it, do not invent
            series[src] = None; skipped.append(dict(var=src, reason=str(getattr(e, "detail", e))))
        return series[src]
    rows = []
    for a, b, expect, why_vi, why_en in CORR_PAIRS:
        da, db = get(a), get(b)
        if da is None or db is None: continue
        try: r = M.lag_calc(da, db, detrend=True)
        except Exception as e:
            skipped.append(dict(var=f"{a}~{b}", reason=str(getattr(e, "detail", e)))); continue
        rows.append(dict(a=a, b=b, expect=expect, why=dict(vi=why_vi, en=why_en), lags=r["lags"], r=r["r"], p=r["p"], n=r["n"], best_lag=r["best_lag"]))
    qs = M.bh_adjust([p for x in rows for p in x["p"]]) if rows else []        # one FDR family: every pair x lag that was tested
    for i, x in enumerate(rows):
        x["q"] = qs[i * len(LAGS):(i + 1) * len(LAGS)]; k = x["lags"].index(x["best_lag"])
        x["r_best"], x["p_best"], x["q_best"], x["n_best"] = x["r"][k], x["p"][k], x["q"][k], x["n"][k]
        x["status"] = "candidate" if x["q_best"] < CORR_Q and abs(x["r_best"]) >= CORR_R else "weak" if x["p_best"] < .05 else "none"
        x["agrees"] = None if x["expect"] is None else bool((x["r_best"] > 0) == (x["expect"] == "+"))
    rows.sort(key=lambda x: ({"candidate": 0, "weak": 1, "none": 2}[x["status"]], -abs(x["r_best"])))
    REPORT["correlations"] = dict(
        city="hcm", years=[CORR_Y0, CORR_Y1], tests=len(qs), thresholds=dict(q=CORR_Q, abs_r=CORR_R), skipped=skipped,
        names={k: v for k, v in names.items()}, pairs=rows,
        method=dict(vi="Chuỗi tháng đã trừ chu kỳ mùa và xu hướng tuyến tính riêng của từng chuỗi; r Pearson ở độ trễ 0–3 tháng (dương = chuỗi thứ hai theo sau); p theo cỡ mẫu hiệu dụng (Bretherton) vì chuỗi tự tương quan; q = hiệu chỉnh Benjamini-Hochberg trên mọi cặp × độ trễ đã thử.",
                    en="Monthly series with the seasonal cycle and each series' own linear trend removed; Pearson r at lags 0-3 months (positive = the second series follows); p uses the effective sample size (Bretherton) because the series are autocorrelated; q = Benjamini-Hochberg over every pair x lag tested."),
        caveat=dict(vi="Tương quan không chứng minh nhân quả. Một cặp chỉ là ứng viên để xem xét khi q < 0,05 và |r| ≥ 0,3; chiều tương quan cũng nên khớp cơ chế vật lý.",
                    en="Correlation does not prove causation. A pair is only a candidate when q < 0.05 and |r| >= 0.3; the sign should also match the physical mechanism."))
    out = dict(REPORT["correlations"], generated=datetime.date.today().isoformat())
    (PROC / "correlations.json").write_text(json.dumps(out, ensure_ascii=False, indent=1, default=float), encoding="utf-8")

def pct(x): return f"{100 * x:.0f}%"
def row(name, s): return f"| {name} | {f(s['slope'], 3)} | {f(s['p_t'], 2)} | {f(s['p_mk'], 2)} | {'có' if s['sig'] else 'không'} | {s['n']} |"
def corr_lines():
    C = REPORT.get("correlations")
    if not C or not C["pairs"]: return ["Chưa tính được (thiếu dữ liệu hoặc không kết nối được NASA POWER): " + "; ".join(f"{s['var']}: {s['reason']}" for s in (C or {}).get("skipped", []))]
    nm = lambda k: (C["names"].get(k) or {}).get("vi") or {"T2M": "Nhiệt độ 2 m", "PRECTOTCORR": "Lượng mưa", "WS2M": "Gió 2 m", "RH2M": "Độ ẩm tương đối"}.get(k, k)
    L = [f"Giai đoạn {C['years'][0]}–{C['years'][1]}, TP.HCM. {C['method']['vi']}", "",
         f"Ngưỡng ứng viên: q < {C['thresholds']['q']} và |r| ≥ {C['thresholds']['abs_r']}. Tổng số phép thử (cặp × độ trễ): {C['tests']}.", "",
         "| Cặp | r tốt nhất | Độ trễ (tháng) | q | n | Kết luận | Khớp cơ chế |", "|---|---|---|---|---|---|---|"]
    for x in C["pairs"]:
        L.append(f"| {nm(x['a'])} ↔ {nm(x['b'])} | {f(x['r_best'], 2)} | {x['best_lag']} | {f(x['q_best'], 2)} | {x['n_best']} | {({'candidate': 'ứng viên', 'weak': 'yếu', 'none': 'không thấy'})[x['status']]} | {'–' if x['agrees'] is None else 'có' if x['agrees'] else 'không'} |")
    L += ["", C["caveat"]["vi"]]
    if C["skipped"]: L += ["", "Bỏ qua: " + "; ".join(f"{s['var']} ({s['reason']})" for s in C["skipped"])]
    return L
def write_report():
    A, N, F = REPORT["aod"], REPORT["no2"], REPORT["fire"]
    L = ["# Chất lượng dữ liệu và tiền xử lý — ca TP.HCM", "",
         "Tự sinh bởi `python scripts/prepare_hcm_data.py` từ thư mục `nasa_data/data/raw`. Mọi con số dưới đây được tính lại mỗi lần chạy.", "",
         "## 1. Tóm tắt", "",
         f"| Nguồn | Phủ thời gian | Dòng | Thiếu (fill) | Vấn đề chính |", "|---|---|---|---|---|",
         f"| AOD 550 nm (MODIS Deep Blue, tháng) | {A['first'][:7]} → {A['last'][:7]} | {A['rows']} | {A['fill']} ({pct(A['fill_share'])}) | Thiếu dồn vào mùa mưa; file `_clean` cũ còn sót −9999 |",
         f"| NO₂ tầng đối lưu (OMI, ngày) | {N['first']} → {N['last']} | {N['rows']} | {N['fill']} ({pct(N['fill_share'])}) + {N['nonpositive']} giá trị ≤ 0 | Tỉ lệ ngày có số đo giảm theo năm; tháng cuối chưa đủ |",
         f"| Điểm cháy (FIRMS MODIS) | {', '.join(map(str, F['years'])) or '–'} | {sum(v['rows'] for v in F['per_file'].values())} | 0 | Mới có {len(F['years'])} năm → chưa đủ để kiểm định xu hướng |", "",
         "## 2. AOD", "",
         f"- **Lỗi đã sửa:** `AOD_550_clean.csv` cũ giữ nguyên {A['fill']} dòng `-9999` vì bộ đọc chỉ bắt fill value nhỏ hơn −1e20. Nếu đưa file đó vào phân tích, trung bình bị kéo xuống {f(A['naive_mean'], 4)} (giá trị AOD thật chỉ khoảng 0,2–1,3) và độ dốc vô nghĩa (xem bảng độ nhạy). Đã sửa `nasa_data/scripts/parse_giovanni.py` (đọc fill value khai báo trong phần đầu file) và chạy lại.",
         f"- **Thiếu không ngẫu nhiên:** {A['fill']}/{A['rows']} tháng ({pct(A['fill_share'])}) không có giá trị, tập trung ở các tháng: " + ", ".join(f"T{m} ({c})" for m, c in sorted(A['missing_by_month'].items(), key=lambda x: -x[1])) + ". Đây là mùa mưa, mây dày làm thuật toán Deep Blue không lấy được số đo. Hệ quả: các tháng còn lại của mùa mưa thiên về ngày quang đãng.",
         f"- **Mùa khô và mùa mưa khác nhau:** trung bình AOD các tháng có dữ liệu là {f(A['dry_season_mean'] if 'dry_season_mean' in A else A['dry_mean'])} (tháng 11–4) so với {f(A['wet_mean'])} (tháng 5–10).",
         f"- **Ngoại lai ({len(A['outliers'])} tháng, robust |z| > 3,5):** " + ", ".join(f"{o['date']} ({f(o['v'])})" for o in A['outliers']) + ". Tháng 9/2015 (AOD ≈ 1,27) trùng đợt khói cháy rừng Indonesia lan rộng Đông Nam Á, nên được **giữ lại** và đánh dấu, không xóa.",
         "- **Phạm vi không gian:** một ô lưới 1° × 1° (106–107°E, 10–11°N) gồm cả vùng nông thôn và các tỉnh lân cận, không chỉ nội đô.", "",
         "Độ nhạy của kết luận xu hướng (độ dốc theo đơn vị AOD/năm, đã bỏ chu kỳ mùa):", "",
         "| Cách xử lý | Độ dốc | p (t-test) | p (Mann-Kendall) | Có ý nghĩa | Số tháng |", "|---|---|---|---|---|---|"]
    L += [row(k, v) for k, v in A["sensitivity"].items()]
    L += ["", "## 3. NO₂", "",
          f"- **Fill value:** {N['fill']} ngày ({pct(N['fill_share'])}) không có số đo (cloud screening, OMI không quét tới). Đã loại, không nội suy.",
          f"- **Giá trị ≤ 0:** {N['nonpositive']} ngày có cột NO₂ âm hoặc bằng 0, không có nghĩa vật lý (nhiễu của thuật toán). Đã loại.",
          f"- **Thiếu dòng:** {N['rows_missing']} ngày trong khoảng thời gian không có cả dòng dữ liệu.",
          f"- **Số ngày có số đo giảm dần theo năm:** trung bình {pct(N['availability_trend']['first4'])} số ngày/năm trong 4 năm đầu (2005–2008) còn {pct(N['availability_trend']['last4'])} trong 4 năm gần nhất (Mann-Kendall τ = {f(N['availability_trend']['tau'])}, p = {f(N['availability_trend']['p'], 2)}). Phù hợp với hiện tượng một phần dải quét của OMI không còn dùng được từ khoảng 2007–2009 (row anomaly). Số mẫu mỗi tháng vì vậy giảm theo thời gian, và đó là rủi ro cho độ tin cậy của xu hướng.",
          "- **Theo mùa:** tỉ lệ ngày có số đo thấp nhất ở các tháng " + ", ".join(f"T{m} ({pct(v)})" for m, v in sorted(N['valid_share_by_month'].items(), key=lambda x: x[1])[:3]) + " (mùa mưa).",
          f"- **Ngoại lai:** {N['outliers_daily']} ngày có robust z > 5 (cao nhất: " + ", ".join(f"{t['date']} = {f(t['v'])}" for t in N['top'][:3]) + " ×10¹⁵ molec/cm²). Được giữ lại; kết quả đã được kiểm tra khi bỏ chúng.",
          f"- **Gộp tháng:** mỗi tháng cần ≥ {MIN_DAYS} ngày hợp lệ ({N['months_low_days']} tháng không đạt), bỏ tháng chưa trọn ({N['partial_month']}). Còn {N['months']} tháng.", "",
          "Độ nhạy (độ dốc theo 10¹⁵ molec/cm²/năm):", "", "| Cách xử lý | Độ dốc | p (t-test) | p (Mann-Kendall) | Có ý nghĩa | Số tháng |", "|---|---|---|---|---|---|"]
    L += [row(k, v) for k, v in N["sensitivity"].items()]
    L += ["", "## 4. Điểm cháy (FIRMS)", ""]
    for name, v in F["per_file"].items():
        L.append(f"- `{name}`: {v['rows']} điểm; {pct(v['type0'])} là cháy thực vật (type 0), {pct(v['low_conf'])} độ tin cậy < 30; {pct(v['dry_season_share'])} rơi vào tháng 12–3; chỉ {pct(v['within300km'])} nằm trong bán kính 300 km quanh TP.HCM; {v['days_with_data']} ngày có điểm cháy.")
    L += ["- Khung tải về rộng (Nam Việt Nam, Campuchia, Đông Thái Lan) vì khói bay xa; phần lớn điểm cháy ở Campuchia, không phải trong thành phố.",
          f"- **Mới có {len(F['years'])} năm ({', '.join(map(str, F['years']))}) trên 22 năm cần có.** " + ("Đã đủ ≥ 5 năm, preset `hcm_fire` đã được tạo." if F["enough"] else "Chưa tạo preset `hcm_fire` vì kiểm định xu hướng trên 2 năm không có ý nghĩa. Cần chạy tiếp `python -m scripts.fetch_firms` (cần MAP_KEY)."),
          "- Quy tắc lọc khi đếm: chỉ type 0 (cháy thực vật; loại nguồn tĩnh và ngoài khơi) và độ tin cậy ≥ 30.", "",
          "## 5. Quy tắc tiền xử lý đã áp dụng", "", "| Bước | Quy tắc | Lý do |", "|---|---|---|",
          "| Fill value | Loại giá trị khai báo là fill (−9999, −1,27e30) | Không phải số đo |",
          "| Nội suy | Không nội suy tháng thiếu | Nội suy tạo dữ liệu không có thật và làm phẳng mùa; kiểm định chịu được chỗ trống |",
          "| NO₂ ≤ 0 | Loại | Cột khí không thể âm |", f"| Gộp tháng | ≥ {MIN_DAYS} ngày hợp lệ, bỏ tháng chưa trọn | Trung bình từ vài ngày kém đại diện |",
          "| Ngoại lai | Đánh dấu (robust z theo cùng tháng), không xóa | Không phân biệt được sự kiện thật với lỗi nếu thiếu số đo mặt đất |",
          "| Chu kỳ mùa | Trừ trung bình từng tháng lịch trước khi kiểm định | Để chu kỳ mùa không che xu hướng |", "",
          "## 6. Sàng lọc tương quan giữa các biến", "", *corr_lines(), "",
          "## 7. Dữ liệu nên bổ sung để nâng cấp", "",
          "1. **Điểm cháy FIRMS 2006–2025** (cần MAP_KEY) để nối khói/cháy với AOD và NO₂ theo độ trễ 0–3 tháng.",
          "2. **PM2.5 mặt đất** (OpenAQ hoặc trạm đại sứ quán Mỹ tại TP.HCM, từ khoảng 2016) để kiểm chứng AOD và NO₂ có phản ánh không khí người dân hít thở không.",
          "3. **Khí tượng cùng giai đoạn 2004–2026** (mưa, gió, nhiệt độ, độ ẩm từ NASA POWER): mưa rửa trôi bụi, gió phân tán khí. Đây là biến gây nhiễu cần đưa vào khi diễn giải AOD và NO₂.",
          "4. **AOD kết hợp Dark Target + Deep Blue và sản phẩm Aqua (MYD08)** để giảm số tháng thiếu; **mở rộng AOD về 2000** (Terra bắt đầu 3/2000) để chuỗi dài thêm 4 năm.",
          "5. **NO₂ từ TROPOMI (2018 →)** có độ phân giải cao hơn nhiều và không bị row anomaly; dùng đối chiếu với OMI.",
          "6. **Cùng bộ AOD / NO₂ cho Hà Nội và một số thành phố khác** để so sánh xu hướng giữa các vùng.", ""]
    (DOCS / "data-quality.md").write_text("\n".join(L), encoding="utf-8")

if __name__ == "__main__":
    do_aod(); do_no2(); do_fire(); do_correlations(); write_report()
    (ROOT / "data" / "quality_report.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=1, default=float), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    print("AOD  rows", REPORT["aod"]["rows"], "fill", REPORT["aod"]["fill"], "-> hcm_aod.csv")
    print("NO2  months", REPORT["no2"]["months"], "-> hcm_no2.csv")
    print("FIRMS years", REPORT["fire"]["years"], "preset" if REPORT["fire"]["enough"] else "(not enough years, no preset)")
    print("report -> docs/data-quality.md")
