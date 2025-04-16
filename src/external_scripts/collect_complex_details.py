import requests
import json
import pprint
import time # time 모듈 임포트 (API 호출 간격 제어 등에 필요할 수 있음)
import sys
import os

# --- ▼▼▼ config 임포트 수정 (cookies, headers만) ▼▼▼ ---
# config.py는 src/ 안에 있다고 가정
try:
    # 기본 실행 경로 (data_handling.py에서 실행될 때)
    from ..config import cookies, headers
except ImportError:
    # 스크립트를 직접 실행하는 경우 등 예외 상황 처리
    print("Warning: Relative import for config failed. Attempting via sys.path.", file=sys.stderr)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    project_root = os.path.dirname(src_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    try:
        from src.config import cookies, headers
        print("Successfully imported cookies, headers from config via sys.path.")
    except ImportError:
        print("\nCritical Error: Could not import 'cookies' and 'headers' from config.", file=sys.stderr)
        print("Ensure 'config.py' exists in 'src/' and contains cookies, headers.", file=sys.stderr)
        sys.exit(1)
# --- ▲▲▲ config 임포트 수정 완료 ▲▲▲ ---

def fetch_complex_details(complex_no, page):
    """주어진 단지 번호(complex_no)와 페이지 번호로 매물 상세 정보를 가져옵니다."""
    # API 엔드포인트 URL 구성
    detail_url = f'https://new.land.naver.com/api/articles/complex/{complex_no}'
    params = {
        'realEstateType': 'APT:ABYG:JGC:PRE', # 아파트, 주상복합, 재건축, 분양권 등 포함 가능성 (필요시 조정)
        'tradeType': '', # 거래 유형 필터 없음 (매매, 전세, 월세 모두 포함)
        'tag': '::::::::', # 태그 필터 없음
        'rentPriceMin': 0,
        'rentPriceMax': 900000000,
        'priceMin': 0,
        'priceMax': 900000000,
        'areaMin': 0,
        'areaMax': 900000000,
        'oldBuildYears': '',
        'recentlyBuildYears': '',
        'minHouseHoldCount': '', # 세대수 필터 제거 (fetch_marker_ids에서 이미 필터링됨)
        'maxHouseHoldCount': '',
        'showArticle': 'false', # 지도 표시용 매물 정보만? (false 유지)
        'sameAddressGroup': 'true', # 동일 주소 그룹화? (true 유지)
        'minMaintenanceCost': '',
        'maxMaintenanceCost': '',
        'priceType': 'RETAIL', # 가격 유형: 호가
        'directions': '',
        'page': page, # 페이지 번호
        'complexNo': complex_no, # 단지 번호
        'buildingNos': '', # 특정 동 필터 없음
        'areaNos': '', # 특정 면적 필터 없음
        'type': 'list', # 목록 형태 요청
        'order': 'prc' # 가격순 정렬 (prc: 낮은 가격순, 최신순: date, 면적순: area)
    }

    try:
        # config에서 가져온 cookies, headers 사용
        response = requests.get(detail_url, params=params, cookies=cookies, headers=headers, timeout=15) # timeout 설정
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생

        response_data = response.json()
        # 응답 데이터 구조 확인 및 articleList 반환
        # 더보기 버튼 유무 (isMoreData) 키 확인
        article_list = response_data.get("articleList", [])
        is_more_data = response_data.get("isMoreData", False)

        print(f"Fetched page {page} for complex {complex_no}. Articles: {len(article_list)}, More data: {is_more_data}") # 로깅 추가
        return article_list, is_more_data # 매물 리스트와 더보기 유무 반환

    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for complex {complex_no}, page {page}: {e}", file=sys.stderr)
        return [], False # 오류 시 빈 리스트와 더보기 없음 반환
    except json.JSONDecodeError:
        print(f"Error parsing JSON response for complex {complex_no}, page {page}. Response: {response.text}", file=sys.stderr)
        return [], False
    except Exception as e:
        print(f"An unexpected error occurred in fetch_complex_details for complex {complex_no}, page {page}: {e}", file=sys.stderr)
        return [], False

if __name__ == "__main__":
    project_root_cwd = os.getcwd() # 스크립트 실행 시점의 CWD (프로젝트 루트여야 함)
    print(f"Executing collect_complex_details.py from CWD: {project_root_cwd}")

    # --- ▼▼▼ 파일 경로 수정 ▼▼▼ ---
    output_dir = 'output'
    input_filename = 'all_marker_info.json' # 입력 파일 이름
    output_filename = 'complex_details_by_district.json' # 출력 파일 이름

    # 입력/출력 파일의 절대 경로 생성 (CWD 기준)
    input_filepath = os.path.join(output_dir, input_filename)
    input_abs_filepath = os.path.abspath(input_filepath)
    output_filepath = os.path.join(output_dir, output_filename)
    output_abs_filepath = os.path.abspath(output_filepath)
    # --- ▲▲▲ 파일 경로 수정 완료 ▲▲▲ ---

    print(f"Attempting to read marker info from: {input_abs_filepath}")
    # 입력 파일 존재 확인
    if not os.path.exists(input_abs_filepath):
        print(f"Error: Input file '{input_abs_filepath}' not found. Run fetch_marker_ids.py first.", file=sys.stderr)
        sys.exit(1)

    # 입력 파일 로드
    try:
        with open(input_abs_filepath, 'r', encoding='utf-8') as file:
            all_markers_data = json.load(file)
    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON from '{input_abs_filepath}'", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading input file '{input_abs_filepath}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred while reading input file: {e}", file=sys.stderr)
        sys.exit(1)

    # 입력 데이터가 딕셔너리 형태인지 확인
    if not isinstance(all_markers_data, dict):
        print(f"Error: Expected input data from '{input_abs_filepath}' to be a dictionary (key: area_name, value: list of markers), but got {type(all_markers_data)}.", file=sys.stderr)
        sys.exit(1)

    complex_details_by_district = {} # 최종 결과를 저장할 딕셔너리
    total_articles_collected = 0
    total_complexes_processed = 0

    # 각 지역(area_name)별로 마커 정보 처리
    for area_name, markers_list in all_markers_data.items():
        # 해당 지역의 마커 리스트가 list 형태인지 확인
        if not isinstance(markers_list, list):
            print(f"Warning: Skipping area '{area_name}' because marker data is not a list (type: {type(markers_list)}).", file=sys.stderr)
            continue

        print(f"\n--- Collecting details for area: {area_name} ---")
        area_complex_details = [] # 현재 지역의 상세 정보를 담을 리스트

        # 현재 지역의 각 마커(단지) 정보 처리
        for marker_info in markers_list:
            # 마커 정보가 딕셔너리 형태이고, 필요한 키가 있는지 확인
            if not isinstance(marker_info, dict):
                print(f"Warning: Skipping invalid marker info item (not a dict) in area '{area_name}': {marker_info}", file=sys.stderr)
                continue

            complex_no = marker_info.get('markerId') # complexNo는 markerId 사용
            latitude = marker_info.get('latitude')
            longitude = marker_info.get('longitude')
            completionYearMonth = marker_info.get('completionYearMonth', '')
            totalHouseholdCount = marker_info.get('totalHouseholdCount', 0)
            divisionName = marker_info.get('divisionName', '') # fetch_marker_ids 에서 추가됨
            cortarName = marker_info.get('cortarName', '') # fetch_marker_ids 에서 추가됨
            complexName = marker_info.get('complexName', '') # 단지명 (fetch_marker_ids 에서 추가됨)

            # 필수 정보 (complex_no) 누락 시 건너뛰기
            if not complex_no:
                print(f"Warning: Skipping marker due to missing 'markerId' (complex_no) in area '{area_name}': {marker_info}", file=sys.stderr)
                continue

            print(f"Processing complex: {complexName} ({complex_no}) in {area_name}...")
            total_complexes_processed += 1
            complex_article_count = 0
            page = 1
            while True: # 페이지별로 데이터 가져오기 (isMoreData로 종료 제어)
                # API 호출 간격 (선택 사항, 필요 시 조절)
                # time.sleep(0.1)

                details, has_more_data = fetch_complex_details(complex_no, page)

                if details:
                    # 각 매물 상세 정보에 추가 정보 병합
                    for detail in details:
                        # detail이 dict 형태인지 확인 (API 응답 보장 어려움)
                        if isinstance(detail, dict):
                            detail['markerId'] = complex_no
                            detail['latitude'] = latitude
                            detail['longitude'] = longitude
                            detail['completionYearMonth'] = completionYearMonth
                            detail['totalHouseholdCount'] = totalHouseholdCount
                            detail['divisionName'] = divisionName # 구 정보 추가
                            detail['cortarName'] = cortarName # 동 정보 추가
                            # detail['complexName'] = complexName # 필요시 단지명도 추가
                        else:
                            print(f"Warning: Received non-dict item in articleList for complex {complex_no}, page {page}: {detail}", file=sys.stderr)

                    # 현재 지역 리스트에 추가
                    area_complex_details.extend(details)
                    complex_article_count += len(details)

                # 더 이상 데이터가 없거나, details가 비었으면 루프 종료
                if not has_more_data or not details:
                    if page == 1 and not details: # 첫 페이지부터 데이터가 없는 경우
                        print(f"No articles found for complex {complex_no} ({complexName}).")
                    else:
                        print(f"Finished fetching for complex {complex_no}. Total articles: {complex_article_count}. Last page checked: {page}.")
                    break # while 루프 탈출

                page += 1 # 다음 페이지로

                # 안전 장치: 최대 페이지 수 제한 (예: 50페이지 초과 시 경고 및 중단)
                if page > 50: # 과도한 요청 방지
                    print(f"Warning: Reached page limit (50) for complex {complex_no}. Stopping fetch.", file=sys.stderr)
                    break

        # 현재 지역의 상세 정보를 최종 결과 딕셔너리에 저장
        if area_complex_details: # 데이터가 있을 때만 저장
            complex_details_by_district[area_name] = area_complex_details
            total_articles_collected += len(area_complex_details)
            print(f"Finished collecting details for area: {area_name}. Total articles in this area: {len(area_complex_details)}")
        else:
            print(f"No details collected for area: {area_name}.")


    # 최종 결과 파일로 저장
    if complex_details_by_district:
        print(f"\n--- Saving collected details ({total_articles_collected} articles from {total_complexes_processed} complexes) ---")
        print(f"Attempting to write complex details to: {output_abs_filepath}")
        try:
            with open(output_abs_filepath, 'w', encoding='utf-8') as file:
                json.dump(complex_details_by_district, file, ensure_ascii=False, indent=4)
            print(f"Complex details have been collected and saved to '{output_abs_filepath}'")
        except IOError as e:
            print(f"Error writing output file '{output_abs_filepath}': {e}", file=sys.stderr)
            sys.exit(1) # 파일 쓰기 실패 시 종료
        except Exception as e:
            print(f"An unexpected error occurred while writing output file: {e}", file=sys.stderr)
            sys.exit(1) # 기타 쓰기 오류 시 종료
    else:
        print("\nNo complex details were collected overall.", file=sys.stderr)
        # 데이터 수집 실패 시 종료 코드
        if total_articles_collected == 0:
            sys.exit(1)

    # 정상 종료
    print("\nScript finished successfully.")
    sys.exit(0)
