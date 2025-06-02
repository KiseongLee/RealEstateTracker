# src/config_page.py
import streamlit as st
import json
import time

def display_config_view():

    st.title("🛠️ 프로그램 초기 설정")
    st.markdown("""
    부동산 실시간 호가 검색 프로그램을 사용하기 위해서는 네이버 부동산 접속 정보(Header, Cookie)와 
    네이버 지도 API 키(Client ID, Client Secret)가 필요합니다.
    아래 정보를 입력해주세요. 입력된 정보는 현재 세션에만 저장됩니다.
    """)

    # 로컬 스토리지를 사용하지 않으므로, 입력 필드의 기본값은 빈 문자열로 설정합니다.
    default_header_str = st.session_state.get('user_header_str_input_cache', "") # 사용자가 이전에 입력했던 값을 유지하기 위한 임시 캐시 (선택적)
    default_cookie_str = st.session_state.get('user_cookie_str_input_cache', "")
    default_client_id = st.session_state.get('naver_client_id_input_cache', "")
    default_client_secret = st.session_state.get('naver_client_secret_input_cache', "")


    with st.form("config_page_form"): # 폼 키를 고유하게 설정
        # ==============================================================================
        # 1. 네이버 부동산 접속 정보 입력 #
        # ==============================================================================
        st.subheader("1. 네이버 부동산 접속 정보")
        st.markdown("""
        - **Header 정보**: 브라우저 개발자 도구(F12) -> Network 탭에서 `new.land.naver.com`으로 시작하는 요청 중 하나를 선택 -> Headers 탭 -> Request Headers 섹션에서 `authorization`을 포함한 주요 헤더들을 JSON 형식으로 복사하여 붙여넣으세요.
        예시: `{"authorization": "Bearer ...", "user-agent": "Mozilla/5.0 ..."}`
        - **Cookie 정보**: 동일한 요청의 Headers 탭 -> Request Headers 섹션의 `cookie` 항목 전체를 복사하여 붙여넣거나, 필요한 쿠키들을 `key1=value1; key2=value2` 형식 또는 JSON 형식으로 입력하세요.
        예시 (문자열): `NNB=XXXX; ASID=YYYY; ...`
        예시 (JSON): `{"NNB": "XXXX", "ASID": "YYYY"}`
        """)
        user_header_str_input = st.text_area("Header 정보 (JSON 형식)", value=default_header_str, height=150,
                                    placeholder='{"authorization": "Bearer ...", "user-agent": "..."}',
                                    key="config_header_input")
        header_error_placeholder = st.empty() # Header 오류 메시지 표시용 플레이스홀더

        user_cookie_str_input = st.text_area("Cookie 정보 (문자열 또는 JSON 형식)", value=default_cookie_str, height=100,
                                    placeholder='NNB=...; ASID=... 또는 {"NNB": "...", "ASID": "..."}',
                                    key="config_cookie_input")
        cookie_error_placeholder = st.empty() # Cookie 오류 메시지 표시용 플레이스홀더

        # ==============================================================================
        # 2. 네이버 지도 API 키 입력 #
        # ==============================================================================
        st.subheader("2. 네이버 지도 API 키 (역지오코딩용)")
        st.markdown("""
        - 네이버 클라우드 플랫폼에서 발급받은 **Reverse Geocoding API**의 Client ID와 Client Secret을 입력하세요.
        """)
        naver_client_id_input = st.text_input("네이버 API Client ID", value=default_client_id, type="password", 
                                        placeholder="여기에 Client ID 입력",
                                        key="config_client_id_input")
        client_id_error_placeholder = st.empty() # Client ID 오류 메시지 표시용 플레이스홀더

        naver_client_secret_input = st.text_input("네이버 API Client Secret", value=default_client_secret, type="password", 
                                            placeholder="여기에 Client Secret 입력",
                                            key="config_client_secret_input")
        client_secret_error_placeholder = st.empty() # Client Secret 오류 메시지 표시용 플레이스홀더

        submitted = st.form_submit_button("✅ 정보 저장 및 프로그램 실행")

        if submitted:
            # ==============================================================================
            # 3. 입력 정보 유효성 검사 및 저장 (개별 오류 처리) #
            # ==============================================================================
            # 이전 오류 메시지 클리어
            header_error_placeholder.empty()
            cookie_error_placeholder.empty()
            client_id_error_placeholder.empty()
            client_secret_error_placeholder.empty()

            all_valid = True # 모든 입력이 유효한지 추적하는 플래그

            # --- Header 파싱 및 유효성 검사 ---
            parsed_headers_for_session = None # 세션에 저장할 딕셔너리
            if user_header_str_input:
                st.session_state.user_header_str_input_cache = user_header_str_input # 입력값 캐시
                try:
                    parsed_headers_for_session = json.loads(user_header_str_input)
                    if not isinstance(parsed_headers_for_session, dict):
                        header_error_placeholder.error("Header 정보는 올바른 JSON 객체(딕셔너리) 형식이어야 합니다.")
                        all_valid = False
                        parsed_headers_for_session = None
                except json.JSONDecodeError:
                    header_error_placeholder.error("Header 정보가 올바른 JSON 형식이 아닙니다. 키와 값을 큰따옴표(\")로 정확히 감싸주세요.")
                    all_valid = False
            else:
                header_error_placeholder.error("Header 정보를 입력해주세요.")
                all_valid = False
            
            # --- Cookie 파싱 및 유효성 검사 ---
            parsed_cookies_for_session = {} # 세션에 저장할 딕셔너리
            if user_cookie_str_input:
                st.session_state.user_cookie_str_input_cache = user_cookie_str_input # 입력값 캐시
                try:
                    # JSON 형식 먼저 시도
                    parsed_cookies_for_session = json.loads(user_cookie_str_input)
                    if not isinstance(parsed_cookies_for_session, dict):
                        raise json.JSONDecodeError("Cookie JSON is not a dict", user_cookie_str_input, 0)
                except json.JSONDecodeError:
                    # JSON 파싱 실패 시, key=value; key=value 형식으로 파싱
                    parsed_cookies_for_session = {} # 초기화
                    for item in user_cookie_str_input.split(';'):
                        item = item.strip()
                        if '=' in item:
                            key_cookie, value_cookie = item.split('=', 1)
                            parsed_cookies_for_session[key_cookie.strip()] = value_cookie.strip()
                        elif item: # 값이 없는 쿠키
                            parsed_cookies_for_session[item.strip()] = True
                    
                    if not parsed_cookies_for_session and user_cookie_str_input:
                        cookie_error_placeholder.error("Cookie 정보 형식이 올바르지 않습니다. 유효한 JSON 또는 'key=value;' 문자열을 입력해주세요.")
                        all_valid = False
            else:
                cookie_error_placeholder.error("Cookie 정보를 입력해주세요.")
                all_valid = False
            
            if user_cookie_str_input and not parsed_cookies_for_session and all_valid:
                cookie_error_placeholder.error("Cookie 정보 형식이 유효하지 않습니다. (파싱 실패)")
                all_valid = False

            # --- Naver API Client ID 유효성 검사 ---
            if naver_client_id_input:
                st.session_state.naver_client_id_input_cache = naver_client_id_input # 입력값 캐시
            else:
                client_id_error_placeholder.error("네이버 API Client ID를 입력해주세요.")
                all_valid = False

            # --- Naver API Client Secret 유효성 검사 ---
            if naver_client_secret_input:
                st.session_state.naver_client_secret_input_cache = naver_client_secret_input # 입력값 캐시
            else:
                client_secret_error_placeholder.error("네이버 API Client Secret을 입력해주세요.")
                all_valid = False
            
            # --- 모든 유효성 검사 통과 시 처리 ---
            if all_valid:
                # 성공 시 세션 상태에 값 저장 및 플래그 설정
                st.session_state.user_headers = parsed_headers_for_session
                st.session_state.user_cookies = parsed_cookies_for_session
                st.session_state.naver_client_id = naver_client_id_input # input 변수 사용
                st.session_state.naver_client_secret = naver_client_secret_input # input 변수 사용
                
                # 로컬 스토리지를 사용하지 않으므로 관련 setItem 코드는 없음

                st.session_state.user_configs_set = True
                st.session_state.naver_api_keys_set = True
                
                # 성공 시 입력값 캐시 클리어 (선택적)
                for key_to_clear in ['user_header_str_input_cache', 'user_cookie_str_input_cache', 
                                    'naver_client_id_input_cache', 'naver_client_secret_input_cache']:
                    if key_to_clear in st.session_state:
                        del st.session_state[key_to_clear]
                
                st.success("정보가 성공적으로 저장되었습니다. 프로그램을 시작합니다...")
                time.sleep(1) # 성공 메시지를 사용자가 볼 수 있도록 잠시 대기
                st.rerun() # app.py를 다시 실행하여 메인 앱으로 넘어가도록 함
            # else: 오류 메시지는 이미 각 플레이스홀더에 표시됨

    # "저장된 설정 모두 지우기" 버튼 (로컬 스토리지 사용 안 함 버전)
    # 이 버튼은 폼 바깥에 있어야 폼 제출과 독립적으로 동작
    if st.button("🗑️ 현재 입력된 세션 설정 초기화", key="clear_session_config_button_outside_form"):
        # 세션 상태의 관련 값들을 모두 초기화
        st.session_state.user_configs_set = False
        st.session_state.naver_api_keys_set = False
        st.session_state.user_headers = None
        st.session_state.user_cookies = None
        st.session_state.naver_client_id = None
        st.session_state.naver_client_secret = None
        # 입력 필드 캐시도 초기화
        for key_to_clear in ['user_header_str_input_cache', 'user_cookie_str_input_cache', 
                            'naver_client_id_input_cache', 'naver_client_secret_input_cache']:
            if key_to_clear in st.session_state:
                del st.session_state[key_to_clear]

        st.session_state.trigger_api_key_error_on_config_page = False # 혹시 설정되어 있었다면 초기화
        st.info("현재 세션의 설정 정보가 초기화되었습니다. 다시 입력해주세요.")
        time.sleep(1.5)
        st.rerun()
