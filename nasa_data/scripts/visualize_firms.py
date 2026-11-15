import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from matplotlib.patches import Rectangle, Ellipse
from .config import RAW, PROCESSED, FIGS, CITIES, BBOX_FIRE, BBOX_HCM

plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 160, "axes.grid": True,
                     "grid.alpha": 0.25, "axes.spines.top": False, "axes.spines.right": False})

FIRMS_DIR = RAW / "firms"
SOURCES = {"MODIS_SP": "MODIS", "VIIRS_SNPP_SP": "VIIRS"}
HCM_LAT, HCM_LON = CITIES["Ho Chi Minh"]
FIRE_SEASON = [12, 1, 2, 3, 4]            # mùa đốt/cháy ở Nam Việt Nam - Campuchia - Thái Lan (chỉnh nếu cần)
RINGS = [0, 100, 300, np.inf]
RING_LABELS = ["< 100 km", "100–300 km", "> 300 km"]


def haversine_km(lat, lon, lat0, lon0):
    p1, p2 = np.radians(lat), np.radians(lat0)
    dphi, dl = p2 - p1, np.radians(lon0 - lon)
    a = np.sin(dphi / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def load(source):
    parts = []
    for f in sorted(FIRMS_DIR.glob(f"{source}_*.csv")):
        try:
            parts.append(pd.read_csv(f, usecols=lambda c: c in {"latitude", "longitude", "acq_date", "frp"}))
        except pd.errors.EmptyDataError:
            continue
    parts = [p for p in parts if len(p)]
    if not parts:
        return None
    df = pd.concat(parts, ignore_index=True)
    df["date"] = pd.to_datetime(df["acq_date"])
    df["month"] = df["date"].dt.to_period("M").dt.to_timestamp()
    df["year"] = df["date"].dt.year
    df["cal_month"] = df["date"].dt.month
    df["dist_km"] = haversine_km(df["latitude"].values, df["longitude"].values, HCM_LAT, HCM_LON)
    df["ring"] = pd.cut(df["dist_km"], RINGS, labels=RING_LABELS, right=False)
    return df.drop(columns=["acq_date"])


def monthly_counts(df):
    s = df.groupby("month").size()
    return s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"), fill_value=0)


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIGS / name)
    plt.close(fig)
    print("Đã lưu figures/" + name)


# ---------- 11. Bản đồ mật độ ----------
def draw_rings(ax):
    for r in (100, 300):
        ax.add_patch(Ellipse((HCM_LON, HCM_LAT), 2 * r / (111 * np.cos(np.radians(HCM_LAT))), 2 * r / 111,
                             fill=False, ls="--", lw=0.9, ec="#2c3e50"))
        ax.text(HCM_LON + r / (111 * np.cos(np.radians(HCM_LAT))) * 0.72, HCM_LAT + r / 111 * 0.72,
                f"{r} km", fontsize=7, color="#2c3e50")
    w, s, e, n = BBOX_HCM
    ax.add_patch(Rectangle((w, s), e - w, n - s, fill=False, ec="red", lw=1.2))
    ax.plot(HCM_LON, HCM_LAT, "*", color="#0b3d91", ms=14, mec="white", zorder=5)
    ax.text(HCM_LON + 0.15, HCM_LAT - 0.35, "TP.HCM", color="#0b3d91", fontsize=8, fontweight="bold")


def fig_map(data):
    w, s, e, n = BBOX_FIRE
    xe, ye = np.arange(w, e + 0.1, 0.1), np.arange(s, n + 0.1, 0.1)
    fig, axes = plt.subplots(len(data), 2, figsize=(11.5, 4.8 * len(data)), squeeze=False)
    for i, (name, df) in enumerate(data.items()):
        nyears = max(df["year"].nunique(), 1)
        for j, (title, mask) in enumerate([("Mùa cháy (tháng 12–4)", df["cal_month"].isin(FIRE_SEASON)),
                                           ("Các tháng còn lại", ~df["cal_month"].isin(FIRE_SEASON))]):
            d = df[mask]
            H, _, _ = np.histogram2d(d["longitude"], d["latitude"], bins=[xe, ye])
            H = np.ma.masked_where(H <= 0, H / nyears)
            ax = axes[i, j]
            if H.count():
                pcm = ax.pcolormesh(xe, ye, H.T, cmap="YlOrRd", norm=LogNorm(vmin=H.min(), vmax=H.max()))
                fig.colorbar(pcm, ax=ax, shrink=0.8, label="điểm cháy / năm / ô 0.1°")
            draw_rings(ax)
            ax.set_xlim(w, e); ax.set_ylim(s, n); ax.set_aspect("equal")
            ax.set_xlabel("Kinh độ"); ax.set_ylabel("Vĩ độ")
            ax.set_title(f"{name}: {title}")
    fig.suptitle("Điểm cháy ở đâu? (đường đứt = cách TP.HCM 100 và 300 km, khung đỏ = khung Giovanni, sao xanh = TP.HCM)", y=1.0)
    save(fig, "11_firms_map.png")


# ---------- 12. Chuỗi tháng ----------
def fig_monthly(data):
    fig, axes = plt.subplots(len(data), 1, figsize=(11, 3.2 * len(data)), sharex=False, squeeze=False)
    for ax, (name, df) in zip(axes[:, 0], data.items()):
        m = monthly_counts(df)
        ax.bar(m.index, m.values, width=25, color="#f0b27a", label="Theo tháng")
        ax.plot(m.index, m.rolling(12, min_periods=9).mean(), color="#c0392b", lw=2, label="Trung bình trượt 12 tháng")
        ax.set_ylabel("Số điểm cháy / tháng")
        ax.set_title(f"{name} (tháng cuối có thể chưa đủ ngày)")
        ax.legend(frameon=False, fontsize=8, loc="upper left")
    save(fig, "12_firms_monthly.png")


# ---------- 13. Lịch năm x tháng ----------
def fig_calendar(data):
    fig, axes = plt.subplots(1, len(data), figsize=(6.2 * len(data), 7), squeeze=False)
    for ax, (name, df) in zip(axes[0], data.items()):
        pv = df.groupby(["year", "cal_month"]).size().unstack(fill_value=0).reindex(columns=range(1, 13), fill_value=0)
        im = ax.imshow(pv.values, aspect="auto", cmap="YlOrRd")
        ax.set_xticks(range(12), range(1, 13))
        ax.set_yticks(range(len(pv)), pv.index)
        ax.grid(False)
        ax.set_xlabel("Tháng")
        ax.set_title(f"{name}: số điểm cháy theo năm × tháng")
        fig.colorbar(im, ax=ax, shrink=0.8)
    save(fig, "13_firms_calendar.png")


# ---------- 14. Tổng theo năm ----------
def fig_annual(data):
    fig, axes = plt.subplots(1, len(data), figsize=(6.2 * len(data), 3.8), squeeze=False)
    this_year = pd.Timestamp.today().year
    for ax, (name, df) in zip(axes[0], data.items()):
        a = df.groupby("year").size()
        colors = ["#bdc3c7" if y >= this_year else "#e67e22" for y in a.index]
        ax.bar(a.index, a.values, color=colors)
        ax.set_title(f"{name}: tổng điểm cháy mỗi năm (xám = năm chưa đủ)")
        ax.set_xlabel("Năm")
    save(fig, "14_firms_annual.png")


# ---------- 15. Theo khoảng cách ----------
def fig_distance(data):
    name, df = next(iter(data.items()))          # dùng nguồn dài nhất (MODIS)
    pv = df.groupby(["month", "ring"], observed=False).size().unstack(fill_value=0)
    pv = pv.reindex(pd.date_range(pv.index.min(), pv.index.max(), freq="MS"), fill_value=0)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4), gridspec_kw={"width_ratios": [2, 1]})
    axes[0].stackplot(pv.index, [pv[c] for c in RING_LABELS], labels=RING_LABELS,
                      colors=["#c0392b", "#e67e22", "#f7dc6f"])
    axes[0].set_title(f"{name}: điểm cháy theo khoảng cách tới TP.HCM")
    axes[0].set_ylabel("Số điểm cháy / tháng")
    axes[0].legend(frameon=False, loc="upper left", fontsize=8)
    clim = df.groupby(["cal_month", "ring"], observed=False).size().unstack(fill_value=0)
    clim = clim.div(clim.sum(axis=1), axis=0) * 100
    bottom = np.zeros(len(clim))
    for c, col in zip(RING_LABELS, ["#c0392b", "#e67e22", "#f7dc6f"]):
        axes[1].bar(clim.index, clim[c], bottom=bottom, color=col, label=c)
        bottom += clim[c].values
    axes[1].set_xticks(range(1, 13))
    axes[1].set_xlabel("Tháng"); axes[1].set_ylabel("% số điểm cháy")
    axes[1].set_title("Cháy xảy ra gần hay xa, theo mùa")
    save(fig, "15_firms_distance.png")


# ---------- 16. Cháy so với AOD ----------
def fig_vs_aod(data):
    p = PROCESSED / "hcm_monthly.csv"
    if not p.exists():
        print("Bỏ qua biểu đồ 16: chưa có data/processed/hcm_monthly.csv (chạy scripts.preprocess)")
        return
    hm = pd.read_csv(p, index_col="date", parse_dates=True)
    aod_col = "aod_combined" if "aod_combined" in hm else "aod"
    if aod_col not in hm:
        return
    name, df = next(iter(data.items()))
    near = df[df["dist_km"] < 300].groupby("month").size()
    near = near.reindex(hm.index, fill_value=0)
    near = near.where((hm.index >= df["month"].min()) & (hm.index <= df["month"].max()))
    d = pd.DataFrame({"fire": near, "aod": hm[aod_col]})

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.2), gridspec_kw={"width_ratios": [2, 1]})
    ax = axes[0]
    ax.plot(d.index, d["fire"].rolling(3, min_periods=2).mean(), color="#e67e22", label=f"Điểm cháy trong 300 km ({name}, TB 3 tháng)")
    ax.set_ylabel("Số điểm cháy / tháng")
    ax2 = ax.twinx()
    ax2.plot(d.index, d["aod"].rolling(3, min_periods=2).mean(), color="#2c3e50", label="AOD (TB 3 tháng)")
    ax2.set_ylabel("AOD"); ax2.grid(False)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, frameon=False, fontsize=8, loc="upper left")
    ax.set_title("Cháy và bụi có lên xuống cùng nhau không?")

    anom = d - d.groupby(d.index.month).transform("mean")          # bỏ chu kỳ mùa
    lags = range(0, 4)
    w = 0.38
    for k, (lab, frame) in enumerate([("Giá trị gốc (có cả mùa vụ)", d), ("Dị thường (đã bỏ mùa vụ)", anom)]):
        vals = [frame["aod"].corr(frame["fire"].shift(l), method="spearman") for l in lags]
        axes[1].bar(np.arange(4) + k * w, vals, w, label=lab)
    axes[1].set_xticks(np.arange(4) + w / 2, [f"{l} tháng" for l in lags])
    axes[1].axhline(0, color="k", lw=0.6)
    axes[1].set_xlabel("Cháy xảy ra TRƯỚC AOD bao lâu"); axes[1].set_ylabel("Tương quan (Spearman)")
    axes[1].set_title("Tương quan cháy → AOD")
    axes[1].legend(frameon=False, fontsize=8)
    save(fig, "16_firms_vs_aod.png")


def main():
    data = {}
    for src, label in SOURCES.items():
        df = load(src)
        if df is not None:
            data[label] = df
            print(f"{label}: {len(df):,} điểm cháy, {df['date'].min():%Y-%m-%d} → {df['date'].max():%Y-%m-%d}")
    if not data:
        raise SystemExit("Không thấy file nào trong data/raw/firms/. Chạy scripts.fetch_firms trước.")
    fig_map(data)
    fig_monthly(data)
    fig_calendar(data)
    fig_annual(data)
    fig_distance(data)
    fig_vs_aod(data)


if __name__ == "__main__":
    main()