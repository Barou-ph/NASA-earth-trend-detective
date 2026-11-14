"""PM2.5 mặt đất theo THÁNG từ OpenAQ (API v3) quanh các thành phố trong OPENAQ_CITIES.
Cần API key miễn phí: đăng ký tại explore.openaq.org -> tạo key trong phần tài khoản.
Chạy (PowerShell):  $env:OPENAQ_API_KEY="khoa_cua_ban"
                    python -m scripts.fetch_openaq
                    python -m scripts.fetch_openaq --include-lowcost     # cho cả cảm biến giá rẻ
Kết quả: data/raw/openaq_pm25_monthly_raw.csv  (từng cảm biến, từng tháng)
         data/raw/openaq_pm25_monthly.csv      (city, date, pm25, n_sensors)
Script cũng in danh sách trạm tìm thấy và khoảng thời gian có dữ liệu: nếu TP.HCM không có trạm nào thì
ghi vào phần "giới hạn" của báo cáo, đừng cố.
"""
import os, sys, time, argparse, datetime as dt
import requests, pandas as pd
from .config import RAW, CITIES, OPENAQ_CITIES, OPENAQ_RADIUS_M, OPENAQ_START

API = "https://api.openaq.org/v3"
SESSION = requests.Session()
KEY = None


def get(path, params=None):
    for attempt in range(6):
        r = SESSION.get(API + path, params=params, headers={"X-API-Key": KEY}, timeout=60)
        if r.status_code == 401:
            sys.exit("OpenAQ báo 401: API key thiếu hoặc sai.")
        if r.status_code == 429:
            wait = 60
            print("  bị giới hạn tốc độ (429), chờ", wait, "giây")
            time.sleep(wait)
            continue
        if r.ok:
            time.sleep(1.1)           # nhẹ tay với giới hạn lượt gọi
            return r.json()
        print("  lỗi", r.status_code, r.text[:150])
        time.sleep(5)
    raise RuntimeError("Gọi API thất bại: " + path)


def is_pm25(sensor):
    name = (sensor.get("parameter") or {}).get("name", "")
    return name.lower().replace(".", "").replace("_", "") == "pm25"


def find_sensors(city):
    lat, lon = CITIES[city]
    data = get("/locations", {"coordinates": f"{lat},{lon}", "radius": OPENAQ_RADIUS_M, "limit": 1000})
    found = []
    for loc in data.get("results", []):
        sensors = loc.get("sensors")
        if sensors is None:
            sensors = get(f"/locations/{loc['id']}/sensors").get("results", [])
        for s in sensors:
            if is_pm25(s):
                found.append({"city": city, "location_id": loc["id"], "location_name": loc.get("name"),
                              "is_monitor": loc.get("isMonitor"), "sensor_id": s["id"],
                              "first": (loc.get("datetimeFirst") or {}).get("local", "")[:10],
                              "last": (loc.get("datetimeLast") or {}).get("local", "")[:10]})
    return found


def monthly(sensor_id):
    rows, page, limit = [], 1, 1000
    date_to = dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    while True:
        data = get(f"/sensors/{sensor_id}/days/monthly",
                   {"date_from": f"{OPENAQ_START}T00:00:00Z", "date_to": date_to, "limit": limit, "page": page})
        res = data.get("results", [])
        for r in res:
            period = (r.get("period") or {}).get("datetimeFrom") or {}
            local = period.get("local") or period.get("utc")      # dùng giờ ĐỊA PHƯƠNG để không lệch tháng
            if not local or r.get("value") is None:
                continue
            cov = (r.get("coverage") or {}).get("percentComplete")
            rows.append({"date": local[:7] + "-01", "value": r["value"], "coverage_pct": cov})
        if len(res) < limit:
            return rows
        page += 1


def main():
    global KEY
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-lowcost", action="store_true", help="giữ cả cảm biến giá rẻ (mặc định chỉ trạm chuẩn)")
    ap.add_argument("--min-coverage", type=float, default=50, help="bỏ tháng có độ phủ dữ liệu dưới ngưỡng này (%%)")
    a = ap.parse_args()
    KEY = os.environ.get("OPENAQ_API_KEY")
    if not KEY:
        sys.exit("Thiếu OPENAQ_API_KEY")

    all_rows, summary = [], []
    for city in OPENAQ_CITIES:
        sensors = find_sensors(city)
        print(f"\n{city}: tìm thấy {len(sensors)} cảm biến PM2.5 trong {OPENAQ_RADIUS_M // 1000} km")
        for s in sensors:
            print(f"  loc {s['location_id']:>8} | {str(s['location_name'])[:35]:35s} | trạm chuẩn={s['is_monitor']} | {s['first']} → {s['last']}")
        for s in sensors:
            for r in monthly(s["sensor_id"]):
                all_rows.append({**s, **r})
    if not all_rows:
        sys.exit("\nKhông có dữ liệu PM2.5 nào. Hãy ghi vào phần giới hạn của báo cáo.")

    raw = pd.DataFrame(all_rows)
    raw.to_csv(RAW / "openaq_pm25_monthly_raw.csv", index=False)

    d = raw.copy()
    if not a.include_lowcost:
        ref = d[d["is_monitor"] == True]
        if ref.empty:
            print("\nCảnh báo: không có trạm chuẩn nào, dùng tất cả cảm biến (độ tin cậy thấp hơn).")
        else:
            d = ref
    d = d[(d["coverage_pct"].isna()) | (d["coverage_pct"] >= a.min_coverage)]
    agg = (d.groupby(["city", "date"]).agg(pm25=("value", "mean"), n_sensors=("sensor_id", "nunique"))
           .reset_index())
    agg.to_csv(RAW / "openaq_pm25_monthly.csv", index=False)
    print("\nĐã lưu openaq_pm25_monthly.csv:")
    print(agg.groupby("city")["date"].agg(["min", "max", "count"]))


if __name__ == "__main__":
    main()
