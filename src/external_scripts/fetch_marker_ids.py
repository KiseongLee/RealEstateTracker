# your_project_directory/src/external_scripts/fetch_marker_ids.py
import requests
import json
import pprint
import time
import sys
import os
import toml # toml 라이브러리 임포트

# --- ▼▼▼ config 임포트 수정 (cookies, headers만) ▼▼▼ ---
# config.py는 src/ 안에 있다고 가정
try:
    # 기본 실행 경로 (data_handling.py에서 실행될 때)
    from ..config import cookies, headers # Naver 키 관련 임포트 제거
except ImportError:
    # 스크립트를 직접 실행하는 경우 등 예외 상황 처리
    print("Warning: Relative import for config failed. Attempting via sys.path.", file=sys.stderr)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.dirname(current_dir)
    project_root = os.path.dirname(src_dir)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    try:
        from src.config import cookies, headers # Naver 키 관련 임포트 제거
        print("Successfully imported cookies, headers from config via sys.path.")
    except ImportError:
        print("\nCritical Error: Could not import 'cookies' and 'headers' from config.", file=sys.stderr)
        print("Ensure 'config.py' exists in 'src/' and contains cookies, headers.", file=sys.stderr)
        sys.exit(1)
# --- ▲▲▲ config 임포트 수정 완료 ▲▲▲ ---

# --- ▼▼▼ secrets.toml 로딩 함수 추가 ▼▼▼ ---
def load_secrets(cwd):
    """현재 작업 디렉토리를 기준으로 .streamlit/secrets.toml 파일을 로드합니다."""
    secrets_path = os.path.join(cwd, ".streamlit", "secrets.toml")
    print(f"Attempting to load secrets from: {secrets_path}") # 경로 확인 로그
    if not os.path.exists(secrets_path):
        print(f"Error: Secrets file not found at '{secrets_path}'.", file=sys.stderr)
        print("Ensure the file exists and the script is run from the project root directory.", file=sys.stderr)
        return None # 파일 없으면 None 반환

    try:
        secrets = toml.load(secrets_path)
        # 필요한 키가 있는지 확인 (예: [naver] 섹션과 그 안의 키들)
        if "naver" in secrets and "client_id" in secrets["naver"] and "client_secret" in secrets["naver"]:
            print("Naver API keys loaded successfully from secrets.toml.")
            return secrets
        else:
            print("Error: 'naver' section or required keys ('client_id', 'client_secret') not found in secrets.toml.", file=sys.stderr)
            return None # 키 없으면 None 반환
    except toml.TomlDecodeError as e:
        print(f"Error decoding secrets.toml file: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred while loading secrets.toml: {e}", file=sys.stderr)
        return None
# --- ▲▲▲ secrets.toml 로딩 함수 추가 완료 ▲▲▲ ---

# --- ▼▼▼ reverse_geocode 함수 수정 (st.secrets 대신 로드된 secrets 사용) ▼▼▼ ---
def reverse_geocode(lat, lng, api_keys):
    """좌표를 사용하여 네이버 역지오코딩 API로 구, 동 정보를 가져옵니다."""
    if not api_keys: # API 키 없으면 함수 실행 불가
        print("Error: Naver API keys not available for reverse geocoding.", file=sys.stderr)
        return ("Keys_Not_Found", "Keys_Not_Found")

    try:
        url = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"
        params = {
            "coords": f"{lng},{lat}",
            "output": "json",
            "orders": "legalcode"
        }
        # 로드된 secrets에서 키 사용
        api_headers = {
            "X-NCP-APIGW-API-KEY-ID": api_keys['naver']['client_id'],
            "X-NCP-APIGW-API-KEY": api_keys['naver']['client_secret']
        }

        response = requests.get(url, params=params, headers=api_headers, timeout=10)
        response.raise_for_status()

        data = response.json()
        if data.get("status", {}).get("code") == 0 and data.get("results"):
            region = data["results"][0].get("region", {})
            area2 = region.get("area2", {}).get("name", "Unknown_Gu")
            area3 = region.get("area3", {}).get("name", "Unknown_Dong")
            return (area2, area3)
        else:
            print(f"Warning: Reverse geocoding for {lat},{lng} failed or returned no results. Status: {data.get('status')}", file=sys.stderr)
            return ("Unknown_API_Fail", "Unknown_API_Fail")

    except requests.exceptions.RequestException as e:
        print(f"Error during reverse geocoding request for {lat},{lng}: {e}", file=sys.stderr)
        return ("Unknown_Request_Error", "Unknown_Request_Error")
    except json.JSONDecodeError:
        print(f"Error parsing JSON response during reverse geocoding for {lat},{lng}. Response: {response.text}", file=sys.stderr)
        return ("Unknown_JSON_Error", "Unknown_JSON_Error")
    except KeyError as e:
        print(f"Error: Missing key {e} when accessing loaded secrets for reverse geocoding.", file=sys.stderr)
        return ("Key_Error", "Key_Error")
    except Exception as e:
        print(f"An unexpected error occurred during reverse geocoding for {lat},{lng}: {e}", file=sys.stderr)
        return ("Unknown_Error", "Unknown_Error")
# --- ▲▲▲ reverse_geocode 함수 수정 완료 ▲▲▲ ---

def calculate_bounds(vertices):
    """꼭지점 리스트에서 경계 좌표(min/max lon/lat)를 계산합니다."""
    # (이 함수는 변경 없음)
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

def fetch_marker_info(cortars_info, loaded_secrets): # secrets 인자 추가
    """주어진 cortar 정보로 네이버 부동산 API에서 마커 정보를 가져옵니다."""
    # (함수 앞부분은 변경 없음)
    cortarNo = cortars_info.get('cortarNo')
    cortarVertexLists = cortars_info.get('cortarVertexLists', [[]])

    if not cortarNo:
        print("Error: Missing 'cortarNo' in cortars_info.", file=sys.stderr)
        return None

    if cortarVertexLists and cortarVertexLists[0]:
        leftLon, rightLon, topLat, bottomLat = calculate_bounds(cortarVertexLists[0])
        if leftLon is None:
            print(f"Error: Could not calculate bounds for cortarNo: {cortarNo}", file=sys.stderr)
            return None
    else:
        print(f"Warning: Invalid or missing 'cortarVertexLists' for cortarNo: {cortarNo}. Bounds calculation skipped or failed.", file=sys.stderr)
        return None

    params = { # API 파라미터 (변경 없음)
        'cortarNo': cortarNo, 'zoom': 15, 'priceType': 'RETAIL', 'markerId': '', 'markerType': '',
        'selectedComplexNo': '', 'selectedComplexBuildingNo': '', 'fakeComplexMarker': '',
        'realEstateType': 'APT', 'tradeType': '', 'tag': '::::::::', 'rentPriceMin': 0,
        'rentPriceMax': 900000000, 'priceMin': 0, 'priceMax': 900000000, 'areaMin': 0,
        'areaMax': 900000000, 'oldBuildYears': '', 'recentlyBuildYears': '', 'minHouseHoldCount': 300,
        'maxHouseHoldCount': '', 'showArticle': 'false', 'sameAddressGroup': 'false',
        'minMaintenanceCost': '', 'maxMaintenanceCost': '', 'directions': '', 'leftLon': leftLon,
        'rightLon': rightLon, 'topLat': topLat, 'bottomLat': bottomLat, 'isPresale': 'false'
    }

    try:
        response = requests.get(
            'https://new.land.naver.com/api/complexes/single-markers/2.0',
            params=params,
            cookies=cookies, # config에서 가져온 cookies
            headers=headers, # config에서 가져온 headers
            timeout=20
        )
        print(f"Fetching marker IDs for cortarNo: {cortarNo} - HTTP status code: {response.status_code}")
        response.raise_for_status()

        response_data = response.json()
        if not isinstance(response_data, list):
            print(f"Error: Expected a list response for markers, but got {type(response_data)}. CortarNo: {cortarNo}", file=sys.stderr)
            pprint.pprint(response_data, stream=sys.stderr)
            return None

        marker_info_list = []
        processed_coords = set()

        for item in response_data:
            if isinstance(item, dict) and all(k in item for k in ['markerId', 'latitude', 'longitude']):
                lat = item['latitude']
                lng = item['longitude']
                coord_key = (lat, lng)

                if coord_key in processed_coords:
                    continue

                # --- ▼▼▼ reverse_geocode 호출 시 loaded_secrets 전달 ▼▼▼ ---
                divisionName, cortarName = reverse_geocode(lat, lng, loaded_secrets)
                # --- ▲▲▲ 호출 수정 ▲▲▲ ---
                processed_coords.add(coord_key)
                time.sleep(0.1)

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
            print(marker_info_list)
            print(f"No valid marker data found in the response for cortarNo: {cortarNo}.")
            return None

    # (예외 처리 부분은 변경 없음)
    except requests.exceptions.RequestException as e:
        print(f"Error during marker fetch request for cortarNo {cortarNo}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"Error parsing JSON response for markers for cortarNo {cortarNo}. Response: {response.text}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred in fetch_marker_info for cortarNo {cortarNo}: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    project_root_cwd = os.getcwd() # 스크립트 실행 시점의 CWD (프로젝트 루트여야 함)
    print(f"Executing fetch_marker_ids.py from CWD: {project_root_cwd}")

    # --- ▼▼▼ secrets.toml 로드 ▼▼▼ ---
    loaded_secrets = load_secrets(project_root_cwd)
    if loaded_secrets is None:
        # secrets 로드 실패 시 스크립트 종료
        sys.exit(1)
    # --- ▲▲▲ secrets.toml 로드 완료 ▲▲▲ ---

    output_dir = 'output'
    input_filename = 'cortars_info.json'
    output_filename = 'all_marker_info.json'

    input_filepath = os.path.join(output_dir, input_filename)
    input_abs_filepath = os.path.abspath(input_filepath)
    output_filepath = os.path.join(output_dir, output_filename)
    output_abs_filepath = os.path.abspath(output_filepath)

    print(f"Attempting to read cortars info from: {input_abs_filepath}")
    if not os.path.exists(input_abs_filepath):
        print(f"Error: Input file '{input_abs_filepath}' not found. Run fetch_cortars.py first.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(input_abs_filepath, 'r', encoding='utf-8') as file:
            cortars_data = json.load(file)
    except Exception as e: # 포괄적인 예외 처리
        print(f"Error reading or parsing input file '{input_abs_filepath}': {e}", file=sys.stderr)
        sys.exit(1)

    if isinstance(cortars_data, dict):
        if 'cortarNo' in cortars_data:
            cortars_data = [cortars_data]
        else:
            print(f"Warning: Input data from '{input_abs_filepath}' is dict but lacks 'cortarNo'. Processing may fail.", file=sys.stderr)
            cortars_data = []
    elif not isinstance(cortars_data, list):
        print(f"Error: Expected input data to be a list or dict, but got {type(cortars_data)}.", file=sys.stderr)
        sys.exit(1)

    all_marker_info = {}
    success_count = 0

    for cortars_info in cortars_data:
        if not isinstance(cortars_info, dict):
            print(f"Warning: Skipping invalid item in cortars data (not a dict): {cortars_info}", file=sys.stderr)
            continue

        division_name = cortars_info.get('divisionName')
        cortar_name = cortars_info.get('cortarName')
        if not division_name or not cortar_name:
            print(f"Warning: Skipping item due to missing 'divisionName' or 'cortarName': {cortars_info}", file=sys.stderr)
            continue
        area_key_name = f"{division_name} {cortar_name}".strip()

        cortar_no = cortars_info.get('cortarNo')
        if not cortar_no:
            print(f"Warning: Skipping item due to missing 'cortarNo' for {area_key_name}", file=sys.stderr)
            continue

        print(f"\nProcessing cortarNo: {cortar_no} ({area_key_name})...")
        # --- ▼▼▼ fetch_marker_info 호출 시 loaded_secrets 전달 ▼▼▼ ---
        marker_info_list = fetch_marker_info(cortars_info, loaded_secrets)
        # --- ▲▲▲ 호출 수정 ▲▲▲ ---

        if marker_info_list:
            all_marker_info[area_key_name] = marker_info_list
            print(f"Successfully fetched {len(marker_info_list)} markers for {area_key_name}.")
            success_count += 1
        else:
            print(f"Failed to fetch or no marker information found for {area_key_name} (cortarNo {cortar_no}).")

    if all_marker_info:
        print(f"\nAttempting to write all marker info to: {output_abs_filepath}")
        try:
            with open(output_abs_filepath, 'w', encoding='utf-8') as file:
                json.dump(all_marker_info, file, ensure_ascii=False, indent=4)
            print(f"All marker information ({success_count} area(s)) collected and saved to '{output_abs_filepath}'")
        except Exception as e: # 포괄적인 예외 처리
            print(f"Error writing output file '{output_abs_filepath}': {e}", file=sys.stderr)
            sys.exit(1)
    else:
        print("\nNo marker information was collected overall.", file=sys.stderr)
        if success_count == 0:
            sys.exit(1)

    sys.exit(0)
