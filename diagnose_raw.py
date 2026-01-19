import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

# [설정] 진단할 시트 월 (스크린샷에서 문제된 12월을 봅니다)
TARGET_MONTH_NAME = "12월" 

# 경로 설정 (키 파일 찾기 위함)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "service_key.json")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Jlyok_qOggzj-KeC1O8xqa6OPyRm8KDw9P7ojNXc4UE/edit"

def inspect_sheet():
    print("🕵️‍♂️ [데이터 정밀 부검] 시작합니다...")
    
    # 1. 인증
    if not os.path.exists(KEY_FILE):
        print(f"❌ 키 파일이 없습니다: {KEY_FILE}")
        return
    
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE, scope)
    client = gspread.authorize(creds)
    
    # 2. 시트 접속
    print(f"☁️ 구글 시트 접속 중... ({TARGET_MONTH_NAME})")
    try:
        doc = client.open_by_url(SHEET_URL)
        ws = doc.worksheet(TARGET_MONTH_NAME)
    except Exception as e:
        print(f"❌ 시트 접속 실패: {e}")
        return

    # 3. 데이터 가져오기 (날것 그대로)
    all_rows = ws.get_all_values()
    
    print("\n" + "="*60)
    print(f"📊 시트 구조 분석 (상위 5줄)")
    print("="*60)
    
    # 헤더 및 초기 데이터 출력
    for i, row in enumerate(all_rows[:5]):
        print(f"[Row {i}] {row}")

    print("\n" + "="*60)
    print(f"🔬 'TRUE' 데이터 추적 (상위 20줄 검사)")
    print("="*60)
    
    # 헤더 분석 (날짜가 어느 열에 있는지)
    header = all_rows[2] # 보통 3번째 줄(인덱스 2)에 날짜가 있다고 가정하고 확인
    print(f"📌 기준 헤더(Row 2): {header}")
    
    # 데이터 행 분석
    found_true = False
    for i, row in enumerate(all_rows):
        if i < 3: continue # 헤더 건너뛰기
        
        # 행에 'TRUE'가 포함되어 있는지 검사
        row_str = str(row).upper()
        if "TRUE" in row_str:
            found_true = True
            print(f"\n🚨 [발견] {i+1}행에서 TRUE 값 발견!")
            print(f"   학생 정보: {row[0]}번 {row[1]}") # 번호, 이름 가정
            
            # 어느 열(Column)에 TRUE가 있는지 지적
            for col_idx, cell_val in enumerate(row):
                if str(cell_val).upper() == "TRUE":
                    # 해당 열의 헤더 이름 가져오기 (범위 내라면)
                    col_name = header[col_idx] if col_idx < len(header) else "알수없음"
                    print(f"   👉 문제의 위치: {col_idx}열 (헤더: '{col_name}') -> 값: '{cell_val}'")
            
            # 너무 많이 출력되면 중단
            if i > 20: 
                print("\n... (이하 생략) ...")
                break
    
    if not found_true:
        print("\n❓ 이 범위 내에서는 'TRUE'가 발견되지 않았습니다.")
        print("   혹시 체크박스가 해제되어 'FALSE'만 있는 것은 아닌가요?")

if __name__ == "__main__":
    inspect_sheet()