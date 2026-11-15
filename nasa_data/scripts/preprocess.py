"""Ghép AOD, NO2, thời tiết POWER, điểm cháy FIRMS thành MỘT bảng theo tháng cho TP.HCM.
Chạy:  python -m scripts.preprocess
Đầu vào (trong data/raw/):  AOD_550_clean.csv, NO2_clean_monthly.csv,
                            power_monthly_cities.csv, firms_monthly_counts.csv
Đầu ra: data/processed/hcm_monthly.csv
Nguồn nào chưa có file thì bị bỏ qua (có in cảnh báo), không làm script dừng.
"""
import pandas as pd
from .config import RAW, PROCESSED

AOD_FILE = "AOD_550_clean.csv"
NO2_FILE = "NO2_clean_monthly.csv"
CITY = "Ho Chi Minh"


def month_start(s):
    return pd.to_datetime(s).dt.to_period("M").dt.to_timestamp()


def load_giovanni(name, col, extra=None):
    p = RAW / name
    if not p.exists():
        print("Bỏ qua (không thấy file):", name)
        return []
    df = pd.read_csv(p, parse_dates=["date"])
    df["date"] = month_start(df["date"])
    out = [df.groupby("date")["value"].mean().rename(col)]
    if extra and extra in df:
        out.append(df.groupby("date")[extra].sum().rename("no2_valid_days"))
    return out


def load_city_csv(name, cols):
    """Đọc file nhiều thành phố (cột city, date, ...) và lấy phần TP.HCM."""
    p = RAW / name
    if not p.exists():
        print("Bỏ qua (không thấy file):", name)
        return []
    df = pd.read_csv(p, parse_dates=["date"])
    df = df[df["city"] == CITY].copy()
    df["date"] = month_start(df["date"])
    df = df.groupby("date")[[c for c in cols if c in df]].mean()
    return [df[c] for c in df.columns]


def load_power():
    p = RAW / "power_monthly_cities.csv"
    if not p.exists():
        print("Bỏ qua (không thấy file): power_monthly_cities.csv")
        return []
    df = pd.read_csv(p, parse_dates=["date"])
    df = df[df["city"] == CITY].copy()
    df["date"] = month_start(df["date"])
    df = df.set_index("date").rename(columns={
        "T2M": "temp_c", "PRECTOTCORR": "rain_mm_day", "RH2M": "rh_pct", "WS2M": "wind_ms"})
    return [df[c] for c in ["temp_c", "rain_mm_day", "rh_pct", "wind_ms"] if c in df]


def load_firms():
    p = RAW / "firms_monthly_counts.csv"
    if not p.exists():
        print("Bỏ qua (không thấy file): firms_monthly_counts.csv")
        return []
    df = pd.read_csv(p, parse_dates=["month"])
    out = []
    for source, tag in [("MODIS_SP", "modis"), ("VIIRS_SNPP_SP", "viirs")]:
        d = df[df["source"] == source].set_index("month")
        if d.empty:
            continue
        # Tháng không có dòng nào = 0 điểm cháy (chỉ điền trong khoảng đã tải)
        full = pd.date_range(d.index.min(), d.index.max(), freq="MS")
        d = d.reindex(full).fillna(0)
        out += [d["fire_count"].rename(f"fire_{tag}"), d["frp_sum"].rename(f"frp_{tag}")]
    return out


def main():
    parts = []
    parts += load_giovanni(AOD_FILE, "aod")
    parts += load_giovanni(NO2_FILE, "no2")
    no2_days = pd.read_csv(RAW / NO2_FILE, parse_dates=["date"]) if (RAW / NO2_FILE).exists() else None
    if no2_days is not None and "n_valid_days" in no2_days:
        no2_days["date"] = month_start(no2_days["date"])
        parts.append(no2_days.set_index("date")["n_valid_days"].rename("no2_valid_days"))
    parts += load_power()
    parts += load_firms()
    parts += load_city_csv("gee_modis_aod_monthly.csv", ["aod_terra", "aod_aqua"])
    parts += load_city_csv("gee_tropomi_no2_monthly.csv", ["no2_tropomi"])
    parts += load_city_csv("openaq_pm25_monthly.csv", ["pm25"])
    if not parts:
        raise SystemExit("Không có dữ liệu nào để ghép. Kiểm tra data/raw/")

    df = pd.concat(parts, axis=1, sort=True)
    df = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    df.index.name = "date"

    # AOD kết hợp Terra + Aqua: trung bình các nguồn có mặt trong tháng đó (Aqua chỉ có từ 2002-07)
    src = [c for c in ["aod_terra", "aod_aqua"] if c in df]
    if src:
        df["aod_combined"] = df[src].mean(axis=1, skipna=True)
        df["aod_n_sources"] = df[src].notna().sum(axis=1)

    # Đặc trưng thời gian
    df["year"], df["month"] = df.index.year, df.index.month
    df["season"] = df["month"].map(lambda m: "Mùa mưa" if 5 <= m <= 10 else "Mùa khô")

    # Dị thường = giá trị trừ trung bình cùng tháng (bỏ tính chu kỳ mùa để thấy xu hướng)
    for c in ["aod", "aod_combined", "no2"]:
        if c in df:
            df[f"{c}_anom"] = df[c] - df.groupby("month")[c].transform("mean")
            df[f"{c}_roll12"] = df[c].rolling(12, min_periods=9).mean().where(df[c].notna())

    out = PROCESSED / "hcm_monthly.csv"
    df.to_csv(out)
    print("Đã lưu", out, df.shape)
    print("\nBáo cáo chất lượng (số tháng có dữ liệu / khoảng thời gian):")
    for c in df.columns:
        if c in ("year", "month", "season", "aod_n_sources") or c.endswith(("_anom", "_roll12")):
            continue
        s = df[c].dropna()
        if len(s):
            print(f"  {c:16s} {len(s):4d}/{len(df)} tháng   {s.index.min():%Y-%m} → {s.index.max():%Y-%m}")


if __name__ == "__main__":
    main()
