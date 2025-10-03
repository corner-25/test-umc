import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta
import os, base64
import requests
from io import BytesIO, StringIO
from api_handler import show_quick_sync_button

# Tắt FutureWarning
pd.set_option('future.no_silent_downcasting', True)

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

# ===== GITHUB MANAGER CLASS =====
class GitHubDataManager:
    def __init__(self):
        try:
            self.github_token = st.secrets.get("github_token", "")
            self.github_owner = st.secrets.get("github_owner", "")
            self.github_repo = st.secrets.get("github_repo", "")
        except Exception:
            # Nếu không có secrets, sử dụng giá trị mặc định
            self.github_token = ""
            self.github_owner = ""
            self.github_repo = ""

    def check_github_connection(self):
        """Kiểm tra kết nối GitHub"""
        if not all([self.github_token, self.github_owner, self.github_repo]):
            return False, "❌ Chưa cấu hình GitHub credentials"

        try:
            headers = {"Authorization": f"token {self.github_token}"}
            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}"
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                return True, "✅ Kết nối GitHub thành công"
            else:
                return False, f"❌ Lỗi kết nối GitHub: {response.status_code}"
        except Exception as e:
            return False, f"❌ Lỗi kết nối: {str(e)}"

    def load_current_data(self):
        """Tải dữ liệu hiện tại từ GitHub"""
        try:
            headers = {"Authorization": f"token {self.github_token}"}

            # Tải file current_dashboard_data.json
            file_url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/current_dashboard_data.json"
            response = requests.get(file_url, headers=headers)

            if response.status_code == 200:
                file_info = response.json()
                download_url = file_info['download_url']

                # Tải và đọc file JSON
                file_response = requests.get(download_url)
                if file_response.status_code == 200:
                    json_data = file_response.json()

                    # Chuyển JSON thành DataFrame
                    if isinstance(json_data, dict) and 'data' in json_data:
                        df = pd.DataFrame(json_data['data'])
                    elif isinstance(json_data, list):
                        df = pd.DataFrame(json_data)
                    else:
                        df = pd.DataFrame(json_data)

                    metadata = {
                        'filename': 'current_dashboard_data.json',
                        'source': 'GitHub',
                        'sha': file_info['sha'],
                        'last_modified': file_info.get('last_modified', 'N/A'),
                        'size': file_info['size']
                    }

                    return df, metadata
            else:
                return None, None

        except Exception as e:
            st.error(f"Lỗi tải dữ liệu từ GitHub: {str(e)}")
            return None, None

# ===== DATA MANAGER CLASS =====
class DataManager:
    def __init__(self):
        self.data = None
        self.metadata = None

    def load_data_from_file(self, file):
        """Load dữ liệu từ file upload"""
        try:
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.name.endswith('.json'):
                df = pd.read_json(file)
            elif file.name.endswith(('.xlsx', '.xls')):
                # Đọc Excel, nếu có nhiều sheet thì lấy sheet đầu tiên
                try:
                    df = pd.read_excel(file, sheet_name=0)
                except Exception as e:
                    # Nếu lỗi, thử đọc với engine khác
                    df = pd.read_excel(file, engine='openpyxl' if file.name.endswith('.xlsx') else 'xlrd')
            else:
                return False, "❌ Format file không hỗ trợ. Chỉ hỗ trợ CSV, JSON, Excel (.xlsx, .xls)"

            # Validate dữ liệu
            required_columns = ['Tuần', 'Tháng', 'Nội dung']
            if not all(col in df.columns for col in required_columns):
                return False, f"❌ Thiếu cột bắt buộc: {required_columns}"

            self.data = df
            self.metadata = {
                'filename': file.name,
                'file_type': file.name.split('.')[-1].upper(),
                'rows': len(df),
                'columns': list(df.columns),
                'categories': df['Danh mục'].unique().tolist() if 'Danh mục' in df.columns else [],
                'upload_time': pd.Timestamp.now()
            }

            return True, "✅ Tải dữ liệu thành công"

        except Exception as e:
            return False, f"❌ Lỗi đọc file: {str(e)}"

    def load_data_from_github(self, github_df, github_metadata):
        """Load dữ liệu từ GitHub"""
        try:
            # Validate dữ liệu
            required_columns = ['Tuần', 'Tháng', 'Nội dung']
            if not all(col in github_df.columns for col in required_columns):
                return False, f"❌ Thiếu cột bắt buộc: {required_columns}"

            self.data = github_df
            self.metadata = {
                'filename': github_metadata['filename'],
                'file_type': 'GitHub',
                'rows': len(github_df),
                'columns': list(github_df.columns),
                'categories': github_df['Danh mục'].unique().tolist() if 'Danh mục' in github_df.columns else [],
                'source': github_metadata['source'],
                'sha': github_metadata['sha'],
                'upload_time': pd.Timestamp.now()
            }

            return True, "✅ Tải dữ liệu từ GitHub thành công"

        except Exception as e:
            return False, f"❌ Lỗi xử lý dữ liệu GitHub: {str(e)}"

    def get_category_data(self, category_name):
        """Lấy dữ liệu theo danh mục"""
        if self.data is None:
            return None

        if 'Danh mục' not in self.data.columns:
            return self.data  # Trả về toàn bộ nếu không có cột Danh mục

        filtered_data = self.data[self.data['Danh mục'] == category_name]
        return filtered_data if not filtered_data.empty else None

    def get_other_categories_data(self, excluded_categories):
        """Lấy dữ liệu cho các danh mục không thuộc danh sách loại trừ"""
        if self.data is None:
            return None

        if 'Danh mục' not in self.data.columns:
            return self.data

        filtered_data = self.data[~self.data['Danh mục'].isin(excluded_categories)]
        return filtered_data if not filtered_data.empty else None

# Initialize managers
if 'data_manager' not in st.session_state:
    st.session_state['data_manager'] = DataManager()

if 'github_manager' not in st.session_state:
    st.session_state['github_manager'] = GitHubDataManager()

data_manager = st.session_state['data_manager']
github_manager = st.session_state['github_manager']

# ===== SIDEBAR GITHUB CONNECTION =====
st.sidebar.header("☁️ Kết nối GitHub")

# Kiểm tra kết nối GitHub
connected, message = github_manager.check_github_connection()

if connected:
    st.sidebar.success("✅ GitHub kết nối thành công")

    # Thử tải dữ liệu từ GitHub
    try:
        github_data, github_metadata = github_manager.load_current_data()

        if github_data is not None and github_metadata:
            # Có dữ liệu từ GitHub
            st.sidebar.info(f"""
📊 **Dữ liệu từ GitHub:**
- File: {github_metadata['filename']}
- Kích thước: {github_metadata['size']:,} bytes
            """)

            # Load vào data manager
            success, load_message = data_manager.load_data_from_github(github_data, github_metadata)
            if success:
                st.sidebar.success("✅ Đã tải dữ liệu từ GitHub")

                # Button refresh
                if st.sidebar.button("🔄 Refresh từ GitHub"):
                    st.rerun()
            else:
                st.sidebar.warning(f"⚠️ {load_message}")
        else:
            st.sidebar.warning("📭 Chưa có dữ liệu trên GitHub")

    except Exception as github_error:
        st.sidebar.error(f"❌ Lỗi GitHub: {str(github_error)}")
else:
    st.sidebar.warning(message)

st.sidebar.markdown("---")

# ===== SIDEBAR API SYNC =====
st.sidebar.header("🔄 Đồng Bộ API")
show_quick_sync_button()

st.sidebar.markdown("---")

# ===== SIDEBAR UPLOAD FILE =====
st.sidebar.header("📁 Tải dữ liệu thủ công")

# Upload file cho dữ liệu mới (Tổ xe, Tổng đài, etc.)
uploaded_file_new = st.sidebar.file_uploader(
    "📊 Upload dữ liệu mới",
    type=['csv', 'json', 'xlsx', 'xls'],
    key="new_data_upload",
    help="Hỗ trợ: CSV, JSON, Excel (.xlsx, .xls)\nDành cho các tab: Tổ xe, Tổng đài, Hệ thống thư ký, Bãi giữ xe, Sự kiện, Khác"
)

# Xử lý file upload
if uploaded_file_new is not None:
    success, message = data_manager.load_data_from_file(uploaded_file_new)

    if success:
        st.sidebar.success(message)

        # Hiển thị thông tin file
        if data_manager.metadata:
            st.sidebar.info(f"📄 **{data_manager.metadata['filename']}**")
            st.sidebar.info(f"📊 **{data_manager.metadata['file_type']}** - {data_manager.metadata['rows']:,} dòng")

            # Hiển thị các danh mục có trong file
            if data_manager.metadata['categories']:
                st.sidebar.write("📋 **Danh mục có trong file:**")
                for cat in data_manager.metadata['categories']:
                    st.sidebar.write(f"- {cat}")
            else:
                st.sidebar.write("📋 **Cột có trong file:**")
                for col in data_manager.metadata['columns'][:5]:  # Hiển thị tối đa 5 cột
                    st.sidebar.write(f"- {col}")
                if len(data_manager.metadata['columns']) > 5:
                    st.sidebar.write(f"- ... và {len(data_manager.metadata['columns']) - 5} cột khác")
    else:
        st.sidebar.error(message)

# Button để xóa dữ liệu đã upload
if data_manager.data is not None:
    if st.sidebar.button("🗑️ Xóa dữ liệu đã tải"):
        data_manager.data = None
        data_manager.metadata = None
        st.rerun()

# Hiển thị trạng thái dữ liệu
if data_manager.data is not None and data_manager.metadata:
    if data_manager.metadata['file_type'] == 'GitHub':
        st.sidebar.success(f"☁️ Dữ liệu từ GitHub: {data_manager.metadata['filename']}")
    else:
        st.sidebar.success(f"✅ Dữ liệu thủ công: {data_manager.metadata['filename']}")
else:
    st.sidebar.info("📭 Chưa có dữ liệu được tải")

st.sidebar.markdown("---")

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

# Hàm tiện ích để load dữ liệu từ GitHub
def load_data_from_github(filename):
    """Load dữ liệu từ GitHub private repo"""
    try:
        github_token = st.secrets.get("github_token", "")
        github_owner = st.secrets.get("github_owner", "")
        github_repo = st.secrets.get("github_repo", "")

        if not all([github_token, github_owner, github_repo]):
            st.error(f"❌ Chưa cấu hình GitHub để load {filename}")
            return None

        url = f"https://api.github.com/repos/{github_owner}/{github_repo}/contents/{filename}"
        headers = {"Authorization": f"token {github_token}"}

        response = requests.get(url, headers=headers, verify=False)

        if response.status_code == 200:
            content = response.json()
            file_content = base64.b64decode(content["content"]).decode('utf-8')
            data = json.loads(file_content)

            # Xử lý data structure
            if isinstance(data, dict) and "data" in data:
                df = pd.DataFrame(data["data"])
            else:
                df = pd.DataFrame(data)

            return df
        else:
            st.warning(f"⚠️ Không tìm thấy {filename} trên GitHub")
            return None

    except Exception as e:
        st.error(f"❌ Lỗi load {filename} từ GitHub: {str(e)}")
        return None

# Hàm tiện ích để áp dụng filter toàn cục
def apply_global_filter(df, date_col='datetime'):
    """Áp dụng bộ lọc toàn cục cho DataFrame"""
    if not enable_global_filter or df is None or df.empty:
        return df

    try:
        # Kiểm tra xem cột datetime có tồn tại không
        if date_col not in df.columns:
            # Nếu không có cột datetime, bỏ qua filter (dữ liệu theo tuần/tháng)
            return df

        filtered_df = df.copy()

        # Áp dụng filter ngày
        if global_date_filter is not None:
            # Kiểm tra nếu là tuple/list với 2 phần tử
            if isinstance(global_date_filter, (list, tuple)) and len(global_date_filter) == 2:
                start_date, end_date = global_date_filter
                if start_date is not None and end_date is not None:
                    filtered_df = filtered_df[
                        (filtered_df[date_col] >= pd.to_datetime(start_date)) &
                        (filtered_df[date_col] <= pd.to_datetime(end_date))
                    ]
            # Nếu chỉ là 1 ngày, filter từ ngày đó trở đi
            elif global_date_filter is not None:
                filtered_df = filtered_df[filtered_df[date_col] >= pd.to_datetime(global_date_filter)]

        return filtered_df
    except Exception as e:
        st.warning(f"⚠️ Bộ lọc toàn cục không áp dụng được cho dữ liệu này (dữ liệu theo tuần/tháng)")
        return df

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
                                         mode='lines', name='Đúng hạn',
                                         line=dict(color='green')))
        fig_processed.add_trace(go.Scatter(x=processed_summary['period'],
                                         y=processed_summary['processed_late'],
                                         mode='lines', name='Trễ hạn',
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

# CSS cho tabs 2 hàng
st.markdown("""
<style>
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
}
.stTabs [data-baseweb="tab"] {
    height: auto;
    white-space: nowrap;
    padding: 8px 12px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
}
</style>
""", unsafe_allow_html=True)

# Tạo tabs với tên ngắn gọn hơn
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10, tab11, tab12 = st.tabs([
    "🏠 Tổng quan",
    "📥 VB Đến",
    "📤 VB Đi",
    "🚗 Tổ xe",
    "📞 Tổng đài",
    "👥 Thư ký",
    "🅿️ Bãi xe",
    "🎉 Sự kiện",
    "📋 Công việc",
    "📅 Lịch họp",
    "🏢 Phòng họp",
    "🔗 Khác"
])

# Tab 1: Tổng quan
with tab1:
    st.markdown('<div class="tab-header">📊 Tổng quan Phòng Hành chính</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ GitHub
    df_summary = load_data_from_github('tonghop.json')

    if df_summary is not None:
        # Tạo cột datetime
        df_summary['datetime'] = pd.to_datetime(df_summary[['year', 'month', 'date']].rename(columns={'date': 'day'}))

        # Chuẩn hóa category names
        df_summary['category_clean'] = df_summary['category'].str.replace(' ', '_').str.lower()
        df_summary['category_vi'] = df_summary['category'].map({
            'Van ban den': '📥 Văn bản đến',
            'Van ban phat hanh di': '📤 Văn bản đi',
            'Van ban phat hanh quyet dinh': '📜 Quyết định',
            'Van ban phat hanhquy dinh': '📋 Quy định',
            'Van ban phat hanhquy trinh': '📋 Quy trình',
            'Van ban phat hanh hop dong': '📝 Hợp đồng',
            'Quan ly phong hop': '🏢 Phòng họp',
            'Quan ly cong viec': '💼 Công việc'
        }).fillna('🔸 ' + df_summary['category'])
    
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
                    st.metric("Tổng", f"{int(category_data['count'].sum()):,}")
                
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
    
    # Load dữ liệu từ GitHub
    df = load_data_from_github('vanbanden.json')

    if df is not None:
        # Xử lý dữ liệu
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

    if df is not None:
        # Áp dụng filter toàn cục
        df = apply_global_filter(df)
        # Thống kê tổng quan
        st.markdown("### 📊 Thống kê tổng quan")

        # Hàng 1: Thống kê chính
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            total_docs = df['total_incoming'].sum()
            st.metric("📑 Tổng văn bản", f"{int(total_docs):,}")

        with col2:
            avg_daily = df['total_incoming'].mean()
            st.metric("📈 Trung bình/ngày", f"{avg_daily:.1f}")

        with col3:
            total_on_time = df['processed_on_time'].sum()
            st.metric("✅ Xử lý đúng hạn", f"{int(total_on_time):,}")

        with col4:
            total_late = df['processed_late'].sum()
            st.metric("⚠️ Xử lý trễ hạn", f"{int(total_late):,}")

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
            st.metric("🔕 Không cần phản hồi", f"{int(no_response):,}")

        with col2:
            need_response = df['response_required'].sum()
            st.metric("📢 Cần phản hồi", f"{int(need_response):,}")

        with col3:
            vanban_response = df['response_required_VanBan'].sum()
            st.metric("📄 PH Văn bản", f"{int(vanban_response):,}")

        with col4:
            email_response = df['response_required_Email'].sum()
            st.metric("📧 PH Email", f"{int(email_response):,}")

        with col5:
            phone_response = df['response_required_DienThoai'].sum()
            st.metric("📞 PH Điện thoại", f"{int(phone_response):,}")

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
    
    # Load dữ liệu từ GitHub
    df_out = load_data_from_github('vanbanphathanh.json')

    if df_out is not None:
        # Flatten nested structure để tạo các cột _total
        for index, row in df_out.iterrows():
            # Extract totals from nested objects
            if 'contracts' in row and isinstance(row['contracts'], dict):
                df_out.loc[index, 'contracts_total'] = row['contracts'].get('total', 0)
            if 'decisions' in row and isinstance(row['decisions'], dict):
                df_out.loc[index, 'decisions_total'] = row['decisions'].get('total', 0)
            if 'regulations' in row and isinstance(row['regulations'], dict):
                df_out.loc[index, 'regulations_total'] = row['regulations'].get('total', 0)
            if 'rules' in row and isinstance(row['rules'], dict):
                df_out.loc[index, 'rules_total'] = row['rules'].get('total', 0)
            if 'procedures' in row and isinstance(row['procedures'], dict):
                df_out.loc[index, 'procedures_total'] = row['procedures'].get('total', 0)
            if 'instruct' in row and isinstance(row['instruct'], dict):
                df_out.loc[index, 'instruct_total'] = row['instruct'].get('total', 0)

        # Xử lý datetime
        if 'datetime' not in df_out.columns:
            if all(col in df_out.columns for col in ['year', 'month', 'date']):
                df_out['datetime'] = pd.to_datetime(df_out[['year', 'month', 'date']].rename(columns={'date': 'day'}))
            elif all(col in df_out.columns for col in ['Year', 'Month', 'Date']):
                df_out['datetime'] = pd.to_datetime(df_out[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))

        # Thêm các cột cần thiết
        df_out['weekday'] = df_out['datetime'].dt.day_name()
        df_out['weekday_vi'] = df_out['weekday'].map({
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
        })
        df_out['year'] = df_out['datetime'].dt.year
        df_out['month'] = df_out['datetime'].dt.month
        df_out['week'] = df_out['datetime'].dt.isocalendar().week

        # Tính total_outgoing (tổng các loại văn bản bao gồm cả documents)
        total_columns = ['documents', 'contracts_total', 'decisions_total', 'regulations_total',
                       'rules_total', 'procedures_total', 'instruct_total']
        for col in total_columns:
            if col not in df_out.columns:
                df_out[col] = 0

        df_out['total_outgoing'] = df_out[total_columns].sum(axis=1)

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
                st.metric("📄 Tổng văn bản đi", f"{int(total_outgoing):,}")

            with col2:
                st.metric("📝 Văn bản phát hành", f"{int(total_docs):,}")

            with col3:
                st.metric("📁 Hợp đồng", f"{int(total_contracts):,}")

            with col4:
                st.metric("⚖️ Quyết định", f"{int(total_decisions):,}")
            
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
                st.metric("📜 Quy định", f"{int(total_regulations):,}")

            with col2:
                st.metric("📋 Quy chế", f"{int(total_rules):,}")

            with col3:
                st.metric("🔄 Thủ tục", f"{int(total_procedures):,}")

            with col4:
                st.metric("📚 Hướng dẫn", f"{int(total_instruct):,}")
            
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

# Tab 9: Quản lý công việc
with tab9:
    st.markdown('<div class="tab-header">📋 Quản lý Công Việc</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ GitHub
    df = load_data_from_github('congviec.json')

    if df is not None:
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

        # Return both dataframes
        df_all_tasks = df
        if detail_rows:
            df_detail_tasks = pd.DataFrame(detail_rows)
            # Tính completion_rate cho detail
            df_detail_tasks['completion_rate'] = df_detail_tasks.apply(lambda row:
                (row['tasks_completed_on_time'] / row['tasks_assigned'] * 100)
                if row['tasks_assigned'] > 0 else 0, axis=1)
        else:
            df_detail_tasks = pd.DataFrame()
    else:
        df_all_tasks = None
        df_detail_tasks = None

    if df_all_tasks is not None and df_detail_tasks is not None:
            # Áp dụng filter toàn cục
            df_all_tasks_filtered = apply_global_filter(df_all_tasks)
            df_detail_tasks_filtered = apply_global_filter(df_detail_tasks)

            # Kiểm tra dữ liệu sau khi filter
            if df_all_tasks_filtered.empty:
                st.warning("⚠️ Không có dữ liệu nào phù hợp với bộ lọc hiện tại. Vui lòng điều chỉnh bộ lọc.")
                st.stop()
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

# Tab 10: Quản lý lịch họp
with tab10:
    st.markdown('<div class="tab-header">📅 Quản lý Lịch Họp</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ GitHub
    df_meetings = load_data_from_github('lichhop.json')

    if df_meetings is not None:
        # Xử lý dữ liệu
        if 'datetime' not in df_meetings.columns:
            if all(col in df_meetings.columns for col in ['year', 'month', 'date']):
                df_meetings['datetime'] = pd.to_datetime(df_meetings[['year', 'month', 'date']].rename(columns={'date': 'day'}))
            elif all(col in df_meetings.columns for col in ['Year', 'Month', 'Date']):
                df_meetings['datetime'] = pd.to_datetime(df_meetings[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))

        # Thêm các cột cần thiết
        df_meetings['weekday'] = df_meetings['datetime'].dt.day_name()
        df_meetings['weekday_vi'] = df_meetings['weekday'].map({
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
        })
        df_meetings['year'] = df_meetings['datetime'].dt.year
        df_meetings['month'] = df_meetings['datetime'].dt.month
        df_meetings['week'] = df_meetings['datetime'].dt.isocalendar().week

        # Thêm cột day_type dựa trên weekday
        df_meetings['day_type'] = df_meetings['weekday'].map({
            'Monday': 'Ngày làm việc', 'Tuesday': 'Ngày làm việc', 'Wednesday': 'Ngày làm việc',
            'Thursday': 'Ngày làm việc', 'Friday': 'Ngày làm việc',
            'Saturday': 'Cuối tuần', 'Sunday': 'Cuối tuần'
        })

        # Đảm bảo cột meeting_schedules tồn tại
        if 'meeting_schedules' not in df_meetings.columns:
            df_meetings['meeting_schedules'] = 0

        # Thêm cột meeting_level dựa trên số lượng meeting_schedules
        df_meetings['meeting_level'] = df_meetings['meeting_schedules'].apply(lambda x:
            'Rất ít' if x <= 2 else
            'Ít' if x <= 5 else
            'Trung bình' if x <= 10 else
            'Nhiều' if x <= 20 else
            'Rất nhiều'
        )

    if df_meetings is not None:
            # Áp dụng filter toàn cục
            df_meetings = apply_global_filter(df_meetings)
            
            # Thống kê tổng quan
            st.markdown("### 📊 Thống kê tổng quan lịch họp")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                total_meetings = df_meetings['meeting_schedules'].sum()
                st.metric("📅 Tổng cuộc họp", f"{int(total_meetings):,}")
            
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
                | 🟡 **Trung bình** | 6-10 cuộc | Ngày khá bận rộn với nhiều cuộc họp |
                | 🟠 **Nhiều** | 11-20 cuộc | Ngày rất bận với mật độ họp cao |
                | 🔴 **Rất nhiều** | >20 cuộc | Ngày cực kỳ bận rộn, liên tục các cuộc họp |

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

# Tab 11: Quản lý phòng họp
with tab11:
    st.markdown('<div class="tab-header">🏢 Quản lý Phòng Họp</div>', unsafe_allow_html=True)
    
    # Load dữ liệu từ GitHub
    df_rooms = load_data_from_github('phonghop.json')

    if df_rooms is not None:
        # Tạo cột datetime
        df_rooms['datetime'] = pd.to_datetime(df_rooms[['Year', 'Month', 'Date']].rename(columns={'Date': 'day'}))
        df_rooms['weekday'] = df_rooms['datetime'].dt.day_name()
        df_rooms['weekday_vi'] = df_rooms['weekday'].map({
            'Monday': 'Thứ 2', 'Tuesday': 'Thứ 3', 'Wednesday': 'Thứ 4',
            'Thursday': 'Thứ 5', 'Friday': 'Thứ 6', 'Saturday': 'Thứ 7', 'Sunday': 'Chủ nhật'
        })
        df_rooms['month_vi'] = df_rooms['Month'].map({
            1: 'Tháng 1', 2: 'Tháng 2', 3: 'Tháng 3', 4: 'Tháng 4',
            5: 'Tháng 5', 6: 'Tháng 6', 7: 'Tháng 7', 8: 'Tháng 8',
            9: 'Tháng 9', 10: 'Tháng 10', 11: 'Tháng 11', 12: 'Tháng 12'
        })

        # Tính toán các chỉ số
        df_rooms['cancel_rate'] = (df_rooms['register_room_cancel'] / df_rooms['register_room'] * 100).fillna(0).round(1)
        df_rooms['net_bookings'] = df_rooms['register_room'] - df_rooms['register_room_cancel']
        df_rooms['is_weekend'] = df_rooms['weekday'].isin(['Saturday', 'Sunday'])
        df_rooms['day_type'] = df_rooms['is_weekend'].map({False: 'Ngày làm việc', True: 'Cuối tuần'})

        # Áp dụng filter toàn cục
        df_rooms = apply_global_filter(df_rooms)
    
    if df_rooms is not None and not df_rooms.empty:
        # Metrics tổng quan
        col1, col2, col3, col4 = st.columns(4)
        
        total_bookings = df_rooms['register_room'].sum()
        total_cancels = df_rooms['register_room_cancel'].sum()
        avg_daily = df_rooms['register_room'].mean()
        cancel_rate_avg = (total_cancels / total_bookings * 100) if total_bookings > 0 else 0
        
        with col1:
            st.metric("📅 Tổng đăng ký", f"{int(total_bookings):,}")
        with col2:
            st.metric("❌ Tổng hủy", f"{int(total_cancels):,}")
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

# Hàm tạo pivot table cho Tổ xe
def create_vehicle_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích Tổ xe theo thời gian")

    # CSS cho table lớn hơn và đẹp hơn
    st.markdown("""
    <style>
    .pivot-table-vehicle {
        font-size: 16px !important;
        font-weight: 500;
    }
    .pivot-table-vehicle td {
        padding: 12px 8px !important;
        text-align: center !important;
    }
    .pivot-table-vehicle th {
        padding: 15px 8px !important;
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        font-size: 17px !important;
    }
    .increase { color: #16a085; font-weight: 600; }
    .decrease { color: #e74c3c; font-weight: 600; }
    .neutral { color: #7f8c8d; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Tuần', 'Tháng', 'Năm'],  # Thêm Năm cho dữ liệu 2025
            index=0,  # Mặc định là Tuần
            key="vehicle_period_type"
        )

    # Dữ liệu Tổ xe có cấu trúc khác - có thể có cột tuần/tháng trực tiếp
    has_time_data = False
    df_period = df.copy()

    # Kiểm tra các cột thời gian - data có Tuần và Tháng
    if 'Tuần' in df.columns or 'Tháng' in df.columns:
        has_time_data = True

        # Chuẩn bị dữ liệu dựa trên period_type được chọn
        if period_type == 'Tuần' and 'Tuần' in df.columns:
            df_period['period'] = 'W' + df_period['Tuần'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
        elif period_type == 'Tháng' and 'Tháng' in df.columns:
            df_period['period'] = 'T' + df_period['Tháng'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tháng'], errors='coerce')
        elif period_type == 'Năm':
            # Dữ liệu năm 2025 - tạo period năm
            df_period['period'] = '2025'
            df_period['period_sort'] = 2025
        else:
            # Fallback: sử dụng Tuần làm mặc định
            if 'Tuần' in df.columns:
                df_period['period'] = 'W' + df_period['Tuần'].astype(str)
                df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
            else:
                has_time_data = False

    elif 'datetime' in df.columns:
        # Xử lý datetime nếu có
        has_time_data = True
        df_period['datetime'] = pd.to_datetime(df_period['datetime'])
        df_period['year'] = df_period['datetime'].dt.year
        df_period['month'] = df_period['datetime'].dt.month
        df_period['week'] = df_period['datetime'].dt.isocalendar().week

        if period_type == 'Tuần':
            df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
        elif period_type == 'Tháng':
            df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    else:
        # Không có dữ liệu thời gian, tạo period giả lập
        has_time_data = False

    if has_time_data:
        # Tạo pivot table với các chỉ số Tổ xe - mở rộng để bao gồm tất cả metrics
        vehicle_metrics = ['so_chuyen', 'km_chay', 'doanh_thu', 'nhien_lieu', 'bao_duong', 'hai_long', 'km_hanh_chinh', 'km_cuu_thuong', 'phieu_khao_sat']

        # Nếu dữ liệu không có các cột metric, tạo chúng từ Nội dung/Số liệu
        if 'Nội dung' in df_period.columns and 'Số liệu' in df_period.columns:
            for metric in vehicle_metrics:
                df_period[metric] = 0

            # Mapping các metric từ Nội dung - dựa trên data thực tế
            metric_mapping = {
                'so_chuyen': ['Số chuyến xe'],
                'km_chay': ['Tổng km chạy'],
                'doanh_thu': ['Doanh thu Tổ xe'],
                'nhien_lieu': ['Tổng số nhiên liệu tiêu thụ'],
                'bao_duong': ['Chi phí bảo dưỡng'],
                'hai_long': ['Tỷ lệ hài lòng của khách hàng'],
                'km_hanh_chinh': ['Km chạy của Km chạy của xe hành chính', 'Km chạy của xe hành chính', 'Km chạy của hành chính'],
                'km_cuu_thuong': ['Km chạy của Km chạy của xe cứu thương', 'Km chạy của xe cứu thương'],
                'phieu_khao_sat': ['Số phiếu khảo sát hài lòng']
            }

            for metric, content_names in metric_mapping.items():
                for content_name in content_names:
                    mask = df_period['Nội dung'] == content_name
                    df_period.loc[mask, metric] = pd.to_numeric(df_period.loc[mask, 'Số liệu'], errors='coerce').fillna(0)

        # Tạo pivot data
        pivot_data = df_period.groupby(['period', 'period_sort'])[vehicle_metrics].sum().reset_index()
        pivot_data = pivot_data.sort_values('period_sort', ascending=False)

        # Tính toán biến động so với kỳ trước
        for col in vehicle_metrics:
            pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
            pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
            pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
            pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

        # Tạo DataFrame hiển thị với biến động trong cùng cell
        display_data = pivot_data.copy()

        # Hàm tạo cell kết hợp giá trị và biến động với comma formatting
        def format_cell_with_change(row, col):
            current_val = row[col]
            change_val = row[f'{col}_change']
            change_pct = row[f'{col}_change_pct']
            prev_val = row[f'{col}_prev']

            # Nếu không có dữ liệu kỳ trước, chỉ hiển thị giá trị hiện tại với comma
            if pd.isna(prev_val) or prev_val == 0:
                return f"{int(current_val):,}"

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

            # Trả về HTML với màu sắc và comma formatting
            return f"""<div style="text-align: center; line-height: 1.2;">
                <div style="font-size: 16px; font-weight: 600;">{int(current_val):,}</div>
                <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                    {arrow} {sign}{int(change_val):,} ({change_pct:+.1f}%)
                </div>
            </div>"""

        # Tạo cột hiển thị mới
        display_columns = ['period']
        column_names = {f'period': f'{period_type}'}

        for col in vehicle_metrics:
            new_col = f'{col}_display'
            display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
            display_columns.append(new_col)

            # Mapping tên cột cho hiển thị
            metric_names = {
                'so_chuyen': 'Số chuyến',
                'km_chay': 'Tổng km',
                'doanh_thu': 'Doanh thu (VNĐ)',
                'nhien_lieu': 'Nhiên liệu (L)',
                'bao_duong': 'Bảo dưỡng (VNĐ)',
                'hai_long': 'Hài lòng (%)',
                'km_hanh_chinh': 'Km hành chính',
                'km_cuu_thuong': 'Km cứu thương',
                'phieu_khao_sat': 'Phiếu khảo sát'
            }
            column_names[new_col] = metric_names.get(col, col)

        st.markdown(f"#### 📋 Tổng hợp theo {period_type} (bao gồm biến động)")

        # Hiển thị bảng với HTML để render màu sắc
        df_display = display_data[display_columns].rename(columns=column_names)

        # Tạo HTML table với sticky header
        html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table class='pivot-table-vehicle' style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

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
                style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd;"
                html_table += f"<td style='{style}'>{cell_value}</td>"
            html_table += "</tr>"
        html_table += "</tbody></table></div>"

        st.markdown(html_table, unsafe_allow_html=True)

    else:
        st.info("📊 Dữ liệu chưa có thông tin thời gian để tạo pivot table")
        # Hiển thị dữ liệu cơ bản với comma formatting
        if 'Nội dung' in df.columns and 'Số liệu' in df.columns:
            summary_data = df[['Nội dung', 'Số liệu']].copy()
            # Clean and format numbers with commas
            def format_summary_number(x):
                cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
                numeric_val = pd.to_numeric(cleaned, errors='coerce')
                if pd.isna(numeric_val):
                    return str(x)
                elif numeric_val >= 1:
                    return f"{numeric_val:,.0f}"
                else:
                    return f"{numeric_val:.1f}"

            summary_data['Số liệu'] = summary_data['Số liệu'].apply(format_summary_number)
            st.dataframe(summary_data, use_container_width=True, hide_index=True)

    return period_type

# Hàm tạo pivot table cho Tổng đài
def create_call_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích Tổng đài theo thời gian")

    # CSS cho table lớn hơn và đẹp hơn
    st.markdown("""
    <style>
    .pivot-table-call {
        font-size: 16px !important;
        font-weight: 500;
    }
    .pivot-table-call td {
        padding: 12px 8px !important;
        text-align: center !important;
    }
    .pivot-table-call th {
        padding: 15px 8px !important;
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        font-size: 17px !important;
    }
    .increase { color: #16a085; font-weight: 600; }
    .decrease { color: #e74c3c; font-weight: 600; }
    .neutral { color: #7f8c8d; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Tuần', 'Tháng', 'Năm'],  # Thêm Năm cho dữ liệu 2025
            index=0,  # Mặc định là Tuần
            key="call_period_type"
        )

    # Dữ liệu Tổng đài có cấu trúc khác - có thể có cột tuần/tháng trực tiếp
    has_time_data = False
    df_period = df.copy()

    # Kiểm tra các cột thời gian - data có Tuần và Tháng
    if 'Tuần' in df.columns or 'Tháng' in df.columns:
        has_time_data = True

        # Chuẩn bị dữ liệu dựa trên period_type được chọn
        if period_type == 'Tuần' and 'Tuần' in df.columns:
            df_period['period'] = 'W' + df_period['Tuần'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
        elif period_type == 'Tháng' and 'Tháng' in df.columns:
            df_period['period'] = 'T' + df_period['Tháng'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tháng'], errors='coerce')
        elif period_type == 'Năm':
            # Dữ liệu năm 2025 - tạo period năm
            df_period['period'] = '2025'
            df_period['period_sort'] = 2025
        else:
            # Fallback: sử dụng Tuần làm mặc định
            if 'Tuần' in df.columns:
                df_period['period'] = 'W' + df_period['Tuần'].astype(str)
                df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
            else:
                has_time_data = False

    elif 'datetime' in df.columns:
        # Xử lý datetime nếu có
        has_time_data = True
        df_period['datetime'] = pd.to_datetime(df_period['datetime'])
        df_period['year'] = df_period['datetime'].dt.year
        df_period['month'] = df_period['datetime'].dt.month
        df_period['week'] = df_period['datetime'].dt.isocalendar().week

        if period_type == 'Tuần':
            df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
        elif period_type == 'Tháng':
            df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    else:
        # Không có dữ liệu thời gian, tạo period giả lập
        has_time_data = False

    if has_time_data:
        # Tạo pivot table với các chỉ số Tổng đài - mở rộng để bao gồm tất cả metrics
        call_metrics = ['tong_goi', 'nho_tu_choi', 'nho_ko_bat', 'ty_le_tra_loi', 'hotline']

        # Nếu dữ liệu không có các cột metric, tạo chúng từ Nội dung/Số liệu
        if 'Nội dung' in df_period.columns and 'Số liệu' in df_period.columns:
            for metric in call_metrics:
                df_period[metric] = 0

            # Mapping các metric từ Nội dung - dựa trên data thực tế
            metric_mapping = {
                'tong_goi': ['Tổng số cuộc gọi đến Bệnh viện'],
                'nho_tu_choi': ['Tổng số cuộc gọi nhỡ do từ chối'],
                'nho_ko_bat': ['Tổng số cuộc gọi nhỡ do không bắt máy'],
                'ty_le_tra_loi': ['Tỷ lệ trả lời'],
                'hotline': ['Hottline']
            }

            for metric, content_names in metric_mapping.items():
                for content_name in content_names:
                    mask = df_period['Nội dung'] == content_name
                    df_period.loc[mask, metric] = pd.to_numeric(df_period.loc[mask, 'Số liệu'], errors='coerce').fillna(0)

        # Tạo pivot data
        pivot_data = df_period.groupby(['period', 'period_sort'])[call_metrics].sum().reset_index()
        pivot_data = pivot_data.sort_values('period_sort', ascending=False)

        # Tính toán biến động so với kỳ trước
        for col in call_metrics:
            pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
            pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
            pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
            pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

        # Tạo DataFrame hiển thị với biến động trong cùng cell
        display_data = pivot_data.copy()

        # Hàm tạo cell kết hợp giá trị và biến động với comma formatting
        def format_cell_with_change(row, col):
            current_val = row[col]
            change_val = row[f'{col}_change']
            change_pct = row[f'{col}_change_pct']
            prev_val = row[f'{col}_prev']

            # Nếu không có dữ liệu kỳ trước, chỉ hiển thị giá trị hiện tại với comma
            if pd.isna(prev_val) or prev_val == 0:
                if col == 'ty_le_tra_loi':
                    return f"{current_val:.1f}%"
                return f"{int(current_val):,}"

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

            # Trả về HTML với màu sắc và comma formatting
            if col == 'ty_le_tra_loi':
                return f"""<div style="text-align: center; line-height: 1.2;">
                    <div style="font-size: 16px; font-weight: 600;">{current_val:.1f}%</div>
                    <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                        {arrow} {sign}{change_val:.1f} ({change_pct:+.1f}%)
                    </div>
                </div>"""
            else:
                return f"""<div style="text-align: center; line-height: 1.2;">
                    <div style="font-size: 16px; font-weight: 600;">{int(current_val):,}</div>
                    <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                        {arrow} {sign}{int(change_val):,} ({change_pct:+.1f}%)
                    </div>
                </div>"""

        # Tạo cột hiển thị mới
        display_columns = ['period']
        column_names = {f'period': f'{period_type}'}

        for col in call_metrics:
            new_col = f'{col}_display'
            display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
            display_columns.append(new_col)

            # Mapping tên cột cho hiển thị
            metric_names = {
                'tong_goi': 'Tổng cuộc gọi',
                'nho_tu_choi': 'Nhỡ (từ chối)',
                'nho_ko_bat': 'Nhỡ (không bắt)',
                'ty_le_tra_loi': 'Tỷ lệ trả lời (%)',
                'hotline': 'Hotline'
            }
            column_names[new_col] = metric_names.get(col, col)

        st.markdown(f"#### 📋 Tổng hợp theo {period_type} (bao gồm biến động)")

        # Hiển thị bảng với HTML để render màu sắc
        df_display = display_data[display_columns].rename(columns=column_names)

        # Tạo HTML table với sticky header
        html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table class='pivot-table-call' style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

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
                style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd;"
                html_table += f"<td style='{style}'>{cell_value}</td>"
            html_table += "</tr>"
        html_table += "</tbody></table></div>"

        st.markdown(html_table, unsafe_allow_html=True)

    else:
        st.info("📊 Dữ liệu chưa có thông tin thời gian để tạo pivot table")
        # Hiển thị dữ liệu cơ bản với comma formatting
        if 'Nội dung' in df.columns and 'Số liệu' in df.columns:
            summary_data = df[['Nội dung', 'Số liệu']].copy()
            # Clean and format numbers with commas
            def format_summary_number(x):
                cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
                numeric_val = pd.to_numeric(cleaned, errors='coerce')
                if pd.isna(numeric_val):
                    return str(x)
                elif numeric_val >= 1:
                    return f"{numeric_val:,.0f}"
                else:
                    return f"{numeric_val:.1f}"

            summary_data['Số liệu'] = summary_data['Số liệu'].apply(format_summary_number)
            st.dataframe(summary_data, use_container_width=True, hide_index=True)

    return period_type

# Hàm tạo pivot table cho Hệ thống thư ký
def create_secretary_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích Hệ thống thư ký theo thời gian")

    # CSS cho table lớn hơn và đẹp hơn
    st.markdown("""
    <style>
    .pivot-table-secretary {
        font-size: 16px !important;
        font-weight: 500;
    }
    .pivot-table-secretary td {
        padding: 12px 8px !important;
        text-align: center !important;
    }
    .pivot-table-secretary th {
        padding: 15px 8px !important;
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        font-size: 17px !important;
    }
    .increase { color: #16a085; font-weight: 600; }
    .decrease { color: #e74c3c; font-weight: 600; }
    .neutral { color: #7f8c8d; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Tuần', 'Tháng', 'Năm'],  # Thêm Năm cho dữ liệu 2025
            index=0,  # Mặc định là Tuần
            key="secretary_period_type"
        )

    # Dữ liệu Hệ thống thư ký có cấu trúc khác - có thể có cột tuần/tháng trực tiếp
    has_time_data = False
    df_period = df.copy()

    # Kiểm tra các cột thời gian - data có Tuần và Tháng
    if 'Tuần' in df.columns or 'Tháng' in df.columns:
        has_time_data = True

        # Chuẩn bị dữ liệu dựa trên period_type được chọn
        if period_type == 'Tuần' and 'Tuần' in df.columns:
            df_period['period'] = 'W' + df_period['Tuần'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
        elif period_type == 'Tháng' and 'Tháng' in df.columns:
            df_period['period'] = 'T' + df_period['Tháng'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tháng'], errors='coerce')
        elif period_type == 'Năm':
            # Dữ liệu năm 2025 - tạo period năm
            df_period['period'] = '2025'
            df_period['period_sort'] = 2025
        else:
            # Fallback: sử dụng Tuần làm mặc định
            if 'Tuần' in df.columns:
                df_period['period'] = 'W' + df_period['Tuần'].astype(str)
                df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
            else:
                has_time_data = False

    elif 'datetime' in df.columns:
        # Xử lý datetime nếu có
        has_time_data = True
        df_period['datetime'] = pd.to_datetime(df_period['datetime'])
        df_period['year'] = df_period['datetime'].dt.year
        df_period['month'] = df_period['datetime'].dt.month
        df_period['week'] = df_period['datetime'].dt.isocalendar().week

        if period_type == 'Tuần':
            df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
        elif period_type == 'Tháng':
            df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    else:
        # Không có dữ liệu thời gian, tạo period giả lập
        has_time_data = False

    if has_time_data:
        # Tạo pivot table với các chỉ số Hệ thống thư ký - mở rộng để bao gồm tất cả metrics
        secretary_metrics = ['tong_tk', 'tuyen_moi', 'nghi_viec', 'hanh_chinh', 'chuyen_mon', 'dao_tao']

        # Nếu dữ liệu không có các cột metric, tạo chúng từ Nội dung/Số liệu
        if 'Nội dung' in df_period.columns and 'Số liệu' in df_period.columns:
            for metric in secretary_metrics:
                df_period[metric] = 0

            # Mapping các metric từ Nội dung - dựa trên data thực tế
            metric_mapping = {
                'tong_tk': ['Tổng số thư ký'],
                'tuyen_moi': ['Số thư ký được tuyển dụng'],
                'nghi_viec': ['Số thư ký nghỉ việc'],
                'hanh_chinh': ['- Thư ký hành chính'],
                'chuyen_mon': ['- Thư ký chuyên môn'],
                'dao_tao': ['Số buổi tập huấn, đào tạo cho thư ký']
            }

            for metric, content_names in metric_mapping.items():
                for content_name in content_names:
                    mask = df_period['Nội dung'] == content_name
                    df_period.loc[mask, metric] = pd.to_numeric(df_period.loc[mask, 'Số liệu'], errors='coerce').fillna(0)

        # Tạo pivot data
        pivot_data = df_period.groupby(['period', 'period_sort'])[secretary_metrics].sum().reset_index()
        pivot_data = pivot_data.sort_values('period_sort', ascending=False)

        # Tính toán biến động so với kỳ trước
        for col in secretary_metrics:
            pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
            pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
            pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
            pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

        # Tạo DataFrame hiển thị với biến động trong cùng cell
        display_data = pivot_data.copy()

        # Hàm tạo cell kết hợp giá trị và biến động với comma formatting
        def format_cell_with_change(row, col):
            current_val = row[col]
            change_val = row[f'{col}_change']
            change_pct = row[f'{col}_change_pct']
            prev_val = row[f'{col}_prev']

            # Nếu không có dữ liệu kỳ trước, chỉ hiển thị giá trị hiện tại với comma
            if pd.isna(prev_val) or prev_val == 0:
                return f"{int(current_val):,}"

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

            # Trả về HTML với màu sắc và comma formatting
            return f"""<div style="text-align: center; line-height: 1.2;">
                <div style="font-size: 16px; font-weight: 600;">{int(current_val):,}</div>
                <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                    {arrow} {sign}{int(change_val):,} ({change_pct:+.1f}%)
                </div>
            </div>"""

        # Tạo cột hiển thị mới
        display_columns = ['period']
        column_names = {f'period': f'{period_type}'}

        for col in secretary_metrics:
            new_col = f'{col}_display'
            display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
            display_columns.append(new_col)

            # Mapping tên cột cho hiển thị
            metric_names = {
                'tong_tk': 'Tổng thư ký',
                'tuyen_moi': 'Tuyển mới',
                'nghi_viec': 'Nghỉ việc',
                'hanh_chinh': 'Hành chính',
                'chuyen_mon': 'Chuyên môn',
                'dao_tao': 'Đào tạo (buổi)'
            }
            column_names[new_col] = metric_names.get(col, col)

        st.markdown(f"#### 📋 Tổng hợp theo {period_type} (bao gồm biến động)")

        # Hiển thị bảng với HTML để render màu sắc
        df_display = display_data[display_columns].rename(columns=column_names)

        # Tạo HTML table với sticky header
        html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table class='pivot-table-secretary' style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

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
                style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd;"
                html_table += f"<td style='{style}'>{cell_value}</td>"
            html_table += "</tr>"
        html_table += "</tbody></table></div>"

        st.markdown(html_table, unsafe_allow_html=True)

    else:
        st.info("📊 Dữ liệu chưa có thông tin thời gian để tạo pivot table")
        # Hiển thị dữ liệu cơ bản với comma formatting
        if 'Nội dung' in df.columns and 'Số liệu' in df.columns:
            summary_data = df[['Nội dung', 'Số liệu']].copy()
            # Clean and format numbers with commas
            def format_summary_number(x):
                cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
                numeric_val = pd.to_numeric(cleaned, errors='coerce')
                if pd.isna(numeric_val):
                    return str(x)
                elif numeric_val >= 1:
                    return f"{numeric_val:,.0f}"
                else:
                    return f"{numeric_val:.1f}"

            summary_data['Số liệu'] = summary_data['Số liệu'].apply(format_summary_number)
            st.dataframe(summary_data, use_container_width=True, hide_index=True)

    return period_type

# Hàm tạo pivot table cho Bãi giữ xe
def create_parking_pivot_table(df):
    st.markdown("### 📊 Bảng Pivot - Phân tích Bãi giữ xe theo thời gian")

    # CSS cho table lớn hơn và đẹp hơn
    st.markdown("""
    <style>
    .pivot-table-parking {
        font-size: 16px !important;
        font-weight: 500;
    }
    .pivot-table-parking td {
        padding: 12px 8px !important;
        text-align: center !important;
    }
    .pivot-table-parking th {
        padding: 15px 8px !important;
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        font-size: 17px !important;
    }
    .increase { color: #16a085; font-weight: 600; }
    .decrease { color: #e74c3c; font-weight: 600; }
    .neutral { color: #7f8c8d; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Tuần', 'Tháng', 'Năm'],  # Thêm Năm cho dữ liệu 2025
            index=0,  # Mặc định là Tuần
            key="parking_period_type"
        )

    # Dữ liệu Bãi giữ xe có cấu trúc khác - có thể có cột tuần/tháng trực tiếp
    has_time_data = False
    df_period = df.copy()

    # Kiểm tra các cột thời gian - data có Tuần và Tháng
    if 'Tuần' in df.columns or 'Tháng' in df.columns:
        has_time_data = True

        # Chuẩn bị dữ liệu dựa trên period_type được chọn
        if period_type == 'Tuần' and 'Tuần' in df.columns:
            df_period['period'] = 'W' + df_period['Tuần'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
        elif period_type == 'Tháng' and 'Tháng' in df.columns:
            df_period['period'] = 'T' + df_period['Tháng'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tháng'], errors='coerce')
        elif period_type == 'Năm':
            # Dữ liệu năm 2025 - tạo period năm
            df_period['period'] = '2025'
            df_period['period_sort'] = 2025
        else:
            # Fallback: sử dụng Tuần làm mặc định
            if 'Tuần' in df.columns:
                df_period['period'] = 'W' + df_period['Tuần'].astype(str)
                df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
            else:
                has_time_data = False

    elif 'datetime' in df.columns:
        # Xử lý datetime nếu có
        has_time_data = True
        df_period['datetime'] = pd.to_datetime(df_period['datetime'])
        df_period['year'] = df_period['datetime'].dt.year
        df_period['month'] = df_period['datetime'].dt.month
        df_period['week'] = df_period['datetime'].dt.isocalendar().week

        if period_type == 'Tuần':
            df_period['period'] = 'W' + df_period['week'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['week']
        elif period_type == 'Tháng':
            df_period['period'] = 'T' + df_period['month'].astype(str) + '-' + df_period['year'].astype(str)
            df_period['period_sort'] = df_period['year'] * 100 + df_period['month']
    else:
        # Không có dữ liệu thời gian, tạo period giả lập
        has_time_data = False

    if has_time_data:
        # Tạo pivot table với các chỉ số Bãi giữ xe - mở rộng để bao gồm tất cả metrics
        parking_metrics = ['ve_ngay', 've_thang', 'doanh_thu', 'cong_suat', 'ty_le_su_dung', 'khieu_nai']

        # Nếu dữ liệu không có các cột metric, tạo chúng từ Nội dung/Số liệu
        if 'Nội dung' in df_period.columns and 'Số liệu' in df_period.columns:
            for metric in parking_metrics:
                df_period[metric] = 0

            # Mapping các metric từ Nội dung - dựa trên data thực tế
            metric_mapping = {
                've_ngay': ['Tổng số lượt vé ngày'],
                've_thang': ['Tổng số lượt vé tháng'],
                'doanh_thu': ['Doanh thu'],
                'cong_suat': ['Công suất trung bình/ngày'],
                'ty_le_su_dung': ['Tỷ lệ sử dụng'],
                'khieu_nai': ['Số phản ánh khiếu nại']
            }

            for metric, content_names in metric_mapping.items():
                for content_name in content_names:
                    mask = df_period['Nội dung'] == content_name
                    df_period.loc[mask, metric] = pd.to_numeric(df_period.loc[mask, 'Số liệu'], errors='coerce').fillna(0)

        # Tạo pivot data
        pivot_data = df_period.groupby(['period', 'period_sort'])[parking_metrics].sum().reset_index()
        pivot_data = pivot_data.sort_values('period_sort', ascending=False)

        # Tính toán biến động so với kỳ trước
        for col in parking_metrics:
            pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
            pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
            pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
            pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

        # Tạo DataFrame hiển thị với biến động trong cùng cell
        display_data = pivot_data.copy()

        # Hàm tạo cell kết hợp giá trị và biến động với comma formatting
        def format_cell_with_change(row, col):
            current_val = row[col]
            change_val = row[f'{col}_change']
            change_pct = row[f'{col}_change_pct']
            prev_val = row[f'{col}_prev']

            # Nếu không có dữ liệu kỳ trước, chỉ hiển thị giá trị hiện tại với comma
            if pd.isna(prev_val) or prev_val == 0:
                if col == 'ty_le_su_dung':
                    return f"{current_val:.1f}%"
                return f"{int(current_val):,}"

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

            # Trả về HTML với màu sắc và comma formatting
            if col == 'ty_le_su_dung':
                return f"""<div style="text-align: center; line-height: 1.2;">
                    <div style="font-size: 16px; font-weight: 600;">{current_val:.1f}%</div>
                    <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                        {arrow} {sign}{change_val:.1f} ({change_pct:+.1f}%)
                    </div>
                </div>"""
            else:
                return f"""<div style="text-align: center; line-height: 1.2;">
                    <div style="font-size: 16px; font-weight: 600;">{int(current_val):,}</div>
                    <div class="{color_class}" style="font-size: 12px; margin-top: 2px;">
                        {arrow} {sign}{int(change_val):,} ({change_pct:+.1f}%)
                    </div>
                </div>"""

        # Tạo cột hiển thị mới
        display_columns = ['period']
        column_names = {f'period': f'{period_type}'}

        for col in parking_metrics:
            new_col = f'{col}_display'
            display_data[new_col] = display_data.apply(lambda row: format_cell_with_change(row, col), axis=1)
            display_columns.append(new_col)

            # Mapping tên cột cho hiển thị
            metric_names = {
                've_ngay': 'Vé ngày',
                've_thang': 'Vé tháng',
                'doanh_thu': 'Doanh thu (VND)',
                'cong_suat': 'Công suất',
                'ty_le_su_dung': 'Tỷ lệ SD (%)',
                'khieu_nai': 'Khiếu nại'
            }
            column_names[new_col] = metric_names.get(col, col)

        st.markdown(f"#### 📋 Tổng hợp theo {period_type} (bao gồm biến động)")

        # Hiển thị bảng với HTML để render màu sắc
        df_display = display_data[display_columns].rename(columns=column_names)

        # Tạo HTML table với sticky header
        html_table = "<div style='max-height: 400px; overflow-y: auto; border: 1px solid #ddd;'><table class='pivot-table-parking' style='width: 100%; border-collapse: collapse; font-size: 16px;'>"

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
                style = "padding: 12px 8px; text-align: center; border: 1px solid #ddd;"
                html_table += f"<td style='{style}'>{cell_value}</td>"
            html_table += "</tr>"
        html_table += "</tbody></table></div>"

        st.markdown(html_table, unsafe_allow_html=True)

    else:
        st.info("📊 Dữ liệu chưa có thông tin thời gian để tạo pivot table")
        # Hiển thị dữ liệu cơ bản với comma formatting
        if 'Nội dung' in df.columns and 'Số liệu' in df.columns:
            summary_data = df[['Nội dung', 'Số liệu']].copy()
            # Clean and format numbers with commas
            def format_summary_number(x):
                cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
                numeric_val = pd.to_numeric(cleaned, errors='coerce')
                if pd.isna(numeric_val):
                    return str(x)
                elif numeric_val >= 1:
                    return f"{numeric_val:,.0f}"
                else:
                    return f"{numeric_val:.1f}"

            summary_data['Số liệu'] = summary_data['Số liệu'].apply(format_summary_number)
            st.dataframe(summary_data, use_container_width=True, hide_index=True)

    return period_type

# Hàm tạo charts cho Tổ xe - giống như document tabs
def create_vehicle_charts(df):
    col1, col2 = st.columns(2)

    with col1:
        # Chart doanh thu theo tuần
        revenue_data = df[df['Nội dung'] == 'Doanh thu Tổ xe']
        if not revenue_data.empty and 'Tuần' in revenue_data.columns:
            revenue_trend = revenue_data.copy()
            revenue_trend['Tuần'] = pd.to_numeric(revenue_trend['Tuần'], errors='coerce')
            revenue_trend['Doanh thu'] = pd.to_numeric(revenue_trend['Số liệu'].astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip(), errors='coerce')
            revenue_trend = revenue_trend.dropna().sort_values('Tuần')

            fig_revenue = go.Figure()
            fig_revenue.add_trace(go.Scatter(
                x=revenue_trend['Tuần'],
                y=revenue_trend['Doanh thu'],
                mode='lines+markers',
                name='Doanh thu',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=8)
            ))

            # Đường xu hướng (nếu đủ dữ liệu)
            if len(revenue_trend) >= 3:
                ma_window = min(3, len(revenue_trend)//2)
                ma_trend = revenue_trend['Doanh thu'].rolling(window=ma_window, center=True).mean()
                fig_revenue.add_trace(go.Scatter(
                    x=revenue_trend['Tuần'],
                    y=ma_trend,
                    mode='lines',
                    name=f'Xu hướng ({ma_window} tuần)',
                    line=dict(color='red', width=3, dash='dash'),
                    opacity=0.8
                ))

            fig_revenue.update_layout(
                title='💰 Doanh thu theo tuần (có xu hướng)',
                xaxis_title='Tuần',
                yaxis_title='Doanh thu (VNĐ)',
                hovermode='x unified'
            )
            st.plotly_chart(fig_revenue, use_container_width=True)

    with col2:
        # Chart km chạy theo tuần
        km_data = df[df['Nội dung'] == 'Tổng km chạy']
        if not km_data.empty and 'Tuần' in km_data.columns:
            km_trend = km_data.copy()
            km_trend['Tuần'] = pd.to_numeric(km_trend['Tuần'], errors='coerce')
            km_trend['Km chạy'] = pd.to_numeric(km_trend['Số liệu'].astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip(), errors='coerce')
            km_trend = km_trend.dropna().sort_values('Tuần')

            fig_km = go.Figure()
            fig_km.add_trace(go.Scatter(
                x=km_trend['Tuần'],
                y=km_trend['Km chạy'],
                mode='lines+markers',
                name='Km chạy',
                line=dict(color='#1f77b4', width=2),
                marker=dict(size=8)
            ))

            # Đường xu hướng
            if len(km_trend) >= 3:
                ma_window = min(3, len(km_trend)//2)
                ma_trend = km_trend['Km chạy'].rolling(window=ma_window, center=True).mean()
                fig_km.add_trace(go.Scatter(
                    x=km_trend['Tuần'],
                    y=ma_trend,
                    mode='lines',
                    name=f'Xu hướng ({ma_window} tuần)',
                    line=dict(color='red', width=3, dash='dash'),
                    opacity=0.8
                ))

            fig_km.update_layout(
                title='🛣️ Km chạy theo tuần (có xu hướng)',
                xaxis_title='Tuần',
                yaxis_title='Km chạy',
                hovermode='x unified'
            )
            st.plotly_chart(fig_km, use_container_width=True)

# Tab 4: Tổ xe
with tab4:
    st.markdown('<div class="tab-header">🚗 Báo cáo Tổ xe</div>', unsafe_allow_html=True)

    def create_vehicle_data():
        """Tạo dữ liệu mẫu cho tổ xe từ format đã cho"""
        return pd.DataFrame({
            'Tuần': [39, 39, 39, 39, 39, 39, 39, 39, 39],
            'Tháng': [9, 9, 9, 9, 9, 9, 9, 9, 9],
            'Nội dung': [
                'Số chuyến xe',
                'Tổng số nhiên liệu tiêu thụ',
                'Tổng km chạy',
                'Km chạy của hành chính',
                'Km chạy của xe cứu thương',
                'Chi phí bảo dưỡng',
                'Doanh thu Tổ xe',
                'Số phiếu khảo sát hài lòng',
                'Tỷ lệ hài lòng của khách hàng'
            ],
            'Số liệu': [245, 1200, 8500, 5200, 3300, 15000000, 25000000, 180, 92.5]
        })

    # Load data từ DataManager hoặc dữ liệu mẫu
    df_vehicle = data_manager.get_category_data('Tổ xe')

    if df_vehicle is not None:
        st.info(f"✅ Đã tải {len(df_vehicle)} bản ghi cho Tổ xe từ file: {data_manager.metadata['filename']}")
    else:
        st.info("📁 Chưa có dữ liệu được tải từ sidebar. Hiển thị dữ liệu mẫu.")
        df_vehicle = create_vehicle_data()

    if not df_vehicle.empty:
        # Metrics overview tổng quan
        st.markdown('<div class="section-header">📊 Tổng quan hoạt động Tổ xe</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        # Debug: Hiển thị cấu trúc dữ liệu
        with st.expander("🔍 Debug: Cấu trúc dữ liệu Tổ xe", expanded=False):
            st.write("**Columns:**", list(df_vehicle.columns))
            st.write("**Shape:**", df_vehicle.shape)
            if 'Nội dung' in df_vehicle.columns:
                st.write("**Nội dung values:**", df_vehicle['Nội dung'].unique().tolist())
            st.dataframe(df_vehicle.head())

        # Tính toán metrics từ dữ liệu - CỘNG TỔNG TẤT CẢ CÁC TUẦN
        def get_metric_value(content_name):
            if 'Nội dung' not in df_vehicle.columns or 'Số liệu' not in df_vehicle.columns:
                return 0

            # Lấy tất cả các hàng có nội dung này và cộng tổng
            result = df_vehicle[df_vehicle['Nội dung'] == content_name]['Số liệu']
            if len(result) > 0:
                # Clean data: remove non-breaking spaces and other whitespace characters
                cleaned_result = result.astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip()
                # Convert tất cả values thành numeric và cộng tổng
                numeric_values = pd.to_numeric(cleaned_result, errors='coerce').fillna(0)
                total = numeric_values.sum()
                return total
            return 0

        so_chuyen = get_metric_value('Số chuyến xe')
        km_chay = get_metric_value('Tổng km chạy')
        doanh_thu = get_metric_value('Doanh thu Tổ xe')

        with col1:
            st.metric("🚗 Số chuyến", f"{int(so_chuyen):,}", help="Tổng số chuyến xe tất cả các tuần")
        with col2:
            st.metric("🛣️ Tổng km", f"{int(km_chay):,}", help="Tổng số kilomet đã chạy tất cả các tuần")
        with col3:
            st.metric("💰 Doanh thu", f"{int(doanh_thu):,}", help="Tổng doanh thu Tổ xe tất cả các tuần (VNĐ)")
        with col4:
            # Tính trung bình tỷ lệ hài lòng - CHỈ TÍNH NHỮNG TUẦN CÓ KHẢO SÁT
            hai_long_data = df_vehicle[df_vehicle['Nội dung'] == 'Tỷ lệ hài lòng của khách hàng']['Số liệu']
            if len(hai_long_data) > 0:
                # Clean data: remove non-breaking spaces and other whitespace characters
                cleaned_hai_long = hai_long_data.astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip()
                hai_long_numeric = pd.to_numeric(cleaned_hai_long, errors='coerce')
                # Chỉ tính những tuần có tỷ lệ hài lòng > 0 (có làm khảo sát)
                hai_long_valid = hai_long_numeric[hai_long_numeric > 0]
                hai_long_avg = hai_long_valid.mean() if len(hai_long_valid) > 0 else 0
            else:
                hai_long_avg = 0
            st.metric("😊 Hài lòng", f"{hai_long_avg:.1f}%", help="Tỷ lệ hài lòng trung bình (chỉ tính tuần có khảo sát)")

        # Thêm hàng metrics thứ 2
        col5, col6, col7, col8 = st.columns(4)

        nhien_lieu = get_metric_value('Tổng số nhiên liệu tiêu thụ')
        # Xử lý typo trong dữ liệu thực: "Km chạy của Km chạy của xe hành chính"
        km_hanh_chinh = get_metric_value('Km chạy của Km chạy của xe hành chính') or get_metric_value('Km chạy của hành chính')
        km_cuu_thuong = get_metric_value('Km chạy của Km chạy của xe cứu thương') or get_metric_value('Km chạy của xe cứu thương')
        bao_duong = get_metric_value('Chi phí bảo dưỡng')

        with col5:
            st.metric("⛽ Nhiên liệu", f"{int(nhien_lieu):,}", help="Tổng nhiên liệu tiêu thụ tất cả các tuần (lít)")
        with col6:
            st.metric("🏢 Hành chính", f"{int(km_hanh_chinh):,} km", help="Tổng km chạy hành chính tất cả các tuần")
        with col7:
            st.metric("🚑 Cứu thương", f"{int(km_cuu_thuong):,} km", help="Tổng km chạy xe cứu thương tất cả các tuần")
        with col8:
            st.metric("🔧 Bảo dưỡng", f"{int(bao_duong):,}", help="Tổng chi phí bảo dưỡng tất cả các tuần (VNĐ)")

        st.markdown("<br>", unsafe_allow_html=True)

        # Pivot Table Section - giống như document tabs
        create_vehicle_pivot_table(df_vehicle)

        st.markdown("<br>", unsafe_allow_html=True)

        # Biểu đồ tổng quan
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích</div>', unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Biểu đồ phân bố km chạy (xử lý typo)
            km_patterns = ['Km chạy của Km chạy của xe hành chính', 'Km chạy của Km chạy của xe cứu thương',
                          'Km chạy của hành chính', 'Km chạy của xe cứu thương']
            km_data = df_vehicle[df_vehicle['Nội dung'].isin(km_patterns)]

            if not km_data.empty:
                # Làm sạch tên hiển thị
                km_data_clean = km_data.copy()
                km_data_clean['Nội dung'] = km_data_clean['Nội dung'].str.replace('Km chạy của Km chạy của xe ', '').str.replace('Km chạy của ', '')

                fig_km = px.pie(km_data_clean, values='Số liệu', names='Nội dung',
                              title='🛣️ Phân bố Km chạy theo loại xe',
                              hole=0.4)
                fig_km.update_layout(height=400)
                st.plotly_chart(fig_km, use_container_width=True)

        with col_chart2:
            # Biểu đồ doanh thu vs chi phí
            finance_data = df_vehicle[df_vehicle['Nội dung'].isin(['Doanh thu Tổ xe', 'Chi phí bảo dưỡng'])]
            if not finance_data.empty:
                fig_finance = px.bar(finance_data, x='Nội dung', y='Số liệu',
                                   title='💰 So sánh Doanh thu - Chi phí',
                                   color='Nội dung')
                fig_finance.update_layout(height=400)
                st.plotly_chart(fig_finance, use_container_width=True)

        # Biểu đồ phân tích chi tiết
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích chi tiết</div>', unsafe_allow_html=True)

        # Biểu đồ phân tích theo thời gian
        col_chart3, col_chart4 = st.columns(2)

        with col_chart3:
            # Xu hướng số chuyến và doanh thu theo tuần
            vehicle_time_data = df_vehicle[df_vehicle['Nội dung'].isin(['Số chuyến xe', 'Doanh thu Tổ xe'])]

            if not vehicle_time_data.empty and 'Tuần' in vehicle_time_data.columns:
                # Pivot để có số chuyến và doanh thu theo tuần
                time_pivot = vehicle_time_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
                time_pivot = time_pivot.reset_index()
                time_pivot['Tuần'] = pd.to_numeric(time_pivot['Tuần'], errors='coerce')
                time_pivot = time_pivot.sort_values('Tuần')

                if 'Doanh thu Tổ xe' in time_pivot.columns and 'Số chuyến xe' in time_pivot.columns:
                    time_pivot['Doanh thu Tổ xe'] = pd.to_numeric(time_pivot['Doanh thu Tổ xe'], errors='coerce')
                    time_pivot['Số chuyến xe'] = pd.to_numeric(time_pivot['Số chuyến xe'], errors='coerce')

                    fig_trend = go.Figure()

                    # Doanh thu (trục y bên trái)
                    fig_trend.add_trace(go.Scatter(
                        x=time_pivot['Tuần'],
                        y=time_pivot['Doanh thu Tổ xe'],
                        name='Doanh thu',
                        line=dict(color='#2ecc71', width=3),
                        yaxis='y'
                    ))

                    # Số chuyến (trục y bên phải)
                    fig_trend.add_trace(go.Scatter(
                        x=time_pivot['Tuần'],
                        y=time_pivot['Số chuyến xe'],
                        name='Số chuyến',
                        line=dict(color='#3498db', width=3),
                        yaxis='y2'
                    ))

                    fig_trend.update_layout(
                        title='📈 Xu hướng doanh thu và số chuyến theo tuần',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Doanh thu (VNĐ)', side='left', color='#2ecc71'),
                        yaxis2=dict(title='Số chuyến', side='right', overlaying='y', color='#3498db'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_trend, use_container_width=True)

        with col_chart4:
            # Xu hướng km chạy theo tuần
            km_time_data = df_vehicle[df_vehicle['Nội dung'].isin(['Tổng km chạy', 'Tổng số nhiên liệu tiêu thụ'])]

            if not km_time_data.empty and 'Tuần' in km_time_data.columns:
                km_pivot = km_time_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
                km_pivot = km_pivot.reset_index()
                km_pivot['Tuần'] = pd.to_numeric(km_pivot['Tuần'], errors='coerce')
                km_pivot = km_pivot.sort_values('Tuần')

                if 'Tổng km chạy' in km_pivot.columns and 'Tổng số nhiên liệu tiêu thụ' in km_pivot.columns:
                    km_pivot['Tổng km chạy'] = pd.to_numeric(km_pivot['Tổng km chạy'], errors='coerce')
                    km_pivot['Tổng số nhiên liệu tiêu thụ'] = pd.to_numeric(km_pivot['Tổng số nhiên liệu tiêu thụ'], errors='coerce')

                    fig_km_trend = go.Figure()

                    # Km chạy
                    fig_km_trend.add_trace(go.Scatter(
                        x=km_pivot['Tuần'],
                        y=km_pivot['Tổng km chạy'],
                        name='Km chạy',
                        line=dict(color='#9b59b6', width=3),
                        yaxis='y'
                    ))

                    # Nhiên liệu (trục phải)
                    fig_km_trend.add_trace(go.Scatter(
                        x=km_pivot['Tuần'],
                        y=km_pivot['Tổng số nhiên liệu tiêu thụ'],
                        name='Nhiên liệu',
                        line=dict(color='#f39c12', width=3),
                        yaxis='y2'
                    ))

                    fig_km_trend.update_layout(
                        title='🛣️ Xu hướng km chạy và nhiên liệu theo tuần',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Km chạy', side='left', color='#9b59b6'),
                        yaxis2=dict(title='Nhiên liệu (lít)', side='right', overlaying='y', color='#f39c12'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_km_trend, use_container_width=True)

        # Row 2: Phân tích chất lượng và chi phí theo thời gian
        col_chart5, col_chart6 = st.columns(2)

        with col_chart5:
            # Xu hướng chất lượng dịch vụ theo tuần
            quality_time_data = df_vehicle[df_vehicle['Nội dung'].isin(['Tỷ lệ hài lòng của khách hàng', 'Số phiếu khảo sát hài lòng'])]

            if not quality_time_data.empty and 'Tuần' in quality_time_data.columns:
                quality_pivot = quality_time_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
                quality_pivot = quality_pivot.reset_index()
                quality_pivot['Tuần'] = pd.to_numeric(quality_pivot['Tuần'], errors='coerce')
                quality_pivot = quality_pivot.sort_values('Tuần')

                if 'Tỷ lệ hài lòng của khách hàng' in quality_pivot.columns:
                    quality_pivot['Tỷ lệ hài lòng của khách hàng'] = pd.to_numeric(quality_pivot['Tỷ lệ hài lòng của khách hàng'], errors='coerce')

                    fig_quality_trend = px.line(
                        quality_pivot,
                        x='Tuần',
                        y='Tỷ lệ hài lòng của khách hàng',
                        title='😊 Xu hướng mức độ hài lòng theo tuần',
                        line_shape='linear',
                        color_discrete_sequence=['#27ae60']
                    )
                    fig_quality_trend.update_layout(height=300, yaxis_title='Tỷ lệ hài lòng (%)')
                    fig_quality_trend.update_traces(line_width=3)
                    st.plotly_chart(fig_quality_trend, use_container_width=True)

        with col_chart6:
            # Xu hướng chi phí bảo dưỡng theo tuần
            cost_time_data = df_vehicle[df_vehicle['Nội dung'] == 'Chi phí bảo dưỡng']

            if not cost_time_data.empty and 'Tuần' in cost_time_data.columns:
                cost_time_data['Tuần'] = pd.to_numeric(cost_time_data['Tuần'], errors='coerce')
                cost_time_data['Chi phí bảo dưỡng'] = pd.to_numeric(cost_time_data['Số liệu'], errors='coerce')
                cost_time_data = cost_time_data.sort_values('Tuần')

                fig_cost_trend = px.bar(
                    cost_time_data,
                    x='Tuần',
                    y='Chi phí bảo dưỡng',
                    title='🔧 Chi phí bảo dưỡng theo tuần',
                    color_discrete_sequence=['#e74c3c']
                )
                fig_cost_trend.update_layout(height=300, yaxis_title='Chi phí (VNĐ)')
                st.plotly_chart(fig_cost_trend, use_container_width=True)

        # 📈 Biểu đồ phân tích chi tiết
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích chi tiết</div>', unsafe_allow_html=True)

        # Row 3: Biểu đồ phân tích chi tiết theo format 2 biểu đồ cuối
        col_detail1, col_detail2 = st.columns(2)

        with col_detail1:
            # Biểu đồ phân tích hiệu suất vận hành (km hành chính vs cứu thương)
            km_detail_data = df_vehicle[df_vehicle['Nội dung'].isin(['Km chạy của hành chính', 'Km chạy của xe cứu thương'])]

            if not km_detail_data.empty and 'Tuần' in km_detail_data.columns:
                km_detail_pivot = km_detail_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                km_detail_pivot = km_detail_pivot.reset_index()
                km_detail_pivot['Tuần'] = pd.to_numeric(km_detail_pivot['Tuần'], errors='coerce')
                km_detail_pivot = km_detail_pivot.sort_values('Tuần')

                if 'Km chạy của hành chính' in km_detail_pivot.columns and 'Km chạy của xe cứu thương' in km_detail_pivot.columns:
                    km_detail_pivot['Km chạy của hành chính'] = pd.to_numeric(km_detail_pivot['Km chạy của hành chính'], errors='coerce')
                    km_detail_pivot['Km chạy của xe cứu thương'] = pd.to_numeric(km_detail_pivot['Km chạy của xe cứu thương'], errors='coerce')

                    fig_km_detail = go.Figure()

                    # Km hành chính
                    fig_km_detail.add_trace(go.Scatter(
                        x=km_detail_pivot['Tuần'],
                        y=km_detail_pivot['Km chạy của hành chính'],
                        mode='lines',
                        name='Km hành chính',
                        line=dict(color='#3498db', width=3),
                        yaxis='y'
                    ))

                    # Km cứu thương (trục phải)
                    fig_km_detail.add_trace(go.Scatter(
                        x=km_detail_pivot['Tuần'],
                        y=km_detail_pivot['Km chạy của xe cứu thương'],
                        mode='lines',
                        name='Km cứu thương',
                        line=dict(color='#e74c3c', width=3),
                        yaxis='y2'
                    ))

                    fig_km_detail.update_layout(
                        title='🚗 Phân tích km chạy theo loại xe',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Km hành chính', side='left', color='#3498db'),
                        yaxis2=dict(title='Km cứu thương', side='right', overlaying='y', color='#e74c3c'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_km_detail, use_container_width=True)

        with col_detail2:
            # Biểu đồ tương quan doanh thu - chi phí
            revenue_cost_data = df_vehicle[df_vehicle['Nội dung'].isin(['Doanh thu Tổ xe', 'Chi phí bảo dưỡng'])]

            if not revenue_cost_data.empty and 'Tuần' in revenue_cost_data.columns:
                rc_pivot = revenue_cost_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                rc_pivot = rc_pivot.reset_index()
                rc_pivot['Tuần'] = pd.to_numeric(rc_pivot['Tuần'], errors='coerce')
                rc_pivot = rc_pivot.sort_values('Tuần')

                if 'Doanh thu Tổ xe' in rc_pivot.columns and 'Chi phí bảo dưỡng' in rc_pivot.columns:
                    rc_pivot['Doanh thu Tổ xe'] = pd.to_numeric(rc_pivot['Doanh thu Tổ xe'], errors='coerce')
                    rc_pivot['Chi phí bảo dưỡng'] = pd.to_numeric(rc_pivot['Chi phí bảo dưỡng'], errors='coerce')

                    fig_revenue_cost = go.Figure()

                    # Doanh thu
                    fig_revenue_cost.add_trace(go.Scatter(
                        x=rc_pivot['Tuần'],
                        y=rc_pivot['Doanh thu Tổ xe'],
                        mode='lines',
                        name='Doanh thu',
                        line=dict(color='#2ecc71', width=3),
                        yaxis='y'
                    ))

                    # Chi phí (trục phải)
                    fig_revenue_cost.add_trace(go.Scatter(
                        x=rc_pivot['Tuần'],
                        y=rc_pivot['Chi phí bảo dưỡng'],
                        mode='lines',
                        name='Chi phí bảo dưỡng',
                        line=dict(color='#f39c12', width=3),
                        yaxis='y2'
                    ))

                    fig_revenue_cost.update_layout(
                        title='💰 Phân tích doanh thu - chi phí',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Doanh thu (VNĐ)', side='left', color='#2ecc71'),
                        yaxis2=dict(title='Chi phí (VNĐ)', side='right', overlaying='y', color='#f39c12'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_revenue_cost, use_container_width=True)

        # Biểu đồ giống như document tabs
        create_vehicle_charts(df_vehicle)

        # Bảng dữ liệu chi tiết
        st.markdown('<div class="section-header">📊 Dữ liệu chi tiết</div>', unsafe_allow_html=True)

        # Hiển thị bảng với formatting
        display_df = df_vehicle.copy()
        # Clean and format the data display
        def clean_and_format_number(x):
            # Clean non-breaking spaces and other whitespace
            cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
            numeric_val = pd.to_numeric(cleaned, errors='coerce')
            if pd.isna(numeric_val):
                return str(x)  # Return original if conversion fails
            elif numeric_val >= 1:
                return f"{numeric_val:,.0f}"
            else:
                return f"{numeric_val:.1f}"

        display_df['Số liệu'] = display_df['Số liệu'].apply(clean_and_format_number)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.error("❌ Không có dữ liệu Tổ xe")
        st.info("📁 Upload dữ liệu hoặc kiểm tra kết nối GitHub để xem thống kê chi tiết")


        # Pivot Table theo tuần
        st.markdown('<div class="section-header">📈 Bảng phân tích theo tuần</div>', unsafe_allow_html=True)

        def create_call_pivot_table(df):
            """Tạo pivot table cho dữ liệu tổng đài"""
            if 'Tuần' not in df.columns:
                st.warning("⚠️ Không tìm thấy cột 'Tuần' trong dữ liệu")
                return None

            # Chọn các metrics chính để hiển thị trong pivot table
            main_metrics = [
                'Tổng số cuộc gọi đến Bệnh viện',
                'Tổng số cuộc gọi nhỡ do từ chối',
                'Tổng số cuộc gọi nhỡ do không bắt máy',
                'Tổng số cuộc gọi đến Hotline'
            ]

            # Lọc data cho các metrics chính
            pivot_data = df[df['Nội dung'].isin(main_metrics)].copy()

            if pivot_data.empty:
                st.warning("⚠️ Không có dữ liệu cho các metrics chính")
                return None

            # Clean data
            pivot_data['Số liệu'] = pivot_data['Số liệu'].astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip()
            pivot_data['Số liệu'] = pd.to_numeric(pivot_data['Số liệu'], errors='coerce').fillna(0)

            # Tạo pivot table
            pivot = pivot_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
            pivot = pivot.reset_index()
            pivot['Tuần'] = pd.to_numeric(pivot['Tuần'], errors='coerce')
            pivot = pivot.sort_values('Tuần')

            # Tính tỷ lệ trả lời cho từng tuần
            if 'Tổng số cuộc gọi đến Bệnh viện' in pivot.columns and 'Tổng số cuộc gọi nhỡ do từ chối' in pivot.columns and 'Tổng số cuộc gọi nhỡ do không bắt máy' in pivot.columns:
                pivot['Tổng cuộc gọi nhỡ'] = pivot['Tổng số cuộc gọi nhỡ do từ chối'] + pivot['Tổng số cuộc gọi nhỡ do không bắt máy']
                pivot['Tỷ lệ trả lời (%)'] = ((pivot['Tổng số cuộc gọi đến Bệnh viện'] - pivot['Tổng cuộc gọi nhỡ']) / pivot['Tổng số cuộc gọi đến Bệnh viện'] * 100).fillna(0)

            return pivot

        pivot_df = create_call_pivot_table(df_calls)

        if pivot_df is not None:
            # Format hiển thị pivot table
            display_pivot = pivot_df.copy()

            # Format các cột chính
            main_cols = ['Tổng số cuộc gọi đến Bệnh viện', 'Tổng số cuộc gọi nhỡ do từ chối', 'Tổng số cuộc gọi nhỡ do không bắt máy', 'Tổng số cuộc gọi đến Hotline']
            for col in main_cols:
                if col in display_pivot.columns:
                    display_pivot[col] = display_pivot[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "0")

            # Format tỷ lệ trả lời
            if 'Tỷ lệ trả lời (%)' in display_pivot.columns:
                display_pivot['Tỷ lệ trả lời (%)'] = display_pivot['Tỷ lệ trả lời (%)'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "0%")

            # Format change columns (ẩn các cột không cần thiết để table gọn hơn)
            cols_to_drop = [col for col in display_pivot.columns if '_Change' in col or col == 'Tổng cuộc gọi nhỡ']
            if cols_to_drop:
                display_pivot = display_pivot.drop(columns=cols_to_drop)

            st.dataframe(display_pivot, use_container_width=True, hide_index=True)

# Tab 5: Tổng đài
with tab5:
    st.markdown('<div class="tab-header">📞 Báo cáo Tổng đài</div>', unsafe_allow_html=True)

    def create_call_center_data():
        """Tạo dữ liệu mẫu cho tổng đài"""
        return pd.DataFrame({
            'Tuần': [39] * 12,
            'Tháng': [9] * 12,
            'Nội dung': [
                'Tổng số cuộc gọi đến Bệnh viện',
                'Tổng số cuộc gọi nhỡ do từ chối',
                'Tổng số cuộc gọi nhỡ do không bắt máy',
                'Số cuộc gọi đến (Nhánh 0-Tổng đài viên)',
                'Nhỡ do từ chối (Nhánh 0-Tổng đài viên)',
                'Nhỡ do không bắt máy (Nhánh 0-Tổng đài viên)',
                'Số cuộc gọi đến (Nhánh 1-Cấp cứu)',
                'Số cuộc gọi đến (Nhánh 2-Tư vấn Thuốc)',
                'Số cuộc gọi đến (Nhánh 3-PKQT)',
                'Số cuộc gọi đến (Nhánh 4-Vấn đề khác)',
                'Hottline',
                'Tỷ lệ trả lời'
            ],
            'Số liệu': [1250, 185, 95, 450, 65, 35, 320, 280, 150, 120, 85, 87.2]
        })

    # Load data từ DataManager hoặc dữ liệu mẫu
    df_calls = data_manager.get_category_data('Tổng đài')

    if df_calls is not None:
        st.info(f"✅ Đã tải {len(df_calls)} bản ghi cho Tổng đài từ file: {data_manager.metadata['filename']}")
    else:
        st.info("📁 Chưa có dữ liệu được tải từ sidebar. Hiển thị dữ liệu mẫu.")
        df_calls = create_call_center_data()

    if not df_calls.empty:
        # Metrics overview tổng quan
        st.markdown('<div class="section-header">📊 Tổng quan hoạt động Tổng đài</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        # Debug: Hiển thị cấu trúc dữ liệu
        with st.expander("🔍 Debug: Cấu trúc dữ liệu Tổng đài", expanded=False):
            st.write("**Columns:**", list(df_calls.columns))
            st.write("**Shape:**", df_calls.shape)
            if 'Nội dung' in df_calls.columns:
                st.write("**Nội dung values:**", df_calls['Nội dung'].unique().tolist())
            st.dataframe(df_calls.head())

        # Tính toán metrics từ dữ liệu - CỘNG TỔNG TẤT CẢ CÁC TUẦN
        def get_call_metric_value(content_name):
            if 'Nội dung' not in df_calls.columns or 'Số liệu' not in df_calls.columns:
                return 0

            # Lấy tất cả các hàng có nội dung này và cộng tổng
            result = df_calls[df_calls['Nội dung'] == content_name]['Số liệu']
            if len(result) > 0:
                # Clean data: remove non-breaking spaces and other whitespace characters
                cleaned_result = result.astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip()
                # Convert tất cả values thành numeric và cộng tổng
                numeric_values = pd.to_numeric(cleaned_result, errors='coerce').fillna(0)
                total = numeric_values.sum()
                return total
            return 0

        tong_goi = get_call_metric_value('Tổng số cuộc gọi đến Bệnh viện')
        nho_tu_choi = get_call_metric_value('Tổng số cuộc gọi nhỡ do từ chối')
        nho_ko_bat = get_call_metric_value('Tổng số cuộc gọi nhỡ do không bắt máy')
        ty_le_raw = get_call_metric_value('Tỷ lệ trả lời')

        # Tính tỷ lệ trả lời từ dữ liệu có sẵn (tổng cuộc gọi - cuộc gọi nhỡ) / tổng cuộc gọi * 100
        ty_le = 0
        if tong_goi > 0:
            tong_nho = nho_tu_choi + nho_ko_bat
            cuoc_goi_tra_loi = tong_goi - tong_nho
            ty_le = (cuoc_goi_tra_loi / tong_goi) * 100 if tong_goi > 0 else 0

        with col1:
            st.metric("📞 Tổng cuộc gọi", f"{int(tong_goi):,}", help="Tổng số cuộc gọi đến Bệnh viện tất cả các tuần")
        with col2:
            st.metric("❌ Từ chối", f"{int(nho_tu_choi):,}", help="Tổng số cuộc gọi nhỡ do từ chối tất cả các tuần")
        with col3:
            st.metric("📵 Không bắt", f"{int(nho_ko_bat):,}", help="Tổng số cuộc gọi nhỡ do không bắt máy tất cả các tuần")
        with col4:
            st.metric("✅ Tỷ lệ trả lời", f"{ty_le:.1f}%", help="Tỷ lệ trả lời trung bình")

        # Thêm hàng metrics thứ 2
        col5, col6, col7, col8 = st.columns(4)

        nhanh_0 = get_call_metric_value('Số cuộc gọi đến (Nhánh 0-Tổng đài viên)')
        nhanh_1 = get_call_metric_value('Số cuộc gọi đến (Nhánh 1-Cấp cứu)')
        nhanh_2 = get_call_metric_value('Số cuộc gọi đến (Nhánh 2-Tư vấn Thuốc)')
        hotline = get_call_metric_value('Hottline')

        with col5:
            st.metric("📞 Nhánh 0", f"{int(nhanh_0):,}", help="Tổng cuộc gọi đến Nhánh 0-Tổng đài viên tất cả các tuần")
        with col6:
            st.metric("🚑 Nhánh 1", f"{int(nhanh_1):,}", help="Tổng cuộc gọi đến Nhánh 1-Cấp cứu tất cả các tuần")
        with col7:
            st.metric("💊 Nhánh 2", f"{int(nhanh_2):,}", help="Tổng cuộc gọi đến Nhánh 2-Tư vấn Thuốc tất cả các tuần")
        with col8:
            st.metric("☎️ Hotline", f"{int(hotline):,}", help="Tổng cuộc gọi Hotline tất cả các tuần")

        st.markdown("<br>", unsafe_allow_html=True)

        # Pivot Table Section - giống như Tab 4
        create_call_pivot_table(df_calls)

        st.markdown("<br>", unsafe_allow_html=True)

        # Biểu đồ tổng quan
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích</div>', unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Biểu đồ phân bố cuộc gọi theo nhánh
            branch_patterns = ['Số cuộc gọi đến (Nhánh 0-Tổng đài viên)', 'Số cuộc gọi đến (Nhánh 1-Cấp cứu)',
                              'Số cuộc gọi đến (Nhánh 2-Tư vấn Thuốc)', 'Số cuộc gọi đến (Nhánh 3-PKQT)',
                              'Số cuộc gọi đến (Nhánh 4-Vấn đề khác)']
            branch_data = df_calls[df_calls['Nội dung'].isin(branch_patterns)]

            if not branch_data.empty:
                # Làm sạch tên hiển thị
                branch_data_clean = branch_data.copy()
                branch_data_clean['Nội dung'] = branch_data_clean['Nội dung'].str.replace('Số cuộc gọi đến (', '').str.replace(')', '')

                fig_branch = px.pie(branch_data_clean, values='Số liệu', names='Nội dung',
                                  title='📞 Phân bố cuộc gọi theo nhánh',
                                  hole=0.4)
                fig_branch.update_layout(height=400)
                st.plotly_chart(fig_branch, use_container_width=True)

        with col_chart2:
            # Biểu đồ tỷ lệ trả lời vs cuộc gọi nhỡ
            response_data = df_calls[df_calls['Nội dung'].isin(['Tổng số cuộc gọi đến Bệnh viện', 'Tổng số cuộc gọi nhỡ do từ chối', 'Tổng số cuộc gọi nhỡ do không bắt máy'])]
            if not response_data.empty:
                # Tính toán dữ liệu hiển thị
                tong_goi_chart = get_call_metric_value('Tổng số cuộc gọi đến Bệnh viện')
                nho_tu_choi_chart = get_call_metric_value('Tổng số cuộc gọi nhỡ do từ chối')
                nho_ko_bat_chart = get_call_metric_value('Tổng số cuộc gọi nhỡ do không bắt máy')
                tra_loi_chart = tong_goi_chart - nho_tu_choi_chart - nho_ko_bat_chart

                response_summary = pd.DataFrame({
                    'Loại': ['Trả lời', 'Từ chối', 'Không bắt'],
                    'Số liệu': [tra_loi_chart, nho_tu_choi_chart, nho_ko_bat_chart]
                })

                fig_response = px.bar(response_summary, x='Loại', y='Số liệu',
                                    title='📊 Tỷ lệ trả lời cuộc gọi',
                                    color='Loại',
                                    color_discrete_map={'Trả lời': '#2ecc71', 'Từ chối': '#e74c3c', 'Không bắt': '#f39c12'})
                fig_response.update_layout(height=400)
                st.plotly_chart(fig_response, use_container_width=True)

        # Biểu đồ phân tích chi tiết
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích chi tiết</div>', unsafe_allow_html=True)

        # Row 1: Biểu đồ tổng quan và phân tích nhánh
        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Xu hướng tổng cuộc gọi và cuộc gọi nhỡ theo tuần
            call_time_data = df_calls[df_calls['Nội dung'].isin(['Tổng số cuộc gọi đến Bệnh viện', 'Tổng số cuộc gọi nhỡ do từ chối', 'Tổng số cuộc gọi nhỡ do không bắt máy'])]

            if not call_time_data.empty and 'Tuần' in call_time_data.columns:
                call_pivot = call_time_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                call_pivot = call_pivot.reset_index()
                call_pivot['Tuần'] = pd.to_numeric(call_pivot['Tuần'], errors='coerce')
                call_pivot = call_pivot.sort_values('Tuần')

                # Clean data
                for col in call_pivot.columns:
                    if col != 'Tuần':
                        call_pivot[col] = pd.to_numeric(call_pivot[col], errors='coerce').fillna(0)

                if 'Tổng số cuộc gọi đến Bệnh viện' in call_pivot.columns:
                    fig_call_trend = go.Figure()

                    # Tổng cuộc gọi
                    fig_call_trend.add_trace(go.Scatter(
                        x=call_pivot['Tuần'],
                        y=call_pivot['Tổng số cuộc gọi đến Bệnh viện'],
                        mode='lines',
                        name='Tổng cuộc gọi',
                        line=dict(color='#2ecc71', width=3),
                        yaxis='y'
                    ))

                    # Cuộc gọi nhỡ (trục phải) - tính tổng từ chối + không bắt
                    if 'Tổng số cuộc gọi nhỡ do từ chối' in call_pivot.columns and 'Tổng số cuộc gọi nhỡ do không bắt máy' in call_pivot.columns:
                        call_pivot['Tổng cuộc gọi nhỡ'] = call_pivot['Tổng số cuộc gọi nhỡ do từ chối'] + call_pivot['Tổng số cuộc gọi nhỡ do không bắt máy']

                        fig_call_trend.add_trace(go.Scatter(
                            x=call_pivot['Tuần'],
                            y=call_pivot['Tổng cuộc gọi nhỡ'],
                            mode='lines',
                            name='Cuộc gọi nhỡ',
                            line=dict(color='#e74c3c', width=3),
                            yaxis='y2'
                        ))

                    fig_call_trend.update_layout(
                        title='📞 Xu hướng cuộc gọi theo tuần',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Tổng cuộc gọi', side='left', color='#2ecc71'),
                        yaxis2=dict(title='Cuộc gọi nhỡ', side='right', overlaying='y', color='#e74c3c'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_call_trend, use_container_width=True)

        with col_chart2:
            # Phân tích cuộc gọi theo nhánh
            branch_data = df_calls[df_calls['Nội dung'].str.contains('Nhánh', na=False)]

            if not branch_data.empty and 'Tuần' in branch_data.columns:
                # Lọc chỉ lấy số cuộc gọi đến các nhánh (không lấy nhỡ)
                branch_call_data = branch_data[branch_data['Nội dung'].str.contains('Số cuộc gọi đến', na=False)]

                if not branch_call_data.empty:
                    branch_pivot = branch_call_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                    branch_pivot = branch_pivot.reset_index()
                    branch_pivot['Tuần'] = pd.to_numeric(branch_pivot['Tuần'], errors='coerce')
                    branch_pivot = branch_pivot.sort_values('Tuần')

                    # Clean data
                    for col in branch_pivot.columns:
                        if col != 'Tuần':
                            branch_pivot[col] = pd.to_numeric(branch_pivot[col], errors='coerce').fillna(0)

                    # Tạo biểu đồ stacked bar
                    fig_branch = go.Figure()

                    colors = ['#3498db', '#9b59b6', '#f39c12', '#1abc9c', '#34495e']
                    color_idx = 0

                    for col in branch_pivot.columns:
                        if col != 'Tuần':
                            fig_branch.add_trace(go.Bar(
                                x=branch_pivot['Tuần'],
                                y=branch_pivot[col],
                                name=col.replace('Số cuộc gọi đến (', '').replace(')', ''),
                                marker_color=colors[color_idx % len(colors)]
                            ))
                            color_idx += 1

                    fig_branch.update_layout(
                        title='🔗 Phân bố cuộc gọi theo nhánh',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis_title='Số cuộc gọi',
                        barmode='stack',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_branch, use_container_width=True)

        # 📈 Biểu đồ phân tích chi tiết
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích chi tiết</div>', unsafe_allow_html=True)

        # Row 2: Biểu đồ phân tích chi tiết theo format dual axis
        col_detail1, col_detail2 = st.columns(2)

        with col_detail1:
            # Biểu đồ phân tích tỷ lệ trả lời và tổng cuộc gọi
            performance_data = df_calls[df_calls['Nội dung'].isin(['Tỷ lệ trả lời', 'Tổng số cuộc gọi đến Bệnh viện'])]

            if not performance_data.empty and 'Tuần' in performance_data.columns:
                perf_pivot = performance_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                perf_pivot = perf_pivot.reset_index()
                perf_pivot['Tuần'] = pd.to_numeric(perf_pivot['Tuần'], errors='coerce')
                perf_pivot = perf_pivot.sort_values('Tuần')

                if 'Tỷ lệ trả lời' in perf_pivot.columns and 'Tổng số cuộc gọi đến Bệnh viện' in perf_pivot.columns:
                    perf_pivot['Tỷ lệ trả lời'] = pd.to_numeric(perf_pivot['Tỷ lệ trả lời'], errors='coerce')
                    perf_pivot['Tổng số cuộc gọi đến Bệnh viện'] = pd.to_numeric(perf_pivot['Tổng số cuộc gọi đến Bệnh viện'], errors='coerce')

                    fig_performance = go.Figure()

                    # Tỷ lệ trả lời
                    fig_performance.add_trace(go.Scatter(
                        x=perf_pivot['Tuần'],
                        y=perf_pivot['Tỷ lệ trả lời'],
                        mode='lines',
                        name='Tỷ lệ trả lời',
                        line=dict(color='#27ae60', width=3),
                        yaxis='y'
                    ))

                    # Tổng cuộc gọi (trục phải)
                    fig_performance.add_trace(go.Scatter(
                        x=perf_pivot['Tuần'],
                        y=perf_pivot['Tổng số cuộc gọi đến Bệnh viện'],
                        mode='lines',
                        name='Tổng cuộc gọi',
                        line=dict(color='#3498db', width=3),
                        yaxis='y2'
                    ))

                    fig_performance.update_layout(
                        title='📈 Tương quan tỷ lệ trả lời - tổng cuộc gọi',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Tỷ lệ trả lời (%)', side='left', color='#27ae60'),
                        yaxis2=dict(title='Tổng cuộc gọi', side='right', overlaying='y', color='#3498db'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_performance, use_container_width=True)

        with col_detail2:
            # Biểu đồ phân tích hotline và tổng đài viên
            operator_data = df_calls[df_calls['Nội dung'].isin(['Hottline', 'Số cuộc gọi đến (Nhánh 0-Tổng đài viên)'])]

            if not operator_data.empty and 'Tuần' in operator_data.columns:
                op_pivot = operator_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                op_pivot = op_pivot.reset_index()
                op_pivot['Tuần'] = pd.to_numeric(op_pivot['Tuần'], errors='coerce')
                op_pivot = op_pivot.sort_values('Tuần')

                if 'Hottline' in op_pivot.columns and 'Số cuộc gọi đến (Nhánh 0-Tổng đài viên)' in op_pivot.columns:
                    op_pivot['Hottline'] = pd.to_numeric(op_pivot['Hottline'], errors='coerce')
                    op_pivot['Số cuộc gọi đến (Nhánh 0-Tổng đài viên)'] = pd.to_numeric(op_pivot['Số cuộc gọi đến (Nhánh 0-Tổng đài viên)'], errors='coerce')

                    fig_operator = go.Figure()

                    # Hotline
                    fig_operator.add_trace(go.Scatter(
                        x=op_pivot['Tuần'],
                        y=op_pivot['Hottline'],
                        mode='lines',
                        name='Hotline',
                        line=dict(color='#e67e22', width=3),
                        yaxis='y'
                    ))

                    # Tổng đài viên (trục phải)
                    fig_operator.add_trace(go.Scatter(
                        x=op_pivot['Tuần'],
                        y=op_pivot['Số cuộc gọi đến (Nhánh 0-Tổng đài viên)'],
                        mode='lines',
                        name='Nhánh tổng đài viên',
                        line=dict(color='#8e44ad', width=3),
                        yaxis='y2'
                    ))

                    fig_operator.update_layout(
                        title='☎️ Phân tích hotline - tổng đài viên',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Hotline', side='left', color='#e67e22'),
                        yaxis2=dict(title='Nhánh tổng đài viên', side='right', overlaying='y', color='#8e44ad'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_operator, use_container_width=True)

        # Bảng dữ liệu chi tiết
        st.markdown('<div class="section-header">📊 Dữ liệu chi tiết</div>', unsafe_allow_html=True)

        # Hiển thị bảng với formatting
        display_df = df_calls.copy()
        # Clean and format the data display
        def clean_and_format_call_number(x):
            # Clean non-breaking spaces and other whitespace
            cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
            numeric_val = pd.to_numeric(cleaned, errors='coerce')
            if pd.isna(numeric_val):
                return str(x)  # Return original if conversion fails
            elif numeric_val >= 1:
                return f"{numeric_val:,.0f}"
            else:
                return f"{numeric_val:.1f}"

        display_df['Số liệu'] = display_df['Số liệu'].apply(clean_and_format_call_number)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.error("❌ Không có dữ liệu Tổng đài")
        st.info("📁 Upload dữ liệu hoặc kiểm tra kết nối GitHub để xem thống kê chi tiết")

# Tab 6: Hệ thống thư ký
with tab6:
    st.markdown('<div class="tab-header">👥 Hệ thống Thư ký Bệnh viện</div>', unsafe_allow_html=True)

    def create_secretary_data():
        """Tạo dữ liệu mẫu cho hệ thống thư ký"""
        return pd.DataFrame({
            'Tuần': [39] * 14,
            'Tháng': [9] * 14,
            'Nội dung': [
                'Số thư ký được sơ tuyển',
                'Số thư ký được tuyển dụng',
                'Số thư ký nhận việc',
                'Số thư ký nghỉ việc',
                'Số thư ký được điều động',
                'Tổng số thư ký',
                '- Thư ký hành chính',
                '- Thư ký chuyên môn',
                'Số buổi sinh hoạt cho thư ký',
                'Số thư ký tham gia sinh hoạt',
                'Số buổi tập huấn, đào tạo cho thư ký',
                'Số thư ký tham gia tập huấn, đào tạo',
                'Số buổi tham quan, học tập',
                'Số thư ký tham gia tham quan, học tập'
            ],
            'Số liệu': [15, 12, 10, 3, 2, 85, 45, 40, 4, 78, 6, 82, 2, 35]
        })

    # Load data từ DataManager hoặc dữ liệu mẫu
    df_secretary = data_manager.get_category_data('Hệ thống thư ký Bệnh viện')

    if df_secretary is not None:
        st.info(f"✅ Đã tải {len(df_secretary)} bản ghi cho Hệ thống thư ký từ file: {data_manager.metadata['filename']}")
    else:
        st.info("📁 Chưa có dữ liệu được tải từ sidebar. Hiển thị dữ liệu mẫu.")
        df_secretary = create_secretary_data()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    if not df_secretary.empty:
        # Metrics overview tổng quan
        st.markdown('<div class="section-header">📊 Tổng quan hoạt động Hệ thống thư ký</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        # Debug: Hiển thị cấu trúc dữ liệu
        with st.expander("🔍 Debug: Cấu trúc dữ liệu Hệ thống thư ký", expanded=False):
            st.write("**Columns:**", list(df_secretary.columns))
            st.write("**Shape:**", df_secretary.shape)
            if 'Nội dung' in df_secretary.columns:
                st.write("**Nội dung values:**", df_secretary['Nội dung'].unique().tolist())
            st.dataframe(df_secretary.head())

        # Tính toán metrics từ dữ liệu - CỘNG TỔNG TẤT CẢ CÁC TUẦN
        def get_secretary_metric_value(content_name):
            if 'Nội dung' not in df_secretary.columns or 'Số liệu' not in df_secretary.columns:
                return 0

            # Lấy tất cả các hàng có nội dung này và cộng tổng
            result = df_secretary[df_secretary['Nội dung'] == content_name]['Số liệu']
            if len(result) > 0:
                # Clean data: remove non-breaking spaces and other whitespace characters
                cleaned_result = result.astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip()
                # Convert tất cả values thành numeric và cộng tổng
                numeric_values = pd.to_numeric(cleaned_result, errors='coerce').fillna(0)
                total = numeric_values.sum()
                return total
            return 0

        tong_tk = get_secretary_metric_value('Tổng số thư ký')
        tuyen_moi = get_secretary_metric_value('Số thư ký được tuyển dụng')
        nghi_viec = get_secretary_metric_value('Số thư ký nghỉ việc')
        dao_tao = get_secretary_metric_value('Số buổi tập huấn, đào tạo cho thư ký')

        with col1:
            st.metric("👥 Tổng thư ký", f"{int(tong_tk):,}", help="Tổng số thư ký tất cả các tuần")
        with col2:
            st.metric("✅ Tuyển mới", f"{int(tuyen_moi):,}", help="Tổng số thư ký được tuyển dụng tất cả các tuần")
        with col3:
            st.metric("❌ Nghỉ việc", f"{int(nghi_viec):,}", help="Tổng số thư ký nghỉ việc tất cả các tuần")
        with col4:
            st.metric("📚 Đào tạo", f"{int(dao_tao):,} buổi", help="Tổng số buổi tập huấn, đào tạo tất cả các tuần")

        # Thêm hàng metrics thứ 2
        col5, col6, col7, col8 = st.columns(4)

        hanh_chinh = get_secretary_metric_value('- Thư ký hành chính')
        chuyen_mon = get_secretary_metric_value('- Thư ký chuyên môn')
        sinh_hoat = get_secretary_metric_value('Số buổi sinh hoạt cho thư ký')
        tham_quan = get_secretary_metric_value('Số buổi tham quan, học tập')

        with col5:
            st.metric("🏢 Hành chính", f"{int(hanh_chinh):,}", help="Tổng số thư ký hành chính tất cả các tuần")
        with col6:
            st.metric("⚕️ Chuyên môn", f"{int(chuyen_mon):,}", help="Tổng số thư ký chuyên môn tất cả các tuần")
        with col7:
            st.metric("🎯 Sinh hoạt", f"{int(sinh_hoat):,} buổi", help="Tổng số buổi sinh hoạt tất cả các tuần")
        with col8:
            st.metric("🎓 Tham quan", f"{int(tham_quan):,} buổi", help="Tổng số buổi tham quan, học tập tất cả các tuần")

        st.markdown("<br>", unsafe_allow_html=True)

        # Pivot Table Section - giống như Tab 4
        create_secretary_pivot_table(df_secretary)

        st.markdown("<br>", unsafe_allow_html=True)

        # Biểu đồ tổng quan
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích</div>', unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Biểu đồ phân bố thư ký theo loại
            type_data = df_secretary[df_secretary['Nội dung'].isin(['- Thư ký hành chính', '- Thư ký chuyên môn'])]

            if not type_data.empty:
                # Làm sạch tên hiển thị
                type_data_clean = type_data.copy()
                type_data_clean['Nội dung'] = type_data_clean['Nội dung'].str.replace('- Thư ký ', '')

                fig_type = px.pie(type_data_clean, values='Số liệu', names='Nội dung',
                                title='👥 Phân bố thư ký theo loại',
                                hole=0.4)
                fig_type.update_layout(height=400)
                st.plotly_chart(fig_type, use_container_width=True)

        with col_chart2:
            # Biểu đồ tuyển dụng vs nghỉ việc
            hr_data = df_secretary[df_secretary['Nội dung'].isin(['Số thư ký được tuyển dụng', 'Số thư ký nghỉ việc'])]
            if not hr_data.empty:
                hr_summary = pd.DataFrame({
                    'Loại': ['Tuyển dụng', 'Nghỉ việc'],
                    'Số liệu': [get_secretary_metric_value('Số thư ký được tuyển dụng'), get_secretary_metric_value('Số thư ký nghỉ việc')]
                })

                fig_hr = px.bar(hr_summary, x='Loại', y='Số liệu',
                              title='📊 Tuyển dụng vs Nghỉ việc',
                              color='Loại',
                              color_discrete_map={'Tuyển dụng': '#2ecc71', 'Nghỉ việc': '#e74c3c'})
                fig_hr.update_layout(height=400)
                st.plotly_chart(fig_hr, use_container_width=True)

        # Biểu đồ phân tích chi tiết
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích chi tiết</div>', unsafe_allow_html=True)

        # Row 1: Biểu đồ tổng quan hoạt động
        col_detail1, col_detail2 = st.columns(2)

        with col_detail1:
            # Xu hướng tổng số thư ký theo tuần
            secretary_time_data = df_secretary[df_secretary['Nội dung'].isin(['Tổng số thư ký', 'Số thư ký được tuyển dụng', 'Số thư ký nghỉ việc'])]

            if not secretary_time_data.empty and 'Tuần' in secretary_time_data.columns:
                secretary_pivot = secretary_time_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
                secretary_pivot = secretary_pivot.reset_index()
                secretary_pivot['Tuần'] = pd.to_numeric(secretary_pivot['Tuần'], errors='coerce')
                secretary_pivot = secretary_pivot.sort_values('Tuần')

                # Clean data
                for col in secretary_pivot.columns:
                    if col != 'Tuần':
                        secretary_pivot[col] = pd.to_numeric(secretary_pivot[col], errors='coerce').fillna(0)

                if 'Tổng số thư ký' in secretary_pivot.columns:
                    fig_secretary_trend = go.Figure()

                    # Tổng số thư ký
                    fig_secretary_trend.add_trace(go.Scatter(
                        x=secretary_pivot['Tuần'],
                        y=secretary_pivot['Tổng số thư ký'],
                        mode='lines',
                        name='Tổng số thư ký',
                        line=dict(color='#3498db', width=3),
                        yaxis='y'
                    ))

                    # Tuyển dụng và nghỉ việc (trục phải)
                    if 'Số thư ký được tuyển dụng' in secretary_pivot.columns:
                        fig_secretary_trend.add_trace(go.Scatter(
                            x=secretary_pivot['Tuần'],
                            y=secretary_pivot['Số thư ký được tuyển dụng'],
                            mode='lines',
                            name='Tuyển dụng',
                            line=dict(color='#2ecc71', width=3),
                            yaxis='y2'
                        ))

                    if 'Số thư ký nghỉ việc' in secretary_pivot.columns:
                        fig_secretary_trend.add_trace(go.Scatter(
                            x=secretary_pivot['Tuần'],
                            y=secretary_pivot['Số thư ký nghỉ việc'],
                            mode='lines',
                            name='Nghỉ việc',
                            line=dict(color='#e74c3c', width=3),
                            yaxis='y2'
                        ))

                    fig_secretary_trend.update_layout(
                        title='👥 Xu hướng thư ký theo tuần',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Tổng số thư ký', side='left', color='#3498db'),
                        yaxis2=dict(title='Tuyển dụng/Nghỉ việc', side='right', overlaying='y', color='#2ecc71'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_secretary_trend, use_container_width=True)

        with col_detail2:
            # Phân tích hoạt động đào tạo
            training_data = df_secretary[df_secretary['Nội dung'].isin(['Số buổi tập huấn, đào tạo cho thư ký', 'Số buổi sinh hoạt cho thư ký', 'Số buổi tham quan, học tập'])]

            if not training_data.empty and 'Tuần' in training_data.columns:
                training_pivot = training_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
                training_pivot = training_pivot.reset_index()
                training_pivot['Tuần'] = pd.to_numeric(training_pivot['Tuần'], errors='coerce')
                training_pivot = training_pivot.sort_values('Tuần')

                # Clean data
                for col in training_pivot.columns:
                    if col != 'Tuần':
                        training_pivot[col] = pd.to_numeric(training_pivot[col], errors='coerce').fillna(0)

                # Tạo biểu đồ stacked bar
                fig_training = go.Figure()

                colors = ['#f39c12', '#9b59b6', '#1abc9c']
                color_idx = 0

                for col in training_pivot.columns:
                    if col != 'Tuần':
                        display_name = col.replace('Số buổi ', '').replace(' cho thư ký', '')
                        fig_training.add_trace(go.Bar(
                            x=training_pivot['Tuần'],
                            y=training_pivot[col],
                            name=display_name,
                            marker_color=colors[color_idx % len(colors)]
                        ))
                        color_idx += 1

                fig_training.update_layout(
                    title='📚 Hoạt động đào tạo theo tuần',
                    height=350,
                    xaxis=dict(title='Tuần', title_standoff=35),
                    yaxis_title='Số buổi',
                    barmode='stack',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=-0.35,
                        xanchor="center",
                        x=0.5
                    ),
                    margin=dict(b=100)
                )

                st.plotly_chart(fig_training, use_container_width=True)

        # Bảng dữ liệu chi tiết
        st.markdown('<div class="section-header">📊 Dữ liệu chi tiết</div>', unsafe_allow_html=True)

        # Hiển thị bảng với formatting
        display_df = df_secretary.copy()
        # Clean and format the data display
        def clean_and_format_secretary_number(x):
            # Clean non-breaking spaces and other whitespace
            cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
            numeric_val = pd.to_numeric(cleaned, errors='coerce')
            if pd.isna(numeric_val):
                return str(x)  # Return original if conversion fails
            elif numeric_val >= 1:
                return f"{numeric_val:,.0f}"
            else:
                return f"{numeric_val:.1f}"

        display_df['Số liệu'] = display_df['Số liệu'].apply(clean_and_format_secretary_number)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.error("❌ Không có dữ liệu Hệ thống thư ký")
        st.info("📁 Upload dữ liệu hoặc kiểm tra kết nối GitHub để xem thống kê chi tiết")

# Tab 7: Bãi giữ xe
with tab7:
    st.markdown('<div class="tab-header">🅿️ Báo cáo Bãi giữ xe</div>', unsafe_allow_html=True)

    def create_parking_data():
        """Tạo dữ liệu mẫu cho bãi giữ xe"""
        return pd.DataFrame({
            'Tuần': [39] * 6,
            'Tháng': [9] * 6,
            'Nội dung': [
                'Tổng số lượt vé ngày',
                'Tổng số lượt vé tháng',
                'Công suất trung bình/ngày',
                'Doanh thu',
                'Số phản ánh khiếu nại',
                'Tỷ lệ sử dụng'
            ],
            'Số liệu': [1850, 145, 265, 18500000, 8, 78.5]
        })

    # Load data từ DataManager hoặc dữ liệu mẫu
    df_parking = data_manager.get_category_data('Bãi giữ xe')

    if df_parking is not None:
        st.info(f"✅ Đã tải {len(df_parking)} bản ghi cho Bãi giữ xe từ file: {data_manager.metadata['filename']}")
    else:
        st.info("📁 Chưa có dữ liệu được tải từ sidebar. Hiển thị dữ liệu mẫu.")
        df_parking = create_parking_data()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    if not df_parking.empty:
        # Metrics overview tổng quan
        st.markdown('<div class="section-header">📊 Tổng quan hoạt động Bãi giữ xe</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        # Debug: Hiển thị cấu trúc dữ liệu
        with st.expander("🔍 Debug: Cấu trúc dữ liệu Bãi giữ xe", expanded=False):
            st.write("**Columns:**", list(df_parking.columns))
            st.write("**Shape:**", df_parking.shape)
            if 'Nội dung' in df_parking.columns:
                st.write("**Nội dung values:**", df_parking['Nội dung'].unique().tolist())
            st.dataframe(df_parking.head())

        # Tính toán metrics từ dữ liệu - CỘNG TỔNG TẤT CẢ CÁC TUẦN
        def get_parking_metric_value(content_name):
            if 'Nội dung' not in df_parking.columns or 'Số liệu' not in df_parking.columns:
                return 0

            # Lấy tất cả các hàng có nội dung này và cộng tổng
            result = df_parking[df_parking['Nội dung'] == content_name]['Số liệu']
            if len(result) > 0:
                # Clean data: remove non-breaking spaces and other whitespace characters
                cleaned_result = result.astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip()
                # Convert tất cả values thành numeric và cộng tổng
                numeric_values = pd.to_numeric(cleaned_result, errors='coerce').fillna(0)
                total = numeric_values.sum()
                return total
            return 0

        ve_ngay = get_parking_metric_value('Tổng số lượt vé ngày')
        ve_thang = get_parking_metric_value('Tổng số lượt vé tháng')
        doanh_thu = get_parking_metric_value('Doanh thu')
        khieu_nai = get_parking_metric_value('Số phản ánh khiếu nại')

        with col1:
            st.metric("🎫 Vé ngày", f"{int(ve_ngay):,}", help="Tổng số lượt vé ngày tất cả các tuần")
        with col2:
            st.metric("📅 Vé tháng", f"{int(ve_thang):,}", help="Tổng số lượt vé tháng tất cả các tuần")
        with col3:
            st.metric("💰 Doanh thu", f"{int(doanh_thu):,} VND", help="Tổng doanh thu tất cả các tuần")
        with col4:
            st.metric("📢 Khiếu nại", f"{int(khieu_nai):,}", help="Tổng số phản ánh khiếu nại tất cả các tuần")

        # Thêm hàng metrics thứ 2
        col5, col6, col7, col8 = st.columns(4)

        cong_suat = get_parking_metric_value('Công suất trung bình/ngày')
        ty_le_su_dung = get_parking_metric_value('Tỷ lệ sử dụng')
        # Tính tổng vé (ngày + tháng)
        tong_ve = ve_ngay + ve_thang
        # Tính doanh thu trung bình mỗi vé
        doanh_thu_per_ve = (doanh_thu / tong_ve) if tong_ve > 0 else 0

        with col5:
            st.metric("⚡ Công suất", f"{int(cong_suat):,} xe/ngày", help="Công suất trung bình mỗi ngày tất cả các tuần")
        with col6:
            st.metric("📊 Tỷ lệ SD", f"{ty_le_su_dung:.1f}%", help="Tỷ lệ sử dụng trung bình tất cả các tuần")
        with col7:
            st.metric("📝 Tổng vé", f"{int(tong_ve):,}", help="Tổng tất cả vé (ngày + tháng)")
        with col8:
            st.metric("💵 DT/vé", f"{int(doanh_thu_per_ve):,} VND", help="Doanh thu trung bình mỗi vé")

        st.markdown("<br>", unsafe_allow_html=True)

        # Pivot Table Section - giống như Tab 4
        create_parking_pivot_table(df_parking)

        st.markdown("<br>", unsafe_allow_html=True)

        # Biểu đồ tổng quan
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích</div>', unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Biểu đồ phân bố vé ngày vs vé tháng
            ticket_data = df_parking[df_parking['Nội dung'].isin(['Tổng số lượt vé ngày', 'Tổng số lượt vé tháng'])]

            if not ticket_data.empty:
                # Làm sạch tên hiển thị
                ticket_data_clean = ticket_data.copy()
                ticket_data_clean['Nội dung'] = ticket_data_clean['Nội dung'].str.replace('Tổng số lượt ', '')

                fig_ticket = px.pie(ticket_data_clean, values='Số liệu', names='Nội dung',
                                  title='🎫 Phân bố loại vé',
                                  hole=0.4)
                fig_ticket.update_layout(height=400)
                st.plotly_chart(fig_ticket, use_container_width=True)

        with col_chart2:
            # Biểu đồ doanh thu và khiếu nại
            summary_data = pd.DataFrame({
                'Chỉ số': ['Doanh thu (triệu VND)', 'Khiếu nại'],
                'Giá trị': [doanh_thu/1000000, khieu_nai]  # Doanh thu tính theo triệu
            })

            fig_summary = px.bar(summary_data, x='Chỉ số', y='Giá trị',
                               title='💰 Doanh thu và Khiếu nại',
                               color='Chỉ số',
                               color_discrete_map={'Doanh thu (triệu VND)': '#2ecc71', 'Khiếu nại': '#e74c3c'})
            fig_summary.update_layout(height=400, yaxis_title='Giá trị')
            st.plotly_chart(fig_summary, use_container_width=True)

        # Biểu đồ phân tích chi tiết
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích chi tiết</div>', unsafe_allow_html=True)

        # Row 1: Biểu đồ tổng quan hoạt động
        col_detail1, col_detail2 = st.columns(2)

        with col_detail1:
            # Xu hướng doanh thu và số vé theo tuần
            parking_time_data = df_parking[df_parking['Nội dung'].isin(['Doanh thu', 'Tổng số lượt vé ngày', 'Tổng số lượt vé tháng'])]

            if not parking_time_data.empty and 'Tuần' in parking_time_data.columns:
                parking_pivot = parking_time_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                parking_pivot = parking_pivot.reset_index()
                parking_pivot['Tuần'] = pd.to_numeric(parking_pivot['Tuần'], errors='coerce')
                parking_pivot = parking_pivot.sort_values('Tuần')

                # Clean data
                for col in parking_pivot.columns:
                    if col != 'Tuần':
                        parking_pivot[col] = pd.to_numeric(parking_pivot[col], errors='coerce').fillna(0)

                # Tính tổng vé
                if 'Tổng số lượt vé ngày' in parking_pivot.columns and 'Tổng số lượt vé tháng' in parking_pivot.columns:
                    parking_pivot['Tổng vé'] = parking_pivot['Tổng số lượt vé ngày'] + parking_pivot['Tổng số lượt vé tháng']

                if 'Doanh thu' in parking_pivot.columns and 'Tổng vé' in parking_pivot.columns:
                    fig_parking_trend = go.Figure()

                    # Doanh thu (trục trái)
                    fig_parking_trend.add_trace(go.Scatter(
                        x=parking_pivot['Tuần'],
                        y=parking_pivot['Doanh thu'],
                        mode='lines',
                        name='Doanh thu',
                        line=dict(color='#2ecc71', width=3),
                        yaxis='y'
                    ))

                    # Tổng vé (trục phải)
                    fig_parking_trend.add_trace(go.Scatter(
                        x=parking_pivot['Tuần'],
                        y=parking_pivot['Tổng vé'],
                        mode='lines',
                        name='Tổng vé',
                        line=dict(color='#3498db', width=3),
                        yaxis='y2'
                    ))

                    fig_parking_trend.update_layout(
                        title='💰 Xu hướng doanh thu và số vé theo tuần',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Doanh thu (VND)', side='left', color='#2ecc71'),
                        yaxis2=dict(title='Số vé', side='right', overlaying='y', color='#3498db'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_parking_trend, use_container_width=True)

        with col_detail2:
            # Phân tích công suất và tỷ lệ sử dụng
            capacity_data = df_parking[df_parking['Nội dung'].isin(['Công suất trung bình/ngày', 'Tỷ lệ sử dụng', 'Số phản ánh khiếu nại'])]

            if not capacity_data.empty and 'Tuần' in capacity_data.columns:
                capacity_pivot = capacity_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0).infer_objects(copy=False)
                capacity_pivot = capacity_pivot.reset_index()
                capacity_pivot['Tuần'] = pd.to_numeric(capacity_pivot['Tuần'], errors='coerce')
                capacity_pivot = capacity_pivot.sort_values('Tuần')

                # Clean data
                for col in capacity_pivot.columns:
                    if col != 'Tuần':
                        capacity_pivot[col] = pd.to_numeric(capacity_pivot[col], errors='coerce').fillna(0)

                if 'Công suất trung bình/ngày' in capacity_pivot.columns and 'Tỷ lệ sử dụng' in capacity_pivot.columns:
                    fig_capacity = go.Figure()

                    # Công suất (trục trái)
                    fig_capacity.add_trace(go.Scatter(
                        x=capacity_pivot['Tuần'],
                        y=capacity_pivot['Công suất trung bình/ngày'],
                        mode='lines',
                        name='Công suất',
                        line=dict(color='#9b59b6', width=3),
                        yaxis='y'
                    ))

                    # Tỷ lệ sử dụng (trục phải)
                    fig_capacity.add_trace(go.Scatter(
                        x=capacity_pivot['Tuần'],
                        y=capacity_pivot['Tỷ lệ sử dụng'],
                        mode='lines',
                        name='Tỷ lệ sử dụng (%)',
                        line=dict(color='#f39c12', width=3),
                        yaxis='y2'
                    ))

                    # Khiếu nại (nếu có)
                    if 'Số phản ánh khiếu nại' in capacity_pivot.columns:
                        fig_capacity.add_trace(go.Bar(
                            x=capacity_pivot['Tuần'],
                            y=capacity_pivot['Số phản ánh khiếu nại'],
                            name='Khiếu nại',
                            marker_color='#e74c3c',
                            opacity=0.7,
                            yaxis='y'
                        ))

                    fig_capacity.update_layout(
                        title='⚡ Phân tích công suất và chất lượng',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Công suất / Khiếu nại', side='left', color='#9b59b6'),
                        yaxis2=dict(title='Tỷ lệ sử dụng (%)', side='right', overlaying='y', color='#f39c12'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_capacity, use_container_width=True)

        # Bảng dữ liệu chi tiết
        st.markdown('<div class="section-header">📊 Dữ liệu chi tiết</div>', unsafe_allow_html=True)

        # Hiển thị bảng với formatting
        display_df = df_parking.copy()
        # Clean and format the data display
        def clean_and_format_parking_number(x):
            # Clean non-breaking spaces and other whitespace
            cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
            numeric_val = pd.to_numeric(cleaned, errors='coerce')
            if pd.isna(numeric_val):
                return str(x)  # Return original if conversion fails
            elif numeric_val >= 1:
                return f"{numeric_val:,.0f}"
            else:
                return f"{numeric_val:.1f}"

        display_df['Số liệu'] = display_df['Số liệu'].apply(clean_and_format_parking_number)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.error("❌ Không có dữ liệu Bãi giữ xe")
        st.info("📁 Upload dữ liệu hoặc kiểm tra kết nối GitHub để xem thống kê chi tiết")

def create_event_pivot_table(df):
    """Tạo pivot table cho dữ liệu sự kiện"""

    # CSS cho table
    st.markdown("""
    <style>
    .pivot-table-event {
        font-size: 16px !important;
        font-weight: 500;
    }
    .pivot-table-event td {
        padding: 12px 8px !important;
        text-align: center !important;
    }
    .pivot-table-event th {
        padding: 15px 8px !important;
        text-align: center !important;
        background-color: #f0f2f6 !important;
        font-weight: bold !important;
        font-size: 17px !important;
    }
    .increase { color: #16a085; font-weight: 600; }
    .decrease { color: #e74c3c; font-weight: 600; }
    .neutral { color: #7f8c8d; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Tuần', 'Tháng', 'Năm'],
            index=0,
            key="event_period_type"
        )

    # Xử lý dữ liệu thời gian
    has_time_data = False
    df_period = df.copy()

    if 'Tuần' in df.columns or 'Tháng' in df.columns:
        has_time_data = True

        if period_type == 'Tuần' and 'Tuần' in df.columns:
            df_period['period'] = 'W' + df_period['Tuần'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
        elif period_type == 'Tháng' and 'Tháng' in df.columns:
            df_period['period'] = 'T' + df_period['Tháng'].astype(str)
            df_period['period_sort'] = pd.to_numeric(df_period['Tháng'], errors='coerce')
        elif period_type == 'Năm':
            df_period['period'] = '2025'
            df_period['period_sort'] = 2025
        else:
            if 'Tuần' in df.columns:
                df_period['period'] = 'W' + df_period['Tuần'].astype(str)
                df_period['period_sort'] = pd.to_numeric(df_period['Tuần'], errors='coerce')
            else:
                has_time_data = False

    if has_time_data:
        # Các metric cho sự kiện
        event_metrics = ['tong_su_kien', 'chu_tri', 'phoi_hop', 'quan_trong', 'hoi_nghi', 'doi_ngoai']

        # Tạo metric columns từ dữ liệu Nội dung/Số liệu
        if 'Nội dung' in df_period.columns and 'Số liệu' in df_period.columns:
            for metric in event_metrics:
                df_period[metric] = 0

            # Mapping các metric từ Nội dung
            metric_mapping = {
                'tong_su_kien': ['Tổng số sự kiện hành chính của Bệnh viện'],
                'chu_tri': ['Phòng Hành chính chủ trì'],
                'phoi_hop': ['Phòng Hành chính phối hợp'],
                'quan_trong': ['Sự kiện quan trọng'],
                'hoi_nghi': ['Hội nghị hội thảo'],
                'doi_ngoai': ['Hoạt động đối ngoại']
            }

            for metric, content_names in metric_mapping.items():
                for content_name in content_names:
                    mask = df_period['Nội dung'] == content_name
                    df_period.loc[mask, metric] = pd.to_numeric(df_period.loc[mask, 'Số liệu'], errors='coerce').fillna(0)

        # Tạo pivot data
        pivot_data = df_period.groupby(['period', 'period_sort'])[event_metrics].sum().reset_index()
        pivot_data = pivot_data.sort_values('period_sort', ascending=False)

        # Tính toán biến động
        for col in event_metrics:
            pivot_data[f'{col}_prev'] = pivot_data[col].shift(-1)
            pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
            pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
            pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)

        # Hàm format cell với biến động
        def format_cell_with_change(row, col):
            current_val = row[col]
            change_val = row[f'{col}_change']
            change_pct = row[f'{col}_change_pct']
            prev_val = row[f'{col}_prev']

            if pd.isna(prev_val) or prev_val == 0:
                return f"{int(current_val):,}"

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

            return f"""<div style="text-align: center; line-height: 1.2;">
                <div style="font-size: 16px; font-weight: 600;">{int(current_val):,}</div>
                <div class="{color_class}" style="font-size: 12px;">{arrow} {sign}{int(change_val):,} ({sign}{change_pct:.1f}%)</div>
            </div>"""

        # Tạo HTML table
        display_data = pivot_data.copy()

        # Tạo header
        html_table = '''
        <table class="pivot-table-event" style="width: 100%; border-collapse: collapse; margin: 20px 0; border: 2px solid #34495e;">
            <thead>
                <tr style="background: linear-gradient(90deg, #34495e, #2c3e50); color: white;">
                    <th style="border: 1px solid #ddd; position: sticky; left: 0; background: #2c3e50; z-index: 10;">Kỳ</th>
                    <th style="border: 1px solid #ddd;">🎉 Tổng SK</th>
                    <th style="border: 1px solid #ddd;">👑 Chủ trì</th>
                    <th style="border: 1px solid #ddd;">🤝 Phối hợp</th>
                    <th style="border: 1px solid #ddd;">⭐ Quan trọng</th>
                    <th style="border: 1px solid #ddd;">🏛️ Hội nghị</th>
                    <th style="border: 1px solid #ddd;">🌍 Đối ngoại</th>
                </tr>
            </thead>
            <tbody>
        '''

        # Thêm các row dữ liệu
        for i, row in display_data.iterrows():
            period_display = row['period']

            # Alternating row colors
            row_color = "#f8f9fa" if i % 2 == 0 else "#ffffff"

            html_table += f'''
            <tr style="background-color: {row_color};">
                <td style="border: 1px solid #ddd; font-weight: bold; background-color: #ecf0f1; position: sticky; left: 0; z-index: 5;">{period_display}</td>
                <td style="border: 1px solid #ddd;">{format_cell_with_change(row, 'tong_su_kien')}</td>
                <td style="border: 1px solid #ddd;">{format_cell_with_change(row, 'chu_tri')}</td>
                <td style="border: 1px solid #ddd;">{format_cell_with_change(row, 'phoi_hop')}</td>
                <td style="border: 1px solid #ddd;">{format_cell_with_change(row, 'quan_trong')}</td>
                <td style="border: 1px solid #ddd;">{format_cell_with_change(row, 'hoi_nghi')}</td>
                <td style="border: 1px solid #ddd;">{format_cell_with_change(row, 'doi_ngoai')}</td>
            </tr>
            '''

        html_table += '''
            </tbody>
        </table>
        <div style="text-align: center; margin: 10px 0; color: #7f8c8d; font-size: 12px;">
            📈 <span style="color: #16a085;">↗ Tăng</span> |
            📉 <span style="color: #e74c3c;">↘ Giảm</span> |
            ➡️ <span style="color: #7f8c8d;">→ Không đổi</span>
        </div>
        '''

        return html_table
    else:
        return "<p style='text-align: center; color: #e74c3c;'>⚠️ Không có dữ liệu thời gian để tạo bảng pivot</p>"

# Tab 8: Sự kiện
with tab8:
    st.markdown('<div class="tab-header">🎉 Báo cáo Sự kiện</div>', unsafe_allow_html=True)

    def create_events_data():
        """Tạo dữ liệu mẫu cho sự kiện"""
        return pd.DataFrame({
            'Tuần': [39] * 8,
            'Tháng': [9] * 8,
            'Nội dung': [
                'Tổng số sự kiện hành chính của Bệnh viện',
                'Phòng Hành chính chủ trì',
                'Phòng Hành chính phối hợp',
                'Tỷ lệ thành công',
                'Sự kiện quan trọng',
                'Hội nghị hội thảo',
                'Hoạt động đối ngoại',
                'Mức độ hài lòng'
            ],
            'Số liệu': [25, 15, 10, 96.0, 8, 12, 5, 92.5]
        })

    # Load data từ DataManager hoặc dữ liệu mẫu
    df_events = data_manager.get_category_data('Sự kiện')

    if df_events is not None:
        st.info(f"✅ Đã tải {len(df_events)} bản ghi cho Sự kiện từ file: {data_manager.metadata['filename']}")
    else:
        st.info("📁 Chưa có dữ liệu được tải từ sidebar. Hiển thị dữ liệu mẫu.")
        df_events = create_events_data()

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    if not df_events.empty:
        # Metrics overview tổng quan
        st.markdown('<div class="section-header">📊 Tổng quan hoạt động Sự kiện</div>', unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns(4)

        # Debug: Hiển thị cấu trúc dữ liệu
        with st.expander("🔍 Debug: Cấu trúc dữ liệu Sự kiện", expanded=False):
            st.write("**Columns:**", list(df_events.columns))
            st.write("**Shape:**", df_events.shape)
            if 'Nội dung' in df_events.columns:
                st.write("**Nội dung values:**", df_events['Nội dung'].unique().tolist())
            st.dataframe(df_events.head())

        # Tính toán metrics từ dữ liệu - CỘNG TỔNG TẤT CẢ CÁC TUẦN
        def get_event_metric_value(content_name):
            if 'Nội dung' not in df_events.columns or 'Số liệu' not in df_events.columns:
                return 0

            # Lấy tất cả các hàng có nội dung này và cộng tổng
            result = df_events[df_events['Nội dung'] == content_name]['Số liệu']
            if len(result) > 0:
                # Clean data: remove non-breaking spaces and other whitespace characters
                cleaned_result = result.astype(str).str.replace('\xa0', '').str.replace(' ', '').str.strip()
                # Convert tất cả values thành numeric và cộng tổng
                numeric_values = pd.to_numeric(cleaned_result, errors='coerce').fillna(0)
                total = numeric_values.sum()
                return total
            return 0

        tong_sk = get_event_metric_value('Tổng số sự kiện hành chính của Bệnh viện')
        chu_tri = get_event_metric_value('Phòng Hành chính chủ trì')
        phoi_hop = get_event_metric_value('Phòng Hành chính phối hợp')
        thanh_cong = get_event_metric_value('Tỷ lệ thành công')

        with col1:
            st.metric("🎉 Tổng sự kiện", f"{int(tong_sk):,}", help="Tổng số sự kiện hành chính tất cả các tuần")
        with col2:
            st.metric("👑 Chủ trì", f"{int(chu_tri):,}", help="Tổng số sự kiện chủ trì tất cả các tuần")
        with col3:
            st.metric("🤝 Phối hợp", f"{int(phoi_hop):,}", help="Tổng số sự kiện phối hợp tất cả các tuần")
        with col4:
            st.metric("✅ Thành công", f"{thanh_cong:.1f}%", help="Tỷ lệ thành công trung bình tất cả các tuần")

        # Thêm hàng metrics thứ 2
        col5, col6, col7, col8 = st.columns(4)

        quan_trong = get_event_metric_value('Sự kiện quan trọng')
        hoi_nghi = get_event_metric_value('Hội nghị hội thảo')
        doi_ngoai = get_event_metric_value('Hoạt động đối ngoại')
        hai_long = get_event_metric_value('Mức độ hài lòng')

        with col5:
            st.metric("⭐ Quan trọng", f"{int(quan_trong):,}", help="Tổng số sự kiện quan trọng tất cả các tuần")
        with col6:
            st.metric("🏛️ Hội nghị", f"{int(hoi_nghi):,}", help="Tổng số hội nghị hội thảo tất cả các tuần")
        with col7:
            st.metric("🌍 Đối ngoại", f"{int(doi_ngoai):,}", help="Tổng số hoạt động đối ngoại tất cả các tuần")
        with col8:
            st.metric("😊 Hài lòng", f"{hai_long:.1f}%", help="Mức độ hài lòng trung bình tất cả các tuần")

        st.markdown("<br>", unsafe_allow_html=True)

        # Pivot Table Section - giống như Tab 4
        create_event_pivot_table(df_events)

        st.markdown("<br>", unsafe_allow_html=True)

        # Biểu đồ tổng quan
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích</div>', unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns(2)

        with col_chart1:
            # Biểu đồ phân bố loại sự kiện
            event_distribution_data = pd.DataFrame({
                'Loại sự kiện': ['Chủ trì', 'Phối hợp', 'Quan trọng', 'Hội nghị', 'Đối ngoại'],
                'Số lượng': [int(chu_tri), int(phoi_hop), int(quan_trong), int(hoi_nghi), int(doi_ngoai)]
            })

            fig_event = px.pie(event_distribution_data, values='Số lượng', names='Loại sự kiện',
                              title='🎯 Phân bố loại sự kiện',
                              hole=0.4)
            fig_event.update_layout(height=400)
            st.plotly_chart(fig_event, use_container_width=True)

        with col_chart2:
            # Biểu đồ hiệu quả và hài lòng
            efficiency_data = pd.DataFrame({
                'Chỉ số': ['Tỷ lệ thành công (%)', 'Mức độ hài lòng (%)'],
                'Giá trị': [float(thanh_cong), float(hai_long)]
            })

            fig_efficiency = px.bar(efficiency_data, x='Chỉ số', y='Giá trị',
                                   title='📊 Hiệu quả tổ chức sự kiện',
                                   color='Chỉ số',
                                   color_discrete_map={'Tỷ lệ thành công (%)': '#2ecc71', 'Mức độ hài lòng (%)': '#3498db'})
            fig_efficiency.update_layout(height=400, yaxis_title='Tỷ lệ (%)')
            st.plotly_chart(fig_efficiency, use_container_width=True)

        # Biểu đồ phân tích chi tiết
        st.markdown('<div class="section-header">📈 Biểu đồ phân tích chi tiết</div>', unsafe_allow_html=True)

        # Row 1: Biểu đồ tổng quan hoạt động
        col_detail1, col_detail2 = st.columns(2)

        with col_detail1:
            # Xu hướng tổng sự kiện và chủ trì theo tuần
            events_time_data = df_events[df_events['Nội dung'].isin(['Tổng số sự kiện hành chính của Bệnh viện', 'Phòng Hành chính chủ trì', 'Phòng Hành chính phối hợp'])]

            if not events_time_data.empty and 'Tuần' in events_time_data.columns:
                events_pivot = events_time_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
                events_pivot = events_pivot.reset_index()
                events_pivot['Tuần'] = pd.to_numeric(events_pivot['Tuần'], errors='coerce')
                events_pivot = events_pivot.sort_values('Tuần')

                # Clean data
                for col in events_pivot.columns:
                    if col != 'Tuần':
                        events_pivot[col] = pd.to_numeric(events_pivot[col], errors='coerce').fillna(0)

                # Tính tổng sự kiện do phòng hành chính thực hiện
                if 'Phòng Hành chính chủ trì' in events_pivot.columns and 'Phòng Hành chính phối hợp' in events_pivot.columns:
                    events_pivot['HC thực hiện'] = events_pivot['Phòng Hành chính chủ trì'] + events_pivot['Phòng Hành chính phối hợp']

                if 'Tổng số sự kiện hành chính của Bệnh viện' in events_pivot.columns and 'HC thực hiện' in events_pivot.columns:
                    fig_events_trend = go.Figure()

                    # Tổng sự kiện (trục trái)
                    fig_events_trend.add_trace(go.Scatter(
                        x=events_pivot['Tuần'],
                        y=events_pivot['Tổng số sự kiện hành chính của Bệnh viện'],
                        mode='lines',
                        name='Tổng sự kiện',
                        line=dict(color='#3498db', width=3),
                        yaxis='y'
                    ))

                    # HC thực hiện (trục phải)
                    fig_events_trend.add_trace(go.Scatter(
                        x=events_pivot['Tuần'],
                        y=events_pivot['HC thực hiện'],
                        mode='lines',
                        name='HC thực hiện',
                        line=dict(color='#e74c3c', width=3),
                        yaxis='y2'
                    ))

                    fig_events_trend.update_layout(
                        title='🎉 Xu hướng sự kiện theo tuần',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Tổng sự kiện', side='left', color='#3498db'),
                        yaxis2=dict(title='HC thực hiện', side='right', overlaying='y', color='#e74c3c'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_events_trend, use_container_width=True)

        with col_detail2:
            # Phân tích hiệu quả và chất lượng
            quality_data = df_events[df_events['Nội dung'].isin(['Tỷ lệ thành công', 'Mức độ hài lòng', 'Sự kiện quan trọng'])]

            if not quality_data.empty and 'Tuần' in quality_data.columns:
                quality_pivot = quality_data.pivot(index='Tuần', columns='Nội dung', values='Số liệu').fillna(0)
                quality_pivot = quality_pivot.reset_index()
                quality_pivot['Tuần'] = pd.to_numeric(quality_pivot['Tuần'], errors='coerce')
                quality_pivot = quality_pivot.sort_values('Tuần')

                # Clean data
                for col in quality_pivot.columns:
                    if col != 'Tuần':
                        quality_pivot[col] = pd.to_numeric(quality_pivot[col], errors='coerce').fillna(0)

                if 'Tỷ lệ thành công' in quality_pivot.columns and 'Mức độ hài lòng' in quality_pivot.columns:
                    fig_quality = go.Figure()

                    # Tỷ lệ thành công (trục trái)
                    fig_quality.add_trace(go.Scatter(
                        x=quality_pivot['Tuần'],
                        y=quality_pivot['Tỷ lệ thành công'],
                        mode='lines',
                        name='Thành công (%)',
                        line=dict(color='#27ae60', width=3),
                        yaxis='y'
                    ))

                    # Mức độ hài lòng (trục phải)
                    fig_quality.add_trace(go.Scatter(
                        x=quality_pivot['Tuần'],
                        y=quality_pivot['Mức độ hài lòng'],
                        mode='lines',
                        name='Hài lòng (%)',
                        line=dict(color='#f39c12', width=3),
                        yaxis='y2'
                    ))

                    # Sự kiện quan trọng (nếu có)
                    if 'Sự kiện quan trọng' in quality_pivot.columns:
                        fig_quality.add_trace(go.Bar(
                            x=quality_pivot['Tuần'],
                            y=quality_pivot['Sự kiện quan trọng'],
                            name='SK quan trọng',
                            marker_color='#9b59b6',
                            opacity=0.7,
                            yaxis='y'
                        ))

                    fig_quality.update_layout(
                        title='📊 Phân tích chất lượng và hiệu quả',
                        height=350,
                        xaxis=dict(title='Tuần', title_standoff=35),
                        yaxis=dict(title='Thành công (%) / SK quan trọng', side='left', color='#27ae60'),
                        yaxis2=dict(title='Hài lòng (%)', side='right', overlaying='y', color='#f39c12'),
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=-0.35,
                            xanchor="center",
                            x=0.5
                        ),
                        margin=dict(b=100)
                    )

                    st.plotly_chart(fig_quality, use_container_width=True)

        # Bảng dữ liệu chi tiết
        st.markdown('<div class="section-header">📊 Dữ liệu chi tiết</div>', unsafe_allow_html=True)

        # Hiển thị bảng với formatting
        display_df = df_events.copy()
        # Clean and format the data display
        def clean_and_format_event_number(x):
            # Clean non-breaking spaces and other whitespace
            cleaned = str(x).replace('\xa0', '').replace(' ', '').strip()
            numeric_val = pd.to_numeric(cleaned, errors='coerce')
            if pd.isna(numeric_val):
                return str(x)  # Return original if conversion fails
            elif numeric_val >= 1:
                return f"{numeric_val:,.0f}"
            else:
                return f"{numeric_val:.1f}"

        display_df['Số liệu'] = display_df['Số liệu'].apply(clean_and_format_event_number)
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    else:
        st.error("❌ Không có dữ liệu Sự kiện")
        st.info("📁 Upload dữ liệu hoặc kiểm tra kết nối GitHub để xem thống kê chi tiết")

# Tab 12: Khác (cho các danh mục không phân loại)
with tab12:
    st.markdown('<div class="tab-header">🔗 Dữ liệu khác</div>', unsafe_allow_html=True)

    st.info("📁 Tab này sẽ hiển thị các dữ liệu không thuộc các danh mục đã định nghĩa ở trên")

    def create_other_data():
        """Tạo dữ liệu mẫu cho các danh mục khác"""
        return pd.DataFrame({
            'Tuần': [39] * 8,
            'Tháng': [9] * 8,
            'Danh mục': ['Lễ tân', 'Tiếp khách trong nước', 'Đón tiếp khách VIP',
                        'Tổ chức cuộc họp trực tuyến', 'Trang điều hành tác nghiệp',
                        'Lễ tân', 'Tiếp khách trong nước', 'Tiếp khách trong nước'],
            'Nội dung': [
                'Hỗ trợ lễ tân cho hội nghị/hội thảo',
                'Tổng số đoàn khách trong nước, trong đó:',
                'Số lượt khách VIP được lễ tân tiếp đón, hỗ trợ khám chữa bệnh',
                'Tổng số cuộc họp trực tuyến do Phòng Hành chính chuẩn bị',
                'Số lượng tin đăng ĐHTN',
                'Tham quan, học tập',
                'Làm việc',
                'Tỷ lệ hài lòng'
            ],
            'Số liệu': [12, 35, 125, 18, 45, 28, 7, 89.5]
        })

    # Load data từ DataManager hoặc dữ liệu mẫu
    main_categories = ['Tổ xe', 'Tổng đài', 'Hệ thống thư ký Bệnh viện', 'Bãi giữ xe', 'Sự kiện']
    df_other = data_manager.get_other_categories_data(main_categories)

    if df_other is not None:
        st.info(f"✅ Đã tải {len(df_other)} bản ghi cho danh mục khác từ file: {data_manager.metadata['filename']}")
    else:
        st.info("📁 Chưa có dữ liệu được tải từ sidebar. Hiển thị dữ liệu mẫu.")
        df_other = create_other_data()

    # Display by category if Danh mục column exists
    if 'Danh mục' in df_other.columns:
        categories = df_other['Danh mục'].unique()
        for category in categories:
            with st.expander(f"📁 {category}", expanded=True):
                category_data = df_other[df_other['Danh mục'] == category]
                st.dataframe(category_data, use_container_width=True)
    else:
        st.subheader("📊 Chi tiết dữ liệu")
        st.dataframe(df_other, use_container_width=True)

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
