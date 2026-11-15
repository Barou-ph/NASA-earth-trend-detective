"""Vẽ biểu đồ từ data/processed/hcm_monthly.csv (và power_monthly_cities.csv cho so sánh thành phố).
Chạy:  python -m scripts.visualize
Kết quả: figures/*.png
"""
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .config import RAW, PROCESSED, FIGS

plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 160, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})

LABELS = {
    "aod": "AOD 550 nm (bụi mịn trong khí quyển)",
    "no2": "NO₂ tầng đối lưu",
    "fire_modis": "Số điểm cháy / tháng (MODIS)",
    "rain_mm_day": "Lượng mưa (mm/ngày)",
    "temp_c": "Nhiệt độ (°C)",
    "rh_pct": "Độ ẩm (%)",
    "wind_ms": "Gió (m/s)",
    "aod_combined": "AOD 550 nm (Terra+Aqua)",
    "no2_tropomi": "NO₂ TROPOMI",
    "pm25": "PM2.5 mặt đất (µg/m³)",
}
SHORT = {"aod": "AOD", "no2": "NO₂", "fire_modis": "Cháy", "rain_mm_day": "Mưa",
         "temp_c": "Nhiệt độ", "rh_pct": "Độ ẩm", "wind_ms": "Gió",
         "aod_combined": "AOD T+A", "no2_tropomi": "NO₂ TROPOMI", "pm25": "PM2.5"}


def load():
    df = pd.read_csv(PROCESSED / "hcm_monthly.csv", index_col="date", parse_dates=True)
    # NO2 thường cỡ 1e15 phân tử/cm2: chia cho dễ đọc
    if "no2" in df and df["no2"].abs().median() > 1e10:
        for c in ["no2", "no2_anom", "no2_roll12", "no2_tropomi"]:
            if c in df:
                df[c] = df[c] / 1e15
        LABELS["no2"] = "NO₂ OMI tầng đối lưu (×10¹⁵ phân tử/cm²)"
        LABELS["no2_tropomi"] = "NO₂ TROPOMI (×10¹⁵ phân tử/cm²)"
    return df


def main_aod(df):
    """Dùng AOD kết hợp Terra+Aqua (dài từ 2000) nếu có, không thì dùng file Giovanni."""
    return "aod_combined" if "aod_combined" in df else "aod"


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGS / name)
    plt.close(fig)
    print("Đã lưu figures/" + name)


def fig_timeseries(df):
    cols = [c for c in [main_aod(df), "no2", "fire_modis", "rain_mm_day"] if c in df]
    fig, axes = plt.subplots(len(cols), 1, figsize=(11, 2.6 * len(cols)), sharex=True)
    axes = np.atleast_1d(axes)
    for ax, c in zip(axes, cols):
        ax.plot(df.index, df[c], color="#9aa5b1", lw=0.9, label="Theo tháng")
        roll = df[c].rolling(12, min_periods=9).mean()
        roll[df[c].isna()] = np.nan              # không kéo đường trượt qua chỗ thiếu dữ liệu
        ax.plot(df.index, roll, color="#c0392b", lw=2, label="Trung bình trượt 12 tháng")
        ax.set_ylabel(LABELS[c], fontsize=8)
    axes[0].legend(loc="upper left", fontsize=8, frameon=False)
    axes[0].set_title("Chuỗi thời gian TP.HCM (chỗ trống = thiếu dữ liệu)")
    save(fig, "01_timeseries.png")


def fig_seasonal(df):
    cols = [c for c in [main_aod(df), "no2", "fire_modis", "rain_mm_day"] if c in df]
    fig, axes = plt.subplots(1, len(cols), figsize=(3.6 * len(cols), 3.4))
    axes = np.atleast_1d(axes)
    for ax, c in zip(axes, cols):
        g = df.groupby("month")[c]
        m, s = g.mean(), g.std()
        ax.plot(m.index, m.values, marker="o", color="#1f77b4")
        ax.fill_between(m.index, m - s, m + s, alpha=0.2, color="#1f77b4")
        ax.set_xticks(range(1, 13))
        ax.set_xlabel("Tháng")
        ax.set_title(SHORT[c])
    fig.suptitle("Chu kỳ theo mùa (đường = trung bình, vùng mờ = ±1 độ lệch chuẩn)", y=1.02)
    save(fig, "02_seasonal.png")


def fig_corr(df):
    cols = [c for c in LABELS if c in df]
    if len(cols) < 2:
        return
    corr = df[cols].corr(method="spearman")
    fig, ax = plt.subplots(figsize=(6.2, 5.2))
    im = ax.imshow(corr, cmap="RdBu_r", vmin=-1, vmax=1)
    ax.set_xticks(range(len(cols)), [SHORT[c] for c in cols], rotation=45, ha="right")
    ax.set_yticks(range(len(cols)), [SHORT[c] for c in cols])
    ax.grid(False)
    for i in range(len(cols)):
        for j in range(len(cols)):
            v = corr.iloc[i, j]
            if pd.notna(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8,
                        color="white" if abs(v) > 0.6 else "black")
    fig.colorbar(im, ax=ax, shrink=0.8, label="Tương quan hạng (Spearman)")
    ax.set_title("Các biến liên quan với nhau thế nào?")
    save(fig, "03_correlation.png")


def fig_lag(df):
    if "fire_modis" not in df:
        return
    lags = range(0, 4)
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    targets = [c for c in ["aod", "no2"] if c in df]
    w = 0.8 / max(len(targets), 1)
    for k, c in enumerate(targets):
        vals = [df[c].corr(df["fire_modis"].shift(l), method="spearman") for l in lags]
        ax.bar(np.arange(len(lags)) + k * w, vals, w, label=SHORT[c])
    ax.set_xticks(np.arange(len(lags)) + w * (len(targets) - 1) / 2, [f"{l} tháng" for l in lags])
    ax.axhline(0, color="k", lw=0.6)
    ax.set_xlabel("Điểm cháy xảy ra TRƯỚC bao lâu")
    ax.set_ylabel("Tương quan (Spearman)")
    ax.set_title("Cháy rừng có đi trước bụi/NO₂ không?")
    ax.legend(frameon=False)
    save(fig, "04_fire_lag.png")


def fig_trend(df):
    cols = [c for c in [main_aod(df), "no2"] if c in df]
    if not cols:
        return
    fig, axes = plt.subplots(1, len(cols), figsize=(5.8 * len(cols), 3.8))
    axes = np.atleast_1d(axes)
    for ax, c in zip(axes, cols):
        g = df.groupby("year")[c]
        ann = g.mean()[g.count() >= 10]          # chỉ lấy năm có >= 10 tháng
        ax.plot(ann.index, ann.values, marker="o", color="#2c7fb8")
        if len(ann) >= 4:
            k, b = np.polyfit(ann.index, ann.values, 1)
            ax.plot(ann.index, k * ann.index + b, "--", color="#c0392b")
            ax.set_title(f"{SHORT[c]}: xu hướng {k:+.4f} / năm")
        ax.set_xlabel("Năm")
        ax.set_ylabel(LABELS[c], fontsize=8)
    fig.suptitle("Trung bình năm (chỉ năm có ≥10 tháng dữ liệu)", y=1.02)
    save(fig, "05_annual_trend.png")


def fig_cities():
    p = RAW / "power_monthly_cities.csv"
    if not p.exists():
        return
    d = pd.read_csv(p, parse_dates=["date"])
    g = d.groupby("city").agg(temp=("T2M", "mean"), rain=("PRECTOTCORR", "mean")).sort_values("temp")
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2), sharey=True)
    axes[0].barh(g.index, g["temp"], color="#e67e22")
    axes[0].set_xlabel("Nhiệt độ trung bình (°C)")
    axes[1].barh(g.index, g["rain"], color="#3498db")
    axes[1].set_xlabel("Lượng mưa trung bình (mm/ngày)")
    fig.suptitle("So sánh khí hậu các thành phố (NASA POWER)")
    save(fig, "06_cities_climate.png")


def fig_aod_sources(df):
    src = {c: n for c, n in [("aod", "Giovanni (file của bạn)"), ("aod_terra", "Terra (GEE)"),
                             ("aod_aqua", "Aqua (GEE)")] if c in df}
    if "aod_combined" not in df and len(src) < 2:
        return
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.2), gridspec_kw={"width_ratios": [2, 1]})
    ax = axes[0]
    for c, name in src.items():
        r = df[c].rolling(12, min_periods=9).mean().where(df[c].notna())
        ax.plot(df.index, r, lw=1.4, label=f"{name}: {int(df[c].notna().sum())} tháng")
    if "aod_combined" in df:
        r = df["aod_combined"].rolling(12, min_periods=9).mean().where(df["aod_combined"].notna())
        ax.plot(df.index, r, color="k", lw=2.4, label=f"Terra+Aqua kết hợp: {int(df['aod_combined'].notna().sum())} tháng")
    ax.set_title("AOD theo nguồn (trung bình trượt 12 tháng)")
    ax.legend(fontsize=8, frameon=False)
    ax2 = axes[1]
    if "aod" in df:
        for c in ["aod_terra", "aod_aqua"]:
            if c in df:
                d = df[["aod", c]].dropna()
                if len(d) > 5:
                    ax2.scatter(d["aod"], d[c], s=10, alpha=0.6, label=f"{src[c]}  r={d['aod'].corr(d[c]):.2f}")
        lim = [0, max(df[[c for c in src]].max().max(), 0.1)]
        ax2.plot(lim, lim, "k--", lw=0.8)
        ax2.set_xlabel("AOD Giovanni")
        ax2.set_ylabel("AOD từ GEE")
        ax2.set_title("Hai nguồn có khớp nhau không?")
        ax2.legend(fontsize=8, frameon=False)
    save(fig, "07_aod_sources.png")


def fig_omi_tropomi(df):
    if not {"no2", "no2_tropomi"} <= set(df.columns):
        return
    d = df[["no2", "no2_tropomi"]].dropna()
    if len(d) < 6:
        return
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4), gridspec_kw={"width_ratios": [2, 1]})
    sub = df.loc[d.index.min():]
    axes[0].plot(sub.index, sub["no2"], label="OMI (Giovanni)")
    axes[0].plot(sub.index, sub["no2_tropomi"], label="TROPOMI (GEE)")
    axes[0].set_ylabel(LABELS["no2"], fontsize=8)
    axes[0].set_title("NO₂: OMI và TROPOMI giai đoạn trùng nhau")
    axes[0].legend(frameon=False)
    axes[1].scatter(d["no2"], d["no2_tropomi"], s=14, alpha=0.7)
    k, b = np.polyfit(d["no2"], d["no2_tropomi"], 1)
    xs = np.array([d["no2"].min(), d["no2"].max()])
    axes[1].plot(xs, k * xs + b, "--", color="#c0392b")
    r = d["no2"].corr(d["no2_tropomi"], method="spearman")
    axes[1].set_title(f"Spearman r = {r:.2f}, n = {len(d)}\nTROPOMI ≈ {k:.2f}×OMI {b:+.2f}")
    axes[1].set_xlabel("OMI")
    axes[1].set_ylabel("TROPOMI")
    save(fig, "08_omi_vs_tropomi.png")


def fig_pm25(df):
    if "pm25" not in df or df["pm25"].notna().sum() < 6:
        return
    fig, axes = plt.subplots(1, 3, figsize=(14, 3.8), gridspec_kw={"width_ratios": [2, 1, 1]})
    axes[0].plot(df.index, df["pm25"], color="#8e44ad")
    axes[0].set_title("PM2.5 mặt đất (trung bình tháng)")
    axes[0].set_ylabel("µg/m³")
    for ax, c in zip(axes[1:], ["aod", "no2"]):
        if c not in df:
            ax.axis("off")
            continue
        d = df[["pm25", c]].dropna()
        ax.scatter(d[c], d["pm25"], s=14, alpha=0.7)
        r = d["pm25"].corr(d[c], method="spearman") if len(d) > 3 else float("nan")
        ax.set_title(f"PM2.5 vs {SHORT[c]}: r = {r:.2f}, n = {len(d)}")
        ax.set_xlabel(LABELS[c], fontsize=8)
    fig.suptitle("Kiểm chứng vệ tinh bằng đo mặt đất (r cao = vệ tinh phản ánh khá đúng không khí thật)", y=1.03)
    save(fig, "09_pm25_validation.png")


def fig_cities_gee():
    a, n = RAW / "gee_modis_aod_monthly.csv", RAW / "gee_tropomi_no2_monthly.csv"
    if not a.exists() and not n.exists():
        return
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2))
    if a.exists():
        d = pd.read_csv(a, parse_dates=["date"])
        d["aod"] = d[[c for c in ["aod_terra", "aod_aqua"] if c in d]].mean(axis=1)
        clim = d.groupby(["city", d["date"].dt.month])["aod"].mean().unstack(0)
        clim.plot(ax=axes[0], lw=1.4)
        axes[0].set_xlabel("Tháng")
        axes[0].set_ylabel("AOD 550 nm")
        axes[0].set_title("Chu kỳ mùa của AOD theo thành phố")
        axes[0].legend(fontsize=7, ncol=2, frameon=False)
    if n.exists():
        d = pd.read_csv(n)
        m = d.groupby("city")["no2_tropomi"].mean().sort_values() / 1e15
        axes[1].barh(m.index, m.values, color="#16a085")
        axes[1].set_xlabel("NO₂ TROPOMI trung bình (×10¹⁵ phân tử/cm²)")
        axes[1].set_title("Mức NO₂ trung bình (2018→)")
    save(fig, "10_cities_aod_no2.png")


def main():
    df = load()
    fig_timeseries(df)
    fig_seasonal(df)
    fig_corr(df)
    fig_lag(df)
    fig_trend(df)
    fig_cities()
    fig_aod_sources(df)
    fig_omi_tropomi(df)
    fig_pm25(df)
    fig_cities_gee()


if __name__ == "__main__":
    main()
