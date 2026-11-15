from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

START_YEAR, END_YEAR = 2000, 2026

# Khung TP.HCM: (tây, nam, đông, bắc)
BBOX_HCM = (106.4, 10.4, 107.0, 11.2)

# Khung cháy rộng hơn (khói bay xa hàng chục-trăm km): Nam VN + Campuchia + Đông Nam Thái.
# Bạn tự chỉnh và ghi rõ lý do trong báo cáo.
BBOX_FIRE = (102.0, 8.0, 108.5, 15.5)

CITIES = {  # toạ độ gần đúng, hãy tự kiểm tra lại
    "Ho Chi Minh": (10.82, 106.63), "Hanoi": (21.03, 105.85),
    "Bangkok": (13.76, 100.50), "Jakarta": (-6.21, 106.85),
    "Delhi": (28.61, 77.21), "Mumbai": (19.08, 72.88),
    "Beijing": (39.90, 116.41), "Cairo": (30.04, 31.24),
    "Lagos": (6.52, 3.38), "London": (51.51, -0.13),
    "Los Angeles": (34.05, -118.24), "Sao Paulo": (-23.55, -46.63),
}
POWER_PARAMS = ["T2M", "PRECTOTCORR", "RH2M", "WS2M"]

PROCESSED = ROOT / "data" / "processed"
FIGS = ROOT / "figures"
PROCESSED.mkdir(parents=True, exist_ok=True)
FIGS.mkdir(parents=True, exist_ok=True)

# ---- Google Earth Engine (AOD Terra/Aqua từ 2000, TROPOMI NO2 từ 2018)
GEE_START = f"{START_YEAR}-01-01"
GEE_END = f"{END_YEAR}-12-31"
CITY_HALF_DEG = 0.3          # thành phố khác TP.HCM: khung = toạ độ ± 0.3 độ

# ---- OpenAQ (PM2.5 mặt đất)
OPENAQ_CITIES = ["Ho Chi Minh", "Hanoi"]
OPENAQ_RADIUS_M = 25000      # bán kính tìm trạm đo quanh toạ độ thành phố (tối đa 25 km)
OPENAQ_START = "2015-01-01"
