# Auto Capture & Extract — Chrome Extension v2.0

Tự động chụp màn hình từng trang → OCR bằng **Gemini AI** → Xuất toàn bộ text ra file **DOCX**.

## Cài đặt vào Chrome

1. Vào `chrome://extensions/`
2. Bật **Developer mode** (góc trên phải)
3. Nhấn **Load unpacked** → chọn thư mục `auto-capture-click`

## Lấy Gemini API Key

1. Vào [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Tạo API key miễn phí (dùng model `gemini-1.5-flash`)
3. Copy key và dán vào ô **Gemini API Key** trong popup

## Cách dùng

1. Mở trang web có ảnh cần chụp
2. Click icon extension → dán API Key → đặt Delay (giây)
3. Nhấn **▶ Bắt đầu**
4. Extension tự động:
   - Chụp từng trang
   - Gửi lên Gemini để trích xuất text
   - Nhấn Next, chờ trang đổi → chụp tiếp
   - Khi nút Next bị disabled → tạo file DOCX → tải về

## File DOCX output

- Tên file: `captured_text_YYYYMMDD_HHMM.docx`
- Lưu trong thư mục: `Downloads/`
- Mỗi trang = 1 phần riêng biệt, có tiêu đề **Trang X / Y**

## Cấu trúc file

```
auto-capture-click/
├── manifest.json      # MV3 config
├── background.js      # Service worker: Gemini API + DOCX generation
├── popup.html         # UI popup
├── popup.js           # Logic popup + API key persistence
├── content.js         # Content script (minimal)
├── jszip.min.js       # JSZip library (tạo file .docx)
└── icons/
    ├── icon16.png
    ├── icon48.png
    └── icon128.png
```

## Lưu ý

- API key được lưu trong `chrome.storage.local` (chỉ trên máy bạn)
- Nếu muốn dừng giữa chừng, nhấn **⏹ Dừng & Xuất DOCX** — extension sẽ xuất file với các trang đã chụp được
- Model Gemini `1.5-flash` có quota miễn phí khá cao (15 req/phút)
