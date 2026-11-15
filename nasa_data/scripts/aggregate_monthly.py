"""Gộp chuỗi theo NGÀY (đã qua parse_giovanni) thành trung bình THÁNG, kèm số ngày hợp lệ.
Chạy:  python -m scripts.aggregate_monthly data/raw/NO2_clean.csv [số_ngày_tối_thiểu]
Kết quả: data/raw/NO2_clean_monthly.csv  (cột: date, value, n_valid_days, n_days)
Tháng có ít ngày hợp lệ hơn ngưỡng (mặc định 5) -> value để trống.
"""
import sys
from pathlib import Path
import pandas as pd

path = Path(sys.argv[1])
min_days = int(sys.argv[2]) if len(sys.argv) > 2 else 5

df = pd.read_csv(path, parse_dates=["date"])
df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
g = df.groupby("month")["value"].agg(value="mean", n_valid_days="count", n_days="size").reset_index()
g.loc[g["n_valid_days"] < min_days, "value"] = float("nan")
g = g.rename(columns={"month": "date"})

out = path.with_name(path.stem + "_monthly.csv")
g.to_csv(out, index=False)
print(out.name, "->", len(g), "tháng,", int(g["value"].isna().sum()), f"tháng bị bỏ (< {min_days} ngày hợp lệ),",
      g["date"].min().date(), "→", g["date"].max().date())
