# src/exporters.py
import pandas as pd
from io import BytesIO
import numpy as np # NaN 값 처리 위해 추가
# src 패키지 내 utils 모듈에서 필요한 함수 임포트
from .utils import format_eok
# data_processor 임포트는 제거 (순환 참조 방지, 필요 시 함수 인자로 전달받도록 구조 변경)
# from .data_processor import create_summary

def to_excel(df_detail, summary_df, area_name, current_date, exclude_low_floors):
    """
    상세 데이터(df_detail)와 요약 데이터(summary_df)를 별도의 시트로 Excel 파일 생성합니다.
    summary_df는 외부에서 생성되어 전달받습니다.
    """
    summary_formatted = summary_df.copy()
    format_cols = [
        '매매평균', '매매중간', '매매최대', '매매최소',
        '전세평균', '전세중간', '전세최대', '전세최소',
        '갭(매매-전세)(평균)'
    ]
    for col in format_cols:
        if col in summary_formatted.columns:
            # Int64 타입의 NA를 처리하기 위해 apply 전에 float으로 변환 후 NA 처리
            summary_formatted[col] = summary_formatted[col].astype(float).apply(format_eok)

    base_name = f"{area_name}_{current_date}"
    if exclude_low_floors:
        base_name += "_저층제외"
    sheet1_name = f"{base_name}_상세"
    sheet2_name = f"{base_name}_요약"
    # 시트 이름 길이 제한 (Excel 제한: 31자) 고려
    sheet1_name = sheet1_name[:31]
    sheet2_name = sheet2_name[:31]


    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 상세 데이터 시트 작성
            df_detail.to_excel(writer, index=False, sheet_name=sheet1_name)
            workbook = writer.book
            worksheet_detail = writer.sheets[sheet1_name]
            url_format = workbook.add_format({'font_color': 'blue', 'underline': 1})
            # 하이퍼링크 설정 (NaN 값 체크 추가)
            if "매물 링크" in df_detail.columns:
                link_col_idx = df_detail.columns.get_loc("매물 링크")
                for row_num, link in enumerate(df_detail["매물 링크"], start=1):
                    if pd.notna(link) and isinstance(link, str) and link.startswith('http'):
                        worksheet_detail.write_url(row_num, link_col_idx, link, cell_format=url_format, string='Link')

            # 요약 데이터 시트 작성 (요약 데이터가 있을 경우)
            if not summary_formatted.empty:
                summary_formatted.to_excel(writer, index=False, sheet_name=sheet2_name)

            # (선택) 컬럼 너비 자동 조정 (데이터 양 많으면 느려질 수 있음)
            # worksheet_detail.autofit()
            # if not summary_formatted.empty:
            #     worksheet_summary = writer.sheets[sheet2_name]
            #     worksheet_summary.autofit()

    except Exception as e:
        print(f"Excel 파일 생성 중 오류: {e}") # Streamlit 에러 대신 콘솔 로그
        # 오류 발생 시 빈 BytesIO 객체 반환 또는 None 반환 고려
        return BytesIO().getvalue() # 빈 데이터 반환

    return output.getvalue()

def export_combined_excel(selected_areas_data, current_date):
    """
    선택된 여러 지역의 상세/요약 데이터를 종합하여 하나의 Excel 파일로 생성합니다.
    """
    output = BytesIO()
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            all_details = []
            all_summaries = []
            cover_data = []

            # 1. 데이터 수집 및 표지 데이터 생성
            for (division, dong, exclude_low_floors), data in selected_areas_data.items():
                # 데이터 유효성 검사 (detail, summary 키 존재 여부)
                if 'detail' not in data or 'summary' not in data:
                    print(f"경고: 키 '{division} {dong}' 데이터에 'detail' 또는 'summary' 누락. 종합 리포트에서 제외됩니다.")
                    continue

                detail_df = data['detail'].copy()
                summary_df = data['summary'].copy()
                display_name = f"{division} {dong}{'_저층제외' if exclude_low_floors else ''}"

                # 지역명 컬럼 추가 (만약 이미 존재하면 덮어쓰지 않도록)
                if '지역구분' not in detail_df.columns:
                    detail_df['지역구분'] = display_name
                if '지역구분' not in summary_df.columns:
                    summary_df['지역구분'] = display_name


                all_details.append(detail_df)
                all_summaries.append(summary_df)

                # 표지 데이터 구성
                cover_data.append({
                    '지역명': display_name,
                    '매매 개수': len(detail_df[detail_df['거래유형'] == '매매']),
                    '전세 개수': len(detail_df[detail_df['거래유형'] == '전세']),
                    '총 데이터 수': len(detail_df)
                })

            # 2. 표지 시트 작성
            if cover_data:
                pd.DataFrame(cover_data).to_excel(writer, sheet_name='종합 리포트', index=False)

            # 3. 통합 요약 시트 작성
            if all_summaries:
                combined_summary = pd.concat(all_summaries, ignore_index=True)

                # 중복 제거 기준 컬럼 정의 (고유 식별 정보 위주)
                duplicate_check_columns = [
                    "구", "동", "아파트명", "연식", "총세대수", "공급면적", "평형", "지역구분" # 지역구분도 포함하여 다른 지역 동일 매물은 유지
                ]
                subset_cols = [col for col in duplicate_check_columns if col in combined_summary.columns]
                if subset_cols:
                    combined_summary = combined_summary.drop_duplicates(subset=subset_cols, keep='first')

                # 갭 기준 오름차순 정렬 (숫자 변환 및 NA 처리)
                if '갭(매매-전세)(평균)' in combined_summary.columns:
                    # 정렬 전 Int64 -> float 변환 (NA 유지)
                    combined_summary['갭_정렬용'] = combined_summary['갭(매매-전세)(평균)'].astype(float)
                    combined_summary = combined_summary.sort_values(by='갭_정렬용', ascending=True, na_position='last')
                    combined_summary = combined_summary.drop(columns=['갭_정렬용'])

                # 포맷팅 적용
                format_cols = [
                    '매매평균', '매매중간', '매매최대', '매매최소',
                    '전세평균', '전세중간', '전세최대', '전세최소',
                    '갭(매매-전세)(평균)'
                ]
                summary_formatted_combined = combined_summary.copy() # 포맷팅용 복사본
                for col in format_cols:
                    if col in summary_formatted_combined.columns:
                        summary_formatted_combined[col] = summary_formatted_combined[col].astype(float).apply(format_eok)


                # 컬럼 순서 조정 (지역구분을 맨 앞으로)
                cols = ['지역구분'] + [col for col in summary_formatted_combined.columns if col != '지역구분']
                # 시트 이름 길이 제한
                summary_sheet_name = f"통합 요약_{current_date}"[:31]
                summary_formatted_combined[cols].to_excel(writer, sheet_name=summary_sheet_name, index=False)


            # 4. 개별 상세 시트 생성 및 하이퍼링크 설정
            workbook = writer.book
            url_format = workbook.add_format({'font_color': 'blue', 'underline': 1})
            for (division, dong, exclude_low_floors), data in selected_areas_data.items():
                # 데이터 유효성 검사 반복 (위에서 했지만 안전하게)
                if 'detail' not in data: continue

                detail_df = data['detail']
                base_name = f"{division}_{dong}_{current_date}{'_저층제외' if exclude_low_floors else ''}"
                sheet_name = f"{base_name}_상세"[:31] # 시트 이름 길이 제한

                detail_df.to_excel(writer, sheet_name=sheet_name, index=False)
                worksheet = writer.sheets[sheet_name]

                if "매물 링크" in detail_df.columns:
                    link_col_idx = detail_df.columns.get_loc("매물 링크")
                    for row_num, link in enumerate(detail_df["매물 링크"], start=1):
                        if pd.notna(link) and isinstance(link, str) and link.startswith('http'):
                            worksheet.write_url(row_num, link_col_idx, link, cell_format=url_format, string='Link')

                # (선택) 개별 상세 시트 컬럼 너비 자동 조정
                # worksheet.autofit()

    except Exception as e:
        print(f"종합 Excel 파일 생성 중 오류: {e}") # Streamlit 에러 대신 콘솔 로그
        return BytesIO().getvalue() # 빈 데이터 반환

    return output.getvalue()

# CSV 내보내기 함수 (현재 app.py에서 사용 안 함, 필요 시 주석 해제)
# def to_csv_with_links(df):
#     """
#     데이터프레임을 UTF-8 (BOM 포함) CSV 문자열로 변환합니다.
#     """
#     try:
#         return df.to_csv(index=False, encoding='utf-8-sig')
#     except Exception as e:
#         print(f"CSV 생성 중 오류: {e}")
#         return "" # 오류 시 빈 문자열 반환
