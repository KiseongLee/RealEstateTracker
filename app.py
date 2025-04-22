# app.py
import streamlit as st
import pandas as pd
from streamlit_folium import st_folium # 지도 상호작용 위해 필요
import os # 파일 경로 지정을 위해 추가

# 다른 모듈에서 필요한 함수들 임포트 (src 패키지 경로 사용)
from src.utils import create_article_url, shorten_text, get_current_date_str # shorten_text 추가 임포트
from src.data_handling import fetch_data
from src.data_processor import filter_out_low_floors, sort_dataframe, create_summary
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

session_keys = [
    'last_coords', 'data_loaded', 'current_data', 'dong_name',
    'is_processing', 'prev_last_clicked', 'selected_areas'
]
for key in session_keys:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'selected_areas' else {}

# ==============================================================================
# Streamlit UI 구성 및 메인 로직
# ==============================================================================

# --- 1. 지도 및 선택 지역 목록 레이아웃 ---
left_column, center_column, right_column = st.columns([1, 2, 1])

with center_column:
    st.markdown("### 🗺️ 지도에서 위치 클릭")
    folium_map = create_folium_map()
    map_interaction = st_folium(folium_map, width=950, height=500, key='folium_map_interaction',
                                returned_objects=['last_clicked'])

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
                        excel_data = export_combined_excel(selected_areas, current_date)
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


# --- 2. 지도 클릭 이벤트 처리 및 데이터 가져오기 ---
if map_interaction and map_interaction.get('last_clicked'):
    current_last_clicked = map_interaction['last_clicked']
    if current_last_clicked != st.session_state.get('prev_last_clicked'):
        st.session_state['prev_last_clicked'] = current_last_clicked
        coords = current_last_clicked
        st.session_state['last_coords'] = coords
        st.session_state['is_processing'] = True
        with st.spinner('매물 데이터를 가져오는 중입니다...'):
            loaded_data = fetch_data(coords, OUTPUT_DIR)
        st.session_state['is_processing'] = False
        st.rerun()


# --- 3. 데이터 표시 및 상호작용 ---
st.markdown("---")

if st.session_state.get('is_processing'):
    st.info('⏳ 데이터를 불러오는 중입니다. 잠시만 기다려주세요...')
elif st.session_state.get('data_loaded') and st.session_state.get('current_data'):
    complex_details_by_district = st.session_state['current_data']
    current_dong_name = st.session_state.get('dong_name', "알 수 없는 지역")
    st.subheader(f"📍 현재 조회된 지역: {current_dong_name}")

    for area_name, area_data in complex_details_by_district.items():
        if not area_data:
            st.warning(f"'{area_name}' 지역에 대한 데이터가 없습니다.")
            continue

        try:
            df = pd.DataFrame(area_data)
            required_columns = ['articleNo', 'markerId', 'latitude', 'longitude', 'divisionName', 'cortarName']
            if not all(col in df.columns for col in required_columns):
                missing = [col for col in required_columns if col not in df.columns]
                st.error(f"'{area_name}' 데이터에 필수 컬럼 누락: {', '.join(missing)}.")
                continue

            df_processed = df.copy()
            df_processed['매물 링크'] = df_processed.apply(
                lambda x: create_article_url(x['articleNo'], x['markerId'], x['latitude'], x['longitude']), axis=1
            )

            display_columns_map = {
                "articleName": "매물명", "divisionName": "구", "cortarName": "동",
                "completionYearMonth": "연식", "totalHouseholdCount": "총세대수",
                "buildingName": "동/건물명", "dealOrWarrantPrc": "가격",
                "tradeTypeName": "거래유형", "floorInfo": "층수", "areaName": "공급면적",
                "direction": "방향", "articleFeatureDesc": "특징", "tagList": "태그",
                "realtorName": "중개사", "sameAddrCnt": "단지매물수", "cpName": "정보제공",
                "매물 링크": "매물 링크"
            }
            cols_to_display = [col for col in display_columns_map.keys() if col in df_processed.columns]
            df_display = df_processed[cols_to_display].rename(columns=display_columns_map)
            
            # --- ▼▼▼ 컬럼 순서 재정렬 ▼▼▼ ---
            # 원하는 최종 표시 순서 정의 (한글 컬럼명 기준)
            target_column_order = [
                "매물명", "구", "동", "연식", "총세대수", "동/건물명", "가격",
                "거래유형", "층수", "공급면적", "방향","태그", "특징",
                "매물 링크","단지매물수", "중개사", "정보제공"
            ]
            # df_display에 실제로 존재하는 컬럼만 사용하여 순서 적용
            existing_cols_in_order = [col for col in target_column_order if col in df_display.columns]
            # 존재하지 않는 컬럼이 있다면 경고 (선택 사항)
            missing_target_cols = [col for col in target_column_order if col not in existing_cols_in_order]
            if missing_target_cols:
                st.warning(f"다음 컬럼이 누락되어 표시 순서에서 제외됩니다: {', '.join(missing_target_cols)}")

            # 데이터프레임 컬럼 순서 재적용
            df_display = df_display[existing_cols_in_order]
            # --- ▲▲▲ 컬럼 순서 재정렬 완료 ▲▲▲ ---
            
            # --- 데이터 타입 변환 및 포맷팅 (기존 코드 유지) ---
            if '연식' in df_display.columns:
                # 연식 null 처리 강화
                df_display['연식'] = df_display['연식'].apply(
                    lambda x: int(str(x)[:4]) if pd.notnull(x) and isinstance(x, (str, int)) and len(str(x)) >= 4 and str(x)[:4].isdigit() else pd.NA
                ).astype('Int64')
            if '총세대수' in df_display.columns:
                df_display['총세대수'] = pd.to_numeric(df_display['총세대수'], errors='coerce').astype('Int64')
            if '단지매물수' in df_display.columns:
                df_display['단지매물수'] = pd.to_numeric(df_display['단지매물수'], errors='coerce').astype('Int64')

            # --- ▼▼▼ 텍스트 줄이기 복원 (매물명, 특징, 태그) ▼▼▼ ---
            if '매물명' in df_display.columns:
                df_display['매물명'] = df_display['매물명'].apply(lambda x: shorten_text(str(x))) 
                
            if '특징' in df_display.columns:
                df_display['특징'] = df_display['특징'].apply(lambda x: shorten_text(str(x))) # 예: 50자로 제한
            if '태그' in df_display.columns:
            #     # 태그는 list일 수도 있으므로 str로 변환 후 줄이기
                df_display['태그'] = df_display['태그'].apply(lambda x: shorten_text(str(x))) # 예: 40자로 제한
            if '중개사' in df_display.columns:
            #     # 태그는 list일 수도 있으므로 str로 변환 후 줄이기
                df_display['중개사'] = df_display['중개사'].apply(lambda x: shorten_text(str(x))) # 예: 40자로 제한
            # # --- ▲▲▲ 텍스트 줄이기 완료 ▲▲▲ ---

            # --- UI 컨트롤 (정렬 부분 수정) ---
            # 컬럼 비율 재조정 (multiselect 공간 확보)
            cols = st.columns([8,2])
            with cols[0]:
                element_cols = st.columns([3.05,2.5,2.5,1.95])
                with element_cols[0]:
                    st.write(f"##### {area_name} 매물 목록 ({len(df_display)}개)")

            # --- ▼▼▼ 복수 정렬 기준 선택 UI ▼▼▼ ---
                with element_cols[1]:
                    sort_options = ['가격', '매물명', '연식', '공급면적', '총세대수'] # 정렬 가능한 컬럼 리스트
                    available_sort_options = [opt for opt in sort_options if opt in df_display.columns or opt == '가격']
                    selected_sort_options = st.multiselect( # selectbox -> multiselect
                        '정렬 기준 (순서대로 적용)', options=available_sort_options, default=['가격'], # 기본값 '가격'
                        key=f'sort_multiselect_{area_name}', label_visibility='collapsed'
                    )
            # --- ▲▲▲ 복수 정렬 기준 선택 UI 완료 ▲▲▲ ---

                with element_cols[2]:
                    order_options = ['오름차순', '내림차순']
                    selected_order_option = st.selectbox(
                        '정렬 순서', options=order_options, index=0,
                        key=f'order_select_{area_name}', label_visibility='collapsed'
                    )
                with element_cols[3]:
                    st.write("") # 빈 공간으로 사용하여 버튼들을 오른쪽으로 밀기
            with cols[1]:
                element_cols = st.columns([0.05,0.35,0.25,0.35])        
                with element_cols[0]:
                    st.write("")  # 빈 공간으로 사용하여 버튼들을 오른쪽으로 밀기
                with element_cols[1]:
                    exclude_low_floors = st.checkbox("저층 제외", key=f'low_floor_check_{area_name}', value=False)

                    # --- ▼▼▼ 복수 정렬 로직 적용 ▼▼▼ ---
                    df_filtered = filter_out_low_floors(df_display, exclude_low_floors)

                    # 선택된 정렬 기준과 순서를 sort_dataframe 함수에 맞게 변환
                    if selected_sort_options: # 하나 이상 선택되었을 때만
                        sort_columns_for_func = []
                        for option in selected_sort_options:
                            # '가격' 선택 시 내부적으로 사용할 컬럼명 지정 (data_processor.py와 일치해야 함)
                            if option == '가격':
                                sort_columns_for_func.append('가격') # sort_dataframe 함수가 '가격_숫자_정렬용' 등으로 처리
                            elif option == '공급면적':
                                sort_columns_for_func.append('공급면적') # sort_dataframe 함수가 '공급면적_숫자_정렬용' 등으로 처리
                            else:
                                sort_columns_for_func.append(option)

                        # 모든 선택된 기준에 대해 동일한 정렬 순서 적용 (오름차순/내림차순)
                        ascending_order = True if selected_order_option == '오름차순' else False
                        ascending_list_for_func = [ascending_order] * len(sort_columns_for_func)

                        # data_processor.py 함수 호출 (리스트 전달)
                        df_sorted = sort_dataframe(df_filtered, sort_columns_for_func, ascending_list_for_func)
                    else: # 정렬 기준 선택 안했을 경우
                        df_sorted = df_filtered
                    df_final_display = df_sorted
                    # --- ▲▲▲ 복수 정렬 로직 적용 완료 ▲▲▲ ---

                    # --- 다운로드 및 지역 추가 버튼 (변경 없음) ---
                    with element_cols[2]: # Excel 다운로드
                        if not df_final_display.empty:
                            summary_df = create_summary(df_final_display)
                            excel_data = to_excel(df_final_display, summary_df, area_name, current_date, exclude_low_floors)
                            st.download_button(
                                label="Excel", data=excel_data,
                                file_name=f"{area_name}_{current_date}{'_저층제외' if exclude_low_floors else ''}.xlsx",
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                key=f'excel_dl_{area_name}'
                            )

                    with element_cols[3]: # 지역 추가 버튼
                        division, dong = "Unknown", "Unknown"
                        parts = area_name.split(' ', 1)
                        if len(parts) == 2: division, dong = parts[0], parts[1]
                        unique_key = (division, dong, exclude_low_floors)
                        add_button_label = f"그룹 추가"
                        if st.button(add_button_label, key=f'add_area_{area_name}'):
                            if unique_key not in st.session_state.selected_areas:
                                current_summary = create_summary(df_final_display)
                                if not current_summary.empty or df_final_display.empty:
                                    st.session_state.selected_areas[unique_key] = {
                                        'detail': df_final_display.copy(), 'summary': current_summary.copy()
                                    }
                                    st.success(f"'{division} {dong}{' (저층 제외)' if exclude_low_floors else ''}' 그룹이 추가되었습니다.")
                                    st.rerun()
                                else:
                                    st.error(f"'{area_name}' 요약 데이터 생성 오류로 그룹 추가 실패.")
                            else:
                                st.warning(f"'{division} {dong}{' (저층 제외)' if exclude_low_floors else ''}' 그룹은 이미 존재합니다.")

            # --- AgGrid 테이블 표시 (변경 없음) ---
            if not df_final_display.empty:
                display_table_with_aggrid(df_final_display)
            else:
                st.info(f"'{area_name}' 지역의 해당 조건에 맞는 매물이 없습니다.")

        except Exception as e:
            st.error(f"'{area_name}' 데이터 처리 중 오류 발생: {e}")
            st.exception(e) # 개발 중 상세 오류 보기 위해 유지

elif not st.session_state.get('last_coords'):
    st.info("👈 지도를 클릭하여 지역을 선택하면 해당 지역의 매물 정보를 조회합니다.")
else:
    st.warning("선택하신 지역에 불러올 데이터가 없습니다. 지도를 다시 클릭하거나 앱 설정을 확인해주세요.")

# --- 앱 하단 정보 ---
st.markdown("---")
st.caption("부동산 데이터는 네이버 부동산 정보를 기반으로 제공됩니다.")

