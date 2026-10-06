# 📸 Captures to Doc (OCR Tiếng Nhật & Dịch Sang Tiếng Việt)

Dự án tự động duyệt qua từng thư mục trong `captures/`, sử dụng **Gemini API** để:
1. **Trích xuất toàn bộ văn bản gốc** từ các ảnh slide/chụp màn hình (`extracted_text.txt`).
2. **Dịch toàn bộ văn bản sang TIẾNG VIỆT** chuẩn mực, tự nhiên (`vietnamese_translation.txt`).

---

## 🚀 Cấu trúc dự án

```text
captures-to-doc/
├── .env                       <-- Chứa GEMINI_API_KEY
├── .env.example               <-- Mẫu biến môi trường
├── requirements.txt           <-- Thư viện cần thiết
├── main.py                    <-- Script xử lý chính
├── captures/                  <-- Thư mục chứa các ảnh cần xử lý (thư mục 6, 7, ..., 18)
│   ├── 6/
│   │   ├── 1_10.png
│   │   ├── 2_10.png
│   │   └── ...
│   └── ...
└── output/                    <-- Thư mục chứa kết quả
    ├── 6/
    │   ├── extracted_text.txt          (văn bản gốc tiếng Nhật từ ảnh)
    │   └── vietnamese_translation.txt  (bản dịch tiếng Việt)
    └── ...
```

---

## 🛠️ Hướng dẫn chạy

### 1. Chạy thử nghiệm trên 1 thư mục (ví dụ folder 12 hoặc 6):
```powershell
python main.py --folder 12
```

### 2. Chạy toàn bộ tất cả các thư mục:
```powershell
python main.py
```

### 3. Buộc chạy lại và ghi đè kết quả cũ:
```powershell
python main.py --force
```

### 4. Tùy chọn nâng cao:
- `--delay 3.0`: Thời gian nghỉ giữa các request (mặc định: 2.5s)
- `--batch-size 6`: Số ảnh gửi mỗi đợt OCR (mặc định: 6 ảnh)
- `--model gemini-flash-lite-latest`: Model ưu tiên (mặc định)

---

## 📂 Kết quả đầu ra

Sau khi chạy, kết quả sẽ được lưu đồng thời ở cả:
1. **Thư mục tập trung:** `output/<tên_thư_mục>/`
   - `extracted_text.txt`: Văn bản gốc trích xuất từ các ảnh.
   - `vietnamese_translation.txt`: Bản dịch tiếng Việt đầy đủ, mạch lạc.
2. **Trực tiếp trong từng thư mục ảnh:** `captures/<tên_thư_mục>/`
