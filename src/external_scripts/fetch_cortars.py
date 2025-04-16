# your_project_directory/src/external_scripts/fetch_cortars.py
import requests
import json
import pprint
import sys
import os # os 모듈 임포트

# --- ▼▼▼ config 임포트 수정 ▼▼▼ ---
# fetch_cortars.py는 src/external_scripts/ 안에 있고, config.py는 src/ 안에 있음.
# 따라서 config.py는 현재 파일 기준으로 부모 패키지(src)에 위치함.
# 상대 경로 '..'를 사용하여 부모 패키지에서 config 모듈을 가져옴.
try:
    # 기본 실행 경로 (data_handling.py에서 실행될 때)
    from ..config import cookies, headers
except ImportError:
    # 스크립트를 직접 실행하는 경우 등 예외 상황 처리 (덜 권장됨)
    # ImportError 발생 시, 프로젝트 루트를 sys.path에 추가하여 src.config를 찾도록 시도
    print("Warning: Relative import failed. Attempting to import via sys.path manipulation.", file=sys.stderr)
    # 현재 파일의 절대 경로를 기준으로 프로젝트 루트 경로 계산
    current_dir = os.path.dirname(os.path.abspath(__file__)) # /path/to/your_project_directory/src/external_scripts
    src_dir = os.path.dirname(current_dir) # /path/to/your_project_directory/src
    project_root = os.path.dirname(src_dir) # /path/to/your_project_directory
    if project_root not in sys.path:
        sys.path.insert(0, project_root) # sys.path 맨 앞에 프로젝트 루트 추가

    try:
        from src.config import cookies, headers
        print("Successfully imported config via sys.path.")
    except ImportError:
        print("\nCritical Error: Could not import 'cookies' and 'headers' from config.", file=sys.stderr)
        print("1. Ensure 'config.py' exists in the 'src/' directory.", file=sys.stderr)
        print("2. Ensure 'src/' directory has an '__init__.py' file.", file=sys.stderr)
        print("3. Check for syntax errors in 'config.py'.", file=sys.stderr)
        sys.exit(1) # config 임포트 최종 실패 시 스크립트 종료
# --- ▲▲▲ config 임포트 수정 완료 ▲▲▲ ---


def fetch_cortars(params):
    """지정된 파라미터로 Naver Land API에서 Cortar 정보를 가져옵니다."""
    try:
        # config에서 가져온 cookies, headers 사용
        response = requests.get('https://new.land.naver.com/api/cortars', params=params, cookies=cookies, headers=headers, timeout=10)
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
            print("Response received:", response_data, file=sys.stderr)
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error during requests to {e.request.url}: {e}", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print(f"Error: Failed to parse JSON response. Response text: {response.text}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"An unexpected error occurred in fetch_cortars: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    project_root_cwd = os.getcwd()
    print(f"Executing fetch_cortars.py from CWD: {project_root_cwd}")

    output_dir = 'output'

    if len(sys.argv) > 1:
        params_file_rel_path = sys.argv[1]
        params_file_abs_path = os.path.abspath(params_file_rel_path)

        print(f"Attempting to read params from: {params_file_abs_path}")

        if not os.path.exists(params_file_abs_path):
            print(f"Error: Parameter file not found at '{params_file_abs_path}'", file=sys.stderr)
            sys.exit(1)

        try:
            with open(params_file_abs_path, 'r', encoding='utf-8') as f:
                params = json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Failed to parse JSON from parameter file '{params_file_abs_path}'", file=sys.stderr)
            sys.exit(1)
        except IOError as e:
            print(f"Error reading parameter file '{params_file_abs_path}': {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred while reading params file: {e}", file=sys.stderr)
            sys.exit(1)

        cortars_info = fetch_cortars(params)

        if cortars_info:
            output_filename = 'cortars_info.json'
            output_filepath = os.path.join(output_dir, output_filename)
            output_abs_filepath = os.path.abspath(output_filepath)

            print(f"Attempting to write cortars info to: {output_abs_filepath}")

            division_name = cortars_info.get('divisionName', 'Unknown_Division')
            cortar_name = cortars_info.get('cortarName', 'Unknown_Cortar')
            display_name = f"{division_name} {cortar_name}".strip()

            try:
                with open(output_abs_filepath, 'w', encoding='utf-8') as file:
                    json.dump(cortars_info, file, ensure_ascii=False, indent=4)
                print(f"Cortars info for '{display_name}' collected and saved to '{output_abs_filepath}'")
            except IOError as e:
                print(f"Error writing cortars info to file '{output_abs_filepath}': {e}", file=sys.stderr)
                sys.exit(1)
            except Exception as e:
                print(f"An unexpected error occurred while writing cortars info: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print("No cortars data collected or an error occurred during fetching.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Error: No parameter file path provided as command-line argument.", file=sys.stderr)
        print("Usage: python fetch_cortars.py <path_to_params.json>", file=sys.stderr)
        sys.exit(1)

    sys.exit(0)
