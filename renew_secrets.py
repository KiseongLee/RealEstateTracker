import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

# --- 💡 사용자 설정이 필요한 부분 💡 ---

# 1. 위에서 압축 해제한 크롬 드라이버 파일의 전체 경로를 입력
CHROME_DRIVER_PATH = "/Users/kiseong/Desktop/chromedriver/chromedriver-mac-arm64/chromedriver"

# 2. 생성될 config_secrets.json 파일의 경로를 지정 (현재 폴더에 생성)
CONFIG_FILE_PATH = "config_secrets.json"

# 3. 이전에 성공했던 'Authorization' 헤더 값을 여기에 붙여넣으세요.
#    이 값은 유효기간이 매우 길기 때문에, 쿠키처럼 매번 갱신할 필요는 없습니다.
#    만료되었을 때만 이 스크립트의 이 부분만 수정해주면 됩니다.
AUTHORIZATION_TOKEN = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6IlJFQUxFU1RBVEUiLCJpYXQiOjE3MzgxMTY0MTIsImV4cCI6MTczODEyNzIxMn0.263YfqLpN2WVVxIER-CptxgLIetj9mPgcj7rIUPKkrU" # "Bearer " 부분을 포함한 전체 토큰

# --- 사용자 설정 끝 ---


def renew_naver_auth():
    """셀레니움을 이용해 네이버 부동산에 접속하고 최신 쿠키를 가져와 파일로 저장합니다."""
    print("셀레니움을 사용하여 네이버 부동산 인증 값 갱신을 시작합니다...")

    # 화면 없는 '헤드리스' 모드 등 크롬 옵션 설정
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36")

    # 웹 드라이버 서비스 설정
    service = Service(executable_path=CHROME_DRIVER_PATH)
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # 네이버 부동산 접속
        print("네이버 부동산에 접속합니다...")
        driver.get("https://new.land.naver.com")

        # 페이지가 로드되고 쿠키가 설정될 시간을 충분히 줍니다.
        print("쿠키가 생성될 때까지 10초 대기합니다...")
        time.sleep(10)

        # 브라우저에서 쿠키 가져오기
        cookies = driver.get_cookies()
        print(f"총 {len(cookies)}개의 쿠키를 가져왔습니다.")

        # `pip`이 사용할 수 있는 {이름: 값} 형태의 딕셔너리로 가공
        formatted_cookies = {cookie['name']: cookie['value'] for cookie in cookies}

        # 최종 설정 파일 내용 생성
        config_data = {
            "headers": {
                "authorization": AUTHORIZATION_TOKEN,
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.0.0 Safari/537.36",
                "referer": "https://new.land.naver.com/"
            },
            "cookies": formatted_cookies
        }

        # 파일에 예쁘게 저장
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)

        print(f"\n성공! 최신 인증 정보가 '{CONFIG_FILE_PATH}' 파일에 저장되었습니다.")

    except Exception as e:
        print(f"\n오류 발생: {e}")
    finally:
        # 브라우저 종료
        driver.quit()
        print("스크립트 실행을 마쳤습니다.")

if __name__ == "__main__":
    renew_naver_auth()