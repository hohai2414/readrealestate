# Ứng dụng trích xuất dữ liệu Sổ đỏ sang Excel

Ứng dụng web được xây dựng bằng Python và Streamlit, sử dụng sức mạnh của Gemini 2.5 Flash để tự động nhận dạng và trích xuất dữ liệu từ hình ảnh Giấy chứng nhận quyền sử dụng đất (Sổ đỏ) tại Việt Nam.

## Tính năng
- Upload một hoặc nhiều ảnh giấy chứng nhận.
- Trích xuất thông tin tự động bằng Gemini 2.5 Flash: Chủ sở hữu, Địa chỉ, Diện tích, Mục đích sử dụng.
- Cho phép xem trước và chỉnh sửa dữ liệu trực tiếp trên bảng.
- Xuất kết quả ra file Excel với cột được tự động căn chỉnh.

## Cài đặt

1. Đảm bảo bạn đã cài đặt Python 3.9+
2. Cài đặt các thư viện yêu cầu:
```bash
pip install -r requirements.txt
```
3. Đổi tên file `.env.example` thành `.env` và nhập API key của Google Gemini vào:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
*(Nếu chưa có API key, bạn có thể tạo tại [Google AI Studio](https://aistudio.google.com/))*

## Chạy ứng dụng

Mở terminal và chạy lệnh:
```bash
streamlit run app.py
```
