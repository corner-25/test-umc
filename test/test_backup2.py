import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import json
from datetime import datetime, timedelta

# Cấu hình trang
st.set_page_config(
    page_title="Dashboard Phòng Hành Chính",
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
</style>
""", unsafe_allow_html=True)

# Header chính
st.markdown('<h1 class="main-header">🏢 Dashboard Phòng Hành Chính</h1>', unsafe_allow_html=True)

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
    pivot_data = pivot_data.sort_values('period_sort')

    # Tính toán biến động so với kỳ trước
    for col in available_columns:
        pivot_data[f'{col}_prev'] = pivot_data[col].shift(1)
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
    
    # Lựa chọn mức độ tổng hợp
    col1, col2 = st.columns([1, 3])
    with col1:
        period_type = st.selectbox(
            "📅 Tổng hợp theo:",
            options=['Ngày', 'Tuần', 'Tháng', 'Quý', 'Năm'],
            index=1,  # Mặc định là Tuần
            key="outgoing_period"
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
    pivot_columns = ['total_outgoing', 'documents', 'contracts_total', 'decisions_total', 'regulations_total', 
                    'rules_total', 'procedures_total', 'instruct_total']
    
    # Kiểm tra các cột có tồn tại không
    available_columns = [col for col in pivot_columns if col in df_period.columns]
    
    pivot_data = df_period.groupby(['period', 'period_sort'])[available_columns].sum().reset_index()
    pivot_data = pivot_data.sort_values('period_sort')
    
    # Tính toán biến động so với kỳ trước
    for col in available_columns:
        pivot_data[f'{col}_prev'] = pivot_data[col].shift(1)
        pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
        pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
        pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)
    
    # Hiển thị bảng chính
    display_columns = ['period'] + available_columns
    
    st.markdown(f"#### 📋 Tổng hợp theo {period_type}")
    st.dataframe(
        pivot_data[display_columns].rename(columns={
            'period': f'{period_type}',
            'total_outgoing': 'Tổng văn bản đi',
            'documents': 'Văn bản phát hành',
            'contracts_total': 'Hợp đồng',
            'decisions_total': 'Quyết định', 
            'regulations_total': 'Quy chế',
            'rules_total': 'Quy định',
            'procedures_total': 'Thủ tục',
            'instruct_total': 'Hướng dẫn'
        }),
        use_container_width=True
    )
    
    # Hiển thị bảng biến động
    st.markdown(f"#### 📈 Biến động so với {period_type.lower()} trước")
    
    # Format hiển thị cho các cột biến động
    change_data = pivot_data[['period']].copy()
    for col in available_columns:
        change_col = f'{col}_change'
        pct_col = f'{col}_change_pct'
        prev_col = f'{col}_prev'
        
        if change_col in pivot_data.columns and pct_col in pivot_data.columns:
            change_data[f'{col}_combined'] = pivot_data.apply(
                lambda row: f"{int(row[change_col]):+} ({row[pct_col]:+.1f}%)" 
                if pd.notna(row[change_col]) and pd.notna(row[prev_col]) and row[prev_col] != 0 else "Mới", axis=1
            )
    
    # Tạo bảng hiển thị cuối cùng
    final_change_columns = ['period'] + [f'{col}_combined' for col in available_columns if f'{col}_combined' in change_data.columns]
    final_rename = {'period': f'{period_type}'}
    for col in available_columns:
        if f'{col}_combined' in change_data.columns:
            col_name = {
                'total_outgoing': 'Tổng văn bản đi',
                'documents': 'Văn bản phát hành',
                'contracts_total': 'Hợp đồng',
                'decisions_total': 'Quyết định',
                'regulations_total': 'Quy chế', 
                'rules_total': 'Quy định',
                'procedures_total': 'Thủ tục',
                'instruct_total': 'Hướng dẫn'
            }.get(col, col)
            final_rename[f'{col}_combined'] = f'{col_name} (±%)'
    
    if len(final_change_columns) > 1:
        st.dataframe(
            change_data[final_change_columns].rename(columns=final_rename),
            use_container_width=True
        )
    
    # Thống kê tóm tắt
    if len(pivot_data) > 0:
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            total_outgoing = pivot_data['total_outgoing'].sum() if 'total_outgoing' in pivot_data.columns else 0
            st.metric("📄 Tổng văn bản đi", f"{total_outgoing:,.0f}")
        with col2:
            total_docs = pivot_data['documents'].sum() if 'documents' in pivot_data.columns else 0
            st.metric("📝 Văn bản phát hành", f"{total_docs:,.0f}")
        with col3:
            total_contracts = pivot_data['contracts_total'].sum() if 'contracts_total' in pivot_data.columns else 0
            st.metric("📁 Hợp đồng", f"{total_contracts:,.0f}")
        with col4:
            total_decisions = pivot_data['decisions_total'].sum() if 'decisions_total' in pivot_data.columns else 0
            st.metric("⚖️ Quyết định", f"{total_decisions:,.0f}")
        with col5:
            other_docs = (pivot_data[['regulations_total', 'rules_total', 'procedures_total', 'instruct_total']].sum().sum() 
                         if all(col in pivot_data.columns for col in ['regulations_total', 'rules_total', 'procedures_total', 'instruct_total']) else 0)
            st.metric("📋 Khác", f"{other_docs:,.0f}")

# Hàm tạo biểu đồ cho văn bản đi
def create_outgoing_docs_charts(df):
    # Hàng 1: Biểu đồ tổng quan
    col1, col2 = st.columns(2)
    
    with col1:
        # Biểu đồ so sánh tổng văn bản đi vs văn bản phát hành
        if 'total_outgoing' in df.columns:
            fig_compare = go.Figure()
            fig_compare.add_trace(go.Scatter(x=df['datetime'], y=df['total_outgoing'],
                                           mode='lines+markers', name='Tổng văn bản đi',
                                           line=dict(color='blue', width=3)))
            fig_compare.add_trace(go.Scatter(x=df['datetime'], y=df['documents'],
                                           mode='lines+markers', name='Văn bản phát hành',
                                           line=dict(color='orange', width=3)))
            fig_compare.update_layout(title='📈 So sánh tổng văn bản đi vs phát hành',
                                    xaxis_title="Ngày", yaxis_title="Số lượng")
            st.plotly_chart(fig_compare, use_container_width=True)
        else:
            # Fallback nếu chưa có total_outgoing
            fig_daily = px.line(df, x='datetime', y='documents', 
                               title='📈 Số lượng văn bản phát hành theo ngày',
                               markers=True)
            fig_daily.update_layout(xaxis_title="Ngày", yaxis_title="Số lượng văn bản")
            fig_daily.update_traces(line_color='#1f77b4', line_width=3)
            st.plotly_chart(fig_daily, use_container_width=True)
        
        # Biểu đồ phân bố theo loại văn bản
        categories = ['contracts_total', 'decisions_total', 'regulations_total', 
                     'rules_total', 'procedures_total', 'instruct_total']
        category_names = ['Hợp đồng', 'Quyết định', 'Quy chế', 'Quy định', 'Thủ tục', 'Hướng dẫn']
        
        category_sums = []
        available_names = []
        for i, cat in enumerate(categories):
            if cat in df.columns:
                total = df[cat].sum()
                if total > 0:
                    category_sums.append(total)
                    available_names.append(category_names[i])
        
        if category_sums:
            fig_pie = px.pie(values=category_sums, names=available_names,
                           title='📊 Phân bố theo loại văn bản')
            st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Biểu đồ xu hướng các loại văn bản chính
        fig_trend = go.Figure()
        
        if 'contracts_total' in df.columns:
            fig_trend.add_trace(go.Scatter(x=df['datetime'], y=df['contracts_total'],
                                         mode='lines+markers', name='Hợp đồng',
                                         line=dict(color='blue')))
        
        if 'decisions_total' in df.columns:
            fig_trend.add_trace(go.Scatter(x=df['datetime'], y=df['decisions_total'],
                                         mode='lines+markers', name='Quyết định',
                                         line=dict(color='red')))
        
        if 'regulations_total' in df.columns:
            fig_trend.add_trace(go.Scatter(x=df['datetime'], y=df['regulations_total'],
                                         mode='lines+markers', name='Quy chế',
                                         line=dict(color='green')))
        
        fig_trend.update_layout(title='📈 Xu hướng các loại văn bản chính',
                              xaxis_title="Ngày", yaxis_title="Số lượng")
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Biểu đồ theo tuần
        if 'week' in df.columns:
            weekly_data = df.groupby('week')['documents'].sum()
            fig_weekly = px.bar(x=weekly_data.index, y=weekly_data.values,
                               title='📅 Số lượng văn bản theo tuần')
            fig_weekly.update_layout(xaxis_title="Tuần", yaxis_title="Số lượng văn bản")
            st.plotly_chart(fig_weekly, use_container_width=True)
    
    # Hàng 2: Biểu đồ chi tiết hợp đồng và nguồn gốc
    st.markdown("#### 📁 Phân tích chi tiết các loại hợp đồng")
    
    # Tổng hợp tất cả loại hợp đồng từ toàn bộ dữ liệu
    contract_types = {}
    decision_types = {}
    
    for _, row in df.iterrows():
        # Xử lý hợp đồng
        if 'contracts_detail' in df.columns and isinstance(row['contracts_detail'], list):
            for contract in row['contracts_detail']:
                if isinstance(contract, dict) and 'name' in contract and 'count' in contract:
                    contract_name = contract['name']
                    contract_count = contract['count']
                    if contract_name in contract_types:
                        contract_types[contract_name] += contract_count
                    else:
                        contract_types[contract_name] = contract_count
        
        # Xử lý quyết định
        if 'decisions_detail' in df.columns and isinstance(row['decisions_detail'], list):
            for decision in row['decisions_detail']:
                if isinstance(decision, dict) and 'name' in decision and 'count' in decision:
                    decision_name = decision['name']
                    decision_count = decision['count']
                    if decision_name in decision_types:
                        decision_types[decision_name] += decision_count
                    else:
                        decision_types[decision_name] = decision_count
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Biểu đồ phân loại hợp đồng
        if contract_types:
            contract_names = list(contract_types.keys())
            contract_counts = list(contract_types.values())
            
            fig_contract_types = px.pie(values=contract_counts, names=contract_names,
                                      title='📄 Phân loại hợp đồng theo loại',
                                      hole=0.3)
            st.plotly_chart(fig_contract_types, use_container_width=True)
            
            # Bảng chi tiết
            st.markdown("**📋 Chi tiết các loại hợp đồng:**")
            contract_df = pd.DataFrame(list(contract_types.items()), 
                                     columns=['Loại hợp đồng', 'Số lượng'])
            contract_df = contract_df.sort_values('Số lượng', ascending=False)
            st.dataframe(contract_df, use_container_width=True)
        else:
            st.info("📄 Không có dữ liệu chi tiết hợp đồng")
    
    with col2:
        # Biểu đồ phân loại quyết định
        if decision_types:
            decision_names = list(decision_types.keys())
            decision_counts = list(decision_types.values())
            
            fig_decision_types = px.bar(x=decision_names, y=decision_counts,
                                      title='⚖️ Phân loại quyết định theo loại')
            fig_decision_types.update_layout(xaxis_title="Loại quyết định", 
                                           yaxis_title="Số lượng",
                                           xaxis_tickangle=-45)
            st.plotly_chart(fig_decision_types, use_container_width=True)
            
            # Bảng chi tiết
            st.markdown("**⚖️ Chi tiết các loại quyết định:**")
            decision_df = pd.DataFrame(list(decision_types.items()), 
                                     columns=['Loại quyết định', 'Số lượng'])
            decision_df = decision_df.sort_values('Số lượng', ascending=False)
            st.dataframe(decision_df, use_container_width=True)
        else:
            st.info("⚖️ Không có dữ liệu chi tiết quyết định")

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
    pivot_data = pivot_data.sort_values('period_sort')
    
    # Tính lại các tỷ lệ sau khi group
    pivot_data['completion_rate'] = (pivot_data['tasks_completed_on_time'] / pivot_data['tasks_assigned'] * 100).fillna(0)
    pivot_data['processing_rate'] = (pivot_data['tasks_processing'] / pivot_data['tasks_assigned'] * 100).fillna(0)
    pivot_data['new_rate'] = (pivot_data['tasks_new'] / pivot_data['tasks_assigned'] * 100).fillna(0)
    
    # Tính toán biến động so với kỳ trước
    if data_type == 'Tổng hợp':
        for col in pivot_columns + ['completion_rate']:
            pivot_data[f'{col}_prev'] = pivot_data[col].shift(1)
            pivot_data[f'{col}_change'] = pivot_data[col] - pivot_data[f'{col}_prev']
            if col != 'completion_rate':
                pivot_data[f'{col}_change_pct'] = ((pivot_data[col] / pivot_data[f'{col}_prev'] - 1) * 100).round(1)
            else:
                pivot_data[f'{col}_change_pct'] = (pivot_data[col] - pivot_data[f'{col}_prev']).round(1)
            pivot_data[f'{col}_change_pct'] = pivot_data[f'{col}_change_pct'].fillna(0)
    
    # Hiển thị bảng chính
    display_columns = group_cols + pivot_columns + ['completion_rate', 'processing_rate', 'new_rate']
    
    rename_dict = {
        'period': f'{period_type}',
        'department': 'Phòng ban',
        'tasks_assigned': 'Giao việc',
        'tasks_completed_on_time': 'Hoàn thành đúng hạn',
        'tasks_new': 'Việc mới',
        'tasks_processing': 'Đang xử lý',
        'completion_rate': 'Tỷ lệ hoàn thành (%)',
        'processing_rate': 'Tỷ lệ đang xử lý (%)',
        'new_rate': 'Tỷ lệ việc mới (%)'
    }
    
    st.markdown(f"#### 📋 Tổng hợp theo {period_type} - {data_type}")
    display_df = pivot_data[display_columns].copy()
    for col in ['completion_rate', 'processing_rate', 'new_rate']:
        if col in display_df.columns:
            display_df[col] = display_df[col].round(1)
    
    st.dataframe(display_df.rename(columns=rename_dict), use_container_width=True)
    
    # Hiển thị bảng biến động (chỉ cho tổng hợp)
    if data_type == 'Tổng hợp' and len(pivot_data) > 1:
        st.markdown(f"#### 📈 Biến động so với {period_type.lower()} trước")
        
        change_data = pivot_data[['period']].copy()
        for col in pivot_columns + ['completion_rate']:
            change_col = f'{col}_change'
            pct_col = f'{col}_change_pct'
            prev_col = f'{col}_prev'
            
            if change_col in pivot_data.columns and pct_col in pivot_data.columns:
                if col == 'completion_rate':
                    change_data[f'{col}_combined'] = pivot_data.apply(
                        lambda row: f"{row[change_col]:+.1f}%" 
                        if pd.notna(row[change_col]) and pd.notna(row[prev_col]) else "Mới", axis=1
                    )
                else:
                    change_data[f'{col}_combined'] = pivot_data.apply(
                        lambda row: f"{int(row[change_col]):+} ({row[pct_col]:+.1f}%)" 
                        if pd.notna(row[change_col]) and pd.notna(row[prev_col]) and row[prev_col] != 0 else "Mới", axis=1
                    )
        
        # Tạo bảng hiển thị cuối cùng
        final_change_columns = ['period'] + [f'{col}_combined' for col in pivot_columns + ['completion_rate'] if f'{col}_combined' in change_data.columns]
        final_rename = {'period': f'{period_type}'}
        for col in pivot_columns + ['completion_rate']:
            if f'{col}_combined' in change_data.columns:
                col_name = rename_dict.get(col, col)
                final_rename[f'{col}_combined'] = f'{col_name} (±%)'
        
        if len(final_change_columns) > 1:
            st.dataframe(
                change_data[final_change_columns].rename(columns=final_rename),
                use_container_width=True
            )
    
    # Thống kê tóm tắt
    if len(pivot_data) > 0:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_assigned = pivot_data['tasks_assigned'].sum()
            st.metric("📋 Tổng giao việc", f"{total_assigned:,.0f}")
        with col2:
            total_completed = pivot_data['tasks_completed_on_time'].sum()
            st.metric("✅ Hoàn thành", f"{total_completed:,.0f}")
        with col3:
            total_processing = pivot_data['tasks_processing'].sum()
            st.metric("🔄 Đang xử lý", f"{total_processing:,.0f}")
        with col4:
            avg_completion = pivot_data['completion_rate'].mean()
            st.metric("📊 Tỷ lệ TB", f"{avg_completion:.1f}%")

# Hàm tạo biểu đồ cho quản lý công việc
def create_task_management_charts(df_all, df_detail):
    col1, col2 = st.columns(2)
    
    with col1:
        # Sắp xếp df_all theo thời gian trước khi vẽ biểu đồ
        df_all_sorted = df_all.sort_values('datetime').reset_index(drop=True)
        
        # Tính toán cộng dồn
        df_all_sorted['cumulative_assigned'] = df_all_sorted['tasks_assigned'].cumsum()
        df_all_sorted['cumulative_completed'] = df_all_sorted['tasks_completed_on_time'].cumsum()
        df_all_sorted['cumulative_processing'] = df_all_sorted['tasks_processing'].cumsum()
        df_all_sorted['cumulative_new'] = df_all_sorted['tasks_new'].cumsum()
        
        # Biểu đồ xu hướng cộng dồn
        fig_trend = go.Figure()
        fig_trend.add_trace(go.Scatter(x=df_all_sorted['datetime'], y=df_all_sorted['cumulative_assigned'],
                                     mode='lines+markers', name='Tổng giao việc',
                                     line=dict(color='blue', width=3)))
        fig_trend.add_trace(go.Scatter(x=df_all_sorted['datetime'], y=df_all_sorted['cumulative_completed'],
                                     mode='lines+markers', name='Tổng đã hoàn thành',
                                     line=dict(color='green', width=3)))
        fig_trend.add_trace(go.Scatter(x=df_all_sorted['datetime'], y=df_all_sorted['cumulative_processing'],
                                     mode='lines+markers', name='Tổng đang xử lý',
                                     line=dict(color='orange', width=2)))
        fig_trend.add_trace(go.Scatter(x=df_all_sorted['datetime'], y=df_all_sorted['cumulative_new'],
                                     mode='lines+markers', name='Tổng việc mới',
                                     line=dict(color='red', width=2)))
        
        fig_trend.update_layout(title='📈 Xu hướng công việc cộng dồn',
                              xaxis_title="Ngày", yaxis_title="Số lượng cộng dồn")
        st.plotly_chart(fig_trend, use_container_width=True)
        
        # Tính tỷ lệ hoàn thành cộng dồn
        df_all_sorted['cumulative_completion_rate'] = (df_all_sorted['cumulative_completed'] / df_all_sorted['cumulative_assigned'] * 100).fillna(0)
        
        # Biểu đồ tỷ lệ hoàn thành cộng dồn
        fig_completion = px.line(df_all_sorted, x='datetime', y='cumulative_completion_rate',
                               title='📊 Tỷ lệ hoàn thành cộng dồn (%)',
                               markers=True)
        fig_completion.update_layout(xaxis_title="Ngày", yaxis_title="Tỷ lệ cộng dồn (%)")
        fig_completion.update_traces(line_color='purple', line_width=3)
        st.plotly_chart(fig_completion, use_container_width=True)
    
    with col2:
        # Thống kê phòng ban theo số lượng công việc
        if len(df_detail) > 0:
            dept_summary = df_detail.groupby('department').agg({
                'tasks_assigned': 'sum',
                'tasks_completed_on_time': 'sum',
                'tasks_processing': 'sum',
                'tasks_new': 'sum'
            }).reset_index()
            
            # Tính số công việc chưa hoàn thành (bao gồm đang xử lý + mới)
            dept_summary['tasks_incomplete'] = dept_summary['tasks_processing'] + dept_summary['tasks_new']
            
            # Sắp xếp theo tổng số công việc
            dept_summary = dept_summary.sort_values('tasks_assigned', ascending=True)
            
            # Biểu đồ stacked bar hàng ngang
            fig_dept = go.Figure()
            
            # Thêm cột hoàn thành (xanh)
            fig_dept.add_trace(go.Bar(
                name='Hoàn thành',
                y=dept_summary['department'],
                x=dept_summary['tasks_completed_on_time'],
                orientation='h',
                marker_color='#28a745'
            ))
            
            # Thêm cột chưa hoàn thành (đỏ)
            fig_dept.add_trace(go.Bar(
                name='Chưa hoàn thành',
                y=dept_summary['department'],
                x=dept_summary['tasks_incomplete'],
                orientation='h',
                marker_color='#dc3545'
            ))
            
            # Cấu hình layout nhỏ gọn
            fig_dept.update_layout(
                title='📊 Số lượng công việc theo phòng ban',
                xaxis_title="Số lượng",
                yaxis_title="",
                barmode='stack',
                showlegend=True,
                height=max(150, len(dept_summary) * 20),
                margin=dict(l=80, r=30, t=40, b=30)
            )
            st.plotly_chart(fig_dept, use_container_width=True)
            
            # Metrics ngắn gọn
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                total_completed_all = dept_summary['tasks_completed_on_time'].sum()
                st.metric("✅ Tổng hoàn thành", f"{total_completed_all:,}")
            with col_b:
                total_incomplete_all = dept_summary['tasks_incomplete'].sum()  
                st.metric("❌ Tổng chưa xong", f"{total_incomplete_all:,}")
            with col_c:
                avg_rate = (total_completed_all / (total_completed_all + total_incomplete_all) * 100) if (total_completed_all + total_incomplete_all) > 0 else 0
                st.metric("📊 Tỷ lệ TB", f"{avg_rate:.1f}%")
            
            # Biểu đồ phân bố trạng thái công việc
            total_completed = df_detail['tasks_completed_on_time'].sum()
            total_processing = df_detail['tasks_processing'].sum()
            total_new = df_detail['tasks_new'].sum()
            
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
                status_colors.append('#ffc107')  # Vàng
                
            if total_new > 0:
                status_data.append('Việc mới')
                status_values.append(total_new)
                status_colors.append('#dc3545')  # Đỏ
            
            if status_values:  # Chỉ vẽ nếu có dữ liệu
                fig_status = go.Figure(data=[go.Pie(
                    labels=status_data, 
                    values=status_values,
                    hole=0.4,
                    marker_colors=status_colors,
                    textinfo='label+value+percent',
                    textposition='auto'
                )])
                
                fig_status.update_layout(
                    title='📋 Phân bố trạng thái công việc',
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="middle", y=0.5)
                )
                
                st.plotly_chart(fig_status, use_container_width=True)
                
                # Thêm thống kê tổng quan
                total_all = total_completed + total_processing + total_new
                st.markdown(f"**📊 Tổng quan trạng thái:**")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("✅ Hoàn thành", f"{total_completed:,}", f"{total_completed/total_all*100:.1f}%" if total_all > 0 else "0%")
                with col_b:
                    st.metric("🔄 Đang xử lý", f"{total_processing:,}", f"{total_processing/total_all*100:.1f}%" if total_all > 0 else "0%")
                with col_c:
                    st.metric("🆕 Việc mới", f"{total_new:,}", f"{total_new/total_all*100:.1f}%" if total_all > 0 else "0%")
            else:
                st.info("📋 Không có dữ liệu trạng thái công việc")

# Hàm tạo biểu đồ cho lịch họp
def create_meeting_charts(df):
    col1, col2 = st.columns(2)
    
    with col1:
        # Biểu đồ số lượng cuộc họp theo ngày
        fig_daily = px.line(df, x='datetime', y='meeting_schedules',
                           title='📅 Số lượng cuộc họp theo ngày',
                           markers=True)
        fig_daily.update_traces(line_color='#007bff', line_width=3)
        fig_daily.update_layout(xaxis_title="Ngày", yaxis_title="Số cuộc họp")
        st.plotly_chart(fig_daily, use_container_width=True)
        
        # Biểu đồ phân bố theo ngày trong tuần
        weekday_summary = df.groupby('weekday_vi')['meeting_schedules'].sum().reindex([
            'Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật'
        ]).fillna(0)
        
        colors = ['#28a745' if day in ['Thứ 7', 'Chủ nhật'] else '#007bff' for day in weekday_summary.index]
        
        fig_weekday = px.bar(x=weekday_summary.index, y=weekday_summary.values,
                            title='📅 Phân bố cuộc họp theo ngày trong tuần',
                            color=weekday_summary.index,
                            color_discrete_sequence=colors)
        fig_weekday.update_layout(xaxis_title="Ngày trong tuần", yaxis_title="Tổng số cuộc họp", showlegend=False)
        st.plotly_chart(fig_weekday, use_container_width=True)
    
    with col2:
        # Biểu đồ mức độ bận rộn
        level_counts = df['meeting_level'].value_counts()
        level_order = ['Rất ít', 'Ít', 'Trung bình', 'Nhiều', 'Rất nhiều']
        level_counts = level_counts.reindex(level_order).fillna(0)
        
        colors_level = {'Rất ít': '#28a745', 'Ít': '#6c757d', 'Trung bình': '#ffc107', 
                       'Nhiều': '#fd7e14', 'Rất nhiều': '#dc3545'}
        
        fig_level = px.pie(values=level_counts.values, names=level_counts.index,
                          title='📊 Phân bố mức độ bận rộn',
                          color=level_counts.index,
                          color_discrete_map=colors_level,
                          hole=0.4)
        st.plotly_chart(fig_level, use_container_width=True)
        
        # Biểu đồ so sánh ngày làm việc vs cuối tuần
        day_type_summary = df.groupby('day_type')['meeting_schedules'].agg(['count', 'sum', 'mean']).round(1)
        
        fig_daytype = go.Figure()
        fig_daytype.add_trace(go.Bar(
            name='Số ngày',
            x=day_type_summary.index,
            y=day_type_summary['count'],
            marker_color='#17a2b8',
            text=day_type_summary['count'],
            textposition='inside'
        ))
        
        fig_daytype.update_layout(
            title='📋 Số ngày họp: Làm việc vs Cuối tuần',
            xaxis_title="Loại ngày",
            yaxis_title="Số ngày",
            showlegend=False
        )
        st.plotly_chart(fig_daytype, use_container_width=True)
        
        # Thống kê ngắn gọn
        st.markdown("**📊 Thống kê chi tiết:**")
        col_a, col_b = st.columns(2)
        with col_a:
            workday_avg = day_type_summary.loc['Ngày làm việc', 'mean'] if 'Ngày làm việc' in day_type_summary.index else 0
            st.metric("💼 TB Ngày LV", f"{workday_avg:.1f} cuộc")
        with col_b:
            weekend_avg = day_type_summary.loc['Cuối tuần', 'mean'] if 'Cuối tuần' in day_type_summary.index else 0
            st.metric("🏡 TB Cuối tuần", f"{weekend_avg:.1f} cuộc")

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
    st.markdown('<div class="tab-header">📊 Tổng quan Phòng Hành Chính</div>', unsafe_allow_html=True)
    
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
            st.metric("📥 Văn bản đến", f"{vb_den:,}")
        
        with col2:
            vb_di = categories_summary.get('📤 Văn bản đi', 0)
            st.metric("📤 Văn bản đi", f"{vb_di:,}")
        
        with col3:
            phong_hop = categories_summary.get('🏢 Phòng họp', 0)
            st.metric("🏢 Cuộc họp", f"{phong_hop:,}")
        
        with col4:
            hop_dong = categories_summary.get('📝 Hợp đồng', 0)
            quyet_dinh = categories_summary.get('📜 Quyết định', 0)
            st.metric("📜 QĐ + HĐ", f"{hop_dong + quyet_dinh:,}")
        
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
    
    # Upload file
    uploaded_file = st.file_uploader(
        "📁 Upload dữ liệu văn bản đến", 
        type=['json', 'csv'],
        key="incoming_docs"
    )
    
    if uploaded_file is not None:
        df = process_incoming_documents_data(uploaded_file)
        
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
    
    # Upload file
    uploaded_file_out = st.file_uploader(
        "📁 Upload dữ liệu văn bản đi", 
        type=['json', 'csv'],
        key="outgoing_docs"
    )
    
    if uploaded_file_out is not None:
        df_out = process_outgoing_documents_data(uploaded_file_out)
        
        if df_out is not None:
            # Áp dụng filter toàn cục
            df_out = apply_global_filter(df_out)
            # Thống kê tổng quan
            st.markdown("### 📊 Thống kê tổng quan văn bản đi")
            
            # Hàng 1: Thống kê chính
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if 'total_outgoing' in df_out.columns:
                    total_outgoing = df_out['total_outgoing'].sum()
                    st.metric("📄 Tổng văn bản đi", f"{total_outgoing:,}")
                else:
                    st.metric("📄 Tổng văn bản đi", "0")
            
            with col2:
                total_docs = df_out['documents'].sum()
                st.metric("📝 Văn bản phát hành", f"{total_docs:,}")
            
            with col3:
                total_contracts = df_out['contracts_total'].sum()
                st.metric("📁 Hợp đồng", f"{total_contracts:,}")
            
            with col4:
                total_decisions = df_out['decisions_total'].sum()
                st.metric("⚖️ Quyết định", f"{total_decisions:,}")
            
            with col5:
                avg_daily = df_out['total_outgoing'].mean() if 'total_outgoing' in df_out.columns else 0
                st.metric("📈 TB/ngày", f"{avg_daily:.1f}")
            
            # Hàng 2: Thống kê quy chế và quy định
            st.markdown("#### 📋 Thống kê quy chế và quy định")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_regulations = df_out['regulations_total'].sum()
                st.metric("📜 Quy định", f"{total_regulations:,}")
            
            with col2:
                total_rules = df_out['rules_total'].sum()
                st.metric("📋 Quy chế", f"{total_rules:,}")
            
            with col3:
                total_procedures = df_out['procedures_total'].sum()
                st.metric("🔄 Thủ tục", f"{total_procedures:,}")
            
            with col4:
                total_instruct = df_out['instruct_total'].sum()
                st.metric("📚 Hướng dẫn", f"{total_instruct:,}")
            
            st.markdown("---")
            
            # Pivot Table
            create_outgoing_pivot_table(df_out)
            
            st.markdown("---")
            
            # Biểu đồ
            create_outgoing_docs_charts(df_out)
            
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
        st.info("📁 Vui lòng upload file dữ liệu để xem thống kê chi tiết")

# Tab 4: Quản lý công việc
with tab4:
    st.markdown('<div class="tab-header">📋 Quản lý Công Việc</div>', unsafe_allow_html=True)
    
    # Upload file
    uploaded_file_tasks = st.file_uploader(
        "📁 Upload dữ liệu công việc", 
        type=['json', 'csv'],
        key="tasks"
    )
    
    if uploaded_file_tasks is not None:
        df_all_tasks, df_detail_tasks = process_task_management_data(uploaded_file_tasks)
        
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
                st.metric("📋 Tổng giao việc", f"{total_assigned:,}")
            
            with col2:
                total_completed = df_all_tasks_filtered['tasks_completed_on_time'].sum()
                st.metric("✅ Hoàn thành", f"{total_completed:,}")
            
            with col3:
                total_processing = df_all_tasks_filtered['tasks_processing'].sum()
                st.metric("🔄 Đang xử lý", f"{total_processing:,}")
            
            with col4:
                total_new = df_all_tasks_filtered['tasks_new'].sum()
                st.metric("🆕 Việc mới", f"{total_new:,}")
            
            with col5:
                avg_completion = df_all_tasks_filtered['completion_rate'].mean()
                st.metric("📊 Tỷ lệ hoàn thành", f"{avg_completion:.1f}%")
            
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
                
                # Top 3 phòng ban
                top_depts = dept_summary.nlargest(3, 'completion_rate')
                
                col1, col2, col3 = st.columns(3)
                for i, (idx, dept) in enumerate(top_depts.iterrows()):
                    with [col1, col2, col3][i]:
                        st.metric(f"🏆 {dept['department']}", f"{dept['completion_rate']:.1f}%", 
                                f"{dept['tasks_completed_on_time']}/{dept['tasks_assigned']} việc")
            
            st.markdown("---")
            
            # Pivot Table
            create_task_pivot_table(df_all_tasks_filtered, df_detail_tasks_filtered)
            
            st.markdown("---")
            
            # Biểu đồ
            create_task_management_charts(df_all_tasks_filtered, df_detail_tasks_filtered)
            
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
    
    uploaded_file_meetings = st.file_uploader(
        "📁 Upload dữ liệu lịch họp", 
        type=['json', 'csv'],
        key="meetings"
    )
    
    if uploaded_file_meetings is not None:
        df_meetings = process_meeting_data(uploaded_file_meetings)
        
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
            
            # Biểu đồ
            create_meeting_charts(df_meetings)
            
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
            with open('meeting_rooms_data.json', 'r', encoding='utf-8') as f:
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
    
    # Upload file hoặc load từ file có sẵn
    uploaded_file_rooms = st.file_uploader(
        "📁 Upload dữ liệu phòng họp mới", 
        type=['json', 'csv'],
        key="rooms"
    )
    
    # Load dữ liệu
    if uploaded_file_rooms is not None:
        if uploaded_file_rooms.type == "application/json":
            data = json.load(uploaded_file_rooms)
            if isinstance(data, dict) and "data" in data:
                df_rooms = pd.DataFrame(data["data"])
            else:
                df_rooms = pd.DataFrame(data)
        else:
            df_rooms = pd.read_csv(uploaded_file_rooms)
        
        # Xử lý dữ liệu upload
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
        df_rooms['cancel_rate'] = (df_rooms['register_room_cancel'] / df_rooms['register_room'] * 100).fillna(0).round(1)
        df_rooms['net_bookings'] = df_rooms['register_room'] - df_rooms['register_room_cancel']
        df_rooms['is_weekend'] = df_rooms['weekday'].isin(['Saturday', 'Sunday'])
        df_rooms['day_type'] = df_rooms['is_weekend'].map({False: 'Ngày làm việc', True: 'Cuối tuần'})
        df_rooms = apply_global_filter(df_rooms)
        
    else:
        # Load từ file có sẵn
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
        
        # Sub-tabs cho phòng họp
        subtab1, subtab2, subtab3 = st.tabs(["📈 Xu hướng", "📊 Phân tích", "🏆 Top ngày"])
        
        with subtab1:
            # Biểu đồ xu hướng
            fig_trend = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Xu hướng đăng ký phòng họp', 'Tỷ lệ hủy theo thời gian'),
                vertical_spacing=0.1
            )
            
            fig_trend.add_trace(
                go.Scatter(x=df_rooms['datetime'], y=df_rooms['register_room'],
                          mode='lines+markers', name='Đăng ký', line=dict(color='#2E86AB')),
                row=1, col=1
            )
            
            fig_trend.add_trace(
                go.Scatter(x=df_rooms['datetime'], y=df_rooms['register_room_cancel'],
                          mode='lines+markers', name='Hủy bỏ', line=dict(color='#F18F01')),
                row=1, col=1
            )
            
            fig_trend.add_trace(
                go.Scatter(x=df_rooms['datetime'], y=df_rooms['cancel_rate'],
                          mode='lines+markers', name='Tỷ lệ hủy (%)', line=dict(color='#C73E1D')),
                row=2, col=1
            )
            
            fig_trend.update_layout(height=600, hovermode='x unified')
            st.plotly_chart(fig_trend, use_container_width=True)
            
            # Thống kê nhanh
            col1, col2, col3 = st.columns(3)
            with col1:
                max_booking = df_rooms['register_room'].max()
                max_date = df_rooms[df_rooms['register_room'] == max_booking]['datetime'].iloc[0]
                st.success(f"🏆 Ngày đăng ký cao nhất\n{max_date.strftime('%d/%m/%Y')}: {max_booking} đăng ký")
            
            with col2:
                max_cancel = df_rooms['register_room_cancel'].max()
                max_cancel_date = df_rooms[df_rooms['register_room_cancel'] == max_cancel]['datetime'].iloc[0]
                st.warning(f"⚠️ Ngày hủy cao nhất\n{max_cancel_date.strftime('%d/%m/%Y')}: {max_cancel} hủy")
            
            with col3:
                max_rate = df_rooms['cancel_rate'].max()
                max_rate_date = df_rooms[df_rooms['cancel_rate'] == max_rate]['datetime'].iloc[0]
                st.info(f"📉 Tỷ lệ hủy cao nhất\n{max_rate_date.strftime('%d/%m/%Y')}: {max_rate}%")
        
        with subtab2:
            # Phân tích theo tháng
            monthly_stats = df_rooms.groupby('month_vi').agg({
                'register_room': ['sum', 'mean'],
                'register_room_cancel': ['sum', 'mean'],
                'cancel_rate': 'mean'
            }).round(2)
            monthly_stats.columns = ['Tổng đăng ký', 'TB/ngày', 'Tổng hủy', 'TB hủy/ngày', 'TB tỷ lệ hủy (%)']
            
            # Biểu đồ tháng
            fig_monthly = go.Figure()
            months = monthly_stats.index
            
            fig_monthly.add_trace(go.Bar(name='Tổng đăng ký', x=months, y=monthly_stats['Tổng đăng ký'], 
                                        marker_color='#2E86AB', yaxis='y'))
            fig_monthly.add_trace(go.Bar(name='Tổng hủy', x=months, y=monthly_stats['Tổng hủy'], 
                                        marker_color='#F18F01', yaxis='y'))
            fig_monthly.add_trace(go.Scatter(name='Tỷ lệ hủy (%)', x=months, y=monthly_stats['TB tỷ lệ hủy (%)'],
                                           mode='lines+markers', line=dict(color='#C73E1D', width=3), yaxis='y2'))
            
            fig_monthly.update_layout(
                title='Phân tích theo tháng',
                xaxis_title='Tháng',
                yaxis=dict(title='Số lượng', side='left'),
                yaxis2=dict(title='Tỷ lệ hủy (%)', side='right', overlaying='y'),
                height=400
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
            
            # Bảng thống kê
            st.dataframe(monthly_stats, use_container_width=True)
            
            # Phân tích theo ngày trong tuần
            weekday_order = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
            weekday_stats = df_rooms.groupby('weekday_vi').agg({
                'register_room': ['sum', 'mean'],
                'register_room_cancel': ['sum', 'mean']
            }).round(2)
            weekday_stats = weekday_stats.reindex(weekday_order)
            weekday_stats.columns = ['Tổng đăng ký', 'TB đăng ký', 'Tổng hủy', 'TB hủy']
            
            # Biểu đồ radar
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=weekday_stats['TB đăng ký'].values,
                theta=weekday_stats.index,
                fill='toself', name='TB đăng ký/ngày',
                line_color='#2E86AB'
            ))
            fig_radar.add_trace(go.Scatterpolar(
                r=weekday_stats['TB hủy'].values,
                theta=weekday_stats.index,
                fill='toself', name='TB hủy/ngày',
                line_color='#F18F01'
            ))
            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, weekday_stats['TB đăng ký'].max() * 1.1])),
                title='Phân tích theo ngày trong tuần', height=400
            )
            st.plotly_chart(fig_radar, use_container_width=True)
            
            st.dataframe(weekday_stats, use_container_width=True)
        
        with subtab3:
            # Top ngày có nhiều đăng ký
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### 📈 Top 10 ngày đăng ký cao nhất")
                top_bookings = df_rooms.nlargest(10, 'register_room')[['datetime', 'register_room', 'register_room_cancel', 'cancel_rate', 'weekday_vi']]
                
                for idx, row in top_bookings.iterrows():
                    st.success(f"""
                    📅 {row['datetime'].strftime('%d/%m/%Y')} ({row['weekday_vi']})
                    🏢 Đăng ký: {row['register_room']} | ❌ Hủy: {row['register_room_cancel']} | 📊 Tỷ lệ: {row['cancel_rate']}%
                    """)
            
            with col2:
                st.markdown("#### 📉 Top 10 ngày hủy cao nhất")
                top_cancels = df_rooms.nlargest(10, 'register_room_cancel')[['datetime', 'register_room', 'register_room_cancel', 'cancel_rate', 'weekday_vi']]
                
                for idx, row in top_cancels.iterrows():
                    st.warning(f"""
                    📅 {row['datetime'].strftime('%d/%m/%Y')} ({row['weekday_vi']})
                    🏢 Đăng ký: {row['register_room']} | ❌ Hủy: {row['register_room_cancel']} | 📊 Tỷ lệ: {row['cancel_rate']}%
                    """)
        
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
    <p>📊 Dashboard Phòng Hành Chính - Phiên bản 1.0</p>
    <p>🔄 Dữ liệu cập nhật từ GitHub Repository</p>
</div>
""", unsafe_allow_html=True)