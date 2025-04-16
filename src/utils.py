# src/utils.py
import pandas as pd
import re
import numpy as np
from datetime import datetime

def format_eok(val):
    """
    숫자를 '억'과 '천만' 단위 문자열로 변환합니다.
    """
    if pd.isna(val):
        return ""

    sign = "-" if val < 0 else ""
    abs_val = abs(val)

    eok = int(abs_val // 100_000_000)
    remainder = int((abs_val % 100_000_000) // 10_000)

    if eok == 0:
        return f"{sign}{remainder:,}" if remainder != 0 else "0"
    else:
        return f"{sign}{eok}억 {remainder:,}" if remainder > 0 else f"{sign}{eok}억"

def convert_price_to_number(price_str):
    """
    가격 문자열 ('1억 5,000', '5000' 등)을 숫자(정수)로 변환합니다.
    """
    if pd.isnull(price_str):
        return 0

    if isinstance(price_str, (float, int)):
        return int(price_str)

    price_str = str(price_str).replace(',', '').replace(' ', '').strip()
    if price_str.lower() == 'nan':
        return 0

    total = 0
    eok_part = 0
    man_part = 0

    if '억' in price_str:
        parts = price_str.split('억')
        # 억 앞부분이 숫자인지 확인
        eok_str = parts[0].replace('-', '') # 음수 부호 임시 제거
        if eok_str.isdigit():
            eok_part = int(parts[0]) * 100_000_000
        # 억 뒷부분이 있고, 숫자인지 확인
        if len(parts) > 1 and parts[1]:
            man_str = parts[1].replace('-', '') # 음수 부호 임시 제거
            if man_str.isdigit():
                 man_part = int(parts[1]) * 10_000
            # 숫자가 아닌 경우 (예: '억') 무시
    elif price_str.replace('-', '').isdigit(): # 음수 포함한 숫자 확인
        man_part = int(price_str) * 10_000 # '억' 없이 숫자만 있으면 만 단위로 처리 (기존 로직 유지)
    else:
        # 처리할 수 없는 형식
        return 0

    # 원래 부호 적용
    total = eok_part + man_part
    # price_str에 '-'가 있었으면 음수로 만듦 (eok_part, man_part 계산 시 부호 제거했으므로)
    if '-' in str(price_str) and total > 0:
        total = -total

    return total


def extract_numeric_area(area_str):
    """
    공급면적 문자열에서 숫자(float)만 추출합니다.
    """
    match = re.search(r'\d+(\.\d+)?', str(area_str))
    if match:
        return float(match.group())
    return None

def extract_floor(floor_info):
    """
    층수 문자열 ('5/15', '저', '3')에서 해당 층 정보만 추출합니다.
    """
    if pd.isna(floor_info):
        return None
    floor_info_str = str(floor_info).strip()
    if '/' in floor_info_str:
        return floor_info_str.split('/')[0].strip()
    else:
        return floor_info_str

def create_article_url(articleNo, markerId, latitude, longitude):
    """
    네이버 부동산 매물 상세 페이지 URL을 생성합니다.
    """
    if pd.isna(articleNo) or pd.isna(markerId) or pd.isna(latitude) or pd.isna(longitude):
        return None
    # articleNo와 markerId를 정수 또는 문자열로 변환 (입력 타입 보장)
    articleNo_str = str(int(articleNo)) if pd.notna(articleNo) else ''
    markerId_str = str(int(markerId)) if pd.notna(markerId) else ''

    if not articleNo_str or not markerId_str:
        return None

    base_url = f"https://new.land.naver.com/complexes/{markerId_str}"
    params = f"?ms={latitude},{longitude},15&a=APT:PRE&b=A1&e=RETAIL&l=300&ad=true&articleNo={articleNo_str}"
    return base_url + params


def shorten_text(text, max_length=50):
    """
    긴 텍스트를 지정된 길이로 줄이고 '...'을 추가합니다.
    """
    text_str = str(text)
    return text_str if len(text_str) <= max_length else text_str[:max_length] + '...'

def get_current_date_str():
    """
    현재 날짜를 'YYYYMMDD' 형식의 문자열로 반환합니다.
    """
    return datetime.now().strftime('%Y%m%d')