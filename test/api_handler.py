"""
API Handler - Xử lý lấy dữ liệu từ API thay thế cho việc copy thủ công từ Postman
"""

import requests
import json
from datetime import datetime, date
import streamlit as st
import urllib3
import base64

# Tắt warning SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class APIHandler:
    def __init__(self, base_url=None, username=None, password=None):
        """
        Khởi tạo API Handler

        Args:
            base_url: URL gốc của API (ví dụ: https://api.example.com)
            username: Username để lấy token
            password: Password để lấy token
        """
        self.base_url = base_url or st.secrets.get("api_base_url", "")
        self.username = username or st.secrets.get("api_username", "")
        self.password = password or st.secrets.get("api_password", "")
        self.token = None
        self.token_expiry = None

        # GitHub config
        self.github_token = st.secrets.get("github_token", "")
        self.github_owner = st.secrets.get("github_owner", "")
        self.github_repo = st.secrets.get("github_repo", "")

    def get_token(self, login_endpoint="/v1/auth/token"):
        """
        Lấy token từ API

        Args:
            login_endpoint: Endpoint để lấy token (mặc định: /v1/auth/token)

        Returns:
            dict: {"success": bool, "token": str, "message": str}
        """
        try:
            url = f"{self.base_url}{login_endpoint}"

            # Payload để lấy token (điều chỉnh theo API của bạn)
            payload = {
                "userName": self.username,
                "password": self.password
            }

            response = requests.post(url, json=payload, verify=False)

            if response.status_code == 200:
                data = response.json()

                # Điều chỉnh theo cấu trúc response của API - Postman lưu vào data
                self.token = data.get("data") or data.get("token") or data.get("access_token")

                if self.token:
                    return {
                        "success": True,
                        "token": self.token,
                        "message": "✅ Lấy token thành công"
                    }
                else:
                    return {
                        "success": False,
                        "token": None,
                        "message": "❌ Không tìm thấy token trong response"
                    }
            else:
                return {
                    "success": False,
                    "token": None,
                    "message": f"❌ Lỗi {response.status_code}: {response.text}"
                }

        except Exception as e:
            return {
                "success": False,
                "token": None,
                "message": f"❌ Lỗi kết nối: {str(e)}"
            }

    def fetch_data(self, endpoint, method="GET", params=None, body=None, save_to_file=None):
        """
        Lấy dữ liệu từ API với token

        Args:
            endpoint: API endpoint (ví dụ: /api/data)
            method: HTTP method (GET, POST, PUT, DELETE)
            params: Query parameters (dict)
            body: Request body (dict)
            save_to_file: Nếu có, lưu dữ liệu vào file JSON

        Returns:
            dict: {"success": bool, "data": dict/list, "message": str}
        """
        if not self.token:
            token_result = self.get_token()
            if not token_result["success"]:
                return {
                    "success": False,
                    "data": None,
                    "message": "❌ Không có token. Vui lòng lấy token trước."
                }

        try:
            url = f"{self.base_url}{endpoint}"

            # Headers với token
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            }

            # Gọi API
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, verify=False)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=body, params=params, verify=False)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=body, params=params, verify=False)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params, verify=False)
            else:
                return {
                    "success": False,
                    "data": None,
                    "message": f"❌ Method {method} không được hỗ trợ"
                }

            if response.status_code == 200:
                data = response.json()

                # Lưu vào file nếu cần
                if save_to_file:
                    with open(save_to_file, 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)

                return {
                    "success": True,
                    "data": data,
                    "message": f"✅ Lấy dữ liệu thành công từ {endpoint}"
                }
            else:
                return {
                    "success": False,
                    "data": None,
                    "message": f"❌ Lỗi {response.status_code}: {response.text}"
                }

        except Exception as e:
            return {
                "success": False,
                "data": None,
                "message": f"❌ Lỗi: {str(e)}"
            }

    def refresh_all_data(self, endpoints_config):
        """
        Làm mới tất cả dữ liệu từ nhiều endpoints

        Args:
            endpoints_config: List of dict với format:
                [
                    {
                        "endpoint": "/api/data1",
                        "method": "GET",
                        "params": {"key": "value"},
                        "save_to": "data1.json"
                    },
                    ...
                ]

        Returns:
            dict: {"success": bool, "results": list, "message": str}
        """
        results = []

        for config in endpoints_config:
            result = self.fetch_data(
                endpoint=config.get("endpoint"),
                method=config.get("method", "GET"),
                params=config.get("params"),
                body=config.get("body"),
                save_to_file=config.get("save_to")
            )
            results.append({
                "endpoint": config.get("endpoint"),
                "success": result["success"],
                "message": result["message"]
            })

        all_success = all(r["success"] for r in results)

        return {
            "success": all_success,
            "results": results,
            "message": "✅ Hoàn thành làm mới dữ liệu" if all_success else "⚠️ Một số endpoint bị lỗi"
        }

    # ===== DASHBOARD PHC SPECIFIC APIs =====
    def get_summary_data(self, start_date, end_date, category="all"):
        """Lấy tổng hợp dữ liệu theo ngày"""
        return self.fetch_data(
            endpoint="/v1/dashboard_phc/documents/summary",
            method="POST",
            params={
                "Start_Date": start_date,
                "End_Date": end_date,
                "Category": category
            }
        )

    def get_daily_data(self, start_date, end_date, category):
        """Lấy dữ liệu theo ngày cho từng loại (incoming, outgoing, task_management, meeting_room, meeting_schedules)"""
        return self.fetch_data(
            endpoint="/v1/dashboard_phc/documents/daily",
            method="POST",
            params={
                "Start_Date": start_date,
                "End_Date": end_date,
                "Category": category
            }
        )

    def get_all_dashboard_phc_data(self, start_date, end_date, save_dir=""):
        """Lấy tất cả dữ liệu Dashboard PHC một lần"""
        results = []

        # 1. Lấy tổng hợp
        r = self.get_summary_data(start_date, end_date, "all")
        results.append({"name": "Tổng hợp", "success": r["success"], "data": r.get("data")})
        if r["success"] and save_dir:
            with open(f"{save_dir}/tonghop.json", 'w', encoding='utf-8') as f:
                json.dump(r["data"], f, ensure_ascii=False, indent=2)

        # 2. Văn bản đến
        r = self.get_daily_data(start_date, end_date, "incoming")
        results.append({"name": "Văn bản đến", "success": r["success"], "data": r.get("data")})
        if r["success"] and save_dir:
            with open(f"{save_dir}/vanbanden.json", 'w', encoding='utf-8') as f:
                json.dump(r["data"], f, ensure_ascii=False, indent=2)

        # 3. Văn bản phát hành
        r = self.get_daily_data(start_date, end_date, "outgoing")
        results.append({"name": "Văn bản phát hành", "success": r["success"], "data": r.get("data")})
        if r["success"] and save_dir:
            with open(f"{save_dir}/vanbanphathanh.json", 'w', encoding='utf-8') as f:
                json.dump(r["data"], f, ensure_ascii=False, indent=2)

        # 4. Quản lý công việc
        r = self.get_daily_data(start_date, end_date, "task_management")
        results.append({"name": "Quản lý công việc", "success": r["success"], "data": r.get("data")})
        if r["success"] and save_dir:
            with open(f"{save_dir}/congviec.json", 'w', encoding='utf-8') as f:
                json.dump(r["data"], f, ensure_ascii=False, indent=2)

        # 5. Đăng ký phòng họp
        r = self.get_daily_data(start_date, end_date, "meeting_room")
        results.append({"name": "Đăng ký phòng họp", "success": r["success"], "data": r.get("data")})
        if r["success"] and save_dir:
            with open(f"{save_dir}/phonghop.json", 'w', encoding='utf-8') as f:
                json.dump(r["data"], f, ensure_ascii=False, indent=2)

        # 6. Đăng ký lịch họp
        r = self.get_daily_data(start_date, end_date, "meeting_schedules")
        results.append({"name": "Đăng ký lịch họp", "success": r["success"], "data": r.get("data")})
        if r["success"] and save_dir:
            with open(f"{save_dir}/lichhop.json", 'w', encoding='utf-8') as f:
                json.dump(r["data"], f, ensure_ascii=False, indent=2)

        all_success = all(r["success"] for r in results)
        return {
            "success": all_success,
            "results": results,
            "message": "✅ Lấy tất cả dữ liệu thành công!" if all_success else "⚠️ Một số dữ liệu bị lỗi"
        }

    def upload_to_github(self, filename, content, commit_message="Update data"):
        """Upload file JSON lên GitHub private repo"""
        try:
            if not all([self.github_token, self.github_owner, self.github_repo]):
                return {"success": False, "message": "❌ Chưa cấu hình GitHub"}

            url = f"https://api.github.com/repos/{self.github_owner}/{self.github_repo}/contents/{filename}"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # Check if file exists to get SHA
            get_response = requests.get(url, headers=headers, verify=False)
            sha = None
            if get_response.status_code == 200:
                sha = get_response.json()["sha"]

            # Prepare content
            if isinstance(content, (dict, list)):
                content = json.dumps(content, ensure_ascii=False, indent=2)

            content_encoded = base64.b64encode(content.encode()).decode()

            # Upload
            payload = {
                "message": commit_message,
                "content": content_encoded,
                "branch": "main"
            }
            if sha:
                payload["sha"] = sha

            response = requests.put(url, headers=headers, json=payload, verify=False)

            if response.status_code in [200, 201]:
                return {"success": True, "message": f"✅ Đã upload {filename}"}
            else:
                return {"success": False, "message": f"❌ Lỗi upload {filename}: {response.text}"}

        except Exception as e:
            return {"success": False, "message": f"❌ Lỗi: {str(e)}"}

    def get_all_dashboard_phc_data_and_upload(self, start_date, end_date):
        """Lấy tất cả dữ liệu và upload lên GitHub"""
        file_map = {
            "Tổng hợp": "tonghop.json",
            "Văn bản đến": "vanbanden.json",
            "Văn bản phát hành": "vanbanphathanh.json",
            "Quản lý công việc": "congviec.json",
            "Đăng ký phòng họp": "phonghop.json",
            "Đăng ký lịch họp": "lichhop.json"
        }

        results = []

        # Lấy dữ liệu
        local_result = self.get_all_dashboard_phc_data(start_date, end_date, save_dir=".")

        # Upload lên GitHub
        for r in local_result["results"]:
            if r["success"] and r["data"]:
                filename = file_map.get(r["name"])
                if filename:
                    upload_result = self.upload_to_github(
                        filename=filename,
                        content=r["data"],
                        commit_message=f"Update {r['name']} - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    )
                    results.append({
                        "name": r["name"],
                        "local": "✅",
                        "github": "✅" if upload_result["success"] else "❌",
                        "message": upload_result["message"]
                    })
                else:
                    results.append({"name": r["name"], "local": "✅", "github": "⚠️", "message": "Không có filename map"})
            else:
                results.append({"name": r["name"], "local": "❌", "github": "-", "message": "Lỗi lấy dữ liệu"})

        all_success = all(r["github"] == "✅" for r in results if r["github"] != "-")
        return {
            "success": all_success,
            "results": results,
            "message": "✅ Hoàn thành!" if all_success else "⚠️ Một số file không upload được"
        }


# ===== STREAMLIT UI =====
def show_api_manager_ui():
    """Hiển thị giao diện quản lý API trong Streamlit"""

    st.title("🔄 API Data Manager")

    # Nút reset ở góc
    if st.button("🔄 Reset", help="Clear cache và reset lại"):
        st.session_state.api_handler = None
        st.rerun()

    st.markdown("---")

    # Khởi tạo session state
    if 'api_handler' not in st.session_state:
        st.session_state.api_handler = None

    # Section 1: Cấu hình API
    with st.expander("⚙️ Cấu hình API", expanded=True):
        col1, col2 = st.columns(2)

        with col1:
            base_url = st.text_input(
                "Base URL",
                value=st.secrets.get("api_base_url", ""),
                placeholder="https://api.example.com"
            )
            username = st.text_input(
                "Username",
                value=st.secrets.get("api_username", ""),
                placeholder="your_username"
            )

        with col2:
            password = st.text_input(
                "Password",
                value=st.secrets.get("api_password", ""),
                type="password",
                placeholder="your_password"
            )
            login_endpoint = st.text_input(
                "Login Endpoint",
                value="/v1/auth/token",
                placeholder="/v1/auth/token"
            )

        if st.button("🔐 Lấy Token", type="primary"):
            if not all([base_url, username, password]):
                st.error("❌ Vui lòng điền đầy đủ thông tin")
            else:
                # Khởi tạo APIHandler mới với cấu hình đầy đủ
                st.session_state.api_handler = APIHandler(base_url, username, password)
                result = st.session_state.api_handler.get_token(login_endpoint)

                if result["success"]:
                    st.success(result["message"])
                    st.code(f"Token: {result['token'][:50]}...", language="text")
                else:
                    st.error(result["message"])
                    st.session_state.api_handler = None

    # Section 2: Lấy tất cả dữ liệu Dashboard PHC
    if st.session_state.api_handler:
        st.markdown("---")
        st.subheader("🚀 Lấy Tất Cả Dữ Liệu Dashboard PHC")

        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Từ ngày", value=datetime(2025, 1, 1))
        with col2:
            end_date = st.date_input("Đến ngày", value=datetime(2026, 1, 1))
        with col3:
            save_to_files = st.checkbox("Lưu vào files", value=True)

        if st.button("🚀 LẤY VÀ UPLOAD GITHUB", type="primary", use_container_width=True):
            with st.spinner("Đang lấy dữ liệu và upload lên GitHub..."):
                result = st.session_state.api_handler.get_all_dashboard_phc_data_and_upload(
                    start_date=start_date.strftime("%Y-%m-%d"),
                    end_date=end_date.strftime("%Y-%m-%d")
                )

                # Hiển thị kết quả
                st.markdown("### 📊 Kết quả:")
                for r in result["results"]:
                    status_icon = "✅" if r['github'] == "✅" else ("❌" if r['github'] == "❌" else "⚠️")
                    st.write(f"{status_icon} **{r['name']}**: {r['message']}")

                if result["success"]:
                    st.balloons()
                    st.success(result["message"])
                else:
                    st.warning(result["message"])

        st.markdown("---")
        st.subheader("📥 Lấy Dữ Liệu Thủ Công")

        col1, col2, col3 = st.columns(3)

        with col1:
            endpoint = st.text_input("Endpoint", placeholder="/api/data")
            method = st.selectbox("Method", ["GET", "POST", "PUT", "DELETE"])

        with col2:
            params = st.text_area("Query Params (JSON)", placeholder='{"key": "value"}', height=100)
            body = st.text_area("Request Body (JSON)", placeholder='{"key": "value"}', height=100)

        with col3:
            save_file = st.text_input("Lưu vào file", placeholder="data.json")
            st.write("")  # Spacing

            if st.button("🚀 Lấy Dữ Liệu", type="primary"):
                try:
                    params_dict = json.loads(params) if params.strip() else None
                    body_dict = json.loads(body) if body.strip() else None

                    result = st.session_state.api_handler.fetch_data(
                        endpoint=endpoint,
                        method=method,
                        params=params_dict,
                        body=body_dict,
                        save_to_file=save_file if save_file.strip() else None
                    )

                    if result["success"]:
                        st.success(result["message"])

                        # Hiển thị preview dữ liệu
                        with st.expander("👀 Preview Dữ Liệu", expanded=True):
                            st.json(result["data"])
                    else:
                        st.error(result["message"])

                except json.JSONDecodeError:
                    st.error("❌ Lỗi: Params hoặc Body không đúng định dạng JSON")

        # Section 3: Làm mới tất cả dữ liệu
        st.markdown("---")
        st.subheader("🔄 Làm Mới Tất Cả Dữ Liệu")

        # Cấu hình endpoints (có thể lưu trong file config)
        endpoints_config = st.text_area(
            "Cấu hình Endpoints (JSON)",
            value=json.dumps([
                {
                    "endpoint": "/api/data1",
                    "method": "GET",
                    "params": {},
                    "save_to": "data1.json"
                },
                {
                    "endpoint": "/api/data2",
                    "method": "GET",
                    "params": {},
                    "save_to": "data2.json"
                }
            ], indent=2),
            height=200
        )

        if st.button("🔄 Làm Mới Tất Cả", type="secondary"):
            try:
                config_list = json.loads(endpoints_config)
                result = st.session_state.api_handler.refresh_all_data(config_list)

                # Hiển thị kết quả
                for r in result["results"]:
                    if r["success"]:
                        st.success(f"{r['endpoint']}: {r['message']}")
                    else:
                        st.error(f"{r['endpoint']}: {r['message']}")

                if result["success"]:
                    st.balloons()

            except json.JSONDecodeError:
                st.error("❌ Lỗi: Cấu hình endpoints không đúng định dạng JSON")


def show_quick_sync_button():
    """Widget nhỏ gọn để nhúng vào dashboard - chỉ hiển thị nút sync"""

    # Khởi tạo session state
    if 'api_handler_sync' not in st.session_state:
        st.session_state.api_handler_sync = None
        st.session_state.api_sync_error = None

    # Tự động khởi tạo từ secrets
    if st.session_state.api_handler_sync is None:
        try:
            # Debug: check secrets
            base_url = st.secrets.get("api_base_url", "")
            username = st.secrets.get("api_username", "")
            password = st.secrets.get("api_password", "")

            if not base_url:
                st.session_state.api_sync_error = "Thiếu api_base_url trong secrets.toml"
            else:
                handler = APIHandler(base_url, username, password)
                # Tự động lấy token
                result = handler.get_token()
                if result["success"]:
                    st.session_state.api_handler_sync = handler
                    st.session_state.api_sync_error = None
                else:
                    st.session_state.api_sync_error = result["message"]
        except Exception as e:
            st.session_state.api_sync_error = f"Lỗi: {str(e)}"

    # Hiển thị lỗi nếu có
    if st.session_state.api_sync_error:
        st.sidebar.error(f"❌ {st.session_state.api_sync_error}")
        if st.sidebar.button("🔄 Thử lại", key="api_retry"):
            st.session_state.api_handler_sync = None
            st.session_state.api_sync_error = None
            st.rerun()
        return

    start_date = st.sidebar.date_input("Từ ngày", value=datetime(2025, 1, 1), key="sync_start")
    end_date = st.sidebar.date_input("Đến ngày", value=datetime(2026, 1, 1), key="sync_end")

    if st.sidebar.button("🚀 Đồng Bộ & Upload GitHub", type="primary", use_container_width=True, key="sync_btn"):
        if st.session_state.api_handler_sync is None:
            st.sidebar.error("❌ Không thể kết nối API. Kiểm tra secrets.toml")
            return

        with st.spinner("⏳ Đang lấy dữ liệu và upload..."):
            result = st.session_state.api_handler_sync.get_all_dashboard_phc_data_and_upload(
                start_date=start_date.strftime("%Y-%m-%d"),
                end_date=end_date.strftime("%Y-%m-%d")
            )

            # Hiển thị kết quả compact
            success_count = sum(1 for r in result["results"] if r['github'] == "✅")
            total_count = len(result["results"])

            if result["success"]:
                st.sidebar.success(f"✅ Thành công! {success_count}/{total_count} files đã upload")
                st.balloons()
            else:
                st.sidebar.warning(f"⚠️ Upload được {success_count}/{total_count} files")

            # Details trong collapse
            if st.sidebar.checkbox("📋 Xem chi tiết", key="sync_details"):
                for r in result["results"]:
                    status_icon = "✅" if r['github'] == "✅" else "❌"
                    st.sidebar.write(f"{status_icon} **{r['name']}**")


if __name__ == "__main__":
    show_api_manager_ui()
