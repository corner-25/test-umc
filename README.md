# 🏥 UMC Dashboard System

**Dashboard tích hợp cho Bệnh viện Đại học Y Dược TP. HCM (University Medical Center)**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url.streamlit.app)

## 🎯 Tổng quan

Hệ thống dashboard tích hợp gồm:

- 📊 **Dashboard Phòng Hành Chính**: Quản lý số liệu hoạt động, văn bản, sự kiện
- 🚗 **Dashboard Tổ Xe**: Quản lý đội xe, nhiên liệu, doanh thu, hiệu suất

## ✨ Tính năng nổi bật

### 📋 Dashboard Phòng Hành Chính
- **Pivot Table thông minh** với thứ tự ưu tiên cố định
- **Hiển thị biến động inline**: `1.234.567 (↑15%)`
- **13 danh mục** và **70+ nội dung** theo thứ tự quan trọng
- **Sparkline xu hướng** cho từng danh mục
- **Xuất báo cáo Excel** đa sheet và CSV
- **Sync tự động** với GitHub storage

### 🚗 Dashboard Tổ Xe
- **Quản lý đội xe** hành chính và cứu thương
- **Phân tích nhiên liệu** với định mức tiêu thụ
- **Theo dõi doanh thu** xe cứu thương
- **Báo cáo hiệu suất** chi tiết từng xe và tài xế
- **Phân tích quá tải** và tối ưu hóa
- **Biểu đồ trực quan** với Plotly

## 🚀 Demo trực tiếp

| Dashboard | Link | Mô tả |
|-----------|------|--------|
| 📊 Phòng Hành Chính | [Live Demo](https://your-admin-dashboard.streamlit.app) | Quản lý số liệu hoạt động |
| 🚗 Tổ Xe | [Live Demo](https://your-fleet-dashboard.streamlit.app) | Quản lý đội xe |

## 📊 Screenshots

### Dashboard Phòng Hành Chính
![Dashboard Phòng Hành Chính](assets/screenshot-admin.png)

### Dashboard Tổ Xe  
![Dashboard Tổ Xe](assets/screenshot-fleet.png)

## 🛠️ Cài đặt

### 1. Clone Repository
```bash
git clone https://github.com/corner-25/dashboard-umc.git
cd dashboard-umc
```

### 2. Cài đặt Dependencies
```bash
pip install -r requirements.txt
```

### 3. Cấu hình Secrets
Tạo file `.streamlit/secrets.toml`:
```toml
github_token = "ghp_your_token_here"
github_owner = "corner-25"
github_repo = "dashboard-umc"
```

### 4. Chạy Dashboard
```bash
# Dashboard Phòng Hành Chính
streamlit run dash_phonghc.py

# Dashboard Tổ Xe
streamlit run dashboard-6.py
```

## 📁 Cấu trúc Project

```
dashboard-umc/
├── 📊 dash_phonghc.py          # Dashboard Phòng Hành Chính
├── 🚗 dashboard-6.py           # Dashboard Tổ Xe
├── 🔧 manual_fleet_sync.py     # Sync dữ liệu tổ xe
├── 📋 requirements.txt         # Dependencies
├── 🎨 assets/                  # Logo, images
├── ⚙️ .streamlit/              # Cấu hình Streamlit
└── 📖 README.md               # Documentation
```

## 🎯 Cách sử dụng

### Dashboard Phòng Hành Chính

1. **Upload dữ liệu**: File Excel với cột Tuần, Tháng, Danh mục, Nội dung, Số liệu
2. **Chọn báo cáo**: Theo Tuần/Tháng/Quý/Năm  
3. **Lọc dữ liệu**: Thời gian và danh mục
4. **Xem kết quả**: Pivot table với biến động và sparkline
5. **Xuất báo cáo**: Excel/CSV với thứ tự ưu tiên

### Dashboard Tổ Xe

1. **Sync dữ liệu**: Tự động từ Google Sheets
2. **Chọn khoảng thời gian**: Bộ lọc ngày linh hoạt
3. **Phân tích**: Hiệu suất xe, nhiên liệu, doanh thu
4. **Theo dõi**: Cảnh báo quá tải và tối ưu hóa

## 🔧 Tính năng kỹ thuật

- **Frontend**: Streamlit với UI tùy chỉnh
- **Visualizations**: Plotly, custom CSS/HTML
- **Data Processing**: Pandas với logic phức tạp
- **Storage**: GitHub API cho sync tự động
- **Authentication**: Personal Access Token
- **Data Formats**: Excel, CSV, JSON
- **Responsive Design**: Mobile-friendly interface

## 📊 Danh mục theo thứ tự ưu tiên

### Dashboard Phòng Hành Chính

| STT | Danh mục | Nội dung chính |
|-----|----------|----------------|
| 1 | 📄 Văn bản đến | Tổng số văn bản, phân loại, xử lý đúng/trễ hạn |
| 2 | 📤 Văn bản phát hành | Văn bản đi, hợp đồng, quyết định, quy định |
| 3 | 👑 Chăm sóc khách VIP | Tiếp đón, hướng dẫn, phục vụ khách VIP |
| 4 | 🎪 Lễ tân | Hỗ trợ lễ tân cho hội nghị/hội thảo |
| 5 | 🤝 Tiếp khách trong nước | Đoàn tham quan, học tập, làm việc |
| 6 | 🎉 Sự kiện | Sự kiện hành chính, chủ trì, phối hợp |
| 7 | 💎 Đón tiếp khách VIP | Lễ tân VIP khám chữa bệnh |
| 8 | 💻 Họp trực tuyến | Chuẩn bị cuộc họp online |
| 9 | 📱 Điều hành tác nghiệp | Tin đăng ĐHTN |
| 10 | 🚗 Tổ xe | Số chuyến, nhiên liệu, km, doanh thu |
| 11 | ☎️ Tổng đài | Cuộc gọi đến, nhỡ, các nhánh |
| 12 | 📋 Hệ thống thư ký | Tuyển dụng, đào tạo, quản lý |
| 13 | 🅿️ Bãi giữ xe | Vé ngày/tháng, doanh thu, khiếu nại |

## 🚗 Modules Dashboard Tổ Xe

### 📊 Phân tích chính

- **Tổng quan hoạt động**: Chuyến xe, doanh thu, nhiên liệu
- **Hiệu suất xe**: So sánh theo từng xe và tài xế
- **Phân tích nhiên liệu**: Định mức vs thực tế, cảnh báo
- **Quá tải**: Phát hiện xe/tài xế làm việc quá mức
- **Xu hướng**: Biểu đồ thời gian với Plotly

### 🔧 Tính năng kỹ thuật

- **Auto-sync**: Kết nối Google Sheets qua API
- **Date filtering**: Bộ lọc thời gian linh hoạt
- **Multi-vehicle**: Hỗ trợ xe hành chính + cứu thương
- **Performance metrics**: KPI tự động tính toán
- **Export**: Báo cáo Excel/CSV chi tiết

## 🔐 Bảo mật

- **Secrets management**: Streamlit secrets cho tokens
- **GitHub storage**: Private repository
- **No sensitive data**: Không lưu dữ liệu nhạy cảm trong code
- **Token rotation**: Hỗ trợ thay đổi token định kỳ

## 📱 Triển khai

### Streamlit Cloud

1. **Fork repo** này về GitHub của bạn
2. **Connect** với Streamlit Cloud
3. **Add secrets** trong Settings:
   ```
   github_token = "ghp_xxxxxxxxxxxx"
   github_owner = "your-username"
   github_repo = "dashboard-umc"
   ```
4. **Deploy** tự động

### Local Development

```bash
# Development mode
streamlit run dash_phonghc.py --server.runOnSave true

# Production mode  
streamlit run dashboard-6.py --server.port 8501
```

## 🔄 Sync & Backup

### Tự động

- **GitHub storage**: Dữ liệu sync qua GitHub API
- **Version control**: Backup tự động với timestamp
- **Rollback**: Khôi phục dữ liệu từ backup
- **Multi-device**: Truy cập từ mọi thiết bị

### Thủ công

- **Upload Excel**: Giao diện upload trực tiếp
- **Export reports**: Tải báo cáo về máy
- **Data validation**: Kiểm tra tính hợp lệ tự động

## 🎨 Customization

### Themes

```toml
# .streamlit/config.toml
[theme]
primaryColor = "#1f77b4"          # UMC Blue
backgroundColor = "#ffffff"        # White
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
```

### Logo & Branding

- Thay file `assets/logo.png` 
- Cập nhật title trong code
- Tùy chỉnh CSS trong dashboard

## 🐛 Troubleshooting

### Lỗi thường gặp

1. **GitHub token hết hạn**
   ```
   ❌ GitHub error: 401
   ✅ Giải pháp: Tạo token mới trong GitHub Settings
   ```

2. **Dữ liệu không sync**
   ```
   ❌ Không load được từ GitHub
   ✅ Giải pháp: Kiểm tra repo permissions và token scope
   ```

3. **Upload file lỗi**
   ```
   ❌ File size too large
   ✅ Giải pháp: Giảm kích thước file Excel < 25MB
   ```

### Debug Mode

```python
# Bật debug trong sidebar
if st.sidebar.checkbox("🔍 Debug Mode"):
    st.write("Debug info...")
    st.write(f"Data shape: {df.shape}")
    st.write(f"Columns: {df.columns.tolist()}")
```

## 🤝 Contributing

### Quy trình đóng góp

1. **Fork** repository
2. **Create branch**: `git checkout -b feature/new-feature`
3. **Commit**: `git commit -m "Add new feature"`
4. **Push**: `git push origin feature/new-feature`
5. **Pull Request**: Mô tả chi tiết thay đổi

### Code Style

- **Python**: PEP 8 compliant
- **Comments**: Tiếng Việt cho business logic
- **Docstrings**: English cho technical functions
- **Streamlit**: Follow best practices

## 📈 Roadmap

### Q1 2025
- [ ] **Real-time sync** với database
- [ ] **Mobile app** companion
- [ ] **Advanced analytics** với ML
- [ ] **Multi-tenant** support

### Q2 2025
- [ ] **API endpoints** cho integration
- [ ] **Automated reports** qua email
- [ ] **Performance optimization**
- [ ] **Advanced visualizations**

## 📞 Hỗ trợ

### Liên hệ

- **Developer**: Dương Hữu Quang
- **Email**: [your-email@umc.edu.vn]
- **GitHub**: [@corner-25](https://github.com/corner-25)
- **Issues**: [GitHub Issues](https://github.com/corner-25/dashboard-umc/issues)

### Documentation

- **Wiki**: [GitHub Wiki](https://github.com/corner-25/dashboard-umc/wiki)
- **API Docs**: [API Documentation](https://corner-25.github.io/dashboard-umc/)
- **Video Tutorials**: [YouTube Playlist](https://youtube.com/playlist)

## 📄 License

```
MIT License

Copyright (c) 2025 UMC Dashboard System

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## 🎯 Acknowledgments

- **Bệnh viện Đại học Y Dược TP.HCM** - University Medical Center
- **Phòng Hành Chính** - Administrative Department  
- **Tổ Xe** - Fleet Management Team
- **Streamlit Community** - Amazing framework
- **Plotly Team** - Beautiful visualizations

---

<div align="center">

**🏥 Made with ❤️ for UMC by [Dương Hữu Quang](https://github.com/corner-25)**

⭐ **Star this repo if it helped you!** ⭐

</div>