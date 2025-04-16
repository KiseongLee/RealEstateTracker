# src/data_handling.py
import streamlit as st
import json
import subprocess
import os
import sys # sys 모듈 임포트 추가

# 외부 스크립트가 있는 디렉토리 경로 (data_handling.py 기준 상대 경로)
EXTERNAL_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "external_scripts")

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

def run_external_script(script_name, *args):
    """
    지정된 외부 파이썬 스크립트를 실행하고 결과를 확인합니다.
    현재 Streamlit 앱과 동일한 파이썬 실행 파일을 사용합니다.
    """
    script_path = os.path.join(EXTERNAL_SCRIPTS_DIR, script_name)
    # --- ▼▼▼ python3 대신 sys.executable 사용 ▼▼▼ ---
    python_executable = sys.executable # 현재 파이썬 인터프리터 경로
    command = [python_executable, script_path] + list(args)
    # --- ▲▲▲ 수정 완료 ▲▲▲ ---

    print(f"Executing command: {' '.join(command)}")
    try:
        # cwd 설정: 외부 스크립트가 파일 입출력을 할 때 기준 디렉토리를 프로젝트 루트로 설정
        # data_handling.py -> src -> your_project_directory
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        print(f"Setting CWD for subprocess to: {project_root}") # CWD 확인 로그 추가

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

def fetch_data(coords, output_dir):
    """
    좌표를 기반으로 외부 스크립트를 순차적으로 실행하여 부동산 데이터를 가져옵니다.
    성공 시 로드된 데이터를, 실패 시 None을 반환합니다.
    생성되는 파일들은 output_dir에 저장됩니다.
    """
    st.session_state['data_loaded'] = False
    st.session_state['current_data'] = None
    st.session_state['dong_name'] = None

    latitude = coords.get('lat')
    longitude = coords.get('lng')

    if latitude is None or longitude is None:
        st.error("유효하지 않은 좌표입니다.")
        return None

    # 좌표 저장 (출력 디렉토리 사용)
    save_coordinates(coords, output_dir)

    # 파라미터 파일 생성 (출력 디렉토리 사용)
    params = create_params(latitude, longitude)
    params_file_rel_path = os.path.join(output_dir, 'params.json') # 상대 경로
    params_file_abs_path = os.path.abspath(params_file_rel_path) # 절대 경로 (로깅용)
    try:
        # params.json 생성 시 output 디렉토리 존재 확인 및 생성
        os.makedirs(output_dir, exist_ok=True)
        with open(params_file_abs_path, 'w', encoding='utf-8') as f:
            json.dump(params, f, ensure_ascii=False, indent=4)
        print(f"파라미터 저장 완료: {params_file_abs_path}")
    except IOError as e:
        st.error(f"{params_file_abs_path} 저장 실패: {e}")
        return None
    except Exception as e:
        st.error(f"파라미터 저장 중 예상치 못한 오류: {e}")
        return None

    # 스크립트 순차 실행
    # 1. fetch_cortars.py 실행 (params.json 경로를 인자로 전달)
    print("\n--- fetch_cortars.py 실행 시작 ---")
    # run_external_script에 전달하는 경로는 CWD(프로젝트 루트) 기준 상대 경로여야 함
    if not run_external_script('fetch_cortars.py', params_file_rel_path):
        st.error("fetch_cortars.py 스크립트 실행 중 오류가 발생했습니다.")
        return None # 오류 발생 시 중단
    print("--- fetch_cortars.py 실행 완료 ---")

    # 동 이름 가져오기 시도
    st.session_state['dong_name'] = get_dong_name_from_file(output_dir)
    print(f"동 이름 가져오기 결과: {st.session_state['dong_name']}")

    # 2. fetch_marker_ids.py 실행 (별도 인자 없음)
    print("\n--- fetch_marker_ids.py 실행 시작 ---")
    if not run_external_script('fetch_marker_ids.py'):
        st.error("fetch_marker_ids.py 스크립트 실행 중 오류가 발생했습니다.")
        return None # 오류 발생 시 중단
    print("--- fetch_marker_ids.py 실행 완료 ---")

    # 3. collect_complex_details.py 실행 (별도 인자 없음)
    print("\n--- collect_complex_details.py 실행 시작 ---")
    if not run_external_script('collect_complex_details.py'):
        st.error("collect_complex_details.py 스크립트 실행 중 오류가 발생했습니다.")
        return None # 오류 발생 시 중단
    print("--- collect_complex_details.py 실행 완료 ---")

    # 최종 데이터 로드 (출력 디렉토리 사용)
    final_data_file_rel_path = os.path.join(output_dir, 'complex_details_by_district.json')
    final_data_file_abs_path = os.path.abspath(final_data_file_rel_path)
    print(f"\n최종 데이터 로드 시도: {final_data_file_abs_path}")
    try:
        with open(final_data_file_abs_path, 'r', encoding='utf-8') as file:
            loaded_data = json.load(file)
        st.session_state['current_data'] = loaded_data
        st.session_state['data_loaded'] = True
        st.success("데이터 로딩 완료!")
        print("데이터 로딩 성공")
        return loaded_data # 성공 시 데이터 반환
    except FileNotFoundError:
        st.error(f"{final_data_file_abs_path} 파일을 찾을 수 없습니다. 데이터 수집 과정에 문제가 있었을 수 있습니다.")
        print(f"오류: 최종 데이터 파일({final_data_file_abs_path}) 없음")
    except json.JSONDecodeError:
        st.error(f"{final_data_file_abs_path} 파일 파싱 오류.")
        print(f"오류: 최종 데이터 파일({final_data_file_abs_path}) JSON 파싱 실패")
    except Exception as e:
        st.error(f"최종 데이터 로드 오류 ({final_data_file_abs_path}): {e}")
        print(f"오류: 최종 데이터 로드 중 예상치 못한 오류: {e}")

    # 실패 시
    st.session_state['data_loaded'] = False
    st.session_state['current_data'] = None
    return None
