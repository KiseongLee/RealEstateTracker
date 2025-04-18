# 부동산 실시간 호가 검색 프로그램

네이버 부동산 정보를 기반으로 특정 지역의 부동산 매물 정보를 조회하고 분석하는 Streamlit 애플리케이션입니다.

## 주요 기능

- 지도 인터페이스를 통해 지역 선택
- 선택 지역의 아파트 매매/전세 실시간 호가 목록 조회 (AgGrid 사용)
- 데이터 필터링 (저층 제외 등) 및 정렬 기능
- 매물 상세 정보 링크 제공
- 단지 및 평형별 요약 데이터 생성
- 조회된 데이터 및 요약 정보 Excel 파일 다운로드
- 여러 지역 데이터를 그룹으로 관리하고 종합 리포트 생성

## 설치 및 실행

1.  **저장소 클론:**
    ```
    git clone https://github.com/KiseongLee/RealEstateTracker.git
    cd RealEstateTracker
    ```

2.  **가상환경 생성 및 활성화 (권장):**
    ```
    python -m venv venv
    source venv/bin/activate  # Linux/macOS
    # venv\Scripts\activate  # Windows
    ```

3.  **필요 라이브러리 설치:**
    ```
    pip install -r requirements.txt --user
    ```

4.  **Streamlit 앱 실행:**
    ```
    streamlit run app.py or python -m streamlit run app.py
    ```

## 프로젝트 구조

-   `app.py`: 메인 애플리케이션 스크립트
-   `requirements.txt`: 의존성 라이브러리 목록
-   `src/`: 애플리케이션 소스 코드
    -   `utils.py`: 유틸리티 함수
    -   `data_handling.py`: 데이터 로딩 및 외부 스크립트 관리
    -   `data_processor.py`: 데이터 처리 및 분석
    -   `exporters.py`: 데이터 내보내기
    -   `ui_elements.py`: UI 컴포넌트 생성
    -   `external_scripts/`: 외부 데이터 수집 스크립트
-   `output/`: 실행 중 생성되는 데이터 파일 (JSON 등) 저장 위치
-   `tests/`: 테스트 코드

## 참고

-   데이터는 네이버 부동산 API를 통해 수집됩니다.
-   외부 스크립트 실행을 위해 `python3` 명령어가 시스템 PATH에 설정되어 있어야 할 수 있습니다.
-   config_sample.py -> config.py로 명을 변경하고 header와 cookie를 작성해야합니다. (참고 : https://iamgus.tistory.com/746 )
-   네이버 역지오코딩 API 설정을 위한 키값을 받아와야 합니다. (참고 : https://api.ncloud-docs.com/docs/application-maps-reversegeocoding)
