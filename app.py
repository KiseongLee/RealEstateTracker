# app.py
import streamlit as st
import pandas as pd
import sys # 로그 출력을 위해 추가

from src.config_page import display_config_view
from src.main_app_page import display_main_app_view

# ==============================================================================
#### 1. 세션 상태 초기화 ####
# ==============================================================================
default_session_values = {
    'last_coords': None, 'current_df': pd.DataFrame(), 'dong_name': None,
    'is_fetching': False, 'coords_to_fetch': None, 'selected_areas': {},
    'last_click_time': 0, 'fetch_start_time': None, 'error_message': None,
    'group_add_status': None,
    'user_configs_set': False, 'naver_api_keys_set': False,
    'user_headers': None, 'user_cookies': None,
    'naver_client_id': None, 'naver_client_secret': None,
    'force_redirect_to_config': False, # 리디렉션 강제 플래그
    'show_api_key_error_popup_on_main_page': False # main_app_page 팝업 플래그
}
for key, value in default_session_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ==============================================================================
#### 0. 강제 리디렉션 처리 (API 키 에러 등) ####
# ==============================================================================
if st.session_state.get('force_redirect_to_config', False):
    print("App.py: 'force_redirect_to_config' is True. Resetting config flags for redirection.", file=sys.stderr)
    st.session_state.user_configs_set = False    
    st.session_state.naver_api_keys_set = False 
    st.session_state.naver_client_id = None 
    st.session_state.naver_client_secret = None
    st.session_state.force_redirect_to_config = False # 플래그 리셋
    # show_api_key_error_popup_on_main_page는 main_app_page에서 관리

# ==============================================================================
#### 2. 페이지 설정 (st.set_page_config) ####
# ==============================================================================
if not st.session_state.get('user_configs_set') or not st.session_state.get('naver_api_keys_set'):
    st.set_page_config(page_title="프로그램 초기 설정", layout="centered", initial_sidebar_state="collapsed")
else:
    st.set_page_config(page_title="부동산 실시간 호가 검색 프로그램", layout="wide")
    
# ==============================================================================
#### 3. 라우팅 로직 ####
# ==============================================================================
if not st.session_state.get('user_configs_set') or not st.session_state.get('naver_api_keys_set'):
    print("App.py: Routing to config page.", file=sys.stderr)
    display_config_view()
else:
    # 메인 페이지로 가기 전에, 혹시 main_app_page에서 팝업을 띄워야 하는지 확인
    # (실제로는 display_main_app_view 내부에서 팝업을 띄우므로, 이 조건은 중복일 수 있음)
    # 하지만 명시적으로 main_app_page를 호출
    print("App.py: Routing to main app page.", file=sys.stderr)
    display_main_app_view()
