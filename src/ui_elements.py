# src/ui_elements.py
import streamlit as st
import folium
from streamlit_folium import st_folium
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode, ColumnsAutoSizeMode
import pandas as pd

def create_folium_map():
    """Folium 지도를 생성하고 초기 설정을 적용합니다."""
    default_location = [37.5665, 126.9780]
    m = folium.Map(location=default_location, zoom_start=11)
    m.add_child(folium.LatLngPopup())
    return m

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
    gb.configure_column('태그', cellRenderer=tag_renderer, width=200) # 예: 200으로 줄임 (필요시 조절)

    # '매물명'은 너비 설정 및 줄바꿈 방지
    gb.configure_column('매물명', width=180, wrapText=False) # 예: 180으로 줄임

    # '특징'은 너비를 더 줄이고, 줄바꿈 방지, 최대 너비 설정 (선택적)
    gb.configure_column('특징', width=50, wrapText=False, maxWidth=100) # 예: 기본 150, 최대 250

    # '중개사'는 너비를 크게 줄이고, 줄바꿈 방지
    gb.configure_column('중개사', width=50, wrapText=False, maxWidth=50) # 예: 100으로 설정

    # '정보제공'은 너비를 크게 줄이고, 줄바꿈 방지
    gb.configure_column('정보제공', width=50, wrapText=False) # 예: 100으로 설정

    # 그 외 자주 사용되거나 내용이 짧은 컬럼 너비 조절 (선택 사항)
    gb.configure_column('동', width=80, wrapText=False)
    gb.configure_column('거래유형', width=70, wrapText=False)
    gb.configure_column('층수', width=70, wrapText=False)
    gb.configure_column('방향', width=60, wrapText=False)
    gb.configure_column('연식', width=60)
    gb.configure_column('총세대수', width=80)
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
            enable_enterprise_modules=False, # 엔터프라이즈 모듈 비활성화
            key=f'aggrid_{hash(df.to_string())}',
            reload_data=True,
            update_mode='MODEL_CHANGED',
            # unsafe_allow_html=True 제거 (JsCode 렌더러 사용 시 불필요 및 보안 위험)
        )
    except Exception as e:
        st.error(f"AgGrid 표시 중 오류 발생: {e}")
        st.dataframe(df) # 오류 시 기본 데이터프레임 표시

