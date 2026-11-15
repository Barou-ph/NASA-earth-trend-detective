"""Lấy AOD (Terra + Aqua, từ 2000) và NO2 TROPOMI (từ 2018) cho nhiều thành phố qua Google Earth Engine.
Cần (làm một lần):  pip install earthengine-api
                    tài khoản Earth Engine + một Google Cloud project (miễn phí cho phi thương mại)
                    earthengine authenticate
Chạy (PowerShell):  $env:GEE_PROJECT="ten-project-cua-ban"
                    python -m scripts.fetch_gee aod            # AOD Terra+Aqua, mọi thành phố
                    python -m scripts.fetch_gee no2            # TROPOMI NO2, mọi thành phố
                    python -m scripts.fetch_gee all --cities "Ho Chi Minh,Hanoi"
Kết quả: data/raw/gee_modis_aod_monthly.csv   (city, date, aod_terra, aod_aqua)
         data/raw/gee_tropomi_no2_monthly.csv (city, date, no2_tropomi [phân tử/cm2], n_images)
"""
import os, sys, time, argparse
import pandas as pd
from .config import RAW, CITIES, BBOX_HCM, CITY_HALF_DEG, GEE_START, GEE_END, START_YEAR, END_YEAR

try:
    import ee
except ImportError:
    sys.exit("Thiếu thư viện: pip install earthengine-api")

AOD_COLLECTIONS = {"aod_terra": "MODIS/061/MOD08_M3", "aod_aqua": "MODIS/061/MYD08_M3"}
# Ưu tiên biến Dark Target + Deep Blue; nếu bộ dữ liệu không có thì lùi về biến Land_Ocean
AOD_BANDS = ["AOD_550_Dark_Target_Deep_Blue_Combined_Mean_Mean", "Aerosol_Optical_Depth_Land_Ocean_Mean_Mean"]
S5P = "COPERNICUS/S5P/OFFL/L3_NO2"
S5P_BAND = "tropospheric_NO2_column_number_density"
MOL_M2_TO_MOLEC_CM2 = 6.02214076e23 / 1e4     # mol/m2 -> phân tử/cm2
_band_cache = {}


def init():
    project = os.environ.get("GEE_PROJECT")
    if not project:
        sys.exit("Thiếu GEE_PROJECT (tên Google Cloud project đã đăng ký Earth Engine)")
    try:
        ee.Initialize(project=project)
    except Exception:
        ee.Authenticate()
        ee.Initialize(project=project)


def region_of(city, lat, lon):
    if city == "Ho Chi Minh":                       # dùng đúng khung đã chọn cho Giovanni
        return ee.Geometry.Rectangle(list(BBOX_HCM))
    h = CITY_HALF_DEG
    return ee.Geometry.Rectangle([lon - h, lat - h, lon + h, lat + h])


def retry(fn, tries=4):
    for k in range(tries):
        try:
            return fn()
        except Exception as e:
            print("   lỗi, thử lại:", str(e)[:150])
            time.sleep(5 * (k + 1))
    raise RuntimeError("Thất bại sau nhiều lần thử")


# ---------------- AOD ----------------
def pick_band(coll_id):
    if coll_id not in _band_cache:
        names = retry(lambda: ee.ImageCollection(coll_id).first().bandNames().getInfo())
        band = next((b for b in AOD_BANDS if b in names), None)
        if band is None:
            sys.exit(f"{coll_id}: không thấy biến AOD nào trong {AOD_BANDS}. Biến có: {names[:30]}")
        print(f"  {coll_id}: dùng biến {band}")
        _band_cache[coll_id] = band
    return _band_cache[coll_id]


def fetch_aod(region, coll_id):
    band = pick_band(coll_id)
    col = ee.ImageCollection(coll_id).filterDate(GEE_START, GEE_END).select(band)

    def per_image(img):
        v = img.reduceRegion(ee.Reducer.mean(), region, 111320, maxPixels=1e9).get(band)
        return ee.Feature(None, {"date": img.date().format("YYYY-MM-01"), "raw": v})

    feats = retry(lambda: ee.FeatureCollection(col.map(per_image)).getInfo()["features"])
    s = pd.Series({f["properties"]["date"]: f["properties"].get("raw") for f in feats}, dtype=float)
    if s.median() > 5:        # số nguyên chưa nhân hệ số 0.001
        s = s * 0.001
    return s


def run_aod(cities):
    rows = []
    for city, (lat, lon) in cities.items():
        region = region_of(city, lat, lon)
        parts = {}
        for col_name, coll_id in AOD_COLLECTIONS.items():
            parts[col_name] = fetch_aod(region, coll_id)
        df = pd.DataFrame(parts)
        df.index.name = "date"
        df.insert(0, "city", city)
        rows.append(df.reset_index())
        print("ok AOD", city, len(df), "tháng")
    out = RAW / "gee_modis_aod_monthly.csv"
    pd.concat(rows).to_csv(out, index=False)
    print("Đã lưu", out)


# ---------------- TROPOMI NO2 ----------------
def tropomi_year(region, year):
    col = (ee.ImageCollection(S5P).select(S5P_BAND)
           .map(lambda im: im.updateMask(im.gt(-0.001))))     # bỏ nhiễu âm quá lớn (khuyến nghị của NASA/ESA)

    def per_month(m):
        start = ee.Date.fromYMD(year, m, 1)
        sub = col.filterDate(start, start.advance(1, "month"))
        n = sub.size()
        val = ee.Algorithms.If(
            n.gt(0),
            sub.mean().reduceRegion(ee.Reducer.mean(), region, 5000, maxPixels=1e9, bestEffort=True).get(S5P_BAND),
            None)
        return ee.Feature(None, {"date": start.format("YYYY-MM-01"), "raw": val, "n_images": n})

    fc = ee.FeatureCollection(ee.List.sequence(1, 12).map(per_month))
    return retry(lambda: fc.getInfo()["features"])


def run_no2(cities):
    rows = []
    for city, (lat, lon) in cities.items():
        region = region_of(city, lat, lon)
        for year in range(max(START_YEAR, 2018), END_YEAR + 1):
            for f in tropomi_year(region, year):
                p = f["properties"]
                raw = p.get("raw")
                rows.append({"city": city, "date": p["date"],
                             "no2_tropomi": None if raw is None else raw * MOL_M2_TO_MOLEC_CM2,
                             "n_images": p.get("n_images", 0)})
        print("ok NO2", city)
    out = RAW / "gee_tropomi_no2_monthly.csv"
    pd.DataFrame(rows).to_csv(out, index=False)
    print("Đã lưu", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["aod", "no2", "all"])
    ap.add_argument("--cities", help='Ví dụ "Ho Chi Minh,Hanoi" (mặc định: tất cả trong config.py)')
    a = ap.parse_args()
    cities = CITIES if not a.cities else {c.strip(): CITIES[c.strip()] for c in a.cities.split(",")}
    init()
    if a.what in ("aod", "all"):
        run_aod(cities)
    if a.what in ("no2", "all"):
        run_no2(cities)


if __name__ == "__main__":
    main()
