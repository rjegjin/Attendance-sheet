import pandas as pd
import json
import re
import os
from datetime import datetime

# --- 설정 (Configuration) ---
# 원본 엑셀 파일명 (확장자 .xlsx 포함)
TARGET_FILENAME = '2026학년도 목일중학교 학사일정안18.xlsx'
# 데이터를 읽어올 시트 이름
TARGET_SHEET_NAME = '2026학년도 전체학년 학사일정'

def parse_date_value(value):
    """
    엑셀 셀 값을 정수형 '일(Day)'로 변환합니다.
    """
    if pd.isna(value) or value == '':
        return None
    
    # 1. datetime 객체인 경우 (엑셀은 날짜를 바로 datetime으로 읽을 수 있음)
    if isinstance(value, datetime):
        return value.day
        
    # 2. 문자열인 경우
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
            
    # 3. 숫자(float/int)인 경우
    if isinstance(value, (int, float)):
        return int(value)
        
    return None

def extract_holidays_to_json(file_path):
    # 파일 존재 여부 확인
    if not os.path.exists(file_path):
        print(f"\n[Error] 파일을 찾을 수 없습니다: {file_path}")
        print(f"현재 작업 경로: {os.getcwd()}")
        return None

    df = None
    
    # [Smart Loader] 엑셀 파일 읽기
    try:
        print(f"Trying to read Excel file: {file_path}...")
        
        # 1. 특정 시트 이름으로 시도
        try:
            df = pd.read_excel(file_path, sheet_name=TARGET_SHEET_NAME, header=None, engine='openpyxl')
            print(f"✅ Success reading sheet: '{TARGET_SHEET_NAME}'")
        except ValueError:
            # 해당 시트가 없으면 첫 번째 시트 읽기
            print(f"⚠️ Sheet '{TARGET_SHEET_NAME}' not found. Reading the first sheet instead.")
            df = pd.read_excel(file_path, sheet_name=0, header=None, engine='openpyxl')
            print("✅ Success reading first sheet!")
            
    except Exception as e:
        print(f"❌ Error reading Excel file: {e}")
        if "openpyxl" in str(e):
            print("👉 Tip: 'pip install openpyxl'을 실행하여 라이브러리를 설치해주세요.")
        return None

    try:
        # 월(Month) 컬럼(B열, index 1) Forward Fill
        df[1] = df[1].ffill()

        holidays = {}

        # [수정됨] 키워드 범위 확장
        include_keywords = [
            "대체공휴일", "재량휴업", "개교기념일", # 재량휴업일 -> 재량휴업 (포괄적 매칭)
            "어린이날", "석가탄신일", "부처님", 
            "현충일", "광복절", "추석", "개천절", "한글날", "성탄절", "신정", "선거", "수능"
        ]
        # 제외 키워드
        exclude_keywords = ["자치", "동아리", "방과후"]

        # 요일별 컬럼 매핑 (날짜열 Index, 행사열 Index)
        day_columns = [
            (2, 4),   # 월
            (5, 7),   # 화
            (8, 10),  # 수
            (11, 13), # 목
            (14, 16)  # 금
        ]

        # 행 순회
        for idx, row in df.iterrows():
            raw_month = row[1]
            
            try:
                # '3월', '3' 등 파싱
                month = int(str(raw_month).replace('월', '').strip())
            except (ValueError, AttributeError):
                continue

            # 연도 계산 (3~12월: 2026, 1~2월: 2027)
            year = 2026 if month >= 3 else 2027

            for date_col_idx, event_col_idx in day_columns:
                if date_col_idx >= len(row) or event_col_idx >= len(row):
                    continue

                date_val = row[date_col_idx]
                event_val = row[event_col_idx]

                day = parse_date_value(date_val)
                if day is None:
                    continue
                
                if pd.isna(event_val) or str(event_val).strip() == '':
                    continue
                
                event_name = str(event_val).strip()

                # 키워드 매칭 로직
                has_include = any(k in event_name for k in include_keywords)
                has_exclude = any(k in event_name for k in exclude_keywords)

                if has_include and not has_exclude:
                    date_str = f"{year}-{month:02d}-{day:02d}"
                    holidays[date_str] = event_name

        # 필수 포함 주말/공휴일 (하드코딩 데이터 병합)
        fixed_holidays = {
            "2026-03-01": "3.1절",
            "2026-05-05": "어린이날",
            "2026-05-24": "부처님오신날",
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

        for date_key, name in fixed_holidays.items():
            if date_key not in holidays:
                holidays[date_key] = name

        sorted_holidays = dict(sorted(holidays.items()))
        return sorted_holidays

    except Exception as e:
        print(f"Error during extraction: {e}")
        return None

# --- [Main Execution] ---
if __name__ == "__main__":
    print(f"🔄 Analyzing file: {TARGET_FILENAME}...")
    
    # 1. 휴일 추출
    holidays_data = extract_holidays_to_json(TARGET_FILENAME)
    
    if holidays_data:
        # 2. 파일명 동적 생성 (holidays_2026.json)
        target_year = "2026"
        if holidays_data:
             first_date = list(holidays_data.keys())[0]
             target_year = first_date.split('-')[0]

        output_filename = f"holidays_{target_year}.json"
        
        # 3. JSON 파일 저장
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(holidays_data, f, ensure_ascii=False, indent=4)
            
        print(f"✅ Successfully saved to: {output_filename}")
        
        # 결과 확인용 출력
        print("\n[Extracted Holidays List]")
        for k, v in holidays_data.items():
            print(f"{k}: {v}")
    else:
        print("❌ Failed to extract holidays.")