import json, time
import requests, pandas as pd
from .config import RAW, CITIES, POWER_PARAMS, START_YEAR, END_YEAR

URL = "https://power.larc.nasa.gov/api/temporal/monthly/point"
CACHE = RAW / "power_cache"
CACHE.mkdir(exist_ok=True)


def fetch(lat, lon):
    r = requests.get(URL, params={
        "parameters": ",".join(POWER_PARAMS), "community": "AG",
        "latitude": lat, "longitude": lon,
        "start": START_YEAR, "end": END_YEAR, "format": "JSON",
    }, timeout=180)
    r.raise_for_status()
    return r.json()


def to_rows(city, data):
    rows = []
    for param, series in data["properties"]["parameter"].items():
        for key, val in series.items():          # key dạng "200401"
            year, month = int(key[:4]), int(key[4:])
            if month == 13:                      # 13 = trung bình cả năm, bỏ
                continue
            rows.append({"city": city, "date": f"{year}-{month:02d}-01",
                         "param": param, "value": None if val == -999 else val})
    return rows


def main():
    all_rows = []
    for city, (lat, lon) in CITIES.items():
        f = CACHE / f"{city.replace(' ', '_')}.json"
        try:
            if f.exists():
                data = json.loads(f.read_text())
            else:
                data = fetch(lat, lon)
                f.write_text(json.dumps(data))
                time.sleep(1)                    # nhẹ tay với API
            all_rows += to_rows(city, data)
            print("ok  ", city)
        except Exception as e:
            print("FAIL", city, e)
    df = pd.DataFrame(all_rows).pivot_table(
        index=["city", "date"], columns="param", values="value").reset_index()
    out = RAW / "power_monthly_cities.csv"
    df.to_csv(out, index=False)
    print("Đã lưu", out, df.shape)


if __name__ == "__main__":
    main()
