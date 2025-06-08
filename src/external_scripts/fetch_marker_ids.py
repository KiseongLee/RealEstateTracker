# your_project_directory/src/external_scripts/fetch_marker_ids.py
import requests
import json
import pprint
import time
import sys
import os
# toml 라이브러리 임포트는 더 이상 필요하지 않습니다.

def get_all_configs_from_env():
    """
    환경 변수에서 Header, Cookie, Naver API 키 정보를 가져와 파싱합니다.
    실패 시 적절한 기본값 (주로 빈 딕셔너리 또는 None)을 반환합니다.
    """
    headers_json_str = os.environ.get('NAVER_API_ALL_HEADERS_JSON')
    cookies_json_str = os.environ.get('NAVER_API_COOKIES_JSON')
    client_id_env = os.environ.get('NAVER_CLIENT_ID')
    client_secret_env = os.environ.get('NAVER_CLIENT_SECRET')

    parsed_headers = {}
    if headers_json_str:
        try:
            parsed_headers = json.loads(headers_json_str)
            if not isinstance(parsed_headers, dict):
                print("Warning: NAVER_API_ALL_HEADERS_JSON is not a valid JSON dictionary. Using empty headers.", file=sys.stderr)
                parsed_headers = {}
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse NAVER_API_ALL_HEADERS_JSON: {e}. Using empty headers.", file=sys.stderr)
            parsed_headers = {}
    else:
        print("Warning: NAVER_API_ALL_HEADERS_JSON environment variable not found. Using empty headers.", file=sys.stderr)

    parsed_cookies = {}
    if cookies_json_str:
        try:
            parsed_cookies = json.loads(cookies_json_str)
            if not isinstance(parsed_cookies, dict):
                print("Warning: NAVER_API_COOKIES_JSON is not a valid JSON dictionary. Using empty cookies.", file=sys.stderr)
                parsed_cookies = {}
        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse NAVER_API_COOKIES_JSON: {e}. Using empty cookies.", file=sys.stderr)
            parsed_cookies = {}
    else:
        print("Warning: NAVER_API_COOKIES_JSON environment variable not found. Using empty cookies.", file=sys.stderr)

    if not client_id_env:
        print("Warning: NAVER_CLIENT_ID environment variable not found.", file=sys.stderr)
    if not client_secret_env:
        print("Warning: NAVER_CLIENT_SECRET environment variable not found.", file=sys.stderr)
        
    return parsed_headers, parsed_cookies, client_id_env, client_secret_env

def reverse_geocode(lat, lng, client_id, client_secret):
    if not client_id or not client_secret:
        print("Error: Naver Client ID or Client Secret not provided for reverse geocoding.", file=sys.stderr)
        return ("API_KEYS_MISSING", "API_KEYS_MISSING") # API 키 누락 시 다른 에러 반환

    try:
        url = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"
        params = {"coords": f"{lng},{lat}", "output": "json", "orders": "legalcode"}
        api_headers = {"X-NCP-APIGW-API-KEY-ID": client_id, "X-NCP-APIGW-API-KEY": client_secret}
        response = requests.get(url, params=params, headers=api_headers, timeout=10)
        
        # 401 에러를 가장 먼저 명시적으로 확인
        if response.status_code == 401:
            print(f"CRITICAL_CALLBACK_SIGNAL (reverse_geocode): 401 Unauthorized for {lat},{lng}. API Key issue.", file=sys.stderr)
            return ("API_KEY_ERROR_401", "API_KEY_ERROR_401") # 특별한 값 반환
        
        response.raise_for_status() # 4xx 또는 5xx 에러 시 여기서 HTTPError 발생
        data = response.json()
        if data.get("status", {}).get("code") == 0 and data.get("results"):
            region = data["results"][0].get("region", {})
            area2 = region.get("area2", {}).get("name", "Unknown_Gu")
            area3 = region.get("area3", {}).get("name", "Unknown_Dong")
            return (area2, area3)
        else:
            print(f"Warning (reverse_geocode): API call successful but no results for {lat},{lng}. Status: {data.get('status')}", file=sys.stderr)
            return ("No_Results_API_Success", "No_Results_API_Success") # API는 성공했으나 결과 없음
    except requests.exceptions.HTTPError as e: # 401 외 다른 HTTP 에러
        print(f"HTTPError (reverse_geocode) for {lat},{lng}: {e}", file=sys.stderr)
        return ("Unknown_HTTP_Error", f"Status_{e.response.status_code if e.response else 'Unknown'}")
    except requests.exceptions.RequestException as e:
        print(f"RequestException during reverse geocoding for {lat},{lng}: {e}", file=sys.stderr)
        return ("Unknown_Request_Error", "Unknown_Request_Error")
    except json.JSONDecodeError:
        response_text_preview = response.text[:200] + "..." if response and len(response.text) > 200 else (response.text if response else "No response text")
        print(f"JSONDecodeError (reverse_geocode) for {lat},{lng}. Response preview: {response_text_preview}", file=sys.stderr)
        return ("Unknown_JSON_Error", "Unknown_JSON_Error")
    except Exception as e:
        print(f"Unexpected error in reverse_geocode for {lat},{lng}: {e}", file=sys.stderr)
        return ("Unknown_Error", "Unknown_Error")

def calculate_bounds(vertices):
    """꼭지점 리스트에서 경계 좌표(min/max lon/lat)를 계산합니다."""
    if not vertices or not all(isinstance(p, (list, tuple)) and len(p) == 2 for p in vertices):
        print("Error: Invalid vertices data for bounds calculation.", file=sys.stderr)
        return None, None, None, None
    try:
        lats = [point[0] for point in vertices]
        lons = [point[1] for point in vertices]
        leftLon = min(lons)
        rightLon = max(lons)
        bottomLat = min(lats)
        topLat = max(lats)
        return leftLon, rightLon, topLat, bottomLat
    except (TypeError, IndexError) as e:
        print(f"Error calculating bounds from vertices: {e}. Vertices: {vertices}", file=sys.stderr)
        return None, None, None, None

# fetch_marker_info 함수 시그니처 변경: headers, cookies, client_id, client_secret 인자 추가
def fetch_marker_info(cortars_info, headers_env, cookies_env, client_id_env, client_secret_env):
    """주어진 cortar 정보로 네이버 부동산 API에서 마커 정보를 가져옵니다."""
    cortarNo = cortars_info.get('cortarNo')
    cortarVertexLists = cortars_info.get('cortarVertexLists', [[]])

    if not cortarNo:
        print("Error: Missing 'cortarNo' in cortars_info.", file=sys.stderr)
        return None

    if cortarVertexLists and cortarVertexLists[0]:
        leftLon, rightLon, topLat, bottomLat = calculate_bounds(cortarVertexLists[0])
        if leftLon is None: # calculate_bounds가 실패하면 None을 반환
            print(f"Error: Could not calculate bounds for cortarNo: {cortarNo}", file=sys.stderr)
            return None
    else:
        # 경계 계산에 실패하거나, 꼭지점 정보가 없을 경우, API 요청은 시도하지 않는 것이 좋을 수 있습니다.
        # 또는, 경계 없이 요청하거나 기본 경계를 사용할 수 있지만, 여기서는 실패로 간주합니다.
        print(f"Warning: Invalid or missing 'cortarVertexLists' for cortarNo: {cortarNo}. Bounds calculation failed or skipped.", file=sys.stderr)
        return None

    # API 파라미터 (leftLon, rightLon, topLat, bottomLat는 위에서 계산된 값 사용)
    params = {
        'cortarNo': cortarNo, 'zoom': 15, 'priceType': 'RETAIL', 'markerId': '', 'markerType': '',
        'selectedComplexNo': '', 'selectedComplexBuildingNo': '', 'fakeComplexMarker': '',
        'realEstateType': 'APT:JGC:PRE:ABYG', 'tradeType': '', 'tag': '::::::::', 'rentPriceMin': 0,
        'rentPriceMax': 900000000, 'priceMin': 0, 'priceMax': 900000000, 'areaMin': 0,
        'areaMax': 900000000, 'oldBuildYears': '', 'recentlyBuildYears': '', 'minHouseHoldCount': 300,
        'maxHouseHoldCount': '', 'showArticle': 'false', 'sameAddressGroup': 'false',
        'minMaintenanceCost': '', 'maxMaintenanceCost': '', 'directions': '',
        'leftLon': leftLon, 'rightLon': rightLon, 'topLat': topLat, 'bottomLat': bottomLat,
        'isPresale': 'false'
    }

    try:
        # 환경 변수에서 가져온 headers_env, cookies_env 사용
        response = requests.get(
            'https://new.land.naver.com/api/complexes/single-markers/2.0',
            params=params,
            cookies=cookies_env,
            headers=headers_env,
            timeout=20 # 타임아웃 증가
        )
        print(f"Fetching marker IDs for cortarNo: {cortarNo} - HTTP status code: {response.status_code}")
        response.raise_for_status()
        response_data = response.json() # 여기서 response.json() 호출

        if not isinstance(response_data, list):
            print(f"Error: Expected a list response for markers, but got {type(response_data)}. CortarNo: {cortarNo}", file=sys.stderr)
            pprint.pprint(response_data, stream=sys.stderr) # 응답 내용 확인
            return None

        marker_info_list = []
        processed_coords = set() # 중복 좌표 처리용

        for item in response_data:
            if isinstance(item, dict) and all(k in item for k in ['markerId', 'latitude', 'longitude']):
                lat = item['latitude']
                lng = item['longitude']
                coord_key = (lat, lng)

                if coord_key in processed_coords: # 이미 처리된 좌표면 건너뛰기
                    continue

                # reverse_geocode 호출 시 환경 변수에서 가져온 client_id_env, client_secret_env 전달
                divisionName, cortarName = reverse_geocode(lat, lng, client_id_env, client_secret_env)
                
                # API 키 에러가 발생했는지 확인
                if divisionName == "API_KEY_ERROR_401" or cortarName == "API_KEY_ERROR_401":
                    print(f"Error (fetch_marker_info): API Key 401 detected from reverse_geocode for marker at ({lat},{lng}) in cortarNo {cortarNo}. Stopping and propagating error.", file=sys.stderr)
                    # 이 지점에서 함수는 "PROPAGATE_API_KEY_ERROR_401"을 반환하고 *즉시 종료*되어야 합니다.
                    # 더 이상 marker_info_list에 아무것도 추가하지 않습니다.
                    return "PROPAGATE_API_KEY_ERROR_401"
                    
                processed_coords.add(coord_key)
                time.sleep(0.1) # API 요청 간 지연

                marker_info = {
                    'markerId': item.get('markerId'), 'latitude': lat, 'longitude': lng,
                    'complexName': item.get('complexName', ''),
                    'completionYearMonth': item.get('completionYearMonth', ''),
                    'totalHouseholdCount': item.get('totalHouseholdCount', 0),
                    'dealCount': item.get('dealCount', 0), 'leaseCount': item.get('leaseCount', 0),
                    'rentCount': item.get('rentCount', 0),
                    'divisionName': divisionName, 'cortarName': cortarName
                }
                marker_info_list.append(marker_info)
            else:
                print(f"Warning: Skipping invalid marker item: {item}", file=sys.stderr)

        if marker_info_list:
            return marker_info_list
        else:
            # 이 로그는 marker_info_list가 비어 있을 때만 출력되도록 수정
            print(f"No valid marker data found in the response for cortarNo: {cortarNo}.")
            return None # 빈 리스트 대신 None 반환하여 명확히 구분

    except requests.exceptions.HTTPError as e:
        print(f"HTTPError (fetch_marker_info) for cortarNo {cortarNo}: {e}", file=sys.stderr)
        return None 
    except requests.exceptions.RequestException as e:
        print(f"RequestException (fetch_marker_info) for cortarNo {cortarNo}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        response_text_preview = response.text[:200] + "..." if response and len(response.text) > 200 else (response.text if response else "No response text")
        print(f"JSONDecodeError (fetch_marker_info) for cortarNo {cortarNo}. Response preview: {response_text_preview}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error in fetch_marker_info for cortarNo {cortarNo}: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    project_root_cwd = os.getcwd()
    print(f"Executing fetch_marker_ids.py from CWD: {project_root_cwd}")

    # 환경 변수에서 모든 설정값 가져오기
    headers_from_env, cookies_from_env, client_id_from_env, client_secret_from_env = get_all_configs_from_env()
    
    if not client_id_from_env or not client_secret_from_env:
        print("CRITICAL (__main__): Naver API keys not found in env. Exiting.", file=sys.stderr)
        sys.exit(1) # API 키 없으면 실행 불가 (종료 코드 1은 일반 오류)
    output_dir = 'output'; input_filename = 'cortars_info.json'; output_filename = 'all_marker_info.json'
    # Header나 Cookie가 없어도 일단 진행은 하되, 경고를 표시합니다. API 요청은 실패할 수 있습니다.
    if not headers_from_env or not cookies_from_env:
        print("Warning (__main__): Headers or Cookies could not be loaded from environment variables. API requests to Naver Land might fail.", file=sys.stderr)
        # API 요청이 실패할 수 있으므로, 여기서 종료하는 것을 고려할 수 있습니다.
        # sys.exit(1) # 필요시 주석 해제

    output_dir = 'output'
    input_filename = 'cortars_info.json'
    output_filename = 'all_marker_info.json'

    input_filepath = os.path.join(output_dir, input_filename) # CWD 기준
    # input_abs_filepath = os.path.abspath(input_filepath) # 로그용
    output_filepath = os.path.join(output_dir, output_filename) # CWD 기준
    # output_abs_filepath = os.path.abspath(output_filepath) # 로그용

    print(f"Attempting to read cortars info from: {input_filepath}", file=sys.stderr)
    if not os.path.exists(input_filepath):
        print(f"Error (__main__): Input file '{input_filepath}' not found. Please run fetch_cortars.py first.", file=sys.stderr)
        sys.exit(1)

    # 입력 파일(cortars_info.json) 로드
    cortars_data_list_main = [] # 변수명 변경 및 초기화
    try:
        with open(input_filepath, 'r', encoding='utf-8') as file: # 상대 경로 사용
            loaded_data = json.load(file) # 임시 변수에 로드
        # 입력 데이터 형식 처리 (단일 dict 또는 list of dicts)
        if isinstance(loaded_data, dict):
            if 'cortarNo' in loaded_data: # 유효한 단일 cortar 정보인지 확인
                cortars_data_list_main = [loaded_data]
            else:
                print(f"Warning (__main__): Input data from '{input_filepath}' is a dict but lacks 'cortarNo'. No data to process.", file=sys.stderr)
        elif isinstance(loaded_data, list):
            cortars_data_list_main = loaded_data
        else:
            print(f"Error (__main__): Expected input data from '{input_filepath}' to be a list or a valid dict, but got {type(loaded_data)}.", file=sys.stderr)
            sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error (__main__): Failed to parse JSON from input file '{input_filepath}': {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error (__main__): Could not read input file '{input_filepath}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e: # 기타 예외 처리
        print(f"Error (__main__): An unexpected error occurred while loading '{input_filepath}': {e}", file=sys.stderr)
        sys.exit(1)
        
    if not cortars_data_list_main: # 로드된 데이터가 없으면
        print("Info (__main__): No cortars data to process from input file. Exiting.", file=sys.stderr)
        # 이 경우, 결과 파일은 생성하지 않고 정상 종료(0)할 수 있습니다.
        # 또는, 입력 파일이 비어있는 것을 오류로 간주한다면 sys.exit(1)도 가능합니다.
        # 여기서는 할 일이 없으므로 정상 종료로 간주합니다.
        # 단, all_marker_info.json 파일이 비어있는 상태로 생성될 수 있으므로, 
        # 아예 파일 생성을 건너뛰거나, 빈 JSON 객체 {} 를 저장할 수 있습니다.
        # 여기서는 빈 JSON 객체를 저장하고 정상 종료합니다.
        try:
            os.makedirs(output_dir, exist_ok=True)
            with open(output_filepath, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4) # 빈 JSON 객체 저장
            print(f"No cortars data processed. Empty marker info file created at '{output_filepath}'.", file=sys.stderr)
        except Exception as e:
            print(f"Error (__main__): Could not write empty marker info file: {e}", file=sys.stderr)
        sys.exit(0)


    all_marker_info_output_main = {} # 최종 결과를 담을 딕셔너리, 변수명 변경
    api_key_error_detected_globally = False # API 키 오류 감지 플래그

    # 각 지역(cortar)별로 마커 정보 수집
    for cortars_item_main in cortars_data_list_main: # 루프 변수명 변경
        # 입력된 cortars_item이 유효한 딕셔너리이고, 'cortarNo'를 포함하는지 확인
        if not (isinstance(cortars_item_main, dict) and cortars_item_main.get('cortarNo')):
            print(f"Warning (__main__): Skipping invalid cortars_item or item missing 'cortarNo': {str(cortars_item_main)[:100]}...", file=sys.stderr)
            continue
        
        # 지역 키 생성 (divisionName과 cortarName 사용, 없으면 cortarNo로 대체)
        division_name_main = cortars_item_main.get('divisionName', 'UnknownGu') # 변수명 변경
        cortar_name_main = cortars_item_main.get('cortarName', 'UnknownDong') # 변수명 변경
        area_key_main = f"{division_name_main} {cortar_name_main}".strip()
        if not area_key_main or "UnknownGu UnknownDong" == area_key_main : # 지역 이름이 제대로 구성되지 않은 경우
            area_key_main = cortars_item_main.get('cortarNo') # fallback으로 cortarNo 사용
            if not area_key_main: # cortarNo조차 없으면 이 아이템은 처리 불가
                print(f"Warning (__main__): Skipping cortars_item due to unidentifiable area key: {str(cortars_item_main)[:100]}...", file=sys.stderr)
                continue
        
        print(f"\nProcessing for area: {area_key_main} (cortarNo: {cortars_item_main.get('cortarNo')})", file=sys.stderr)
        
        # fetch_marker_info 함수 호출하여 해당 지역의 마커 리스트 가져오기
        marker_list_result_main = fetch_marker_info( # 변수명 변경
            cortars_item_main, 
            headers_from_env, 
            cookies_from_env, 
            client_id_from_env, 
            client_secret_from_env
        )
# ======================== ▼▼▼ API 키 오류 명시적 확인 및 처리 ▼▼▼ ========================
        # print("marker_list_result_main:",marker_list_result_main)
        if marker_list_result_main == "PROPAGATE_API_KEY_ERROR_401":
            print(f"CRITICAL_ERROR_SIGNAL (__main__): API Key 401 error detected while processing area '{area_key_main}'. Terminating script with exit code 99.", file=sys.stderr)
            api_key_error_detected_globally = True # 플래그 설정
            break # for 루프를 즉시 중단합니다. (더 이상 다른 지역 처리 안 함)
# ======================== ▲▲▲ API 키 오류 명시적 확인 및 처리 ▲▲▲ ========================

        elif marker_list_result_main is not None: # None이 아니면 (즉, 유효한 리스트, 빈 리스트 포함)
            all_marker_info_output_main[area_key_main] = marker_list_result_main
            print(f"Finished processing for {area_key_main}. Found {len(marker_list_result_main)} markers.", file=sys.stderr)
        else: # marker_list_result_main is None (fetch_marker_info에서 일반 오류 발생)
            print(f"Warning (__main__): Error or no data returned from fetch_marker_info for {area_key_main}. Assigning empty list for this area.", file=sys.stderr)
            all_marker_info_output_main[area_key_main] = [] # 해당 지역은 빈 리스트로 처리

    # for 루프 종료 후 (API 키 에러로 break 되었거나, 모든 지역 처리 완료)

    # API 키 에러가 발생했다면, 여기서 스크립트를 종료 코드 99로 종료합니다.
    if api_key_error_detected_globally:
        sys.exit(99)

    # API 키 에러가 아니었고, 수집된 마커 정보가 있다면 파일로 저장합니다.
    if all_marker_info_output_main: # 저장할 데이터가 하나라도 있다면
        print(f"\nAttempting to write all marker info to: {output_filepath}", file=sys.stderr)
        try:
            os.makedirs(output_dir, exist_ok=True) # 출력 디렉토리 생성 (이미 존재해도 에러 없음)
            with open(output_filepath, 'w', encoding='utf-8') as file:
                json.dump(all_marker_info_output_main, file, ensure_ascii=False, indent=4)
            print(f"All marker information successfully saved to '{output_filepath}'", file=sys.stderr)
            sys.exit(0) # 성공적으로 모든 작업 완료
        except IOError as e:
            print(f"Error (__main__): Could not write output file '{output_filepath}': {e}", file=sys.stderr)
            sys.exit(1) # 파일 쓰기 오류 시 종료 코드 1
        except Exception as e:
            print(f"Error (__main__): An unexpected error occurred while writing output file: {e}", file=sys.stderr)
            sys.exit(1) # 기타 쓰기 오류 시 종료 코드 1
    else: # API 키 에러도 아니었고, 저장할 마커 정보도 없는 경우
        print("\nNo marker information was collected or processed successfully overall (and no API key error).", file=sys.stderr)
        # 처리할 cortars 데이터가 있었는데 결과가 없는 경우 실패로 간주할 수 있습니다.
        if cortars_data_list_main: # 처리할 아이템이 있었는데 결과가 비었다면
            sys.exit(1) # 일반 실패로 간주
        else: # 처리할 아이템 자체가 없었다면 (예: cortars_info.json이 비어있었음)
            # 이 경우는 오류가 아니므로 정상 종료할 수 있습니다.
            # 또는, 이 상황을 알리기 위해 빈 all_marker_info.json을 생성할 수도 있습니다.
            # 이전 로직에서 cortars_data_list_main이 비면 이미 종료했으므로, 이 else는 거의 도달하지 않을 수 있습니다.
            # 만약 도달한다면, 안전하게 정상 종료합니다.
            print("Info (__main__): No cortars data was provided, so no marker info was generated.", file=sys.stderr)
            sys.exit(0)