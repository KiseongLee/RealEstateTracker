# your_project_directory/src/external_scripts/collect_complex_details.py
import requests
import json
import pprint # 디버깅용, 실제로는 제거 가능
import time # API 호출 간격 제어 등에 필요
import sys
import os

def get_config_from_env():
    """
    환경 변수에서 Header와 Cookie 정보를 가져와 파싱합니다.
    실패 시 기본값으로 빈 딕셔너리를 반환합니다.
    """
    headers_json_str = os.environ.get('NAVER_API_ALL_HEADERS_JSON')
    cookies_json_str = os.environ.get('NAVER_API_COOKIES_JSON')

    parsed_headers = {}
    if headers_json_str:
        try:
            parsed_headers = json.loads(headers_json_str)
            if not isinstance(parsed_headers, dict):
                print("Warning (collect_complex_details): NAVER_API_ALL_HEADERS_JSON is not a valid JSON dictionary. Using empty headers.", file=sys.stderr)
                parsed_headers = {}
        except json.JSONDecodeError as e:
            print(f"Warning (collect_complex_details): Failed to parse NAVER_API_ALL_HEADERS_JSON: {e}. Using empty headers.", file=sys.stderr)
            parsed_headers = {}
    else:
        print("Warning (collect_complex_details): NAVER_API_ALL_HEADERS_JSON environment variable not found. Using empty headers.", file=sys.stderr)

    parsed_cookies = {}
    if cookies_json_str:
        try:
            parsed_cookies = json.loads(cookies_json_str)
            if not isinstance(parsed_cookies, dict):
                print("Warning (collect_complex_details): NAVER_API_COOKIES_JSON is not a valid JSON dictionary. Using empty cookies.", file=sys.stderr)
                parsed_cookies = {}
        except json.JSONDecodeError as e:
            print(f"Warning (collect_complex_details): Failed to parse NAVER_API_COOKIES_JSON: {e}. Using empty cookies.", file=sys.stderr)
            parsed_cookies = {}
    else:
        print("Warning (collect_complex_details): NAVER_API_COOKIES_JSON environment variable not found. Using empty cookies.", file=sys.stderr)
        
    return parsed_headers, parsed_cookies

# fetch_complex_details 함수 시그니처 변경: headers_env, cookies_env 인자 추가
def fetch_complex_details(complex_no, page, headers_env, cookies_env):
    """주어진 단지 번호(complex_no)와 페이지 번호로 매물 상세 정보를 가져옵니다."""
    detail_url = f'https://new.land.naver.com/api/articles/complex/{complex_no}'
    params = {
        'realEstateType': 'APT:JGC:PRE:ABYG', 
        'tradeType': '', 'tag': '::::::::', 'rentPriceMin': 0, 'rentPriceMax': 900000000,
        'priceMin': 0, 'priceMax': 900000000, 'areaMin': 0, 'areaMax': 900000000,
        'oldBuildYears': '', 'recentlyBuildYears': '', 'minHouseHoldCount': '', 
        'maxHouseHoldCount': '', 'showArticle': 'false', 'sameAddressGroup': 'true',
        'minMaintenanceCost': '', 'maxMaintenanceCost': '', 'priceType': 'RETAIL',
        'directions': '', 'page': page, 'complexNo': complex_no,
        'buildingNos': '', 'areaNos': '', 'type': 'list', 'order': 'prc'
    }

    try:
        # 함수 호출 시 전달받은 headers_env, cookies_env 사용
        response = requests.get(detail_url, params=params, cookies=cookies_env, headers=headers_env, timeout=15)
        response.raise_for_status() 

        response_data = response.json()
        article_list = response_data.get("articleList", [])
        is_more_data = response_data.get("isMoreData", False)

        print(f"Fetched page {page} for complex {complex_no}. Articles: {len(article_list)}, More data: {is_more_data}", file=sys.stderr)
        return article_list, is_more_data

    except requests.exceptions.RequestException as e:
        print(f"Error fetching details for complex {complex_no}, page {page}: {e}", file=sys.stderr)
        return [], False
    except json.JSONDecodeError:
        # 응답 내용이 너무 길 수 있으므로, 처음 200자만 미리보기로 출력
        response_text_preview = response.text[:200] + "..." if len(response.text) > 200 else response.text
        print(f"Error parsing JSON response for complex {complex_no}, page {page}. Response preview: {response_text_preview}", file=sys.stderr)
        return [], False
    except Exception as e:
        print(f"An unexpected error in fetch_complex_details for complex {complex_no}, page {page}: {e}", file=sys.stderr)
        return [], False

if __name__ == "__main__":
    project_root_cwd = os.getcwd()
    print(f"Executing collect_complex_details.py from CWD: {project_root_cwd}", file=sys.stderr)

    # 환경 변수에서 Header와 Cookie 정보 가져오기
    headers_from_env, cookies_from_env = get_config_from_env()

    if not headers_from_env or not cookies_from_env:
        print("Warning (collect_complex_details): Headers or Cookies could not be loaded from environment variables.", file=sys.stderr)
        print("API requests to Naver Land might fail or be incomplete.", file=sys.stderr)
        # 여기서 스크립트를 종료할 수도 있지만, 일단 진행하도록 둡니다.
        # sys.exit(1) # 필요시 주석 해제

    output_dir = 'output'
    input_filename = 'all_marker_info.json'
    output_filename = 'complex_details_by_district.json'

    input_filepath = os.path.join(output_dir, input_filename)
    input_abs_filepath = os.path.abspath(input_filepath) # 로그용
    output_filepath = os.path.join(output_dir, output_filename)
    output_abs_filepath = os.path.abspath(output_filepath) # 로그용

    print(f"Attempting to read marker info from: {input_abs_filepath} (relative: {input_filepath})", file=sys.stderr)
    if not os.path.exists(input_filepath): # 상대 경로로 파일 존재 확인
        print(f"Error: Input file '{input_filepath}' (abs: '{input_abs_filepath}') not found. Run fetch_marker_ids.py first.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_filepath, 'r', encoding='utf-8') as file: # 상대 경로 사용
            all_markers_data = json.load(file)
    except Exception as e:
        print(f"Error reading or parsing input file '{input_filepath}': {e}", file=sys.stderr)
        sys.exit(1)

    if not isinstance(all_markers_data, dict):
        print(f"Error: Expected input from '{input_filepath}' to be a dict, but got {type(all_markers_data)}.", file=sys.stderr)
        sys.exit(1)

    complex_details_by_district_output = {} # 최종 출력용
    total_articles_collected = 0
    total_complexes_processed = 0

    for area_name_loop, markers_list_loop in all_markers_data.items(): # 변수명 충돌 방지
        if not isinstance(markers_list_loop, list):
            print(f"Warning: Skipping area '{area_name_loop}', marker data not a list (type: {type(markers_list_loop)}).", file=sys.stderr)
            continue

        print(f"Collecting details for area: {area_name_loop}", file=sys.stderr)
        area_complex_details_list = [] # 현재 지역 상세 정보 리스트, 변수명 변경

        for marker_info_loop in markers_list_loop: # 변수명 충돌 방지
            if not isinstance(marker_info_loop, dict):
                print(f"Warning: Skipping invalid marker (not a dict) in '{area_name_loop}': {marker_info_loop}", file=sys.stderr)
                continue

            complex_no_loop = marker_info_loop.get('markerId') # 변수명 변경
            latitude_loop = marker_info_loop.get('latitude') # 변수명 변경
            longitude_loop = marker_info_loop.get('longitude') # 변수명 변경
            completionYearMonth_loop = marker_info_loop.get('completionYearMonth', '') # 변수명 변경
            totalHouseholdCount_loop = marker_info_loop.get('totalHouseholdCount', 0) # 변수명 변경
            divisionName_loop = marker_info_loop.get('divisionName', '') # 변수명 변경
            cortarName_loop = marker_info_loop.get('cortarName', '') # 변수명 변경
            complexName_loop = marker_info_loop.get('complexName', '') # 변수명 변경

            if not complex_no_loop:
                print(f"Warning: Skipping marker due to missing 'markerId' in '{area_name_loop}': {marker_info_loop}", file=sys.stderr)
                continue

            print(f"Processing complex: {complexName_loop} ({complex_no_loop}) in {area_name_loop}...", file=sys.stderr)
            total_complexes_processed += 1
            complex_article_count_loop = 0 # 변수명 변경
            page_loop = 1 # 변수명 변경

            while True:
                # fetch_complex_details 호출 시 환경 변수에서 가져온 headers와 cookies 전달
                details_loop, has_more_data_loop = fetch_complex_details(
                    complex_no_loop, page_loop, headers_from_env, cookies_from_env
                ) # 변수명 변경

                if details_loop:
                    for detail_item in details_loop: # 변수명 변경
                        if isinstance(detail_item, dict):
                            detail_item['markerId'] = complex_no_loop
                            detail_item['latitude'] = latitude_loop
                            detail_item['longitude'] = longitude_loop
                            detail_item['completionYearMonth'] = completionYearMonth_loop
                            detail_item['totalHouseholdCount'] = totalHouseholdCount_loop
                            detail_item['divisionName'] = divisionName_loop
                            detail_item['cortarName'] = cortarName_loop
                        else:
                            print(f"Warning: Non-dict item in articleList for {complex_no_loop}, page {page_loop}: {detail_item}", file=sys.stderr)
                    area_complex_details_list.extend(details_loop)
                    complex_article_count_loop += len(details_loop)

                if not has_more_data_loop or not details_loop:
                    if page_loop == 1 and not details_loop:
                        print(f"No articles found for complex {complex_no_loop} ({complexName_loop}).", file=sys.stderr)
                    else:
                        print(f"Finished fetching for complex {complex_no_loop}. Articles: {complex_article_count_loop}. Last page: {page_loop}.", file=sys.stderr)
                    break 
                page_loop += 1
                if page_loop > 50: # 최대 페이지 제한
                    print(f"Warning: Reached page limit (50) for complex {complex_no_loop}. Stopping.", file=sys.stderr)
                    break
                time.sleep(0.05) # API 요청 간 짧은 지연 (필요시 조절)

        if area_complex_details_list:
            complex_details_by_district_output[area_name_loop] = area_complex_details_list
            total_articles_collected += len(area_complex_details_list)
            print(f"Finished for area: {area_name_loop}. Total articles: {len(area_complex_details_list)}", file=sys.stderr)
        else:
            print(f"No details collected for area: {area_name_loop}.", file=sys.stderr)

    if complex_details_by_district_output:
        print(f"Saving {total_articles_collected} articles from {total_complexes_processed} complexes", file=sys.stderr)
        print(f"Writing to: {output_abs_filepath} (relative: {output_filepath})", file=sys.stderr)
        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, 'w', encoding='utf-8') as file:
                json.dump(complex_details_by_district_output, file, ensure_ascii=False, indent=4)
            print(f"Complex details saved to '{output_abs_filepath}'", file=sys.stderr)
        except Exception as e:
            print(f"Error writing output file '{output_filepath}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("No complex details collected overall. Initializing/Clearing JSON file.", file=sys.stderr)
        try:
            # 기존 파일이 있으면 빈 JSON 객체로 덮어쓰기
            os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, 'w', encoding='utf-8') as file:
                json.dump({}, file, ensure_ascii=False, indent=4)
            print(f"Initialized/Cleared JSON file at '{output_abs_filepath}'.", file=sys.stderr)
        except Exception as e:
            print(f"Error initializing JSON file '{output_filepath}': {e}", file=sys.stderr)
            sys.exit(1)
        
        # 처리 시도는 했으나 결과가 없는 경우 (복잡한 단지는 처리했으나 매물이 하나도 없음)
        if total_articles_collected == 0 and total_complexes_processed > 0:
            sys.exit(1)  # 실패로 간주
        else:
            sys.exit(0)  # 처리할 데이터 자체가 없었을 경우 정상 종료

    print("Script finished successfully.", file=sys.stderr)
    sys.exit(0)
