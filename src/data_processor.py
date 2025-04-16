# src/data_processor.py
import streamlit as st
import pandas as pd
import numpy as np
# src 패키지 내 utils 모듈에서 필요한 함수 임포트
from .utils import convert_price_to_number, extract_numeric_area, extract_floor

def create_summary(df_detail):
    """
    상세 데이터프레임(df_detail)에서 아파트 단지 및 평형별 요약 데이터를 생성합니다.
    '구', '동' 컬럼이 df_detail에 반드시 포함되어야 합니다.
    """
    df_summary = df_detail.copy()

    required_cols = ['구', '동', '매물명', '공급면적', '가격', '거래유형', '연식', '총세대수']
    if not all(col in df_summary.columns for col in required_cols):
        missing = [col for col in required_cols if col not in df_summary.columns]
        st.error(f"요약 생성 오류: 상세 데이터에 필수 컬럼 누락: {', '.join(missing)}")
        return pd.DataFrame(columns=[
            "구", "동", "아파트명", "연식", "총세대수", "공급면적", "평형",
            "매매개수", "전세개수", "매매평균", "매매중간", "매매최대", "매매최소",
            "전세평균", "전세중간", "전세최대", "전세최소", "갭(매매-전세)(평균)"
        ])

    df_summary['가격_숫자'] = df_summary['가격'].apply(convert_price_to_number)
    df_summary["공급면적_숫자"] = df_summary["공급면적"].apply(extract_numeric_area)
    df_summary["평형"] = np.where(
        df_summary["공급면적_숫자"].notna() & (df_summary["공급면적_숫자"] != 0),
        (df_summary["공급면적_숫자"] / 3.3).round(1),
        None
    )

    # 정보제공 컬럼 이름 변경 (CP사 -> 정보제공) - df_detail에 해당 컬럼이 있는지 확인 필요
    if "CP사" in df_summary.columns:
        df_summary = df_summary.rename(columns={"CP사": "정보제공"})

    # 정보제공 컬럼 기준으로 필터링
    if "정보제공" in df_summary.columns:
        df_filtered = df_summary[df_summary["정보제공"] != "한국공인중개사협회"].copy()
    else:
        df_filtered = df_summary.copy() # 정보제공 컬럼 없으면 필터링 없이 진행

    grouping_cols = ["구", "동", "매물명", "공급면적", "평형", "연식", "총세대수"]

    # 필수 그룹핑 컬럼 존재 확인
    missing_group_cols = [col for col in grouping_cols if col not in df_filtered.columns]
    if missing_group_cols:
        st.error(f"요약 생성 오류: 그룹핑에 필요한 컬럼 누락: {', '.join(missing_group_cols)}")
        # 빈 데이터프레임 또는 기본 구조를 반환
        return pd.DataFrame(columns=[
            "구", "동", "아파트명", "연식", "총세대수", "공급면적", "평형",
            "매매개수", "전세개수", "매매평균", "매매중간", "매매최대", "매매최소",
            "전세평균", "전세중간", "전세최대", "전세최소", "갭(매매-전세)(평균)"
        ])


    agg_funcs = {
        "평균": ("가격_숫자", "mean"),
        "중간": ("가격_숫자", "median"),
        "최대": ("가격_숫자", "max"),
        "최소": ("가격_숫자", "min"),
        "개수": ("가격_숫자", "size")
    }

    # 가격 데이터가 없는 경우 집계 시 오류 발생 가능성 -> NaN 처리된 데이터 제외 고려
    df_agg_ready = df_filtered.dropna(subset=['가격_숫자']) # 가격이 NaN인 행 제외하고 집계

    # 집계 수행 (데이터가 없는 경우 빈 DF 반환될 수 있음)
    if not df_agg_ready.empty:
        summary_stats = df_agg_ready.groupby(grouping_cols + ["거래유형"], as_index=False).agg(**agg_funcs)
    else:
        summary_stats = pd.DataFrame() # 집계할 데이터 없으면 빈 DF

    # Pivot 테이블 변환 (데이터 있을 때만)
    if not summary_stats.empty:
        summary_pivot = summary_stats.pivot_table(
            index=grouping_cols,
            columns='거래유형',
            values=['평균', '중간', '최대', '최소', '개수'],
            fill_value=pd.NA # 집계값 없는 경우 0 대신 NA로 채워서 타입 유지
        )

        summary_pivot.columns = [f'{col[1]}{col[0]}' for col in summary_pivot.columns]
        summary_pivot = summary_pivot.reset_index()
    else:
        # 집계 결과 없으면 기본 컬럼 구조 가진 빈 DF 생성
        summary_pivot = pd.DataFrame(columns=grouping_cols)

    # 갭 계산 (NA 값 고려)
    매매평균_col = '매매평균'
    전세평균_col = '전세평균'

    if 매매평균_col in summary_pivot.columns and 전세평균_col in summary_pivot.columns:
        # NA가 아닌 경우에만 계산, 한쪽이라도 NA면 결과도 NA
        summary_pivot["갭(매매-전세)(평균)"] = summary_pivot[매매평균_col].astype(float) - summary_pivot[전세평균_col].astype(float)
    else:
        summary_pivot["갭(매매-전세)(평균)"] = pd.NA

    summary_pivot = summary_pivot.rename(columns={
        "매물명": "아파트명",
        "매매개수": "매매개수",
        "전세개수": "전세개수"
    })

    final_columns = [
        "구", "동", "아파트명", "연식", "총세대수", "공급면적", "평형",
        "매매개수", "전세개수", "매매평균", "매매중간", "매매최대", "매매최소",
        "전세평균", "전세중간", "전세최대", "전세최소", "갭(매매-전세)(평균)"
    ]
    existing_final_columns = [col for col in final_columns if col in summary_pivot.columns]
    summary_final = summary_pivot.reindex(columns=final_columns) # 모든 최종 컬럼 포함, 없는 값은 NA

    # 개수 컬럼 NA -> 0, 정수형 변환
    if '매매개수' in summary_final.columns:
        summary_final['매매개수'] = summary_final['매매개수'].fillna(0).astype(int)
    if '전세개수' in summary_final.columns:
        summary_final['전세개수'] = summary_final['전세개수'].fillna(0).astype(int)

    # 평균, 중간, 최대, 최소 등 수치형 컬럼도 필요 시 NA 처리 및 타입 변환
    numeric_summary_cols = ['매매평균', '매매중간', '매매최대', '매매최소',
                            '전세평균', '전세중간', '전세최대', '전세최소', '갭(매매-전세)(평균)']
    for col in numeric_summary_cols:
        if col in summary_final.columns:
            # pd.to_numeric으로 이미 숫자형(주로 float)으로 변환되었거나 원본이 숫자형임.
            # 추가적인 astype('Int64') 변환을 시도하지 않습니다.
            # 필요하다면 여기서 .astype(float) 등으로 명시할 수 있으나, 보통 불필요합니다.
            pass # 특별한 타입 변환 없이 넘어감

    # 또는 Pandas의 nullable float 타입 사용 시 (선택 사항):
    # for col in numeric_summary_cols:
    #     if col in summary_final.columns:
    #         summary_final[col] = pd.to_numeric(summary_final[col], errors='coerce').astype('Float64')

    return summary_final


def filter_out_low_floors(df, exclude_low_floors):
    """
    '저층 제외' 옵션에 따라 데이터프레임을 필터링합니다.
    """
    if not exclude_low_floors:
        return df

    df_filtered = df.copy()
    if '층수' in df_filtered.columns:
        # extract_floor 함수는 문자열 반환하므로, NaN 처리 후 적용
        df_filtered['층'] = df_filtered['층수'].dropna().apply(extract_floor)
    else:
        st.warning("'층수' 컬럼이 없어 저층 필터링을 수행할 수 없습니다.")
        return df

    low_floor_criteria = ['1', '2', '3', '저']
    # '층' 컬럼이 생성되었고, 값이 있는 행에 대해서만 필터링
    df_filtered = df_filtered[
        df_filtered['층'].notna() & ~df_filtered['층'].isin(low_floor_criteria)
    ]
    # 임시 '층' 컬럼 제거 (필터링 후 제거해야 함)
    if '층' in df_filtered.columns:
        df_filtered = df_filtered.drop(columns=['층'])
    return df_filtered


def sort_dataframe(df, sort_columns, ascending_list):
    """
    주어진 정렬 기준과 순서에 따라 데이터프레임을 정렬합니다.
    """
    if not sort_columns or df.empty: # 정렬 기준 없거나 df 비어있으면 원본 반환
        return df

    df_sorted = df.copy()

    # 임시 정렬용 컬럼 생성 리스트
    temp_sort_cols = []
    actual_sort_columns = list(sort_columns) # 복사본 사용

    if '가격' in sort_columns:
        if '가격_숫자_정렬용' not in df_sorted.columns: # 기존 임시 컬럼명과 겹치지 않게
            try:
                df_sorted['가격_숫자_정렬용'] = df_sorted['가격'].apply(convert_price_to_number)
                temp_sort_cols.append('가격_숫자_정렬용')
            except Exception as e:
                st.error(f"가격 숫자 변환 중 오류 (정렬): {e}")
                # 가격 정렬 불가 시, 해당 기준 제거
                indices_to_remove = [i for i, col in enumerate(sort_columns) if col == '가격']
                actual_sort_columns = [col for i, col in enumerate(sort_columns) if i not in indices_to_remove]
                ascending_list = [asc for i, asc in enumerate(ascending_list) if i not in indices_to_remove]

        # 실제 정렬 기준 리스트 업데이트
        actual_sort_columns = ['가격_숫자_정렬용' if col == '가격' else col for col in actual_sort_columns]

    # 다른 숫자형 컬럼(예: 공급면적)도 정렬 필요 시 유사 로직 추가 가능
    if '공급면적' in sort_columns:
        if '공급면적_숫자_정렬용' not in df_sorted.columns:
            try:
                df_sorted['공급면적_숫자_정렬용'] = df_sorted['공급면적'].apply(extract_numeric_area)
                temp_sort_cols.append('공급면적_숫자_정렬용')
            except Exception as e:
                st.error(f"공급면적 숫자 변환 중 오류 (정렬): {e}")
                indices_to_remove = [i for i, col in enumerate(sort_columns) if col == '공급면적']
                actual_sort_columns = [col for i, col in enumerate(sort_columns) if i not in indices_to_remove]
                ascending_list = [asc for i, asc in enumerate(ascending_list) if i not in indices_to_remove]
        actual_sort_columns = ['공급면적_숫자_정렬용' if col == '공급면적' else col for col in actual_sort_columns]


    # 유효한 정렬 기준 컬럼 및 순서 확인
    valid_sort_info = [
        (col, asc) for col, asc in zip(actual_sort_columns, ascending_list) if col in df_sorted.columns
    ]

    if not valid_sort_info:
        st.warning("유효한 정렬 기준이 없습니다.")
        # 임시 컬럼 제거 후 원본 반환
        if temp_sort_cols:
            df_sorted = df_sorted.drop(columns=temp_sort_cols, errors='ignore')
        return df_sorted

    valid_sort_columns = [info[0] for info in valid_sort_info]
    valid_ascending_list = [info[1] for info in valid_sort_info]

    # 데이터 정렬 (NA 값 처리: 정렬 시 마지막으로 보내도록 설정)
    try:
        df_sorted = df_sorted.sort_values(
            by=valid_sort_columns,
            ascending=valid_ascending_list,
            na_position='last' # NA 값을 뒤로 보냄
        )
    except Exception as e:
        st.error(f"데이터 정렬 중 오류: {e}")
        # 정렬 실패 시 임시 컬럼 제거 후 반환 (정렬 안 된 상태)
        if temp_sort_cols:
            df_sorted = df_sorted.drop(columns=temp_sort_cols, errors='ignore')
        return df_sorted

    # 정렬에 사용된 임시 컬럼 제거
    if temp_sort_cols:
        df_sorted = df_sorted.drop(columns=temp_sort_cols, errors='ignore')

    return df_sorted
