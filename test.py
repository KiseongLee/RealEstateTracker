import streamlit as st
import requests
import json

st.title("네이버 지도 Reverse Geocoding API 테스트")

# API 인증 키 설정
try:
    client_id = st.secrets["naver"]["client_id"]
    client_secret = st.secrets["naver"]["client_secret"]
except KeyError:
    st.warning("secrets.toml 파일에 네이버 API 키(client_id, client_secret)가 설정되지 않았습니다.")
    client_id = st.text_input("네이버 Cloud Client ID 입력")
    client_secret = st.text_input("네이버 Cloud Client Secret 입력", type="password")
    if not client_id or not client_secret:
        st.stop()

# 테스트 좌표 (URL에서 제공된 좌표 사용)
default_lng = 127.585
default_lat = 34.9765

st.subheader("좌표 입력")
lng = st.number_input("경도(Longitude)", value=default_lng, format="%.6f")
lat = st.number_input("위도(Latitude)", value=default_lat, format="%.6f")

# API 요청 설정
st.subheader("API 요청 설정")
output_format = st.selectbox("출력 형식", ["json", "xml"], index=0)
order_options = ["legalcode", "admcode", "addr", "roadaddr"]
orders = st.multiselect("주소 정보 요청", order_options, default=order_options)

if st.button("API 호출 테스트"):
    # 좌표 문자열 생성
    coords = f"{lng},{lat}"
    order_string = ",".join(orders)
    
    # 제공된 URL 형식 사용 (maps.apigw.ntruss.com 도메인)
    url = "https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc"
    
    # API 요청 헤더
    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id,
        "X-NCP-APIGW-API-KEY": client_secret
    }
    
    # API 요청 파라미터
    params = {
        "coords": coords,
        "output": output_format,
        "orders": order_string
    }
    
    # 요청 정보 표시
    st.write("--- 요청 정보 ---")
    st.write(f"Method: GET")
    st.write(f"URL: {url}")
    st.write(f"Params: {params}")
    st.write(f"Headers: {{ 'X-NCP-APIGW-API-KEY-ID': '{client_id[:5]}...', 'X-NCP-APIGW-API-KEY': '{client_secret[:5]}...' }}")
    
    try:
        # API 요청 보내기
        response = requests.get(url, headers=headers, params=params)
        
        # 응답 정보 표시
        st.write("--- 응답 정보 ---")
        st.write(f"Status Code: {response.status_code}")
        
        # 응답 헤더 표시
        st.write("Response Headers:")
        st.write(response.headers)
        
        # 응답 본문 표시
        st.write("Response Body:")
        st.text(response.text)
        
        # JSON 응답인 경우 구조화된 데이터로 표시
        if output_format == "json" and response.status_code == 200:
            try:
                data = response.json()
                st.json(data)
                
                # 성공적인 응답에서 주소 정보 추출
                if "results" in data:
                    st.write("--- 추출된 주소 정보 ---")
                    for idx, result in enumerate(data["results"]):
                        st.write(f"**결과 {idx+1} - 유형: {result.get('name')}**")
                        
                        region = result.get("region", {})
                        address_parts = []
                        
                        # 지역 정보 수집
                        area0 = region.get("area0", {}).get("name", "")  # 국가
                        if area0:
                            address_parts.append(area0)
                        area1 = region.get("area1", {}).get("name", "")  # 시도
                        if area1:
                            address_parts.append(area1)
                        area2 = region.get("area2", {}).get("name", "")  # 시군구
                        if area2:
                            address_parts.append(area2)
                        area3 = region.get("area3", {}).get("name", "")  # 읍면동
                        if area3:
                            address_parts.append(area3)
                        area4 = region.get("area4", {}).get("name", "")  # 리
                        if area4:
                            address_parts.append(area4)
                            
                        st.write("주소: " + " ".join(address_parts))
                        
                        # 상세 주소 정보 (지번 또는 도로명)
                        if result.get("name") == "addr" and "land" in result:
                            land = result["land"]
                            number1 = land.get("number1", "")
                            number2 = land.get("number2", "")
                            st.write(f"지번: {number1}" + (f"-{number2}" if number2 else ""))
                            
                        elif result.get("name") == "roadaddr" and "land" in result:
                            land = result["land"]
                            road_name = land.get("name", "")
                            number1 = land.get("number1", "")
                            number2 = land.get("number2", "")
                            building = land.get("addition0", {}).get("value", "")
                            
                            road_detail = f"{road_name} {number1}"
                            if number2:
                                road_detail += f"-{number2}"
                            if building:
                                road_detail += f" ({building})"
                            
                            st.write(f"도로명: {road_detail}")
            except json.JSONDecodeError:
                st.error("JSON 파싱 실패. 응답이 JSON 형식이 아닙니다.")
        
        # HTTP 요청 실패 메시지 표시
        if response.status_code >= 400:
            st.error(f"HTTP 요청 실패: {response.status_code} {response.reason}")
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            st.error(f"URL: {url}?{query_string}")
            
    except requests.exceptions.RequestException as e:
        st.error(f"API 요청 실패: {str(e)}")

st.write("""
**참고사항:**
- 이 코드는 'https://maps.apigw.ntruss.com/map-reversegeocode/v2/gc' URL을 사용합니다.
- 이전에 사용하던 'naveropenapi.apigw.ntruss.com' 또는 'naveropenapi.apigw.gov-ntruss.com' 대신 새로운 도메인을 사용합니다.
- API 키는 네이버 클라우드 플랫폼에서 발급받은 Client ID와 Client Secret을 사용합니다.
- API 호출 시 오류가 발생하면 네이버 클라우드 플랫폼 콘솔에서 API 권한 설정을 확인하세요.
""")
