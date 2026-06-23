import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO
from openpyxl.utils import get_column_letter
from dotenv import load_dotenv
import os
import json
import re
from PIL import Image

# 1. Khởi tạo cấu hình và tải biến môi trường
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if API_KEY:
    genai.configure(api_key=API_KEY)
else:
    st.warning("⚠️ Chưa tìm thấy GEMINI_API_KEY trong file .env hoặc biến môi trường.")

# Tên mô hình Gemini được sử dụng
MODEL_NAME = 'gemini-2.5-flash'

# Prompt hệ thống theo yêu cầu
PROMPT = """Bạn là hệ thống OCR chuyên đọc Giấy chứng nhận quyền sử dụng đất Việt Nam.

Hãy đọc ảnh được cung cấp và trích xuất chính xác các trường sau:

{
"chu_so_huu": "",
"dia_chi": "",
"dien_tich": "",
"muc_dich_su_dung_dat": ""
}

Quy tắc:

* Chỉ trả về JSON hợp lệ.
* Không giải thích.
* Không dùng markdown.
* Giữ nguyên tiếng Việt có dấu.
* Chủ sở hữu lấy từ phần người sử dụng đất.
* Địa chỉ lấy từ thông tin thửa đất.
* Diện tích giữ nguyên đơn vị m² nếu có.
* Mục đích sử dụng đất lấy đúng theo giấy chứng nhận.
* Nếu ảnh bị xoay, nghiêng hoặc chữ mờ, vẫn cố gắng đọc.
* Nếu không chắc chắn, thêm giá trị rỗng thay vì đoán."""

def clean_json_string(json_str):
    """
    Làm sạch chuỗi JSON phòng trường hợp Gemini trả về kèm markdown
    hoặc khoảng trắng dư thừa.
    """
    json_str = json_str.strip()
    if json_str.startswith("```json"):
        json_str = json_str[7:]
    elif json_str.startswith("```"):
        json_str = json_str[3:]
    if json_str.endswith("```"):
        json_str = json_str[:-3]
    return json_str.strip()

def process_image_with_gemini(image):
    """
    Gửi ảnh cho Gemini, đọc nội dung và phân tích thành Dictionary.
    """
    try:
        model = genai.GenerativeModel(MODEL_NAME)
        # Gửi ảnh và prompt lên Gemini
        response = model.generate_content([PROMPT, image])
        
        raw_text = response.text
        cleaned_text = clean_json_string(raw_text)
        
        try:
            # Chuyển đổi chuỗi text thành JSON
            data = json.loads(cleaned_text)
            return data, None
        except json.JSONDecodeError:
            return None, f"Lỗi parse JSON. Kết quả trả về không hợp lệ: {raw_text}"
            
    except Exception as e:
        return None, f"Lỗi khi gọi Gemini API: {str(e)}"

def create_excel_download(df):
    """
    Xuất DataFrame ra file định dạng Excel lưu vào BytesIO 
    và tự động điều chỉnh độ rộng các cột.
    """
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Du_lieu_So_do')
        worksheet = writer.sheets['Du_lieu_So_do']
        
        # Tự động căn chỉnh độ rộng của các cột
        for i, col in enumerate(df.columns):
            # Lấy độ dài chuỗi lớn nhất trong dữ liệu cột hoặc tên cột
            max_len = max(
                df[col].astype(str).map(len).max() if not df[col].empty else 0,
                len(str(col))
            )
            # Thêm 2 ký tự khoảng trắng dư để nhìn thoáng hơn
            worksheet.column_dimensions[get_column_letter(i+1)].width = max_len + 2
            
    return output.getvalue()

def main():
    # Cấu hình giao diện Streamlit
    st.set_page_config(page_title="Trích xuất dữ liệu Sổ đỏ", layout="wide", page_icon="📄")
    st.title("📄 Trích xuất dữ liệu sổ đỏ sang Excel")
    
    st.markdown("Upload ảnh **Giấy chứng nhận quyền sử dụng đất** để trích xuất thông tin tự động bằng **Gemini 2.5 Flash API**.")
    
    # Khu vực upload nhiều ảnh
    uploaded_files = st.file_uploader(
        "Chọn một hoặc nhiều hình ảnh (hỗ trợ .jpg, .jpeg, .png, .webp)",
        type=['jpg', 'jpeg', 'png', 'webp'],
        accept_multiple_files=True
    )
    
    # Sử dụng Session State để lưu dữ liệu đã trích xuất, 
    # giúp không bị mất data khi thao tác với bảng st.data_editor
    if "extracted_data" not in st.session_state:
        st.session_state.extracted_data = []
        st.session_state.processed_files = set()

    if uploaded_files:
        st.write("### 🖼️ Ảnh đã tải lên")
        
        # Hiển thị preview các ảnh đã upload
        cols = st.columns(min(len(uploaded_files), 4))
        for idx, file in enumerate(uploaded_files):
            with cols[idx % 4]:
                image = Image.open(file)
                st.image(image, caption=file.name, use_column_width=True)

        # Nút bấm thực hiện OCR trích xuất
        if st.button("🚀 Trích xuất dữ liệu", type="primary"):
            if not API_KEY:
                st.error("Lỗi: Vui lòng cấu hình `GEMINI_API_KEY` trong file `.env` hoặc biến môi trường trước khi trích xuất.")
                return

            with st.spinner("Đang gửi dữ liệu lên Gemini để phân tích... Quá trình này có thể mất vài giây đối với nhiều ảnh."):
                new_data = []
                for file in uploaded_files:
                    # Bỏ qua những file đã xử lý thành công trước đó
                    if file.name not in st.session_state.processed_files:
                        image = Image.open(file)
                        result_dict, error = process_image_with_gemini(image)
                        
                        if error:
                            st.error(f"❌ Lỗi ở file {file.name}: {error}")
                        else:
                            # Đảm bảo các trường tồn tại theo đúng yêu cầu
                            new_data.append({
                                "Tên file gốc": file.name,
                                "Chủ sở hữu": result_dict.get("chu_so_huu", ""),
                                "Địa chỉ": result_dict.get("dia_chi", ""),
                                "Diện tích": result_dict.get("dien_tich", ""),
                                "Mục đích sử dụng đất": result_dict.get("muc_dich_su_dung_dat", "")
                            })
                            st.session_state.processed_files.add(file.name)
                            st.success(f"✅ Đã đọc thành công: {file.name}")
                
                # Nạp dữ liệu mới vào session_state
                if new_data:
                    st.session_state.extracted_data.extend(new_data)
                    
    # Hiển thị bảng kết quả cho phép chỉnh sửa
    if st.session_state.extracted_data:
        st.write("---")
        st.write("### ✍️ Kiểm tra và chỉnh sửa dữ liệu")
        
        # Tạo DataFrame tạm từ session_state
        df = pd.DataFrame(st.session_state.extracted_data)
        
        # Cột STT tự động tăng
        df.insert(0, "STT", range(1, len(df) + 1))
        
        # Chọn các cột cần xuất ra Excel theo yêu cầu (Loại bỏ cột Tên file gốc khỏi view)
        view_df = df[["STT", "Chủ sở hữu", "Địa chỉ", "Diện tích", "Mục đích sử dụng đất"]]
        
        # Bảng Data Editor cho phép người dùng sửa text nếu Gemini nhận dạng bị sai
        edited_df = st.data_editor(
            view_df,
            num_rows="dynamic",        # Cho phép thêm/xóa dòng
            use_container_width=True,  # Trải rộng ra màn hình
            hide_index=True            # Ẩn cột index của pandas
        )
        
        # Khu vực Tải file Excel
        st.write("### ⬇️ Xuất dữ liệu")
        
        # Chuẩn bị BytesIO Excel
        excel_data = create_excel_download(edited_df)
        
        cols_btn = st.columns([2, 10])
        with cols_btn[0]:
            st.download_button(
                label="📥 Tải file Excel (.xlsx)",
                data=excel_data,
                file_name="TrichXuat_SoDo.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        with cols_btn[1]:
            # Nút reset dữ liệu
            if st.button("🗑️ Xóa toàn bộ kết quả"):
                st.session_state.extracted_data = []
                st.session_state.processed_files = set()
                st.rerun()

if __name__ == "__main__":
    main()
