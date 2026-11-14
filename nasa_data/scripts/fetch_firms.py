"""Điểm cháy NASA FIRMS qua API, cắt từng cửa sổ 5 ngày, có lưu tiến độ (chạy lại sẽ bỏ qua năm đã xong).
Cần MAP_KEY:  export FIRMS_MAP_KEY=xxxx   (Windows: set FIRMS_MAP_KEY=xxxx)
Chạy:  python -m scripts.fetch_firms            -> tải + đếm theo tháng
       python -m scripts.fetch_firms --count-only
Kết quả: data/raw/firms/<SOURCE>_<năm>.csv  và  data/raw/firms_monthly_counts.csv
Lưu ý: API có giới hạn số lượt gọi (khoảng 5000 lượt / 10 phút), script đã nghỉ giữa các lượt.
"""
import os, sys, io, time, datetime as dt
import requests, pandas as pd
from .config import RAW, BBOX_FIRE, START_YEAR, END_YEAR

BASE = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
SOURCES = {  # nguồn lưu trữ chuẩn (SP) + ngày bắt đầu có dữ liệu
    "MODIS_SP": dt.date(2000, 11, 1),
    "VIIRS_SNPP_SP": dt.date(2012, 1, 20),
}
DAYS = 5
OUT = RAW / "firms"
OUT.mkdir(exist_ok=True)


def get_chunk(key, source, day):
    w, s, e, n = BBOX_FIRE
    url = f"{BASE}/{key}/{source}/{w},{s},{e},{n}/{DAYS}/{day.isoformat()}"
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=120)
            text = r.text.strip()
            if r.ok and text.startswith("latitude"):
                return text
            print("  lỗi/trả lời lạ:", text[:120])
        except requests.RequestException as ex:
            print("  mạng lỗi:", ex)
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Thất bại: {source} {day}")


def download(key):
    for source, first in SOURCES.items():
        for year in range(START_YEAR, END_YEAR + 1):
            f = OUT / f"{source}_{year}.csv"
            if f.exists():
                continue
            start = max(dt.date(year, 1, 1), first)
            end = dt.date(year, 12, 31)
            if start > end:
                continue
            frames, d = [], start
            while d <= end:
                text = get_chunk(key, source, d)
                frames.append(pd.read_csv(io.StringIO(text)))
                d += dt.timedelta(days=DAYS)
                time.sleep(0.3)
            df = pd.concat(frames).drop_duplicates()
            df = df[(df["acq_date"] >= str(start)) & (df["acq_date"] <= str(end))]
            df.to_csv(f, index=False)
            print("ok", source, year, len(df), "điểm cháy")


def count_monthly():
    parts = []
    for f in sorted(OUT.glob("*.csv")):
        source = f.stem.rsplit("_", 1)[0]
        df = pd.read_csv(f)
        if df.empty:
            continue
        df["month"] = pd.to_datetime(df["acq_date"]).dt.to_period("M").dt.to_timestamp()
        g = df.groupby("month").agg(fire_count=("latitude", "size"),
                                    frp_sum=("frp", "sum")).reset_index()
        g["source"] = source
        parts.append(g)
    out = pd.concat(parts).groupby(["source", "month"], as_index=False).sum()
    out.to_csv(RAW / "firms_monthly_counts.csv", index=False)
    print("Đã lưu firms_monthly_counts.csv", out.shape)


if __name__ == "__main__":
    if "--count-only" not in sys.argv:
        key = os.environ.get("FIRMS_MAP_KEY")
        if not key:
            sys.exit("Thiếu FIRMS_MAP_KEY (xin tại firms.modaps.eosdis.nasa.gov/api/map_key/)")
        download(key)
    count_monthly()
