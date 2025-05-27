# app.py
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium # 지도 상호작용 위해 필요
import os # 파일 경로 지정을 위해 추가
import time
import folium
# 다른 모듈에서 필요한 함수들 임포트 (src 패키지 경로 사용)
from src.utils import create_article_url, shorten_text, get_current_date_str # shorten_text 추가 임포트
from src.data_handling import fetch_data
from src.data_processor import filter_out_low_floors, sort_dataframe, create_summary, extract_year_from_string
from src.exporters import to_excel, export_combined_excel
from src.ui_elements import create_folium_map, display_table_with_aggrid

# ==============================================================================
# 기본 설정 및 경로 정의
# ==============================================================================
st.set_page_config(page_title="부동산 실시간 호가 검색 프로그램", layout="wide")
st.title("부동산 실시간 호가 검색 프로그램")
text = "네이버 부동산 API를 사용하여 특정 좌표에 대한 부동산 목록을 가져와서 표시합니다.<br>조회 기준은 300세대 이상 아파트 입니다.(재건축, 분양권 제외)"
st.markdown(text, unsafe_allow_html=True)

OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
current_date = get_current_date_str()

session_keys_with_defaults = {
    'last_coords': None,           # 마지막으로 성공적으로 조회된 좌표 딕셔너리 (UI 표시용)
    'current_df': pd.DataFrame(),  # 현재 표시할 메인 데이터프레임 (빈 DF로 초기화)
    'dong_name': None,             # 현재 조회된 지역명
    'is_fetching': False,          # 데이터 조회 중 상태 플래그 (False로 초기화)
    'coords_to_fetch': None,       # 콜백이 설정하는, 다음 실행 시 조회할 좌표 튜플
    'selected_areas': {},          # 지역 그룹 저장용 딕셔너리 (빈 딕셔너리로 초기화)
    'last_click_time': 0,          # 디바운스용 타임스탬프 추가
    'fetch_start_time': None,      # 조회 시작 시간 추가
    'error_message': None          # 에러 메시지 저장용 추가
}

for key, default_value in session_keys_with_defaults.items():
    if key not in st.session_state:
        st.session_state[key] = default_value
# ==============================================================================
# HTML/CSS 코드 (전체 화면 오버레이) - 새로 추가
# ==============================================================================
# 로딩 스피너 스타일 (CSS)
custom_css = """
<style>
.fullscreen-overlay {
    position: fixed; /* 화면 전체에 고정 */
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.65); /* 반투명도 살짝 더 어둡게 */
    z-index: 99999; /* 다른 모든 요소 위에 표시 */
    display: flex;
    flex-direction: column; /* 스피너와 텍스트를 세로로 정렬 */
    justify-content: center;
    align-items: center;
    color: white; /* 텍스트 색상 */
    font-family: sans-serif; /* 깔끔한 폰트 */
}

/* 새로운 스피너 스타일 (더 작고 세련되게) */
.loading-spinner-small {
    border: 6px solid #f3f3f3; /* 테두리 두께 줄임 */
    border-top: 6px solid #007bff; /* 파란색 계열 (Streamlit 기본 버튼과 유사) */
    border-radius: 50%;
    width: 60px; /* 크기 줄임 */
    height: 60px; /* 크기 줄임 */
    animation: spin 1s linear infinite; /* 애니메이션 속도 약간 빠르게 */
}

/* 로딩 텍스트 스타일 (선택 사항) */
.loading-text {
    margin-top: 20px; /* 스피너와의 간격 */
    font-size: 1.2em; /* 텍스트 크기 */
    letter-spacing: 1px; /* 자간 */
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
</style>
"""

# 오버레이 HTML (스피너 클래스 변경 및 로딩 텍스트 추가)
overlay_html_with_text = """
<div class="fullscreen-overlay">
    <div class="loading-spinner-small"></div>
    <div class="loading-text">⏳ 데이터를 가져오는 중입니다...</div>
</div>
"""

# ==============================================================================
# 콜백 함수 (디바운스 메커니즘 추가)
# ==============================================================================
def handle_map_click():
    map_state = st.session_state.get('folium_map_interaction')
    if not map_state or not map_state.get('last_clicked'):
        return

    lat, lng = map_state['last_clicked']['lat'], map_state['last_clicked']['lng']

    # --- is_fetching 상태일 때는 무시 (디바운싱 강화) ---
    if st.session_state.is_fetching:
        print("Callback: 데이터 조회 중 - 클릭 무시")
        return
    
    if None in (lat, lng): return
    
    # 디바운스 메커니즘 (500ms 내 중복 클릭 무시)
    last_click_time = st.session_state.get('last_click_time', 0)
    current_time = time.time()
    if current_time - last_click_time < 0.5:
        print(f"Callback: 디바운스 - 연속 클릭 무시 ({current_time - last_click_time:.3f}s)")
        return
    
    # 새로운 클릭 처리
    clicked_coords_tuple = (lat, lng)
    print(f"Callback: 새 좌표 감지 {clicked_coords_tuple}")
    
    # 상태 초기화 및 플래그 설정
    st.session_state.last_click_time = current_time
    st.session_state.coords_to_fetch = clicked_coords_tuple # UI 표시용으로만 사용될 수 있음
    st.session_state.is_fetching = True # "조회 시작" 상태로 즉시 변경
    st.session_state.fetch_start_time = current_time
    st.session_state.error_message = None # 이전 앱 레벨 에러 메시지 초기화
    
    # UI용 데이터 초기화
    st.session_state.dong_name = None
    st.session_state.current_df = pd.DataFrame()

# ==============================================================================
# 데이터 가져오기 (st.cache_data 적용)
# ==============================================================================
@st.cache_data(ttl=600) # 10분 동안 캐시 유지
def cached_fetch_data(coords_tuple, output_dir_param):
    print(f"--- cached_fetch_data 호출됨 (캐시 사용 또는 실제 fetch_data 실행) for {coords_tuple} ---")
    return fetch_data(coords_tuple, output_dir_param)
# ==============================================================================
# Streamlit UI 구성 및 메인 로직
# ==============================================================================

# --- 0. 오버레이 조건부 표시 ---
st.markdown(custom_css, unsafe_allow_html=True)
# --- 1. 오버레이 조건부 표시 ---
# is_fetching이 True이면, 다른 UI 요소들보다 먼저 오버레이를 그려서 화면을 덮도록 시도합니다.
# 이 코드는 스크립트 상단 근처에 위치하여 다른 UI 요소들 위에 오버레이가 그려지도록 합니다.
if st.session_state.is_fetching:
    st.markdown(overlay_html_with_text, unsafe_allow_html=True)
    print("Main App: is_fetching is True. 오버레이를 표시합니다.")
    # 오버레이가 활성화된 동안에는 사용자 입력을 막고, 백그라운드 작업이 진행됩니다.
    # 이 아래의 UI 요소들은 그려지더라도 오버레이에 가려지게 됩니다.
    
# --- 2. 지도 및 선택 지역 목록 레이아웃 ---
left_column, center_column, right_column = st.columns([1, 2, 1])

with center_column:
    st.markdown("### 🗺️ 지도에서 위치 클릭")
    folium_map = create_folium_map()
    map_interaction_return_value = st_folium(
        folium_map,
        width=950, height=500,
        key='folium_map_interaction',          # 콜백에서 상태 접근 위해 유지
        returned_objects=['last_clicked'],     # 반환값 유지 (디버깅 등)
        on_change=handle_map_click             # 콜백 함수 연결
    )

with right_column:
    # (선택된 지역 그룹 관리 UI - 변경 없음)
    st.markdown("### 🗂️ 선택된 지역 그룹")
    selected_areas = st.session_state.get('selected_areas', {})
    if not selected_areas:
        st.info("지도에서 위치를 클릭하고 데이터를 조회한 후, '지역 추가' 버튼을 눌러 그룹을 생성하세요.")
    else:
        display_names = []
        for (division, dong, exclude_low_floors) in selected_areas.keys():
            suffix = ' (저층 제외)' if exclude_low_floors else ''
            display_names.append(f"{division} {dong}{suffix}")
        selected_idx = st.selectbox("관리할 지역 그룹 선택:", range(len(display_names)),
                                    format_func=lambda x: display_names[x], index=0 if display_names else None)
        if selected_idx is not None:
            cols_manage = st.columns([0.5, 0.5])
            with cols_manage[0]:
                if st.button("🗑️ 선택 그룹 삭제", key="delete_selected_area"):
                    selected_key = list(selected_areas.keys())[selected_idx]
                    del st.session_state.selected_areas[selected_key]
                    st.success(f"'{display_names[selected_idx]}' 그룹이 삭제되었습니다.")
                    st.rerun()
            with cols_manage[1]:
                if st.button("🧹 전체 그룹 초기화", key="clear_all_areas"):
                    st.session_state.selected_areas = {}
                    st.success("모든 지역 그룹이 초기화되었습니다.")
                    st.rerun()
            st.markdown("---")
        if st.button("📊 종합 리포트 생성", key="generate_combined_report"):
            if selected_areas:
                try:
                    with st.spinner("종합 리포트 생성 중..."):
                        excel_data = export_combined_excel(st.session_state.selected_areas, current_date)
                    st.download_button(
                        label="⬇️ 종합 리포트 다운로드 (.xlsx)",
                        data=excel_data,
                        file_name=f"종합_부동산_분석_{current_date}.xlsx",
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key="download_combined_report"
                    )
                    st.success("종합 리포트 생성이 완료되었습니다.")
                except Exception as e:
                    st.error(f"리포트 생성 실패: {str(e)}")
            else:
                st.warning("리포트를 생성할 선택된 지역 그룹이 없습니다.")


# ==============================================================================
# 메인 로직 
# ==============================================================================

print(f"\n=== Rerun Start ===")
print(f"is_fetching: {st.session_state.is_fetching}")
print(f"coords_to_fetch: {st.session_state.coords_to_fetch}")
print(f"dong_name: {st.session_state.dong_name}")
print(f"current_df empty: {st.session_state.current_df.empty}")
print("=" * 20)

coords_to_fetch_now = st.session_state.coords_to_fetch
if coords_to_fetch_now is not None and st.session_state.is_fetching:
    print(f"Main Logic: 데이터 조회 시작 - {coords_to_fetch_now}")

    # 초기화
    st.session_state.coords_to_fetch = None

    fetch_success = False
    error_occurred = False
    try:
        # 실제 데이터 조회 (캐시된 함수 사용)
        print(f"Main Logic: cached_fetch_data 호출 ({coords_to_fetch_now}, {OUTPUT_DIR})")
        df_fetched, dong_name_from_fetch = cached_fetch_data(coords_to_fetch_now, OUTPUT_DIR)
        print(f"Main Logic: cached_fetch_data 반환 받음. Dong: '{dong_name_from_fetch}'")
        
        # 결과 처리
        if dong_name_from_fetch and dong_name_from_fetch != "Unknown":
            st.session_state.dong_name = dong_name_from_fetch
        else:
            st.session_state.dong_name = "지역명 확인 불가"

        if df_fetched is not None and not df_fetched.empty:
            df_processed = df_fetched.copy()
            # (후처리)
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
            st.session_state.last_coords = {
                'lat': coords_to_fetch_now[0],
                'lng': coords_to_fetch_now[1]
            }

            print(f"Main Logic: 데이터 처리 성공 ({len(df_processed)} rows)")
            fetch_success = True

        else: # 데이터 없는 경우
            st.session_state.current_df = pd.DataFrame()
            st.session_state.last_coords = {
                'lat': coords_to_fetch_now[0],
                'lng': coords_to_fetch_now[1]
            }

            print("Main Logic: 조회 완료 - 데이터 없음")
            fetch_success = True

    except Exception as e:
        error_occurred = True
        error_msg = f"데이터 조회 중 오류 발생: {str(e)}"
        st.session_state.error_message = error_msg

        # 오류 시 상태 초기화
        st.session_state.current_df = pd.DataFrame()
        st.session_state.dong_name = None
        st.session_state.last_coords = None

        print(f"Main Logic: Exception 발생 - {error_msg}")
        # 오류 표시
        st.error(error_msg)
        st.exception(e)

    finally:
        print("Main Logic: finally 블록 진입")
        # --- 중요: 작업 완료 후 is_fetching을 False로 설정하여 오버레이를 숨김 ---
        st.session_state.is_fetching = False
        st.session_state.fetch_start_time = None # 관련 타이머 초기화

        # 이전의 progress_placeholder 관련 코드는 오버레이 사용으로 불필요해졌으므로 제거합니다.
        # time.sleep(1)도 오버레이가 즉시 사라지는 것을 방해할 수 있으므로 제거하거나 조정합니다.

        print(f"Main Logic: finally - is_fetching을 {st.session_state.is_fetching}로 설정 완료.")
        # --- 중요: 상태 변경 후 UI를 즉시 새로고침하여 오버레이를 없애고 결과 데이터를 표시 ---
        st.rerun()

# ==============================================================================
# 데이터가 있을 때만 테이블 및 관련 UI 표시
# ==============================================================================
if not st.session_state.is_fetching:
    print("UI Display Section: is_fetching is False. 화면 내용 표시 시도.")
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        # 오류 메시지 표시 후 초기화 (선택 사항, 다음 rerun에서 계속 보이지 않도록)
        # st.session_state.error_message = None
    elif st.session_state.dong_name and st.session_state.current_df.empty:
        st.info(f"{st.session_state.dong_name} 지역의 매물 데이터가 없거나 불러오지 못했습니다.")
    elif not st.session_state.current_df.empty and st.session_state.dong_name:
        # (데이터 테이블 표시 로직 - paste.txt와 동일)
        current_dong_name = st.session_state.dong_name
        df_display_source = st.session_state.current_df.copy()
        st.subheader(f"📍 현재 조회된 지역: {current_dong_name}")
        # ... (이하 컬럼 매핑, 정렬, 버튼, AgGrid 등 테이블 표시 로직 전체를 여기에 포함) ...
            
        # --- 컬럼 선택 및 이름 변경 (기존 코드와 거의 동일) ---
        display_columns_map = {
            # JSON 키 -> 표시될 한글 컬럼명 (기존과 동일하게 유지)
            "articleName": "매물명", "divisionName": "구", "cortarName": "동",
            "completionYearMonth": "연식", "totalHouseholdCount": "총세대수",
            "buildingName": "동/건물명", "dealOrWarrantPrc": "가격",
            "tradeTypeName": "거래유형", "floorInfo": "층수", "areaName": "공급면적",
            "direction": "방향", "articleFeatureDesc": "특징", "tagList": "태그",
            "realtorName": "중개사", "sameAddrCnt": "단지매물수", "cpName": "정보제공",
            "매물 링크": "매물 링크"
        }
        # 원본 데이터의 컬럼을 기준으로 표시할 컬럼 선택
        cols_to_display = [col for col in display_columns_map.keys() if col in df_display_source.columns]
        # 이름 변경 및 선택된 컬럼만 포함하는 새 DataFrame 생성
        df_display = df_display_source[cols_to_display].rename(columns=display_columns_map)

        # --- 컬럼 순서 재정렬 (기존 코드와 거의 동일) ---
        target_column_order = [
            "매물명", "구", "동", "연식", "총세대수", "동/건물명", "가격",
            "거래유형", "층수", "공급면적", "방향","태그", "특징",
            "매물 링크","단지매물수", "중개사", "정보제공"
        ]
        existing_cols_in_order = [col for col in target_column_order if col in df_display.columns]
        df_display = df_display[existing_cols_in_order]
        
        if existing_cols_in_order:
            df_display = df_display[existing_cols_in_order]
        # 텍스트 줄이기 (Display용 처리 - 유지)
        text_shorten_cols = ['매물명', '특징', '태그', '중개사', '정보제공']
        for col in text_shorten_cols:
            if col in df_display.columns:
                df_display[col] = df_display[col].apply(lambda x: shorten_text(str(x)))

        # --- UI 컨트롤 (정렬, 필터, 버튼 등 - 기존 코드 구조 유지) ---
        cols_header = st.columns([8, 2])
        with cols_header[0]:
            element_cols = st.columns([3.05, 2.5, 2.5, 1.95])
            with element_cols[0]:
                st.write(f"##### {current_dong_name} 매물 목록 ({len(df_display)}개)")
            with element_cols[1]: # 복수 정렬 기준
                sort_options = ['가격', '매물명', '연식', '공급면적', '총세대수']
                available_sort_options = [opt for opt in sort_options if opt in df_display.columns or opt == '가격']
                selected_sort_options = st.multiselect(
                    '정렬 기준', options=available_sort_options, default=['가격'],
                    key=f'sort_multiselect_{current_dong_name}', label_visibility='collapsed'
                )
            with element_cols[2]: # 정렬 순서
                order_options = ['오름차순', '내림차순']
                selected_order_option = st.selectbox(
                    '정렬 순서', options=order_options, index=0,
                    key=f'order_select_{current_dong_name}', label_visibility='collapsed'
                )
            with element_cols[3]:
                st.write("") # 빈 공간으로 사용하여 버튼들을 오른쪽으로 밀기
        with cols_header[1]:
            button_cols = st.columns([0.05, 0.35, 0.25, 0.35])
            with button_cols[0]:
                st.write("")  # 빈 공간으로 사용하여 버튼들을 오른쪽으로 밀기
            with button_cols[1]: # 저층 제외
                exclude_low_floors = st.checkbox("저층 제외", key=f'low_floor_check_{current_dong_name}', value=False)

                # --- 데이터 필터링 및 정렬 적용 (기존 코드와 거의 동일) ---
                df_filtered = filter_out_low_floors(df_display, exclude_low_floors)
                if selected_sort_options:
                    sort_columns_for_func = []
                    for option in selected_sort_options:
                    # sort_dataframe 함수가 내부적으로 처리할 컬럼명 매핑 (가격, 공급면적 등)
                        sort_columns_for_func.append('가격' if option == '가격' else ('공급면적' if option == '공급면적' else option))
                        ascending_order = True if selected_order_option == '오름차순' else False
                        ascending_list_for_func = [ascending_order] * len(sort_columns_for_func)
                        df_sorted = sort_dataframe(df_filtered, sort_columns_for_func, ascending_list_for_func)
                else:
                    df_sorted = df_filtered
                df_final_display = df_sorted # 최종 표시할 데이터

            # --- 버튼들 (Excel, 그룹 추가 - 세션 상태 사용) ---
            with button_cols[2]: # Excel 다운로드
                if not df_final_display.empty:
                    # Excel 생성 시 현재 세션의 요약 데이터 사용
                    summary_df_current = create_summary(df_final_display)
                    # 요약 데이터가 비었을 경우 빈 DataFrame 전달 또는 에러 처리 필요
                    if summary_df_current is None: summary_df_current = pd.DataFrame()
                    excel_data = to_excel(df_final_display, summary_df_current, current_dong_name, current_date, exclude_low_floors)
                    st.download_button(
                        label="Excel", data=excel_data,
                        file_name=f"{current_dong_name}_{current_date}{'_저층제외' if exclude_low_floors else ''}.xlsx",
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key=f'excel_dl_{current_dong_name}'
                    )
            with button_cols[3]: # 지역 추가
                # area_name 대신 current_dong_name 사용
                division, dong = "Unknown", "Unknown"
                parts = current_dong_name.split(' ', 1)
                if len(parts) == 2: division, dong = parts[0], parts[1]
                unique_key = (division, dong, exclude_low_floors)
                add_button_label = f"그룹 추가"
                if st.button(add_button_label, key=f'add_area_{current_dong_name}'):
                    if unique_key not in st.session_state.selected_areas:
                        summary_for_group = create_summary(df_final_display)
                        # 요약이 비었거나, 상세 데이터가 비었을 경우 그룹 추가 여부 결정 필요
                        # 현재 로직: 요약이 비었거나 상세가 없어도 추가는 함 (추후 조정 가능)
                        st.session_state.selected_areas[unique_key] = {
                                'detail': df_final_display.copy(),
                                'summary': summary_for_group.copy()
                            }
                        st.success(f"'{division} {dong}{' (저층 제외)' if exclude_low_floors else ''}' 그룹이 추가되었습니다.")
                        st.rerun() # 그룹 목록 업데이트 위해 rerun
                    else:
                        st.warning(f"'{division} {dong}{' (저층 제외)' if exclude_low_floors else ''}' 그룹은 이미 존재합니다.")
        # --- AgGrid 테이블 표시 (기존 코드와 거의 동일) ---
        if not df_final_display.empty:
            # display_table_with_aggrid 함수에 키 전달하여 재랜더링 문제 방지 고려
            display_table_with_aggrid(df_final_display)
        # (데이터 없을 때 메시지는 위쪽 '현재 상태 메시지 표시' 부분에서 처리)
    elif not st.session_state.coords_to_fetch and not st.session_state.last_coords and not st.session_state.error_message:
        # 초기 상태 (아무것도 클릭 안 했고, 오류도 없는 상태)
        st.info("👈 지도를 클릭하여 지역을 선택하면 해당 지역의 매물 정보를 조회합니다.")
# --- 앱 하단 정보 ---
st.markdown("---")
st.caption("부동산 데이터는 네이버 부동산 정보를 기반으로 제공됩니다.")

