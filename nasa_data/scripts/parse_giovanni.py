"""Đọc CSV tải từ Giovanni (AOD, NO2) -> bảng sạch (date, value) + file metadata.
Chạy:  python -m scripts.parse_giovanni data/raw/hcm_aod_modis_monthly.csv data/raw/hcm_no2_omi_monthly.csv
Kết quả: <tên>_clean.csv và <tên>_meta.txt cạnh file gốc.
Giovanni CSV thường có vài dòng thông tin ở đầu rồi mới tới dòng tiêu đề bắt đầu bằng "time".
"""
import sys
from pathlib import Path
import pandas as pd


def parse(path):
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    idx = next(i for i, l in enumerate(lines) if l.lower().startswith("time"))
    meta = [l for l in lines[:idx] if l.strip()]
    df = pd.read_csv(path, skiprows=idx)
    df.columns = ["time", "value"] + list(df.columns[2:])
    df["date"] = pd.to_datetime(df["time"], errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df.loc[df["value"] < -1e20, "value"] = float("nan")   # giá trị thiếu kiểu fill-value cực lớn (NO2)
    # Fill value khai báo trong phần đầu file (AOD dùng -9999, không bắt được bởi ngưỡng -1e20 ở trên)
    for l in meta:
        if l.lower().startswith("fill value"):
            try:
                fv = float(l.rsplit(",", 1)[1])
            except ValueError:
                continue
            df.loc[(df["value"] - fv).abs() <= abs(fv) * 1e-6, "value"] = float("nan")
    return df[["date", "value"]].dropna(subset=["date"]), meta


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")   # console Windows (cp1252) không in được tiếng Việt
    for p in sys.argv[1:]:
        df, meta = parse(p)
        p = Path(p)
        df.to_csv(p.with_name(p.stem + "_clean.csv"), index=False)
        p.with_name(p.stem + "_meta.txt").write_text("\n".join(meta), encoding="utf-8")
        print(p.name, "->", len(df), "dòng,", int(df["value"].isna().sum()), "dòng thiếu,",
              df["date"].min().date(), "→", df["date"].max().date())
