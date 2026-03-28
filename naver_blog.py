import os
import time
import requests
import re
import datetime
import itertools
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class NaverBlogAnalyzer:
    def __init__(self):
        self.driver = None
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://blog.naver.com/",
            "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def setup_driver(self, headless=False):
        if self.driver:
            return self.driver
            
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--start-maximized")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

    def sanitize_filename(self, filename):
        # 1. 개행 문자(\n, \r), 탭(\t) 제거
        clean = re.sub(r'[\r\n\t]', " ", filename)
        # 2. Windows 예약 문자 (\ / : * ? " < > |)를 언더바(_)로 치환
        clean = re.sub(r'[\\/:*?"<>|]', "_", clean)
        # 3. 양끝 공백 제거 및 길이 제한 (보통 200자 내외가 안전)
        return clean.strip()[:200]

    def open_browser(self):
        """수동 로그인용 브라우저 창 띄우기"""
        try:
            self.setup_driver(headless=False)
            self.driver.get("https://nid.naver.com/nidlogin.login")
            return True, "브라우저가 열렸습니다."
        except Exception as e:
            return False, f"브라우저 실행 실패: {str(e)}"

    def start_auto_scraping(self, base_url, down_url, save_dir, keyword=None, image_prefix=None):
        """비로그인 무패스 모드"""
        try:
            self.setup_driver(headless=False)
            return self._execute_scraping_logic(base_url, down_url, save_dir, keyword, image_prefix)
        except Exception as e:
            return False, f"오류 발생: {str(e)}"
        finally:
            self.close_driver()

    def start_manual_scraping(self, base_url, down_url, save_dir, keyword=None, image_prefix=None):
        """수동 로그인 후 크롤링 시작"""
        if not self.driver:
            return False, "브라우저가 열려있지 않습니다."
        try:
            return self._execute_scraping_logic(base_url, down_url, save_dir, keyword, image_prefix)
        except Exception as e:
            return False, f"오류 발생: {str(e)}"
        # 수동 모드에서는 창을 닫지 않음 (사용자 선택)

    def _execute_scraping_logic(self, base_url, down_url, save_dir, keyword=None, image_prefix=None):
        driver = self.driver
        driver.get(down_url)
        time.sleep(3)

        # 이미지 파일명 접두사 설정 (키워드가 있으면 키워드로, 없으면 폴더명이나 기본값)
        if not image_prefix:
            image_prefix = keyword if keyword else "이미지"
        safe_prefix = self.sanitize_filename(image_prefix)

        # 1. '네이버블로그' 메인 폴더 생성 (키워드 있으면 하위 폴더)
        if keyword:
            main_folder = os.path.join(save_dir, "네이버블로그", self.sanitize_filename(keyword))
        else:
            main_folder = os.path.join(save_dir, "네이버블로그")
        os.makedirs(main_folder, exist_ok=True)

        # 2. 게시글 목록 추출
        post_links = []
        
        # 2-1. 만약 down_url 자체가 개별 포스팅 주소라면?
        if "PostView.naver" in down_url or re.search(r'blog\.naver\.com/\w+/\d+', down_url):
            post_links = [down_url]
        else:
            try:
                driver.switch_to.frame("mainFrame")
            except:
                pass

            # 목록에서 글 URL들 수집
            link_elements = driver.find_elements(By.CSS_SELECTOR, "a.tit, a.p_title, .title_text a, a[href*='PostView.naver?blogId=']")
            for el in link_elements:
                href = el.get_attribute("href")
                if href and href not in post_links:
                    post_links.append(href)

            if not post_links:
                link_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/PostView.naver']")
                for el in link_elements:
                    href = el.get_attribute("href")
                    if href and href not in post_links:
                        post_links.append(href)

        print(f"발견된 게시글 수: {len(post_links)}")
        
        success_count = 0
        for i, post_url in enumerate(post_links):
            try:
                print(f"[{i+1}/{len(post_links)}] 분석 중: {post_url}")
                driver.get(post_url)
                time.sleep(2)
                
                # iframe 전환
                driver.switch_to.default_content()
                
                # 만약 이미 PostView (이미 iframe 안의 주소)라면 프레임 전환을 건너뜜
                if "PostView.naver" not in post_url:
                    try:
                        WebDriverWait(driver, 5).until(EC.frame_to_be_available_and_switch_to_it((By.ID, "mainFrame")))
                    except:
                        print("iframe(mainFrame)을 찾을 수 없거나 이미 전환된 상태일 수 있습니다.")

                # 3. 데이터 추출
                # 제목
                title = "제목없음"
                try:
                    # 제목 선택자 보강 (se-fs-, se-ff-, se-title-text 등)
                    title_el = driver.find_element(By.CSS_SELECTOR, ".se-title-text, .se-fs-, .se-ff-, .se_title h3, .htext span, h3.title, .p_title")
                    title = title_el.text.strip()
                    if not title:
                        title = title_el.get_attribute("innerText").strip()
                    
                    # [출처] 등의 접두사/접미사 제거 ([ 문자 이전까지만 사용)
                    if " [" in title:
                        title = title.split(" [")[0].strip()
                except:
                    pass
                
                safe_title = self.sanitize_filename(title)
                item_folder = os.path.join(main_folder, safe_title)
                os.makedirs(item_folder, exist_ok=True)

                # 본문 파싱 (순차적)
                # 현대적인 Smart Editor ONE 구조 기준
                post_content = ""
                img_count = 0
                
                # 본문 전체 컨테이너
                container = driver.find_elements(By.CSS_SELECTOR, ".se-main-container, #postViewArea")
                if container:
                    # 컨테이너 내부의 모든 자식 요소를 순회하여 순서 유지
                    # 텍스트 섹션: .se-module-text, 이미지 섹션: .se-module-image
                    # 또는 그냥 모든 자식 요소를 순서대로 확인
                    elements = container[0].find_elements(By.CSS_SELECTOR, ".se-component")
                    if not elements: # 구버전 에디터
                        elements = container[0].find_elements(By.XPATH, "./*")

                    for el in elements:
                        # 텍스트 추출
                        text_modules = el.find_elements(By.CSS_SELECTOR, ".se-module-text")
                        for tm in text_modules:
                            txt = tm.text.strip()
                            if txt:
                                post_content += txt + "\n"

                        # 이미지 추출
                        img_modules = el.find_elements(By.CSS_SELECTOR, "img.se-image-resource, img.se-inline-image-resource, .se-module-image img, #postViewArea img")
                        for im in img_modules:
                            # 원본 화질을 위해 data-lazy-src 또는 data-src 우선 확인
                            src = im.get_attribute("data-lazy-src")
                            if not src:
                                src = im.get_attribute("data-src")
                            if not src:
                                src = im.get_attribute("src")
                                
                            if src and "data:image" not in src:
                                img_count += 1
                                img_name = f"이미지_{img_count}.jpg"
                                img_path = os.path.join(item_folder, img_name)
                                
                                # 이미지 다운로드
                                if self.download_image(src, img_path):
                                    post_content += f"\n[{img_name}]\n"
                
                # 4. 텍스트 파일 저장
                char_count_no_space = len(re.sub(r'\s+', '', post_content))
                
                # 키워드 사용 횟수 측정
                kw_stats = []
                check_kw = image_prefix if image_prefix else keyword
                if check_kw:
                    results = set()
                    results.add(check_kw)
                    # 4글자 2+2 분할 규칙
                    if len(check_kw) == 4 and ' ' not in check_kw:
                        p1, p2 = check_kw[:2], check_kw[2:]
                        results.add(p1)
                        results.add(p2)
                        results.add(f"{p1} {p2}")
                    
                    # 공백 포함 단어 조합 규칙
                    if ' ' in check_kw:
                        words = check_kw.split()
                        for r in range(1, len(words) + 1):
                            for subset in itertools.combinations(words, r):
                                results.add(" ".join(subset))
                                results.add("".join(subset))
                    
                    sorted_kws = sorted(list(results), key=len, reverse=True)
                    for k in sorted_kws:
                        count = post_content.count(k)
                        kw_stats.append(f"{k} : {count}회")

                with open(os.path.join(item_folder, "본문.txt"), "w", encoding="utf-8") as f:
                    f.write(f"제목: {title}\n")
                    f.write(f"URL: {post_url}\n")
                    f.write(f"이미지 장수 : {img_count}장\n")
                    f.write(f"글자수 공백미포함 : {char_count_no_space}자\n")
                    if kw_stats:
                        f.write("-" * 10 + " 키워드 사용횟수 " + "-" * 10 + "\n")
                        f.write("\n".join(kw_stats) + "\n")
                    f.write("-" * 30 + "\n\n")
                    f.write(post_content)
                
                success_count += 1
            except Exception as e:
                print(f"글 처리 중 오류 ({post_url}): {e}")
                continue

        return True, f"총 {len(post_links)}개의 글 중 {success_count}개를 성공적으로 백업했습니다."

    def download_image(self, url, filepath):
        try:
            # 네이버 블로그 원본 이미지 추출 전략
            # 1. 파라미터가 있는 경우 (type=w966 등)를 type=w2 (원본)으로 교체 시도
            if '?' in url:
                base_url = url.split('?')[0]
                # type=w2 는 네이버 포스트/블로그에서 원본 화질을 불러올 때 주로 사용됨
                original_url = f"{base_url}?type=w2"
            else:
                original_url = f"{url}?type=w2"
            
            # 우선 w2 파라미터로 시도
            res = requests.get(original_url, headers=self.headers, timeout=15)
            
            # 만약 w2가 실패하거나 너무 작으면 파라미터 제거 버전 시도
            if res.status_code != 200 or len(res.content) < 10000:
                clean_url = url.split('?')[0]
                res = requests.get(clean_url, headers=self.headers, timeout=15)
                
            # 그래도 실패하면 원본 url 그대로 시도
            if res.status_code != 200:
                res = requests.get(url, headers=self.headers, timeout=15)
                
            if res.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(res.content)
                print(f"이미지 다운로드 성공: {len(res.content)} bytes")
                return True
            
        except Exception as e:
            print(f"이미지 다운로드 실패 ({url}): {e}")
        return False

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None

    # 구버전 API 호환성 유지용 (main.py에서 platform dispatcher가 부를 수 있음)
    def analyze_keyword(self, keyword, url, keep_open=False, base_output_dir=None, platform_dir_name="N블로그"):
        """기본 통합 분석 (비로그인 모드로 동작)"""
        return self.start_auto_scraping(url, url, base_output_dir)
