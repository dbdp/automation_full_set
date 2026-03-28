import os
import time
import requests
from bs4 import BeautifulSoup
import re

class MaritAnalyzer:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }

    def sanitize_filename(self, filename):
        return re.sub(r'[\\/*?:"<>|]', "", filename)

    def download_image(self, url, filepath):
        if not url.startswith('http'):
            url = 'https:' + url
        try:
            response = requests.get(url, headers=self.headers, stream=True, timeout=10)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return True
        except Exception as e:
            print(f"이미지 다운로드 실패 ({url}): {e}")
        return False

    def analyze_keyword(self, keyword, url, keep_open=False, base_output_dir=None, platform_dir_name="마리트"):
        """
        마이리얼트립 전용 핵심 분석 로직
        """
        try:
            print(f"====================================")
            print(f"[마이리얼트립 로직 실행] 키워드: {keyword}")
            print(f"====================================")
            
            # 1. 디렉토리 생성 (선택한디렉토리/플랫폼명/키워드명 또는 현재디렉토리/플랫폼명/키워드명)
            safe_keyword = self.sanitize_filename(keyword)
            root_dir = base_output_dir if base_output_dir else os.getcwd()
            base_dir = os.path.join(root_dir, platform_dir_name, safe_keyword)
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
                print(f"디렉토리 생성 완료: {base_dir}")
                
            result_data = []
            result_data.append(f"키워드 : {keyword}")
            
            # 여기서 url 파라미터는 사실상 main.py에서 HTML 소스코드(또는 URL 문자열)을 담아 보낸 것입니다.
            # 만약 HTML코드가 아니라 짧은 일반 URL 문자열이라면, 실제 크롤링 요청을 해야 하지만
            # 현재 사용자 요청은 "TXT불러와서 HTML을 삽입하는 방식"에 맞춘 오프라인 파싱을 전제로 합니다.
            # 따라서 url 변수 자체에 HTML이 들어있다고 가정하고 파싱합니다.
            if url.startswith("http"):
                 result_data.append(f"URL : {url}\n")
                 try:
                     # MyRealTrip often blocks basic requests. Add more realistic headers.
                     custom_headers = {
                         "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                         "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                         "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                         "Referer": "https://www.myrealtrip.com/"
                     }
                     response = requests.get(url, headers=custom_headers, timeout=15)
                     response.raise_for_status()
                     html_content = response.text
                     
                     if "로봇" in html_content or "캡차" in html_content or "captcha" in html_content.lower():
                          print("마이리얼트립 봇 탐지 활성화 됨. 크롤링 차단.")
                 except Exception as req_e:
                     print(f"URL 가져오기 실패: {req_e}")
                     return False, f"마이리얼트립 URL 접속 실패: {req_e}"
            else:
                 result_data.append(f"URL : HTML 직접 입력\n")
                 html_content = url

            soup = BeautifulSoup(html_content, 'lxml')
            
            # --- 가격 추출 ---
            price_span = soup.find('span', class_=lambda c: c and 'e1da6r466' in c and 'css-1z0ugyy' in c)
            price = price_span.get_text(strip=True) if price_span else "찾을 수 없음"
            result_data.append(f"가격 : {price}")
            
            # --- 상품명 추출 ---
            title_h1 = soup.find('h1', class_=lambda c: c and 'e2io25d1' in c and 'css-1q04c8l' in c)
            title = title_h1.get_text(strip=True) if title_h1 else "찾을 수 없음"
            result_data.append(f"상품명 : {title}\n")
            
            # --- 평점 추출 ---
            rating_span = soup.find('span', class_=lambda c: c and 'e10qflf62' in c and 'css-1ja6huh' in c)
            rating = rating_span.get_text(strip=True).replace('·', '').strip() if rating_span else "찾을 수 없음"
            result_data.append(f"{rating}\n")
            
            # --- 후기수 추출 ---
            review_count_span = soup.find('span', class_=lambda c: c and 'e10qflf63' in c and 'css-1mpe80w' in c)
            review_count = review_count_span.get_text(strip=True) if review_count_span else "찾을 수 없음"
            result_data.append(f"후기수 : {review_count}\n")
            
            # --- AI 리뷰 추출 ---
            result_data.append("AI 리뷰")
            ai_title_1 = soup.find('span', class_=lambda c: c and 'e13d2zsp3' in c and 'css-guca6a' in c)
            ai_title_2 = soup.find('span', class_=lambda c: c and 'e13d2zsp4' in c and 'css-gszkl4' in c)
            if ai_title_1 and ai_title_2:
                result_data.append(f"{ai_title_1.get_text(strip=True)} {ai_title_2.get_text(strip=True)}")
            
            ai_items = soup.find_all('div', class_=lambda c: c and 'e1pdsvcv0' in c)
            for item in ai_items:
                item_title_span = item.find('span', class_=lambda c: c and 'e1pdsvcv3' in c)
                item_desc_span = item.find('span', class_=lambda c: c and 'css-h1yn3c' in c)
                
                if item_title_span and item_desc_span:
                    item_title = item_title_span.get_text(strip=True)
                    item_desc = item_desc_span.get_text(separator=' ', strip=True)
                    # "더보기" 텍스트 제거
                    if item_desc.startswith("더보기"):
                        item_desc = item_desc[3:].strip()
                        
                    result_data.append(f"- {item_title}")
                    result_data.append(f"  {item_desc}")
            result_data.append("")

            # --- 실 후기 추출 ---
            result_data.append("실 후기 :")
            real_reviews = soup.find_all('span', class_=lambda c: c and 'ebhs27u1' in c and 'css-w6nxm' in c)
            for rev in real_reviews:
                text = rev.get_text(separator='\n', strip=True)
                if text:
                    result_data.append(text)
                    result_data.append("") # 구분선 공백

            # --- 이미지 추출 및 다운로드 ---
            img_tags = soup.find_all('img', class_=lambda c: c and 'css-y5m0bt' in c)
            image_urls = []
            for img in img_tags:
                src = img.get('src')
                if src:
                    image_urls.append(src)
            
            # 중복 제거 (순서 유지)
            image_urls = list(dict.fromkeys(image_urls))
            
            # 10개까지만 제한
            image_urls = image_urls[:10]
            
            for idx, img_url in enumerate(image_urls):
                ext = ".jpg" # 기본 확장자
                if ".png" in img_url.lower(): ext = ".png"
                elif ".gif" in img_url.lower(): ext = ".gif"
                
                filename = f"{safe_keyword}_{idx+1}{ext}"
                filepath = os.path.join(base_dir, filename)
                
                if self.download_image(img_url, filepath):
                    print(f"이미지 다운로드 완료: {filepath}")
                else:
                    print(f"이미지 다운로드 실패: {filepath}")

            # 텍스트 결과 저장
            result_filepath = os.path.join(base_dir, f"{safe_keyword}.txt")
            with open(result_filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(result_data))
                
            print(f"텍스트 결과 저장 완료: {result_filepath}")
            
            return True, f"마이리얼트립 '{keyword}' 처리 및 파일 생성 완료"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"오류 발생: {str(e)}"
