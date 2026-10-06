#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chương trình trích xuất văn bản từ hình ảnh và tạo tài liệu tiếng Nhật bằng Gemini API.
"""

import os
import re
import sys
import time
import argparse
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Bỏ qua các cảnh báo không cần thiết từ thư viện SDK
warnings.filterwarnings("ignore")

# Nạp biến môi trường từ file .env
load_dotenv()

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("❌ Lỗi: Thư viện 'google-genai' chưa được cài đặt.")
    print("👉 Hãy chạy: pip install -r requirements.txt")
    sys.exit(1)


# Danh sách các model dự phòng khi model chính bị quá tải (503) hoặc chạm hạn mức (429)
DEFAULT_FALLBACK_MODELS = [
    "gemini-flash-lite-latest",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]


def natural_sort_key(s):
    """Sắp xếp chuỗi chứa số theo thứ tự tự nhiên (ví dụ: 1, 2, ..., 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]


def get_image_part(image_path: Path) -> types.Part:
    """Đọc dữ liệu ảnh và đóng gói thành Part object cho Gemini API."""
    ext = image_path.suffix.lower()
    mime_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
    }
    mime_type = mime_types.get(ext, "image/png")
    with open(image_path, "rb") as f:
        data = f.read()
    return types.Part.from_bytes(data=data, mime_type=mime_type)


def call_gemini_with_fallback(client, models: list[str], contents, max_retries: int = 3, initial_delay: int = 4) -> tuple[str, str]:
    """
    Gọi Gemini API kèm cơ chế tự động chuyển đổi sang model dự phòng nếu model hiện tại:
    - Bị 503 UNAVAILABLE (quá tải hệ thống)
    - Bị 429 RESOURCE_EXHAUSTED (hết hạn mức)
    - Bị 404 NOT_FOUND (model không còn hỗ trợ)
    """
    for model in models:
        delay = initial_delay
        for attempt in range(1, max_retries + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=contents
                )
                if response and response.text:
                    return response.text.strip(), model
                else:
                    return "", model
            except Exception as e:
                err_str = str(e)
                is_rate_limit = "429" in err_str or "resource_exhausted" in err_str.lower()
                is_unavailable = "503" in err_str or "unavailable" in err_str.lower()
                is_not_found = "404" in err_str or "not_found" in err_str.lower()

                if is_not_found:
                    print(f"   ⚠️ Model '{model}' không khả dụng (404). Chuyển sang model khác...")
                    break  # Bỏ qua model này, sang model tiếp theo trong danh sách

                if is_unavailable or is_rate_limit:
                    if attempt < max_retries:
                        print(f"   ⏳ [{model} - {'503 Quá tải' if is_unavailable else '429 Rate Limit'}] Đang đợi {delay}s...")
                        time.sleep(delay)
                        delay = min(delay * 2, 30)
                    else:
                        print(f"   ⚠️ Model '{model}' gặp sự cố sau {max_retries} lần thử. Đang chuyển sang model dự phòng...")
                        break
                else:
                    print(f"   ⚠️ Lỗi khác ({model}): {e}")
                    if attempt == max_retries:
                        break
                    time.sleep(delay)

    raise RuntimeError("Tất cả các model Gemini đều không phản hồi. Vui lòng kiểm tra lại kết nối mạng hoặc API Key.")


def extract_text_from_images(client, models: list[str], images: list[Path], folder_name: str, batch_size: int = 8, delay: float = 3.0) -> str:
    """
    Trích xuất toàn bộ văn bản từ danh sách ảnh.
    Nếu số lượng ảnh lớn hơn batch_size, tự động chia nhỏ để đảm bảo độ chính xác.
    """
    all_extracted_texts = []
    total_images = len(images)
    
    for i in range(0, total_images, batch_size):
        batch = images[i:i + batch_size]
        batch_idx = (i // batch_size) + 1
        total_batches = (total_images + batch_size - 1) // batch_size
        
        if total_batches > 1:
            print(f"   📷 Đang trích xuất ảnh đợt {batch_idx}/{total_batches} ({len(batch)} ảnh)...")
        else:
            print(f"   📷 Đang gửi {len(batch)} ảnh tới Gemini để trích xuất...")

        prompt = (
            f"Bạn là chuyên gia OCR và số hóa tài liệu kỹ thuật cao cấp.\n"
            f"Nhiệm vụ: Trích xuất ĐẦY ĐỦ, TRUNG THỰC và CHÍNH XÁC toàn bộ nội dung văn bản "
            f"từ các hình ảnh dưới đây thuộc thư mục '{folder_name}'.\n\n"
            f"Yêu cầu:\n"
            f"1. Với mỗi hình ảnh, hãy đặt tiêu đề phân cách rõ ràng theo định dạng:\n"
            f"   === [Hình ảnh: <tên_file_ảnh>] ===\n"
            f"2. Trích xuất đầy đủ mọi câu chữ theo đúng ngôn ngữ gốc trên ảnh.\n"
            f"3. Giữ nguyên định dạng phân cấp Markdown (# tiêu đề, - danh sách, 1. 2. 3. các bước hướng dẫn).\n"
            f"4. Tuyệt đối KHÔNG tóm tắt, KHÔNG lược bỏ thông tin, KHÔNG bịa đặt nội dung.\n"
            f"5. Nếu ảnh không có chữ, ghi: [Không có văn bản].\n"
        )

        contents = [prompt]
        for img_path in batch:
            contents.append(f"\n[Ảnh đính kèm: {img_path.name}]")
            contents.append(get_image_part(img_path))

        extracted_batch, used_model = call_gemini_with_fallback(client, models, contents)
        all_extracted_texts.append(extracted_batch.strip())
        
        # Nghỉ nhẹ giữa các batch
        if i + batch_size < total_images:
            time.sleep(delay)

    return "\n\n".join(all_extracted_texts)


def translate_to_vietnamese(client, models: list[str], extracted_text: str) -> str:
    """Dịch văn bản đã trích xuất sang tiếng Việt chuẩn xác và mạch lạc."""
    print("   🌐 Đang dịch văn bản sang tiếng Việt...")
    prompt = (
        "Bạn là một biên dịch viên tiếng Nhật - tiếng Việt chuyên nghiệp trong lĩnh vực tài liệu kỹ thuật, slide thuyết trình và hướng dẫn nghiệp vụ.\n"
        "Nhiệm vụ: Dịch toàn bộ nội dung sau (gốc là tiếng Nhật) sang TIẾNG VIỆT (Vietnamese) chuẩn mực, mạch lạc và tự nhiên.\n\n"
        "Yêu cầu bản dịch:\n"
        "1. Giữ nguyên cấu trúc các phân đoạn và các tiêu đề phân cách ảnh theo định dạng:\n"
        "   === [Hình ảnh: <tên_file_ảnh>] ===\n"
        "2. Văn phong chuẩn mực, tự nhiên, chuyên nghiệp theo tài liệu kỹ thuật/kinh doanh/thuyết trình tiếng Việt.\n"
        "3. Giữ nguyên các thuật ngữ kỹ thuật quốc tế (SaaS, AI, Framework, OpenWork...), mã code, URL, tên riêng nếu có.\n"
        "4. Dịch đầy đủ 100%, tuyệt đối không tóm tắt, không lược bỏ thông tin.\n\n"
        "Nội dung cần dịch:\n"
        "--------------------\n"
        f"{extracted_text}\n"
        "--------------------"
    )

    result_text, used_model = call_gemini_with_fallback(client, models, prompt)
    return result_text


def get_folders_to_process(captures_dir: Path):
    """Lấy danh sách các thư mục cần xử lý theo thứ tự tự nhiên."""
    folders = []
    valid_exts = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
    
    # 1. Quét các thư mục con
    for item in captures_dir.iterdir():
        if item.is_dir():
            imgs = [f for f in item.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
            if imgs:
                folders.append((item.name, item, sorted(imgs, key=lambda x: natural_sort_key(x.name))))

    # Sắp xếp thư mục theo số thứ tự (6, 7, ..., 18)
    folders.sort(key=lambda x: natural_sort_key(x[0]))

    # 2. Kiểm tra nếu có ảnh lẻ nằm trực tiếp ở thư mục gốc captures
    root_imgs = [f for f in captures_dir.iterdir() if f.is_file() and f.suffix.lower() in valid_exts]
    if root_imgs:
        root_imgs_sorted = sorted(root_imgs, key=lambda x: natural_sort_key(x.name))
        folders.insert(0, ("root_images", captures_dir, root_imgs_sorted))

    return folders


def main():
    parser = argparse.ArgumentParser(description="Trích xuất text từ ảnh trong captures và dịch sang tiếng Việt.")
    parser.add_argument("--captures-dir", default="captures", help="Đường dẫn thư mục ảnh captures (mặc định: captures)")
    parser.add_argument("--output-dir", default="output", help="Đường dẫn thư mục lưu kết quả (mặc định: output)")
    parser.add_argument("--folder", default=None, help="Chỉ xử lý 1 folder cụ thể (ví dụ: --folder 6)")
    parser.add_argument("--force", action="store_true", help="Xử lý lại ngay cả khi file kết quả đã tồn tại")
    parser.add_argument("--delay", type=float, default=2.5, help="Thời gian nghỉ giữa các request (giây, mặc định: 2.5)")
    parser.add_argument("--batch-size", type=int, default=6, help="Số ảnh tối đa gửi trong 1 request OCR (mặc định: 6)")
    parser.add_argument("--model", default=None, help="Tên model Gemini ưu tiên")
    args = parser.parse_args()

    print("=" * 60)
    print("🚀 DỰ ÁN: TRÍCH XUẤT VĂN BẢN VÀ DỊCH SANG TIẾNG VIỆT")
    print("=" * 60)

    # 1. Kiểm tra API Key
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key.strip() == "" or api_key == "your_gemini_api_key_here":
        print("\n❌ Chưa tìm thấy GEMINI_API_KEY hợp lệ trong file .env!")
        print("👉 Vui lòng mở file .env và dán API Key của bạn:")
        print("   GEMINI_API_KEY=AIzaSy...")
        print("💡 Bạn có thể lấy API Key miễn phí tại: https://aistudio.google.com/app/apikey\n")
        sys.exit(1)

    # 2. Khởi tạo Gemini Client
    client = genai.Client(api_key=api_key)

    # Xây dựng danh sách models (ưu tiên model người dùng chọn + các fallback models)
    preferred_model = args.model or os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    model_list = [preferred_model]
    for m in DEFAULT_FALLBACK_MODELS:
        if m not in model_list:
            model_list.append(m)

    print(f"🤖 Model ưu tiên: {preferred_model} (sẵn sàng chuyển model dự phòng nếu quá tải)")

    # 3. Quét các thư mục
    base_captures = Path(args.captures_dir)
    base_output = Path(args.output_dir)
    base_output.mkdir(parents=True, exist_ok=True)

    if not base_captures.exists():
        print(f"❌ Không tìm thấy thư mục: {base_captures.resolve()}")
        sys.exit(1)

    all_folders = get_folders_to_process(base_captures)
    if not all_folders:
        print(f"⚠️ Không tìm thấy ảnh nào trong {base_captures.resolve()}")
        sys.exit(0)

    # Nếu người dùng chọn lọc theo 1 folder cụ thể
    if args.folder:
        all_folders = [f for f in all_folders if f[0] == args.folder]
        if not all_folders:
            print(f"❌ Không tìm thấy folder '{args.folder}' trong {args.captures_dir}")
            sys.exit(1)

    print(f"📁 Tìm thấy {len(all_folders)} thư mục/nhóm ảnh cần xử lý.")

    # 4. Xử lý từng thư mục
    for idx, (folder_name, folder_path, images) in enumerate(all_folders, 1):
        print(f"\n[{idx}/{len(all_folders)}] 📂 Đang xử lý thư mục: '{folder_name}' ({len(images)} ảnh)")

        # Đường dẫn thư mục output
        out_folder = base_output / folder_name
        out_folder.mkdir(parents=True, exist_ok=True)

        extracted_file_out = out_folder / "extracted_text.txt"
        vietnamese_file_out = out_folder / "vietnamese_translation.txt"

        # Đường dẫn lưu trực tiếp trong thư mục captures (nếu không phải thư mục ảo root_images)
        captures_extracted_file = folder_path / "extracted_text.txt" if folder_path.is_dir() and folder_name != "root_images" else None
        captures_vietnamese_file = folder_path / "vietnamese_translation.txt" if folder_path.is_dir() and folder_name != "root_images" else None

        # Kiểm tra nếu đã có file và không dùng cờ --force
        if not args.force and extracted_file_out.exists() and vietnamese_file_out.exists():
            print(f"   ⏩ Đã tồn tại kết quả. Bỏ qua (dùng --force nếu muốn xử lý lại).")
            continue

        start_time = time.time()
        try:
            # Bước 1: Trích xuất text từ ảnh (nếu đã có file extracted_text thì có thể tận dụng hoặc tạo mới)
            if not args.force and extracted_file_out.exists():
                print(f"   📄 Đã có file trích xuất, đang đọc lại để dịch...")
                extracted_text = extracted_file_out.read_text(encoding="utf-8")
            else:
                extracted_text = extract_text_from_images(
                    client=client,
                    models=model_list,
                    images=images,
                    folder_name=folder_name,
                    batch_size=args.batch_size,
                    delay=args.delay
                )

                # Lưu file trích xuất vào output/
                extracted_file_out.write_text(extracted_text, encoding="utf-8")
                print(f"   💾 Đã lưu file trích xuất: {extracted_file_out}")

                # Lưu đồng thời vào thư mục captures
                if captures_extracted_file:
                    captures_extracted_file.write_text(extracted_text, encoding="utf-8")
                    print(f"   💾 Đã lưu vào thư mục captures: {captures_extracted_file}")

                # Nghỉ nhẹ giữa trích xuất và dịch
                time.sleep(args.delay)

            # Bước 2: Dịch sang tiếng Việt
            vietnamese_text = translate_to_vietnamese(
                client=client,
                models=model_list,
                extracted_text=extracted_text
            )

            # Lưu file tiếng Việt vào output/
            vietnamese_file_out.write_text(vietnamese_text, encoding="utf-8")
            print(f"   💾 Đã lưu file tiếng Việt: {vietnamese_file_out}")

            # Lưu đồng thời vào thư mục captures
            if captures_vietnamese_file:
                captures_vietnamese_file.write_text(vietnamese_text, encoding="utf-8")
                print(f"   💾 Đã lưu vào thư mục captures: {captures_vietnamese_file}")

            elapsed = time.time() - start_time
            print(f"   ✅ Hoàn thành thư mục '{folder_name}' trong {elapsed:.1f}s.")

            # Nghỉ trước khi sang folder tiếp theo để tránh chạm giới hạn Rate Limit
            if idx < len(all_folders):
                time.sleep(args.delay)

        except Exception as e:
            print(f"   ❌ Gặp lỗi khi xử lý thư mục '{folder_name}': {e}")
            print(f"   👉 Tiếp tục xử lý các thư mục khác...")

    print("\n" + "=" * 60)
    print("🎉 TẤT CẢ ĐÃ HOÀN TẤT!")
    print(f"📁 Kết quả đã được lưu tại:")
    print(f"   1. Thư mục tập trung: {base_output.resolve()}")
    print(f"   2. Và trực tiếp trong từng thư mục tại: {base_captures.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
