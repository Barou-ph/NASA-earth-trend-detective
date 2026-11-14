"""Backend tests. Statistics are checked against independent implementations
(statsmodels OLS, brute-force Mann-Kendall / Theil-Sen), plus short / missing / flat data.
Run: pytest -q"""
import io, itertools, math
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
