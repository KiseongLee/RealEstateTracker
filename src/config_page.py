# src/config_page.py
import streamlit as st
import time

def display_config_view():
    st.title("🛠️ API 키 설정")
    st.markdown("네이버 지도 API(Reverse Geocoding) 사용을 위해 발급받은 **Client ID**와 **Client Secret**을 입력해주세요.")

    default_client_id = st.session_state.get('naver_client_id_input_cache', "")
    default_client_secret = st.session_state.get('naver_client_secret_input_cache', "")

    with st.form("api_key_form"):
        naver_client_id_input = st.text_input("네이버 API Client ID", value=default_client_id, type="password")
        naver_client_secret_input = st.text_input("네이버 API Client Secret", value=default_client_secret, type="password")
        
        submitted = st.form_submit_button("✅ 키 저장 및 프로그램 실행")

        if submitted:
            all_valid = True
            if not naver_client_id_input:
                st.error("네이버 API Client ID를 입력해주세요.")
                all_valid = False
            if not naver_client_secret_input:
                st.error("네이버 API Client Secret을 입력해주세요.")
                all_valid = False

            if all_valid:
                # 성공 시 세션 상태에 값 저장 및 플래그 설정
                st.session_state.naver_client_id = naver_client_id_input
                st.session_state.naver_client_secret = naver_client_secret_input
                st.session_state.naver_api_keys_set = True # API 키만 설정되었음을 표시

                st.success("API 키가 성공적으로 저장되었습니다. 프로그램을 시작합니다...")
                time.sleep(1)
                st.rerun()

    if st.button("🗑️ 저장된 API 키 초기화"):
        st.session_state.naver_api_keys_set = False
        st.session_state.naver_client_id = None
        st.session_state.naver_client_secret = None
        st.info("저장된 API 키 정보가 초기화되었습니다.")
        time.sleep(1)
        st.rerun()