import customtkinter as ctk
import os
import json
import datetime
import requests
import xml.etree.ElementTree as ET
import webbrowser
import threading
from tkinter import messagebox, filedialog

class APIHandler:
    def __init__(self, parent_frame):
        self.parent = parent_frame
        
        # main.py의 resource_path를 활용하기 위해 import (또는 직접 구현)
        try:
            from main import resource_path
        except:
            def resource_path(relative_path, external=False):
                import sys, os
                if hasattr(sys, '_MEIPASS'): base_path = sys._MEIPASS if not external else os.path.dirname(sys.executable)
                elif hasattr(sys, 'frozen'): base_path = os.path.dirname(__file__) if not external else os.path.dirname(sys.executable)
                else: base_path = os.path.abspath(".")
                return os.path.join(base_path, relative_path)

        self.settings_file = resource_path("api_settings.txt", external=True) # 설정은 외부 저장
        self.api_list_file = resource_path("api_list.txt") # 리스트는 내부에 번들링 가능
        self.api_data = self.load_settings()
        self.api_links = self.load_api_list()
        
        self.current_page = 1
        self.items_per_page = 10
        self.fetched_data = [] # List of dicts: {"checked": bool, "id": int, "title": str, "date": str}
        
        # LH Region Mapping
        self.lh_regions = {
            "전체": "", "서울특별시": "11", "부산광역시": "26", "대구광역시": "27", "인천광역시": "28",
            "광주광역시": "29", "대전광역시": "30", "울산광역시": "31", "세종특별자치시": "36110",
            "경기도": "41", "강원도": "42", "충청북도": "43", "충청남도": "44",
            "전북특별자치도": "52", "전라남도": "46", "경상북도": "47", "경상남도": "48", "제주특별자치도": "50"
        }
        
        self.setup_ui()

    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_settings(self):
        with open(self.settings_file, "w", encoding="utf-8") as f:
            json.dump(self.api_data, f, ensure_ascii=False, indent=4)

    def load_api_list(self):
        links = {}
        if os.path.exists(self.api_list_file):
            try:
                with open(self.api_list_file, "r", encoding="utf-8") as f:
                    lines = [line.strip() for line in f if line.strip()]
                    # Iterate in pairs (Name, URL)
                    for i in range(0, len(lines) - 1, 2):
                        name = lines[i]
                        url = lines[i+1]
                        if url.startswith("http"):
                            links[name] = url
            except:
                pass
        
        # Default fallback if file is empty or missing
        if not links:
            links = {
                "부산광역시_교육/강좌 정보": "https://www.data.go.kr/data/15034069/openapi.do",
                "국가평생교육진흥원_K-MOOC_강좌정보": "https://www.data.go.kr/data/15042355/openapi.do",
                "한국관광공사_축제_행사정보": "https://www.data.go.kr/data/15101578/openapi.do",
                "LH_분양임대공고": "https://www.data.go.kr/data/15006451/openapi.do",
                "대한민국 공공서비스 정보": "https://www.data.go.kr/data/15109950/openapi.do"
            }
        return links

    def setup_ui(self):
        # Top Control Frame
        self.ctrl_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", padx=20, pady=10)

        # Selectbox
        self.api_options = list(self.api_links.keys())
        self.api_var = ctk.StringVar(value=self.api_options[0] if self.api_options else "")
        self.api_select = ctk.CTkOptionMenu(self.ctrl_frame, variable=self.api_var, values=self.api_options, command=self.on_api_change)
        self.api_select.pack(side="left", padx=5)

        # API Key Entry
        self.api_key_entry = ctk.CTkEntry(self.ctrl_frame, placeholder_text="API Key를 입력하세요", width=250)
        self.api_key_entry.pack(side="left", padx=5)
        
        # Load existing key if any
        self.update_key_entry()

        # Save/Delete Buttons
        self.btn_save = ctk.CTkButton(self.ctrl_frame, text="저장", width=60, command=self.save_api_key)
        self.btn_save.pack(side="left", padx=5)

        self.btn_delete = ctk.CTkButton(self.ctrl_frame, text="삭제", width=60, fg_color="#dc3545", hover_color="#c82333", command=self.delete_api_key)
        self.btn_delete.pack(side="left", padx=5)

        self.btn_api_list = ctk.CTkButton(self.ctrl_frame, text="api List", width=80, fg_color="#6c757d", hover_color="#5a6268", command=self.open_api_guide)
        self.btn_api_list.pack(side="left", padx=5)

        # Bottom Action Frame
        self.action_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.action_frame.pack(fill="x", padx=20, pady=5)

        self.btn_start = ctk.CTkButton(self.action_frame, text="작업 시작", width=120, command=self.start_api_work)
        self.btn_start.pack(side="left", padx=5)

        self.btn_check_down = ctk.CTkButton(self.action_frame, text="체크 다운", width=120, command=self.check_down)
        self.btn_check_down.pack(side="left", padx=5)

        # Festival Date Input (Hidden or visible based on selection)
        # Festival Date Input (Visible for Festivals)
        self.date_lbl = ctk.CTkLabel(self.action_frame, text="행사 시작일(년월일):")
        self.date_lbl.pack(side="left", padx=(15, 2))
        
        self.festival_date_entry = ctk.CTkEntry(self.action_frame, placeholder_text="예: 20260303", width=150)
        self.festival_date_entry.insert(0, datetime.datetime.now().strftime("%Y%m%d"))
        # self.festival_date_entry.pack(side="left", padx=2)

        # LH Region Select (Hidden by default)
        self.region_lbl = ctk.CTkLabel(self.action_frame, text="지역:")
        self.region_var = ctk.StringVar(value="전체")
        self.region_select = ctk.CTkOptionMenu(self.action_frame, variable=self.region_var, values=list(self.lh_regions.keys()), width=150)

        # LH Status Select (Hidden by default)
        self.status_lbl = ctk.CTkLabel(self.action_frame, text="상태:")
        self.status_var = ctk.StringVar(value="공고중")
        self.status_select = ctk.CTkOptionMenu(self.action_frame, variable=self.status_var, values=["공고중", "접수중", "접수마감", "상담요청", "정정공고중"], width=120)

        # LH Guide Label
        self.lh_guide_lbl = ctk.CTkLabel(self.parent, text="", text_color="#17a2b8")
        # Note: We'll pack it in on_api_change if needed

        # Initial visibility check
        self.on_api_change(self.api_var.get())

        # Board Frame (Header)
        self.board_header = ctk.CTkFrame(self.parent)
        self.board_header.pack(fill="x", padx=20, pady=(10, 0))
        
        headers = ["체크", "순번", "글제목", "날짜"]
        widths = [50, 60, 450, 150]
        for i, (h, w) in enumerate(zip(headers, widths)):
            lbl = ctk.CTkLabel(self.board_header, text=h, width=w, font=ctk.CTkFont(weight="bold"))
            lbl.pack(side="left", padx=2)

        # Board Content
        self.board_content = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.board_content.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Pagination Frame
        self.page_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.page_frame.pack(fill="x", padx=20, pady=10)

        # Progress Frame
        self.progress_frame = ctk.CTkFrame(self.parent, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=600)
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", padx=(0, 10), fill="x", expand=True)
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="대기 중", width=120)
        self.progress_label.pack(side="left")

    def update_progress_ui(self, current, total, text=None):
        if total <= 0: return
        val = current / total
        percent = int(val * 100)
        
        # UI update in a thread-safe way
        def update_val():
            self.progress_bar.set(val)
            if text:
                self.progress_label.configure(text=text)
            else:
                self.progress_label.configure(text=f"진행 중: {percent}%")
                
        self.parent.after(0, update_val)

    def on_api_change(self, choice):
        self.update_key_entry()
        if choice == "한국관광공사_축제_행사정보":
            self.date_lbl.pack(side="left", padx=(15, 2))
            self.festival_date_entry.pack(side="left", padx=2)
            self.region_lbl.pack_forget()
            self.region_select.pack_forget()
        elif choice == "LH_분양임대공고":
            self.region_lbl.pack(side="left", padx=(15, 2))
            self.region_select.pack(side="left", padx=2)
            self.status_lbl.pack(side="left", padx=(15, 2))
            self.status_select.pack(side="left", padx=2)
            
            # Show guide text
            today = datetime.datetime.now()
            start_date = today - datetime.timedelta(days=90)
            guide_text = f"* 해당데이터는 오늘기준 ({today.strftime('%Y.%m.%d')}) -90일 ({start_date.strftime('%Y.%m.%d')})의 데이터를 볼 수 있습니다."
            self.lh_guide_lbl.configure(text=guide_text)
            self.lh_guide_lbl.pack(after=self.action_frame, pady=5)
            
            self.date_lbl.pack_forget()
            self.festival_date_entry.pack_forget()
        else:
            self.date_lbl.pack_forget()
            self.festival_date_entry.pack_forget()
            self.region_lbl.pack_forget()
            self.region_select.pack_forget()
            self.status_lbl.pack_forget()
            self.status_select.pack_forget()
            self.lh_guide_lbl.pack_forget()
        
        # Ensure progress frame or other elements stay at the bottom if needed?
        # Actually they are in separate main frame packs.

    def update_key_entry(self):
        current_api = self.api_var.get()
        self.api_key_entry.delete(0, 'end')
        if current_api in self.api_data:
            self.api_key_entry.insert(0, self.api_data[current_api])

    def save_api_key(self):
        current_api = self.api_var.get()
        key = self.api_key_entry.get().strip()
        if not key:
            messagebox.showwarning("경고", "API Key를 입력해주세요.")
            return
        self.api_data[current_api] = key
        self.save_settings()
        messagebox.showinfo("성공", f"{current_api}의 API Key가 저장되었습니다.")

    def delete_api_key(self):
        current_api = self.api_var.get()
        if current_api in self.api_data:
            del self.api_data[current_api]
            self.save_settings()
            self.api_key_entry.delete(0, 'end')
            messagebox.showinfo("성공", f"{current_api}의 API Key가 삭제되었습니다.")

    def open_api_guide(self):
        if os.path.exists(self.api_list_file):
            os.startfile(self.api_list_file)
        else:
            messagebox.showwarning("경고", "api_list.txt 파일을 찾을 수 없습니다.")

    def start_api_work(self):
        # Hide LH guide if visible
        if hasattr(self, "lh_guide_lbl"):
            self.lh_guide_lbl.pack_forget()

        api_name = self.api_var.get()
        api_key = self.api_key_entry.get().strip()
        
        if not api_key:
            messagebox.showwarning("경고", "API Key가 필요합니다.")
            return

        self.fetched_data = []
        if hasattr(self, "master_cb_var"):
            self.master_cb_var.set(False)
            
        try:
            self.fetch_data_from_api(api_name, api_key)
        except Exception as e:
            messagebox.showerror("오류", f"데이터를 가져오는 중 오류가 발생했습니다:\n{e}")
            return
        
        self.current_page = 1
        self.render_board()

    def fetch_data_from_api(self, name, key):
        endpoints = {
            "울산광역시_강좌정보": "https://apis.data.go.kr/6310000/ulsanyesedu/getUlsaneduList",
            "부산광역시_교육/강좌 정보": "https://apis.data.go.kr/6260000/BusanCrsTrnngInfoService/getCrsTrnngInfo",
            "국가평생교육진흥원_K-MOOC_강좌정보": "https://apis.data.go.kr/B552881/kmooc_v2_0/courseList_v2_0",
            "한국관광공사_반려동물_동반여행": "https://apis.data.go.kr/B551011/KorService2/detailPetTour2",
            "한국관광공사_축제_행사정보": "https://apis.data.go.kr/B551011/KorService2/searchFestival2",
            "인천공항_일별승객예상도": "https://apis.data.go.kr/B551177/passgrAnncmt/getPassgrAnncmt",
            "LH_분양임대공고": "http://apis.data.go.kr/B552555/lhLeaseNoticeInfo1/lhLeaseNoticeInfo1",
            "대한민국 공공서비스 정보": "https://api.odcloud.kr/api/gov24/v3/serviceList"
        }

        import urllib.parse
        
        url = endpoints.get(name)
        if not url:
            raise Exception("정의되지 않은 API입니다.")

        params = {
            "numOfRows": 100,
            "pageNo": 1,
            "_type": "json"
        }

        # Standard Data APIs (api.data.go.kr) are often sensitive to key encoding.
        # Use manual concatenation to ensure the serviceKey is passed exactly as in the UI.
        if "api.data.go.kr" in url and "apis." not in url:
            import urllib.parse
            p_copy = params.copy()
            if "_type" in p_copy: del p_copy["_type"]
            
            if "_type" in p_copy: del p_copy["_type"]
            
            query = urllib.parse.urlencode(p_copy)
            # Append the key literally to the URL
            url = f"{url}?{query}&serviceKey={key}"
            params = {} # Clear params dict
        else:
            decoded_key = urllib.parse.unquote(key)
            params["serviceKey"] = decoded_key

        if name == "인천공항_일별승객예상도":
            params["type"] = "json"
            if "_type" in params: del params["_type"]
        elif name == "대한민국 공공서비스 정보":
            params["page"] = params.pop("pageNo")
            params["perPage"] = params.pop("numOfRows")
            # Clear _type/returnType/type as ODCloud can be picky
            if "_type" in params: del params["_type"]
        elif "한국관광공사" in name:
            params["MobileOS"] = "ETC"
            params["MobileApp"] = "MatoBlogHelper"
            # _type is already json by default
            if name == "한국관광공사_축제_행사정보":
                # Use value from entry field
                date_input = self.festival_date_entry.get().strip()
                if len(date_input) == 8 and date_input.isdigit():
                    params["eventStartDate"] = date_input
                else:
                    # Fallback or warning
                    params["eventStartDate"] = datetime.datetime.now().strftime("%Y%m%d")
        elif "K-MOOC" in name:
            params["Page"] = params.pop("pageNo")
            params["Size"] = params.pop("numOfRows")
            params["ServiceKey"] = params.pop("serviceKey") # Now it exists
        elif name == "LH_분양임대공고":
            params["PG_SZ"] = params.pop("numOfRows")
            params["PAGE"] = params.pop("pageNo")
            # Filter Status
            params["PAN_SS"] = self.status_var.get()
            
            # Date Range (90 days)
            today = datetime.datetime.now()
            start_dt = today - datetime.timedelta(days=90)
            params["PAN_ST_DT"] = start_dt.strftime("%Y%m%d")
            params["PAN_ED_DT"] = today.strftime("%Y%m%d")
            
            # Region Filter
            selected_region = self.region_var.get()
            region_code = self.lh_regions.get(selected_region, "")
            if region_code:
                params["CNP_CD"] = region_code
        
        print(f"Requesting: {url} with params {params}") # Debug log
        response = requests.get(url, params=params, timeout=15)
        
        if response.status_code != 200:
            error_msg = f"HTTP 오류: {response.status_code}"
            if response.status_code == 403:
                error_msg += " (403 Forbidden: API 키 권한이 없거나 활성화되지 않았습니다. 한국관광공사는 활용신청 10분 후 사용 가능합니다.)"
            elif response.status_code == 404:
                error_msg += " (404 Not Found: API 엔드포인트 세부 주소가 올바르지 않습니다.)"
            elif response.status_code == 401:
                error_msg += " (401 Unauthorized: API 키가 올바르지 않거나 등록되지 않았습니다.)"
            raise Exception(error_msg)

        try:
            data = response.json()
            # Check for API-level error in JSON
            if isinstance(data, dict):
                header = data.get("response", {}).get("header", {})
                res_code = header.get("resultCode")
                if res_code and res_code not in ["00", "0000", "OK"]:
                    res_msg = header.get("resultMsg", "알 수 없는 API 에러")
                    raise Exception(f"API 에러 ({res_code}): {res_msg}")
            elif isinstance(data, list) and name == "LH_분양임대공고":
                if len(data) > 1:
                    header = data[1].get("resHeader", [{}])[0]
                    ss_code = header.get("SS_CODE")
                    if ss_code and ss_code != "Y":
                        raise Exception(f"LH API 에러: {ss_code}")
        except json.JSONDecodeError:
            try:
                root = ET.fromstring(response.content)
                # Check for API-level error in XML
                msg_header = root.find(".//cmmMsgHeader")
                if msg_header is not None:
                    err_msg = msg_header.findtext("errMsg") or "API 에러"
                    err_code = msg_header.findtext("returnReasonCode") or ""
                    raise Exception(f"API 에러 ({err_code}): {err_msg}")
                
                self.parse_xml_data(name, root)
                return
            except Exception as e:
                if "API 에러" in str(e): raise e
                raise Exception("JSON 및 XML 파싱 실패. API 키가 유효하지 않거나 서버 오류일 수 있습니다.")
        except Exception as e:
            if "API 에러" in str(e): raise e
            raise e

        self.parse_json_data(name, data)

    def parse_json_data(self, name, data):
        items = []
        try:
            if isinstance(data, list) and name != "LH_분양임대공고":
                items = data
            elif name == "울산광역시_강좌정보":
                items = data.get("response", {}).get("body", {}).get("items", [])
            elif name == "부산광역시_교육/강좌 정보":
                items = data.get("getCrsTrnngInfo", {}).get("item", [])
                if not items: # Fallback for different response structure
                    items = data.get("response", {}).get("body", {}).get("items", [])
            elif name == "국가평생교육진흥원_K-MOOC_강좌정보":
                items = data.get("items", [])
                if not items:
                    items = data.get("results", [])
                if not items:
                    items = data.get("response", {}).get("body", {}).get("items", [])
            elif "한국관광공사" in name:
                # Handle nested structure: response -> body -> items -> item
                body = data.get("response", {}).get("body", {})
                if isinstance(body, dict):
                    items_wrapper = body.get("items", {})
                    if isinstance(items_wrapper, dict):
                        items = items_wrapper.get("item", [])
                    elif isinstance(items_wrapper, str) and items_wrapper == "":
                        items = []
                    else:
                        items = items_wrapper
                else:
                    items = []
            elif name == "인천공항_일별승객예상도":
                items = data.get("response", {}).get("body", {}).get("items", [])
            elif name == "LH_분양임대공고":
                # LH API returns a list [{}, {dsList: [...]}]
                if isinstance(data, list) and len(data) > 1:
                    items = data[1].get("dsList", [])
                else:
                    items = []
            elif name == "전국주차장정보표준":
                # Handle standard tn_pubr structure which might have items: { item: [...] } or items: [...]
                body = data.get("response", {}).get("body", {})
                items_obj = body.get("items", [])
                if isinstance(items_obj, dict):
                    items = items_obj.get("item", [])
                else:
                    items = items_obj
            elif name == "무인민원발급기정보조회":
                items = data.get("ManlessCivilAppealIssue", [{}])[1].get("row", [])
                if not items:
                    # Alternative structure
                    body = data.get("response", {}).get("body", {})
                    items = body.get("items", {}).get("item", [])
            elif name == "대한민국 공공서비스 정보":
                items = data.get("data", [])
        except Exception as e:
            print(f"JSON Parsing Error for {name}: {e}")
            items = []

        if not isinstance(items, list):
            items = [items]

        for i, item in enumerate(items):
            title = "제목 없음"
            date = "날짜 없음"
            
            # Key Mapping based on API
            if name == "울산광역시_강좌정보":
                title = item.get("courseName") or item.get("강좌명") or item.get("name") or "제목 없음"
                date = item.get("courseStartDate") or item.get("beginDate") or "날짜 없음"
            elif name == "부산광역시_교육/강좌 정보":
                title = item.get("title") or item.get("강좌명") or item.get("crsNm") or item.get("resvNm") or "제목 없음"
                date = item.get("beginDate") or item.get("operStartDt") or item.get("date") or "날짜 없음"
            elif "K-MOOC" in name:
                title = item.get("name") or item.get("title") or "제목 없음"
                
                def ts_to_date(ts):
                    if not ts: return ""
                    try:
                        import datetime
                        return datetime.datetime.fromtimestamp(int(ts)).strftime('%y.%m.%d')
                    except: return str(ts)

                e_start = ts_to_date(item.get("enrollment_start"))
                e_end = ts_to_date(item.get("enrollment_end"))
                s_start = ts_to_date(item.get("study_start"))
                s_end = ts_to_date(item.get("study_end"))
                
                item["enroll_start"] = e_start
                item["enroll_end"] = e_end
                item["study_start"] = s_start
                item["study_end"] = s_end
                
                date = e_start if e_start else "날짜 없음"
            elif "한국관광공사" in name:
                # detailPetTour2 fields: acmpyTypeCd, acmpyPsblCpam, petTursmInfo, etcAcmpyInfo
                # searchFestival2 fields: title, eventstartdate, eventenddate
                title = item.get("title") or item.get("acmpyPsblCpam") or item.get("acmpyTypeCd") or item.get("petTursmInfo") or item.get("etcAcmpyInfo") or item.get("contentid") or "제목 없음"
                # For long text fields, truncate for the board
                if len(title) > 60: title = title[:57] + "..."
                
                # Check for multiple date fields (Prioritize eventstartdate for festivals)
                start_date = item.get("eventstartdate")
                end_date = item.get("eventenddate")
                
                if name == "한국관광공사_축제_행사정보" and start_date and end_date:
                    raw_start = str(start_date)[:8]
                    raw_end = str(end_date)[:8]
                    if len(raw_start) == 8 and raw_start.isdigit(): 
                        item["start_date"] = f"{raw_start[:4]}-{raw_start[4:6]}-{raw_start[6:8]}"
                    else: item["start_date"] = raw_start
                    
                    if len(raw_end) == 8 and raw_end.isdigit(): 
                        item["end_date"] = f"{raw_end[:4]}-{raw_end[4:6]}-{raw_end[6:8]}"
                    else: item["end_date"] = raw_end
                    date = item["start_date"] # Fallback for unified logic
                else:
                    date_val = start_date or end_date or item.get("createdtime") or item.get("modifiedtime")
                    if date_val:
                        raw_date = str(date_val)[:8]
                        if len(raw_date) == 8 and raw_date.isdigit(): 
                            date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
                        else: 
                            date = raw_date
                    else:
                        date = "날짜 없음"
            elif name == "인천공항_일별승객예상도":
                area = item.get("iatatitle") or item.get("terminal") or item.get("terminalid") or "공항"
                time = item.get("time") or ""
                title = f"{area} 예상 승객 ({time}시)"
                date = item.get("tdate") or item.get("regist_dt") or "날짜 없음"
            elif name == "LH_분양임대공고":
                title = item.get("PAN_NM") or "제목 없음"
                if len(title) > 35: title = title[:32] + "..."
                
                date = item.get("PAN_NT_ST_DT") or "날짜 없음"
                
                region = item.get("CNP_CD_NM") or ""
                if len(region) > 12: region = region[:10] + "..."
                
                status = item.get("PAN_SS") or ""
                if len(status) > 10: status = status[:8] + "..."
                
                item["CNP_CD_NM"] = region
                item["PAN_SS"] = status
            elif name == "전국주차장정보표준":
                title = item.get("prkplceNm") or "주차장명 없음"
                date = item.get("referenceDate") or "날짜 없음"
            elif name == "무인민원발급기정보조회":
                place = item.get("ADRES_CN") or item.get("INSTL_LCTN_NM") or "무인민원발급기"
                region = item.get("CTPV_NM") or item.get("SGG_NM") or ""
                title = f"{region} {place}"
                date = item.get("LAST_MDFCN_PNT") or "날짜 없음"
                if len(date) >= 8: date = f"{date[:4]}-{date[4:6]}-{date[6:8]}"
            elif name == "대한민국 공공서비스 정보":
                raw_title = item.get("서비스명") or "서비스명 없음"
                title = (raw_title[:27] + "...") if len(raw_title) > 30 else raw_title
                
                reg = item.get("등록일시", "")[:10]
                mod = item.get("수정일시", "")[:10]
                end = item.get("신청기한", "")
                if not mod: mod = reg
                
                # Format: 수정:2024-03-19 (기한:상시)
                date = f"수정:{mod} (기한:{end})"
                # If too long, the Treeview normally truncates anyway, but let's keep it somewhat clean

            # Final check/cleanup
            if not title or title == "None": title = "제목 없음"
            if not date or date == "None": date = "날짜 없음"

            self.fetched_data.append({
                "checked": False,
                "id": i + 1,
                "title": title,
                "date": date,
                "enroll_start": item.get("enroll_start", ""),
                "enroll_end": item.get("enroll_end", ""),
                "study_start": item.get("study_start", ""),
                "study_end": item.get("study_end", ""),
                "raw": item
            })

    def parse_xml_data(self, name, root):
        if name == "울산광역시_강좌정보":
            items = root.findall(".//list")
        else:
            items = root.findall(".//item")
            if not items:
                items = root.findall(".//row")
            if not items and name == "전국주차장정보표준":
                items = root.findall(".//record") # Some standard APIs use <record>

        for i, item in enumerate(items):
            title = "제목 없음"
            date = "날짜 없음"
            target_raw = ""
            inst = ""
            start_date = ""
            end_date = ""
            
            # Simple heuristic mapping for XML
            for child in item:
                tag = child.tag.lower()
                text = (child.text or "").strip()
                if not text: continue

                if any(k in tag for k in ["name", "title", "subject", "crsnm", "resvnm", "강좌명", "lname", "lctrenm"]):
                    if title == "제목 없음" or tag in ["lname", "lctrenm"]: title = text
                
                # Busan specific tags
                if tag == "resvegroupnm": inst = text
                if tag == "reqstbegindttm": start_date = text[:10]
                if tag == "reqstenddttm": end_date = text[:10]
                
                if any(k in tag for k in ["date", "time", "day", "begin", "start", "dt", "tdate", "regist_dt", "lstart", "rstart", "lctrebegindttm"]):
                    if date == "날짜 없음": 
                        date = text
                    # Override for specific tags with priority and formatting
                    if name == "울산광역시_강좌정보":
                        if tag == "rstart":
                            date = text[:10]
                        elif tag == "lstart" and date == "날짜 없음":
                            date = text
                    elif name == "부산광역시_교육/강좌 정보":
                        if tag == "lctrebegindttm":
                            date = text[:10]

                if tag == "target":
                    target_raw = text

            # Target decoding for Ulsan
            target_map = {
                "I": "유아/어린이", "Y": "청소년", "A": "성인", "W": "주부", 
                "S": "노인", "H": "장애인", "F": "여성", "D": "성인(커플)"
            }
            target_decoded = target_map.get(target_raw.strip().upper(), target_raw)

            self.fetched_data.append({
                "checked": False,
                "id": i + 1,
                "title": title,
                "date": date,
                "target": target_decoded,
                "inst": inst,
                "start_date": start_date,
                "end_date": end_date,
                "raw": ET.tostring(item, encoding='unicode')
            })

    def render_board(self):
        # Setup Header based on API
        api_name = self.api_var.get()
        is_festival = api_name == "한국관광공사_축제_행사정보"
        
        for widget in self.board_content.winfo_children():
            widget.destroy()
        for widget in self.page_frame.winfo_children():
            widget.destroy()
            
        if is_festival:
            headers = ["", "순번", "글제목", "시작일", "종료일"]
            widths = [50, 60, 420, 110, 110]
        elif api_name == "부산광역시_교육/강좌 정보":
            headers = ["", "순번", "글제목", "운영기관", "신청시작", "신청마감"]
            widths = [50, 60, 300, 150, 120, 120]
        elif api_name == "울산광역시_강좌정보":
            headers = ["", "순번", "글제목", "대상", "날짜"]
            widths = [50, 60, 350, 100, 150]
        elif api_name == "국가평생교육진흥원_K-MOOC_강좌정보":
            headers = ["", "순번", "글제목", "신청시작", "신청마감"]
            widths = [50, 60, 420, 120, 120]
        elif api_name == "LH_분양임대공고":
            headers = ["", "순번", "글제목", "지역", "상태", "공고일"]
            widths = [30, 40, 450, 120, 80, 130]
        elif api_name == "대한민국 공공서비스 정보":
            headers = ["", "순번", "글제목", "등록일", "수정일", "마감기한"]
            widths = [30, 40, 300, 100, 100, 180]
        else:
            headers = ["", "순번", "글제목", "날짜"]
            widths = [50, 60, 450, 150]

        # Only recreate header if needed or update master checkbox state
        current_master_val = getattr(self, "master_cb_var", None)
        master_val = current_master_val.get() if current_master_val else False

        for widget in self.board_header.winfo_children():
            widget.destroy()

        for i, (h, w) in enumerate(zip(headers, widths)):
            if i == 0: # Checkbox column
                self.master_cb_var = ctk.BooleanVar(value=master_val)
                lbl = ctk.CTkCheckBox(self.board_header, text="", variable=self.master_cb_var, width=w, command=self.toggle_all_check)
            else:
                lbl = ctk.CTkLabel(self.board_header, text=h, width=w, font=ctk.CTkFont(weight="bold"))
            lbl.pack(side="left", padx=2)

        if not self.fetched_data:
            ctk.CTkLabel(self.board_content, text="표시할 데이터가 없습니다.").pack(pady=20)
            return

        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.fetched_data[start_idx:end_idx]

        for item in page_items:
            row = ctk.CTkFrame(self.board_content, fg_color="transparent")
            row.pack(fill="x", pady=2)

            cb_var = ctk.BooleanVar(value=item["checked"])
            cb = ctk.CTkCheckBox(row, text="", variable=cb_var, width=widths[0], command=lambda i=item, v=cb_var: self.update_check_status(i, v))
            cb.pack(side="left", padx=2)

            if is_festival:
                ctk.CTkLabel(row, text=str(item["id"]), width=widths[1]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["title"], width=widths[2], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["raw"].get("start_date", "날짜 없음") if isinstance(item["raw"], dict) else item["date"], width=widths[3]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["raw"].get("end_date", "날짜 없음") if isinstance(item["raw"], dict) else "날짜 없음", width=widths[4]).pack(side="left", padx=2)
            elif api_name == "부산광역시_교육/강좌 정보":
                ctk.CTkLabel(row, text=str(item["id"]), width=widths[1]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["title"], width=widths[2], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item.get("inst", "정보 없음"), width=widths[3], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item.get("start_date", "날짜 없음"), width=widths[4]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item.get("end_date", "날짜 없음"), width=widths[5]).pack(side="left", padx=2)
            elif api_name == "울산광역시_강좌정보":
                ctk.CTkLabel(row, text=str(item["id"]), width=widths[1]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["title"], width=widths[2], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item.get("target", "정보 없음"), width=widths[3]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["date"], width=widths[4]).pack(side="left", padx=2)
            elif api_name == "국가평생교육진흥원_K-MOOC_강좌정보":
                ctk.CTkLabel(row, text=str(item["id"]), width=widths[1]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["title"], width=widths[2], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item.get("enroll_start", ""), width=widths[3]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item.get("enroll_end", ""), width=widths[4]).pack(side="left", padx=2)
            elif api_name == "LH_분양임대공고":
                ctk.CTkLabel(row, text=str(item["id"]), width=widths[1]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["title"], width=widths[2], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["raw"].get("CNP_CD_NM", ""), width=widths[3]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["raw"].get("PAN_SS", ""), width=widths[4]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["date"], width=widths[5]).pack(side="left", padx=2)
            elif api_name == "대한민국 공공서비스 정보":
                ctk.CTkLabel(row, text=str(item["id"]), width=widths[1]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["title"], width=widths[2], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["raw"].get("등록일시", "")[:10], width=widths[3]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["raw"].get("수정일시", "")[:10], width=widths[4]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["raw"].get("신청기한", ""), width=widths[5], anchor="w").pack(side="left", padx=2)
            else:
                ctk.CTkLabel(row, text=str(item["id"]), width=widths[1]).pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["title"], width=widths[2], anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row, text=item["date"], width=widths[3]).pack(side="left", padx=2)

        total_pages = (len(self.fetched_data) + self.items_per_page - 1) // self.items_per_page
        if total_pages > 1:
            for p in range(1, min(total_pages + 1, 15)): 
                btn = ctk.CTkButton(self.page_frame, text=str(p), width=30, 
                                    fg_color="transparent" if p != self.current_page else None,
                                    command=lambda page=p: self.go_to_page(page))
                btn.pack(side="left", padx=2)

    def update_check_status(self, item, var):
        item["checked"] = var.get()

    def toggle_all_check(self):
        is_checked = self.master_cb_var.get()
        start_idx = (self.current_page - 1) * self.items_per_page
        end_idx = start_idx + self.items_per_page
        page_items = self.fetched_data[start_idx:end_idx]
        
        for item in page_items:
            item["checked"] = is_checked
        
        self.render_board()

    def go_to_page(self, page):
        self.current_page = page
        self.render_board()

    def check_down(self):
        selected_items = [item for item in self.fetched_data if item["checked"]]
        if not selected_items:
            messagebox.showwarning("경고", "다운로드할 항목을 선택해주세요.")
            return

        base_dir = filedialog.askdirectory(title="저장할 디렉토리를 지정하세요")
        if not base_dir:
            return

        api_name = self.api_var.get()
        if api_name == "한국관광공사_축제_행사정보":
            target_func = self.download_festival_details
        elif api_name == "울산광역시_강좌정보":
            target_func = self.download_ulsan_details
        elif api_name == "부산광역시_교육/강좌 정보":
            target_func = self.download_busan_details
        elif api_name == "국가평생교육진흥원_K-MOOC_강좌정보":
            target_func = self.download_kmooc_details
        elif api_name == "LH_분양임대공고":
            target_func = self.download_lh_details
        elif api_name == "대한민국 공공서비스 정보":
            target_func = self.download_gov_details
        else:
            target_func = self.download_generic
            
        # Run download in a separate thread to keep UI responsive
        download_thread = threading.Thread(target=target_func, args=(base_dir, selected_items), daemon=True)
        download_thread.start()

    def download_generic(self, base_dir, selected_items):
        api_dir = os.path.join(base_dir, "api")
        if not os.path.exists(api_dir):
            os.makedirs(api_dir)

        count = 0
        total = len(selected_items)
        for i, item in enumerate(selected_items):
            self.update_progress_ui(i, total)
            safe_title = "".join([c for c in item['title'] if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
            if not safe_title: safe_title = f"item_{item['id']}"
            
            # Create sub-directory based on title
            item_dir = os.path.join(api_dir, safe_title)
            if not os.path.exists(item_dir):
                os.makedirs(item_dir, exist_ok=True)
            
            file_path = os.path.join(item_dir, f"{safe_title}.txt")
            
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"제목: {item['title']}\n날짜: {item['date']}\n\n[데이터 원본]\n")
                    f.write(json.dumps(item['raw'], ensure_ascii=False, indent=4) if isinstance(item['raw'], dict) else str(item['raw']))
                count += 1
            except Exception as e:
                print(f"Error saving {item['title']}: {e}")

        self.update_progress_ui(total, total, "100% 완료")
        self.parent.after(0, lambda: messagebox.showinfo("완료", f"{count}개의 파일이 '{api_dir}' 폴더에 저장되었습니다."))

    def download_festival_details(self, base_dir, selected_items):
        import urllib.parse
        import re
        
        # Ensure main 'api' folder exists
        main_api_dir = os.path.join(base_dir, "api")
        if not os.path.exists(main_api_dir):
            os.makedirs(main_api_dir)
            
        api_dir = os.path.join(main_api_dir, "축제_행사정보")
        if not os.path.exists(api_dir):
            os.makedirs(api_dir)

        api_key = self.api_key_entry.get().strip()
        decoded_key = urllib.parse.unquote(api_key)
        detail_url = "https://apis.data.go.kr/B551011/KorService2/detailCommon2"
        
        count = 0
        total = len(selected_items)
        for i, entry in enumerate(selected_items):
            self.update_progress_ui(i, total)
            # contentid extraction
            raw_item = entry.get("raw", {})
            content_id = raw_item.get("contentid")
            if not content_id:
                print(f"Skipping {entry['title']}: No contentid found.")
                continue

            params = {
                "serviceKey": decoded_key,
                "MobileOS": "ETC",
                "MobileApp": "MatoBlogHelper",
                "_type": "json",
                "contentId": content_id
            }

            try:
                response = requests.get(detail_url, params=params, timeout=10)
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")
                
                data = response.json()
                item_list = data.get("response", {}).get("body", {}).get("items", {}).get("item", [])
                if not item_list:
                    continue
                item = item_list[0] if isinstance(item_list, list) else item_list

                title = item.get("title", entry["title"])
                addr1 = item.get("addr1", "")
                addr2 = item.get("addr2", "")
                tel = item.get("tel", "")
                homepage = item.get("homepage", "")
                overview = item.get("overview", "")
                
                # Image URLs
                img_urls = []
                if item.get("firstimage"): img_urls.append(item.get("firstimage"))
                if item.get("firstimage2"): img_urls.append(item.get("firstimage2"))

                # Simple HTML tag removal for homepage/overview
                def clean_html(text):
                    if not text: return ""
                    # Remove all HTML tags and replace <br> with newline
                    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
                    text = re.sub(r'<[^>]+>', '', text)
                    # Unescape HTML entities if any (like &amp; &nbsp;)
                    import html
                    text = html.unescape(text)
                    return text.strip()

                homepage_clean = clean_html(homepage)
                overview_clean = clean_html(overview)

                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                if not safe_title: safe_title = f"festival_{content_id}"
                
                # Save Text
                file_path = os.path.join(api_dir, f"{safe_title}.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"축제명: {title}\n")
                    address = f"{addr1} {addr2}".strip()
                    f.write(f"주소: {address}\n")
                    f.write(f"전화번호: {tel}\n")
                    f.write(f"홈페이지: {homepage_clean}\n")
                    f.write(f"\n[상세 개요]\n{overview_clean}\n")
                
                # Download Images
                for idx, img_url in enumerate(img_urls, 1):
                    try:
                        img_res = requests.get(img_url, timeout=10)
                        if img_res.status_code == 200:
                            img_ext = ".jpg"
                            if ".png" in img_url.lower(): img_ext = ".png"
                            img_path = os.path.join(api_dir, f"{safe_title}_{idx}{img_ext}")
                            with open(img_path, "wb") as f_img:
                                f_img.write(img_res.content)
                    except Exception as e:
                        print(f"Error downloading image {img_url}: {e}")

                count += 1
            except Exception as e:
                print(f"Error fetching/saving detail for {entry['title']}: {e}")

        self.update_progress_ui(total, total, "100% 완료")
        self.parent.after(0, lambda: messagebox.showinfo("완료", f"{count}개의 축제 상세 정보 및 이미지가 '{api_dir}' 폴더에 저장되었습니다."))

    def download_ulsan_details(self, base_dir, selected_items):
        import urllib.parse
        
        main_api_dir = os.path.join(base_dir, "api")
        if not os.path.exists(main_api_dir):
            os.makedirs(main_api_dir, exist_ok=True)

        api_dir = os.path.join(main_api_dir, "울산_강좌정보")
        if not os.path.exists(api_dir):
            os.makedirs(api_dir, exist_ok=True)

        api_key = self.api_key_entry.get().strip()
        decoded_key = urllib.parse.unquote(api_key)
        detail_url = "http://apis.data.go.kr/6310000/ulsanyesedu/getUlsaneduView"
        
        count = 0
        total = len(selected_items)
        for i, entry in enumerate(selected_items):
            self.update_progress_ui(i, total)
            # lec_id extraction from raw XML string
            try:
                xml_root = ET.fromstring(entry["raw"])
                lec_id = xml_root.findtext("lec_id") or xml_root.findtext("LEC_ID")
            except:
                lec_id = None
                
            if not lec_id:
                print(f"Skipping {entry['title']}: No lec_id found.")
                continue

            params = {
                "serviceKey": decoded_key,
                "lecid": lec_id
            }

            try:
                response = requests.get(detail_url, params=params, timeout=10)
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}")
                
                # Ulsan API returns XML. parse it.
                root = ET.fromstring(response.content)
                item = root.find(".//list")
                if item is None:
                    continue

                def get_val(tag):
                    node = item.find(tag)
                    return (node.text or "").strip() if node is not None else ""

                lname = get_val("lname")
                target = get_val("target")
                method = get_val("method")
                lstatus = get_val("lstatus")
                price2 = get_val("price2")
                content = get_val("content")
                note = get_val("note")
                player_nm = get_val("player_nm")
                lec_time = get_val("lec_time")
                rstart = get_val("rstart")
                rend = get_val("rend")
                lstart = get_val("lstart")
                lend = get_val("lend")

                safe_title = "".join([c for c in lname if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                if not safe_title: safe_title = f"ulsan_{lec_id}"
                
                # Save Text
                file_path = os.path.join(api_dir, f"{safe_title}.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"강좌명: {lname}\n")
                    f.write(f"강좌코드: {lec_id}\n")
                    f.write(f"교육대상: {target}\n")
                    f.write(f"접수방법: {method}\n")
                    f.write(f"강좌상태: {lstatus}\n")
                    f.write(f"수강료: {price2}\n")
                    f.write(f"강사명: {player_nm}\n")
                    f.write(f"교육시간: {lec_time}\n")
                    f.write(f"접수기간: {rstart} ~ {rend}\n")
                    f.write(f"교육기간: {lstart} ~ {lend}\n")
                    f.write(f"\n[강좌 소개]\n{content}\n")
                    if note:
                        f.write(f"\n[주의 사항]\n{note}\n")
                
                count += 1
            except Exception as e:
                print(f"Error fetching/saving detail for {entry['title']}: {e}")

        self.update_progress_ui(total, total, "100% 완료")
        self.parent.after(0, lambda: messagebox.showinfo("완료", f"{count}개의 울산 강좌 상세 정보가 '{api_dir}' 폴더에 저장되었습니다."))

    def download_busan_details(self, base_dir, selected_items):
        # Ensure main 'api' folder exists
        main_api_dir = os.path.join(base_dir, "api")
        if not os.path.exists(main_api_dir):
            os.makedirs(main_api_dir)

        api_dir = os.path.join(main_api_dir, "부산_교육강좌")
        if not os.path.exists(api_dir):
            os.makedirs(api_dir)

        count = 0
        total = len(selected_items)
        for i, entry in enumerate(selected_items):
            self.update_progress_ui(i, total)
            
            try:
                # Parse the raw XML item
                item_xml = ET.fromstring(entry["raw"])
                
                def get_val(tag):
                    node = item_xml.find(tag)
                    return (node.text or "").strip() if node is not None else ""

                title = get_val("lctreNm")
                addr = get_val("adres")
                inst = get_val("resveGroupNm")
                status = get_val("progrsSttusNm")
                l_start = get_val("lctreBeginDttm")
                l_end = get_val("lctreEndDttm")
                r_start = get_val("reqstBeginDttm")
                r_end = get_val("reqstEndDttm")
                price = get_val("lctreChargeAmount")
                b_time = get_val("lctreBeginTime")
                e_time = get_val("lctreEndTime")
                tel = get_val("lctreRefrnc")
                quota = get_val("lctrePsncpa")
                residual = get_val("residualCNT")

                safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                if not safe_title: safe_title = f"busan_{i+1}"
                
                file_path = os.path.join(api_dir, f"{safe_title}.txt")
                with open(file_path, "w", encoding="utf-8") as f:
                    # Specific format requested by user: "제목 {강좌명}", "주소 {주소}"
                    f.write(f"제목 {title}\n")
                    f.write(f"주소 {addr}\n")
                    f.write(f"운영기관: {inst}\n")
                    f.write(f"접수상태: {status}\n")
                    f.write(f"수강료: {price}\n")
                    f.write(f"문의전화: {tel}\n")
                    f.write(f"교육시간: {b_time} ~ {e_time}\n")
                    f.write(f"교육기간: {l_start} ~ {l_end}\n")
                    f.write(f"신청기간: {r_start} ~ {r_end}\n")
                    f.write(f"정원/잔여: {quota} / {residual}\n")
                
                count += 1
            except Exception as e:
                print(f"Error parsing/saving Busan item {entry.get('title')}: {e}")

        self.update_progress_ui(total, total, "100% 완료")
        self.parent.after(0, lambda: messagebox.showinfo("완료", f"{count}개의 부산 강좌 정보가 '{api_dir}' 폴더에 저장되었습니다."))

    def download_kmooc_details(self, base_dir, selected_items):
        import time
        import os
        import requests
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from webdriver_manager.chrome import ChromeDriverManager

        # Progress bar setup
        total = len(selected_items)
        count = 0

        # Create main 'api' folder
        main_api_dir = os.path.join(base_dir, "api")
        if not os.path.exists(main_api_dir):
            os.makedirs(main_api_dir)

        kmooc_base_dir = os.path.join(main_api_dir, "kmooc_상세정보")
        if not os.path.exists(kmooc_base_dir):
            os.makedirs(kmooc_base_dir)

        # Selenium Options
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        driver = None
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            
            for i, entry in enumerate(selected_items):
                self.update_progress_ui(i, total)
                
                raw_item = entry.get("raw", {})
                course_id = None
                if isinstance(raw_item, dict):
                    course_id = raw_item.get("id")
                
                if not course_id:
                    # Try to extract from string if it was XML or other
                    import re
                    match = re.search(r'id=["\']?(\d+)', str(raw_item))
                    if match: course_id = match.group(1)

                if not course_id:
                    print(f"Skipping {entry['title']}: No course_id found.")
                    continue

                url = f"https://www.kmooc.kr/view/course/detail/{course_id}"
                driver.get(url)
                
                # Handle unexpected alerts (Course not in session etc.)
                try:
                    alert = driver.switch_to.alert
                    print(f"Alert detected for {course_id}: {alert.text}")
                    alert.accept()
                except:
                    pass

                try:
                    # Wait for essential element - reduced timeout slightly for failed pages
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "text")))
                    
                    # 1. Course Title & Folder
                    title_elem = driver.find_element(By.CSS_SELECTOR, ".text .title h4")
                    course_title = title_elem.text.strip()
                    safe_title = "".join([c for c in course_title if c.isalnum() or c in (' ', '.', '_', '-')]).strip()
                    if not safe_title: safe_title = f"kmooc_{course_id}"
                    
                    course_folder = os.path.join(kmooc_base_dir, safe_title)
                    if not os.path.exists(course_folder):
                        os.makedirs(course_folder)

                    # 2. Basic Info (Category, Institution, Phone, etc.)
                    info_dict = {}
                    dots = driver.find_elements(By.CSS_SELECTOR, ".list p.dot")
                    for dot in dots:
                        try:
                            cat = dot.find_element(By.CLASS_NAME, "catagory").text.strip()
                            val = dot.find_element(By.CLASS_NAME, "content").text.strip()
                            if cat: info_dict[cat] = val
                        except: continue

                    # 3. Introduction & Objectives
                    intro_text = ""
                    try:
                        intro_section = driver.find_element(By.CLASS_NAME, "introduce")
                        intro_text = intro_section.text.strip()
                    except: pass

                    # 4. Syllabus Table
                    syllabus_text = ""
                    try:
                        syll_table = driver.find_element(By.CLASS_NAME, "syllabus_table")
                        rows = syll_table.find_elements(By.TAG_NAME, "tr")
                        syll_lines = []
                        for row in rows:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            col_texts = [c.text.strip() for c in cols if c.text.strip()]
                            if col_texts:
                                syll_lines.append(" | ".join(col_texts))
                        syllabus_text = "\n".join(syll_lines)
                    except: pass

                    # 5. Staff Profiles
                    staff_info = []
                    staff_images = []
                    try:
                        prof_list = driver.find_elements(By.CSS_SELECTOR, "ul.professor li")
                        for idx, prof in enumerate(prof_list, 1):
                            role = prof.find_element(By.CSS_SELECTOR, ".info .title strong").text.strip()
                            p_text = prof.find_element(By.CSS_SELECTOR, ".info .text").text.strip()
                            staff_info.append(f"[{role}]\n{p_text}")
                            
                            # Image URL
                            try:
                                img_url = prof.find_element(By.TAG_NAME, "img").get_attribute("src")
                                if img_url and "http" in img_url:
                                    staff_images.append((f"staff_{idx}_{role}", img_url))
                            except: pass
                    except: pass

                    # 6. Course Main Image
                    main_img_url = None
                    try:
                        # Sometimes it's a specific class, or we can use the API one if needed
                        # But let's try to find it on page if possible. Usually course_image is in the API.
                        # For now, let's use the API one if available as a fallback
                        main_img_url = entry.get("raw", {}).get("course_image")
                    except: pass

                    # Save to TXT
                    file_path = os.path.join(course_folder, f"{safe_title}_상세정보.txt")
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(f"강좌명: {course_title}\n")
                        f.write(f"URL: {url}\n\n")
                        f.write("[기본 정보]\n")
                        for k, v in info_dict.items():
                            f.write(f"- {k}: {v}\n")
                        
                        f.write(f"\n[강좌 소개]\n{intro_text}\n")
                        
                        if syllabus_text:
                            f.write(f"\n[수업 계획서]\n{syllabus_text}\n")
                        
                        if staff_info:
                            f.write("\n[강좌 운영진]\n")
                            f.write("\n\n".join(staff_info))

                    # Download Images
                    def download_img(name, img_url):
                        try:
                            res = requests.get(img_url, timeout=10)
                            if res.status_code == 200:
                                ext = ".jpg"
                                if ".png" in img_url.lower(): ext = ".png"
                                elif ".gif" in img_url.lower(): ext = ".gif"
                                img_path = os.path.join(course_folder, f"{name}{ext}")
                                with open(img_path, "wb") as f_img:
                                    f_img.write(res.content)
                        except: pass

                    if main_img_url:
                        download_img("메인이미지", main_img_url)
                    for s_name, s_url in staff_images:
                        download_img(s_name, s_url)

                    count += 1
                except Exception as e:
                    print(f"Error scraping {url}: {e}")

        except Exception as e:
            print(f"Selenium Driver Error: {e}")
            self.parent.after(0, lambda: messagebox.showerror("오류", f"셀레니움 실행 중 오류가 발생했습니다: {e}"))
        finally:
            if driver: driver.quit()

        self.update_progress_ui(total, total, "100% 완료")
        self.parent.after(0, lambda: messagebox.showinfo("완료", f"{count}개의 K-MOOC 강좌 상세 정보와 이미지가 '{kmooc_base_dir}' 폴더에 저장되었습니다."))

    def download_lh_details(self, base_dir, selected_items):
        import re
        main_api_dir = os.path.join(base_dir, "api")
        if not os.path.exists(main_api_dir):
            os.makedirs(main_api_dir, exist_ok=True)

        api_dir = os.path.join(main_api_dir, "LH_분양공고")
        if not os.path.exists(api_dir):
            os.makedirs(api_dir, exist_ok=True)

        lh_field_map = {
            "PAN_NM": "공고명",
            "PAN_NT_ST_DT": "공고게시일",
            "CLSG_DT": "공고마감일",
            "PAN_SS": "공고상태",
            "CNP_CD_NM": "지역명",
            "AIS_TP_CD_NM": "매물유형",
            "UPP_AIS_TP_NM": "상위매물유형",
            "DTL_URL": "상세URL",
            "PAN_ID": "공고ID"
        }

        count = 0
        total = len(selected_items)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        # Initialize session to keep cookies
        session = requests.Session()
        session.headers.update(headers)

        for i, item in enumerate(selected_items):
            self.update_progress_ui(i, total, f"진행 중: {i+1}/{total}")
            
            raw = item.get("raw", {})
            title = item.get("title", "제목없음")
            safe_title = "".join([c for c in title if c.isalnum() or c in (' ', '.', '_', '-', '(', ')', '[', ']')]).strip()
            # Windows: Remove trailing dots to prevent directory creation mismatch
            safe_title = safe_title.rstrip(".")
            if not safe_title: safe_title = "공고이름없음"
            
            # Create folder
            item_folder = os.path.join(api_dir, safe_title)
            os.makedirs(item_folder, exist_ok=True)
            
            detail_content = ""
            file_links = []
            
            # 1. Crawl Detail Page
            detail_url = raw.get("DTL_URL")
            if detail_url:
                try:
                    res = session.get(detail_url, timeout=15)
                    if res.status_code == 200:
                        html = res.text
                        # ... (crawling text logic remains same)
                        cont_match = re.search(r'<div class="bbsV_cont">.*?<dd>(.*?)</dd>', html, re.DOTALL | re.IGNORECASE)
                        if cont_match:
                            cont_text = cont_match.group(1)
                            cont_text = re.sub(r'<.*?>', '', cont_text).strip()
                            detail_content += f"[공고 내용]\n{cont_text}\n\n"
                        
                        table_match = re.findall(r'<table.*?>(.*?)</table>', html, re.DOTALL | re.IGNORECASE)
                        for table_html in table_match:
                            rows = re.findall(r'<tr.*?>(.*?)</tr>', table_html, re.DOTALL | re.IGNORECASE)
                            table_text = ""
                            for row in rows:
                                cols = re.findall(r'<t[dh].*?>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
                                cols_text = [re.sub(r'<.*?>', '', col).strip() for col in cols]
                                if any(cols_text):
                                    table_text += " | ".join(cols_text) + "\n"
                            if table_text.strip():
                                detail_content += f"[구성 정보]\n{table_text}\n"

                        # 1. Extract File Links (Attachments)
                        all_ids = re.findall(r"fileDownLoad\('(\d+)'\)", html)
                        for fid in all_ids:
                            # Find the label in the anchor tag
                            m = re.search(fr"<a [^>]*fileDownLoad\('{fid}'\)[^>]*>(.*?)</a>", html, re.DOTALL | re.IGNORECASE)
                            f_name = f"file_{fid}"
                            if m:
                                f_name = re.sub(r"<.*?>", "", m.group(1)).strip()
                            
                            if (fid, f_name) not in file_links:
                                file_links.append((fid, f_name))
                            
                        # 2. Extract Floor Plans and Perspectives from JSON (wrtancFloorplan)
                        fp_match = re.search(r"var wrtancFloorplan = JSON\.parse\('(.*?)'\);", html, re.DOTALL)
                        if fp_match:
                            try:
                                fp_json_str = fp_match.group(1)
                                fp_data = json.loads(fp_json_str)
                                for tab in fp_data:
                                    for item in tab:
                                        hty = item.get('htyNna', '안내')
                                        # Floor Plan (cmnAhflSn)
                                        f_id = item.get('cmnAhflSn')
                                        if f_id:
                                            label = f"평면도_{hty}.jpg"
                                            if (str(f_id), label) not in file_links:
                                                file_links.append((str(f_id), label))
                                        
                                        # Perspective/Isometric (persCmnAhflSn)
                                        p_id = item.get('persCmnAhflSn')
                                        if p_id:
                                            label = f"투시도_{hty}.jpg"
                                            if (str(p_id), label) not in file_links:
                                                file_links.append((str(p_id), label))
                            except: pass

                        # 3. Extract Site Images (Generic - more strict filtering)
                        img_matches = re.finditer(r'<img [^>]*src=["\'](/[^"\']+\.(?:jpg|jpeg|png|gif|bmp))["\']', html, re.IGNORECASE)
                        for i, m in enumerate(img_matches):
                            img_path = m.group(1)
                            # EXCLUDE everything that looks like UI or placeholders
                            if any(x in img_path.lower() for x in ["logo", "ico", "btn", "common", "layout", "noimg", "loading", "bullet", "arrow", "top", "footer", "menu", "tab", "navi", "slider"]): continue
                            label = f"단지이미지_{i}.jpg"
                            if (img_path, label) not in file_links:
                                file_links.append((img_path, label))
                            
                except Exception as e:
                    print(f"Error crawling detail: {e}")

            # 2. Write Text File (logic remains same)
            text_file_path = os.path.join(item_folder, f"{safe_title}.txt")
            try:
                with open(text_file_path, "w", encoding="utf-8") as f:
                    f.write(f"제목: {title}\n")
                    f.write(f"수집일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("[기본 정보]\n")
                    for key, val in raw.items():
                        if key in ["RNUM", "ALL_CNT", "SPL_INF_TP_CD", "AIS_TP_CD", "PAN_DT", "CCR_CNNT_SYS_DS_CD", "DTL_URL_MOB", "UPP_AIS_TP_CD"]: continue
                        kor_name = lh_field_map.get(key, key)
                        f.write(f"- {kor_name}: {val}\n")
                    if detail_content: f.write(f"\n{detail_content}")
                    if file_links:
                        f.write("\n[첨부 파일 목록]\n")
                        for fid, fname in file_links: f.write(f"- {fname} (ID: {fid})\n")
            except Exception as e: print(f"Error writing text file: {e}")

            # 3. Download Files
            for fid, fname in file_links:
                try:
                    fname = "".join([c for c in fname if c.isalnum() or c in (' ', '.', '_', '-', '(', ')', '[', ']')]).strip()
                    # Iteratively try multiple download endpoints
                    # If fid starts with / it's a direct path
                    if isinstance(fid, str) and fid.startswith("/"):
                        path_variants = [fid]
                        # LH often prepends /upload or uses upload_dec folders
                        if not fid.startswith("/upload"):
                            path_variants.append("/upload" + fid)
                        if "/Files/upload/" in fid:
                            path_variants.append(fid.replace("/Files/upload/", "/upload/Files/upload_dec/"))
                        
                        endpoints = []
                        for pv in path_variants:
                            endpoints.append((f"https://apply.lh.or.kr{pv}", "GET", {}))
                    else:
                        # It's a file ID
                        endpoints = [
                            ("https://apply.lh.or.kr/lhapply/lhFile.do", "GET", {"fileid": fid}),
                            ("https://apply.lh.or.kr/lhapply/apply/cm/file/fileDownLoad.do", "POST", {"fileId": fid}),
                            ("https://apply.lh.or.kr/lhapply/apply/cm/file/fileDownLoad.do", "GET", {"fileId": fid})
                        ]
                    
                    # Headers with Referer
                    dl_headers = session.headers.copy()
                    if detail_url: dl_headers["Referer"] = detail_url
                    
                    f_res = None
                    chunk = None
                    for base_url, method, params in endpoints:
                        try:
                            if method == "POST":
                                temp_res = session.post(base_url, data=params, headers=dl_headers, timeout=30, stream=True)
                            else:
                                temp_res = session.get(base_url, params=params, headers=dl_headers, timeout=30, stream=True)
                            
                            if temp_res.status_code == 200:
                                temp_chunk = next(temp_res.iter_content(chunk_size=1024), None)
                                # Check if it's not HTML and not empty
                                if temp_chunk and b"<!DOCTYPE html>" not in temp_chunk and b"<script" not in temp_chunk:
                                    f_res = temp_res
                                    chunk = temp_chunk
                                    break
                        except: continue

                    if f_res and chunk:
                        f_save_path = os.path.join(item_folder, fname)
                        with open(f_save_path, "wb") as fb:
                            fb.write(chunk)
                            for c in f_res.iter_content(chunk_size=8192):
                                if c: fb.write(c)
                        print(f"Successfully downloaded: {fname}")
                    else:
                        print(f"Failed to download after trying all endpoints: {fname} (ID: {fid})")
                except Exception as e:
                    print(f"Error downloading file {fname}: {e}")

            count += 1

        self.update_progress_ui(total, total, "100% 완료")
        self.parent.after(0, lambda: messagebox.showinfo("완료", f"{count}개의 LH 공고 상세 정보와 첨부파일이 '{api_dir}' 폴더에 저장되었습니다."))

    def download_gov_details(self, base_dir, selected_items):
        import urllib.parse
        main_api_dir = os.path.join(base_dir, "api")
        os.makedirs(main_api_dir, exist_ok=True)
            
        api_dir = os.path.join(main_api_dir, "대한민국공공서비스정보")
        os.makedirs(api_dir, exist_ok=True)

        api_key = self.api_key_entry.get().strip()
        decoded_key = urllib.parse.unquote(api_key)
        detail_base_url = "https://api.odcloud.kr/api/gov24/v3/serviceDetail"

        count = 0
        total = len(selected_items)
        
        for i, item in enumerate(selected_items):
            self.update_progress_ui(i, total, f"진행 중: {i+1}/{total}")
            raw = item.get("raw", {})
            svc_id = raw.get("서비스ID")
            title = item.get("title", "공공서비스")
            
            if not svc_id:
                print(f"Skipping {title}: No 서비스ID found.")
                continue

            # Fetch Detailed Information for each service
            detail_data = {}
            try:
                params = {
                    "serviceKey": decoded_key,
                    "cond[서비스ID::EQ]": svc_id,
                    "page": 1,
                    "perPage": 1,
                    "returnType": "json"
                }
                res = requests.get(detail_base_url, params=params, timeout=15)
                if res.status_code == 200:
                    res_json = res.json()
                    detail_list = res_json.get("data", [])
                    if detail_list:
                        detail_data = detail_list[0]
            except Exception as e:
                print(f"Error fetching detail for {svc_id}: {e}")

            # Merge raw and detail_data
            full_data = {**raw, **detail_data}
            
            fs_title = title
            if len(fs_title) > 50: fs_title = fs_title[:47] + "..."
            safe_title = "".join([c for c in fs_title if c.isalnum() or c in (' ', '.', '_', '-', '(', ')', '[', ']')]).strip()
            if not safe_title: safe_title = f"서비스_{svc_id}"
            
            item_folder = os.path.join(api_dir, safe_title)
            os.makedirs(item_folder, exist_ok=True)
            
            file_path = os.path.join(item_folder, f"{safe_title}.txt")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(f"서비스명: {title}\n")
                    f.write(f"서비스ID: {svc_id}\n")
                    f.write(f"수집일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write("[상세 설명]\n")
                    f.write(f"{full_data.get('서비스목적', full_data.get('서비스목적요약', ''))}\n\n")
                    
                    f.write("[지원 대상 및 선정 기준]\n")
                    f.write(f"대상: {full_data.get('지원대상', '')}\n")
                    f.write(f"기준: {full_data.get('선정기준', '')}\n\n")
                    
                    f.write("[지원 내용]\n")
                    f.write(f"{full_data.get('지원내용', '')}\n\n")
                    
                    f.write("[신청 방법 및 기한]\n")
                    f.write(f"방법: {full_data.get('신청방법', '')}\n")
                    f.write(f"기한: {full_data.get('신청기한', '')}\n")
                    if full_data.get('온라인신청사이트URL'):
                        f.write(f"URL: {full_data.get('온라인신청사이트URL')}\n")
                    
                    f.write("\n[기타 정보]\n")
                    f.write(f"소관기관: {full_data.get('소관기관명', '')}\n")
                    f.write(f"부서: {full_data.get('부서명', '')}\n")
                    f.write(f"전화: {full_data.get('전화문의', full_data.get('문의처', ''))}\n")
                    
                count += 1
            except Exception as e:
                print(f"Error saving {title}: {e}")

        self.update_progress_ui(total, total, "100% 완료")
        self.parent.after(0, lambda: messagebox.showinfo("완료", f"{count}개의 공공서비스 정보가 '{api_dir}' 폴더에 저장되었습니다."))




