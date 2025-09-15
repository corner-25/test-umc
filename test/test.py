import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import os, base64

# Cấu hình trang
st.set_page_config(
    page_title="Dashboard Phòng Hành chính",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS tùy chỉnh
st.markdown("""
<style>
.main-header {
    font-size: 2.5rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-bottom: 2rem;
}
.metric-container {
    background-color: #f0f2f6;
    padding: 1rem;
    border-radius: 10px;
    border-left: 4px solid #1f77b4;
}
.tab-header {
    font-size: 1.8rem;
    font-weight: bold;
    color: #2c3e50;
    margin-bottom: 1rem;
}

/* Centered header container and text */
.header-container {
    text-align: center;
    display: flex;
    flex-direction: row;
    align-items: center;
    justify-content: center;
    margin-bottom: 2rem;
}

.header-text {
    font-size: 3.2rem;
    font-weight: bold;
    color: #1f77b4;
    text-align: center;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# HEADER: logo + title on one line (flexbox)
try:
    # Encode logo to base64 for inline <img>
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logo_base64 = ""
    # Check for logo.png in current directory first, then in ./assets/
    for p in [
        os.path.join(script_dir, "logo.png"),                      # 1️⃣ same-level logo
        os.path.join(script_dir, "assets", "logo.png")            # 2️⃣ assets folder
    ]:
        if os.path.exists(p):
            with open(p, "rb") as f:
                logo_base64 = base64.b64encode(f.read()).decode()
            break
except Exception:
    logo_base64 = ""

# Build logo HTML (fallback emoji if logo not found)
if logo_base64:
    logo_html = f"<img src='data:image/png;base64,{logo_base64}' style='height:80px; width:auto;' />"
else:
    logo_html = "<span style='font-size:80px;'>🏢</span>"

# Header chính với logo
st.markdown(f"""
<div class="header-container">
    {logo_html}
    <div class="header-text" style="margin-left: 20px;">
        Dashboard Phòng Hành chính
    </div>
</div>
""", unsafe_allow_html=True)

# Sidebar - Bộ lọc toàn cục
st.sidebar.markdown("## 🔍 Bộ lọc toàn cục")

# Khởi tạo biến filter mặc định
global_date_filter = None
global_dept_filter = None

# Checkbox để bật/tắt filter
enable_global_filter = st.sidebar.checkbox("🎯 Bật bộ lọc toàn cục", value=False)

if enable_global_filter:
    # Filter ngày
    st.sidebar.markdown("### 📅 Khoảng thời gian")
    
    # Sử dụng 2 date_input riêng biệt để tránh lỗi
    col1, col2 = st.sidebar.columns(2)
    with col1:
        start_date = st.date_input(
            "Từ ngày:",
            value=None,
            help="Chọn ngày bắt đầu"
        )
    with col2:
        end_date = st.date_input(
            "Đến ngày:",
            value=None,
            help="Chọn ngày kết thúc"
        )
    
    # Tạo global_date_filter từ 2 ngày
    if start_date is not None and end_date is not None:
        global_date_filter = (start_date, end_date)
    elif start_date is not None:
        global_date_filter = start_date
    else:
        global_date_filter = None
    
    # Filter phòng ban (chỉ hiện khi có dữ liệu)
    st.sidebar.markdown("### 🏢 Phòng ban")
    st.sidebar.info("Filter phòng ban sẽ xuất hiện khi upload dữ liệu có thông tin phòng ban")

st.sidebar.markdown("---")

# Hàm tiện ích để áp dụng filter toàn cục
def apply_global_filter(df, date_col='datetime'):
    """Áp dụng bộ lọc toàn cục cho DataFrame"""
    if not enable_global_filter:
        return df
    
    filtered_df = df.copy()
    
    # Áp dụng filter ngày
    if global_date_filter is not None:
        # Kiểm tra nếu là tuple/list với 2 phần tử
        if isinstance(global_date_filter, (list, tuple)) and len(global_date_filter) == 2:
            filtered_df = filtered_df[
                (filtered_df[date_col] >= pd.to_datetime(global_date_filter[0])) & 
                (filtered_df[date_col] <= pd.to_datetime(global_date_filter[1]))
            ]
        # Nếu chỉ là 1 ngày, filter từ ngày đó trở đi
        elif hasattr(global_date_filter, '__iter__') == False:  # single date
            filtered_df = filtered_df[filtered_df[date_col] >= pd.to_datetime(global_date_filter)]
    
    return filtered_df

# Hàm xử lý dữ liệu văn bản đến
def process_incoming_documents_data(uploaded_file):
    try:
        if uploaded_file.type == "application/json":
            data = json.load(uploaded_file)
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
            else:
                df = pd.DataFrame(data)
        else:
            df = pd.read_csv(uploaded_file)
        
        # Tạo cột datetime (sử dụng 'date' thay vì 'day')
        df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
        df['weekday'] = df['datetime'].dt.day_name()
        df['week'] = df['datetime'].dt.isocalendar().week
        
        # Đảm bảo các cột cần thiết tồn tại, nếu không thì tạo với giá trị 0
        required_columns = ['no_response_required', 'response_required', 
                          'response_required_VanBan', 'response_required_Email', 
                          'response_required_DienThoai', 'response_required_PhanMem']
        
        for col in required_columns:
            if col not in df.columns:
                df[col] = 0
        
        # Đảm bảo cột processed_rate_on_time và processed_rate_late tồn tại
        if 'processed_rate_on_time' not in df.columns:
            df['processed_rate_on_time'] = 0
        if 'processed_rate_late' not in df.columns:
            df['processed_rate_late'] = 0
            
        return df
    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu: {str(e)}")
        return None

# Hàm tạo pivot table
def create_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích theo thời gian")

    # CSS cho table lớn hơn và đẹp hơn
    st.markdown("""
    <style>
    .pivot-table {
        font-size: 16px !important;
        font-weight: 500;
    }
    .pivot-table td {
        padding: 12px 8px !important;
        text-align: center !important;
    }
    .pivot-table th {
        padding: 15px 8px !important;
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        font-size: 17px !important;
    }
    .increase { color: #28a745 !important; font-weight: bold; }
    .decrease { color: #dc3545 !important; font-weight: bold; }
    .neutral { color: #6c757d !important; }
    .new-period { color: #007bff !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    # Lựa chọn mức độ tổng hợp
    col1, col2 = st.columns([1, 3])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Ngày', 'Tuần', 'Tháng', 'Quý', 'Năm'],
            index=1,  # Mặc định là Tuần
            key="pivot_period_type"
        )

    # Chuẩn bị dữ liệu theo loại period
    df_period = df.copy()

    if period_type == 'Tuần':
        df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
    elif period_type == 'Tháng':
        df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    elif period_type == 'Quý':
        df_period['quarter'] = ((df_period['month'] - 1) // 3) + 1
        df_period['period'] = 'Q' + df_period['quarter'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['quarter']
    elif period_type == 'Năm':
        df_period['period'] = df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year']
    else:  # Ngày
        df_period['period'] = df_period['datetime'].dt.strftime('%d/%m/%Y')
        df_period['period_sort'] = df_period['datetime']

    # Tạo pivot table với các chỉ số mới
    pivot_columns = ['total_incoming', 'no_response_required', 'response_required',
                    'processed_on_time', 'processed_late', 'response_required_VanBan',
                    'response_required_Email', 'response_required_DienThoai', 'response_required_PhanMem']

    # Kiểm tra các cột có tồn tại không
    available_columns = [col for col in pivot_columns if col in df_period.columns]

    pivot_data = df_period.groupby(['period', 'period_sort'])[available_columns].sum().reset_index()
    pivot_data = pivot_data.sort_values('period_sort', ascending=False)

    # Tính toán biến động so với kỳ trước
    for col in available_columns:
        pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
        pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
        pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
        pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

    # Tính tỷ lệ xử lý đúng hạn
    if 'total_incoming' in available_columns and 'processed_on_time' in available_columns:
        pivot_data['on_time_rate'] = (pivot_data['processed_on_time'] / pivot_data['total_incoming'] * 100).round(1)
        pivot_data['on_time_rate'] = pivot_data['on_time_rate'].fillna(0)

    # Tạo DataFrame hiển thị với biến động trong cùng cell
    display_data = pivot_data.copy()

    # Hàm tạo cell kết hợp giá trị và biến động
    def format_cell_with_change(row, col):
        current_val = row[col]
        change_val = row[f'{col}_change']
        change_pct = row[f'{col}_change_pct']
        prev_val = row[f'{col}_prev']

        # Nếu không có dữ liệu kỳ trước, chỉ hiển thị giá trị hiện tại
        if pd.isna(prev_val) or prev_val == 0:
            return f"{int(current_val)}"

        # Định màu sắc theo chiều hướng thay đổi
        if change_val > 0:
            color_class = "increase"
            arrow = "↗"
            sign = "+"
        elif change_val < 0:
            color_class = "decrease"
            arrow = "↘"
            sign = ""
        else:
            color_class = "neutral"
            arrow = "→"
            sign = ""

        # Trả về HTML với màu sắc
        return f"""<div style="text-align: center; line-height: 1.2;">
            <div style="font-size: 16px; font-weight: 600;">{int(current_val)}</div>
            <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                {arrow} {sign}{int(change_val)} ({change_pct:+.1f}%)
            </div>
        </div>"""

    # Tạo cột hiển thị mới
    display_columns = ['period']
    column_names = {f'period': f'{period_type}'}

    for col in available_columns:
        new_col = f'{col}_display'
        display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
        display_columns.append(new_col)

        # Mapping tên cột
        if col == 'total_incoming':
            column_names[new_col] = 'Tổng VB đến'
        elif col == 'no_response_required':
            column_names[new_col] = 'Không yêu cầu phản hồi'
        elif col == 'response_required':
            column_names[new_col] = 'Yêu cầu phản hồi'
        elif col == 'processed_on_time':
            column_names[new_col] = 'Xử lý đúng hạn'
        elif col == 'processed_late':
            column_names[new_col] = 'Xử lý trễ hạn'
        elif col == 'response_required_VanBan':
            column_names[new_col] = 'PH - Văn bản'
        elif col == 'response_required_Email':
            column_names[new_col] = 'PH - Email'
        elif col == 'response_required_DienThoai':
            column_names[new_col] = 'PH - Điện thoại'
        elif col == 'response_required_PhanMem':
            column_names[new_col] = 'PH - Phần mềm'

    # Bỏ tỷ lệ đúng hạn theo yêu cầu

    st.markdown(f"#### 📋 Tổng hợp theo {period_type} (bao gồm biến động)")

    # Hiển thị bảng với HTML để render màu sắc
    df_display = display_data[display_columns].rename(columns=column_names)

    # Tạo HTML table với sticky header
    html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table class='pivot-table' style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

    # Header với sticky positioning
    html_table += "<thead><tr>"
    for col in df_display.columns:
        html_table += f"<th style='position: sticky; top: 0; padding: 15px 8px; text-align: center; background-color: #f0f2f6; font-weight: bold; font-size: 17px; border: 1px solid #ddd; z-index: 10;'>{col}</th>"
    html_table += "</tr></thead>"

    # Body
    html_table += "<tbody>"
    for _, row in df_display.iterrows():
        html_table += "<tr>"
        for i, col in enumerate(df_display.columns):
            cell_value = row[col]
            style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd; vertical-align: middle;"
            if i == 0:  # Period column
                style += " font-weight: 600; background-color: #f8f9fa;"
            html_table += f"<td style='{style}'>{cell_value}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table></div>"

    st.markdown(html_table, unsafe_allow_html=True)

    return period_type


# Hàm xử lý dữ liệu văn bản đi
def process_outgoing_documents_data(uploaded_file):
    try:
        if uploaded_file.type == "application/json":
            data = json.load(uploaded_file)
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
            else:
                df = pd.DataFrame(data)
        else:
            df = pd.read_csv(uploaded_file)
        
        # Tạo cột datetime
        df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
        df['weekday'] = df['datetime'].dt.day_name()
        df['week'] = df['datetime'].dt.isocalendar().week
        
        # Xử lý các cột nested (contracts, decisions, etc.)
        def extract_total(col_data):
            if pd.isna(col_data):
                return 0
            if isinstance(col_data, dict):
                return col_data.get('total', 0)
            if isinstance(col_data, str):
                try:
                    parsed = json.loads(col_data)
                    return parsed.get('total', 0)
                except:
                    return 0
            return 0
        
        # Hàm trích xuất chi tiết từ nested data
        def extract_detail(col_data):
            if pd.isna(col_data):
                return []
            if isinstance(col_data, dict) and 'detail' in col_data:
                return col_data.get('detail', [])
            if isinstance(col_data, str):
                try:
                    parsed = json.loads(col_data)
                    return parsed.get('detail', [])
                except:
                    return []
            return []
        
        # Tạo các cột tổng hợp
        category_columns = ['contracts', 'decisions', 'regulations', 'rules', 'procedures', 'instruct']
        for col in category_columns:
            if col in df.columns:
                df[f'{col}_total'] = df[col].apply(extract_total)
                df[f'{col}_detail'] = df[col].apply(extract_detail)
            else:
                df[f'{col}_total'] = 0
                df[f'{col}_detail'] = []
        
        # Đảm bảo cột documents tồn tại
        if 'documents' not in df.columns:
            df['documents'] = 0
            
        # Tổng văn bản đi = documents + tất cả các loại khác
        df['total_outgoing'] = (
            df['documents'] +
            df.get('contracts_total', 0) + 
            df.get('decisions_total', 0) + 
            df.get('regulations_total', 0) + 
            df.get('rules_total', 0) + 
            df.get('procedures_total', 0) + 
            df.get('instruct_total', 0)
        )
            
        return df
    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu văn bản đi: {str(e)}")
        return None

# Hàm tạo pivot table cho văn bản đi
def create_outgoing_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích văn bản đi theo thời gian")

    # CSS cho table lớn hơn và đẹp hơn
    st.markdown("""
    <style>
    .pivot-table-outgoing {
        font-size: 16px !important;
        font-weight: 500;
    }
    .pivot-table-outgoing td {
        padding: 12px 8px !important;
        text-align: center !important;
    }
    .pivot-table-outgoing th {
        padding: 15px 8px !important;
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        font-size: 17px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Lựa chọn mức độ tổng hợp
    col1, col2 = st.columns([1, 3])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Ngày', 'Tuần', 'Tháng', 'Quý', 'Năm'],
            index=1,  # Mặc định là Tuần
            key="outgoing_period_type"
        )

    # Chuẩn bị dữ liệu theo loại period
    df_period = df.copy()

    if period_type == 'Tuần':
        df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
    elif period_type == 'Tháng':
        df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    elif period_type == 'Quý':
        df_period['quarter'] = ((df_period['month'] - 1) // 3) + 1
        df_period['period'] = 'Q' + df_period['quarter'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['quarter']
    elif period_type == 'Năm':
        df_period['period'] = df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year']
    else:  # Ngày
        df_period['period'] = df_period['datetime'].dt.strftime('%d/%m/%Y')
        df_period['period_sort'] = df_period['datetime']

    # Tạo pivot table với các chỉ số văn bản đi
    pivot_columns = ['documents', 'contracts_total', 'decisions_total', 'regulations_total',
                    'rules_total', 'procedures_total', 'instruct_total']

    # Kiểm tra các cột có tồn tại không
    available_columns = [col for col in pivot_columns if col in df_period.columns]

    pivot_data = df_period.groupby(['period', 'period_sort'])[available_columns].sum().reset_index()

    # Tính total_outgoing đúng công thức = tất cả các loại cộng lại
    total_columns = ['documents', 'contracts_total', 'decisions_total', 'regulations_total',
                    'rules_total', 'procedures_total', 'instruct_total']

    # Chỉ cộng các cột có trong pivot_data
    existing_total_columns = [col for col in total_columns if col in pivot_data.columns]
    if existing_total_columns:
        pivot_data['total_outgoing'] = pivot_data[existing_total_columns].sum(axis=1)
    else:
        pivot_data['total_outgoing'] = 0

    # Cập nhật available_columns để bao gồm total_outgoing
    available_columns = ['total_outgoing'] + available_columns
    pivot_data = pivot_data.sort_values('period_sort', ascending=False)

    # Tính toán biến động so với kỳ trước
    for col in available_columns:
        pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
        pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
        pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
        pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

    # Tạo DataFrame hiển thị với biến động trong cùng cell
    display_data = pivot_data.copy()

    # Hàm tạo cell kết hợp giá trị và biến động
    def format_cell_with_change(row, col):
        current_val = row[col]
        change_val = row[f'{col}_change']
        change_pct = row[f'{col}_change_pct']
        prev_val = row[f'{col}_prev']

        # Nếu không có dữ liệu kỳ trước, chỉ hiển thị giá trị hiện tại
        if pd.isna(prev_val) or prev_val == 0:
            return f"{int(current_val)}"

        # Định màu sắc theo chiều hướng thay đổi
        if change_val > 0:
            color_class = "increase"
            arrow = "↗"
            sign = "+"
        elif change_val < 0:
            color_class = "decrease"
            arrow = "↘"
            sign = ""
        else:
            color_class = "neutral"
            arrow = "→"
            sign = ""

        # Trả về HTML với màu sắc
        return f"""<div style="text-align: center; line-height: 1.2;">
            <div style="font-size: 16px; font-weight: 600;">{int(current_val)}</div>
            <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                {arrow} {sign}{int(change_val)} ({change_pct:+.1f}%)
            </div>
        </div>"""

    # Tạo cột hiển thị mới
    display_columns = ['period']
    column_names = {f'period': f'{period_type}'}

    for col in available_columns:
        new_col = f'{col}_display'
        display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
        display_columns.append(new_col)

        # Mapping tên cột
        if col == 'total_outgoing':
            column_names[new_col] = 'Tổng VB đi'
        elif col == 'documents':
            column_names[new_col] = 'VB phát hành'
        elif col == 'contracts_total':
            column_names[new_col] = 'Hợp đồng'
        elif col == 'decisions_total':
            column_names[new_col] = 'Quyết định'
        elif col == 'regulations_total':
            column_names[new_col] = 'Quy chế'
        elif col == 'rules_total':
            column_names[new_col] = 'Quy định'
        elif col == 'procedures_total':
            column_names[new_col] = 'Thủ tục'
        elif col == 'instruct_total':
            column_names[new_col] = 'Hướng dẫn'

    st.markdown(f"#### 📋 Tổng hợp theo {period_type} (bao gồm biến động)")

    # Hiển thị bảng với HTML để render màu sắc
    df_display = display_data[display_columns].rename(columns=column_names)

    # Tạo HTML table với sticky header
    html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table class='pivot-table-outgoing' style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

    # Header với sticky positioning
    html_table += "<thead><tr>"
    for col in df_display.columns:
        html_table += f"<th style='position: sticky; top: 0; padding: 15px 8px; text-align: center; background-color: #f0f2f6; font-weight: bold; font-size: 17px; border: 1px solid #ddd; z-index: 10;'>{col}</th>"
    html_table += "</tr></thead>"

    # Body
    html_table += "<tbody>"
    for _, row in df_display.iterrows():
        html_table += "<tr>"
        for i, col in enumerate(df_display.columns):
            cell_value = row[col]
            style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd; vertical-align: middle;"
            if i == 0:  # Period column
                style += " font-weight: 600; background-color: #f8f9fa;"
            html_table += f"<td style='{style}'>{cell_value}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table></div>"

    st.markdown(html_table, unsafe_allow_html=True)

    return period_type

# Hàm tạo biểu đồ cho văn bản đi
def create_outgoing_docs_charts(df, period_type='Tuần'):
    # Hàng 1: Biểu đồ tổng quan
    col1, col2 = st.columns(2)
    
    with col1:
        # Chart 1: Hướng dẫn + Thủ tục
        # Biểu đồ theo period_type được chọn
        df_chart = df.copy()

        # Tạo period theo lựa chọn
        if period_type == 'Tuần':
            df_chart['period'] = 'W' + df_chart['week'].astype(str) + '-' + df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['week']
            chart_title = '📈 Văn bản đi theo tuần'
            x_title = "Tuần"
        elif period_type == 'Tháng':
            df_chart['period'] = 'T' + df_chart['month'].astype(str) + '-' + df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['month']
            chart_title = '📈 Văn bản đi theo tháng'
            x_title = "Tháng"
        elif period_type == 'Quý':
            df_chart['quarter'] = ((df_chart['month'] - 1) // 3) + 1
            df_chart['period'] = 'Q' + df_chart['quarter'].astype(str) + '-' + df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['quarter']
            chart_title = '📈 Văn bản đi theo quý'
            x_title = "Quý"
        elif period_type == 'Năm':
            df_chart['period'] = df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year']
            chart_title = '📈 Văn bản đi theo năm'
            x_title = "Năm"
        else:  # Ngày
            df_chart['period'] = df_chart['datetime'].dt.strftime('%d/%m/%Y')
            df_chart['period_sort'] = df_chart['datetime']
            chart_title = '📈 Văn bản đi theo ngày'
            x_title = "Ngày"

        business_categories = ['instruct_total', 'procedures_total']
        business_names = ['Hướng dẫn', 'Thủ tục']
        business_colors = ['#1f77b4', '#ff7f0e']

        # Chỉ lấy các cột có trong DataFrame
        available_business_categories = [col for col in business_categories if col in df_chart.columns]

        # Tính data theo period (chỉ với các cột có sẵn)
        if available_business_categories:
            business_data = df_chart.groupby(['period', 'period_sort'])[available_business_categories].sum().reset_index()
        else:
            # Tạo DataFrame rỗng nếu không có cột nào
            business_data = df_chart.groupby(['period', 'period_sort']).size().reset_index(name='count')
        business_data = business_data.sort_values('period_sort')

        fig_business = go.Figure()

        for i, cat in enumerate(business_categories):
            if cat in available_business_categories and cat in business_data.columns and business_data[cat].sum() > 0:
                fig_business.add_trace(go.Scatter(
                    x=business_data['period'],
                    y=business_data[cat],
                    mode='lines+markers',
                    name=business_names[i],
                    line=dict(color=business_colors[i], width=3),
                    marker=dict(size=8)
                ))

                # Thêm đường xu hướng
                if len(business_data) >= 3:
                    ma_window = min(3, len(business_data)//2)
                    if ma_window > 0:
                        ma_trend = business_data[cat].rolling(window=ma_window, center=True).mean()
                        fig_business.add_trace(go.Scatter(
                            x=business_data['period'],
                            y=ma_trend,
                            mode='lines',
                            name=f'{business_names[i]} - Xu hướng',
                            line=dict(color=business_colors[i], width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False
                        ))

        fig_business.update_layout(
            title=f'📄 Hướng dẫn & Thủ tục theo {period_type.lower()}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified'
        )
        st.plotly_chart(fig_business, use_container_width=True)
    
    with col2:
        # Chart 2: Quy chế + Quy định (bỏ hướng dẫn và thủ tục)
        admin_categories = ['regulations_total', 'rules_total']
        admin_names = ['Quy chế', 'Quy định']
        admin_colors = ['#2ca02c', '#d62728']

        # Chỉ lấy các cột có trong DataFrame
        available_admin_categories = [col for col in admin_categories if col in df_chart.columns]

        # Tính data theo period (chỉ với các cột có sẵn)
        if available_admin_categories:
            admin_data = df_chart.groupby(['period', 'period_sort'])[available_admin_categories].sum().reset_index()
        else:
            # Tạo DataFrame rỗng nếu không có cột nào
            admin_data = df_chart.groupby(['period', 'period_sort']).size().reset_index(name='count')
        admin_data = admin_data.sort_values('period_sort')

        fig_admin = go.Figure()

        for i, cat in enumerate(admin_categories):
            if cat in available_admin_categories and cat in admin_data.columns and admin_data[cat].sum() > 0:
                fig_admin.add_trace(go.Scatter(
                    x=admin_data['period'],
                    y=admin_data[cat],
                    mode='lines+markers',
                    name=admin_names[i],
                    line=dict(color=admin_colors[i], width=3),
                    marker=dict(size=8)
                ))

                # Thêm đường xu hướng
                if len(admin_data) >= 3:
                    ma_window = min(3, len(admin_data)//2)
                    if ma_window > 0:
                        ma_trend = admin_data[cat].rolling(window=ma_window, center=True).mean()
                        fig_admin.add_trace(go.Scatter(
                            x=admin_data['period'],
                            y=ma_trend,
                            mode='lines',
                            name=f'{admin_names[i]} - Xu hướng',
                            line=dict(color=admin_colors[i], width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False
                        ))

        fig_admin.update_layout(
            title=f'📋 Quy chế & Quy định theo {period_type.lower()}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified'
        )
        st.plotly_chart(fig_admin, use_container_width=True)
    
    # Hàng 2: Biểu đồ chi tiết các nhóm văn bản
    st.markdown("#### 📊 Phân tích chi tiết theo nhóm văn bản")

    col1, col2 = st.columns(2)

    with col1:
        # Group data theo period
        period_data = df_chart.groupby(['period', 'period_sort']).agg({
            'total_outgoing': 'sum',
            'documents': 'sum'
        }).reset_index()
        period_data = period_data.sort_values('period_sort')

        # Tạo biểu đồ so sánh
        fig_compare = go.Figure()

        if 'total_outgoing' in df.columns:
            # Đường chính
            fig_compare.add_trace(go.Scatter(
                x=period_data['period'],
                y=period_data['total_outgoing'],
                mode='lines+markers',
                name='Tổng văn bản đi',
                line=dict(color='blue', width=3),
                marker=dict(size=8)
            ))

            # Đường xu hướng
            if len(period_data) >= 3:
                ma_window = min(3, len(period_data)//2)
                if ma_window > 0:
                    ma_trend = period_data['total_outgoing'].rolling(window=ma_window, center=True).mean()
                    fig_compare.add_trace(go.Scatter(
                        x=period_data['period'],
                        y=ma_trend,
                        mode='lines',
                        name='Xu hướng tổng',
                        line=dict(color='blue', width=2, dash='dash'),
                        opacity=0.7,
                        showlegend=False
                    ))

        # Đường chính
        fig_compare.add_trace(go.Scatter(
            x=period_data['period'],
            y=period_data['documents'],
            mode='lines+markers',
            name='Văn bản phát hành',
            line=dict(color='orange', width=3),
            marker=dict(size=8)
        ))

        # Đường xu hướng
        if len(period_data) >= 3:
            ma_window = min(3, len(period_data)//2)
            if ma_window > 0:
                ma_trend = period_data['documents'].rolling(window=ma_window, center=True).mean()
                fig_compare.add_trace(go.Scatter(
                    x=period_data['period'],
                    y=ma_trend,
                    mode='lines',
                    name='Xu hướng phát hành',
                    line=dict(color='orange', width=2, dash='dash'),
                    opacity=0.7,
                    showlegend=False
                ))

        fig_compare.update_layout(
            title=f'{chart_title} (So sánh)',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified'
        )
        st.plotly_chart(fig_compare, use_container_width=True)

        # Biểu đồ phân bố theo loại văn bản theo period
        categories = ['contracts_total', 'decisions_total', 'regulations_total',
                     'rules_total', 'procedures_total', 'instruct_total']
        category_names = ['Hợp đồng', 'Quyết định', 'Quy chế', 'Quy định', 'Thủ tục', 'Hướng dẫn']

        # Chỉ lấy các cột có trong DataFrame
        available_categories = [col for col in categories if col in df_chart.columns]

        # Tính tổng các loại văn bản theo period (chỉ với các cột có sẵn)
        if available_categories:
            category_data = df_chart.groupby(['period', 'period_sort'])[available_categories].sum().reset_index()
        else:
            # Tạo DataFrame rỗng nếu không có cột nào
            category_data = df_chart.groupby(['period', 'period_sort']).size().reset_index(name='count')
        category_data = category_data.sort_values('period_sort')

        # Tạo stacked bar chart
        fig_stack = go.Figure()

        for i, cat in enumerate(categories):
            if cat in available_categories and cat in category_data.columns and category_data[cat].sum() > 0:
                fig_stack.add_trace(go.Bar(
                    name=category_names[i],
                    x=category_data['period'],
                    y=category_data[cat]
                ))

        fig_stack.update_layout(
            title=f'📊 Phân bố loại văn bản theo {period_type.lower()}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            barmode='stack'
        )
        st.plotly_chart(fig_stack, use_container_width=True)

    with col2:
        # Biểu đồ xu hướng các loại văn bản chính theo period
        fig_trend = go.Figure()

        # Top 2 loại văn bản chính: Hợp đồng + Quyết định (bỏ quy chế)
        top_categories = ['contracts_total', 'decisions_total']
        top_names = ['Hợp đồng', 'Quyết định']
        colors = ['blue', 'red']

        for i, cat in enumerate(top_categories):
            if cat in df.columns and category_data[cat].sum() > 0:
                # Đường chính
                fig_trend.add_trace(go.Scatter(
                    x=category_data['period'],
                    y=category_data[cat],
                    mode='lines+markers',
                    name=top_names[i],
                    line=dict(color=colors[i], width=3),
                    marker=dict(size=8)
                ))

                # Thêm đường xu hướng
                if len(category_data) >= 3:
                    ma_window = min(3, len(category_data)//2)
                    if ma_window > 0:
                        ma_trend = category_data[cat].rolling(window=ma_window, center=True).mean()
                        fig_trend.add_trace(go.Scatter(
                            x=category_data['period'],
                            y=ma_trend,
                            mode='lines',
                            name=f'{top_names[i]} - Xu hướng',
                            line=dict(color=colors[i], width=2, dash='dash'),
                            opacity=0.7,
                            showlegend=False
                        ))

        fig_trend.update_layout(
            title=f'📈 Xu hướng văn bản chính theo {period_type.lower()}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified'
        )
        st.plotly_chart(fig_trend, use_container_width=True)

        # Biểu đồ pie tổng hợp
        category_totals = []
        available_names = []
        for i, cat in enumerate(categories):
            if cat in df.columns:
                total = df[cat].sum()
                if total > 0:
                    category_totals.append(total)
                    available_names.append(category_names[i])

        if category_totals:
            fig_pie = px.pie(
                values=category_totals,
                names=available_names,
                title='📊 Phân bố tổng hợp theo loại văn bản'
            )
            st.plotly_chart(fig_pie, use_container_width=True)

# Hàm xử lý dữ liệu quản lý công việc
def process_task_management_data(uploaded_file):
    try:
        if uploaded_file.type == "application/json":
            data = json.load(uploaded_file)
            if isinstance(data, dict) and "data" in data:
                data_list = data["data"]
            else:
                data_list = data
        else:
            df_temp = pd.read_csv(uploaded_file)
            data_list = df_temp.to_dict('records')
        
        # Tạo DataFrame từ all_departments
        all_dept_records = []
        dept_detail_records = []
        
        for record in data_list:
            # Xử lý Date -> date để consistent với các tab khác
            if 'Date' in record:
                record['date'] = record['Date']
            if 'Month' in record:
                record['month'] = record['Month'] 
            if 'Year' in record:
                record['year'] = record['Year']
            
            # Tạo record cho tổng hợp all_departments
            all_dept_data = record.get('all_departments', {})
            all_dept_record = {
                'date': record.get('date', record.get('Date', 1)),
                'month': record.get('month', record.get('Month', 1)),
                'year': record.get('year', record.get('Year', 2025)),
                'department': 'Tất cả phòng ban',
                'tasks_assigned': all_dept_data.get('tasks_assigned', 0),
                'tasks_completed_on_time': all_dept_data.get('tasks_completed_on_time', 0),
                'tasks_completed_on_time_rate': all_dept_data.get('tasks_completed_on_time_rate', 0),
                'tasks_new': all_dept_data.get('tasks_new', 0),
                'tasks_new_rate': all_dept_data.get('tasks_new_rate', 0),
                'tasks_processing': all_dept_data.get('tasks_processing', 0),
                'tasks_processing_rate': all_dept_data.get('tasks_processing_rate', 0)
            }
            all_dept_records.append(all_dept_record)
            
            # Tạo records cho từng phòng ban
            detail_depts = record.get('detail_departments', [])
            for dept in detail_depts:
                dept_record = {
                    'date': record.get('date', record.get('Date', 1)),
                    'month': record.get('month', record.get('Month', 1)),
                    'year': record.get('year', record.get('Year', 2025)),
                    'department': dept.get('Name', 'Không xác định'),
                    'tasks_assigned': dept.get('tasks_assigned', 0),
                    'tasks_completed_on_time': dept.get('tasks_completed_on_time', 0),
                    'tasks_completed_on_time_rate': dept.get('tasks_completed_on_time_rate', 0),
                    'tasks_new': dept.get('tasks_new', 0),
                    'tasks_new_rate': dept.get('tasks_new_rate', 0),
                    'tasks_processing': dept.get('tasks_processing', 0),
                    'tasks_processing_rate': dept.get('tasks_processing_rate', 0)
                }
                dept_detail_records.append(dept_record)
        
        # Tạo DataFrame tổng hợp
        df_all = pd.DataFrame(all_dept_records)
        df_detail = pd.DataFrame(dept_detail_records)
        
        # Tạo datetime và week
        for df in [df_all, df_detail]:
            df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
            df['weekday'] = df['datetime'].dt.day_name()
            df['week'] = df['datetime'].dt.isocalendar().week
            
            # Tính các chỉ số phụ
            df['completion_rate'] = (df['tasks_completed_on_time'] / df['tasks_assigned'] * 100).fillna(0)
            df['processing_rate'] = (df['tasks_processing'] / df['tasks_assigned'] * 100).fillna(0)
            df['new_rate'] = (df['tasks_new'] / df['tasks_assigned'] * 100).fillna(0)
        
        return df_all, df_detail
        
    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu quản lý công việc: {str(e)}")
        return None, None

# Hàm xử lý dữ liệu lịch họp
def process_meeting_data(uploaded_file):
    try:
        if uploaded_file.type == "application/json":
            data = json.load(uploaded_file)
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
            else:
                df = pd.DataFrame(data)
        else:
            df = pd.read_csv(uploaded_file)
        
        # Chuẩn hóa tên cột
        if 'Date' in df.columns:
            df['date'] = df['Date']
        if 'Month' in df.columns:
            df['month'] = df['Month']
        if 'Year' in df.columns:
            df['year'] = df['Year']
            
        # Tạo cột datetime
        df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
        df['weekday'] = df['datetime'].dt.day_name()
        df['weekday_vi'] = df['weekday'].map({
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
        })
        df['week'] = df['datetime'].dt.isocalendar().week
        
        # Đảm bảo cột meeting_schedules tồn tại
        if 'meeting_schedules' not in df.columns:
            df['meeting_schedules'] = 0
            
        # Phân loại mức độ bận rộn
        df['meeting_level'] = df['meeting_schedules'].apply(lambda x: 
            'Rất ít' if x <= 2 else
            'Ít' if x <= 5 else
            'Trung bình' if x <= 10 else
            'Nhiều' if x <= 20 else
            'Rất nhiều'
        )
        
        # Tính số ngày làm việc/cuối tuần
        df['is_weekend'] = df['weekday'].isin(['Saturday', 'Sunday'])
        df['day_type'] = df['is_weekend'].map({False: 'Ngày làm việc', True: 'Cuối tuần'})
        
        return df
    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu lịch họp: {str(e)}")
        return None

# Hàm tạo pivot table cho quản lý công việc
def create_task_pivot_table(df_all, df_detail):
    st.markdown("### 📊 Bảng Pivot - Phân tích công việc theo thời gian")
    
    # Lựa chọn mức độ tổng hợp và loại dữ liệu
    col1, col2 = st.columns(2)
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Ngày', 'Tuần', 'Tháng', 'Quý', 'Năm'],
            index=1,  # Mặc định là Tuần
            key="task_period"
        )
    
    with col2:
        data_type = st.selectbox(
            "📋 Dữ liệu:",
            options=['Tổng hợp', 'Chi tiết phòng ban'],
            index=0,
            key="task_data_type"
        )
    
    # Chọn DataFrame phù hợp
    df = df_all if data_type == 'Tổng hợp' else df_detail
    
    # Chuẩn bị dữ liệu theo loại period
    df_period = df.copy()
    
    if period_type == 'Tuần':
        df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
    elif period_type == 'Tháng':
        df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    elif period_type == 'Quý':
        df_period['quarter'] = ((df_period['month'] - 1) // 3) + 1
        df_period['period'] = 'Q' + df_period['quarter'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['quarter']
    elif period_type == 'Năm':
        df_period['period'] = df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year']
    else:  # Ngày
        df_period['period'] = df_period['datetime'].dt.strftime('%d/%m/%Y')
        df_period['period_sort'] = df_period['datetime']
    
    # Groupby columns
    group_cols = ['period', 'period_sort']
    if data_type == 'Chi tiết phòng ban':
        group_cols.append('department')
    
    # Tạo pivot table
    pivot_columns = ['tasks_assigned', 'tasks_completed_on_time', 'tasks_new', 'tasks_processing']
    
    pivot_data = df_period.groupby(group_cols)[pivot_columns].sum().reset_index()
    pivot_data = pivot_data.sort_values('period_sort', ascending=False)
    
    # Tính lại các tỷ lệ sau khi group
    pivot_data['completion_rate'] = (pivot_data['tasks_completed_on_time'] / pivot_data['tasks_assigned'] * 100).fillna(0)
    pivot_data['processing_rate'] = (pivot_data['tasks_processing'] / pivot_data['tasks_assigned'] * 100).fillna(0)
    pivot_data['new_rate'] = (pivot_data['tasks_new'] / pivot_data['tasks_assigned'] * 100).fillna(0)
    
    # Tính toán biến động so với kỳ trước
    if data_type == 'Tổng hợp':
        for col in pivot_columns + ['completion_rate']:
            pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
            pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
            if col != 'completion_rate':
                pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
            else:
                pivot_data[f'{col}_change_pct'] = (pivot_data[col] - pivot_data[f'{col}_prev']).round(1)
            pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)
    
    st.markdown(f"#### 📋 Tổng hợp theo {period_type} - {data_type}")

    if data_type == 'Tổng hợp':
        # Hàm format cell với biến động (giống như document modules)
        def format_cell_with_change(row, col):
            current_val = row[col]
            change_val = row[f'{col}_change']
            change_pct = row[f'{col}_change_pct']
            prev_val = row[f'{col}_prev']

            if pd.isna(prev_val) or (col != 'completion_rate' and prev_val == 0):
                if col == 'completion_rate':
                    return f"{current_val:.1f}%"
                else:
                    return f"{int(current_val)}"

            if change_val > 0:
                color = "#28a745"
                arrow = "↗"
                sign = "+"
            elif change_val < 0:
                color = "#dc3545"
                arrow = "↘"
                sign = ""
            else:
                color = "#6c757d"
                arrow = "→"
                sign = ""

            if col == 'completion_rate':
                return f"""<div style="text-align: center; line-height: 1.2;">
                    <div style="font-size: 16px; font-weight: 600;">{current_val:.1f}%</div>
                    <div style="color: {color}; font-weight: 600; font-size: 12px; margin-top: 2px;">
                        {arrow} {sign}{change_val:.1f}%
                    </div>
                </div>"""
            else:
                return f"""<div style="text-align: center; line-height: 1.2;">
                    <div style="font-size: 16px; font-weight: 600;">{int(current_val)}</div>
                    <div style="color: {color}; font-weight: 600; font-size: 12px; margin-top: 2px;">
                        {arrow} {sign}{int(change_val)} ({change_pct:+.1f}%)
                    </div>
                </div>"""

        # Tạo DataFrame hiển thị với biến động trong cùng cell
        display_data = pivot_data.copy()
        display_columns = ['period']
        column_names = {f'period': f'{period_type}'}

        # Tạo cột hiển thị mới cho từng metric
        task_columns = ['tasks_assigned', 'tasks_completed_on_time', 'tasks_new', 'tasks_processing', 'completion_rate']
        task_names = ['Giao việc', 'Hoàn thành', 'Việc mới', 'Đang xử lý', 'Tỷ lệ hoàn thành']

        for i, col in enumerate(task_columns):
            new_col = f'{col}_display'
            display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
            display_columns.append(new_col)
            column_names[new_col] = task_names[i]

        # Hiển thị bảng với HTML để render màu sắc (giống như document modules)
        df_display = display_data[display_columns].rename(columns=column_names)

        # Tạo HTML table với sticky header (giống hệt document modules)
        html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

        # Header với sticky positioning
        html_table += "<thead><tr>"
        for col in df_display.columns:
            html_table += f"<th style='position: sticky; top: 0; padding: 15px 8px; text-align: center; background-color: #f0f2f6; font-weight: bold; font-size: 17px; border: 1px solid #ddd; z-index: 10;'>{col}</th>"
        html_table += "</tr></thead>"

        # Body
        html_table += "<tbody>"
        for _, row in df_display.iterrows():
            html_table += "<tr>"
            for i, col in enumerate(df_display.columns):
                cell_value = row[col]
                style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd; vertical-align: middle;"
                if i == 0:  # Period column
                    style += " font-weight: 600; background-color: #f8f9fa;"
                html_table += f"<td style='{style}'>{cell_value}</td>"
            html_table += "</tr>"
        html_table += "</tbody></table></div>"

        st.markdown(html_table, unsafe_allow_html=True)
    else:
        # Hiển thị bình thường cho chi tiết phòng ban
        display_columns = group_cols + pivot_columns + ['completion_rate']
        rename_dict = {
            'period': f'{period_type}',
            'department': 'Phòng ban',
            'tasks_assigned': 'Giao việc',
            'tasks_completed_on_time': 'Hoàn thành đúng hạn',
            'tasks_new': 'Việc mới',
            'tasks_processing': 'Đang xử lý',
            'completion_rate': 'Tỷ lệ hoàn thành (%)'
        }

        display_df = pivot_data[display_columns].copy()
        display_df['completion_rate'] = display_df['completion_rate'].round(1)
        st.dataframe(display_df.rename(columns=rename_dict), use_container_width=True)

    return period_type

# Hàm tạo biểu đồ cho quản lý công việc
def create_task_management_charts(df_all, df_detail, period_type='Tuần'):
    # Chart tổng số lượng công việc theo phòng ban trước
    if len(df_detail) > 0:
        st.markdown("#### 📊 Tổng số lượng công việc theo phòng ban")

        dept_summary = df_detail.groupby('department').agg({
            'tasks_assigned': 'sum',
            'tasks_completed_on_time': 'sum',
            'tasks_processing': 'sum',
            'tasks_new': 'sum'
        }).reset_index()

        # Tính số công việc chưa hoàn thành (bao gồm đang xử lý + mới)
        dept_summary['tasks_incomplete'] = dept_summary['tasks_processing'] + dept_summary['tasks_new']

        # Sắp xếp theo tổng số công việc (từ nhiều nhất đến ít nhất)
        dept_summary = dept_summary.sort_values('tasks_assigned', ascending=False)

        # Hiển thị tất cả phòng ban với chiều cao động
        dept_display = dept_summary.iloc[::-1]  # Reverse để chart hiển thị đúng thứ tự

        # Tạo chart với tất cả dữ liệu
        fig_dept_full = go.Figure()

        # Thêm cột hoàn thành (xanh)
        fig_dept_full.add_trace(go.Bar(
            name='Hoàn thành',
            y=dept_display['department'],
            x=dept_display['tasks_completed_on_time'],
            orientation='h',
            marker_color='#28a745'
        ))

        # Thêm cột chưa hoàn thành (đỏ)
        fig_dept_full.add_trace(go.Bar(
            name='Chưa hoàn thành',
            y=dept_display['department'],
            x=dept_display['tasks_incomplete'],
            orientation='h',
            marker_color='#dc3545'
        ))

        # Cấu hình layout với chiều cao đầy đủ để hiển thị tất cả phòng ban
        fig_dept_full.update_layout(
            title=f'📊 Tổng số lượng công việc theo phòng ban (Tất cả {len(dept_summary)} phòng ban)',
            xaxis_title="Số lượng",
            yaxis_title="",
            barmode='stack',
            showlegend=True,
            height=max(500, len(dept_summary) * 25 + 100),  # Dynamic height với minimum 500px
            margin=dict(l=150, r=30, t=60, b=30)  # Tăng left margin để hiển thị tên phòng ban dài
        )

        st.plotly_chart(fig_dept_full, use_container_width=True)

        # Thêm bảng chi tiết phòng ban
        with st.expander(f"📋 Chi tiết tất cả {len(dept_summary)} phòng ban"):
            dept_display_table = dept_summary.copy()
            dept_display_table['completion_rate'] = (dept_display_table['tasks_completed_on_time'] / dept_display_table['tasks_assigned'] * 100).round(1)

            st.dataframe(
                dept_display_table[['department', 'tasks_assigned', 'tasks_completed_on_time', 'tasks_processing', 'tasks_new', 'completion_rate']].rename(columns={
                    'department': 'Phòng ban',
                    'tasks_assigned': 'Tổng giao việc',
                    'tasks_completed_on_time': 'Hoàn thành',
                    'tasks_processing': 'Đang xử lý',
                    'tasks_new': 'Việc mới',
                    'completion_rate': 'Tỷ lệ hoàn thành (%)'
                }),
                use_container_width=True
            )

        st.markdown("---")

    # Biểu đồ cumulative lớn
    st.markdown("#### 📈 Xu hướng tích lũy tất cả các công việc")

    # Sắp xếp theo thời gian và tính cumulative
    df_all_sorted = df_all.sort_values('datetime').reset_index(drop=True)

    # Tính toán cộng dồn
    df_all_sorted['cumulative_assigned'] = df_all_sorted['tasks_assigned'].cumsum()
    df_all_sorted['cumulative_completed'] = df_all_sorted['tasks_completed_on_time'].cumsum()
    df_all_sorted['cumulative_processing'] = df_all_sorted['tasks_processing'].cumsum()
    df_all_sorted['cumulative_new'] = df_all_sorted['tasks_new'].cumsum()

    # Biểu đồ cumulative lớn
    fig_cumulative = go.Figure()

    # Thêm các đường cumulative
    fig_cumulative.add_trace(go.Scatter(
        x=df_all_sorted['datetime'],
        y=df_all_sorted['cumulative_assigned'],
        mode='lines+markers',
        name='📋 Tổng giao việc',
        line=dict(color='#1f77b4', width=4),
        marker=dict(size=10)
    ))

    fig_cumulative.add_trace(go.Scatter(
        x=df_all_sorted['datetime'],
        y=df_all_sorted['cumulative_completed'],
        mode='lines+markers',
        name='✅ Tổng đã hoàn thành',
        line=dict(color='#28a745', width=4),
        marker=dict(size=10)
    ))

    fig_cumulative.add_trace(go.Scatter(
        x=df_all_sorted['datetime'],
        y=df_all_sorted['cumulative_processing'],
        mode='lines+markers',
        name='🔄 Tổng đang xử lý',
        line=dict(color='#fd7e14', width=3),
        marker=dict(size=8)
    ))

    fig_cumulative.add_trace(go.Scatter(
        x=df_all_sorted['datetime'],
        y=df_all_sorted['cumulative_new'],
        mode='lines+markers',
        name='🆕 Tổng việc mới',
        line=dict(color='#dc3545', width=3),
        marker=dict(size=8)
    ))

    fig_cumulative.update_layout(
        title='📊 Tích lũy tất cả công việc theo thời gian',
        xaxis_title="Thời gian",
        yaxis_title="Số lượng tích lũy",
        hovermode='x unified',
        height=500,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        )
    )

    st.plotly_chart(fig_cumulative, use_container_width=True)

    st.markdown("---")

    # Các biểu đồ chi tiết
    col1, col2 = st.columns(2)

    # Chuẩn bị dữ liệu theo period_type cho cả 2 cột
    df_chart = df_all.copy()

    # Tạo period theo lựa chọn
    if period_type == 'Tuần':
        df_chart['period'] = 'W' + df_chart['week'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['week']
        chart_title_base = 'theo tuần'
        x_title = "Tuần"
    elif period_type == 'Tháng':
        df_chart['period'] = 'T' + df_chart['month'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['month']
        chart_title_base = 'theo tháng'
        x_title = "Tháng"
    elif period_type == 'Quý':
        df_chart['quarter'] = ((df_chart['month'] - 1) // 3) + 1
        df_chart['period'] = 'Q' + df_chart['quarter'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['quarter']
        chart_title_base = 'theo quý'
        x_title = "Quý"
    elif period_type == 'Năm':
        df_chart['period'] = df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year']
        chart_title_base = 'theo năm'
        x_title = "Năm"
    else:  # Ngày
        df_chart['period'] = df_chart['datetime'].dt.strftime('%d/%m/%Y')
        df_chart['period_sort'] = df_chart['datetime']
        chart_title_base = 'theo ngày'
        x_title = "Ngày"

    # Group data theo period
    period_data = df_chart.groupby(['period', 'period_sort']).agg({
        'tasks_assigned': 'sum',
        'tasks_completed_on_time': 'sum',
        'tasks_processing': 'sum',
        'tasks_new': 'sum'
    }).reset_index()
    period_data = period_data.sort_values('period_sort')

    with col1:
        # Chart 1: Chỉ hiển thị Giao việc
        fig_assigned = go.Figure()

        fig_assigned.add_trace(go.Scatter(
            x=period_data['period'],
            y=period_data['tasks_assigned'],
            mode='lines+markers',
            name='Giao việc',
            line=dict(color='#1f77b4', width=4),
            marker=dict(size=10)
        ))

        # Thêm đường xu hướng cho giao việc
        if len(period_data) >= 3:
            ma_window = min(3, len(period_data)//2)
            if ma_window > 0:
                ma_trend = period_data['tasks_assigned'].rolling(window=ma_window, center=True).mean()
                fig_assigned.add_trace(go.Scatter(
                    x=period_data['period'],
                    y=ma_trend,
                    mode='lines',
                    name='Xu hướng',
                    line=dict(color='#1f77b4', width=2, dash='dash'),
                    opacity=0.7,
                    showlegend=False
                ))

        fig_assigned.update_layout(
            title=f'📋 Giao việc {chart_title_base}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_assigned, use_container_width=True)

    with col2:
        # Chart 2: Hoàn thành, Đang xử lý, Việc mới
        fig_status = go.Figure()

        # Thêm các đường cho các loại công việc (trừ giao việc)
        status_data = [
            ('tasks_completed_on_time', 'Hoàn thành', '#28a745'),
            ('tasks_processing', 'Đang xử lý', '#fd7e14'),
            ('tasks_new', 'Việc mới', '#dc3545')
        ]

        for col_name, name, color in status_data:
            fig_status.add_trace(go.Scatter(
                x=period_data['period'],
                y=period_data[col_name],
                mode='lines+markers',
                name=name,
                line=dict(color=color, width=3),
                marker=dict(size=8)
            ))

            # Thêm đường xu hướng
            if len(period_data) >= 3:
                ma_window = min(3, len(period_data)//2)
                if ma_window > 0:
                    ma_trend = period_data[col_name].rolling(window=ma_window, center=True).mean()
                    fig_status.add_trace(go.Scatter(
                        x=period_data['period'],
                        y=ma_trend,
                        mode='lines',
                        name=f'{name} - Xu hướng',
                        line=dict(color=color, width=2, dash='dash'),
                        opacity=0.7,
                        showlegend=False
                    ))

        fig_status.update_layout(
            title=f'📊 Trạng thái công việc {chart_title_base}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_status, use_container_width=True)

    # Hàng 2: 2 charts bổ sung
    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        # Chart 3: Tỷ lệ hoàn thành
        period_data['completion_rate'] = (period_data['tasks_completed_on_time'] / period_data['tasks_assigned'] * 100).fillna(0)

        fig_completion = go.Figure()
        fig_completion.add_trace(go.Scatter(
            x=period_data['period'],
            y=period_data['completion_rate'],
            mode='lines+markers',
            name='Tỷ lệ hoàn thành',
            line=dict(color='purple', width=3),
            marker=dict(size=8)
        ))

        # Thêm đường xu hướng cho tỷ lệ hoàn thành
        if len(period_data) >= 3:
            ma_window = min(3, len(period_data)//2)
            if ma_window > 0:
                ma_trend = period_data['completion_rate'].rolling(window=ma_window, center=True).mean()
                fig_completion.add_trace(go.Scatter(
                    x=period_data['period'],
                    y=ma_trend,
                    mode='lines',
                    name='Xu hướng tỷ lệ',
                    line=dict(color='purple', width=2, dash='dash'),
                    opacity=0.7,
                    showlegend=False
                ))

        fig_completion.update_layout(
            title=f'📊 Tỷ lệ hoàn thành {chart_title_base}',
            xaxis_title=x_title,
            yaxis_title="Tỷ lệ (%)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_completion, use_container_width=True)

    with col4:
        # Chart 4: Pie chart tổng hợp trạng thái
        total_completed = period_data['tasks_completed_on_time'].sum()
        total_processing = period_data['tasks_processing'].sum()
        total_new = period_data['tasks_new'].sum()

        # Chỉ hiển thị các trạng thái có giá trị > 0
        status_data = []
        status_values = []
        status_colors = []

        if total_completed > 0:
            status_data.append('Hoàn thành')
            status_values.append(total_completed)
            status_colors.append('#28a745')  # Xanh

        if total_processing > 0:
            status_data.append('Đang xử lý')
            status_values.append(total_processing)
            status_colors.append('#fd7e14')  # Cam

        if total_new > 0:
            status_data.append('Việc mới')
            status_values.append(total_new)
            status_colors.append('#dc3545')  # Đỏ

        if status_values:  # Chỉ vẽ nếu có dữ liệu
            fig_pie = go.Figure(data=[go.Pie(
                labels=status_data,
                values=status_values,
                hole=0.4,
                marker_colors=status_colors,
                textinfo='label+value+percent',
                textposition='auto'
            )])

            fig_pie.update_layout(
                title='📋 Tổng hợp trạng thái công việc',
                showlegend=True,
                legend=dict(orientation="v", yanchor="middle", y=0.5),
                height=400
            )

            st.plotly_chart(fig_pie, use_container_width=True)

        else:
            st.info("📋 Không có dữ liệu trạng thái công việc")

# Hàm tạo pivot table cho lịch họp
def create_meeting_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích lịch họp theo thời gian")

    # Lựa chọn mức độ tổng hợp
    period_type = st.selectbox(
        "📅 Tổng hợp theo:",
        options=['Ngày', 'Tuần', 'Tháng', 'Quý', 'Năm'],
        index=1,  # Mặc định là Tuần
        key="meeting_period"
    )

    # Chuẩn bị dữ liệu theo loại period
    df_period = df.copy()

    if period_type == 'Tuần':
        df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
    elif period_type == 'Tháng':
        df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    elif period_type == 'Quý':
        df_period['quarter'] = ((df_period['month'] - 1) // 3) + 1
        df_period['period'] = 'Q' + df_period['quarter'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['quarter']
    elif period_type == 'Năm':
        df_period['period'] = df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year']
    else:  # Ngày
        df_period['period'] = df_period['datetime'].dt.strftime('%d/%m/%Y')
        df_period['period_sort'] = df_period['datetime']

    # Tạo pivot table cho meeting data
    pivot_columns = ['meeting_schedules']

    pivot_data = df_period.groupby(['period', 'period_sort'])[pivot_columns].sum().reset_index()
    pivot_data = pivot_data.sort_values('period_sort', ascending=False)

    # Tính tỷ lệ ngày bận rộn (>5 cuộc họp)
    busy_days = df_period.groupby(['period', 'period_sort']).apply(
        lambda x: (x['meeting_schedules'] > 5).sum()
    ).reset_index(name='busy_days')

    total_days = df_period.groupby(['period', 'period_sort']).size().reset_index(name='total_days')

    pivot_data = pivot_data.merge(busy_days, on=['period', 'period_sort'])
    pivot_data = pivot_data.merge(total_days, on=['period', 'period_sort'])

    pivot_data['busy_rate'] = (pivot_data['busy_days'] / pivot_data['total_days'] * 100).fillna(0)

    # Tính toán biến động so với kỳ trước
    for col in ['meeting_schedules', 'busy_days', 'busy_rate']:
        pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
        pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
        if col not in ['busy_rate']:
            pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
        else:
            pivot_data[f'{col}_change_pct'] = (pivot_data[col] - pivot_data[f'{col}_prev']).round(1)
        pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

    st.markdown(f"#### 📋 Tổng hợp theo {period_type}")

    # Hàm format cell với biến động (giống như task management)
    def format_cell_with_change(row, col):
        current_val = row[col]
        change_val = row[f'{col}_change']
        change_pct = row[f'{col}_change_pct']
        prev_val = row[f'{col}_prev']

        if pd.isna(prev_val) or (col not in ['busy_rate'] and prev_val == 0):
            if col == 'busy_rate':
                return f"{current_val:.1f}%"
            else:
                return f"{int(current_val)}"

        if change_val > 0:
            color = "#28a745"
            arrow = "↗"
            sign = "+"
        elif change_val < 0:
            color = "#dc3545"
            arrow = "↘"
            sign = ""
        else:
            color = "#6c757d"
            arrow = "→"
            sign = ""

        if col == 'busy_rate':
            return f"""<div style="text-align: center; line-height: 1.2;">
                <div style="font-size: 16px; font-weight: 600;">{current_val:.1f}%</div>
                <div style="color: {color}; font-weight: 600; font-size: 12px; margin-top: 2px;">
                    {arrow} {sign}{change_val:.1f}%
                </div>
            </div>"""
        else:
            return f"""<div style="text-align: center; line-height: 1.2;">
                <div style="font-size: 16px; font-weight: 600;">{int(current_val)}</div>
                <div style="color: {color}; font-weight: 600; font-size: 12px; margin-top: 2px;">
                    {arrow} {sign}{int(change_val)} ({change_pct:+.1f}%)
                </div>
            </div>"""

    # Tạo DataFrame hiển thị với biến động trong cùng cell
    display_data = pivot_data.copy()
    display_columns = ['period']
    column_names = {f'period': f'{period_type}'}

    # Tạo cột hiển thị mới cho từng metric
    meeting_columns = ['meeting_schedules', 'busy_days', 'busy_rate']
    meeting_names = ['Tổng cuộc họp', 'Ngày bận rộn', 'Tỷ lệ ngày bận (%)']

    for i, col in enumerate(meeting_columns):
        new_col = f'{col}_display'
        display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
        display_columns.append(new_col)
        column_names[new_col] = meeting_names[i]

    # Hiển thị bảng với HTML để render màu sắc (giống như task management)
    df_display = display_data[display_columns].rename(columns=column_names)

    # Tạo HTML table với sticky header (giống hệt task management)
    html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

    # Header với sticky positioning
    html_table += "<thead><tr>"
    for col in df_display.columns:
        html_table += f"<th style='position: sticky; top: 0; padding: 15px 8px; text-align: center; background-color: #f0f2f6; font-weight: bold; font-size: 17px; border: 1px solid #ddd; z-index: 10;'>{col}</th>"
    html_table += "</tr></thead>"

    # Body
    html_table += "<tbody>"
    for _, row in df_display.iterrows():
        html_table += "<tr>"
        for i, col in enumerate(df_display.columns):
            cell_value = row[col]
            style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd; vertical-align: middle;"
            if i == 0:  # Period column
                style += " font-weight: 600; background-color: #f8f9fa;"
            html_table += f"<td style='{style}'>{cell_value}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table></div>"

    st.markdown(html_table, unsafe_allow_html=True)

    return period_type

# Hàm tạo pivot table cho quản lý phòng họp
def create_room_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích đăng ký phòng họp theo thời gian")

    # Lựa chọn mức độ tổng hợp
    period_type = st.selectbox(
        "📅 Tổng hợp theo:",
        options=['Ngày', 'Tuần', 'Tháng', 'Quý', 'Năm'],
        index=1,  # Mặc định là Tuần
        key="room_period"
    )

    # Chuẩn bị dữ liệu theo loại period
    df_period = df.copy()
    df_period['year'] = df_period['datetime'].dt.year
    df_period['month'] = df_period['datetime'].dt.month
    df_period['week'] = df_period['datetime'].dt.isocalendar().week

    if period_type == 'Tuần':
        df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
    elif period_type == 'Tháng':
        df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    elif period_type == 'Quý':
        df_period['quarter'] = ((df_period['month'] - 1) // 3) + 1
        df_period['period'] = 'Q' + df_period['quarter'].astype(str) + '-' + df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year'] * 100 + df_period['quarter']
    elif period_type == 'Năm':
        df_period['period'] = df_period['year'].astype(str)
        df_period['period_sort'] = df_period['year']
    else:  # Ngày
        df_period['period'] = df_period['datetime'].dt.strftime('%d/%m/%Y')
        df_period['period_sort'] = df_period['datetime']

    # Tạo pivot table cho room data
    pivot_data = df_period.groupby(['period', 'period_sort']).agg({
        'register_room': 'sum',
        'register_room_cancel': 'sum',
        'net_bookings': 'sum'
    }).reset_index()
    pivot_data = pivot_data.sort_values('period_sort', ascending=False)

    # Tính tỷ lệ hủy
    pivot_data['cancel_rate'] = (pivot_data['register_room_cancel'] / pivot_data['register_room'] * 100).fillna(0)

    # Tính toán biến động so với kỳ trước
    for col in ['register_room', 'register_room_cancel', 'net_bookings', 'cancel_rate']:
        pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
        pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
        if col not in ['cancel_rate']:
            pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
        else:
            pivot_data[f'{col}_change_pct'] = (pivot_data[col] - pivot_data[f'{col}_prev']).round(1)
        pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

    st.markdown(f"#### 📋 Tổng hợp theo {period_type}")

    # Hàm format cell với biến động
    def format_cell_with_change(row, col):
        current_val = row[col]
        change_val = row[f'{col}_change']
        change_pct = row[f'{col}_change_pct']
        prev_val = row[f'{col}_prev']

        if pd.isna(prev_val) or (col not in ['cancel_rate'] and prev_val == 0):
            if col == 'cancel_rate':
                return f"{current_val:.1f}%"
            else:
                return f"{int(current_val)}"

        if change_val > 0:
            color = "#28a745"
            arrow = "↗"
            sign = "+"
        elif change_val < 0:
            color = "#dc3545"
            arrow = "↘"
            sign = ""
        else:
            color = "#6c757d"
            arrow = "→"
            sign = ""

        if col == 'cancel_rate':
            return f"""<div style="text-align: center; line-height: 1.2;">
                <div style="font-size: 16px; font-weight: 600;">{current_val:.1f}%</div>
                <div style="color: {color}; font-weight: 600; font-size: 12px; margin-top: 2px;">
                    {arrow} {sign}{change_val:.1f}%
                </div>
            </div>"""
        else:
            return f"""<div style="text-align: center; line-height: 1.2;">
                <div style="font-size: 16px; font-weight: 600;">{int(current_val)}</div>
                <div style="color: {color}; font-weight: 600; font-size: 12px; margin-top: 2px;">
                    {arrow} {sign}{int(change_val)} ({change_pct:+.1f}%)
                </div>
            </div>"""

    # Tạo DataFrame hiển thị với biến động trong cùng cell
    display_data = pivot_data.copy()
    display_columns = ['period']
    column_names = {f'period': f'{period_type}'}

    # Tạo cột hiển thị mới cho từng metric
    room_columns = ['register_room', 'register_room_cancel', 'net_bookings', 'cancel_rate']
    room_names = ['Tổng đăng ký', 'Tổng hủy', 'Đăng ký thực', 'Tỷ lệ hủy (%)']

    for i, col in enumerate(room_columns):
        new_col = f'{col}_display'
        display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
        display_columns.append(new_col)
        column_names[new_col] = room_names[i]

    # Hiển thị bảng với HTML để render màu sắc
    df_display = display_data[display_columns].rename(columns=column_names)

    # Tạo HTML table với sticky header
    html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

    # Header với sticky positioning
    html_table += "<thead><tr>"
    for col in df_display.columns:
        html_table += f"<th style='position: sticky; top: 0; padding: 15px 8px; text-align: center; background-color: #f0f2f6; font-weight: bold; font-size: 17px; border: 1px solid #ddd; z-index: 10;'>{col}</th>"
    html_table += "</tr></thead>"

    # Body
    html_table += "<tbody>"
    for _, row in df_display.iterrows():
        html_table += "<tr>"
        for i, col in enumerate(df_display.columns):
            cell_value = row[col]
            style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd; vertical-align: middle;"
            if i == 0:  # Period column
                style += " font-weight: 600; background-color: #f8f9fa;"
            html_table += f"<td style='{style}'>{cell_value}</td>"
        html_table += "</tr>"
    html_table += "</tbody></table></div>"

    st.markdown(html_table, unsafe_allow_html=True)

    return period_type

# Hàm tạo biểu đồ cho quản lý phòng họp
def create_room_charts(df, period_type='Tuần'):
    # Các biểu đồ chi tiết
    col1, col2 = st.columns(2)
    # Chuẩn bị dữ liệu theo period_type
    df_chart = df.copy()

    # Thêm các cột cần thiết
    df_chart['year'] = df_chart['datetime'].dt.year
    df_chart['month'] = df_chart['datetime'].dt.month
    df_chart['week'] = df_chart['datetime'].dt.isocalendar().week

    # Tạo period theo lựa chọn
    if period_type == 'Tuần':
        df_chart['period'] = 'W' + df_chart['week'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['week']
        chart_title_base = 'theo tuần'
        x_title = "Tuần"
    elif period_type == 'Tháng':
        df_chart['period'] = 'T' + df_chart['month'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['month']
        chart_title_base = 'theo tháng'
        x_title = "Tháng"
    elif period_type == 'Quý':
        df_chart['quarter'] = ((df_chart['month'] - 1) // 3) + 1
        df_chart['period'] = 'Q' + df_chart['quarter'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['quarter']
        chart_title_base = 'theo quý'
        x_title = "Quý"
    elif period_type == 'Năm':
        df_chart['period'] = df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year']
        chart_title_base = 'theo năm'
        x_title = "Năm"
    else:  # Ngày
        df_chart['period'] = df_chart['datetime'].dt.strftime('%d/%m/%Y')
        df_chart['period_sort'] = df_chart['datetime']
        chart_title_base = 'theo ngày'
        x_title = "Ngày"

    # Group data theo period
    period_data = df_chart.groupby(['period', 'period_sort']).agg({
        'register_room': 'sum',
        'register_room_cancel': 'sum',
        'net_bookings': 'sum'
    }).reset_index()
    period_data = period_data.sort_values('period_sort')
    period_data['cancel_rate'] = (period_data['register_room_cancel'] / period_data['register_room'] * 100).fillna(0)

    with col1:
        # Chart 1: Đăng ký phòng theo period
        fig_bookings = go.Figure()

        fig_bookings.add_trace(go.Scatter(
            x=period_data['period'],
            y=period_data['register_room'],
            mode='lines+markers',
            name='Đăng ký',
            line=dict(color='#007bff', width=4),
            marker=dict(size=10)
        ))

        # Thêm đường xu hướng
        if len(period_data) >= 3:
            ma_window = min(3, len(period_data)//2)
            if ma_window > 0:
                ma_trend = period_data['register_room'].rolling(window=ma_window, center=True).mean()
                fig_bookings.add_trace(go.Scatter(
                    x=period_data['period'],
                    y=ma_trend,
                    mode='lines',
                    name='Xu hướng',
                    line=dict(color='#007bff', width=2, dash='dash'),
                    opacity=0.7,
                    showlegend=False
                ))

        fig_bookings.update_layout(
            title=f'🏢 Đăng ký phòng {chart_title_base}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_bookings, use_container_width=True)

    with col2:
        # Chart 2: So sánh đăng ký vs hủy
        fig_compare = go.Figure()

        fig_compare.add_trace(go.Bar(
            x=period_data['period'],
            y=period_data['register_room'],
            name='Đăng ký',
            marker_color='#28a745'
        ))

        fig_compare.add_trace(go.Bar(
            x=period_data['period'],
            y=period_data['register_room_cancel'],
            name='Hủy bỏ',
            marker_color='#dc3545'
        ))

        fig_compare.update_layout(
            title=f'📊 So sánh đăng ký vs hủy {chart_title_base}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig_compare, use_container_width=True)

    # Hàng 2: 2 charts bổ sung
    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        # Chart 3: Tỷ lệ hủy theo period
        fig_cancel_rate = go.Figure()

        fig_cancel_rate.add_trace(go.Scatter(
            x=period_data['period'],
            y=period_data['cancel_rate'],
            mode='lines+markers',
            name='Tỷ lệ hủy',
            line=dict(color='#ffc107', width=4),
            marker=dict(size=10)
        ))

        # Thêm đường xu hướng
        if len(period_data) >= 3:
            ma_window = min(3, len(period_data)//2)
            if ma_window > 0:
                ma_trend_cancel = period_data['cancel_rate'].rolling(window=ma_window, center=True).mean()
                fig_cancel_rate.add_trace(go.Scatter(
                    x=period_data['period'],
                    y=ma_trend_cancel,
                    mode='lines',
                    name='Xu hướng',
                    line=dict(color='#ffc107', width=2, dash='dash'),
                    opacity=0.7,
                    showlegend=False
                ))

        fig_cancel_rate.update_layout(
            title=f'📉 Tỷ lệ hủy {chart_title_base}',
            xaxis_title=x_title,
            yaxis_title="Tỷ lệ (%)",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_cancel_rate, use_container_width=True)

    with col4:
        # Chart 4: Phân bố theo ngày trong tuần
        weekday_summary = df.groupby('weekday_vi').agg({
            'register_room': 'sum',
            'register_room_cancel': 'sum'
        }).reindex([
            'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'
        ]).fillna(0)

        fig_weekday = go.Figure()

        fig_weekday.add_trace(go.Bar(
            name='Đăng ký',
            x=weekday_summary.index,
            y=weekday_summary['register_room'],
            marker_color='#007bff'
        ))

        fig_weekday.add_trace(go.Bar(
            name='Hủy bỏ',
            x=weekday_summary.index,
            y=weekday_summary['register_room_cancel'],
            marker_color='#dc3545'
        ))

        fig_weekday.update_layout(
            title='📅 Phân bố theo ngày trong tuần',
            xaxis_title="Ngày trong tuần",
            yaxis_title="Số lượng",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig_weekday, use_container_width=True)

# Hàm tạo biểu đồ cho lịch họp
def create_meeting_charts(df, period_type='Tuần'):

    # Các biểu đồ chi tiết
    col1, col2 = st.columns(2)
    # Chuẩn bị dữ liệu theo period_type
    df_chart = df.copy()

    # Tạo period theo lựa chọn
    if period_type == 'Tuần':
        df_chart['period'] = 'W' + df_chart['week'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['week']
        chart_title_base = 'theo tuần'
        x_title = "Tuần"
    elif period_type == 'Tháng':
        df_chart['period'] = 'T' + df_chart['month'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['month']
        chart_title_base = 'theo tháng'
        x_title = "Tháng"
    elif period_type == 'Quý':
        df_chart['quarter'] = ((df_chart['month'] - 1) // 3) + 1
        df_chart['period'] = 'Q' + df_chart['quarter'].astype(str) + '-' + df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['quarter']
        chart_title_base = 'theo quý'
        x_title = "Quý"
    elif period_type == 'Năm':
        df_chart['period'] = df_chart['year'].astype(str)
        df_chart['period_sort'] = df_chart['year']
        chart_title_base = 'theo năm'
        x_title = "Năm"
    else:  # Ngày
        df_chart['period'] = df_chart['datetime'].dt.strftime('%d/%m/%Y')
        df_chart['period_sort'] = df_chart['datetime']
        chart_title_base = 'theo ngày'
        x_title = "Ngày"

    # Group data theo period
    period_data = df_chart.groupby(['period', 'period_sort']).agg({
        'meeting_schedules': 'sum'
    }).reset_index()
    period_data = period_data.sort_values('period_sort')

    with col1:
        # Chart 1: Cuộc họp theo period
        fig_meetings = go.Figure()

        fig_meetings.add_trace(go.Scatter(
            x=period_data['period'],
            y=period_data['meeting_schedules'],
            mode='lines+markers',
            name='Cuộc họp',
            line=dict(color='#007bff', width=4),
            marker=dict(size=10)
        ))

        # Thêm đường xu hướng
        if len(period_data) >= 3:
            ma_window = min(3, len(period_data)//2)
            if ma_window > 0:
                ma_trend = period_data['meeting_schedules'].rolling(window=ma_window, center=True).mean()
                fig_meetings.add_trace(go.Scatter(
                    x=period_data['period'],
                    y=ma_trend,
                    mode='lines',
                    name='Xu hướng',
                    line=dict(color='#007bff', width=2, dash='dash'),
                    opacity=0.7,
                    showlegend=False
                ))

        fig_meetings.update_layout(
            title=f'📅 Cuộc họp {chart_title_base}',
            xaxis_title=x_title,
            yaxis_title="Số lượng",
            hovermode='x unified',
            height=400
        )
        st.plotly_chart(fig_meetings, use_container_width=True)

    with col2:
        # Chart 2: Phân bố theo ngày trong tuần
        weekday_summary = df.groupby('weekday_vi')['meeting_schedules'].sum().reindex([
            'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'
        ]).fillna(0)

        colors = ['#28a745' if day in ['Thứ 7', 'Chủ nhật'] else '#007bff' for day in weekday_summary.index]

        fig_weekday = px.bar(
            x=weekday_summary.index,
            y=weekday_summary.values,
            title='📅 Phân bố cuộc họp theo ngày trong tuần',
            color=weekday_summary.index,
            color_discrete_sequence=colors
        )
        fig_weekday.update_layout(
            xaxis_title="Ngày trong tuần",
            yaxis_title="Tổng số cuộc họp",
            showlegend=False,
            height=400
        )
        st.plotly_chart(fig_weekday, use_container_width=True)

    # Hàng 2: 2 charts bổ sung
    st.markdown("---")
    col3, col4 = st.columns(2)

    with col3:
        # Chart 3: Mức độ bận rộn
        level_counts = df['meeting_level'].value_counts()
        level_order = ['Rất ít', 'Ít', 'Trung bình', 'Nhiều', 'Rất nhiều']
        level_counts = level_counts.reindex(level_order).fillna(0)

        colors_level = {'Rất ít': '#28a745', 'Ít': '#6c757d', 'Trung bình': '#ffc107',
                       'Nhiều': '#fd7e14', 'Rất nhiều': '#dc3545'}

        fig_level = px.pie(
            values=level_counts.values,
            names=level_counts.index,
            title='📊 Phân bố mức độ bận rộn',
            color=level_counts.index,
            color_discrete_map=colors_level,
            hole=0.4
        )
        fig_level.update_layout(height=400)
        st.plotly_chart(fig_level, use_container_width=True)

    with col4:
        # Chart 4: So sánh ngày làm việc vs cuối tuần
        day_type_summary = df.groupby('day_type')['meeting_schedules'].agg(['count', 'sum', 'mean']).round(1)

        fig_daytype = go.Figure()
        fig_daytype.add_trace(go.Bar(
            name='Số ngày',
            x=day_type_summary.index,
            y=day_type_summary['count'],
            marker_color='lightblue'
        ))
        fig_daytype.add_trace(go.Bar(
            name='Tổng cuộc họp',
            x=day_type_summary.index,
            y=day_type_summary['sum'],
            marker_color='darkblue'
        ))

        fig_daytype.update_layout(
            title='📊 So sánh ngày làm việc vs cuối tuần',
            xaxis_title="Loại ngày",
            yaxis_title="Số lượng",
            barmode='group',
            height=400
        )
        st.plotly_chart(fig_daytype, use_container_width=True)

# Hàm tạo biểu đồ cho văn bản đến
def create_incoming_docs_charts(df, period_type='Tuần'):
    col1, col2 = st.columns(2)
    
    with col1:
        # Biểu đồ theo period_type được chọn
        df_chart = df.copy()

        # Tạo period theo lựa chọn
        if period_type == 'Tuần':
            df_chart['period'] = 'W' + df_chart['week'].astype(str) + '-' + df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['week']
            chart_title = '📈 Số lượng văn bản đến theo tuần'
            x_title = "Tuần"
        elif period_type == 'Tháng':
            df_chart['period'] = 'T' + df_chart['month'].astype(str) + '-' + df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['month']
            chart_title = '📈 Số lượng văn bản đến theo tháng'
            x_title = "Tháng"
        elif period_type == 'Quý':
            df_chart['quarter'] = ((df_chart['month'] - 1) // 3) + 1
            df_chart['period'] = 'Q' + df_chart['quarter'].astype(str) + '-' + df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year'] * 100 + df_chart['quarter']
            chart_title = '📈 Số lượng văn bản đến theo quý'
            x_title = "Quý"
        elif period_type == 'Năm':
            df_chart['period'] = df_chart['year'].astype(str)
            df_chart['period_sort'] = df_chart['year']
            chart_title = '📈 Số lượng văn bản đến theo năm'
            x_title = "Năm"
        else:  # Ngày
            df_chart['period'] = df_chart['datetime'].dt.strftime('%d/%m/%Y')
            df_chart['period_sort'] = df_chart['datetime']
            chart_title = '📈 Số lượng văn bản đến theo ngày'
            x_title = "Ngày"

        # Group data theo period
        period_data = df_chart.groupby(['period', 'period_sort'])['total_incoming'].sum().reset_index()
        period_data = period_data.sort_values('period_sort')

        # Tạo biểu đồ
        fig_period = go.Figure()

        # Đường biểu đồ chính
        fig_period.add_trace(go.Scatter(
            x=period_data['period'],
            y=period_data['total_incoming'],
            mode='lines+markers',
            name='Văn bản đến',
            line=dict(color='#1f77b4', width=2),
            marker=dict(size=8)
        ))

        # Đường xu hướng (nếu đủ dữ liệu)
        if len(period_data) >= 3:
            ma_window = min(3, len(period_data)//2)
            ma_trend = period_data['total_incoming'].rolling(window=ma_window, center=True).mean()
            fig_period.add_trace(go.Scatter(
                x=period_data['period'],
                y=ma_trend,
                mode='lines',
                name=f'Xu hướng ({ma_window} {period_type.lower()})',
                line=dict(color='red', width=3, dash='dash'),
                opacity=0.8
            ))

        fig_period.update_layout(
            title=f'{chart_title} (có xu hướng)',
            xaxis_title=x_title,
            yaxis_title="Số lượng văn bản",
            hovermode='x unified'
        )
        st.plotly_chart(fig_period, use_container_width=True)
        
        # Biểu đồ tỷ lệ xử lý đúng hạn vs trễ hạn theo period_type
        # Tính lại processed data theo period
        processed_summary = df_chart.groupby(['period', 'period_sort']).agg({
            'processed_on_time': 'sum',
            'processed_late': 'sum'
        }).reset_index()
        processed_summary = processed_summary.sort_values('period_sort')

        fig_processed = go.Figure()
        fig_processed.add_trace(go.Scatter(x=processed_summary['period'],
                                         y=processed_summary['processed_on_time'],
                                         mode='lines+markers', name='Đúng hạn',
                                         line=dict(color='green')))
        fig_processed.add_trace(go.Scatter(x=processed_summary['period'],
                                         y=processed_summary['processed_late'],
                                         mode='lines+markers', name='Trễ hạn',
                                         line=dict(color='red')))
        fig_processed.update_layout(title=f'⏰ Tình hình xử lý văn bản theo {period_type.lower()}',
                                  xaxis_title=x_title, yaxis_title="Số lượng")
        st.plotly_chart(fig_processed, use_container_width=True)
    
    with col2:
        # Biểu đồ phân bố theo đơn vị gửi
        def extract_sender_name(x):
            try:
                if isinstance(x, dict):
                    return x.get('send_name', 'Khác')
                elif isinstance(x, str):
                    import json
                    parsed = json.loads(x)
                    return parsed.get('send_name', 'Khác')
                else:
                    return 'Khác'
            except:
                return 'Khác'

        sender_data = df['total_incoming_detail'].apply(extract_sender_name).value_counts()
        fig_sender = px.pie(values=sender_data.values, names=sender_data.index,
                           title='🏛️ Phân bố theo đơn vị gửi')
        st.plotly_chart(fig_sender, use_container_width=True)

        # Biểu đồ top đơn vị gửi theo period_type
        try:
            # Tạo DataFrame với sender cho từng period
            df_chart['sender'] = df_chart['total_incoming_detail'].apply(extract_sender_name)

            # Tìm top 5 senders tổng thể
            top_senders = df_chart['sender'].value_counts().head(5).index.tolist()

            if len(top_senders) > 0:
                fig_sender_trend = go.Figure()

                for sender in top_senders:
                    # Đếm số văn bản từ sender này theo period
                    sender_data = df_chart[df_chart['sender'] == sender].groupby(['period', 'period_sort']).size().reset_index(name='count')
                    sender_data = sender_data.sort_values('period_sort')

                    # Đảm bảo tất cả periods đều có dữ liệu (fill missing với 0)
                    all_periods = period_data[['period', 'period_sort']].drop_duplicates()
                    sender_data = all_periods.merge(sender_data, on=['period', 'period_sort'], how='left')
                    sender_data['count'] = sender_data['count'].fillna(0)

                    fig_sender_trend.add_trace(go.Bar(
                        name=sender,
                        x=sender_data['period'],
                        y=sender_data['count']
                    ))

                fig_sender_trend.update_layout(
                    title=f'📊 Top 5 đơn vị gửi theo {period_type.lower()}',
                    xaxis_title=x_title,
                    yaxis_title="Số lượng văn bản",
                    barmode='stack'
                )
                st.plotly_chart(fig_sender_trend, use_container_width=True)
            else:
                st.info(f"Không có dữ liệu đơn vị gửi theo {period_type.lower()}")
        except Exception as e:
            st.error(f"Lỗi khi tạo biểu đồ đơn vị gửi: {str(e)}")
            st.info("Hiển thị biểu đồ đơn vị gửi đơn giản thay thế")

            # Fallback - biểu đồ đơn giản hơn
            if 'total_incoming_detail' in df.columns:
                simple_sender_data = df['total_incoming_detail'].apply(extract_sender_name).value_counts().head(5)
                fig_simple = px.bar(
                    x=simple_sender_data.index,
                    y=simple_sender_data.values,
                    title='📊 Top 5 đơn vị gửi (tổng hợp)',
                    labels={'x': 'Đơn vị', 'y': 'Số lượng văn bản'}
                )
                st.plotly_chart(fig_simple, use_container_width=True)

# Tạo tabs
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🏠 Tổng quan", 
    "📥 Văn bản đến", 
    "📤 Văn bản đi", 
    "📋 Quản lý công việc", 
    "📅 Quản lý lịch họp", 
    "🏢 Quản lý phòng họp"
])

# Tab 1: Tổng quan
with tab1:
    st.markdown('<div class="tab-header">📊 Tổng quan Phòng Hành chính</div>', unsafe_allow_html=True)
    
    def load_summary_data():
        """Load dữ liệu tổng hợp từ tonghop.json"""
        try:
            with open('tonghop.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data['data'])
                
                # Tạo cột datetime
                df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
                
                # Chuẩn hóa category names
                df['category_clean'] = df['category'].str.replace(' ', '_').str.lower()
                df['category_vi'] = df['category'].map({
                    'Van ban den': '📥 Văn bản đến',
                    'Van ban phat hanh di': '📤 Văn bản đi', 
                    'Van ban phat hanh quyet dinh': '📜 Quyết định',
                    'Van ban phat hanhquy dinh': '📋 Quy định',
                    'Van ban phat hanhquy trinh': '📋 Quy trình',
                    'Van ban phat hanh hop dong': '📝 Hợp đồng',
                    'Quan ly phong hop': '🏢 Phòng họp',
                    'Quan ly cong viec': '💼 Công việc'
                }).fillna('🔸 ' + df['category'])
                
                return df
        except Exception as e:
            st.error(f"Lỗi khi load dữ liệu tổng hợp: {e}")
            return None
    
    # Load dữ liệu
    df_summary = load_summary_data()
    
    if df_summary is not None:
        # Áp dụng global filter
        df_summary = apply_global_filter(df_summary)
        
        # Tính toán metrics tổng quan
        categories_summary = df_summary.groupby('category_vi')['count'].sum().sort_values(ascending=False)
        total_items = df_summary['count'].sum()
        
        # Metrics tổng quan
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            vb_den = categories_summary.get('📥 Văn bản đến', 0)
            st.metric("📥 Văn bản đến", vb_den)
        
        with col2:
            vb_di = categories_summary.get('📤 Văn bản đi', 0)
            st.metric("📤 Văn bản đi", vb_di)
        
        with col3:
            phong_hop = categories_summary.get('🏢 Phòng họp', 0)
            st.metric("🏢 Cuộc họp", phong_hop)
        
        with col4:
            hop_dong = categories_summary.get('📝 Hợp đồng', 0)
            quyet_dinh = categories_summary.get('📜 Quyết định', 0)
            st.metric("📜 QĐ + HĐ", hop_dong + quyet_dinh)
        
        st.markdown("---")
        
        # Biểu đồ tổng quan
        col1, col2 = st.columns(2)
        
        with col1:
            # Biểu đồ xu hướng theo thời gian
            daily_summary = df_summary.groupby(['datetime', 'category_vi'])['count'].sum().reset_index()
            
            fig_trend = px.line(daily_summary, x='datetime', y='count', color='category_vi',
                               title='📈 Xu hướng hoạt động theo thời gian',
                               labels={'count': 'Số lượng', 'datetime': 'Ngày', 'category_vi': 'Loại hoạt động'})
            fig_trend.update_layout(height=400, hovermode='x unified')
            st.plotly_chart(fig_trend, use_container_width=True)
        
        with col2:
            # Biểu đồ phân bố theo loại hoạt động
            fig_pie = px.pie(values=categories_summary.values, names=categories_summary.index,
                           title='📊 Phân bố theo loại hoạt động',
                           hole=0.4)
            fig_pie.update_layout(height=400)
            st.plotly_chart(fig_pie, use_container_width=True)
        
        # Phân tích chi tiết
        st.markdown('<div class="section-header">📈 Phân tích chi tiết</div>', unsafe_allow_html=True)
        
        # Tabs con cho phân tích
        subtab1, subtab2, subtab3 = st.tabs(["📅 Theo thời gian", "📊 Theo loại", "📈 Top ngày"])
        
        with subtab1:
            # Phân tích theo tháng liên tục
            df_summary['year_month'] = df_summary['year'].astype(str) + '-' + df_summary['month'].astype(str).str.zfill(2)
            df_summary['month_year_vi'] = df_summary['month'].astype(str) + '/' + df_summary['year'].astype(str)
            
            monthly_data = df_summary.groupby(['year_month', 'month_year_vi', 'category_vi'])['count'].sum().reset_index()
            
            fig_monthly = px.bar(monthly_data, x='month_year_vi', y='count', color='category_vi',
                               title='Hoạt động theo thời gian (tháng/năm)', barmode='group',
                               labels={'count': 'Số lượng', 'month_year_vi': 'Tháng/Năm', 'category_vi': 'Loại'})
            fig_monthly.update_xaxes(tickangle=45)
            st.plotly_chart(fig_monthly, use_container_width=True)
            
            # Bảng thống kê theo tháng liên tục
            monthly_stats = df_summary.groupby(['month_year_vi', 'category_vi'])['count'].sum().unstack(fill_value=0)
            monthly_stats = monthly_stats.sort_index(key=lambda x: pd.to_datetime(x, format='%m/%Y'))
            st.dataframe(monthly_stats, use_container_width=True)
        
        with subtab2:
            # Phân tích chi tiết theo từng loại
            for category in categories_summary.index[:4]:  # Top 4 categories
                category_data = df_summary[df_summary['category_vi'] == category]
                daily_trend = category_data.groupby('datetime')['count'].sum()
                
                st.markdown(f"#### {category}")
                col_a, col_b, col_c = st.columns([2, 1, 1])
                
                with col_a:
                    fig_cat = px.line(x=daily_trend.index, y=daily_trend.values,
                                     title=f'Xu hướng {category}')
                    fig_cat.update_layout(height=300)
                    st.plotly_chart(fig_cat, use_container_width=True)
                
                with col_b:
                    st.metric("Tổng", f"{category_data['count'].sum():,}")
                
                with col_c:
                    st.metric("TB/ngày", f"{category_data['count'].mean():.1f}")
        
        with subtab3:
            # Top ngày có hoạt động cao nhất
            daily_total = df_summary.groupby('datetime')['count'].sum().sort_values(ascending=False)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 🏆 Top 10 ngày hoạt động mạnh nhất")
                for i, (date, count) in enumerate(daily_total.head(10).items(), 1):
                    day_detail = df_summary[df_summary['datetime'] == date].groupby('category_vi')['count'].sum()
                    detail_text = " | ".join([f"{cat}: {val}" for cat, val in day_detail.items()])
                    st.success(f"#{i}. {date.strftime('%d/%m/%Y')}: **{count}** hoạt động\n\n{detail_text}")
            
            with col2:
                st.markdown("#### 📊 Hoạt động theo ngày trong tuần")
                df_summary['weekday'] = df_summary['datetime'].dt.day_name()
                df_summary['weekday_vi'] = df_summary['weekday'].map({
                    'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                    'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'CN'
                })
                
                weekday_stats = df_summary.groupby('weekday_vi')['count'].agg(['sum', 'mean']).round(2)
                weekday_stats.columns = ['Tổng', 'TB/ngày']
                
                fig_weekday = px.bar(x=weekday_stats.index, y=weekday_stats['Tổng'],
                                   title='Tổng hoạt động theo ngày trong tuần')
                st.plotly_chart(fig_weekday, use_container_width=True)
                
                st.dataframe(weekday_stats, use_container_width=True)
    
    else:
        st.error("❌ Không thể load dữ liệu tổng hợp từ file tonghop.json")
        st.info("📁 Đảm bảo file tonghop.json tồn tại trong thư mục gốc")

# Tab 2: Văn bản đến
with tab2:
    st.markdown('<div class="tab-header">📥 Quản lý Văn bản Đến</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ file có sẵn
    def load_incoming_docs_data():
        """Load dữ liệu văn bản đến từ file vbden.json"""
        try:
            with open('vbden.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data['data'] if isinstance(data, dict) and 'data' in data else data)

                # Xử lý dữ liệu tương tự như process_incoming_documents_data
                if 'datetime' not in df.columns:
                    if all(col in df.columns for col in ['year', 'month', 'date']):
                        df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
                    elif all(col in df.columns for col in ['Year', 'Month', 'Date']):
                        df['datetime'] = pd.to_datetime(df[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))

                # Thêm các cột cần thiết
                df['weekday'] = df['datetime'].dt.day_name()
                df['weekday_vi'] = df['weekday'].map({
                    'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                    'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
                })
                df['year'] = df['datetime'].dt.year
                df['month'] = df['datetime'].dt.month
                df['week'] = df['datetime'].dt.isocalendar().week

                return df
        except Exception as e:
            st.error(f"Lỗi khi load dữ liệu từ vbden.json: {e}")
            return None

    df = load_incoming_docs_data()

    if df is not None:
        # Áp dụng filter toàn cục
        df = apply_global_filter(df)
        # Thống kê tổng quan
        st.markdown("### 📊 Thống kê tổng quan")

        # Hàng 1: Thống kê chính
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            total_docs = df['total_incoming'].sum()
            st.metric("📑 Tổng văn bản", f"{total_docs:,}")

        with col2:
            avg_daily = df['total_incoming'].mean()
            st.metric("📈 Trung bình/ngày", f"{avg_daily:.1f}")

        with col3:
            total_on_time = df['processed_on_time'].sum()
            st.metric("✅ Xử lý đúng hạn", f"{total_on_time:,}")

        with col4:
            total_late = df['processed_late'].sum()
            st.metric("⚠️ Xử lý trễ hạn", f"{total_late:,}")

        with col5:
            if total_docs > 0:
                on_time_rate = (total_on_time / total_docs) * 100
            else:
                on_time_rate = 0
            st.metric("📊 Tỷ lệ đúng hạn", f"{on_time_rate:.1f}%")

        # Hàng 2: Phân loại phản hồi
        st.markdown("#### 📋 Phân loại theo yêu cầu phản hồi")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            no_response = df['no_response_required'].sum()
            st.metric("🔕 Không cần phản hồi", f"{no_response:,}")

        with col2:
            need_response = df['response_required'].sum()
            st.metric("📢 Cần phản hồi", f"{need_response:,}")

        with col3:
            vanban_response = df['response_required_VanBan'].sum()
            st.metric("📄 PH Văn bản", f"{vanban_response:,}")

        with col4:
            email_response = df['response_required_Email'].sum()
            st.metric("📧 PH Email", f"{email_response:,}")

        with col5:
            phone_response = df['response_required_DienThoai'].sum()
            st.metric("📞 PH Điện thoại", f"{phone_response:,}")

        st.markdown("---")

        # Pivot Table
        selected_period_type = create_pivot_table(df)

        st.markdown("---")

        # Biểu đồ
        create_incoming_docs_charts(df, selected_period_type)

        # Bảng dữ liệu chi tiết
        st.markdown("### 📋 Chi tiết dữ liệu")
            
        # Lọc dữ liệu
        col1, col2 = st.columns(2)
        with col1:
                date_range = st.date_input(
                    "📅 Chọn khoảng thời gian",
                    value=(df['datetime'].min(), df['datetime'].max()),
                    min_value=df['datetime'].min(),
                    max_value=df['datetime'].max()
                )
            
        with col2:
                min_docs = st.number_input("📊 Số văn bản tối thiểu", min_value=0, value=0)
            
            # Áp dụng filter
        if len(date_range) == 2:
                filtered_df = df[
                    (df['datetime'] >= pd.to_datetime(date_range[0])) & 
                    (df['datetime'] <= pd.to_datetime(date_range[1])) &
                    (df['total_incoming'] >= min_docs)
                ]
        else:
                filtered_df = df[df['total_incoming'] >= min_docs]
            
        display_cols = ['datetime', 'total_incoming', 'no_response_required', 'response_required',
                           'processed_on_time', 'processed_late']
            
            # Thêm các cột phản hồi nếu có
        response_cols = ['response_required_VanBan', 'response_required_Email', 
                           'response_required_DienThoai', 'response_required_PhanMem']
        for col in response_cols:
                if col in filtered_df.columns:
                    display_cols.append(col)
            
            # Thêm cột detail nếu có
        if 'total_incoming_detail' in filtered_df.columns:
                display_cols.append('total_incoming_detail')
            
        st.dataframe(filtered_df[display_cols], use_container_width=True)
    else:
        st.info("📁 Vui lòng upload file dữ liệu để xem thống kê chi tiết")

# Tab 3: Văn bản đi
with tab3:
    st.markdown('<div class="tab-header">📤 Quản lý Văn bản Đi</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ file có sẵn
    def load_outgoing_docs_data():
        """Load dữ liệu văn bản đi từ file vbdi.json"""
        try:
            with open('vbdi.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data['data'] if isinstance(data, dict) and 'data' in data else data)

                # Flatten nested structure để tạo các cột _total
                for index, row in df.iterrows():
                    # Extract totals from nested objects
                    if 'contracts' in row and isinstance(row['contracts'], dict):
                        df.loc[index, 'contracts_total'] = row['contracts'].get('total', 0)
                    if 'decisions' in row and isinstance(row['decisions'], dict):
                        df.loc[index, 'decisions_total'] = row['decisions'].get('total', 0)
                    if 'regulations' in row and isinstance(row['regulations'], dict):
                        df.loc[index, 'regulations_total'] = row['regulations'].get('total', 0)
                    if 'rules' in row and isinstance(row['rules'], dict):
                        df.loc[index, 'rules_total'] = row['rules'].get('total', 0)
                    if 'procedures' in row and isinstance(row['procedures'], dict):
                        df.loc[index, 'procedures_total'] = row['procedures'].get('total', 0)
                    if 'instruct' in row and isinstance(row['instruct'], dict):
                        df.loc[index, 'instruct_total'] = row['instruct'].get('total', 0)

                # Xử lý datetime
                if 'datetime' not in df.columns:
                    if all(col in df.columns for col in ['year', 'month', 'date']):
                        df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
                    elif all(col in df.columns for col in ['Year', 'Month', 'Date']):
                        df['datetime'] = pd.to_datetime(df[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))

                # Thêm các cột cần thiết
                df['weekday'] = df['datetime'].dt.day_name()
                df['weekday_vi'] = df['weekday'].map({
                    'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                    'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
                })
                df['year'] = df['datetime'].dt.year
                df['month'] = df['datetime'].dt.month
                df['week'] = df['datetime'].dt.isocalendar().week

                # Tính total_outgoing (tổng các loại văn bản bao gồm cả documents)
                total_columns = ['documents', 'contracts_total', 'decisions_total', 'regulations_total',
                               'rules_total', 'procedures_total', 'instruct_total']
                for col in total_columns:
                    if col not in df.columns:
                        df[col] = 0

                df['total_outgoing'] = df[total_columns].sum(axis=1)

                return df
        except Exception as e:
            st.error(f"Lỗi khi load dữ liệu từ vbdi.json: {e}")
            return None

    df_out = load_outgoing_docs_data()

    if df_out is not None:
            # Áp dụng filter toàn cục
            df_out = apply_global_filter(df_out)
            # Thống kê tổng quan
            st.markdown("### 📊 Thống kê tổng quan văn bản đi")
            
            # Hàng 1: Thống kê chính
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                # Tính tổng tất cả các loại văn bản đi (bao gồm cả documents)
                total_docs = df_out['documents'].sum() if 'documents' in df_out.columns else 0
                total_contracts = df_out['contracts_total'].sum() if 'contracts_total' in df_out.columns else 0
                total_decisions = df_out['decisions_total'].sum() if 'decisions_total' in df_out.columns else 0
                total_regulations = df_out['regulations_total'].sum() if 'regulations_total' in df_out.columns else 0
                total_rules = df_out['rules_total'].sum() if 'rules_total' in df_out.columns else 0
                total_procedures = df_out['procedures_total'].sum() if 'procedures_total' in df_out.columns else 0
                total_instruct = df_out['instruct_total'].sum() if 'instruct_total' in df_out.columns else 0

                total_outgoing = total_docs + total_contracts + total_decisions + total_regulations + total_rules + total_procedures + total_instruct
                st.metric("📄 Tổng văn bản đi", total_outgoing)

            with col2:
                st.metric("📝 Văn bản phát hành", total_docs)

            with col3:
                st.metric("📁 Hợp đồng", total_contracts)

            with col4:
                st.metric("⚖️ Quyết định", total_decisions)
            
            with col5:
                # Tính trung bình dựa trên tổng văn bản thực tế
                if len(df_out) > 0:
                    avg_daily = total_outgoing / len(df_out)
                    st.metric("📈 TB/ngày", f"{avg_daily:.1f}")
                else:
                    st.metric("📈 TB/ngày", "0")

            # Hàng 2: Thống kê quy chế và quy định
            st.markdown("#### 📋 Thống kê quy chế và quy định")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("📜 Quy định", total_regulations)

            with col2:
                st.metric("📋 Quy chế", total_rules)

            with col3:
                st.metric("🔄 Thủ tục", total_procedures)

            with col4:
                st.metric("📚 Hướng dẫn", total_instruct)
            
            st.markdown("---")
            
            # Pivot Table
            selected_period_type_out = create_outgoing_pivot_table(df_out)

            st.markdown("---")

            # Biểu đồ
            create_outgoing_docs_charts(df_out, selected_period_type_out)
            
            # Bảng dữ liệu chi tiết
            st.markdown("### 📋 Chi tiết dữ liệu")

            # Lọc dữ liệu
            col1, col2 = st.columns(2)
            with col1:
                date_range_out = st.date_input(
                    "📅 Chọn khoảng thời gian",
                    value=(df_out['datetime'].min(), df_out['datetime'].max()),
                    min_value=df_out['datetime'].min(),
                    max_value=df_out['datetime'].max(),
                    key="outgoing_date_range"
                )

            with col2:
                min_docs_out = st.number_input("📊 Số văn bản tối thiểu", min_value=0, value=0, key="outgoing_min_docs")

            # Áp dụng filter
            if len(date_range_out) == 2:
                filtered_df_out = df_out[
                    (df_out['datetime'] >= pd.to_datetime(date_range_out[0])) &
                    (df_out['datetime'] <= pd.to_datetime(date_range_out[1])) &
                    (df_out['documents'] >= min_docs_out)
                ]
            else:
                filtered_df_out = df_out[df_out['documents'] >= min_docs_out]
            display_cols_out = ['datetime', 'total_outgoing', 'documents', 'contracts_total', 'decisions_total',
                               'regulations_total', 'rules_total', 'procedures_total', 'instruct_total']
            # Chỉ hiển thị các cột có trong DataFrame
            display_cols_out = [col for col in display_cols_out if col in filtered_df_out.columns]

            # Thêm cột contracts, decisions detail nếu có
            detail_cols = ['contracts', 'decisions']
            for col in detail_cols:
                if col in filtered_df_out.columns:
                    display_cols_out.append(col)

            st.dataframe(filtered_df_out[display_cols_out], use_container_width=True)
    else:
        st.error("❌ Không có dữ liệu từ vbdi.json")

# Tab 4: Quản lý công việc
with tab4:
    st.markdown('<div class="tab-header">📋 Quản lý Công Việc</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ file có sẵn
    def load_task_data():
        """Load dữ liệu công việc từ file cviec.json"""
        try:
            with open('cviec.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data['data'] if isinstance(data, dict) and 'data' in data else data)

                # Flatten nested structure từ all_departments
                for index, row in df.iterrows():
                    if 'all_departments' in row and isinstance(row['all_departments'], dict):
                        all_dept = row['all_departments']
                        df.loc[index, 'tasks_assigned'] = all_dept.get('tasks_assigned', 0)
                        df.loc[index, 'tasks_completed_on_time'] = all_dept.get('tasks_completed_on_time', 0)
                        df.loc[index, 'tasks_completed_on_time_rate'] = all_dept.get('tasks_completed_on_time_rate', 0)
                        df.loc[index, 'tasks_new'] = all_dept.get('tasks_new', 0)
                        df.loc[index, 'tasks_new_rate'] = all_dept.get('tasks_new_rate', 0)
                        df.loc[index, 'tasks_processing'] = all_dept.get('tasks_processing', 0)
                        df.loc[index, 'tasks_processing_rate'] = all_dept.get('tasks_processing_rate', 0)

                # Xử lý datetime
                if 'datetime' not in df.columns:
                    if all(col in df.columns for col in ['year', 'month', 'date']):
                        df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
                    elif all(col in df.columns for col in ['Year', 'Month', 'Date']):
                        df['datetime'] = pd.to_datetime(df[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))

                # Thêm các cột cần thiết
                df['weekday'] = df['datetime'].dt.day_name()
                df['weekday_vi'] = df['weekday'].map({
                    'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                    'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
                })
                df['year'] = df['datetime'].dt.year
                df['month'] = df['datetime'].dt.month
                df['week'] = df['datetime'].dt.isocalendar().week

                # Đảm bảo các cột task tồn tại với giá trị mặc định
                task_columns = ['tasks_assigned', 'tasks_completed_on_time', 'tasks_completed_on_time_rate',
                               'tasks_new', 'tasks_new_rate', 'tasks_processing', 'tasks_processing_rate']
                for col in task_columns:
                    if col not in df.columns:
                        df[col] = 0

                # Tính completion_rate cho mỗi hàng
                df['completion_rate'] = df.apply(lambda row:
                    (row['tasks_completed_on_time'] / row['tasks_assigned'] * 100)
                    if row['tasks_assigned'] > 0 else 0, axis=1)

                # Tạo DataFrame riêng cho detail_departments
                detail_rows = []
                for index, row in df.iterrows():
                    if 'detail_departments' in row and isinstance(row['detail_departments'], list):
                        for dept in row['detail_departments']:
                            if isinstance(dept, dict):
                                detail_row = {
                                    'Date': row.get('Date', row.get('date', '')),
                                    'Month': row.get('Month', row.get('month', '')),
                                    'Year': row.get('Year', row.get('year', '')),
                                    'datetime': row.get('datetime', ''),
                                    'weekday': row.get('weekday', ''),
                                    'weekday_vi': row.get('weekday_vi', ''),
                                    'year': row.get('year', ''),
                                    'month': row.get('month', ''),
                                    'week': row.get('week', ''),
                                    'department': dept.get('Name', ''),
                                    'tasks_assigned': dept.get('tasks_assigned', 0),
                                    'tasks_completed_on_time': dept.get('tasks_completed_on_time', 0),
                                    'tasks_completed_on_time_rate': dept.get('tasks_completed_on_time_rate', 0),
                                    'tasks_new': dept.get('tasks_new', 0),
                                    'tasks_new_rate': dept.get('tasks_new_rate', 0),
                                    'tasks_processing': dept.get('tasks_processing', 0),
                                    'tasks_processing_rate': dept.get('tasks_processing_rate', 0)
                                }
                                detail_rows.append(detail_row)

                if detail_rows:
                    df_detail = pd.DataFrame(detail_rows)
                    # Tính completion_rate cho detail
                    df_detail['completion_rate'] = df_detail.apply(lambda row:
                        (row['tasks_completed_on_time'] / row['tasks_assigned'] * 100)
                        if row['tasks_assigned'] > 0 else 0, axis=1)
                else:
                    df_detail = pd.DataFrame()

                return df, df_detail
        except Exception as e:
            st.error(f"Lỗi khi load dữ liệu từ cviec.json: {e}")
            return None, None

    df_all_tasks, df_detail_tasks = load_task_data()

    if df_all_tasks is not None and df_detail_tasks is not None:
            # Áp dụng filter toàn cục
            df_all_tasks_filtered = apply_global_filter(df_all_tasks)
            df_detail_tasks_filtered = apply_global_filter(df_detail_tasks)
            # Thống kê tổng quan
            st.markdown("### 📊 Thống kê tổng quan công việc")
            
            # Hàng 1: Thống kê chính
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                total_assigned = df_all_tasks_filtered['tasks_assigned'].sum()
                st.metric("📋 Tổng giao việc", total_assigned)
            
            with col2:
                total_completed = df_all_tasks_filtered['tasks_completed_on_time'].sum()
                st.metric("✅ Hoàn thành", total_completed)
            
            with col3:
                total_processing = df_all_tasks_filtered['tasks_processing'].sum()
                st.metric("🔄 Đang xử lý", total_processing)
            
            with col4:
                total_new = df_all_tasks_filtered['tasks_new'].sum()
                st.metric("🆕 Việc mới", total_new)
            
            with col5:
                # Tính tỷ lệ hoàn thành: (completed / assigned) * 100
                total_assigned_all = df_all_tasks_filtered['tasks_assigned'].sum()
                total_completed_all = df_all_tasks_filtered['tasks_completed_on_time'].sum()
                if total_assigned_all > 0:
                    avg_completion = (total_completed_all / total_assigned_all) * 100
                    st.metric("📊 Tỷ lệ hoàn thành", f"{avg_completion:.1f}%")
                else:
                    st.metric("📊 Tỷ lệ hoàn thành", "0%")
            
            # Hàng 2: Thống kê phòng ban
            st.markdown("#### 📋 Thống kê theo phòng ban")
            if len(df_detail_tasks_filtered) > 0:
                dept_summary = df_detail_tasks_filtered.groupby('department').agg({
                    'tasks_assigned': 'sum',
                    'tasks_completed_on_time': 'sum',
                    'tasks_processing': 'sum',
                    'tasks_new': 'sum'
                }).reset_index()
                dept_summary['completion_rate'] = (dept_summary['tasks_completed_on_time'] / dept_summary['tasks_assigned'] * 100).fillna(0)
                
                # Top 3 phòng ban theo tổng số công việc được giao
                top_depts = dept_summary.nlargest(3, 'tasks_assigned')

                col1, col2, col3 = st.columns(3)
                for i, (idx, dept) in enumerate(top_depts.iterrows()):
                    with [col1, col2, col3][i]:
                        completion_rate = (dept['tasks_completed_on_time'] / dept['tasks_assigned'] * 100) if dept['tasks_assigned'] > 0 else 0
                        st.metric(f"🏆 {dept['department']}",
                                f"{dept['tasks_completed_on_time']}/{dept['tasks_assigned']} việc",
                                f"Tỷ lệ: {completion_rate:.1f}%")
            
            st.markdown("---")
            
            # Pivot Table
            selected_period_type_tasks = create_task_pivot_table(df_all_tasks_filtered, df_detail_tasks_filtered)

            st.markdown("---")

            # Biểu đồ
            create_task_management_charts(df_all_tasks_filtered, df_detail_tasks_filtered, selected_period_type_tasks)
            
            # Bảng dữ liệu chi tiết
            st.markdown("### 📋 Chi tiết dữ liệu")
            
            # Chọn loại dữ liệu hiển thị
            detail_type = st.selectbox(
                "📊 Hiển thị dữ liệu:",
                options=['Tổng hợp tất cả phòng ban', 'Chi tiết từng phòng ban'],
                key="task_detail_type"
            )
            
            # Chọn DataFrame đã được filter toàn cục
            display_df = df_all_tasks_filtered if detail_type == 'Tổng hợp tất cả phòng ban' else df_detail_tasks_filtered
            
            # Lọc thêm theo số việc tối thiểu
            min_tasks = st.number_input("📊 Số việc tối thiểu", min_value=0, value=0, key="tasks_min")
            filtered_df_tasks = display_df[display_df['tasks_assigned'] >= min_tasks]
            
            # Các cột hiển thị
            display_cols_tasks = ['datetime', 'tasks_assigned', 'tasks_completed_on_time', 
                                 'tasks_processing', 'tasks_new', 'completion_rate']
            
            if detail_type == 'Chi tiết từng phòng ban':
                display_cols_tasks.insert(1, 'department')
            
            # Format completion_rate
            filtered_df_display = filtered_df_tasks[display_cols_tasks].copy()
            filtered_df_display['completion_rate'] = filtered_df_display['completion_rate'].round(1)
            
            st.dataframe(
                filtered_df_display.rename(columns={
                    'datetime': 'Ngày',
                    'department': 'Phòng ban',
                    'tasks_assigned': 'Giao việc',
                    'tasks_completed_on_time': 'Hoàn thành',
                    'tasks_processing': 'Đang xử lý',
                    'tasks_new': 'Việc mới',
                    'completion_rate': 'Tỷ lệ hoàn thành (%)'
                }), 
                use_container_width=True
            )
    else:
        st.info("📁 Vui lòng upload file dữ liệu để xem thống kê chi tiết")

# Tab 5: Quản lý lịch họp
with tab5:
    st.markdown('<div class="tab-header">📅 Quản lý Lịch Họp</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ file có sẵn
    def load_meeting_data():
        """Load dữ liệu lịch họp từ file lhop.json"""
        try:
            with open('lhop.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data['data'] if isinstance(data, dict) and 'data' in data else data)

                # Xử lý dữ liệu tương tự như process_meeting_data
                if 'datetime' not in df.columns:
                    if all(col in df.columns for col in ['year', 'month', 'date']):
                        df['datetime'] = pd.to_datetime(df[['year', 'month', 'date']].rename(columns={'date': 'day'}))
                    elif all(col in df.columns for col in ['Year', 'Month', 'Date']):
                        df['datetime'] = pd.to_datetime(df[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))

                # Thêm các cột cần thiết
                df['weekday'] = df['datetime'].dt.day_name()
                df['weekday_vi'] = df['weekday'].map({
                    'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                    'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
                })
                df['year'] = df['datetime'].dt.year
                df['month'] = df['datetime'].dt.month
                df['week'] = df['datetime'].dt.isocalendar().week

                # Thêm cột day_type dựa trên weekday
                df['day_type'] = df['weekday'].map({
                    'Monday': 'Ngày làm việc', 'Tuesday': 'Ngày làm việc', 'Wednesday': 'Ngày làm việc',
                    'Thursday': 'Ngày làm việc', 'Friday': 'Ngày làm việc',
                    'Saturday': 'Cuối tuần', 'Sunday': 'Cuối tuần'
                })

                # Đảm bảo cột meeting_schedules tồn tại
                if 'meeting_schedules' not in df.columns:
                    df['meeting_schedules'] = 0

                # Thêm cột meeting_level dựa trên số lượng meeting_schedules
                def categorize_meeting_level(count):
                    if count == 0:
                        return 'Không có họp'
                    elif count <= 2:
                        return 'Ít họp'
                    elif count <= 5:
                        return 'Trung bình'
                    else:
                        return 'Nhiều họp'

                df['meeting_level'] = df['meeting_schedules'].apply(categorize_meeting_level)

                return df
        except Exception as e:
            st.error(f"Lỗi khi load dữ liệu từ lhop.json: {e}")
            return None

    df_meetings = load_meeting_data()

    if df_meetings is not None:
            # Áp dụng filter toàn cục
            df_meetings = apply_global_filter(df_meetings)
            
            # Thống kê tổng quan
            st.markdown("### 📊 Thống kê tổng quan lịch họp")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                total_meetings = df_meetings['meeting_schedules'].sum()
                st.metric("📅 Tổng cuộc họp", f"{total_meetings:,}")
            
            with col2:
                avg_daily = df_meetings['meeting_schedules'].mean()
                st.metric("📈 TB/ngày", f"{avg_daily:.1f}")
            
            with col3:
                max_day = df_meetings['meeting_schedules'].max()
                st.metric("🔥 Nhiều nhất", f"{max_day} cuộc")
            
            with col4:
                min_day = df_meetings['meeting_schedules'].min()
                st.metric("🔻 Ít nhất", f"{min_day} cuộc")
            
            with col5:
                total_days = len(df_meetings)
                st.metric("📆 Tổng ngày", f"{total_days} ngày")
            
            # Hàng 2: Thống kê theo loại ngày
            st.markdown("#### 📋 Phân tích theo loại ngày")
            col1, col2, col3 = st.columns(3)
            
            workday_data = df_meetings[df_meetings['day_type'] == 'Ngày làm việc']
            weekend_data = df_meetings[df_meetings['day_type'] == 'Cuối tuần']
            
            with col1:
                workday_total = workday_data['meeting_schedules'].sum()
                workday_count = len(workday_data)
                st.metric("💼 Ngày làm việc", f"{workday_total} cuộc", f"{workday_count} ngày")
            
            with col2:
                weekend_total = weekend_data['meeting_schedules'].sum()
                weekend_count = len(weekend_data)
                st.metric("🏡 Cuối tuần", f"{weekend_total} cuộc", f"{weekend_count} ngày")
            
            with col3:
                busy_days = len(df_meetings[df_meetings['meeting_schedules'] > 10])
                st.metric("🔥 Ngày bận rộn", f"{busy_days} ngày", ">10 cuộc")
            
            st.markdown("---")

            # Pivot Table
            selected_period_type_meetings = create_meeting_pivot_table(df_meetings)

            st.markdown("---")

            # Tab định nghĩa mức độ bận rộn
            with st.expander("ℹ️ Định nghĩa mức độ bận rộn"):
                st.markdown("""
                #### 📊 Phân loại mức độ hoạt động lịch họp:

                | Mức độ | Số cuộc họp/ngày | Mô tả |
                |--------|------------------|-------|
                | 🟢 **Rất ít** | 0-2 cuộc | Ngày làm việc bình thường, ít hoạt động họp |
                | 🔵 **Ít** | 3-5 cuộc | Ngày có một số cuộc họp, mức độ vừa phải |
                | 🟡 **Trung bình** | 6-8 cuộc | Ngày khá bận rộn với nhiều cuộc họp |
                | 🟠 **Nhiều** | 9-12 cuộc | Ngày rất bận với mật độ họp cao |
                | 🔴 **Rất nhiều** | >12 cuộc | Ngày cực kỳ bận rộn, liên tục các cuộc họp |

                ---
                #### 📈 Các chỉ số quan trọng:
                - **Ngày bận rộn**: Ngày có >5 cuộc họp (từ mức Trung bình trở lên)
                - **Tỷ lệ ngày bận**: % ngày trong kỳ có >5 cuộc họp
                - **Xu hướng**: So sánh với kỳ trước để theo dõi biến động
                """)

            # Biểu đồ
            create_meeting_charts(df_meetings, selected_period_type_meetings)
            
            st.markdown("---")
            
            # Bảng dữ liệu chi tiết
            st.markdown("### 📋 Chi tiết dữ liệu lịch họp")
            
        # Lọc dữ liệu
    col1, col2 = st.columns(2)
    with col1:
                min_meetings = st.number_input("📊 Số cuộc họp tối thiểu", min_value=0, value=0, key="meetings_min")
    with col2:
                selected_level = st.selectbox(
                    "📅 Mức độ bận rộn",
                    options=['Tất cả'] + list(df_meetings['meeting_level'].unique()),
                    key="meeting_level_filter"
                )
            
            # Áp dụng filter
    filtered_meetings = df_meetings[df_meetings['meeting_schedules'] >= min_meetings]
    if selected_level != 'Tất cả':
                filtered_meetings = filtered_meetings[filtered_meetings['meeting_level'] == selected_level]
            
            # Hiển thị bảng
    display_cols_meetings = ['datetime', 'weekday_vi', 'meeting_schedules', 'meeting_level', 'day_type']
            
    st.dataframe(
                filtered_meetings[display_cols_meetings].rename(columns={
                    'datetime': 'Ngày',
                    'weekday_vi': 'Ngày trong tuần', 
                    'meeting_schedules': 'Số cuộc họp',
                    'meeting_level': 'Mức độ bận rộn',
                    'day_type': 'Loại ngày'
                }),
                use_container_width=True
            )
            
            # Thống kê cuối
    st.markdown("**📊 Insights chính:**")
    insights = []
            
    if len(df_meetings) > 0:
                busiest_day = df_meetings.loc[df_meetings['meeting_schedules'].idxmax()]
                insights.append(f"🔥 Ngày bận rộn nhất: {busiest_day['datetime'].strftime('%d/%m/%Y')} ({busiest_day['weekday_vi']}) với {busiest_day['meeting_schedules']} cuộc họp")
                
                quietest_day = df_meetings.loc[df_meetings['meeting_schedules'].idxmin()]
                insights.append(f"🔻 Ngày ít họp nhất: {quietest_day['datetime'].strftime('%d/%m/%Y')} ({quietest_day['weekday_vi']}) với {quietest_day['meeting_schedules']} cuộc họp")
                
                most_common_level = df_meetings['meeting_level'].mode()[0] if len(df_meetings['meeting_level'].mode()) > 0 else 'Không xác định'
                insights.append(f"📊 Mức độ phổ biến nhất: {most_common_level}")
                
                for insight in insights:
                    st.write(f"- {insight}")
    else:
        st.error("❌ Không có dữ liệu lịch họp")
        st.info("📁 Upload dữ liệu để quản lý lịch họp chi tiết")

# Tab 6: Quản lý phòng họp
with tab6:
    st.markdown('<div class="tab-header">🏢 Quản lý Phòng Họp</div>', unsafe_allow_html=True)
    
    def load_room_data_from_file():
        """Load dữ liệu phòng họp từ file có sẵn"""
        try:
            with open('phop.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data['data'])
                
                # Tạo cột datetime
                df['datetime'] = pd.to_datetime(df[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))
                df['weekday'] = df['datetime'].dt.day_name()
                df['weekday_vi'] = df['weekday'].map({
                    'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
                    'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
                })
                df['month_vi'] = df['Month'].map({
                    1: 'Tháng 1', 2: 'Tháng 2', 3: 'Tháng 3', 4: 'Tháng 4',
                    5: 'Tháng 5', 6: 'Tháng 6', 7: 'Tháng 7', 8: 'Tháng 8',
                    9: 'Tháng 9', 10: 'Tháng 10', 11: 'Tháng 11', 12: 'Tháng 12'
                })
                
                # Tính toán các chỉ số
                df['cancel_rate'] = (df['register_room_cancel'] / df['register_room'] * 100).fillna(0).round(1)
                df['net_bookings'] = df['register_room'] - df['register_room_cancel']
                df['is_weekend'] = df['weekday'].isin(['Saturday', 'Sunday'])
                df['day_type'] = df['is_weekend'].map({False: 'Ngày làm việc', True: 'Cuối tuần'})
                
                return df
        except Exception as e:
            st.error(f"Lỗi khi load dữ liệu: {e}")
            return None
    
    # Load dữ liệu từ file có sẵn
    df_rooms = load_room_data_from_file()
    if df_rooms is not None:
        df_rooms = apply_global_filter(df_rooms)
    
    if df_rooms is not None and not df_rooms.empty:
        # Metrics tổng quan
        col1, col2, col3, col4 = st.columns(4)
        
        total_bookings = df_rooms['register_room'].sum()
        total_cancels = df_rooms['register_room_cancel'].sum()
        avg_daily = df_rooms['register_room'].mean()
        cancel_rate_avg = (total_cancels / total_bookings * 100) if total_bookings > 0 else 0
        
        with col1:
            st.metric("📅 Tổng đăng ký", f"{total_bookings:,}")
        with col2:
            st.metric("❌ Tổng hủy", f"{total_cancels:,}")
        with col3:
            st.metric("📊 TB/ngày", f"{avg_daily:.1f}")
        with col4:
            st.metric("📉 Tỷ lệ hủy", f"{cancel_rate_avg:.1f}%")

        st.markdown("---")

        # Pivot Table
        selected_period_type_rooms = create_room_pivot_table(df_rooms)

        st.markdown("---")

        # Biểu đồ
        create_room_charts(df_rooms, selected_period_type_rooms)

        st.markdown("---")

        # Bảng dữ liệu chi tiết
        st.markdown("### 📋 Chi tiết dữ liệu phòng họp")

        # Lọc dữ liệu
        col1, col2 = st.columns(2)
        with col1:
            min_bookings = st.number_input("📊 Số đăng ký tối thiểu", min_value=0, value=0, key="rooms_min")
        with col2:
            selected_day_type = st.selectbox(
                "📅 Loại ngày",
                options=['Tất cả'] + list(df_rooms['day_type'].unique()),
                key="room_day_type_filter"
            )

        # Áp dụng filter
        filtered_rooms = df_rooms[df_rooms['register_room'] >= min_bookings]
        if selected_day_type != 'Tất cả':
            filtered_rooms = filtered_rooms[filtered_rooms['day_type'] == selected_day_type]

        # Hiển thị bảng
        display_cols_rooms = ['datetime', 'weekday_vi', 'register_room', 'register_room_cancel', 'net_bookings', 'cancel_rate', 'day_type']

        st.dataframe(
            filtered_rooms[display_cols_rooms].rename(columns={
                'datetime': 'Ngày',
                'weekday_vi': 'Ngày trong tuần',
                'register_room': 'Tổng đăng ký',
                'register_room_cancel': 'Tổng hủy',
                'net_bookings': 'Đăng ký thực',
                'cancel_rate': 'Tỷ lệ hủy (%)',
                'day_type': 'Loại ngày'
            }),
            use_container_width=True
        )
    else:
        st.error("❌ Không có dữ liệu phòng họp")
        st.info("📁 Upload dữ liệu hoặc đảm bảo file meeting_rooms_data.json tồn tại để xem chi tiết")

# Footer
st.markdown("---")
st.markdown("### 🔧 Hướng dẫn sử dụng")
with st.expander("💡 Xem hướng dẫn chi tiết"):
    st.markdown("""
    **Cách sử dụng Dashboard:**
    
    1. **📁 Upload dữ liệu**: Mỗi tab có mục upload riêng, hỗ trợ file JSON và CSV
    2. **📊 Xem thống kê**: Sau khi upload, hệ thống sẽ tự động tính toán và hiển thị biểu đồ
    3. **🔍 Lọc dữ liệu**: Sử dụng các bộ lọc để xem dữ liệu theo điều kiện cụ thể
    4. **📈 Biểu đồ tương tác**: Click vào biểu đồ để xem chi tiết
    
    **📋 Cấu trúc dữ liệu:**
    - Văn bản đến: Cần có các trường date, month, year, total_incoming, processed_on_time, processed_late
    - Các module khác sẽ có cấu trúc tương tự tùy theo yêu cầu nghiệp vụ
    """)

st.markdown("""
<div style='text-align: center; padding: 2rem; color: #7f8c8d;'>
    <p>📊 Dashboard Phòng Hành chính - Phiên bản 1.0</p>
    <p>🔄 Dữ liệu cập nhật từ GitHub Repository</p>
</div>
""", unsafe_allow_html=True)
