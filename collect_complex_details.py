# collect_complex_details.py
import requests
import json
import pprint
from config import cookies, headers  # config.py에서 쿠키와 헤더 가져오기

# Load marker information from the JSON file

# all_marker_info.json 파일에서 마커 정보 로드
with open('all_marker_info.json', 'r', encoding='utf-8') as file:
    all_markers_data = json.load(file)

def fetch_complex_details(complex_no, page):
    detail_url = f'https://new.land.naver.com/api/articles/complex/{complex_no}?realEstateType=APT%3AABYG%3AJGC%3APRE&tradeType=&tag=%3A%3A%3A%3A%3A%3A%3A%3A&rentPriceMin=0&rentPriceMax=900000000&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000&oldBuildYears=&recentlyBuildYears=&minHouseHoldCount=&maxHouseHoldCount=&showArticle=false&sameAddressGroup=true&minMaintenanceCost=&maxMaintenanceCost=&priceType=RETAIL&directions=&page={page}&complexNo={complex_no}&buildingNos=&areaNos=&type=list&order=prc'
    response = requests.get(detail_url, cookies=cookies, headers=headers)
    if response.status_code == 200:
        return response.json().get("articleList", [])
    else:
        return []

if __name__ == "__main__":
    complex_details_by_district = {}

    # 각 지역에 대해 단지 상세 정보 수집
    for area_name, markers_list in all_markers_data.items():
        area_complex_details = []

        for marker_info in markers_list:
            complex_no = marker_info['markerId']  # complexNo는 markerId입니다.
            latitude = marker_info['latitude']
            longitude = marker_info['longitude']

            for page in range(1, 1000):  # 필요한 경우 최대 페이지 수 조정
                details = fetch_complex_details(complex_no, page)
                if details:
                    # 각 상세 정보에 markerId, latitude, longitude 추가
                    for detail in details:
                        detail['markerId'] = complex_no  # markerId 추가
                        detail['latitude'] = latitude     # latitude 추가
                        detail['longitude'] = longitude   # longitude 추가
                    area_complex_details.extend(details)
                    print(f"Successfully retrieved data for complex {complex_no}, area {area_name}, page {page}. Number of articles: {len(details)}")
                else:
                    print(f"No more articles for complex {complex_no} at page {page}.")
                    break  # 다음 페이지에 데이터가 없으면 반복 종료

        complex_details_by_district[area_name] = area_complex_details
        print(f"Details collected for area: {area_name}")

    # 결과를 JSON 파일로 저장
    with open('complex_details_by_district.json', 'w', encoding='utf-8') as file:
        json.dump(complex_details_by_district, file, ensure_ascii=False, indent=4)

    print("Complex details have been collected and saved to complex_details_by_district.json")