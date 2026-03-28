import os
import time
import requests
from bs4 import BeautifulSoup
import re

class CoupangAnalyzer:
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

    def analyze_keyword(self, keyword, html_content, keep_open=False, base_output_dir=None, platform_dir_name="쿠팡"):
        """
        쿠팡 전용 핵심 분석 로직 (HTML 직접 파싱)
        """
        try:
            print(f"====================================")
            print(f"[쿠팡 로직 실행] 키워드: {keyword}")
            print(f"====================================")
            
            # 1. 디렉토리 생성 (선택한디렉토리/플랫폼명/키워드명 또는 현재디렉토리/플랫폼명/키워드명)
            safe_keyword = self.sanitize_filename(keyword)
            root_dir = base_output_dir if base_output_dir else os.getcwd()
            base_dir = os.path.join(root_dir, platform_dir_name, safe_keyword)
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
                print(f"디렉토리 생성 완료: {base_dir}")
                
            soup = BeautifulSoup(html_content, 'lxml')
            
            result_data = []
            result_data.append(f"[{keyword} 쿠팡 분석 결과]\n")
            
            # --- 업체명 추출 ---
            brand_div = soup.find('div', class_=lambda c: c and 'twc-text-[#346AFF]' in c)
            brand_name = brand_div.get_text(strip=True) if brand_div else "알 수 없음"
            result_data.append(f"1. 업체명:\n{brand_name}\n")
            
            # --- 상품가 추출 ---
            raw_prices = []
            price_container = soup.find('div', class_=lambda c: c and 'price-container' in c)
            if price_container:
                amount_divs = price_container.find_all('div', class_=lambda c: c and 'price-amount' in c and '!twc-leading-[24px]' in c)
                for amount in amount_divs:
                    text = amount.get_text(strip=True)
                    if text:
                        # 숫자만 추출해서 int로 변환 비교용 저장
                        num_str = re.sub(r'[^0-9]', '', text)
                        if num_str:
                            raw_prices.append((int(num_str), text))
            
            result_data.append("2. 상품가:")
            if raw_prices:
                # 중복 제거 (금액 기준)
                unique_prices = []
                seen = set()
                for p in raw_prices:
                    if p[0] not in seen:
                        seen.add(p[0])
                        unique_prices.append(p)
                
                # 금액 큰 순서대로 정렬 내림차순
                unique_prices.sort(key=lambda x: x[0], reverse=True)
                
                if len(unique_prices) == 1:
                    result_data.append(f"일반회원가 : {unique_prices[0][1]}")
                elif len(unique_prices) >= 2:
                    result_data.append(f"일반회원가 : {unique_prices[0][1]}")
                    result_data.append(f"와우회원가 : {unique_prices[-1][1]}")
            else:
                result_data.append("게시된 가격 정보를 찾을 수 없습니다.")
            result_data.append("")
                
            # --- 이미지 추출 부분 ---
            img_container = soup.find('div', class_='product-image')
            image_urls = []
            if img_container:
                # 썸네일 리스트에서 이미지 추출
                thumb_imgs = img_container.find_all('img', class_='twc-w-[70px]')
                for img in thumb_imgs:
                    src = img.get('src')
                    if src:
                        image_urls.append(src)
                        
            # 중복 제거 (순서 유지)
            image_urls = list(dict.fromkeys(image_urls))
            
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
            
            # --- 베스트 상품평 추출 ---
            reviews = []
            # 'break-all', 'twc-bg-white', 'translate="no"' 속성을 가진 span 태그 찾기
            review_spans = soup.find_all('span', {'class': 'twc-bg-white', 'translate': 'no'})
            for span in review_spans:
                # text 추출 시 <br> 등을 띄어쓰기로 변경
                text = span.get_text(separator=' ', strip=True)
                if text:
                    reviews.append(text)
            
            # 최대 4개까지만
            reviews = reviews[:4]
            
            result_data.append("3. 상품평 (베스트순 상위 4개):")
            for idx, review in enumerate(reviews):
                result_data.append(f"[{idx+1}]\n{review}\n")

            # --- 결과 파일 저장 ---
            result_filepath = os.path.join(base_dir, f"{safe_keyword}.txt")
            with open(result_filepath, 'w', encoding='utf-8') as f:
                f.write("\n".join(result_data))
                
            print(f"텍스트 결과 저장 완료: {result_filepath}")
            
            return True, f"쿠팡 '{keyword}' 분석 및 저장 완료"
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"오류 발생: {str(e)}"
