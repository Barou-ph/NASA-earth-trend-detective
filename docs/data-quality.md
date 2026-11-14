# Chất lượng dữ liệu và tiền xử lý — ca TP.HCM

Tự sinh bởi `python scripts/prepare_hcm_data.py` từ thư mục `nasa_data/data/raw`. Mọi con số dưới đây được tính lại mỗi lần chạy.

## 1. Tóm tắt

| Nguồn | Phủ thời gian | Dòng | Thiếu (fill) | Vấn đề chính |
|---|---|---|---|---|
| AOD 550 nm (MODIS Deep Blue, tháng) | 2004-01 → 2026-10 | 274 | 38 (14%) | Thiếu dồn vào mùa mưa; file `_clean` cũ còn sót −9999 |
| NO₂ tầng đối lưu (OMI, ngày) | 2004-10-01 → 2026-11-11 | 8028 | 2835 (35%) + 112 giá trị ≤ 0 | Tỉ lệ ngày có số đo giảm theo năm; tháng cuối chưa đủ |
| Điểm cháy (FIRMS MODIS) | 2004, 2005 | 102798 | 0 | Mới có 2 năm → chưa đủ để kiểm định xu hướng |

## 2. AOD

- **Lỗi đã sửa:** `AOD_550_clean.csv` cũ giữ nguyên 38 dòng `-9999` vì bộ đọc chỉ bắt fill value nhỏ hơn −1e20. Nếu đưa file đó vào phân tích, trung bình bị kéo xuống -1386 (giá trị AOD thật chỉ khoảng 0,2–1,3) và độ dốc vô nghĩa (xem bảng độ nhạy). Đã sửa `nasa_data/scripts/parse_giovanni.py` (đọc fill value khai báo trong phần đầu file) và chạy lại.
- **Thiếu không ngẫu nhiên:** 38/274 tháng (14%) không có giá trị, tập trung ở các tháng: T9 (14), T8 (10), T5 (5), T7 (4), T10 (3), T6 (2). Đây là mùa mưa, mây dày làm thuật toán Deep Blue không lấy được số đo. Hệ quả: các tháng còn lại của mùa mưa thiên về ngày quang đãng.
- **Mùa khô và mùa mưa khác nhau:** trung bình AOD các tháng có dữ liệu là 0.547 (tháng 11–4) so với 0.471 (tháng 5–10).
- **Ngoại lai (6 tháng, robust |z| > 3,5):** 2004-06 (0.581), 2004-12 (0.682), 2013-12 (0.721), 2015-09 (1.27), 2020-08 (0.977), 2026-09 (1.05). Tháng 9/2015 (AOD ≈ 1,27) trùng đợt khói cháy rừng Indonesia lan rộng Đông Nam Á, nên được **giữ lại** và đánh dấu, không xóa.
- **Phạm vi không gian:** một ô lưới 1° × 1° (106–107°E, 10–11°N) gồm cả vùng nông thôn và các tỉnh lân cận, không chỉ nội đô.

Độ nhạy của kết luận xu hướng (độ dốc theo đơn vị AOD/năm, đã bỏ chu kỳ mùa):

| Cách xử lý | Độ dốc | p (t-test) | p (Mann-Kendall) | Có ý nghĩa | Số tháng |
|---|---|---|---|---|---|
| Chưa làm sạch (giữ cả giá trị −9999) | 13.4 | 0.61 | 0.93 | không | 274 |
| Đã bỏ fill value (dùng trong công cụ) | -0.00234 | 0.018 | 0.00071 | có | 236 |
| Bỏ thêm các tháng ngoại lai (z robust > 3,5) | -0.00249 | 0.0015 | 0.00039 | có | 230 |
| Chỉ mùa mưa (tháng 5–10) | -0.00359 | 0.042 | 0.0012 | có | 100 |
| Chỉ mùa khô (tháng 11–4) | -0.00134 | 0.29 | 0.12 | không | 136 |

## 3. NO₂

- **Fill value:** 2835 ngày (35%) không có số đo (cloud screening, OMI không quét tới). Đã loại, không nội suy.
- **Giá trị ≤ 0:** 112 ngày có cột NO₂ âm hoặc bằng 0, không có nghĩa vật lý (nhiễu của thuật toán). Đã loại.
- **Thiếu dòng:** 49 ngày trong khoảng thời gian không có cả dòng dữ liệu.
- **Số ngày có số đo giảm dần theo năm:** trung bình 75% số ngày/năm trong 4 năm đầu (2005–2008) còn 56% trong 4 năm gần nhất (Mann-Kendall τ = -0.505, p = 0.001). Phù hợp với hiện tượng một phần dải quét của OMI không còn dùng được từ khoảng 2007–2009 (row anomaly). Số mẫu mỗi tháng vì vậy giảm theo thời gian, và đó là rủi ro cho độ tin cậy của xu hướng.
- **Theo mùa:** tỉ lệ ngày có số đo thấp nhất ở các tháng T9 (48%), T7 (50%), T8 (54%) (mùa mưa).
- **Ngoại lai:** 16 ngày có robust z > 5 (cao nhất: 2022-06-04 = 17.6, 2020-06-17 = 15.1, 2008-01-04 = 13.8 ×10¹⁵ molec/cm²). Được giữ lại; kết quả đã được kiểm tra khi bỏ chúng.
- **Gộp tháng:** mỗi tháng cần ≥ 10 ngày hợp lệ (8 tháng không đạt), bỏ tháng chưa trọn (2026-11). Còn 258 tháng.

Độ nhạy (độ dốc theo 10¹⁵ molec/cm²/năm):

| Cách xử lý | Độ dốc | p (t-test) | p (Mann-Kendall) | Có ý nghĩa | Số tháng |
|---|---|---|---|---|---|
| Mặc định (≥ 10 ngày hợp lệ/tháng, bỏ giá trị ≤ 0) | 0.0669 | 3.1e-24 | 2.7e-33 | có | 258 |
| Ngưỡng ≥ 5 ngày/tháng | 0.0654 | 3e-23 | 1.7e-33 | có | 265 |
| Ngưỡng ≥ 15 ngày/tháng | 0.0644 | 1.2e-23 | 5.9e-30 | có | 226 |
| Ngưỡng ≥ 20 ngày/tháng (chỉ tháng được lấy mẫu dày) | 0.0496 | 2.2e-16 | 5.3e-14 | có | 125 |
| Dùng trung vị thay trung bình | 0.0652 | 2.8e-20 | 2.5e-31 | có | 258 |
| Bỏ thêm ngày ngoại lai (z > 5) | 0.064 | 2.4e-24 | 9e-33 | có | 257 |
| Giữ cả giá trị ≤ 0 | 0.0672 | 2.8e-21 | 3.8e-32 | có | 260 |

## 4. Điểm cháy (FIRMS)

- `MODIS_SP_2004`: 55981 điểm; 98% là cháy thực vật (type 0), 4% độ tin cậy < 30; 91% rơi vào tháng 12–3; chỉ 37% nằm trong bán kính 300 km quanh TP.HCM; 333 ngày có điểm cháy.
- `MODIS_SP_2005`: 46817 điểm; 98% là cháy thực vật (type 0), 4% độ tin cậy < 30; 87% rơi vào tháng 12–3; chỉ 30% nằm trong bán kính 300 km quanh TP.HCM; 313 ngày có điểm cháy.
- Khung tải về rộng (Nam Việt Nam, Campuchia, Đông Thái Lan) vì khói bay xa; phần lớn điểm cháy ở Campuchia, không phải trong thành phố.
- **Mới có 2 năm (2004, 2005) trên 22 năm cần có.** Chưa tạo preset `hcm_fire` vì kiểm định xu hướng trên 2 năm không có ý nghĩa. Cần chạy tiếp `python -m scripts.fetch_firms` (cần MAP_KEY).
- Quy tắc lọc khi đếm: chỉ type 0 (cháy thực vật; loại nguồn tĩnh và ngoài khơi) và độ tin cậy ≥ 30.

## 5. Quy tắc tiền xử lý đã áp dụng

| Bước | Quy tắc | Lý do |
|---|---|---|
| Fill value | Loại giá trị khai báo là fill (−9999, −1,27e30) | Không phải số đo |
| Nội suy | Không nội suy tháng thiếu | Nội suy tạo dữ liệu không có thật và làm phẳng mùa; kiểm định chịu được chỗ trống |
| NO₂ ≤ 0 | Loại | Cột khí không thể âm |
| Gộp tháng | ≥ 10 ngày hợp lệ, bỏ tháng chưa trọn | Trung bình từ vài ngày kém đại diện |
| Ngoại lai | Đánh dấu (robust z theo cùng tháng), không xóa | Không phân biệt được sự kiện thật với lỗi nếu thiếu số đo mặt đất |
| Chu kỳ mùa | Trừ trung bình từng tháng lịch trước khi kiểm định | Để chu kỳ mùa không che xu hướng |

## 6. Dữ liệu nên bổ sung để nâng cấp

1. **Điểm cháy FIRMS 2006–2025** (cần MAP_KEY) để nối khói/cháy với AOD và NO₂ theo độ trễ 0–3 tháng.
2. **PM2.5 mặt đất** (OpenAQ hoặc trạm đại sứ quán Mỹ tại TP.HCM, từ khoảng 2016) để kiểm chứng AOD và NO₂ có phản ánh không khí người dân hít thở không.
3. **Khí tượng cùng giai đoạn 2004–2026** (mưa, gió, nhiệt độ, độ ẩm từ NASA POWER): mưa rửa trôi bụi, gió phân tán khí. Đây là biến gây nhiễu cần đưa vào khi diễn giải AOD và NO₂.
4. **AOD kết hợp Dark Target + Deep Blue và sản phẩm Aqua (MYD08)** để giảm số tháng thiếu; **mở rộng AOD về 2000** (Terra bắt đầu 3/2000) để chuỗi dài thêm 4 năm.
5. **NO₂ từ TROPOMI (2018 →)** có độ phân giải cao hơn nhiều và không bị row anomaly; dùng đối chiếu với OMI.
6. **Cùng bộ AOD / NO₂ cho Hà Nội và một số thành phố khác** để so sánh xu hướng giữa các vùng.
