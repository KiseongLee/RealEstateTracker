# src/ui_elements.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
import pandas as pd
from folium.features import DivIcon # DivIcon을 사용하기 위해 임포트

def create_folium_map():
    """
    Folium 지도를 생성합니다.
    st.session_state에 저장된 'last_coords'와 'dong_name'을 사용하여
    지도 중심을 설정하고, 해당 위치에 핀 마커와 함께 'dong_name' 텍스트 라벨을 표시합니다.
    """
    
    default_map_center = [37.5665, 126.9780]  # 서울 시청 기본 위치
    default_zoom_level = 12                   # 기본 확대 레벨

    saved_last_coords = st.session_state.get('last_coords')
    
    current_map_center = default_map_center
    current_zoom_level = default_zoom_level

    if saved_last_coords and \
        isinstance(saved_last_coords, dict) and \
        'lat' in saved_last_coords and 'lng' in saved_last_coords:
        current_map_center = [saved_last_coords['lat'], saved_last_coords['lng']]
        current_zoom_level = 15  # 데이터 조회 후에는 좀 더 확대
    
    folium_map_object = folium.Map(location=current_map_center, zoom_start=current_zoom_level)

    current_dong_name = st.session_state.get('dong_name')

    if saved_last_coords and \
        isinstance(saved_last_coords, dict) and \
        'lat' in saved_last_coords and 'lng' in saved_last_coords and \
        current_dong_name:
        
        marker_coordinates = [saved_last_coords['lat'], saved_last_coords['lng']]
        
        # 1. 표준 핀 마커 추가 (세련된 아이콘과 색상 사용)
        # FontAwesome 아이콘을 사용하려면 prefix='fa'를 지정합니다.
        # 아이콘 종류: 'map-marker', 'info-circle', 'home', 'building' 등 (FontAwesome v4.7 기준)
        # 색상 참고: 'blue', 'green', 'purple', 'orange', 'darkred', 'lightred', 'beige', 
        # 'darkblue', 'darkgreen', 'cadetblue', 'white', 'pink', 'lightblue', 
        # 'lightgreen', 'gray', 'black', 'lightgray'.
        # 아이콘 색상을 'darkblue'로 지정합니다.
        pin_marker_folium_color = 'darkgreen'     # Folium에서 제공하는 색상 이름
        pin_marker_base_hex_color = '#006400'          # 'darkgreen'의 Hex 코드

        folium.Marker(
            location=marker_coordinates,
            popup=folium.Popup(f"<strong>{current_dong_name}</strong><br>이곳의 데이터를 조회했습니다.", max_width=250),
            icon=folium.Icon(color=pin_marker_folium_color, icon='map-pin', prefix='fa'), # 'map-pin' 아이콘 사용
            tooltip=f"{current_dong_name} - 상세 정보 보기"
        ).add_to(folium_map_object)

        # 2. 텍스트 라벨 마커 추가 (DivIcon 사용, 세련된 디자인 적용)
        # CSS transform을 사용하여 핀 마커 기준으로 라벨 위치를 미세 조정합니다.
        # translate(X, Y): X는 가로 이동(양수: 오른쪽), Y는 세로 이동(양수: 아래쪽).
        # 핀 마커의 높이가 약 38-42px이므로, Y를 -45px 정도로 하면 핀 위쪽에 위치합니다.
        # X를 0으로 하면 핀 중앙 위, 양수로 하면 핀 오른쪽 위, 음수로 하면 핀 왼쪽 위에 위치.
        # 아래는 핀 마커 중앙 상단에 위치하도록 조정하는 예시입니다.
        div_icon_border_color = '#005000' # #006400 보다 약간 어두운 녹색

        text_label_html = f"""
        <div style="
            position: absolute;
            transform: translate(-50%, -140%);
            font-family: 'Open Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
            font-size: 10.5pt;
            font-weight: 500;
            color: #FFFFFF; /* 텍스트 색상: 흰색 */
            background-color: {pin_marker_base_hex_color}; /* 배경색: 핀 마커의 기본색 #006400 */
            padding: 6px 13px;
            border-radius: 18px;
            border: 1px solid {div_icon_border_color}; /* 테두리: 배경색과 유사한 톤으로 미세하게 */
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2); /* 그림자: 매우 약하게 */
            white-space: nowrap;
            text-align: center;
            pointer-events: none;
            user-select: none;
            ">
            {current_dong_name}
        </div>
        """
        
        folium.Marker(
            location=marker_coordinates,
            icon=DivIcon(
                icon_size=(0,0),    # HTML 내용물 크기에 맞춰 자동 조절되도록 (0,0) 또는 작은 값 사용 가능
                                    # 또는 내용물의 예상 최대 크기 지정 (예: (180, 40))
                icon_anchor=(0,0),  # DivIcon의 기준점. HTML 내부에서 position:absolute와 transform으로 위치를 조정하므로,
                                    # 여기서는 (0,0) (좌상단) 또는 실제 라벨의 시각적 중심을 고려한 값으로 설정.
                                    # transform: translate(-50%, Y)를 사용하므로, icon_anchor를 (0,0)으로 두면
                                    # 마커 좌표에서 라벨의 좌상단이 시작되고, transform으로 이동됩니다.
                                    # 만약 라벨의 중심을 마커 좌표에 맞추고 싶다면, icon_anchor를 (div너비/2, div높이/2)로 설정하고
                                    # transform 조정이 필요할 수 있습니다. (0,0)과 transform 조합이 직관적일 수 있습니다.
                html=text_label_html
            )
        ).add_to(folium_map_object)

    return folium_map_object

def get_aggrid_options(df):
    """AgGrid 표시에 필요한 GridOptions를 설정합니다."""
    gb = GridOptionsBuilder.from_dataframe(df)

    gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
    gb.configure_side_bar()
    gb.configure_default_column(
        groupable=True, editable=False, filter=True, resizable=True, sortable=True,
        wrapText=True, # 기본적으로 텍스트 줄바꿈 활성화 [6]
        autoHeight=True # 내용에 따라 행 높이 자동 조절 활성화 [6]
    )

    # 링크 컬럼 렌더러 (변경 없음)
    cell_renderer_link = JsCode('''
    class HyperlinkRenderer {
        init(params) {
            this.eGui = document.createElement('a');
            if (params.value && typeof params.value === 'string' && params.value.startsWith('http')) {
                this.eGui.innerText = '매물 보기';
                this.eGui.href = params.value;
                this.eGui.target = '_blank';
                this.eGui.style.color = 'blue';
                this.eGui.style.textDecoration = 'underline';
            } else { this.eGui.innerText = ''; }
        }
        getGui() { return this.eGui; }
        refresh(params) { return false; }
    }
    ''')

    # --- ▼▼▼ 태그 컬럼 렌더러 CSS 수정 ▼▼▼ ---
    tag_renderer = JsCode("""
    class TagRenderer {
        init(params) {
            this.eGui = document.createElement('div');
            // this.eGui.style.lineHeight = '1.5'; // 줄 간격 필요시 조절
            var tags = [];
            var value = params.value; // app.py에서 이미 shorten_text(str(x)) 적용됨

            // 단순 문자열 처리 (쉼표 구분)
            if (typeof value === 'string' && value.trim()) {
                 // 이미 shorten_text(str(x)) 처리 되었으므로, 파싱 로직 단순화 가능
                 // 예: "['tag1', 'tag2']..." -> "tag1, tag2" 형태 가정
                 // 실제 데이터 형태 보고 조정 필요
                 value = value.replace(/[\[\]'"]/g, ''); // 대괄호, 따옴표 제거
                tags = value.split(',').map(tag => tag.trim()).filter(tag => tag);
            } else if (Array.isArray(value)) {
                // 만약 배열 형태 데이터가 그대로 넘어온다면 (shorten_text 주석처리 시)
                tags = value.map(tag => String(tag).trim()).filter(tag => tag);
            }

            tags.forEach(tag => {
                if (tag) {
                    var span = document.createElement('span');
                    span.textContent = tag;
                    span.style.display = 'inline-block';
                    // 이전 CSS 스타일 적용
                    span.style.backgroundColor = '#24516e'; // 파란색 배경
                    span.style.color = 'white';           // 흰색 글씨
                    span.style.padding = '0px 8px';       // 위아래 패딩 0, 좌우 8
                    span.style.margin = '2px';
                    span.style.borderRadius = '20px';      // 매우 둥근 모서리 (원통형)
                    span.style.fontSize = '12px';         // 폰트 크기
                    span.style.whiteSpace = 'nowrap'; // 태그 내 줄바꿈 방지
                    this.eGui.appendChild(span);
                }
            });
        }
        getGui() { return this.eGui; }
        refresh(params) { return false; }
    }
    """)
    # --- ▲▲▲ 태그 컬럼 렌더러 CSS 수정 완료 ▲▲▲ ---

    # --- ▼▼▼ 컬럼 너비 조정 ▼▼▼ ---
    # '매물 링크'는 고정 너비 없이 자동 조절 (기존 유지)
    gb.configure_column("매물 링크", cellRenderer=cell_renderer_link, suppressMenu=True, filter=False)

    # '태그'는 렌더러 사용, 너비는 적절히 설정 (wrapText=True 기본값 적용됨)
    gb.configure_column('태그', cellRenderer=tag_renderer) # 예: 200으로 줄임 (필요시 조절)

    # '매물명'은 너비 설정 및 줄바꿈 방지
    gb.configure_column('매물명', width=180, wrapText=False) # 예: 180으로 줄임

    # '특징'은 너비를 더 줄이고, 줄바꿈 방지, 최대 너비 설정 (선택적)
    gb.configure_column('특징', width=50, wrapText=False) # 예: 기본 150, 최대 250

    # '중개사'는 너비를 크게 줄이고, 줄바꿈 방지
    gb.configure_column('중개사', width=50, wrapText=False, maxWidth=50) # 예: 100으로 설정

    # '정보제공'은 너비를 크게 줄이고, 줄바꿈 방지
    gb.configure_column('정보제공', width=50, wrapText=False) # 예: 100으로 설정

    # 그 외 자주 사용되거나 내용이 짧은 컬럼 너비 조절 (선택 사항)
    gb.configure_column('동', width=80, wrapText=False)
    gb.configure_column('거래유형', width=70, wrapText=False)
    gb.configure_column('층수', width=70, wrapText=False)
    gb.configure_column('방향', width=60, wrapText=False)
    gb.configure_column('연식', width=45)
    gb.configure_column('총세대수', witdh=50)
    gb.configure_column('공급면적', width=80)
    gb.configure_column('가격', width=130) # 가격은 비교적 중요하므로 적당히 확보

    # --- ▲▲▲ 컬럼 너비 조정 완료 ▲▲▲ ---

    gridOptions = gb.build()

    # 컬럼 크기 자동 조정 모드 (선택 사항, fitGridWidth가 일반적) [6]
    gridOptions['columnAutoSizeStrategy'] = {
        'type': 'fitGridWidth' # 컬럼 전체 너비를 그리드 너비에 맞춤
    }

    return gridOptions

def display_table_with_aggrid(df):
    """데이터프레임을 AgGrid를 사용하여 Streamlit에 표시합니다."""
    if df.empty:
        st.info("표시할 데이터가 없습니다.")
        return

    try:
        gridOptions = get_aggrid_options(df)
        AgGrid(
            df,
            gridOptions=gridOptions,
            width='100%',
            height=600,
            theme='streamlit',
            allow_unsafe_jscode=True, # JsCode 사용 허용
            enable_enterprise_modules=True, # 엔터프라이즈 모듈 비활성화
            key=f'aggrid_{hash(df.to_string())}',
            reload_data=True,
            update_mode='MODEL_CHANGED',
            # unsafe_allow_html=True 제거 (JsCode 렌더러 사용 시 불필요 및 보안 위험)
        )
    except Exception as e:
        st.error(f"AgGrid 표시 중 오류 발생: {e}")
        st.dataframe(df) # 오류 시 기본 데이터프레임 표시

