import pandas as pd
import json
import re
from datetime import datetime

def parse_date_value(value):
    """
    엑셀/CSV에서 읽어온 날짜 셀 값을 정수형 '일(Day)'로 변환합니다.
    - 1900-01-05 (datetime/str) -> 5
    - "5" (str) -> 5
    - 5 (int/float) -> 5
    """
    if pd.isna(value) or value == '':
        return None
    
    # 1. 문자열인 경우
    if isinstance(value, str):
        value = value.strip()
        # "1900-01-05" 형식 처리
        if '-' in value:
            try:
                dt = pd.to_datetime(value, errors='coerce')
                if not pd.isna(dt):
                    return dt.day
            except:
                pass
        # 단순 숫자 문자열 처리
        if value.isdigit():
            return int(value)
            
    # 2. 숫자(float/int)인 경우
    if isinstance(value, (int, float)):
        return int(value)
        
    # 3. 이미 datetime 객체인 경우
    if isinstance(value, datetime):
        return value.day
        
    return None

def extract_holidays_to_json(csv_file_path, output_json_path):
    try:
        # 1. 데이터 로드 (Header가 없는 것으로 간주하거나, 첫 줄부터 데이터일 수 있음)
        # B열이 Index 1, C열이 Index 2...
        df = pd.read_csv(csv_file_path, header=None)
        
        # 2. 월(Month) 컬럼(B열, index 1) Forward Fill 처리
        # 빈칸이면 이전 행의 값을 가져옴
        df[1] = df[1].ffill()

        holidays = {}

        # 필터링 키워드 정의
        include_keywords = [
            "대체공휴일", "재량휴업일", "어린이날", "석가탄신일", "부처님", 
            "현충일", "광복절", "추석", "개천절", "한글날", "성탄절", "신정", "선거"
        ]
        exclude_keywords = ["자치", "동아리"]

        # 3. 요일별 컬럼 매핑 (날짜열 Index, 행사열 Index)
        # 월: C(2), E(4) / 화: F(5), H(7) / 수: I(8), K(10) / 목: L(11), N(13) / 금: O(14), Q(16)
        day_columns = [
            (2, 4),   # 월
            (5, 7),   # 화
            (8, 10),  # 수
            (11, 13), # 목
            (14, 16)  # 금
        ]

        # 4. 행 순회
        for idx, row in df.iterrows():
            raw_month = row[1]
            
            # 월 정보가 없거나 숫자가 아니면 스킵 (헤더나 빈 줄일 가능성)
            try:
                month = int(str(raw_month).replace('월', '').strip())
            except (ValueError, AttributeError):
                continue

            # 연도 계산 로직 (3월~12월: 2026, 1월~2월: 2027)
            year = 2026 if month >= 3 else 2027

            # 각 요일별 컬럼 쌍 확인
            for date_col_idx, event_col_idx in day_columns:
                # 인덱스 범위 체크
                if date_col_idx >= len(row) or event_col_idx >= len(row):
                    continue

                date_val = row[date_col_idx]
                event_val = row[event_col_idx]

                # 날짜 파싱
                day = parse_date_value(date_val)
                if day is None:
                    continue
                
                # 행사명 확인
                if pd.isna(event_val) or str(event_val).strip() == '':
                    continue
                
                event_name = str(event_val).strip()

                # 키워드 필터링
                has_include = any(k in event_name for k in include_keywords)
                has_exclude = any(k in event_name for k in exclude_keywords)

                if has_include and not has_exclude:
                    # 날짜 포맷팅 (YYYY-MM-DD)
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    holidays[date_str] = event_name

        # 5. 필수 포함 주말/공휴일 하드코딩 (2026년 기준, 2027년 1,2월 포함)
        # 평일 데이터만 있는 경우 누락될 수 있는 실제 공휴일을 추가합니다.
        # 이미 맵에 존재하면 덮어쓰지 않거나, 명확한 국경일 명칭으로 업데이트합니다.
        fixed_holidays = {
            "2026-03-01": "3.1절",
            "2026-05-05": "어린이날",
            "2026-05-24": "부처님오신날", # 2026년 기준 일요일 -> 대체공휴일 발생 가능성 체크 필요하나 일단 원본 날짜 입력
            "2026-06-06": "현충일",
            "2026-08-15": "광복절",
            "2026-09-24": "추석 연휴",
            "2026-09-25": "추석",
            "2026-09-26": "추석 연휴",
            "2026-10-03": "개천절",
            "2026-10-09": "한글날",
            "2026-12-25": "성탄절",
            "2027-01-01": "신정"
        }

        # 하드코딩된 휴일 병합 (기존 추출된 데이터가 '대체공휴일' 등으로 더 구체적일 수 있으므로 주의)
        # 전략: 기존에 없으면 추가.
        for date_key, name in fixed_holidays.items():
            if date_key not in holidays:
                holidays[date_key] = name

        # 6. 날짜순 정렬
        sorted_holidays = dict(sorted(holidays.items()))

        # 7. JSON 저장
        with open(output_json_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_holidays, f, ensure_ascii=False, indent=4)
        
        print(f"Successfully extracted {len(sorted_holidays)} holidays to {output_json_path}")
        return sorted_holidays

    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return None
