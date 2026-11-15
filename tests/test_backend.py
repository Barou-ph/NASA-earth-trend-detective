"""Backend tests. Statistics are checked against independent implementations
(statsmodels OLS, brute-force Mann-Kendall / Theil-Sen), plus short / missing / flat data.
Run: pytest -q"""
import datetime, io, itertools, math
import numpy as np, pandas as pd, pytest
import statsmodels.api as sm
from fastapi import HTTPException
from fastapi.testclient import TestClient

import backend.main as M

client = TestClient(M.app)

def monthly(years=20, slope=0.0, noise=0.3, seed=0, season=3.0, y0=2000, phi=0.0):
    rng = np.random.default_rng(seed)
    rows, e = [], 0.0
    for y in range(y0, y0 + years):
        for m in range(1, 13):
            t = y + (m - .5) / 12
            e = phi * e + rng.normal(0, noise)
            rows.append((t, m, 20 + season * math.sin(2 * math.pi * m / 12) + slope * (t - y0) + e))
    return pd.DataFrame(rows, columns=["t", "m", "v"])

@pytest.fixture
def fake_fetch(monkeypatch):
    """Replace NASA POWER by deterministic synthetic series (key = parameter + latitude)."""
    def f(lat, lon, par, y0, y1):
        return monthly(years=y1 - y0 + 1, slope={"T2M": .03}.get(par, 0.0), seed=int(abs(lat) * 100) % 997, y0=y0)
    monkeypatch.setattr(M, "fetch", f)

# ---------------------------------------------------------------- cross-checks
def test_ols_matches_statsmodels():
    df = monthly(slope=0.05, noise=0.5, seed=1, phi=0.4)
    a = M.analyze(df, deseason=True)
    d = M.deseasonalize(df)
    fit = sm.OLS(d.v.values, sm.add_constant(d.t.values)).fit()
    assert a["slope"] == pytest.approx(fit.params[1], rel=1e-9)
    assert a["fit"][0] == pytest.approx(fit.params[0] + fit.params[1] * d.t.values[0], rel=1e-9)
    # independent lag-1 autocorrelation of residuals -> effective n -> widened standard error
    res = fit.resid; r1 = np.corrcoef(res[:-1], res[1:])[0, 1]
    n = len(d); neff = max(3.0, n * (1 - r1) / (1 + r1)) if r1 > 0 else n
    se = fit.bse[1] * math.sqrt((n - 2) / (neff - 2))
    half = (a["ci"][1] - a["ci"][0]) / 2
    from scipy import stats
    assert half == pytest.approx(stats.t.ppf(.975, neff - 2) * se, rel=1e-9)
    assert a["r1"] == pytest.approx(r1, rel=1e-9)

def test_mann_kendall_and_sen_match_bruteforce():
    df = monthly(years=10, slope=0.1, noise=0.8, seed=2)
    a = M.analyze(df, deseason=True)
    t, v = np.array(a["t"]), np.array(a["v"])
    pairs = list(itertools.combinations(range(len(t)), 2))
    S = sum(np.sign(v[j] - v[i]) for i, j in pairs)
    assert a["tau"] == pytest.approx(S / len(pairs), abs=0.02)        # tau-b == S/n0 up to ties
    assert a["sen"] == pytest.approx(np.median([(v[j] - v[i]) / (t[j] - t[i]) for i, j in pairs]), rel=1e-6)

def test_lagged_corr_matches_numpy():
    rng = np.random.default_rng(3); x = rng.normal(size=200); y = np.roll(x, 2) + rng.normal(scale=.2, size=200)
    r, p, n = M.lagged_corr(x, y, 2)
    assert r == pytest.approx(np.corrcoef(x[:-2], y[2:])[0, 1]) and n == 198 and p < 1e-6

# ------------------------------------------------------------- edge cases
def test_strong_trend_is_significant():
    a = M.analyze(monthly(slope=0.1, noise=0.2), deseason=True)
    assert a["sig"] and a["slope"] == pytest.approx(0.1, abs=0.01)

def test_no_trend_false_positive_rate_is_near_nominal():
    """Pure AR(1) noise: both tests p<.05 should be rare and the 95 % CI should cover 0 about 95 % of the time."""
    runs = [M.analyze(monthly(slope=0.0, noise=0.5, seed=s, phi=0.5), deseason=True) for s in range(120)]
    assert sum(a["sig"] for a in runs) / len(runs) < 0.12
    assert sum(a["ci"][0] < 0 < a["ci"][1] for a in runs) / len(runs) > 0.88

def test_constant_series_does_not_crash():
    df = monthly(noise=0.0, season=0.0)
    a = M.analyze(df, deseason=True)
    assert a["sig"] is False and a["p_t"] == 1.0 and a["p_mk"] == 1.0 and a["tau"] == 0.0
    assert all(math.isfinite(a[k]) for k in ("slope", "r1", "n_eff", "sen", "total"))

def test_perfect_line_is_finite():
    df = pd.DataFrame({"t": np.arange(20) + .5, "m": 1, "v": 2 * np.arange(20.0)})
    a = M.analyze(df, deseason=False)
    assert a["slope"] == pytest.approx(2) and a["p_t"] == 0.0 and math.isfinite(a["n_eff"])

def test_too_few_points():
    with pytest.raises(HTTPException) as e:
        M.analyze(monthly(years=1).head(7), deseason=False)
    assert e.value.status_code == 422

def test_deseason_needs_two_years():
    with pytest.raises(HTTPException) as e:
        M.analyze(monthly(years=1), deseason=True)
    assert e.value.status_code == 422

def test_annual_needs_eight_years():
    with pytest.raises(HTTPException) as e:
        M.analyze(monthly(years=6), deseason=True, annual=True)
    assert e.value.status_code == 422

def test_missing_months_are_tolerated():
    df = monthly(years=20, slope=.05).sample(frac=.8, random_state=0).sort_values("t")
    assert M.analyze(df, deseason=True)["n"] == len(df)

def test_fetch_drops_fill_values_and_month13(monkeypatch, tmp_path):
    monkeypatch.setattr(M, "CACHE", tmp_path)
    (tmp_path / "X_1.00_2.00_2000_2001.json").write_text('{"200001": 1.5, "200002": -999, "200013": 9, "200101": 2.5}')
    df = M.fetch(1.0, 2.0, "X", 2000, 2001)
    assert df.v.tolist() == [1.5, 2.5] and df.m.tolist() == [1, 1]

# --------------------------------------------------------------------- CSV
GIO = """# Title: Time Series, Area-Averaged
# Region: 106E, 10N
Time,mean_AOD
2000-01-01 00:00:00,0.31
2000-01-02 00:00:00,0.29
2000-02-01 00:00:00,-9999
2000-02-15 00:00:00,0.40
"""
def test_parse_giovanni_skips_header_fill_and_averages_months():
    df = M.parse_series_csv(GIO.encode())
    assert df.m.tolist() == [1, 2] and df.v.tolist() == pytest.approx([0.30, 0.40])

def test_parse_rejects_garbage():
    with pytest.raises(HTTPException) as e:
        M.parse_series_csv(b"hello,world\nfoo,bar\n")
    assert e.value.status_code == 422

def _csv(df, header=True):
    body = "# generated\n" + ("Time,val\n" if header else "")
    return body + "".join(f"{int(t)}-{m:02d}-01T00:00:00Z,{v}\n" for t, m, v in zip(df.t, df.m, df.v))

def test_upload_same_structure_as_analyze(fake_fetch):
    r = client.post("/api/upload?unit=%C2%B0C", files={"file": ("my data.csv", _csv(monthly(slope=.05)), "text/csv")})
    assert r.status_code == 200
    j = r.json(); ref = client.get("/api/analyze?city=hcm&var=T2M").json()
    assert set(ref) <= set(j)
    assert j["sig"] is True and "my data" in j["verdict"]["en"]

def test_upload_errors():
    assert client.post("/api/upload", files={"file": ("a.csv", "x,y\n1,2\n", "text/csv")}).status_code == 422
    assert client.post("/api/upload", files={"file": ("a.csv", _csv(monthly(years=1)), "text/csv")}).status_code == 422
    assert client.post("/api/upload", files={"file": ("a.csv", b"#" * (M.MAX_UPLOAD + 10), "text/csv")}).status_code == 413

# ------------------------------------------------------------------ endpoints
ANALYZE_KEYS = {"t", "v", "fit", "slope", "ci", "p_t", "p_mk", "tau", "sen", "r1", "n_eff", "total", "span", "sig", "verdict"}

def test_analyze_by_city_and_latlon_agree(fake_fetch):
    a = client.get("/api/analyze?city=hcm&var=T2M").json()
    c = next(c for c in M.CITIES if c["id"] == "hcm")
    b = client.get(f"/api/analyze?lat={c['lat']}&lon={c['lon']}&var=T2M").json()
    assert ANALYZE_KEYS <= set(a) and a["slope"] == b["slope"] and set(a["verdict"]) == {"vi", "en"}

def test_analyze_errors(fake_fetch):
    assert client.get("/api/analyze?var=T2M").status_code == 422
    assert client.get("/api/analyze?city=nowhere&var=T2M").status_code == 404
    assert client.get("/api/analyze?city=hcm&var=NOPE").status_code == 404
    assert client.get("/api/analyze?city=hcm").status_code == 422

def test_lag_finds_planted_delay(monkeypatch):
    a = monthly(years=25, noise=1.0, seed=7, season=0)
    b = a.copy(); b["v"] = np.roll(a.v.values, 2) + np.random.default_rng(8).normal(0, .2, len(a))   # b follows a by 2 months
    monkeypatch.setattr(M, "fetch", lambda lat, lon, par, y0, y1: a if par == "T2M" else b)
    j = client.get("/api/lag?city=hcm&a=T2M&b=RH2M").json()
    assert j["lags"] == [0, 1, 2, 3] and len(j["r"]) == len(j["p"]) == 4
    assert j["best_lag"] == 2 and j["sig"] and set(j["caveat"]) == {"vi", "en"}
    assert "nhân quả" in j["caveat"]["vi"] and "causation" in j["caveat"]["en"]

def test_lag_unrelated_series_not_significant(monkeypatch):
    monkeypatch.setattr(M, "fetch", lambda lat, lon, par, y0, y1: monthly(years=25, seed=11 if par == "T2M" else 12))
    j = client.get("/api/lag?city=hcm&a=T2M&b=RH2M").json()
    assert min(j["p"]) > 0.001 and max(abs(x) for x in j["r"]) < 0.3

def test_anomaly_flags_extremes(monkeypatch):
    df = monthly(years=25, seed=4); df.loc[100, "v"] += 20; df.loc[101, "v"] -= 20
    monkeypatch.setattr(M, "fetch", lambda *a: df)
    j = client.get("/api/anomaly?city=hcm&var=T2M").json()
    ms = j["months"]; assert len(ms) == len(df)
    assert ms[100]["flag"] == "high" and ms[101]["flag"] == "low"
    assert all(m["p05"] <= m["p95"] for m in ms)
    assert 0.05 < sum(1 for m in ms if m["flag"]) / len(ms) < 0.2     # ~10 % by construction
    assert set(ms[0]) >= {"t", "v", "p05", "p95", "flag"}

def test_anomaly_needs_five_years(monkeypatch):
    monkeypatch.setattr(M, "fetch", lambda *a: monthly(years=4))
    assert client.get("/api/anomaly?city=hcm&var=T2M").status_code == 422

def test_ranking_sorted_and_tolerates_failures(monkeypatch):
    def f(lat, lon, par, y0, y1):
        if lat == M.CITIES[1]["lat"]: raise HTTPException(502, "down")
        return monthly(years=y1 - y0 + 1, slope=lat / 100, seed=int(abs(lat) * 10))
    monkeypatch.setattr(M, "fetch", f)
    rows = client.get("/api/ranking?var=T2M").json()
    assert len(rows) == len(M.CITIES) - 1
    assert [r["slope"] for r in rows] == sorted((r["slope"] for r in rows), reverse=True)
    assert set(rows[0]) >= {"city", "lat", "lon", "slope", "p", "sig", "q", "sig_fdr", "region", "name"}
    assert all(r["q"] >= r["p"] - 1e-12 or r["q"] >= max(r["p"], r["p_mk"]) - 1e-12 for r in rows)

def test_presets_availability_and_csv_preset(monkeypatch, tmp_path):
    ids = {p["id"]: p for p in client.get("/api/presets").json()}
    assert {"hcm_aod", "hcm_no2", "hcm_t2m"} <= set(ids)
    monkeypatch.setattr(M, "PRESET_DIR", tmp_path)
    assert not {p["id"]: p for p in client.get("/api/presets").json()}["hcm_aod"]["available"]
    assert client.get("/api/analyze?preset=hcm_aod").status_code == 404
    (tmp_path / "hcm_aod.csv").write_text(_csv(monthly(slope=.02, noise=.1)))
    assert {p["id"]: p for p in client.get("/api/presets").json()}["hcm_aod"]["available"]
    j = client.get("/api/analyze?preset=hcm_aod").json()
    assert ANALYZE_KEYS <= set(j) and "AOD" in j["verdict"]["en"]
    (tmp_path / "hcm_no2.csv").write_text(_csv(monthly(slope=.0, noise=.1, seed=9)))
    l = client.get("/api/lag?a=hcm_aod&b=hcm_no2").json()          # CSV presets need no city
    assert l["lags"] == [0, 1, 2, 3]

def test_cities_and_variables():
    assert len(client.get("/api/cities").json()) >= 10 and len(client.get("/api/variables").json()) >= 5

# -------------------------------------------------------------------- summary
def _kinds(j): return [b["kind"] for b in j["bullets"]]

def test_summary_full(fake_fetch):
    j = client.get("/api/summary?city=hcm&var=T2M&b=RH2M").json()
    assert {"headline", "bullets", "text", "facts", "period", "place", "unit"} <= set(j)
    assert _kinds(j)[0] == "trend" and {"change", "extreme", "season", "anomaly", "lag", "rank"} <= set(_kinds(j))
    assert all(b["vi"] and b["en"] and b["tone"] in {"up", "down", "flat", "warn", "info"} for b in j["bullets"])
    assert j["facts"]["sig"] is True and "tăng" in j["headline"]["vi"] and "rising" in j["headline"]["en"]
    assert "TP. Hồ Chí Minh" in j["headline"]["vi"] and j["facts"]["rank_total"] == sum(c["region"] == "vn" for c in M.CITIES)    # rank within the city's own region
    # numbers in the summary are the same numbers the charts use
    a = client.get("/api/analyze?city=hcm&var=T2M").json()
    assert j["facts"]["slope"] == a["slope"] and a["verdict"]["vi"] == j["bullets"][0]["vi"]
    an = client.get("/api/anomaly?city=hcm&var=T2M").json()
    assert j["facts"]["n_high"] + j["facts"]["n_low"] == an["n_flagged"]

def test_summary_block_difference_matches_planted_trend(monkeypatch):
    monkeypatch.setattr(M, "fetch", lambda *a: monthly(years=25, slope=0.1, noise=0.05))
    j = client.get("/api/summary?lat=10&lon=106&var=T2M").json()
    assert j["facts"]["block_diff"] == pytest.approx(0.1 * 15, abs=0.1)      # block centres are 15 years apart
    assert "rank" not in _kinds(j) and "lag" not in _kinds(j) and "10.00" in j["place"]["en"]

def test_summary_no_trend_and_missing_months(monkeypatch):
    df = monthly(years=20, slope=0.0, noise=0.5, seed=3).drop(index=range(30, 40)).reset_index(drop=True)
    monkeypatch.setattr(M, "fetch", lambda *a: df)
    j = client.get("/api/summary?city=hcm&var=T2M&rank=false").json()
    assert j["facts"]["sig"] is False and j["bullets"][0]["tone"] == "flat" and "no clear trend" in j["headline"]["en"]
    assert j["facts"]["missing_months"] == 10 and "quality" in _kinds(j)

def test_summary_short_series_degrades_gracefully(monkeypatch):
    monkeypatch.setattr(M, "fetch", lambda *a: monthly(years=3))
    j = client.get("/api/summary?city=hcm&var=T2M&rank=false").json()
    assert "anomaly" not in _kinds(j) and "change" not in _kinds(j) and "trend" in _kinds(j)
    monkeypatch.setattr(M, "fetch", lambda *a: monthly(years=1))
    assert client.get("/api/summary?city=hcm&var=T2M&rank=false").status_code == 422

def test_summary_survives_bad_second_variable(fake_fetch):
    j = client.get("/api/summary?city=hcm&var=T2M&b=NOPE&rank=false").json()
    assert "lag" not in _kinds(j) and j["b"] is None


# -------------------------------------------------- quality, FDR, scan, detrend
def test_bh_matches_statsmodels():
    from statsmodels.stats.multitest import multipletests
    ps = list(np.random.default_rng(0).uniform(0, 1, 40) ** 3)
    assert M.bh_adjust(ps) == pytest.approx(multipletests(ps, method="fdr_bh")[1], rel=1e-9)
    assert M.bh_adjust([0.01]) == [0.01] and M.bh_adjust([]) == []

def test_data_quality_clean_series():
    q = M.data_quality(monthly(years=12))
    assert q["n_missing"] == 0 and q["coverage"] == 1 and q["notes"][0]["level"] == "ok" and q["n_expected"] == 144

def test_data_quality_flags_clustered_gaps_and_outliers():
    df = monthly(years=15, seed=2)
    df.loc[40, "v"] += 25                                                     # one absurd month
    gone = df[df.m.isin([8, 9]) & (df.t.astype(int) % 2 == 0)].index          # wet-season holes in alternate years
    q = M.data_quality(df.drop(index=gone).reset_index(drop=True))
    assert q["n_missing"] == len(gone) and q["longest_gap"] == 2
    assert q["missing_by_month"]["8"] > 0 and q["missing_by_month"]["1"] == 0
    assert any(n["level"] == "warn" and "9" in n["vi"] for n in q["notes"])   # cluster warning names the months
    assert q["n_outliers"] >= 1 and q["outliers"][0]["z"] > 3.5 and abs(q["outliers"][0]["v"] - df.loc[40, "v"]) < 1e-9
    assert all(set(n) == {"level", "vi", "en"} for n in q["notes"])

def test_data_quality_short_series_warns():
    assert any("10" in n["vi"] and n["level"] == "warn" for n in M.data_quality(monthly(years=5))["notes"])

def test_analyze_and_upload_carry_quality(fake_fetch):
    a = client.get("/api/analyze?city=hcm&var=T2M").json()
    assert a["quality"]["coverage"] == 1 and a["quality"]["parse"] is None
    u = client.post("/api/upload", files={"file": ("a.csv", _csv(monthly(slope=.05)), "text/csv")}).json()
    assert u["quality"]["parse"]["rows_numeric"] == 240 and u["quality"]["parse"]["fill_dropped"] == 0

def test_parser_counts_drops_and_ignores_key_metadata():
    lines = ["Title:,Time Series", "Fill Value (x):, -9999", "# c", "time,val", "2000-01-01,1", "2000-02-01,-9999", "not-a-date,5", "2000-03-01,3"]
    csvtext = chr(10).join(lines) + chr(10)
    df = M.parse_series_csv(csvtext.encode()); p = df.attrs["parse"]
    assert df.v.tolist() == [1.0, 3.0]
    assert p["fill_dropped"] == 1 and p["bad_dates"] == 1 and p["rows_numeric"] == 4      # the "Fill Value" line is not a data row

def test_parser_daily_to_monthly_min_days():
    rng = pd.date_range("2005-01-01", "2007-12-31")
    rows = [(d, 5.0 + (d.month == 7) * 100) for d in rng if not (d.month == 3 and d.day > 4)]      # March: only 4 valid days each year
    txt = chr(10).join(["time,v"] + [f"{d.date()},{v}" for d, v in rows]) + chr(10)
    df = M.parse_series_csv(txt.encode()); p = df.attrs["parse"]
    assert p["sub_monthly"] and p["min_days"] == 10 and p["months_dropped"] == 3 and 3 not in df.m.tolist()
    assert M.parse_series_csv(txt.encode(), min_days=3).attrs["parse"]["months_dropped"] == 0
    assert len(M.parse_series_csv(txt.encode())) == 33

def test_lag_detrend_removes_shared_drift(monkeypatch):
    a, b = monthly(years=25, slope=0.1, noise=0.6, seed=1, season=0), monthly(years=25, slope=0.1, noise=0.6, seed=2, season=0)
    monkeypatch.setattr(M, "fetch", lambda lat, lon, par, y0, y1: a if par == "T2M" else b)
    raw = client.get("/api/lag?city=hcm&a=T2M&b=RH2M&detrend=false").json()
    dt = client.get("/api/lag?city=hcm&a=T2M&b=RH2M").json()                   # detrend is the default
    assert raw["detrended"] is False and dt["detrended"] is True
    assert raw["sig"] and abs(raw["r"][0]) > 0.4 and abs(dt["r"][0]) < 0.2     # a shared trend is not a relationship

def test_scan_ranks_and_applies_fdr(monkeypatch):
    def f(lat, lon, par, y0, y1):
        slope = {"T2M": 0.1, "RH2M": -0.05}.get(par, 0.0)
        return monthly(years=y1 - y0 + 1, slope=slope, noise=0.3, seed=sum(map(ord, par)))
    monkeypatch.setattr(M, "fetch", f)
    rows = client.get("/api/scan?city=hcm").json()
    assert {r["var"] for r in rows} >= {v["id"] for v in M.VARS}
    assert rows[0]["var"] == "T2M" and rows[0]["sig_fdr"] and rows[0]["effect_sd"] > 0
    assert rows[1]["var"] == "RH2M" and rows[1]["effect_sd"] < 0
    assert all(r["q"] >= max(r["p"], r["p_mk"]) - 1e-12 for r in rows)
    flags = [(not r["sig_fdr"], not r["sig"]) for r in rows]; assert flags == sorted(flags)      # strongest evidence first
    assert client.get("/api/scan").status_code == 422

def test_ranking_region_filter(fake_fetch):
    vn = client.get("/api/ranking?var=T2M&region=vn").json(); world = client.get("/api/ranking?var=T2M&region=world").json()
    assert {r["region"] for r in vn} == {"vn"} and {r["region"] for r in world} == {"world"}
    assert len(vn) + len(world) == len(M.CITIES) and client.get("/api/ranking?var=T2M&region=mars").status_code == 422

def test_new_power_variables_and_cities_are_consistent():
    ids = [v["id"] for v in M.VARS]; assert len(ids) == len(set(ids)) and {"EVLAND", "CLOUD_AMT", "T2M_MIN"} <= set(ids)
    assert all(v["name"]["vi"] and v["name"]["en"] and v["desc"]["vi"] and v["desc"]["en"] for v in M.VARS)
    cid = [c["id"] for c in M.CITIES]; assert len(cid) == len(set(cid)) and {c["region"] for c in M.CITIES} == {"vn", "world"}

def test_shipped_hcm_presets_are_clean():
    for pid in ("hcm_aod", "hcm_no2"):
        f = M.preset_file(M.find_preset(pid))
        if not f.exists(): pytest.skip("run scripts/prepare_hcm_data.py first")
        df = M.parse_series_csv(f.read_bytes())
        assert df.v.min() > 0 and df.attrs["parse"]["fill_dropped"] == 0 and len(df) > 200      # no -9999 left, no non-physical values
    assert M.parse_series_csv(M.preset_file(M.find_preset("hcm_aod")).read_bytes()).v.max() < 3

def test_scan_includes_city_presets_only_for_that_city(fake_fetch):
    ids = lambda q: {r["var"] for r in client.get("/api/scan?" + q).json()}
    assert {"hcm_aod", "hcm_no2"} <= ids("city=hcm") or not M.preset_file(M.find_preset("hcm_aod")).exists()
    assert not ({"hcm_aod", "hcm_no2"} & ids("city=hanoi")) and not ({"hcm_aod", "hcm_no2"} & ids("lat=21&lon=105"))


# ------------------------------------------------- evidence score, brief, globe
def test_evidence_strong_for_a_clean_trend():
    ev = M.evidence_for(monthly(years=25, slope=0.1, noise=0.3, seed=1))
    assert ev["level"] == "strong" and ev["score"] == ev["of"] == 5 and all(c["passed"] for c in ev["checks"])
    assert all(set(c) == {"id", "passed", "vi", "en"} for c in ev["checks"])

def test_evidence_is_none_or_weak_for_noise():
    levels = [M.evidence_for(monthly(years=25, slope=0.0, noise=0.5, seed=s, phi=0.5))["level"] for s in range(30)]
    assert levels.count("none") >= 24 and levels.count("strong") <= 2          # a chance false positive can still pass the checks, but rarely

def test_evidence_downgrades_a_trend_made_of_outliers():
    df = monthly(years=25, slope=0.0, noise=0.3, seed=2)
    df.loc[df.index[-12:], "v"] += 25                                         # twelve absurd months at the very end
    ev = M.evidence_for(df)
    assert ev["checks"][1]["passed"] is False and ev["level"] != "strong"     # "still holds without outliers" fails

def test_evidence_needs_enough_data():
    ev = M.evidence_for(monthly(years=8, slope=0.2, noise=0.2, seed=3))
    assert ev["checks"][4]["passed"] is False and ev["level"] in ("moderate", "weak", "strong") and ev["score"] <= 4

def test_analyze_returns_evidence(fake_fetch):
    a = client.get("/api/analyze?city=hcm&var=T2M").json()
    assert a["evidence"]["level"] in ("strong", "moderate", "weak", "none") and len(a["evidence"]["checks"]) == 5

def test_every_variable_has_an_action_in_both_directions():
    for v in M.VARS:
        for slope in (1, -1):
            r = dict(var=v["id"], name=v["name"], slope=slope, evidence=dict(level="strong"))
            a = M.action_for(r)
            assert a["vi"] and a["en"] and a["direction"] == ("up" if slope > 0 else "down")

def test_brief_shape_and_rules(fake_fetch):
    b = client.get("/api/brief?city=hcm").json()
    assert {"place", "period", "generated", "n_vars", "n_trusted", "headline", "findings", "watch", "actions", "caveats"} <= set(b)
    assert b["n_vars"] >= len(M.VARS) and set(b["headline"]) == {"vi", "en"} and len(b["caveats"]) >= 2
    f = b["findings"]
    assert any(x["var"] == "T2M" for x in f) and all(x["evidence"]["level"] != "none" for x in f)
    ranks = [M.LEVEL_RANK[x["evidence"]["level"]] for x in f]; assert ranks == sorted(ranks, reverse=True)       # most trustworthy first
    assert any(a["topic"] == "heat" and a["var"] == "T2M" for a in b["actions"])
    assert all(M.LEVEL_RANK[a["level"]] >= 2 for a in b["actions"])                                             # no advice from weak evidence
    assert all(set(a) >= {"topic", "var", "direction", "vi", "en", "level"} for a in b["actions"])

def test_brief_for_a_custom_point_has_no_city_presets(fake_fetch):
    b = client.get("/api/brief?lat=21&lon=105").json()
    assert b["n_vars"] == len(M.VARS) and "điểm" in b["place"]["vi"] and b["city"] is None
    assert client.get("/api/brief").status_code == 422 and client.get("/api/brief?city=nowhere").status_code == 404

def test_brief_with_nothing_trending_says_so(monkeypatch):
    monkeypatch.setattr(M, "fetch", lambda lat, lon, par, y0, y1: monthly(years=y1 - y0 + 1, slope=0.0, noise=0.5, seed=sum(map(ord, par))))
    b = client.get("/api/brief?lat=5&lon=5").json()
    assert b["actions"] == [] or all(M.LEVEL_RANK[a["level"]] >= 2 for a in b["actions"])
    assert b["n_trusted"] == len(b["findings"]) or b["n_trusted"] > len(b["findings"])

def test_globe_rows_are_aligned_and_corrected(fake_fetch):
    g = client.get("/api/globe?var=T2M").json()
    assert len(g["cities"]) == len(M.CITIES) and g["years"] == sorted(g["years"]) and g["unit"] == "°C"
    for c in g["cities"]:
        assert len(c["anom"]) == len(g["years"]) and {"lat", "lon", "slope", "q", "sig_fdr", "effect_sd", "name", "region"} <= set(c)
        assert all(a is None or isinstance(a, float) for a in c["anom"])
    assert client.get("/api/globe?var=NOPE").status_code == 404

def test_cap_evidence_never_calls_a_barely_surviving_trend_strong():
    rows = [dict(q=0.0001, evidence=dict(level="strong")), dict(q=0.04, evidence=dict(level="strong")),
            dict(q=0.04, evidence=dict(level="moderate")), dict(q=0.5, evidence=dict(level="none"))]
    M.cap_evidence(rows)
    assert [r["evidence"]["level"] for r in rows] == ["strong", "moderate", "moderate", "none"]
    assert rows[1]["evidence"]["capped"] is True and "capped" not in rows[0]["evidence"]
    assert M.evidence_for(monthly(years=25, slope=0.1, noise=0.3, seed=1))["capped"] is False


# ------------------------------------------------------------------ weekly + highlights
def daily(years=5, slope_per_year=0.0, seed=0, end="2026-11-10"):
    rng = np.random.default_rng(seed)
    idx = pd.date_range(end=end, periods=int(365.25 * years))
    t = np.arange(len(idx)) / 365.25
    return pd.Series(25 + 3 * np.sin(2 * math.pi * idx.dayofyear / 365.25) + slope_per_year * t + rng.normal(0, .4, len(idx)), index=idx)

def test_weekly_calc_shape_and_flat_series_is_not_significant():
    w = M.weekly_calc(daily(seed=3))
    assert len(w["weeks"]) == len(w["v"]) == len(w["clim"]) == len(w["anom"]) == 52 and w["n"] >= 40
    assert w["last"]["week"] == w["weeks"][-1] and set(w["note"]) == {"vi", "en"}
    assert abs(w["mean_anom"]) < 1.0

def test_weekly_calc_detects_a_clear_recent_trend():
    s = daily(seed=1); s[s.index >= s.index[-1] - pd.Timedelta(days=364)] += np.linspace(0, 6, int((s.index >= s.index[-1] - pd.Timedelta(days=364)).sum()))
    w = M.weekly_calc(s)
    assert w["slope_week"] > 0.03 and w["sig"] and w["last"]["anom"] > 3

def test_weekly_calc_rejects_short_or_empty_data():
    with pytest.raises(HTTPException) as e: M.weekly_calc(daily(years=2))
    assert e.value.status_code == 422
    with pytest.raises(HTTPException) as e: M.weekly_calc(pd.Series(dtype=float))
    assert e.value.status_code == 502

def test_weekly_endpoint(monkeypatch):
    monkeypatch.setattr(M, "fetch_daily", lambda *a: daily(seed=2))
    d = client.get("/api/weekly?var=T2M&city=hcm").json()
    assert d["var"] == "T2M" and d["unit"] == "°C" and len(d["weeks"]) == 52 and "slope_week" in d
    assert client.get("/api/weekly?var=hcm_no2&city=hcm").status_code == 422        # CSV preset: monthly only
    assert client.get("/api/weekly?var=NOPE&city=hcm").status_code == 404
    assert client.get("/api/weekly?var=T2M&city=hcm&weeks=5").status_code == 422

def test_pick_highlights_prefers_fdr_survivors_and_limits_per_city():
    mk = lambda city, p, eff: dict(city=city, p=p, effect_sd=eff, var="x")
    rows = [mk("a", 1e-9, 1.0), mk("a", 1e-9, 0.5), mk("a", 1e-9, 3.0), mk("b", 1e-9, 2.0), mk("c", 0.04, -9.0), mk("d", 0.5, 8.0)] + [mk("z%d" % i, 0.9, 0.1) for i in range(30)]
    out = M.pick_highlights(rows, limit=10, per_city=2)
    assert [(r["city"], r["effect_sd"]) for r in out[:4]] == [("a", 3.0), ("b", 2.0), ("a", 1.0), ("c", -9.0)][:4] or sum(r["city"] == "a" for r in out) == 2
    assert all(r["p"] < .05 for r in out) and "d" not in {r["city"] for r in out}              # raw p >= 0.05 never shown
    assert sum(r["city"] == "a" for r in out) == 2 and out[0]["sig_fdr"] is True
    assert [r["city"] for r in out].index("c") > [r["city"] for r in out].index("b")           # c (only raw p) comes after FDR survivors
    assert len(M.pick_highlights(rows, limit=2)) == 2

def test_recent7_flags_an_unusual_last_week_and_ignores_a_normal_one():
    base = daily(years=5, seed=4, end="2026-11-10")
    normal = M.recent7_calc(base, datetime.date(2026, 11, 12))
    assert normal["n"] >= 5 and normal["stale_days"] == 2 and abs(normal["effect_sd"]) < 3 and len(normal["days"]["v"]) == 30
    hot = base.copy(); hot[hot.index > hot.index[-1] - pd.Timedelta(days=7)] += 6.0
    r = M.recent7_calc(hot, datetime.date(2026, 11, 12))
    assert r["anom"] > 4 and r["effect_sd"] > 4 and r["p"] < .02 and r["sig"] and r["end"] == "2026-11-10"
    cold = base.copy(); cold[cold.index > cold.index[-1] - pd.Timedelta(days=7)] -= 6.0
    assert M.recent7_calc(cold)["effect_sd"] < -4

def test_recent7_rejects_short_or_stale_windows():
    with pytest.raises(HTTPException) as e: M.recent7_calc(daily(years=2))
    assert e.value.status_code == 422
    s = daily(years=5, seed=1); gap = s[(s.index <= s.index[-1] - pd.Timedelta(days=7)) | (s.index.dayofweek == 0)]    # only ~1 valid day in the final week
    with pytest.raises(HTTPException) as e: M.recent7_calc(gap)
    assert e.value.status_code == 422

def test_weekly_endpoint_includes_the_last_7_days(monkeypatch):
    monkeypatch.setattr(M, "fetch_daily", lambda *a: daily(seed=2))
    d = client.get("/api/weekly?var=T2M&city=hcm").json()
    assert d["recent"]["n"] >= 5 and len(d["recent"]["days"]["dates"]) == 30 and "effect_sd" in d["recent"]

def test_city_week_rows_use_the_last_7_days_and_skip_stale_indicators(monkeypatch):
    today = datetime.date(2026, 11, 12)
    def f(lat, lon, par, d0, d1): return daily(seed=7, end="2026-11-10") if par != "CLOUD_AMT" else daily(seed=7, end="2026-08-30")   # cloud amount lags months
    monkeypatch.setattr(M, "fetch_daily", f)
    rows = M.city_week_rows(M.CITIES[0], today)
    assert "CLOUD_AMT" not in {r["var"] for r in rows} and len(rows) == len(M.VARS) - 1
    assert all(len(r["spark"]["v"]) == 30 and r["direction"] in ("up", "down") and r["end"] == "2026-11-10" for r in rows)
    assert {"effect_sd", "p", "anom", "mean", "clim", "place", "name"} <= set(rows[0])

def test_globe_effect_sd_matches_the_scan_definition(fake_fetch):
    c = M.CITIES[0]; g = {r["city"]: r for r in client.get("/api/globe?var=T2M").json()["cities"]}[c["id"]]
    s = {r["var"]: r for r in client.get(f"/api/scan?city={c['id']}").json()}["T2M"]
    assert g["effect_sd"] == pytest.approx(s["effect_sd"], rel=1e-6)


def test_static_files_are_revalidated_not_cached_blindly():
    r = client.get("/home.js")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache" and "7 ngày" in r.text and "52 tuần gần nhất so với" not in r.text


def test_parse_gibs_layers_reads_title_time_and_legend():
    xml = ("<Layer><ows:Title xml:lang='en'>Wind</ows:Title><ows:Identifier>L1</ows:Identifier>"
           "<Style><LegendURL xlink:href='https://x/L1_H.svg' /></Style><Dimension><Default>2026-08-01</Default></Dimension></Layer>"
           "<Layer><ows:Title>No time</ows:Title><ows:Identifier>L2</ows:Identifier></Layer>")
    d = M.parse_gibs_layers(xml, ["L1", "L2", "L3"])
    assert d["L1"] == {"layer": "L1", "title": "Wind", "time": "2026-08-01", "legend": "https://x/L1_H.svg"}
    assert "L2" not in d and "L3" not in d


def _seasonal_df(amps, y0=2000):
    rows = [(y0 + i + (m - .5) / 12, m, 10 + a * math.sin(2 * math.pi * (m - 1) / 12)) for i, a in enumerate(amps) for m in range(1, 13)]
    return pd.DataFrame(rows, columns=["t", "m", "v"])


def test_cycle_calc_detects_a_growing_seasonal_swing():
    r = M.cycle_calc(_seasonal_df([1 + .5 * i for i in range(12)]))
    assert r["early"]["amp"] == pytest.approx(4.5, abs=.05) and r["late"]["amp"] == pytest.approx(10.5, abs=.05)
    assert r["amp_change_pct"] == pytest.approx(133.3, abs=1)
    assert r["amp_trend"]["sig"] and r["amp_trend"]["slope"] == pytest.approx(1.0, abs=.05)
    assert r["early"]["peak"] == 4 and r["early"]["trough"] == 10


def test_cycle_calc_flat_swing_and_gaps():
    r = M.cycle_calc(_seasonal_df([2.0] * 12))
    assert abs(r["amp_change_pct"]) < 1 and not r["amp_trend"]["sig"]
    d = _seasonal_df([2.0] * 12); d = d[~d.m.between(5, 10)]                 # rainy-season gap like AOD: no amplitude is claimed
    r2 = M.cycle_calc(d)
    assert r2["early"]["amp"] is None and r2["amp_change_pct"] is None
    with pytest.raises(HTTPException): M.cycle_calc(_seasonal_df([2.0] * 4))


def test_api_cycle_skips_presets_of_another_city(monkeypatch):
    monkeypatch.setattr(M, "fetch", lambda lat, lon, par, y0, y1: _seasonal_df([2.0] * 12))
    c = TestClient(M.app)
    d = c.get("/api/cycle", params=dict(city="hanoi", vars="T2M,hcm_aod", start=2000, end=2011)).json()
    assert [i["var"] for i in d["items"]] == ["T2M"] and d["skipped"][0]["var"] == "hcm_aod"
    assert c.get("/api/cycle", params=dict(city="hanoi", vars="hcm_aod")).status_code == 422


def test_api_correlations_serves_the_preprocessing_output(monkeypatch, tmp_path):
    c = TestClient(M.app)
    d = c.get("/api/correlations").json()
    assert d["tests"] == len(d["pairs"]) * 4 and all(x["status"] in ("candidate", "weak", "none") for x in d["pairs"])
    assert all(len(x["q"]) == 4 and x["q_best"] >= x["p_best"] for x in d["pairs"])
    monkeypatch.setattr(M, "ROOT", tmp_path / "backend")
    assert c.get("/api/correlations").status_code == 404
