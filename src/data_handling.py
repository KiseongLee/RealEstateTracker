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
    클릭된 좌표를 지정된 출력 디렉토리의 JSON 파일에 저장합니다.
    """
    filepath = os.path.join(output_dir, 'clicked_coords.json')
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(coords, f, ensure_ascii=False, indent=4)
        print(f"좌표 저장 완료: {filepath}")
    except IOError as e:
        st.error(f"좌표 저장 실패 ({filepath}): {e}")
    except Exception as e:
        st.error(f"좌표 저장 중 예상치 못한 오류: {e}")

def create_params(lat, lon):
    """
    외부 스크립트용 파라미터 딕셔너리를 생성합니다.
    """
    return {'zoom': '15', 'centerLat': str(lat), 'centerLon': str(lon)}

def get_dong_name_from_file(output_dir):
    """
    지정된 출력 디렉토리의 cortars_info.json 파일에서 동 이름을 읽어옵니다.
    """
    filepath = os.path.join(output_dir, 'cortars_info.json')
    try:
        with open(filepath, 'r', encoding='utf-8') as file:
            cortars_info = json.load(file)
            division = cortars_info.get('divisionName', '')
            cortar = cortars_info.get('cortarName', '')
            # 구 또는 동 이름이 비어있지 않은 경우에만 조합, 아니면 "Unknown"
            if division and cortar:
                return f"{division} {cortar}".strip()
            else:
                print(f"경고: {filepath} 파일에서 divisionName 또는 cortarName을 찾을 수 없습니다.")
                return "Unknown"
    except FileNotFoundError:
        print(f"경고: {filepath} 파일을 찾을 수 없습니다.")
        return "Unknown"
    except json.JSONDecodeError:
        st.error(f"{filepath} 파일 파싱 오류.")
        return "Unknown"
    except Exception as e:
        st.error(f"동 이름 가져오기 오류 ({filepath}): {e}")
        return "Unknown"

def run_external_script(script_name, *args, auth_token=None, cookies=None):
    """
    지정된 외부 파이썬 스크립트를 실행하고 결과를 확인합니다.
    인증 정보(auth_token, cookies)를 환경 변수로 전달할 수 있습니다.
    """
    script_path = os.path.join(EXTERNAL_SCRIPTS_DIR, script_name)
    python_executable = sys.executable
    command = [python_executable, script_path] + list(args)

    print(f"Executing command: {' '.join(command)}")
    try:
        # cwd 설정: 외부 스크립트가 파일 입출력을 할 때 기준 디렉토리를 프로젝트 루트로 설정
        # data_handling.py -> src -> your_project_directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(f"Setting CWD for subprocess to: {project_root}") # CWD 확인 로그 추가

        # --- 환경 변수 설정 로직 추가 ---
        env = os.environ.copy()
        if auth_token:
            env['NAVER_AUTH_TOKEN'] = auth_token
        if cookies:
            # 필요한 쿠키를 환경 변수로 전달 (예시)
            if 'NNB' in cookies: env['NAVER_COOKIE_NNB'] = cookies['NNB']
            # ... 다른 쿠키 추가 ...
        
        result = subprocess.run(
            command,
            check=True,       # True: 반환 코드가 0이 아니면 CalledProcessError 발생
            capture_output=True,# True: stdout, stderr 캡처
            text=True,        # True: stdout, stderr를 문자열로 디코딩
            encoding='utf-8', # 디코딩 인코딩 지정
            cwd=project_root  # 실행 디렉토리 설정
            )
        # 성공 시 로그 (stdout이 너무 길면 문제가 될 수 있으니 주의)
        print(f"스크립트 {script_name} 실행 성공:")
        if result.stdout:
            print(f"STDOUT:\n{result.stdout[:1000]}...") # 너무 길면 일부만 출력
        if result.stderr:
            print(f"STDERR:\n{result.stderr[:1000]}...") # 에러 스트림도 출력 (경고 등 포함 가능)
        return True

    except FileNotFoundError:
        # sys.executable 경로가 잘못되었거나, 스크립트 파일 자체가 없을 때 발생 가능
        st.error(f"스크립트 실행 오류: 실행 파일 '{python_executable}' 또는 스크립트 '{script_path}'를 찾을 수 없습니다. PATH 및 파일 위치를 확인하세요.")
        print(f"FileNotFoundError: Command '{' '.join(command)}' failed.")
        return False
    except subprocess.CalledProcessError as e:
        # 외부 스크립트가 오류를 내며 종료(non-zero exit code)했을 때 발생
        st.error(f"스크립트 {script_name} 실행 실패 (종료 코드: {e.returncode}):")
        # 오류 발생 시 stdout, stderr 무조건 출력하여 원인 파악
        print(f"CalledProcessError for {script_name}:")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")
        # Streamlit UI에도 에러 표시
        if e.stderr:
            st.error(f"스크립트 오류 메시지:\n{e.stderr}")
        elif e.stdout:
            st.warning(f"스크립트 출력 메시지:\n{e.stdout}") # 오류는 없지만 출력이 있을 경우
        return False
    except Exception as e:
        # 그 외 예상치 못한 오류 (예: 권한 문제)
        st.error(f"스크립트 {script_name} 실행 중 예상치 못한 오류: {e}")
        print(f"Unexpected error running {script_name}: {e}")
        return False

#@st.cache_data #(show_spinner="매물 데이터 조회 중...") # 캐싱 데코레이터 추가
def fetch_data(coords_tuple, output_dir):
    """
    좌표 튜플을 기반으로 외부 스크립트를 실행하여 부동산 데이터를 가져옵니다. (캐싱 적용됨)
    성공 시 (로드된 DataFrame, 동 이름), 실패 시 (빈 DataFrame, 동 이름 또는 None) 반환.
    """
    print(f"--- fetch_data 실행 시작 for coords: {coords_tuple} ---") # 캐시 확인용 로그

    # 튜플 유효성 검사 및 위도, 경도 추출
    if not isinstance(coords_tuple, tuple) or len(coords_tuple) != 2:
        st.error("fetch_data: 유효하지 않은 좌표 튜플입니다.")
        return pd.DataFrame(), None # 실패 시 빈 DF와 None 반환

    latitude, longitude = coords_tuple

    # 좌표 저장용 딕셔너리 생성 (save_coordinates는 딕셔너리 필요)
    coords_dict = {'lat': latitude, 'lng': longitude}

    # 좌표 저장 (변경 없음)
    save_coordinates(coords_dict, output_dir)

    # 파라미터 파일 생성 (변경 없음)
    params = create_params(latitude, longitude)
    params_file_rel_path = os.path.join(output_dir, 'params.json')
    params_file_abs_path = os.path.abspath(params_file_rel_path)
    try:
        os.makedirs(output_dir, exist_ok=True)
        with open(params_file_abs_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=4)
        print(f"파라미터 저장 완료: {params_file_abs_path}")
    except Exception as e:
        st.error(f"파라미터 저장 중 오류: {e}")
        return pd.DataFrame(), None # 실패 시 빈 DF와 None 반환

    # --- (선택) 자동 인증 정보 가져오기 로직 (미구현 상태) ---
    auth_token_to_pass = None
    cookies_to_pass = None
    # ---------------------------------------------------
    # 스크립트 순차 실행 (run_external_script에 인증 정보 전달)
    print("\n--- fetch_cortars.py 실행 시작 ---")
    if not run_external_script('fetch_cortars.py', params_file_rel_path, auth_token=auth_token_to_pass, cookies=cookies_to_pass):
        st.error("fetch_cortars.py 실패.")
        # 실패해도 동 이름은 시도해볼 수 있음 (파일이 이미 생성되었을 수 있으므로)
        dong_name_on_fail = get_dong_name_from_file(output_dir)
        return pd.DataFrame(), dong_name_on_fail
    print("--- fetch_cortars.py 실행 완료 ---")

    # 동 이름 파일에서 읽기 (st.session_state 대신 변수에 저장)
    dong_name = get_dong_name_from_file(output_dir)
    print(f"동 이름 가져오기(파일): {dong_name}")

    print("\n--- fetch_marker_ids.py 실행 시작 ---")
    if not run_external_script('fetch_marker_ids.py', auth_token=auth_token_to_pass, cookies=cookies_to_pass):
        st.error("fetch_marker_ids.py 실패.")
        return pd.DataFrame(), dong_name # 실패 시 빈 DF와 현재까지 얻은 동 이름 반환
    print("--- fetch_marker_ids.py 실행 완료 ---")

    print("\n--- collect_complex_details.py 실행 시작 ---")
    if not run_external_script('collect_complex_details.py', auth_token=auth_token_to_pass, cookies=cookies_to_pass):
        st.error("collect_complex_details.py 실패.")
        return pd.DataFrame(), dong_name # 실패 시 빈 DF와 현재까지 얻은 동 이름 반환
    print("--- collect_complex_details.py 실행 완료 ---")

    # 최종 데이터 로드 및 DataFrame 변환
    final_data_file_rel_path = os.path.join(output_dir, 'complex_details_by_district.json')
    final_data_file_abs_path = os.path.abspath(final_data_file_rel_path)
    print(f"\n최종 데이터 로드 시도: {final_data_file_abs_path}")
    try:
        with open(final_data_file_abs_path, 'r', encoding='utf-8') as file:
            raw_data = json.load(file)

        # --- ▼▼▼ 수정 4: JSON을 DataFrame으로 변환하는 로직 추가 ▼▼▼ ---
        # JSON 구조가 {'지역명': [{}, {}, ...]} 형태라고 가정
        # dong_name을 키로 사용하거나, 첫 번째 키 사용 (상황에 맞게 조정 필요)
        area_key_to_load = dong_name if dong_name != "Unknown" and dong_name in raw_data else None
        if not area_key_to_load and raw_data:
            area_key_to_load = list(raw_data.keys())[0] # 첫 번째 키 사용 (임시 방편)

        if area_key_to_load and raw_data.get(area_key_to_load):
            loaded_df = pd.DataFrame(raw_data[area_key_to_load])
            print("데이터 로딩 및 DataFrame 변환 성공")
            # st.success는 app.py에서 호출하도록 제거
            # st.success("데이터 로딩 완료!")
            return loaded_df, dong_name # 성공 시 DataFrame과 동 이름 반환
        else:
            print("로드된 JSON 데이터가 비어있거나 해당 지역 키가 없습니다.")
            st.warning(f"'{dong_name}' 지역의 상세 데이터가 없습니다.") # UI 메시지 app.py에서 처리
            return pd.DataFrame(), dong_name # 데이터 없으면 빈 DF와 동 이름 반환

    except FileNotFoundError:
        st.error(f"최종 데이터 파일({final_data_file_abs_path}) 없음.")
        print(f"오류: 최종 데이터 파일({final_data_file_abs_path}) 없음")
    except json.JSONDecodeError:
        st.error(f"최종 데이터 파일({final_data_file_abs_path}) JSON 파싱 오류.")
        print(f"오류: 최종 데이터 파일({final_data_file_abs_path}) JSON 파싱 실패")
    except Exception as e:
        st.error(f"최종 데이터 로드 중 오류: {e}")
        print(f"오류: 최종 데이터 로드 중 예상치 못한 오류: {e}")

    # 로드 실패 시 빈 데이터프레임과 현재까지 얻은 동 이름 반환
    return pd.DataFrame(), dong_name
