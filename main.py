import customtkinter as ctk
from Naver_nShop import NaverNShopAnalyzer
import threading
from tkinter import messagebox
import os
import sys

def resource_path(relative_path, external=False):
    """ 
    리소스 절대 경로 반환
    external=True: 실행 파일(.exe)과 같은 폴더 (설정값 저장용)
    external=False: 실행 파일 내부 또는 임시 폴더 (번들된 리소스용)
    """
    import sys
    import os
    
    if hasattr(sys, '_MEIPASS'): # PyInstaller
        base_path = sys._MEIPASS if not external else os.path.dirname(sys.executable)
    elif hasattr(sys, 'frozen') and hasattr(sys, '__nuitka_binary_dir'): # Nuitka
        base_path = os.path.dirname(__file__) if not external else os.path.dirname(sys.executable)
    else: # 개발 환경
        base_path = os.path.abspath(".")
        
    return os.path.join(base_path, relative_path)

class BrandConnectApp(ctk.CTk):
    def setup_nblog_ui(self):
        # We don't need this anymore as we use the main UI frames
        pass

    def start_nblog_all(self):
        """비로그인 무패스 모드 실행 (다중 행 지원)"""
        base_url = self.nblog_base_url.get().strip()
        tasks = []
        for item in self.row_items:
            kw = self.clean_title(item["keyword"].get().strip())
            item["keyword"].delete(0, 'end')
            item["keyword"].insert(0, kw)
            kw2 = item["keyword2"].get().strip() if "keyword2" in item else ""
            url = item["url"].get().strip()
            if url:
                tasks.append((kw, url, kw2))
                
        if not tasks:
            messagebox.showwarning("경고", "최소 하나 이상의 다운_URL을 입력해주세요.")
            return
            
        # Optional: ensure base_url exists even if empty
        if not base_url:
            base_url = tasks[0][1]
            
        from tkinter import filedialog
        save_dir = filedialog.askdirectory(title="백업 결과물을 저장할 폴더를 선택하세요")
        if not save_dir: return

        self.btn_nblog_start_all.configure(state="disabled")
        
        def run():
            try:
                if not hasattr(self, 'nblog_analyzer'):
                    import naver_blog
                    self.nblog_analyzer = naver_blog.NaverBlogAnalyzer()
                
                total_msg = []
                total_tasks = len(tasks)
                for i, (kw, url, kw2) in enumerate(tasks):
                    display_kw = kw if kw else f"작업_{i+1}"
                    self.after(0, lambda v=i/total_tasks, s=f"N블로그 분석 중 ({i+1}/{total_tasks}): {display_kw}": self.update_progress(v, s))
                    success, msg = self.nblog_analyzer.start_auto_scraping(base_url, url, save_dir, kw, image_prefix=kw2)
                    total_msg.append(f"[{display_kw}] {msg}")
                
                self.after(0, lambda: self.update_progress(1.0, "N블로그 분석 완료"))
                self.after(0, lambda: messagebox.showinfo("결과", "\n".join(total_msg)))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
            finally:
                self.after(0, lambda: self.btn_nblog_start_all.configure(state="normal"))
        
        threading.Thread(target=run, daemon=True).start()

    def open_nblog_window(self):
        """수동 로그인용 브라우저 창 띄우기"""
        if not hasattr(self, 'nblog_analyzer'):
            import naver_blog
            self.nblog_analyzer = naver_blog.NaverBlogAnalyzer()
        
        success, msg = self.nblog_analyzer.open_browser()
        if success:
            messagebox.showinfo("안내", "브라우저가 열렸습니다. 네이버 로그인을 완료한 뒤 '크롤링 시작' 버튼을 눌러주세요.")
        else:
            messagebox.showerror("오류", msg)

    def start_nblog_crawl(self):
        """로그인 후 크롤링 시작 (다중 행 지원)"""
        base_url = self.nblog_base_url.get().strip()
        tasks = []
        for item in self.row_items:
            kw = self.clean_title(item["keyword"].get().strip())
            item["keyword"].delete(0, 'end')
            item["keyword"].insert(0, kw)
            kw2 = item["keyword2"].get().strip() if "keyword2" in item else ""
            url = item["url"].get().strip()
            if url:
                tasks.append((kw, url, kw2))

        if not tasks:
            messagebox.showwarning("경고", "최소 하나 이상의 다운_URL을 입력해주세요.")
            return
            
        # Optional: ensure base_url exists even if empty
        if not base_url:
            base_url = tasks[0][1]
            
        if not hasattr(self, 'nblog_analyzer') or not self.nblog_analyzer.driver:
            messagebox.showwarning("경고", "'크롤링창 띄우기'를 먼저 클릭해주세요.")
            return

        from tkinter import filedialog
        save_dir = filedialog.askdirectory(title="백업 결과물을 저장할 폴더를 선택하세요")
        if not save_dir: return

        self.btn_nblog_start_crawl.configure(state="disabled")
        
        def run():
            try:
                total_msg = []
                total_tasks = len(tasks)
                for i, (kw, url, kw2) in enumerate(tasks):
                    display_kw = kw if kw else f"작업_{i+1}"
                    self.after(0, lambda v=i/total_tasks, s=f"N블로그 분석 중 ({i+1}/{total_tasks}): {display_kw}": self.update_progress(v, s))
                    success, msg = self.nblog_analyzer.start_manual_scraping(base_url, url, save_dir, kw, image_prefix=kw2)
                    total_msg.append(f"[{display_kw}] {msg}")
                
                self.after(0, lambda: self.update_progress(1.0, "N블로그 분석 완료"))
                self.after(0, lambda: messagebox.showinfo("결과", "\n".join(total_msg)))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("오류", str(e)))
            finally:
                self.after(0, lambda: self.btn_nblog_start_crawl.configure(state="normal"))
        
        threading.Thread(target=run, daemon=True).start()

    def __init__(self):
        super().__init__()

        self.title("mato_blog_helper v1.1")
        self.geometry("900x700") # Resized for board UI
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.current_platform = "unified"
        self.analyzer = NaverNShopAnalyzer()
        self.row_items = [] # Store row components: (keyword_entry, url_entry, frame)
        self.nblog_disclaimer_accepted = False # Track nblog disclaimer acceptance

        self.setup_ui()
        self.add_row() # Start with one row
        self.switch_platform("usage") # Initialize state with Usage tab

    def setup_ui(self):
        # Navigation Bar
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(fill="x", pady=(20, 0), padx=20)
        
        self.btn_usage = ctk.CTkButton(self.nav_frame, text="사용방법", width=80, command=lambda: self.switch_platform("usage"))
        self.btn_usage.pack(side="left", padx=(0, 10))

        self.btn_prompt = ctk.CTkButton(self.nav_frame, text="프롬프트", width=80, command=lambda: self.switch_platform("prompt"))
        self.btn_prompt.pack(side="left", padx=(0, 10))

        self.btn_unified = ctk.CTkButton(self.nav_frame, text="통합", width=80, command=lambda: self.switch_platform("unified"))
        self.btn_unified.pack(side="left", padx=10, anchor="n")

        self.btn_naver = ctk.CTkButton(self.nav_frame, text="네이버", width=80, command=lambda: self.switch_platform("naver"))
        self.btn_naver.pack(side="left", padx=10, anchor="n")
        
        self.btn_coupang = ctk.CTkButton(self.nav_frame, text="쿠팡", width=80, command=lambda: self.switch_platform("coupang"))
        self.btn_coupang.pack(side="left", padx=10, anchor="n")
        
        self.btn_marit = ctk.CTkButton(self.nav_frame, text="마리트", width=80, command=lambda: self.switch_platform("marit"))
        self.btn_marit.pack(side="left", padx=10, anchor="n")

        self.btn_api = ctk.CTkButton(self.nav_frame, text="API", width=80, command=lambda: self.switch_platform("api"))
        self.btn_api.pack(side="left", padx=10, anchor="n")

        self.btn_nblog = ctk.CTkButton(self.nav_frame, text="N블로그", width=80, command=lambda: self.switch_platform("nblog"))
        self.btn_nblog.pack(side="left", padx=10, anchor="n")

        # N-Blog Top Entry (Global for nblog platform)
        self.nblog_top_frame = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(self.nblog_top_frame, text="네이버_URL:", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(20, 5))
        self.nblog_base_url = ctk.CTkEntry(self.nblog_top_frame, placeholder_text="예: https://blog.naver.com/아이디", width=500)
        self.nblog_base_url.pack(side="left", padx=5, fill="x", expand=True)

        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", pady=20, padx=20)
        
        self.title_label = ctk.CTkLabel(self.header_frame, text="mato_blog_helper v1.0", font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left")

        # Control Buttons
        self.add_row_button = ctk.CTkButton(self.header_frame, text="+ 행 추가", width=100, command=self.add_row, fg_color="#28a745", hover_color="#218838")
        self.add_row_button.pack(side="right", padx=(10, 0))

        # Main Content - Scrollable Frame (For URLs/Keywords)
        self.scrollable_frame = ctk.CTkScrollableFrame(self, label_text="키워드 및 URL 리스트 (네이버)")
        self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # Load Usage Content Frame
        self.usage_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        self.usage_text = ctk.CTkTextbox(self.usage_frame, font=ctk.CTkFont(size=16), wrap="word")
        self.usage_text.pack(fill="both", expand=True, pady=40, padx=20)
        
        note_path = resource_path("Note.txt")
        default_usage_info = "[ 사용방법 및 공지사항 ]\n\n\n현재 준비중입니다.\n\n이곳에 프로그램의 자세한 사용 방법을 입력하거나 Note.txt 파일을 수정해주세요."
        
        if os.path.exists(note_path):
            try:
                try:
                    with open(note_path, "r", encoding="utf-8") as f:
                        usage_info = f.read()
                except UnicodeError:
                    try:
                        with open(note_path, "r", encoding="cp949") as f:
                            usage_info = f.read()
                    except UnicodeError:
                        with open(note_path, "r", encoding="utf-16") as f:
                            usage_info = f.read()
            except Exception as e:
                usage_info = f"Note.txt 파일을 읽는 중 오류가 발생했습니다:\n{e}"
        else:
            usage_info = default_usage_info
            try:
                with open(note_path, "w", encoding="utf-8") as f:
                    f.write(default_usage_info)
            except Exception:
                pass
                
        self.usage_text.insert("0.0", usage_info)
        self.usage_text.configure(state="disabled")  # Make it read-only but allow selection/copy

        # Prompt Content Frame (Hidden by default)
        self.prompt_frame = ctk.CTkFrame(self, fg_color="transparent")
        
        # Ensure Prompt directory exists
        self.prompt_dir = resource_path("Prompt")
        if not os.path.exists(self.prompt_dir):
            os.makedirs(self.prompt_dir)
            
        self.prompt_top_frame = ctk.CTkFrame(self.prompt_frame, fg_color="transparent")
        self.prompt_top_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(self.prompt_top_frame, text="프롬프트 선택:", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 10))
        
        self.prompt_var = ctk.StringVar(value="선택하세요")
        self.prompt_combo = ctk.CTkOptionMenu(
            self.prompt_top_frame, 
            variable=self.prompt_var,
            values=["선택하세요"],
            command=self.on_prompt_select,
            width=200
        )
        self.prompt_combo.pack(side="left")
        
        self.btn_refresh_prompts = ctk.CTkButton(self.prompt_top_frame, text="새로고침", width=60, command=self.load_prompt_list)
        self.btn_refresh_prompts.pack(side="left", padx=10)
        
        self.btn_copy_prompt = ctk.CTkButton(self.prompt_top_frame, text="전체복사", width=80, fg_color="#28a745", hover_color="#218838", command=self.copy_prompt_to_clipboard)
        self.btn_copy_prompt.pack(side="left", padx=5)
        
        self.prompt_text = ctk.CTkTextbox(self.prompt_frame, font=ctk.CTkFont(size=16), wrap="word")
        self.prompt_text.pack(fill="both", expand=True, pady=(0, 40), padx=20)
        self.prompt_text.configure(state="disabled")

        self.load_prompt_list()

        # API Content Frame (Hidden by default)
        self.api_frame = ctk.CTkFrame(self, fg_color="transparent")
        from api_s import APIHandler
        self.api_handler = APIHandler(self.api_frame)

        # NBlog Content Frame (Hidden by default)
        self.nblog_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.setup_nblog_ui()

        # Bottom Frame (Progress & Actions)
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(fill="x", padx=20, pady=20)

        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self.bottom_frame)
        self.progress_bar.pack(fill="x", padx=10, pady=(10, 5))
        self.progress_bar.set(0)

        self.progress_status = ctk.CTkLabel(self.bottom_frame, text="준비됨", font=ctk.CTkFont(size=12))
        self.progress_status.pack(pady=5)

        self.run_button = ctk.CTkButton(self.bottom_frame, text="전체 작업 시작", height=40, font=ctk.CTkFont(size=16, weight="bold"), command=self.start_all_tasks)
        self.run_button.pack(fill="x", padx=10, pady=10)

        # N-Blog Bottom Actions (Hidden by default)
        self.nblog_bottom_frame = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        
        self.btn_nblog_start_all = ctk.CTkButton(self.nblog_bottom_frame, text="전체작업시작\n(비로그인 무패스)", width=150, height=50, fg_color="#28a745", hover_color="#218838", command=self.start_nblog_all)
        self.btn_nblog_start_all.pack(side="left", padx=10)

        self.btn_nblog_open_win = ctk.CTkButton(self.nblog_bottom_frame, text="크롤링창 띄우기\n(수동 로그인용)", width=150, height=50, fg_color="#17a2b8", hover_color="#138496", command=self.open_nblog_window)
        self.btn_nblog_open_win.pack(side="left", padx=10)

        self.btn_nblog_start_crawl = ctk.CTkButton(self.nblog_bottom_frame, text="크롤링 시작\n(로그인 후 클릭)", width=150, height=50, fg_color="#fd7e14", hover_color="#e36c09", command=self.start_nblog_crawl)
        self.btn_nblog_start_crawl.pack(side="left", padx=10)

    def load_prompt_list(self):
        if not os.path.exists(self.prompt_dir):
            return
            
        prompt_files = [f for f in os.listdir(self.prompt_dir) if f.lower().endswith('.txt')]
        if not prompt_files:
            self.prompt_combo.configure(values=["<프롬프트 파일 없음>"])
            self.prompt_var.set("<프롬프트 파일 없음>")
            self.update_prompt_text("Prompt 폴더에 .txt 파일이 없습니다.")
        else:
            prompt_names = [os.path.splitext(f)[0] for f in prompt_files]
            self.prompt_combo.configure(values=prompt_names)
            if self.prompt_var.get() not in prompt_names:
                self.prompt_var.set(prompt_names[0])
                self.on_prompt_select(prompt_names[0])
            else:
                self.on_prompt_select(self.prompt_var.get())
                
    def on_prompt_select(self, filename_without_ext):
        if filename_without_ext == "<프롬프트 파일 없음>" or filename_without_ext == "선택하세요":
            self.update_prompt_text("프롬프트 파일을 선택해주세요.")
            return
            
        filename = f"{filename_without_ext}.txt"
        filepath = os.path.join(self.prompt_dir, filename)
        if os.path.exists(filepath):
            try:
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read()
                except UnicodeDecodeError:
                    with open(filepath, "r", encoding="cp949") as f:
                        content = f.read()
                self.update_prompt_text(content)
            except Exception as e:
                self.update_prompt_text(f"파일을 읽는 중 오류가 발생했습니다:\n{e}")
        else:
            self.update_prompt_text("파일을 찾을 수 없습니다.")
            self.load_prompt_list()

    def update_prompt_text(self, text):
        self.prompt_text.configure(state="normal")
        self.prompt_text.delete("0.0", "end")
        self.prompt_text.insert("0.0", text)
        self.prompt_text.configure(state="disabled")

    def copy_prompt_to_clipboard(self):
        text = self.prompt_text.get("0.0", "end-1c")
        if not text or text.strip() == "" or text == "프롬프트 파일을 선택해주세요." or text == "Prompt 폴더에 .txt 파일이 없습니다.":
            messagebox.showwarning("경고", "복사할 내용이 없습니다.")
            return
            
        self.clipboard_clear()
        self.clipboard_append(text)
        messagebox.showinfo("복사 완료", "프롬프트 내용이 클립보드에 복사되었습니다.")

    def switch_platform(self, platform):
        self.current_platform = platform
        
        # 버튼을 클릭하여 플랫폼을 전환할 때 키워드 및 URL 창 리셋 (첫 번째 행만 남기고 값 삭제)
        if hasattr(self, 'row_items') and self.row_items:
            for item in self.row_items[1:]:
                item["frame"].destroy()
            self.row_items = self.row_items[:1]
            self.row_items[0]["keyword"].delete(0, 'end')
            self.row_items[0]["url"].configure(state="normal")
            self.row_items[0]["url"].delete(0, 'end')
            if "html_data" in self.row_items[0]:
                self.row_items[0]["html_data"] = ""
        
        # Reset button colors (using ctk default blue theme colors)
        default_color = ["#3a7ebf", "#1f538d"]
        active_color = ["#2fa572", "#106a43"]
        
        self.btn_unified.configure(fg_color=default_color)
        self.btn_naver.configure(fg_color=default_color)
        self.btn_coupang.configure(fg_color=default_color)
        self.btn_marit.configure(fg_color=default_color)
        self.btn_usage.configure(fg_color=default_color)
        self.btn_prompt.configure(fg_color=default_color)
        if hasattr(self, 'btn_api'):
            self.btn_api.configure(fg_color=default_color)
        if hasattr(self, 'btn_nblog'):
            self.btn_nblog.configure(fg_color=default_color)

        # Hide ALL content frames first
        self.usage_frame.pack_forget()
        self.prompt_frame.pack_forget()
        self.api_frame.pack_forget()
        self.nblog_top_frame.pack_forget()
        self.nblog_bottom_frame.pack_forget()
        self.header_frame.pack_forget()
        self.scrollable_frame.pack_forget()
        self.bottom_frame.pack_forget()
        self.run_button.pack_forget()
        
        # Now pack then in standard order if not usage/prompt/nblog/api
        if platform not in ["usage", "prompt", "nblog", "api"]:
            self.header_frame.pack(fill="x", pady=20, padx=20)
            self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=10)
            self.bottom_frame.pack(fill="x", padx=20, pady=20)
            self.run_button.pack(fill="x", padx=10, pady=10)

        if platform == "unified":
            self.btn_unified.configure(fg_color=active_color)
            self.title_label.configure(text="통합 브랜드 커넥트 분석 도구")
            self.scrollable_frame.configure(label_text="키워드 및 URL 리스트 (통합)")
        elif platform == "naver":
            self.btn_naver.configure(fg_color=active_color)
            self.title_label.configure(text="네이버 브랜드 커넥트 분석 도구")
            self.scrollable_frame.configure(label_text="키워드 및 URL/TXT 리스트 (네이버)")
            for item in self.row_items:
                item["url"].configure(state="normal")
                item["url"].configure(placeholder_text="분석할 URL 또는 TXT 경로 입력")
                if "upload_btn" in item:
                    item["upload_btn"].pack(side="left", padx=5, before=item["delete_btn"])
                    
        elif platform == "coupang":
            self.btn_coupang.configure(fg_color=active_color)
            self.title_label.configure(text="쿠팡 분석 도구")
            self.scrollable_frame.configure(label_text="키워드 및 HTML/TXT 리스트 (쿠팡)")
            
            for item in self.row_items:
                item["url"].configure(state="normal")
                if not item.get("html_data"):
                    item["url"].delete(0, 'end')
                item["url"].configure(placeholder_text="키워드, html 소스코드 업로드 해주세요")
                item["url"].configure(state="readonly")
                if "upload_btn" in item:
                    item["upload_btn"].pack(side="left", padx=5, before=item["delete_btn"])
                
        elif platform == "marit":
            self.btn_marit.configure(fg_color=active_color)
            self.title_label.configure(text="마이리얼트립 분석 도구")
            self.scrollable_frame.configure(label_text="키워드 및 HTML/TXT 리스트 (마리트)")
            for item in self.row_items:
                item["url"].configure(state="normal")
                if not item.get("html_data"):
                    item["url"].delete(0, 'end')
                item["url"].configure(placeholder_text="키워드, html 소스코드 업로드 해주세요")
                item["url"].configure(state="readonly")
                if "upload_btn" in item:
                    item["upload_btn"].pack(side="left", padx=5, before=item["delete_btn"])
                    
        elif platform == "nblog":
            if not self.nblog_disclaimer_accepted:
                disclaimer = "타인의 제작물을 허가없이 재가공,재사용하는건 저작권법에 위배되며, 법적문제가 발생 할 수 있으며, 이는 본인이 책임져야 합니다."
                if messagebox.askokcancel("저작권 주의사항", disclaimer):
                    self.nblog_disclaimer_accepted = True
                else:
                    self.destroy()
                    return

            if hasattr(self, 'btn_nblog'):
                self.btn_nblog.configure(fg_color=active_color)
            
            self.title_label.configure(text="네이버 블로그 글, 이미지 다운")

            # Show NBlog UI with Row support
            self.nblog_top_frame.pack(fill="x", pady=(20, 10))
            self.header_frame.pack(fill="x", pady=20, padx=20)
            self.scrollable_frame.pack(fill="both", expand=True, padx=20, pady=10)
            self.scrollable_frame.configure(label_text="키워드(폴더명) 및 다운_URL 리스트 (N블로그)")
            self.bottom_frame.pack(fill="x", padx=20, pady=20)
            self.nblog_bottom_frame.pack(pady=10)
            
            # Reset rows with NBlog placeholders
            for item in self.row_items:
                if "keyword2" in item:
                    item["keyword2"].pack(side="left", padx=5, before=item["keyword"])
                    item["keyword2"].configure(placeholder_text="키워드명")
                item["keyword"].configure(placeholder_text="네이버블로그제목")
                item["url"].configure(placeholder_text="블로그 URL")

        elif platform == "usage":
            self.btn_usage.configure(fg_color=active_color)
            self.title_label.configure(text="사용 방법 및 공지사항")
            # Show Usage text
            self.usage_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
        elif platform == "prompt":
            self.btn_prompt.configure(fg_color=active_color)
            self.title_label.configure(text="AI 프롬프트 설정")
            # Show Prompt UI
            self.prompt_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            # Refresh prompt list when entering tab
            self.load_prompt_list()

        elif platform == "api":
            if hasattr(self, 'btn_api'):
                self.btn_api.configure(fg_color=active_color)
            self.title_label.configure(text="공공데이터 API 분석 도구")
            # Show API UI
            self.api_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Revert placeholders back to URL if not coupang/naver/marit/nblog
        if platform not in ["coupang", "naver", "marit", "nblog", "unified", "usage", "prompt"]:
            for item in self.row_items:
                if "keyword2" in item:
                    item["keyword2"].pack_forget()
                item["url"].configure(state="normal")
                item["url"].configure(placeholder_text="분석할 URL 입력")
                if "upload_btn" in item:
                    item["upload_btn"].pack_forget()
                    
        # Always pack for unified as well assuming they can use TXT
        if platform == "unified":
            self.scrollable_frame.configure(label_text="키워드 및 URL/HTML/TXT 리스트 (통합)")
            for item in self.row_items:
                item["url"].configure(state="normal")
                item["url"].configure(placeholder_text="분석할 URL/HTML 또는 TXT 경로 입력")
                if "upload_btn" in item:
                    item["upload_btn"].pack(side="left", padx=5, before=item["delete_btn"])

    def upload_txt(self, current_item):
        from tkinter import filedialog, messagebox
        import os
        import re
        filename = filedialog.askopenfilename(
            title="TXT 파일 선택", 
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
        )
        if not filename:
            return
            
        try:
            try:
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read().strip()
            except UnicodeDecodeError:
                with open(filename, "r", encoding="cp949") as f:
                    content = f.read().strip()
            
            # 1. Advanced Streaming Parser: Handles T-U or U-T pairs in any sequence
            all_lines = [l.strip() for l in content.split('\n') if l.strip() and not re.match(r'^[=-]{3,}$', l.strip())]
            base_name = os.path.splitext(os.path.basename(filename))[0]
            
            pairs = []
            temp_text = []
            temp_url = None
            
            def flush_pair():
                nonlocal temp_text, temp_url
                if temp_url:
                    kw = " ".join(temp_text) if temp_text else base_name
                    pairs.append((kw, temp_url))
                elif temp_text:
                    # Text without URL? 
                    # If it's just a single URL in the whole file, it's handled below.
                    pass
                temp_text = []
                temp_url = None

            for line in all_lines:
                is_url = re.search(r'https?://[^\s]+', line)
                
                if is_url:
                    if temp_url:
                        # Already have a URL, flush it first
                        flush_pair()
                        temp_url = line
                    elif temp_text:
                        # Pair found: Keyword first, then URL
                        temp_url = line
                        flush_pair()
                    else:
                        temp_url = line
                else:
                    if temp_url:
                        # Pair found: URL first, then Keyword
                        temp_text = [line]
                        flush_pair()
                    else:
                        temp_text.append(line)
            
            # Final flush if anything remains
            if temp_url or temp_text:
                flush_pair()
            
            if pairs:
                valid_pairs = []
                ignored_count = 0
                for k, v in pairs:
                    v_lower = v.lower()
                    k_lower = k.lower()
                    if self.current_platform == "unified":
                        if "naver.me" in v_lower or "naver.com" in v_lower or "coupang.com" in v_lower or "myrealtrip.com" in v_lower or "myrealt.rip" in v_lower or "<html" in v_lower or "네이버" in k_lower or "쿠팡" in k_lower or "마리트" in k_lower:
                            valid_pairs.append((k, v))
                        else:
                            ignored_count += 1
                    elif self.current_platform == "naver" and ("naver.me" in v_lower or "naver.com" in v_lower):
                        valid_pairs.append((k, v))
                    elif self.current_platform == "coupang" and ("coupang.com" in v_lower or "<html" in v_lower or "쿠팡" in k_lower):
                        valid_pairs.append((k, v))
                    elif self.current_platform == "nblog" and ("naver.me" in v_lower or "blog.naver.com" in v_lower):
                        valid_pairs.append((k, v))
                    elif self.current_platform == "marit" and ("myrealtrip.com" in v_lower or "myrealt.rip" in v_lower or "<html" in v_lower or "마리트" in k_lower):
                        valid_pairs.append((k, v))
                    else:
                        ignored_count += 1
                
                if ignored_count > 0:
                    alert_msg = ""
                    if self.current_platform == "naver":
                        alert_msg = "네이버 브랜드커넥트 링크만 삽입해주세요."
                    elif self.current_platform == "coupang":
                        alert_msg = "쿠팡 링크만 삽입해주세요."
                    elif self.current_platform == "marit":
                        alert_msg = "마이리얼트립 링크만 삽입해주세요."
                    elif self.current_platform == "unified":
                        alert_msg = "네이버 브랜드커넥트\n쿠팡, 마이리얼트립의 URL 을 삽입해주세요."
                    else:
                        alert_msg = f"현재 플랫폼에 맞지 않는 URL {ignored_count}개가 제외되었습니다."
                        
                    messagebox.showwarning("URL 오류", alert_msg)

                if not valid_pairs:
                    # 모든 항목이 유효하지 않아 등록되지 않으면 현재 입력창을 완전히 초기화
                    current_item["keyword"].delete(0, 'end')
                    current_item["url"].configure(state="normal")
                    current_item["url"].delete(0, 'end')
                    if "html_data" in current_item:
                        current_item["html_data"] = ""
                    return

                # 하나라도 유효한 값이 있을 경우 첫 번째 셀에 등록
                first_k, first_val = valid_pairs[0]
                
                # 네이버 블로그 제목 [출처] 제거
                if self.current_platform == "nblog":
                    first_k = self.clean_title(first_k)
                
                current_item["keyword"].delete(0, 'end')
                current_item["keyword"].insert(0, first_k)
                
                current_item["url"].configure(state="normal")
                current_item["url"].delete(0, 'end')
                
                is_html_payload = ("<html" in first_val.lower() or len(first_val) > 500)
                if self.current_platform in ["coupang", "marit"] or (self.current_platform == "unified" and is_html_payload):
                    current_item["url"].insert(0, f"HTML 로드됨 ({len(first_val)} bytes)")
                    current_item["url"].configure(state="readonly")
                    current_item["html_data"] = first_val
                else:
                    current_item["url"].insert(0, first_val)
                    current_item["html_data"] = ""
                
                for i in range(1, len(valid_pairs)):
                    k, v = valid_pairs[i]
                    if self.current_platform == "nblog":
                        k = self.clean_title(k)
                    self.add_row(keyword=k, html_data=v)
                    
        except Exception as e:
            messagebox.showerror("오류", f"파일을 읽는 중 오류가 발생했습니다:\n{e}")

    def clean_title(self, title):
        if title and " [" in title:
            return title.split(" [")[0].strip()
        return title

    def add_row(self, keyword="", html_data=""):
        row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=5)

        placeholder_k = "네이버블로그제목" if self.current_platform == "nblog" else "키워드"
        keyword_entry = ctk.CTkEntry(row_frame, width=150, placeholder_text=placeholder_k)
        keyword_entry.pack(side="left", padx=5)

        # 네이버 블로그 제목 [출처] 자동 제거 바인딩 (포커스 아웃 시 실행)
        def on_keyword_focus_out(event, entry=keyword_entry):
            if self.current_platform == "nblog":
                val = entry.get()
                cleaned = self.clean_title(val)
                if cleaned != val:
                    entry.delete(0, 'end')
                    entry.insert(0, cleaned)

        keyword_entry.bind("<FocusOut>", on_keyword_focus_out)
        if keyword:
            keyword_entry.insert(0, keyword)

        # N블로그용 키워드명Entry (이미지 파일명용)
        keyword2_entry = ctk.CTkEntry(row_frame, width=120, placeholder_text="키워드명")
        if self.current_platform == "nblog":
            keyword2_entry.pack(side="left", padx=5, before=keyword_entry)
        
        if self.current_platform == "nblog":
            placeholder = "블로그 URL"
        else:
            placeholder = "키워드, html 소스코드 업로드 해주세요" if self.current_platform in ["coupang", "marit"] else "분석할 URL 입력"
        
        url_entry = ctk.CTkEntry(row_frame, placeholder_text=placeholder, width=300)
        url_entry.pack(side="left", padx=5, expand=True, fill="x")

        upload_btn = ctk.CTkButton(row_frame, text="TXT 첨부", width=60, fg_color="#6c757d", hover_color="#5a6268")

        delete_btn = ctk.CTkButton(row_frame, text="X", width=30, fg_color="#dc3545", hover_color="#c82333", command=lambda f=row_frame: self.remove_row(f))
        
        item = {
            "frame": row_frame,
            "keyword": keyword_entry,
            "keyword2": keyword2_entry,
            "url": url_entry,
            "upload_btn": upload_btn,
            "delete_btn": delete_btn,
            "html_data": html_data
        }
        
        upload_btn.configure(command=lambda i=item: self.upload_txt(i))
        
        is_html_payload = ("<html" in html_data.lower() or len(html_data) > 500) if html_data else False
        if self.current_platform in ["coupang", "marit"] or (self.current_platform == "unified" and is_html_payload):
            url_entry.configure(state="normal")
            if html_data:
                url_entry.insert(0, f"HTML 로드됨 ({len(html_data)} bytes)")
            url_entry.configure(state="readonly")
        else:
            url_entry.configure(state="normal")
            if html_data:
                url_entry.insert(0, html_data)
                
        upload_btn.pack(side="left", padx=5)
        delete_btn.pack(side="left", padx=5)

        self.row_items.append(item)

    def remove_row(self, frame):
        if len(self.row_items) <= 1:
            messagebox.showwarning("주의", "최소 하나의 행은 있어야 합니다.")
            return

        for i, item in enumerate(self.row_items):
            if item["frame"] == frame:
                item["frame"].destroy()
                self.row_items.pop(i)
                break

    def start_all_tasks(self):
        # Validate tasks
        tasks = []
        for item in self.row_items:
            k = item["keyword"].get().strip()
            if self.current_platform == "nblog":
                k = self.clean_title(k)
                item["keyword"].delete(0, 'end')
                item["keyword"].insert(0, k)
            
            u = item.get("html_data") if item.get("html_data") else item["url"].get().strip()
            
            if k and u:
                u_lower = u.lower()
                k_lower = k.lower()
                valid = True
                
                if self.current_platform == "unified":
                    if not ("naver.me" in u_lower or "naver.com" in u_lower or "coupang.com" in u_lower or "myrealtrip.com" in u_lower or "myrealt.rip" in u_lower or "<html" in u_lower or "네이버" in k_lower or "쿠팡" in k_lower or "마리트" in k_lower):
                        valid = False
                elif self.current_platform == "naver":
                    if "naver.me" not in u_lower and "naver.com" not in u_lower:
                        valid = False
                elif self.current_platform == "coupang":
                    if not ("coupang.com" in u_lower or "<html" in u_lower or "쿠팡" in k_lower):
                        valid = False
                elif self.current_platform == "nblog":
                    if "naver.me" not in u_lower and "blog.naver.com" not in u_lower:
                        valid = False
                elif self.current_platform == "marit":
                    if not ("myrealtrip.com" in u_lower or "myrealt.rip" in u_lower or "<html" in u_lower or "마리트" in k_lower):
                        valid = False
                
                if not valid:
                    alert_msg = ""
                    if self.current_platform == "naver":
                        alert_msg = f"네이버 브랜드커넥트 링크를 삽입해주세요.\n(입력된 URL: {u})"
                    elif self.current_platform == "coupang":
                        alert_msg = f"쿠팡 링크를 삽입해주세요.\n(입력된 URL: {u})"
                    elif self.current_platform == "marit":
                        alert_msg = f"마이리얼트립 링크(myrealtrip.com 또는 myrealt.rip)를 삽입해주세요.\n(입력된 URL: {u})"
                    else:
                        alert_msg = "네이버 브랜드커넥트\n쿠팡, 마이리얼트립의 URL 을 삽입해주세요."
                    
                    messagebox.showwarning("URL 오류", alert_msg)
                    item["keyword"].delete(0, 'end')
                    item["url"].configure(state="normal")
                    item["url"].delete(0, 'end')
                else:
                    tasks.append((k, u))

        if not tasks:
            messagebox.showwarning("입력 오류", "유효한 키워드와 데이터를 입력해주세요.")
            return

        from tkinter import filedialog
        base_output_dir = filedialog.askdirectory(title="결과물을 저장할 폴더를 선택하세요")
        if not base_output_dir:
            messagebox.showinfo("취소", "작업이 취소되었습니다. (폴더 미선택)")
            return

        self.run_button.configure(state="disabled")
        self.add_row_button.configure(state="disabled")
        
        # Start threading
        thread = threading.Thread(target=self.process_tasks_thread, args=(tasks, base_output_dir))
        thread.daemon = True
        thread.start()

    def process_tasks_thread(self, tasks, base_output_dir=None):
        total = len(tasks)
        for i, (keyword, url) in enumerate(tasks):
            # Update progress UI
            progress_val = (i) / total
            status_text = f"[{i+1}/{total}] '{keyword}' ({self.current_platform}) 분석 중..."
            self.after(0, lambda p=progress_val, s=status_text: self.update_progress(p, s))

            # Execute analysis depending on platform
            keep_open = (i < total - 1)
            
            target_platform = self.current_platform
            
            if target_platform == "unified":
                content_lower = url.lower()
                keyword_lower = keyword.lower()
                
                if "naver.me" in content_lower or "naver.com" in content_lower or "네이버" in keyword_lower:
                    active_platform = "naver"
                elif "coupang.com" in content_lower or "coupang" in content_lower or "쿠팡" in keyword_lower or ("<html" in content_lower and "coupang" in content_lower):
                    active_platform = "coupang"
                elif "myrealtrip.com" in content_lower or "myrealt.rip" in content_lower or "마리트" in keyword_lower or ("<html" in content_lower and "myrealtrip" in content_lower):
                    active_platform = "marit"
                elif "<html" in content_lower:
                    if "coupang" in content_lower: active_platform = "coupang"
                    elif "myreal" in content_lower: active_platform = "marit"
                    else: active_platform = "naver"
                else:
                    active_platform = "naver"
                    
                platform_dir_name = "통합"
            else:
                active_platform = target_platform
                if active_platform == "naver": platform_dir_name = "네이버"
                elif active_platform == "coupang": platform_dir_name = "쿠팡"
                elif active_platform == "marit": platform_dir_name = "마리트"
                elif active_platform == "nblog": platform_dir_name = "N블로그"
                else: platform_dir_name = "통합"
            
            if active_platform == "naver":
                success, message = self.analyzer.analyze_keyword(keyword, url, keep_open=keep_open, base_output_dir=base_output_dir, platform_dir_name=platform_dir_name)
            elif active_platform == "coupang":
                content = url
                try:
                    import coupang
                    if hasattr(coupang, 'CoupangAnalyzer'):
                        if not hasattr(self, 'coupang_analyzer'):
                            self.coupang_analyzer = coupang.CoupangAnalyzer()
                        success, message = self.coupang_analyzer.analyze_keyword(keyword, content, keep_open=keep_open, base_output_dir=base_output_dir, platform_dir_name=platform_dir_name)
                    else:
                        success, message = False, "coupang.py에 CoupangAnalyzer 클래스가 구현되지 않았습니다."
                except ImportError:
                    success, message = False, "coupang.py 로드 실패"
            elif active_platform == "marit":
                try:
                    import marit
                    if hasattr(marit, 'MaritAnalyzer'):
                        if not hasattr(self, 'marit_analyzer'):
                            self.marit_analyzer = marit.MaritAnalyzer()
                        
                        content_to_pass = url
                        try:
                            if len(url) < 1000 and os.path.isfile(url) and url.lower().endswith(".txt"):
                                try:
                                    try:
                                        with open(url, "r", encoding="utf-8") as f:
                                            content_to_pass = f.read()
                                    except UnicodeDecodeError:
                                        with open(url, "r", encoding="cp949") as f:
                                            content_to_pass = f.read()
                                except Exception as e:
                                    print(f"TXT 파일 읽기 오류: {e}")
                        except Exception:
                            pass
                                
                        success, message = self.marit_analyzer.analyze_keyword(keyword, content_to_pass, keep_open=keep_open, base_output_dir=base_output_dir, platform_dir_name=platform_dir_name)
                    else:
                        success, message = False, "marit.py에 MaritAnalyzer 클래스가 구현되지 않았습니다."
                except ImportError:
                    success, message = False, "marit.py 로드 실패"
            elif active_platform == "nblog":
                try:
                    import naver_blog
                    if hasattr(naver_blog, 'NaverBlogAnalyzer'):
                        if not hasattr(self, 'nblog_analyzer'):
                            self.nblog_analyzer = naver_blog.NaverBlogAnalyzer()
                        success, message = self.nblog_analyzer.analyze_keyword(keyword, url, keep_open=keep_open, base_output_dir=base_output_dir, platform_dir_name=platform_dir_name)
                    else:
                        success, message = False, "naver_blog.py에 NaverBlogAnalyzer 클래스가 구현되지 않았습니다."
                except ImportError:
                    success, message = False, "naver_blog.py 로드 실패"
            else:
                success, message = False, "알 수 없는 플랫폼입니다."
            
            # log for debugging
            print(f"Task result: {success}, {message}")

        # Final Update
        self.after(0, lambda: self.update_progress(1.0, f"총 {total} 건의 작업이 완료되었습니다."))
        self.after(0, self.finish_all_tasks)

    def update_progress(self, val, status):
        self.progress_bar.set(val)
        self.progress_status.configure(text=status)

    def finish_all_tasks(self):
        self.run_button.configure(state="normal")
        self.add_row_button.configure(state="normal")
        messagebox.showinfo("완료", "모든 작업이 완료되었습니다.")

if __name__ == "__main__":
    app = BrandConnectApp()
    app.mainloop()