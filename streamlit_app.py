import streamlit as st
import json
import pandas as pd
import folium
from streamlit_folium import st_folium
import subprocess
import numpy as np
from io import BytesIO
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
import re
#현재 날짜
from datetime import datetime
import pprint


# Streamlit 페이지 설정 및 초기화
st.set_page_config(page_title="Real Estate Listings Viewer", layout="wide")
st.title("부동산 실시간 호가 검색 프로그램")
st.markdown("이 앱은 네이버 부동산 API를 사용하여 특정 좌표에 대한 부동산 목록을 가져와서 표시합니다.")

# 저장된 동 이름 가져오기
# dong_name = st.session_state.get('dong_name', None)
# if dong_name:
#     st.write(f"클릭한 위치의 동 이름: {dong_name}")
#     # 필요한 경우 추가적인 데이터 조회나 처리 수행
# else:
#     st.error("동 이름을 가져올 수 없습니다.")

# 현재 날짜를 원하는 형식으로 가져오기 (예: YYYYMMDD)
current_date = datetime.now().strftime('%Y%m%d')

# 세션 상태 초기화
session_keys = [
    'last_coords', 'data_loaded', 'current_data',
    'dong_name', 'is_processing', 'prev_last_clicked', 'selected_areas'
]
for key in session_keys:
    if key not in st.session_state:
        st.session_state[key] = None if key != 'selected_areas' else {}
        
# 지도 생성 및 표시
def create_folium_map():
    default_location = [37.5665, 126.9780]  # 서울 중심부 좌표
    m = folium.Map(location=default_location, zoom_start=11)
    m.add_child(folium.LatLngPopup())  # 좌표 클릭 이벤트 설정
    return m
# ▼▼▼ 기존 to_excel() 함수 밖에 추가 ▼▼▼
def format_eok(val):
    """
    숫자를 억 단위와 천만 단위로 변환하여 문자열로 반환합니다.
    - 1억 미만: 2000 → "2,000"
    - 1억 이상: 250000000 → "2억 5,000"
    - 음수: -150000000 → "-1억 5,000"
    """
    if pd.isna(val):
        return ""
    
    sign = "-" if val < 0 else ""
    abs_val = abs(val)
    
    eok = int(abs_val // 100_000_000)
    remainder = int((abs_val % 100_000_000) // 10_000)

    # 1억 미만 처리
    if eok == 0:
        return f"{sign}{remainder:,}" if remainder != 0 else "0"
    
    # 1억 이상 처리
    return (
        f"{sign}{eok}억 {remainder:,}"
        if remainder > 0
        else f"{sign}{eok}억"
    )
def export_combined_excel(selected_data, current_date):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # 1. 표지 시트 생성 ▼▼▼ 키 구조 수정
        cover_data = []
        #pprint.pprint(selected_data.items())
        for (division, dong, exclude_low_floors), data in selected_data.items():
            detail_df = data['detail']
            display_name = f"{division} {dong}{'_저층제외' if exclude_low_floors else ''}"
            
            cover_data.append({
                '지역명': display_name,
                '매매 개수': len(detail_df[detail_df['거래유형'] == '매매']),
                '전세 개수': len(detail_df[detail_df['거래유형'] == '전세']),
                '총 데이터 수': len(detail_df)
            })
            pd.DataFrame(cover_data).to_excel(writer, sheet_name='종합 리포트', index=False)

        # ▲▲▲ 수정 완료 ▲▲▲

        # 2. 개별 상세 시트 생성 ▼▼▼ 키 구조 수정
        for (division, dong, exclude_low_floors), data in selected_data.items():
            base_name = f"{division}_{dong}_{current_date}"
            if exclude_low_floors:
                base_name += "_저층제외"
            data['detail'].to_excel(writer, sheet_name=f"{base_name}_상세", index=False)
        # ▲▲▲ 수정 완료 ▲▲▲

        # 3. 통합 요약 시트 생성 ▼▼▼ 키 구조 수정
        all_summaries = []
        with open('all_marker_info.json', 'r', encoding='utf-8') as f:
            marker_info = json.load(f)
        
        for (division, dong, exclude_low_floors), data in selected_data.items():
            summary_df = data['summary'].copy()
            # 컬럼 추가
            summary_df.insert(0, '구', division)
            summary_df.insert(1, '동', dong)
            all_summaries.append(summary_df)
        
        combined_summary = pd.concat(all_summaries, ignore_index=True)

        # 갭 기준 오름차순 정렬 (숫자 처리)
        combined_summary = combined_summary.sort_values(
            by='갭(매매-전세)(평균)', 
            ascending=True
        )
            
        # 포맷팅 적용
        format_cols = [
            '매매평균', '매매중간', '매매최대', '매매최소',
            '전세평균', '전세중간', '전세최대', '전세최소',
            '갭(매매-전세)(평균)'
        ]
        for col in format_cols:
            combined_summary[col] = combined_summary[col].apply(format_eok)
            
        
        # 모든 요약 병합
        if all_summaries:
            combined_summary.to_excel(
                writer, 
                sheet_name=f"요약 데이터_{current_date}",
                index=False
            )

        # 4. 하이퍼링크 설정 (기존 코드 유지)
        workbook = writer.book
        for (division, dong, exclude_low_floors), data in selected_data.items():  # 3개 요소 언패킹
            base_name = f"{division}_{dong}_{current_date}"
            if exclude_low_floors:
                base_name += "_저층제외"
                
            worksheet = writer.sheets[f"{base_name}_상세"]
            if "매물 링크" in data['detail'].columns:
                link_col_idx = data['detail'].columns.get_loc("매물 링크")
                for row_num, link in enumerate(data['detail']["매물 링크"], start=1):
                    worksheet.write_url(row_num, link_col_idx, link, string='매물링크')
            
    return output.getvalue()

# 세 개의 열을 생성하고, 비율을 설정합니다.
left_column, center_column, right_column = st.columns([1, 2, 1])  # 비율은 원하는 대로 조정 가능

with center_column:
    m = create_folium_map()
    map_html = st_folium(m, width=1000, height=500, key='my_map',  # 고정된 키 값 설정
    returned_objects=['last_clicked'])
    
# ▼▼▼ 추가할 코드 ▼▼▼ (right_column 내부)
with right_column:
    st.markdown("### 🗂️ 선택된 지역 목록")
    
    if st.session_state.selected_areas:
        # ▼▼▼ 수정된 부분: divisionName과 cortarName 조합 표시 ▼▼▼
        display_names = []
        for (division, dong, exclude_low_floors) in st.session_state.selected_areas.keys():
        
            display_names.append(f"{division} {dong}{'_저층제외' if exclude_low_floors else ''}")

        selected_idx = st.selectbox("저장된 지역 선택", range(len(display_names)), format_func=lambda x: display_names[x])
        # ▲▲▲ 수정 완료 ▲▲▲
        
        cols = st.columns([0.5,0.5])
        with cols[0]:
            if st.button("🗑️ 선택 삭제"):
                selected_key = list(st.session_state.selected_areas.keys())[selected_idx]
                del st.session_state.selected_areas[selected_key]
                st.rerun()  
        with cols[1]:
            if st.button("🧹 전체 초기화"):
                st.session_state.selected_areas = {}
                st.rerun()  
                
        # ▼▼▼ 추가된 리포트 생성 및 다운로드 버튼 ▼▼▼
        if st.button("📊 종합 리포트 생성"):
            try:
                excel_data = export_combined_excel(
                    st.session_state.selected_areas,
                    current_date
                )
                st.download_button(
                    label="⬇️ 종합 리포트 다운로드",
                    data=excel_data,
                    file_name=f"종합_부동산_분석_{current_date}.xlsx",
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            except Exception as e:
                st.error(f"리포트 생성 실패: {str(e)}")
        # ▲▲▲ 추가 완료 ▲▲▲
# 좌표 처리 및 데이터 가져오기 함수
def save_coordinates(coords):
    with open('clicked_coords.json', 'w') as f:
        json.dump(coords, f)

def create_params(lat, lon):
    return {'zoom': '15', 'centerLat': str(lat), 'centerLon': str(lon)}

def get_dong_name_from_file():
    try:
        with open('cortars_info.json', 'r', encoding='utf-8') as file:
            cortars_info = json.load(file)
            cortar_name = f"{cortars_info.get('divisionName', 'Unknown')} {cortars_info.get('cortarName', 'Unknown')}"
            return cortar_name
    except:
        return "Unknown"

def fetch_data(coords):
    latitude = coords['lat']
    longitude = coords['lng']
    save_coordinates(coords)
    params = create_params(latitude, longitude)
    with open('params.json', 'w') as f:
        json.dump(params, f)

    subprocess.run(['python3', 'fetch_cortars.py', 'params.json'])
    st.session_state['dong_name'] = get_dong_name_from_file()

    subprocess.run(['python3', 'fetch_marker_ids.py'])
    subprocess.run(['python3', 'collect_complex_details.py'])

    try:
        with open('complex_details_by_district.json', 'r', encoding='utf-8') as file:
            st.session_state['current_data'] = json.load(file)
        st.session_state['data_loaded'] = True
    except:
        st.session_state['current_data'] = None
        st.session_state['data_loaded'] = False

if map_html:
    current_last_clicked = map_html.get('last_clicked', None)
    previous_last_clicked = st.session_state.get('prev_last_clicked', None)

    # # 디버깅용 출력
    # st.write(f"current_last_clicked: {current_last_clicked}")
    # st.write(f"previous_last_clicked: {previous_last_clicked}")

    # last_clicked 값이 변경되었을 때 처리
    if current_last_clicked != previous_last_clicked:
        if current_last_clicked is not None:
            # 실제 클릭 이벤트 발생 시
            st.session_state['prev_last_clicked'] = current_last_clicked
            coords = current_last_clicked

            # 데이터 처리 상태 업데이트
            st.session_state['last_coords'] = coords
            st.session_state['is_processing'] = True

            # 데이터 가져오기
            with st.spinner('데이터를 가져오는 중입니다...'):
                fetch_data(coords)

            st.session_state['is_processing'] = False
            
            
# 공급면적 숫자로 저장
def extract_numeric_area(area_str):
    """
    공급면적에서 숫자만 추출하여 반환합니다.
    예: '121A' -> 121, '114B' -> 114
    """
    # 정규식을 사용하여 숫자만 추출
    match = re.search(r'\d+', str(area_str))
    if match:
        return float(match.group())  # 숫자를 float으로 변환
    return None  # 숫자가 없으면 None 반환

# 요약 데이터 함수
def create_summary(df):
    """상세 데이터프레임에서 요약 데이터 생성"""
    df_summary = df.copy()
    
    # 가격 변환
    df_summary['가격_숫자'] = df_summary['가격'].apply(convert_price_to_number)
    
    # 공급면적 처리
    df_summary["공급면적_숫자"] = df_summary["공급면적"].apply(extract_numeric_area)
    df_summary["평형"] = (df_summary["공급면적_숫자"] / 3.3).round(1)

    # CP사 필터링
    if "CP사" in df_summary.columns:
        df_filtered = df_summary[df_summary["CP사"] != "한국공인중개사협회"]
    else:
        df_filtered = df_summary.copy()

    # 매매/전세 집계
    sale_df = df_filtered[df_filtered["거래유형"] == "매매"].groupby(
        ["매물명", "공급면적", "평형", "연식", "총세대수"], as_index=False
    ).agg(
        매매평균=("가격_숫자", "mean"),
        매매중간=("가격_숫자", "median"),
        매매최대=("가격_숫자", "max"),
        매매최소=("가격_숫자", "min")
    )

    jeonse_df = df_filtered[df_filtered["거래유형"] == "전세"].groupby(
        ["매물명", "공급면적", "평형", "연식", "총세대수"], as_index=False
    ).agg(
        전세평균=("가격_숫자", "mean"),
        전세중간=("가격_숫자", "median"),
        전세최대=("가격_숫자", "max"),
        전세최소=("가격_숫자", "min")
    )

    # 매물 개수 계산
    sale_count = df_filtered[df_filtered['거래유형'] == '매매'] \
        .groupby(["매물명", "공급면적", "평형", "연식", "총세대수"]).size().reset_index(name='매매개수')
    jeonse_count = df_filtered[df_filtered['거래유형'] == '전세'] \
        .groupby(["매물명", "공급면적", "평형", "연식", "총세대수"]).size().reset_index(name='전세개수')

    # 데이터 병합
    summary_df = pd.merge(sale_df, jeonse_df, on=["매물명", "공급면적", "평형", "연식", "총세대수"], how="outer")
    summary_df = pd.merge(summary_df, sale_count, on=["매물명", "공급면적", "평형", "연식", "총세대수"], how="left")
    summary_df = pd.merge(summary_df, jeonse_count, on=["매물명", "공급면적", "평형", "연식", "총세대수"], how="left")
    
    # 갭 계산
    summary_df["갭(매매-전세)(평균)"] = summary_df["매매평균"] - summary_df["전세평균"]
    
    # 컬럼 정리
    summary_df = summary_df.rename(columns={"매물명": "아파트명"})
    return summary_df[
        [
            "아파트명", "연식", "총세대수", "공급면적", "평형",
            "매매개수", "전세개수", "매매평균", "매매중간",
            "매매최대", "매매최소", "전세평균", "전세중간",
            "전세최대", "전세최소", "갭(매매-전세)(평균)"
        ]
    ]

def to_excel(df, area_name, current_date, exclude_low_floors):
    # 요약 데이터 생성 (create_summary 호출)
    summary_df = create_summary(df)
    
    # 숫자 포맷팅 적용
    format_cols = ['매매평균', '매매중간', '매매최대', '매매최소',
                    '전세평균', '전세중간', '전세최대', '전세최소',
                    '갭(매매-전세)(평균)']
    for col in format_cols:
        summary_df[col] = summary_df[col].apply(format_eok)
    
    # ▼▼▼ 시트 이름 생성 로직 ▼▼▼
    base_name = f"{area_name}_{current_date}"
    if exclude_low_floors:
        base_name += "_저층제외"
    
    sheet1_name = f"{base_name}_상세"
    sheet2_name = f"{base_name}_요약"
    
    # 엑셀 파일 생성
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name=sheet1_name)
        summary_df.to_excel(writer, index=False, sheet_name=sheet2_name)
        
        # 하이퍼링크 설정
        workbook = writer.book
        worksheet = writer.sheets[sheet1_name]
        if "매물 링크" in df.columns:
            link_col_idx = df.columns.get_loc("매물 링크")
            for row_num, link in enumerate(df["매물 링크"], start=1):
                worksheet.write_url(row_num, link_col_idx, link, string='매물 링크')
    
    return output.getvalue()

# CSV로 저장하는 함수
def to_csv_with_links(df):
    return df.to_csv(index=False, encoding='utf-8-sig')

# 링크 생성 함수
def create_article_url(articleNo, markerId, latitude, longitude):
    base_url = f"https://new.land.naver.com/complexes/{markerId}"
    params = f"?ms={latitude},{longitude},15&a=APT:PRE&b=A1&e=RETAIL&l=300&ad=true&articleNo={articleNo}"
    return base_url + params

# 긴 텍스트 줄이기 함수
def shorten_text(text, max_length=50):
    return text if len(text) <= max_length else text[:max_length] + '...'

# 데이터 표시 함수
def display_table_with_aggrid(df):
    
    # Grid 옵션 생성
    gb = GridOptionsBuilder.from_dataframe(df)

    # 한 페이지에 100개씩 표시하도록 설정
    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
    gb.configure_side_bar()
    gb.configure_default_column(
        groupable=True,
        editable=False,
        filter=True,
        resizable=True,
        sortable=True
    )
    
    # 링크 컬럼을 하이퍼링크로 표시하도록 설정
    cell_renderer = JsCode('''
    class HyperlinkRenderer {
        init(params) {
            this.eGui = document.createElement('a');
            this.eGui.innerText = '매물 링크';
            this.eGui.href = params.value;
            this.eGui.target = '_blank';
        }
        getGui() {
            return this.eGui;
        }
    }
    ''')
    
    # 태그 컬럼 CSS 적용
    tag_renderer = JsCode("""
    class TagRenderer {
        init(params) {
            this.eGui = document.createElement('div');
            var value = params.value;
            var tags = [];

            if (Array.isArray(value)) {
                tags = value;
            } else if (typeof value === 'string') {
                value = value.replace(/[\[\]'"]/g, '');
                tags = value.split(',').map(function(tag) {
                    return tag.trim();
                });
            }

            tags.forEach((tag) => {
                var span = document.createElement('span');
                span.innerText = tag;
                span.style.display = 'inline-block';
                span.style.backgroundColor = '#24516e';
                span.style.color = 'white';
                span.style.padding = '0px 8px';
                span.style.margin = '2px';
                span.style.borderRadius = '20px';
                span.style.fontSize = '12px';
                this.eGui.appendChild(span);
            });
        }

        getGui() {
            return this.eGui;
        }
    }
    """)
    gb.configure_column("매물 링크", cellRenderer=cell_renderer)
    gb.configure_column('태그', cellRenderer=tag_renderer, autoHeight=True, wrapText=True, width=800)

    gridOptions = gb.build()
    
    
    
    # 테마 설정
    AgGrid(
        df,
        gridOptions=gridOptions,
        enable_enterprise_modules=True,
        fit_columns_on_grid_load=True,
        theme='streamlit',
        allow_unsafe_jscode=True,
        unsafe_allow_html=True,  # HTML 렌더링 허용
    )

# 층 정보 추출하여 새로운 컬럼 추가
def extract_floor(floor_info):
    """'층수'에서 층 정보를 추출합니다."""
    if '/' in floor_info:
        floor = floor_info.split('/')[0].strip()
        return floor
    else:
        return floor_info.strip()

# 기능 추가 : 저층 제외
def filter_out_low_floors(df_display, exclude_low_floors):
    # '층' 컬럼이 없다면 생성
    if '층' not in df_display.columns:
        df_display['층'] = df_display['층수'].apply(extract_floor)

    # 체크박스 상태에 따라 데이터 필터링
    if exclude_low_floors:
        df_display = df_display[~df_display['층'].isin(['1', '2', '3', '저'])]
    
    # '층' 컬럼을 제외한 표시용 데이터프레임 생성
    df_display_for_show = df_display.drop(columns=['층'])
    return df_display_for_show

# 기능 추가 : 가격 숫자로 변경
def convert_price_to_number(price_str):
    # 만약 price_str이 NaN이면 0 반환
    if pd.isnull(price_str):
        return 0  # NaN인 경우 0 반환

    # price_str이 float나 int인 경우 문자열로 변환
    if isinstance(price_str, (float, int)):
        price_str = str(price_str)
    
    # 문자열이 'nan'인 경우 0 반환
    if price_str.lower() == 'nan':
        return 0
    
    price_str = price_str.replace(',', '').replace(' ', '').strip()
    
    # 정규식을 사용하여 숫자와 단위를 추출
    match = re.match(r'(\d+)(억)?(\d+)?', price_str)
    
    if not match:
        return 0  # 매칭되지 않으면 0 반환
    
    num1 = match.group(1)  # 억 앞의 숫자
    unit1 = match.group(2)  # '억'
    num2 = match.group(3)  # 억 뒤의 숫자 (만원 단위)
    
    total = 0
    if unit1 == '억':
        total += int(num1) * 100000000  # 억 단위 변환
    else:
        total += int(num1)  # '억' 단위가 없으면 그대로
    
    if num2:
        total += int(num2) * 10000  # 만원 단위 변환

    return total

# 기능 추가 : 가격 정렬 기준 선택
def sort_prices_by_criteria(selected_sort_options, selected_order_option):
    # 정렬 기준과 순서 설정
    sort_columns = []
    for option in selected_sort_options:
        if option == '가격':
            sort_columns.append('가격_숫자')
        else:
            sort_columns.append(option)

    ascending_order = True if selected_order_option == '오름차순' else False
    ascending_list = [ascending_order] * len(sort_columns)
    return sort_columns, ascending_list

# 기능 추가 : 가격 정렬
def sort_prices(df_display, sort_columns=['가격_숫자'], ascending_list=[True]):
    # 가격_숫자 컬럼 추가
    if '가격_숫자' not in df_display.columns:
        df_display['가격_숫자'] = df_display['가격'].apply(convert_price_to_number)

    # 가격_숫자 기준으로 정렬
    df_display_sorted = df_display.sort_values(by=sort_columns, ascending=ascending_list)

    # '가격_숫자' 컬럼을 제외한 표시용 데이터프레임 생성
    df_display_for_show = df_display_sorted.drop(columns=['가격_숫자'])
    return df_display_for_show

# 실제 데이터를 사용하여 코드 실행
if st.session_state.get('is_processing'):
    st.info('데이터를 불러오는 중입니다. 잠시만 기다려주세요...')
elif st.session_state.get('data_loaded') and st.session_state.get('current_data'):
    complex_details_by_district = st.session_state['current_data']
    for area_name, area_data in complex_details_by_district.items():
        if area_data:
            df = pd.DataFrame(area_data)
        
            # 필요한 컬럼이 있는지 확인
            required_columns = ['markerId', 'latitude', 'longitude', 'articleNo']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                st.error(f"다음 컬럼이 데이터에 없습니다: {', '.join(missing_columns)}. 데이터를 다시 불러와주세요.")
                continue

            # 링크 생성 및 추가
            df['매물 링크'] = df.apply(lambda x: create_article_url(
                x['articleNo'], x['markerId'], x['latitude'], x['longitude']
            ), axis=1)

            # 표시할 컬럼 선택
            display_columns = [
                "articleName",
                # 총세대수, 연식 추가
                "completionYearMonth",
                "totalHouseholdCount",
                "buildingName",
                "dealOrWarrantPrc",
                "tradeTypeName",
                "floorInfo",
                "areaName",
                # "realEstateTypeName",
                "direction",
                #"articleConfirmYmd",
                "articleFeatureDesc",
                "tagList",
                "sameAddrMaxPrc",
                "sameAddrMinPrc",
                "realtorName",
                "sameAddrCnt",
                "cpName",
                "매물 링크"
            ]

            # 선택한 컬럼들로 데이터프레임 생성
            df_display = df.loc[:, display_columns].copy()
                
            # 컬럼 이름을 한글로 변경
            df_display = df_display.rename(columns={
                "articleName": "매물명",
                # 총세대수, 연식 추가
                "completionYearMonth": "연식",
                "totalHouseholdCount": "총세대수",
                "buildingName": "건물명",
                "dealOrWarrantPrc": "가격",
                "tradeTypeName": "거래유형",
                "floorInfo": "층수",
                "areaName": "공급면적",
                # "realEstateTypeName": "부동산유형",
                "direction": "방향",
                #"articleConfirmYmd": "확인일자",
                "articleFeatureDesc": "특징",
                "tagList": "태그",
                "sameAddrMaxPrc": "최고가",
                "sameAddrMinPrc": "최저가",
                "realtorName": "중개사",
                "sameAddrCnt": "매물수",
                "cpName": "CP사"
                # "매물 링크"는 이미 한글로 되어 있으므로 변경하지 않습니다.
            })

            # 긴 텍스트 컬럼 내용 줄이기
            df_display["특징"] = df_display["특징"].apply(lambda x: shorten_text(str(x)))
            df_display["태그"] = df_display["태그"].apply(lambda x: shorten_text(str(x)))
            
            # 추가: "completionYearMonth" 컬럼의 값에서 연도(앞 4자리)만 추출하여 숫자로 변환
            df_display["연식"] = df_display["연식"].apply(
                    lambda x: int(str(x)[:4]) if pd.notnull(x) and len(str(x)) >= 4 and str(x)[:4].isdigit() else x
                )
                
            # 가격에 콤마 추가
            #df_display["가격"] = df_display["가격"].apply(lambda x: f"{int(x.replace(',', '').replace(' ', '')):,}원" if isinstance(x, str) and x.replace(',', '').replace(' ', '').isdigit() else x)
            #df_display["최고가"] = df_display["최고가"].apply(lambda x: f"{int(x):,}원" if x and str(x).isdigit() else x)
            #df_display["최저가"] = df_display["최저가"].apply(lambda x: f"{int(x):,}원" if x and str(x).isdigit() else x)

            # 확인일자 형식 변환
            #df_display["확인일자"] = pd.to_datetime(df_display["확인일자"], errors='coerce').dt.strftime('%Y-%m-%d')

            # CSS 스타일을 정의하여 컬럼 간의 간격을 조절
            st.markdown(
                """
                <style>
                /* 컬럼들을 감싸는 div의 gap을 조절하여 간격을 줄임 */
                div[data-testid="stVerticalBlock"] {
                    gap: 1rem;
                }
                div[data-testid="stHorizontalBlock"] {
                    gap: 0.1rem;
                }              
                </style>
                """,
                unsafe_allow_html=True
            )
            
            # 다운로드 버튼을 표의 오른쪽 상단에 배치하기 위해 컬럼 생성
            cols = st.columns([8,2])  # 컬럼 너비 조정

            # 표 제목 설정
            with cols[0]:
                element_cols = st.columns([3.05,2.5,2.5,1.95])
                with element_cols[0]:
                    st.write(f"### {area_name}")
                with element_cols[1]:
                    # 정렬 기준 선택 multi select box 생성(복수 선택 가능)
                    sort_options = ['매물명', '가격']
                    selected_sort_options = st.multiselect('정렬 기준', options=sort_options, default=['가격'], label_visibility='collapsed')
                with element_cols[2]:
                    # 정렬 순서 선택 select box 생성
                    order_options = ['오름차순', '내림차순']
                    selected_order_option = st.selectbox('정렬 순서', options=order_options, label_visibility='collapsed')
                with element_cols[3]:
                    st.write("")  # 빈 공간으로 사용하여 버튼들을 오른쪽으로 밀기

            with cols[1]:
                # 체크박스와 버튼들을 가로로 배치하기 위해 내부에서 컬럼 생성
                element_cols = st.columns([0.1, 0.45, 0.19, 0.16])  # [공백, multi select box, select box, 체크박스, 버튼1, 버튼2]
                # 체크박스 생성
                with element_cols[0]:
                    st.write("")  # 빈 공간으로 사용하여 버튼들을 오른쪽으로 밀기
                
                with element_cols[1]:
                    exclude_low_floors = st.checkbox("저층 제외(1,2,3,저)", key=f'checkbox_{area_name}')
                    
                # 가격 기준 설정
                sort_columns, ascending_list = sort_prices_by_criteria(selected_sort_options, selected_order_option)
                # 가격 정렬
                df_display = sort_prices(df_display, sort_columns=sort_columns, ascending_list=ascending_list)
                # 저층 제외
                df_display_for_show = filter_out_low_floors(df_display, exclude_low_floors)

                # 다운로드 버튼 설정
                csv_data = to_csv_with_links(df_display_for_show).encode('utf-8-sig')
                excel_data = to_excel(df_display_for_show, area_name, current_date, exclude_low_floors)
            
                # 다운로드 버튼 배치 (element_cols 내부에서)
                with element_cols[2]:
                    st.download_button(
                        label="Excel",
                        data=excel_data,
                        file_name=f"{area_name}_{current_date}" + ("_저층제외" if exclude_low_floors else "") + ".xlsx",
                        mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        key=f'excel_{area_name}'
                    )

                with element_cols[3]:
                    st.download_button(
                        label="CSV",
                        data=csv_data,
                        file_name=f'{area_name}_data.csv',
                        mime='text/csv',
                        key=f'csv_{area_name}'
                    )

            # 데이터프레임을 표시
            display_table_with_aggrid(df_display_for_show)
            # ▼▼▼ 추가할 코드 (데이터 표시 하단) ▼▼▼
            st.markdown("---")  # 구분선 추가
            button_cols = st.columns(2)
            with button_cols[0]:
                if st.button(f"📥 {area_name} 추가", key=f'add_{area_name}'):
                    # ▼▼▼ divisionName과 cortarName 조회 추가 ▼▼▼
                    division, dong = "Unknown", "Unknown"
                    with open('all_marker_info.json', 'r', encoding='utf-8') as f:
                        marker_info = json.load(f)
                        for marker_key in marker_info:
                            if area_name in marker_key:
                                division = marker_info[marker_key][0].get('divisionName', 'Unknown')
                                dong = marker_info[marker_key][0].get('cortarName', 'Unknown')
                                break
                    
                    # 고유 키 생성 방식 변경 ▼▼▼
                    unique_key = (division, dong, exclude_low_floors)
                    if unique_key not in st.session_state.selected_areas:
                        summary_df = create_summary(df_display_for_show)
                        st.session_state.selected_areas[unique_key] = {
                            'detail': df_display_for_show,
                            'summary': summary_df
                        }
                        st.rerun()

            with button_cols[1]:
                if st.button(f"📤 {area_name} 제거", key=f'remove_{area_name}'):
                    # 고유 키 추출 방식 변경 ▼▼▼
                    division, dong = "Unknown", "Unknown"
                    with open('all_marker_info.json', 'r', encoding='utf-8') as f:
                        marker_info = json.load(f)
                        for marker_key in marker_info:
                            if area_name in marker_key:
                                division = marker_info[marker_key][0].get('divisionName', 'Unknown')
                                dong = marker_info[marker_key][0].get('cortarName', 'Unknown')
                                break
                    
                    unique_key = (division, dong, exclude_low_floors)
                    if unique_key in st.session_state.selected_areas:
                        del st.session_state.selected_areas[unique_key]
                        st.rerun()
            # ▲▲▲ 추가할 코드 ▲▲▲
        else:
            st.write(f"{area_name}에 대한 데이터가 없습니다.")
else:
    st.write("지도를 클릭하여 좌표를 선택하세요.")