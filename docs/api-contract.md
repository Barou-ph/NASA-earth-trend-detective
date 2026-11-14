# API contract (frozen)

**Rule:** a field name that is listed here never changes without telling the other side.
New fields may be **added**, never renamed. Arrays are shortened with `…` below; the full
files are in `frontend/mock/*.json` (regenerate with `python scripts/make_mocks.py`).

Place selection: every endpoint takes **`city`** (an `id` from `/api/cities`) **or** `lat`+`lon`.
Optional everywhere: `start` (default 2000), `end` (default 2024).
Errors: `{"detail": "<message>"}` with HTTP 404 (unknown id / missing preset file), 413 (upload > 5 MB),
422 (bad input or too little data), 502 (NASA POWER unreachable).

| Endpoint | Returns |
|---|---|
| `GET /api/variables` | `[{id, topic, unit, name{vi,en}, desc{vi,en}}]` |
| `GET /api/cities` | `[{id, name{vi,en}, lat, lon}]` (+ `region`: `"vn"` or `"world"`) |
| `GET /api/analyze?city&var&deseason&annual` | `t[], v[], fit[2], slope, ci[2], p_t, p_mk, tau, sen, r1, n_eff, total, span, sig, verdict{vi,en}` (+ `n`, `source`, `quality{…}`). Also accepts `lat`+`lon` or `preset=<id>` |
| `GET /api/lag?city&a&b&detrend` | `lags[0..3], r[], p[], best_lag, caveat{vi,en}` (+ `a, b, n[], sig, detrended`) |
| `GET /api/anomaly?city&var` | `months[{t, v, p05, p95, flag}]` (+ `var, unit, n_flagged`) |
| `GET /api/ranking?var&region` | `[{city, lat, lon, slope, p, sig}]` (+ `name{vi,en}, region, p_mk, q, sig_fdr`), sorted by slope, descending. `region` = `all` (default), `vn` or `world` |
| `GET /api/scan?city` | `[{var, kind, name{vi,en}, unit, slope, total, effect_sd, tau, p, p_mk, q, sig, sig_fdr, n, span}]`: every variable at one place, strongest evidence first |
| `GET /api/summary?city&var&b` | `headline{vi,en}, bullets[{kind, tone, vi, en}], text{vi,en}, facts{…}, period[2]` (+ `var, b, city, unit, name, place`). `b` and `rank=false` are optional |
| `POST /api/upload` (multipart `file`) | same structure as `/api/analyze` (incl. `quality`). Optional `min_days` |
| `GET /api/presets` | `[{id, kind, city, var, title{vi,en}, available}]`, includes `hcm_aod`, `hcm_no2`, `hcm_fire` (+ `name, desc, unit, topic` for CSV presets) |
| `GET /api/grid?lat&lon&var` | `[{lat, lon, slope, p, sig}]`, 3×3 cells (existing) |

Meaning of the fields
- `t` decimal year (month centre: 2000.0417 = Jan 2000). `v` value (de-seasoned anomaly if `deseason=true`).
- `fit` = `[trend at t[0], trend at t[last]]`. `slope`, `sen`, `ci` in unit/year. `total` = slope × span.
- `p_t` t-test p-value adjusted for lag-1 autocorrelation (`r1`, `n_eff`); `p_mk`, `tau` Mann-Kendall.
  `sig` = `p_t < 0.05 && p_mk < 0.05`.
- `lag`: `r[i]`, `p[i]`, `n[i]` belong to `lags[i]`; a positive lag means **b follows a** by that many months.
  Both series are de-seasoned first. `best_lag` = lag with the largest |r|. `caveat` must always be shown.
- `anomaly.flag`: `"high"` (above the 95th percentile of the same calendar month), `"low"` (below the 5th), else `null`.
- `presets[].kind`: `"power"` (NASA POWER) or `"csv"` (Giovanni file in `backend/presets/`).
  `available:false` = file not dropped yet. CSV presets can also be used as `var`, `a`, `b` (e.g. `a=hcm_aod&b=hcm_no2`, no city needed).
- `summary`: rule-based text built from the same numbers as the charts (no AI model). `bullets[].kind` is one of
  `trend, change, extreme, season, anomaly, lag, rank, quality` (a bullet is left out when there is too little data, no `b`, or no `city`);
  `tone` is `up | down | flat | warn | info`. `bullets[0]` is always the trend verdict. `text` = headline + bullets as one paragraph.
  `facts` holds the raw numbers: `slope, ci, p_t, p_mk, sig, total, n, block_diff, max_year, min_year, peak_month, low_month,
  n_high, n_low, n_high_recent, n_low_recent, best_lag, lag_r, lag_sig, rank, rank_total, missing_months, r1, n_eff`.
- `quality` (inside `analyze` and `upload`): a report on the raw series; nothing is removed or imputed by it.
  `span[2], n_expected, n_valid, n_missing, coverage (0-1), longest_gap, missing_by_month{"1".."12"}, n_outliers,
  outliers[{t, v, z}]` (robust z against the same calendar month, `|z| > 3.5`), `parse` (CSV only: `rows_numeric, fill_dropped, bad_dates,
  sub_monthly, min_days, months_dropped`, else `null`), `notes[{level: ok|info|warn, vi, en}]`.
- `ranking` / `scan`: many places or variables are tested at once, so `q` is the Benjamini-Hochberg adjusted value of the more
  conservative of `p` and `p_mk`; `sig_fdr = q < 0.05`. Prefer `sig_fdr` over `sig` when comparing many cities or variables.
  `scan.effect_sd` = `total` divided by the standard deviation of the de-seasoned series (unit-free, comparable across variables).
  `scan` includes CSV presets only when `city` matches the preset's city. `kind` is `power` or `preset`.
- `lag` removes each series' own linear trend by default (`detrend=true`), so two variables that merely drift the same way are not reported as related.
- Upload: optional query `deseason`, `annual`, `name`, `unit`. CSV: lines starting with `#` ignored, first column = time,
  last column = value, fill values (≤ −990) dropped, sub-monthly data averaged per month.

## Examples

`GET /api/analyze?city=hcm&var=T2M` (real NASA POWER data, 2000–2024)
```json
{"n":300,"slope":0.03237604,"ci":[0.008287421,0.05646466],"p_t":0.009121503,"p_mk":2.066788e-09,
 "tau":0.2320447,"sen":0.03228777,"r1":0.5975005,"n_eff":75.58673,"total":0.806703,"span":24.91667,"sig":true,
 "t":[2000.042,2000.125,2000.208,"…"],"v":[-0.9396,-1.504,-1.2308,"…"],"fit":[-0.4033515,0.4033515],
 "verdict":{"vi":"Nhiệt độ không khí 2 m có xu hướng tăng đáng kể: 0.0324 °C/năm (0.807 °C trong 25 năm). Cả t-test (đã hiệu chỉnh tự tương quan) lẫn Mann-Kendall đều có p<0,05.",
            "en":"2-m air temperature shows a significant increasing trend: 0.0324 °C/year (0.807 °C over 25 years). Both the t-test (autocorrelation-adjusted) and Mann-Kendall give p<0.05."},
 "source":"T2M"}
```

`GET /api/lag?city=hcm&a=T2M&b=RH2M`
```json
{"a":"T2M","b":"RH2M","lags":[0,1,2,3],"r":[-0.7909878,-0.5379608,-0.3489672,-0.3004098],
 "p":[2.519249e-26,3.870921e-10,0.0001107329,0.0009700604],"n":[300,299,298,297],"best_lag":0,"sig":true,
 "caveat":{"vi":"Tương quan có độ trễ chỉ cho thấy hai chuỗi biến động cùng nhau, không chứng minh nhân quả: có thể do yếu tố thứ ba hoặc do trùng hợp.",
           "en":"A lagged correlation only shows that two series move together; it does not prove causation. A third factor or coincidence may explain it."}}
```

`GET /api/anomaly?city=hcm&var=T2M`
```json
{"var":"T2M","unit":"°C","n_flagged":48,
 "months":[{"t":2000.042,"v":25.12,"p05":24.406,"p95":27.91,"flag":null},
           {"t":2000.125,"v":26.38,"p05":26.154,"p95":29.33,"flag":null},"…"]}
```

`GET /api/ranking?var=T2M`
```json
[{"city":"hcm","name":{"vi":"TP. Hồ Chí Minh","en":"Ho Chi Minh City"},"lat":10.78,"lon":106.7,"slope":0.03242756,"p":0.1208721,"sig":false},
 {"city":"camau","name":{"vi":"Cà Mau","en":"Ca Mau"},"lat":9.18,"lon":105.15,"slope":0.02983077,"p":0.0007956403,"sig":true},"…"]
```
(Ranking uses annual means of de-seasoned data, so `p` is not the same as the monthly `/api/analyze` value.)

`GET /api/scan?city=hcm` (first rows, real data)
```json
[{"var":"hcm_no2","kind":"preset","name":{"vi":"NO₂ tầng đối lưu","en":"Tropospheric NO₂"},"unit":"10¹⁵ molec/cm²","slope":0.0669,"total":1.47,
  "effect_sd":2.39,"tau":0.45,"p":3.1e-24,"p_mk":2.7e-33,"q":5e-23,"sig":true,"sig_fdr":true,"n":258,"span":22},
 {"var":"T2M","kind":"power","slope":0.0324,"effect_sd":1.03,"q":0.049,"sig_fdr":true,"…":"…"},"…"]
```

`quality` (from `GET /api/analyze?preset=hcm_aod`, abbreviated)
```json
{"span":[2004,2026],"n_expected":274,"n_valid":236,"n_missing":38,"coverage":0.861,"longest_gap":3,
 "missing_by_month":{"1":0,"5":5,"8":10,"9":14,"…":0},"n_outliers":6,"outliers":[{"t":2015.708,"v":1.273,"z":5.65}],"parse":null,
 "notes":[{"level":"warn","vi":"Thiếu 38/274 tháng (14%), …","en":"38 of 274 months are missing (14%), …"}]}
```

`GET /api/presets`
```json
[{"id":"hcm_t2m","kind":"power","city":"hcm","var":"T2M","title":{"vi":"TP.HCM: nhiệt độ không khí","en":"HCMC: air temperature"},"available":true},
 {"id":"hcm_aod","kind":"csv","city":"hcm","var":"hcm_aod","title":{"vi":"TP.HCM: bụi mịn AOD","en":"HCMC: aerosol optical depth"},
  "name":{"vi":"Bụi mịn trong khí quyển (AOD)","en":"Aerosol optical depth (AOD)"},"unit":"","topic":"air","available":false},
 {"id":"hcm_no2","kind":"csv","city":"hcm","var":"hcm_no2","title":{"vi":"TP.HCM: khí NO₂","en":"HCMC: nitrogen dioxide"},"available":false}]
```

`GET /api/summary?city=hcm&var=T2M&b=RH2M`
```json
{"var":"T2M","b":"RH2M","city":"hcm","unit":"°C","place":{"vi":"TP. Hồ Chí Minh","en":"Ho Chi Minh City"},"period":[2000,2024],
 "headline":{"vi":"Nhiệt độ không khí 2 m tại TP. Hồ Chí Minh đang tăng 0.0324 °C/năm.","en":"2-m air temperature in Ho Chi Minh City is rising by 0.0324 °C per year."},
 "bullets":[{"kind":"trend","tone":"up","vi":"Nhiệt độ không khí 2 m có xu hướng tăng đáng kể: …","en":"2-m air temperature shows a significant increasing trend: …"},
            {"kind":"change","tone":"up","vi":"Trung bình 10 năm gần nhất (2015–2024) cao hơn 10 năm đầu (2000–2009) 0.603 °C: 27.8 so với 27.2 °C.","en":"The latest 10 years (2015–2024) average 0.603 °C higher than the first 10 (2000–2009): 27.8 vs 27.2 °C."},"…"],
 "text":{"vi":"…","en":"…"},
 "facts":{"slope":0.03237604,"sig":true,"block_diff":0.6028333,"max_year":2015,"min_year":2000,"peak_month":4,"low_month":12,
          "n_high":24,"n_low":24,"n_high_recent":9,"n_low_recent":3,"best_lag":0,"lag_r":-0.7909878,"rank":1,"rank_total":12,"…":"…"}}
```

`POST /api/upload` — same JSON shape as `/api/analyze` (`source` is `"upload"`).

## Workflow
- Drop Giovanni CSVs into `backend/presets/` (`hcm_aod.csv`, `hcm_no2.csv`) and raw crawls into `data/raw/`; no code change needed.
- Frontend `USE_MOCK` (top of `frontend/app.js`, or open the page with `?mock=1`) serves `frontend/mock/*.json` instead of the API.
