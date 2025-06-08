# src/main_app_page.py
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium
import os
import time
import folium
import sys

# 다른 모듈에서 필요한 함수들 임포트 (src 패키지 경로 사용)
from src.utils import create_article_url, shorten_text, get_current_date_str
from src.data_handling import fetch_data # 이 fetch_data는 st.session_state를 사용하도록 수정되어야 함
from src.data_processor import filter_out_low_floors, sort_dataframe, create_summary, extract_year_from_string
from src.exporters import to_excel, export_combined_excel
from src.ui_elements import create_folium_map, display_table_with_aggrid

# 데이터 가져오기 캐시 함수 (이전과 동일, 반환값 3개 유의)
@st.cache_data(ttl=600)
def cached_fetch_data_main(coords_tuple, output_dir_param):
    print(f"--- cached_fetch_data_main 호출 for {coords_tuple} ---", file=sys.stderr)
    return fetch_data(coords_tuple, output_dir_param)
def display_main_app_view():
    """
    메인 애플리케이션의 UI와 로직을 표시합니다.
    API 키 오류 시 현재 페이지에 팝업을 띄우고, 확인 시 설정 페이지로 이동합니다.
    """
# ==============================================================================
# 0. API 키 오류 팝업 처리 (페이지 상단) ####
# ==============================================================================
    if st.session_state.get('show_api_key_error_popup_on_main_page', False):
        @st.dialog("API 키 인증 오류")
        def show_api_key_error_modal_on_main():
            st.error("네이버 API 키 인증에 실패했습니다 (401 Unauthorized).\nAPI 키를 확인하고 올바른 값으로 다시 등록해주세요.")
            if st.button("확인", key="api_key_error_modal_confirm_on_main"):
                st.session_state.show_api_key_error_popup_on_main_page = False # 팝업 플래그 리셋
                st.session_state.force_redirect_to_config = True # 리디렉션 플래그 설정
                st.rerun() # app.py가 리디렉션 처리하도록 rerun
        
        show_api_key_error_modal_on_main() # 팝업 함수 호출
        # 팝업이 떠 있는 동안에는 아래 UI 렌더링이 중단될 수 있으므로,
        # 사용자가 "확인"을 누르면 rerun되어 app.py에서 리디렉션이 일어납니다.
    elif st.session_state.get('error_popup_on_main_page', False):
        @st.dialog("일반 오류")
        def show_error_modal_on_main():
            st.error("Error 발생. \nCookie와 Header를 확인하고 올바른 값으로 다시 등록해주세요.")
            if st.button("확인", key="api_key_error_modal_confirm_on_main"):
                st.session_state.error_popup_on_main_page = False # 팝업 플래그 리셋
                st.session_state.force_redirect_to_config = True # 리디렉션 플래그 설정
                st.rerun() # app.py가 리디렉션 처리하도록 rerun
        
        show_error_modal_on_main() # 팝업 함수 호출
# ==============================================================================
# 1. 페이지 기본 정보 및 스타일 설정 (이전과 동일) ####
# ==============================================================================
    st.title("부동산 실시간 호가 검색 프로그램")
    text = "네이버 부동산 API를 사용하여 특정 좌표에 대한 부동산 목록을 가져와서 표시합니다.<br>조회 기준은 300세대 이상 아파트 입니다."
    st.markdown(text, unsafe_allow_html=True)

    # 메인 앱 범위에서 사용할 상수 및 변수 
    OUTPUT_DIR = "output" 
    os.makedirs(OUTPUT_DIR, exist_ok=True) 
    current_date = get_current_date_str()

    # HTML/CSS 코드 (전체 화면 오버레이)
    custom_css = """
    <style>
    .fullscreen-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background-color: rgba(0, 0, 0, 0.65); z-index: 99999;
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        color: white; font-family: sans-serif;
    }
    .loading-spinner-small {
        border: 6px solid #f3f3f3; border-top: 6px solid #007bff;
        border-radius: 50%; width: 60px; height: 60px;
        animation: spin 1s linear infinite;
    }
    .loading-text { margin-top: 20px; font-size: 1.2em; letter-spacing: 1px; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
    """
    overlay_html_with_text = """
    <div class="fullscreen-overlay">
        <div class="loading-spinner-small"></div>
        <div class="loading-text">⏳ 데이터를 가져오는 중입니다...</div>
    </div>
    """
    st.markdown(custom_css, unsafe_allow_html=True) # CSS는 한 번만 주입
# ==============================================================================
# 2. 팝업 다이얼로그 및 콜백 함수 정의 #
# ==============================================================================
    @st.dialog("알림")
    def display_group_add_status_dialog_main():
        status = st.session_state.get('group_add_status')
        if not status:
            st.warning("표시할 메시지가 없습니다.")
            _, col_btn_close, _ = st.columns([1, 0.5, 1])
            with col_btn_close:
                if st.button("닫기", key="dialog_close_button_main", use_container_width=True):
                    st.session_state.group_add_status = None
                    st.rerun()
            return

        message = status.get("message", "알 수 없는 정보입니다.")
        msg_type = status.get("type", "info")

        if msg_type == "success": st.success(message)
        elif msg_type == "warning": st.warning(message)
        else: st.info(message)

        col_spacer1, col_button, col_spacer2 = st.columns([1, 0.5, 1])
        with col_button:
            if st.button("확인", key="dialog_confirm_button_main", use_container_width=True):
                st.session_state.group_add_status = None
                st.rerun()
    
    # 그룹 추가 상태 메시지 다이얼로그 표시 (필요시)
    if st.session_state.get('group_add_status'):
        display_group_add_status_dialog_main()

    # 콜백 함수 정의
    def handle_map_click_main():
        map_state = st.session_state.get('folium_map_interaction_main') # folium 위젯 키와 일치
        if not map_state or not map_state.get('last_clicked'):
            return

        lat, lng = map_state['last_clicked']['lat'], map_state['last_clicked']['lng']
        if st.session_state.is_fetching:
            print("Callback_main: 데이터 조회 중 - 클릭 무시")
            return
        
        if None in (lat, lng): return
        
        last_click_time = st.session_state.get('last_click_time', 0)
        current_time_cb = time.time() # 변수명 충돌 피하기
        if current_time_cb - last_click_time < 0.5:
            print(f"Callback_main: 디바운스 - 연속 클릭 무시 ({current_time_cb - last_click_time:.3f}s)")
            return
        
        clicked_coords_tuple = (lat, lng)
        print(f"Callback_main: 새 좌표 감지 {clicked_coords_tuple}")
        
        st.session_state.last_click_time = current_time_cb
        st.session_state.coords_to_fetch = clicked_coords_tuple
        st.session_state.is_fetching = True
        st.session_state.fetch_start_time = current_time_cb
        st.session_state.error_message = None
        st.session_state.dong_name = None
        st.session_state.current_df = pd.DataFrame()
# ==============================================================================
# 3. UI 레이아웃 구성 (지도, 그룹 관리, 오버레이) ####
# ==============================================================================
    # --- 오버레이 조건부 표시  ---
    # custom_css는 위에서 이미 markdown으로 주입됨
    if st.session_state.is_fetching:
        st.markdown(overlay_html_with_text, unsafe_allow_html=True)
        print("Main App Page: is_fetching is True. 오버레이 표시.")
        
    # --- 지도 및 선택 지역 목록 레이아웃  ---
    left_column, right_column = st.columns([3, 1])

    with left_column:
        st.markdown("### 🗺️ 지도에서 위치 클릭")
        folium_map_instance = create_folium_map() # from src.ui_elements
        map_interaction_return_value = st_folium(
            folium_map_instance,
            width=1300, height=600,
            key='folium_map_interaction_main', # 고유 키 사용
            returned_objects=['last_clicked'],
            on_change=handle_map_click_main
        )

    with right_column:
        st.markdown("### 🗂️ 선택된 지역 그룹")
        selected_areas = st.session_state.get('selected_areas', {})
        if not selected_areas:
            st.info("지도에서 위치를 클릭하고 데이터를 조회한 후, '지역 추가' 버튼을 눌러 그룹을 생성하세요.")
        else:
            display_names = []
            for (division, dong, exclude_low_floors_flag) in selected_areas.keys(): # 변수명 일치
                suffix = ' (저층 제외)' if exclude_low_floors_flag else ''
                display_names.append(f"{division} {dong}{suffix}")
            
            selected_idx = st.selectbox("관리할 지역 그룹 선택:", range(len(display_names)),
                                        format_func=lambda x: display_names[x], 
                                        index=0 if display_names else None,
                                        key="group_selectbox_main") # 고유 키
            if selected_idx is not None:
                cols_manage = st.columns([0.5, 0.5])
                with cols_manage[0]:
                    if st.button("🗑️ 선택 그룹 삭제", key="delete_selected_area_main"): # 고유 키
                        selected_key_to_delete = list(selected_areas.keys())[selected_idx]
                        del st.session_state.selected_areas[selected_key_to_delete]
                        st.success(f"'{display_names[selected_idx]}' 그룹이 삭제되었습니다.")
                        st.rerun()
                with cols_manage[1]:
                    if st.button("🧹 전체 그룹 초기화", key="clear_all_areas_main"): # 고유 키
                        st.session_state.selected_areas = {}
                        st.success("모든 지역 그룹이 초기화되었습니다.")
                        st.rerun()
                st.markdown("---")

        if st.button("📊 종합 리포트 생성", key="generate_combined_report_main"): # 고유 키
            if selected_areas:
                try:
                    with st.spinner("종합 리포트 생성 중..."):
                        excel_data = export_combined_excel(st.session_state.selected_areas, current_date) # from src.exporters
                    
                    # --- ▼▼▼ 파일명 생성 로직 ▼▼▼ ---
                    first_dong_name_for_filename = "선택지역없음" # 기본값
                        # 첫 번째 키 (튜플)를 가져옵니다.
                    first_key_tuple = next(iter(selected_areas.keys()), None) 
                    if first_key_tuple and len(first_key_tuple) >= 2:
                        # 튜플의 두 번째 요소가 '동' 이름입니다.
                        # 파일명에 부적합한 문자가 있을 경우를 대비해 간단한 처리 (예: 공백을 밑줄로)
                        gu_part = str(first_key_tuple[0]).replace(" ", "_")  # '구' 정보 (공백을 밑줄로)
                        dong_part = str(first_key_tuple[1]).replace(" ", "_") # '동' 정보 (공백을 밑줄로)
                        first_gu_dong_name_for_filename = f"{gu_part} {dong_part}" # "00구 00동" 형태로 조합
                
                    # 파일명에 포함될 상세 설명 부분 생성
                    filename_detail_part = ""
                    num_selected_areas = len(selected_areas)
                    if num_selected_areas == 1:
                        filename_detail_part = f"({first_gu_dong_name_for_filename})"
                    elif num_selected_areas > 1:
                        filename_detail_part = f"({first_gu_dong_name_for_filename} 외)"
                    # num_selected_areas가 0인 경우는 selected_areas가 비어있을 때이며, 이 경우 버튼 비활성화 또는 다른 처리 필요
                    # 현재 로직은 if selected_areas: 블록 안에 있으므로 num_selected_areas는 최소 1입니다.

                    final_report_filename = f"종합_부동산_분석{filename_detail_part}_{current_date}.xlsx"
                    # --- ▲▲▲ 파일명 생성 로직 수정 완료 ▲▲▲ ---
                    
                    st.download_button(
                        label="⬇️ 종합 리포트 다운로드 (.xlsx)",
                        data=excel_data,
                        file_name=final_report_filename,
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key="download_combined_report_main" # 고유 키
                    )
                    st.success("종합 리포트 생성이 완료되었습니다.")
                except Exception as e:
                    st.error(f"리포트 생성 실패: {str(e)}")
            else:
                st.warning("리포트를 생성할 선택된 지역 그룹이 없습니다.")
# ==============================================================================
# 4. 메인 데이터 조회 및 처리 로직 #
# ==============================================================================    
    # ---  메인 데이터 조회 및 처리 로직 ---
    print(f"\n=== Rerun Start (Main App Page) ===") # 로그 추가
    print(f"is_fetching: {st.session_state.is_fetching}")
    print(f"coords_to_fetch: {st.session_state.coords_to_fetch}")

    coords_to_fetch_now = st.session_state.get('coords_to_fetch')
    # API 키 오류 팝업이 떠야 하는 상황이 아니고, 실제로 데이터를 가져와야 할 때만 아래 로직 실행
    if not st.session_state.get('show_api_key_error_popup_on_main_page') and not st.session_state.get('error_popup_on_main_page') and coords_to_fetch_now is not None and st.session_state.get('is_fetching'):
        
        print(f"Main App Page Logic: 데이터 조회 시작 - {coords_to_fetch_now}", file=sys.stderr)
        st.session_state.coords_to_fetch = None # 한 번만 조회하도록 초기화
        try:
            print(f"Main App Page Logic: cached_fetch_data_main 호출 ({coords_to_fetch_now}, {OUTPUT_DIR})")
            df_fetched, dong_name_from_fetch, error_signal = cached_fetch_data_main(coords_to_fetch_now, OUTPUT_DIR)
            
            # ======================== ▼▼▼ 에러 신호 처리 ▼▼▼ ========================
            # ======================== API KEY ERROR =============================
            if error_signal == "API_KEY_ERROR_SIGNAL":
                print("Main App Page: API Key Error Signal received from fetch_data.", file=sys.stderr)
                st.session_state.show_api_key_error_popup_on_main_page = True # 현재 페이지에 팝업 띄우기
                st.session_state.is_fetching = False # 로딩 중 상태 해제
                st.rerun() # app.py의 라우팅 로직을 다시 타도록 함
                return # 현재 display_main_app_view 함수 실행 중단 (rerun이 실행 흐름을 변경)
            # ======================== 일반적 ERROR(Cookie, Header) =============================
            elif error_signal == "ERROR":
                print("Main App Page: Error Signal received from fetch_data.", file=sys.stderr)
                st.session_state.error_popup_on_main_page = True # 현재 페이지에 팝업 띄우기
                st.session_state.is_fetching = False # 로딩 중 상태 해제
                st.rerun() # app.py의 라우팅 로직을 다시 타도록 함
                return # 현재 display_main_app_view 함수 실행 중단 (rerun이 실행 흐름을 변경)
            # ======================== ▲▲▲ API 키 에러 신호 처리 ▲▲▲ ========================
            
            if dong_name_from_fetch and dong_name_from_fetch != "Unknown":
                st.session_state.dong_name = dong_name_from_fetch
            else:
                st.session_state.dong_name = "지역명 확인 불가"

            if df_fetched is not None and not df_fetched.empty:
                df_processed = df_fetched.copy()
                df_processed['매물 링크'] = df_processed.apply(
                    lambda x: create_article_url(
                        x.get('articleNo'), x.get('markerId'),
                        x.get('latitude'), x.get('longitude')
                    ), axis=1
                )
                if 'completionYearMonth' in df_processed.columns:
                    df_processed['completionYearMonth'] = df_processed['completionYearMonth'].apply(
                        extract_year_from_string
                    ).astype('Int64')
                if 'totalHouseholdCount' in df_processed.columns:
                    df_processed['totalHouseholdCount'] = pd.to_numeric(
                        df_processed['totalHouseholdCount'], errors='coerce'
                    ).astype('Int64')
                if 'sameAddrCnt' in df_processed.columns:
                    df_processed['sameAddrCnt'] = pd.to_numeric(
                        df_processed['sameAddrCnt'], errors='coerce'
                    ).astype('Int64')

                st.session_state.current_df = df_processed
                st.session_state.last_coords = {'lat': coords_to_fetch_now[0], 'lng': coords_to_fetch_now[1]}
                print(f"Main App Page Logic: 데이터 처리 성공 ({len(df_processed)} rows)")
                # fetch_success_flag = True
            else:
                st.session_state.current_df = pd.DataFrame()
                st.session_state.last_coords = {'lat': coords_to_fetch_now[0], 'lng': coords_to_fetch_now[1]}
                print("Main App Page Logic: 조회 완료 - 데이터 없음")
                # fetch_success_flag = True # 데이터가 없어도 조회 자체는 성공으로 간주 가능

        except Exception as e:
            error_msg = f"데이터 조회 중 오류 발생: {str(e)}"
            st.session_state.error_message = error_msg
            st.session_state.current_df = pd.DataFrame()
            st.session_state.dong_name = None
            st.session_state.last_coords = None
            print(f"Main App Page Logic: Exception 발생 - {error_msg}")
            st.error(error_msg) # UI에 즉시 에러 표시
            # st.exception(e) # 디버깅 시 상세 traceback 표시용

        finally:
            # 이 finally 블록은 API 키 에러로 인해 위에서 return 되기 전에 실행될 수도 있고,
            # rerun() 호출로 인해 실행 흐름이 바뀌어 도달하지 않을 수도 있습니다.
            # API 키 에러로 인한 강제 리디렉션 플래그가 설정되지 않았을 때만 is_fetching을 False로 설정하고 rerun합니다.
            if not st.session_state.get('force_redirect_to_config'): # API 키 에러로 인한 강제 리디렉션이 아닐 때만
                print("Main App Page Logic: finally 블록 - 일반적인 경우", file=sys.stderr)
                st.session_state.is_fetching = False 
                st.session_state.fetch_start_time = None
                print(f"Main App Page Logic: finally - is_fetching을 False로 설정 완료.", file=sys.stderr)
                st.rerun() # 상태 변경 후 UI 즉시 새로고침하여 결과 표시
            else:
                print("Main App Page Logic: finally 블록 - force_redirect_to_config is True, no extra rerun from here.", file=sys.stderr)
# ==============================================================================
# 5. 데이터 테이블 및 관련 UI 표시 #
# ==============================================================================
    if not st.session_state.is_fetching: # is_fetching이 False일 때만 아래 내용 표시
        print("Main App Page UI Display: is_fetching is False. 화면 내용 표시 시도.")
        if st.session_state.error_message:
            st.error(st.session_state.error_message)
        elif st.session_state.dong_name and st.session_state.current_df.empty and st.session_state.last_coords:
            st.info(f"{st.session_state.dong_name} 지역의 매물 데이터가 없거나 불러오지 못했습니다.")
        elif not st.session_state.current_df.empty and st.session_state.dong_name:
            current_dong_name_main = st.session_state.dong_name # 변수명 구분
            df_display_source_main = st.session_state.current_df.copy() # 변수명 구분
            
            st.subheader(f"📍 현재 조회된 지역: {current_dong_name_main}")
            
            display_columns_map = {
                "articleName": "매물명", "divisionName": "구", "cortarName": "동",
                "completionYearMonth": "연식", "totalHouseholdCount": "총세대수",
                "buildingName": "동/건물명", "dealOrWarrantPrc": "가격",
                "tradeTypeName": "거래유형", "floorInfo": "층수", "areaName": "공급면적",
                "direction": "방향", "articleFeatureDesc": "특징", "tagList": "태그",
                "realtorName": "중개사", "sameAddrCnt": "단지매물수", "cpName": "정보제공",
                "매물 링크": "매물 링크"
            }
            cols_to_display = [col for col in display_columns_map.keys() if col in df_display_source_main.columns]
            df_display = df_display_source_main[cols_to_display].rename(columns=display_columns_map)

            target_column_order = [
                "매물명", "구", "동", "연식", "총세대수", "동/건물명", "가격",
                "거래유형", "층수", "공급면적", "방향","태그", "특징",
                "매물 링크","단지매물수", "중개사", "정보제공"
            ]
            existing_cols_in_order = [col for col in target_column_order if col in df_display.columns]
            if existing_cols_in_order: # 컬럼이 하나라도 존재할 때만 순서 변경
                df_display = df_display[existing_cols_in_order]
            
            text_shorten_cols = ['매물명', '특징', '태그', '중개사', '정보제공']
            for col in text_shorten_cols:
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(lambda x: shorten_text(str(x))) # from src.utils

            cols_header = st.columns([8, 2])
            with cols_header[0]:
                element_cols = st.columns([3.05, 2.5, 2.5, 1.95])
                with element_cols[0]:
                    st.write(f"##### {current_dong_name_main} 근처 매물 목록 ({len(df_display)}개)")
                with element_cols[1]:
                    sort_options = ['가격', '매물명', '연식', '공급면적', '총세대수']
                    available_sort_options = [opt for opt in sort_options if opt in df_display.columns]
                    selected_sort_options = st.multiselect(
                        '정렬 기준', options=available_sort_options, default=['가격'] if '가격' in available_sort_options else None,
                        key=f'sort_multiselect_{current_dong_name_main.replace(" ", "_")}_main', label_visibility='collapsed' # 고유 키
                    )
                with element_cols[2]:
                    order_options = ['오름차순', '내림차순']
                    selected_order_option = st.selectbox(
                        '정렬 순서', options=order_options, index=0,
                        key=f'order_select_{current_dong_name_main.replace(" ", "_")}_main', label_visibility='collapsed' # 고유 키
                    )
                # element_cols[3]는 paste.txt에서 비어있었음
            
            df_final_display = df_display # 초기값 (필터링 및 정렬 전)
            with cols_header[1]:
                button_cols = st.columns([0.05, 0.35, 0.25, 0.35])
                with button_cols[1]:
                    exclude_low_floors_flag_ui = st.checkbox("저층 제외", 
                                                    key=f'low_floor_check_{current_dong_name_main.replace(" ", "_")}_main', # 고유 키
                                                    value=False)
            
                df_filtered = filter_out_low_floors(df_display, exclude_low_floors_flag_ui) # from src.data_processor
                if selected_sort_options:
                    ascending_order = True if selected_order_option == '오름차순' else False
                    df_sorted = sort_dataframe(df_filtered, selected_sort_options, [ascending_order] * len(selected_sort_options)) # from src.data_processor
                else:
                    df_sorted = df_filtered
                df_final_display = df_sorted # 최종적으로 표시할 데이터프레임

                with button_cols[2]:
                    if not df_final_display.empty:
                        summary_df_current = create_summary(df_final_display) # from src.data_processor
                        if summary_df_current is None: summary_df_current = pd.DataFrame()
                        
                        excel_data = to_excel(df_final_display, summary_df_current, current_dong_name_main, current_date, exclude_low_floors_flag_ui) # from src.exporters
                        st.download_button(
                            label="Excel", data=excel_data,
                            file_name=f"{current_dong_name_main}_{current_date}{'_저층제외' if exclude_low_floors_flag_ui else ''}.xlsx",
                            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            key=f'excel_dl_{current_dong_name_main.replace(" ", "_")}_main' # 고유 키
                        )
                with button_cols[3]:
                    division_ui, dong_ui = "Unknown", "Unknown" # 변수명 구분
                    parts_ui = current_dong_name_main.split(' ', 1)
                    if len(parts_ui) == 2: division_ui, dong_ui = parts_ui[0], parts_ui[1]
                    
                    unique_key_ui = (division_ui, dong_ui, exclude_low_floors_flag_ui)
                    add_button_label = f"그룹 추가"
                    if st.button(add_button_label, key=f'add_area_{current_dong_name_main.replace(" ", "_")}_main'): # 고유 키
                        MAX_GROUPS = 5
                        current_selected_areas_count = len(st.session_state.selected_areas)
                        message_to_show, message_type = "", ""

                        if unique_key_ui in st.session_state.selected_areas:
                            message_to_show = f"'{division_ui} {dong_ui}{' (저층 제외)' if exclude_low_floors_flag_ui else ''}' 그룹은 이미 존재합니다."
                            message_type = "warning"
                        elif current_selected_areas_count >= MAX_GROUPS:
                            message_to_show = f"더 이상 그룹을 추가할 수 없습니다. (최대 {MAX_GROUPS}개)"
                            message_type = "warning"
                        else:
                            summary_for_group = create_summary(df_final_display) # from src.data_processor
                            st.session_state.selected_areas[unique_key_ui] = {
                                'detail': df_final_display.copy(),
                                'summary': summary_for_group.copy() if summary_for_group is not None else pd.DataFrame()
                            }
                            new_count = len(st.session_state.selected_areas)
                            message_to_show = f"'{division_ui} {dong_ui}{' (저층 제외)' if exclude_low_floors_flag_ui else ''}' 그룹 추가됨. (현재 {new_count}/{MAX_GROUPS}개)"
                            message_type = "success"
                        
                        st.session_state.group_add_status = {"message": message_to_show, "type": message_type}
                        # display_group_add_status_dialog_main() # 다이얼로그를 여기서 호출하거나, rerun 후 상단에서 처리
                        st.rerun() # 상태 변경 후 UI 반영 위해 rerun

            if not df_final_display.empty:
                display_table_with_aggrid(df_final_display) # from src.ui_elements
        
        elif not st.session_state.coords_to_fetch and not st.session_state.last_coords and not st.session_state.error_message:
            st.info("👈 지도를 클릭하여 지역을 선택하면 해당 지역의 매물 정보를 조회합니다.")

# ==============================================================================
# 5. 앱 하단 정보 #
# ==============================================================================
    st.markdown("---")
    st.caption("부동산 데이터는 네이버 부동산 정보를 기반으로 제공됩니다.")
