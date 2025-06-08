# your_project_directory/src/external_`script`s/fetch_cortars.py
import requests
import json
import pprint
import sys
import os # os 모듈 임포트

# header와 cookie 정보는 환경 변수로부터 가져옵니다.
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
        
    return parsed_headers, parsed_cookies

def fetch_cortars(params, headers_env, cookies_env): # 인자로 headers와 cookies를 받도록 수정
    """지정된 파라미터로 Naver Land API에서 Cortar 정보를 가져옵니다."""
    try:
        # 함수 호출 시 전달받은 headers_env, cookies_env 사용
        response = requests.get('https://new.land.naver.com/api/cortars', params=params, cookies=cookies_env, headers=headers_env, timeout=10)
        response.raise_for_status() # HTTP 오류 발생 시 예외 발생

        response_data = response.json()
        # pprint.pprint(response_data) # 디버깅 필요 시 주석 해제

        if 'cortarVertexLists' in response_data:
            cortars_info = {
                "cortarVertexLists": response_data['cortarVertexLists'],
                "cortarNo": response_data.get('cortarNo', ''),
                "cortarName": response_data.get('cortarName', ''),
                "cityName": response_data.get('cityName', ''),
                "divisionName": response_data.get('divisionName', ''),
                "sectorName": response_data.get('sectorName', ''),
                "cityNo": response_data.get('cityNo', ''),
                "divisionNo": response_data.get('divisionNo', ''),
                "sectorNo": response_data.get('sectorNo', ''),
                "cortarType": response_data.get('cortarType', ''),
                "centerLat": response_data.get('centerLat', 0),
                "centerLon": response_data.get('centerLon', 0),
                "cortarZoom": response_data.get('cortarZoom', 0)
            }
            return cortars_info
        else:
            print("Error: Response JSON does not contain 'cortarVertexLists'.", file=sys.stderr)
            # 응답 내용이 너무 길 수 있으므로, 필요한 부분만 출력하거나 파일로 저장하는 것이 좋습니다.
            # 여기서는 처음 500자만 출력하도록 제한합니다.
            response_text_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
            print(f"Response text preview: {response_text_preview}", file=sys.stderr)
            # print("Full response received:", response_data, file=sys.stderr) # 매우 길 수 있음
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during requests to {e.request.url}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        response_text_preview = response.text[:500] + "..." if len(response.text) > 500 else response.text
        print(f"Error: Failed to parse JSON response. Response text preview: {response_text_preview}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred in fetch_cortars: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    project_root_cwd = os.getcwd() # 현재 작업 디렉토리 가져오기
    print(f"Executing fetch_cortars.py from CWD: {project_root_cwd}")

    output_dir = 'output' # 출력 디렉토리, 필요시 CWD 기준으로 상대 경로 사용 가능

    # 스크립트 직접 실행 시에도 환경 변수에서 config 가져오기
    headers_from_env, cookies_from_env = get_config_from_env()

    if not headers_from_env or not cookies_from_env:
        print("Warning: Headers or Cookies could not be loaded from environment variables for standalone execution.", file=sys.stderr)
        print("API requests might fail or be incomplete.", file=sys.stderr)
        # 여기서 스크립트를 종료할 수도 있지만, 일단 진행하도록 둡니다.
        # sys.exit(1)

    if len(sys.argv) > 1:
        params_file_rel_path = sys.argv[1]
        # params_file_abs_path는 CWD 기준으로 절대 경로를 만듭니다.
        # data_handling.py에서 cwd를 프로젝트 루트로 설정하므로, 여기서도 동일한 가정을 합니다.
        params_file_abs_path = os.path.abspath(params_file_rel_path) 

        print(f"Attempting to read params from: {params_file_abs_path}")

        if not os.path.exists(params_file_abs_path):
            print(f"Error: Parameter file not found at '{params_file_abs_path}'", file=sys.stderr)
            sys.exit(1)

        try:
            with open(params_file_abs_path, 'r', encoding='utf-8') as f:
                params_main = json.load(f) # 변수명 변경 (params -> params_main)
        except json.JSONDecodeError:
            print(f"Error: Failed to parse JSON from parameter file '{params_file_abs_path}'", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            print(f"Error reading parameter file '{params_file_abs_path}': {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while reading params file: {e}", file=sys.stderr)
            sys.exit(1)

        # fetch_cortars 함수에 환경변수에서 가져온 headers와 cookies 전달
        cortars_info_main = fetch_cortars(params_main, headers_from_env, cookies_from_env) # 변수명 변경
        # 출력 파일 경로도 CWD 기준으로 output 디렉토리 안에 저장
        output_filename = 'cortars_info.json'
        # output_dir이 상대 경로인 경우, CWD를 기준으로 경로가 결정됩니다.
        # data_handling.py와 일관성을 위해 os.path.join을 사용합니다.
        output_filepath = os.path.join(output_dir, output_filename) 
        # 절대 경로는 로그용으로만 사용
        output_abs_filepath = os.path.abspath(output_filepath)

        if cortars_info_main:

            print(f"Attempting to write cortars info to: {output_abs_filepath} (relative path used: {output_filepath})")

            division_name = cortars_info_main.get('divisionName', 'Unknown_Division')
            cortar_name = cortars_info_main.get('cortarName', 'Unknown_Cortar')
            display_name = f"{division_name} {cortar_name}".strip()

            try:
                # output 디렉토리가 CWD 내에 없다면 생성
                # data_handling.py에서 cwd를 프로젝트 루트로 설정하고 output 디렉토리를 생성할 것이므로
                # 이 스크립트가 직접 output 디렉토리를 생성해야 할 수도 있습니다.
                # 하지만 보통 data_handling.py에 의해 이미 생성되어 있을 것입니다.
                # 안전을 위해 여기서도 확인 및 생성 로직을 추가할 수 있습니다.
                os.makedirs(output_dir, exist_ok=True) # output 디렉토리 생성 (이미 있어도 에러 안남)

                with open(output_filepath, 'w', encoding='utf-8') as file: # 상대 경로 사용
                    json.dump(cortars_info_main, file, ensure_ascii=False, indent=4)
                print(f"Cortars info for '{display_name}' collected and saved to '{output_abs_filepath}'")
            except IOError as e:
                print(f"Error writing cortars info to file '{output_abs_filepath}': {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"An unexpected error occurred while writing cortars info: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("No cortars data collected or an error occurred during fetching.", file=sys.stderr)            
            try:
                # 기존 파일이 있으면 빈 JSON 객체로 덮어쓰기
                os.makedirs(output_dir, exist_ok=True)
                with open(output_filepath, 'w', encoding='utf-8') as file:
                    json.dump({}, file, ensure_ascii=False, indent=4)
                print(f"Initialized/Cleared JSON file at '{output_abs_filepath}'.", file=sys.stderr)
            except Exception as e:
                print(f"Error initializing JSON file '{output_filepath}': {e}", file=sys.stderr)
                sys.exit(1)
    else:
        print("Error: No parameter file path provided as command-line argument.", file=sys.stderr)
        print("Usage: python fetch_cortars.py <path_to_params.json>", file=sys.stderr)
        sys.exit(1)

    sys.exit(0) # 성공 시 종료 코드 0
