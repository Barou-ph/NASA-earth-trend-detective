"""In danh sách khung toạ độ + tên file gợi ý để tải NO2 OMI (Giovanni) cho các thành phố khác.
Giovanni cần đăng nhập nên phần này tải tay, mỗi thành phố một lần (làm như TP.HCM, nên chọn cùng loại bản
theo ngày để dùng lại parse_giovanni.py + aggregate_monthly.py).
Chạy: python -m scripts.giovanni_checklist
"""
from .config import CITIES, BBOX_HCM, CITY_HALF_DEG

print(f"{'Thành phố':14s} {'Khung (tây, nam, đông, bắc)':34s} Tên file gợi ý")
for city, (lat, lon) in CITIES.items():
    h = CITY_HALF_DEG
    w, s, e, n = BBOX_HCM if city == "Ho Chi Minh" else (lon - h, lat - h, lon + h, lat + h)
    tag = city.lower().replace(" ", "_")
    print(f"{city:14s} {w:.2f}, {s:.2f}, {e:.2f}, {n:.2f}".ljust(50) + f"data/raw/{tag}_no2_omi_daily.csv")
