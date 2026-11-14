# Bộ lấy dữ liệu NASA cho ca TP.HCM

pip install -r requirements.txt   (chạy mọi lệnh từ thư mục gốc nasa_data/)

1. Thời tiết (không cần tài khoản):   python -m scripts.fetch_power
2. Điểm cháy (cần MAP_KEY):           export FIRMS_MAP_KEY=...  &&  python -m scripts.fetch_firms
3. AOD / NO2: tải CSV tay từ Giovanni (khung 106.4,10.4,107.0,11.2; theo tháng; 2004→nay),
   lưu vào data/raw/ rồi:             python -m scripts.parse_giovanni data/raw/hcm_aod_modis_monthly.csv data/raw/hcm_no2_omi_monthly.csv

Khung vùng, danh sách thành phố, năm bắt đầu/kết thúc chỉnh trong scripts/config.py
