# src/data_handling.py
import streamlit as st
import json
import subprocess
import os
import sys # sys 모듈 임포트 추가
# 최종 데이터를 DataFrame으로 반환하기 위해 필요
import pandas as pd

# 외부 스크립트가 있는 디렉토리 경로 (data_handling.py 기준 상대 경로)
EXTERNAL_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "external_scripts")
OUTPUT_DIR = "output" # 출력 디렉토리 정의 (fetch_data 등에서 일관되게 사용)


def save_coordinates(coords, output_dir):
    """
    클릭된 좌표를 지정된 출력 디렉토리의 JSON 파일에 저장합니다. (현재 사용 안 함 가정)
    오류 발생 시 Streamlit UI에 직접 에러를 표시하지 않고, 콘솔에만 로그를 남깁니다.
    """
    filepath = os.path.join(output_dir, 'clicked_coords.json')
    try:
        os.makedirs(output_dir, exist_ok=True) # output_dir이 없을 경우 생성
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(coords, f, ensure_ascii=False, indent=4)
        print(f"좌표 저장 완료: {filepath}", file=sys.stderr) # 로그는 stderr로
    except IOError as e:
        print(f"오류: 좌표 저장 실패 ({filepath}): {e}", file=sys.stderr)
    except Exception as e:
        print(f"오류: 좌표 저장 중 예상치 못한 오류: {e}", file=sys.stderr)


def create_params(lat, lon):
    """
    외부 스크립트용 파라미터 딕셔너리를 생성합니다.
    """
    return {'zoom': '15', 'centerLat': str(lat), 'centerLon': str(lon)}

def get_dong_name_from_file(output_dir):
    """
    지정된 출력 디렉토리의 cortars_info.json 파일에서 동 이름을 읽어옵니다.
    오류 발생 시 Streamlit UI에 직접 에러를 표시하지 않고, 콘솔에만 로그를 남깁니다.
    """
    filepath = os.path.join(output_dir, 'cortars_info.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            cortars_info = json.load(file)
            division = cortars_info.get('divisionName', '')
            cortar = cortars_info.get('cortarName', '')
            if division and cortar:
                return f"{division} {cortar}".strip()
            else:
                print(f"경고: {filepath} 파일에서 divisionName 또는 cortarName을 찾을 수 없습니다.", file=sys.stderr)
                return "Unknown"
    except FileNotFoundError:
        print(f"경고: {filepath} 파일을 찾을 수 없습니다.", file=sys.stderr)
        return "Unknown"
    except json.JSONDecodeError:
        print(f"오류: {filepath} 파일 파싱 오류.", file=sys.stderr)
        return "Unknown"
    except Exception as e:
        print(f"오류: 동 이름 가져오기 오류 ({filepath}): {e}", file=sys.stderr)
        return "Unknown"

def run_external_script(script_name, *args, 
                        headers_to_pass=None, cookies_to_pass=None, 
                        client_id_to_pass=None, client_secret_to_pass=None):
    """
    외부 파이썬 스크립트를 실행하고 결과를 확인합니다.
    API 키 오류 발생 시 특별한 문자열 "API_KEY_ERROR_FROM_SCRIPT_EXIT_CODE_99"을 반환합니다.
    일반 실패 시 False, 성공 시 True를 반환합니다.
    """
    script_path = os.path.join(EXTERNAL_SCRIPTS_DIR, script_name)
    python_executable = sys.executable # 현재 Streamlit 앱을 실행하는 Python 인터프리터
    command = [python_executable, script_path] + list(args)

    print(f"Executing command: {' '.join(command)}", file=sys.stderr)
    try:
        # 외부 스크립트의 작업 디렉토리를 프로젝트 루트로 설정
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # src 폴더의 부모
        
        # 환경 변수 설정
        env = os.environ.copy()
        if headers_to_pass and isinstance(headers_to_pass, dict):
            env['NAVER_API_ALL_HEADERS_JSON'] = json.dumps(headers_to_pass)
        if cookies_to_pass and isinstance(cookies_to_pass, dict):
            env['NAVER_API_COOKIES_JSON'] = json.dumps(cookies_to_pass)
        if client_id_to_pass:
            env['NAVER_CLIENT_ID'] = client_id_to_pass
        if client_secret_to_pass:
            env['NAVER_CLIENT_SECRET'] = client_secret_to_pass
        
        result = subprocess.run(
            command,
            check=False,        # False로 설정하여 반환 코드를 직접 확인
            capture_output=True,
            text=True,
            encoding='utf-8',
            cwd=project_root,   # 작업 디렉토리 설정
            env=env             # 수정된 환경 변수 전달
        )
        
        # 종료 코드 확인
        if result.returncode == 99: # API 키 에러 특정 종료 코드 (fetch_marker_ids.py에서 설정)
            print(f"Script {script_name} indicated API Key (401) error via exit code 99.", file=sys.stderr)
            if result.stderr: # 에러 스트림이 있다면 출력 (디버깅용)
                print(f"STDERR from API Key errored script ({script_name}):\n{result.stderr[:1000]}...", file=sys.stderr)
            return "API_KEY_ERROR_FROM_SCRIPT_EXIT_CODE_99" # 특별한 문자열 반환

        elif result.returncode != 0: # 99가 아닌 다른 오류 종료 코드
            print(f"Script {script_name} failed with exit code {result.returncode}.", file=sys.stderr)
            if result.stdout: print(f"STDOUT ({script_name}):\n{result.stdout[:1000]}...", file=sys.stderr)
            if result.stderr: print(f"STDERR ({script_name}):\n{result.stderr[:1000]}...", file=sys.stderr)
            return False # 일반적인 실패

        # 성공 시 (returncode == 0)
        print(f"Script {script_name} executed successfully.", file=sys.stderr)
        if result.stdout: print(f"STDOUT ({script_name}):\n{result.stdout[:500]}...", file=sys.stderr)
        if result.stderr: print(f"STDERR (Info/Warnings from {script_name}):\n{result.stderr[:500]}...", file=sys.stderr)
        return True

    except FileNotFoundError:
        print(f"FileNotFoundError: Command '{' '.join(command)}' failed. Check script path and python executable.", file=sys.stderr)
        return False # 일반적인 실패
    except Exception as e: # subprocess.run 자체에서 발생할 수 있는 다른 예외들 (권한 문제 등)
        print(f"Unexpected error running {script_name}: {e}", file=sys.stderr)
        return False # 일반적인 실패

def fetch_data(coords_tuple, output_dir):
    """
    좌표 튜플을 기반으로 외부 스크립트를 순차적으로 실행하여 부동산 데이터를 가져옵니다.
    반환값: (DataFrame, str_dong_name, str_error_signal or None)
    - DataFrame: 성공 시 로드된 데이터, 실패 시 빈 DataFrame
    - str_dong_name: 확인된 동 이름, 실패 시 "Unknown" 또는 유사 값
    - str_error_signal: API 키 오류 시 "API_KEY_ERROR_SIGNAL", 그 외 성공/일반실패 시 None
    """
    print(f"--- fetch_data 실행 시작 for coords: {coords_tuple} ---", file=sys.stderr)

    # --- 1. 입력 유효성 검사 및 파라미터 준비 ---
    if not isinstance(coords_tuple, tuple) or len(coords_tuple) != 2:
        print("오류: fetch_data: 유효하지 않은 좌표 튜플입니다.", file=sys.stderr)
        return pd.DataFrame(), "Invalid_Coords", None # (df, dong_name, error_signal)

    latitude, longitude = coords_tuple
    
    # save_coordinates는 현재 직접적인 데이터 흐름에 영향을 주지 않으므로, 필요시 호출
    # save_coordinates({'lat': latitude, 'lng': longitude}, output_dir) 

    params = create_params(latitude, longitude)
    params_file_rel_path = os.path.join(output_dir, 'params.json')
    params_file_abs_path = os.path.abspath(params_file_rel_path)
    try:
        os.makedirs(output_dir, exist_ok=True) # 출력 디렉토리 생성
        with open(params_file_abs_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=4)
        print(f"파라미터 저장 완료: {params_file_abs_path}", file=sys.stderr)
    except Exception as e:
        print(f"오류: 파라미터 저장 중 오류: {e}", file=sys.stderr)
        return pd.DataFrame(), "Params_Save_Error", None

    # --- 2. 세션에서 설정값 가져오기 ---
    user_headers = st.session_state.get('user_headers', {})
    user_cookies = st.session_state.get('user_cookies', {})
    naver_client_id = st.session_state.get('naver_client_id')
    naver_client_secret = st.session_state.get('naver_client_secret')

    common_run_params = {
        "headers_to_pass": user_headers,
        "cookies_to_pass": user_cookies,
        "client_id_to_pass": naver_client_id,
        "client_secret_to_pass": naver_client_secret
    }

    # --- 3. 외부 스크립트 순차 실행 ---
    # 3.1. fetch_cortars.py 실행
    print("\n--- fetch_cortars.py 실행 시작 ---", file=sys.stderr)
    script_cortars_result = run_external_script('fetch_cortars.py', params_file_rel_path, **common_run_params)
    # fetch_cortars.py는 API 키 오류를 직접 감지하지 않는다고 가정 (일반 성공/실패만 반환)
    if not script_cortars_result: # True가 아닌 경우 (False 또는 다른 문자열 - 여기서는 False만 일반 실패로 간주)
        print("오류: fetch_cortars.py 실행 실패.", file=sys.stderr)
        dong_name_on_cortars_fail = get_dong_name_from_file(output_dir) # 실패해도 동 이름은 시도
        return pd.DataFrame(), dong_name_on_cortars_fail, None
    print("--- fetch_cortars.py 실행 완료 ---", file=sys.stderr)
    dong_name = get_dong_name_from_file(output_dir) # 성공 후 동 이름 가져오기
    print(f"동 이름 가져오기(파일): {dong_name}", file=sys.stderr)

    # 3.2. fetch_marker_ids.py 실행
    print("\n--- fetch_marker_ids.py 실행 시작 ---", file=sys.stderr)
    script_marker_result = run_external_script('fetch_marker_ids.py', **common_run_params)
    
    # API 키 오류 시그널 확인
    if script_marker_result == "API_KEY_ERROR_FROM_SCRIPT_EXIT_CODE_99":
        print("fetch_data: API Key error (exit code 99) detected from fetch_marker_ids.py.", file=sys.stderr)
        # API 키 에러 발생 시, (빈 DataFrame, 현재까지의 동 이름, "API_KEY_ERROR_SIGNAL") 반환
        return pd.DataFrame(), dong_name, "API_KEY_ERROR_SIGNAL" 
    elif not script_marker_result: # True가 아닌 일반적인 실패 (False)
        print("오류: fetch_marker_ids.py 실행 실패 (일반 오류).", file=sys.stderr)
        return pd.DataFrame(), dong_name, None # 일반 실패 시 에러 신호는 None
    print("--- fetch_marker_ids.py 실행 완료 ---", file=sys.stderr)

    # 3.3. collect_complex_details.py 실행
    print("\n--- collect_complex_details.py 실행 시작 ---", file=sys.stderr)
    # 이 스크립트도 API 키 오류를 직접 감지하지 않는다고 가정
    if not run_external_script('collect_complex_details.py', **common_run_params):
        print("오류: collect_complex_details.py 실행 실패.", file=sys.stderr)
        return pd.DataFrame(), dong_name, None
    print("--- collect_complex_details.py 실행 완료 ---", file=sys.stderr)

    # --- 4. 최종 데이터 로드 ---
    final_data_file_rel_path = os.path.join(output_dir, 'complex_details_by_district.json')
    final_data_file_abs_path = os.path.abspath(final_data_file_rel_path)
    print(f"\n최종 데이터 로드 시도: {final_data_file_abs_path}", file=sys.stderr)
    try:
        with open(final_data_file_abs_path, 'r', encoding='utf-8') as file:
            raw_data = json.load(file)
        
        # 동 이름으로 데이터 추출 (기존 로직과 유사)
        area_key_to_load = dong_name if dong_name != "Unknown" and dong_name in raw_data else None
        if not area_key_to_load and raw_data: # 첫 번째 키를 사용하거나, 더 나은 로직 필요
            area_key_to_load = list(raw_data.keys())[0] if raw_data.keys() else None

        if area_key_to_load and raw_data.get(area_key_to_load):
            loaded_df = pd.DataFrame(raw_data[area_key_to_load])
            print("데이터 로딩 및 DataFrame 변환 성공.", file=sys.stderr)
            return loaded_df, dong_name, None # 성공 시 에러 신호는 None
        else:
            print(f"경고: 로드된 JSON 데이터가 비었거나 '{dong_name}' 또는 '{area_key_to_load}' 지역 키가 없습니다.", file=sys.stderr)
            return pd.DataFrame(), dong_name, None # 데이터 없어도 일반적인 흐름, 에러 신호 None
    except FileNotFoundError:
        print(f"오류: 최종 데이터 파일({final_data_file_abs_path}) 없음.", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"오류: 최종 데이터 파일({final_data_file_abs_path}) JSON 파싱 오류.", file=sys.stderr)
    except Exception as e:
        print(f"오류: 최종 데이터 로드 중 예상치 못한 오류: {e}", file=sys.stderr)

    # 최종적으로 실패한 경우
    return pd.DataFrame(), dong_name, None