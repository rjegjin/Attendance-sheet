import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_FILE = os.path.join(BASE_DIR, "service_key.json")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1Jlyok_qOggzj-KeC1O8xqa6OPyRm8KDw9P7ojNXc4UE/edit"

def diagnose_header():
    print("🕵️‍♂️ [헤더 정밀 진단] 시작...")
    
    if not os.path.exists(KEY_FILE):
        print("❌ 키 파일이 없습니다.")
        return

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_FILE, scope)
    client = gspread.authorize(creds)
    
    try:
        doc = client.open_by_url(SHEET_URL)
        # 보통 3월이 기준이 되므로 3월 확인
        ws = None
        for cand in ["3월", "03월"]:
            try: ws = doc.worksheet(cand); break
            except: pass
            
        if not ws:
            print("❌ 3월 시트를 못 찾았습니다.")
            return

        print(f"✅ '{ws.title}' 시트 접속 성공. 상위 5줄을 분석합니다.")
        rows = ws.get_all_values()[:5]
        
        header_row = None
        header_idx = -1
        
        # 헤더 찾기
        for i, row in enumerate(rows):
            row_str = str(row)
            if "번호" in row_str and ("이름" in row_str or "성명" in row_str):
                header_row = row
                header_idx = i
                print(f"📍 헤더 발견 (Row {i}): {row}")
                break
        
        if header_row:
            print("\n🔬 [열 인덱스 분석]")
            for idx, col_name in enumerate(header_row):
                if not col_name.strip(): continue
                print(f"   - Index {idx}: '{col_name}'")
                
                if "이름" in col_name or "성명" in col_name:
                    print(f"     👉 [타겟 확인] 이름은 {idx}번째 열입니다!")
            
            # 실제 데이터 샘플 확인 (헤더 다음 줄)
            if len(rows) > header_idx + 1:
                sample = rows[header_idx + 1]
                print(f"\n🧪 데이터 샘플 확인 (Row {header_idx + 1}):")
                print(f"   - 전체: {sample}")
                # 이름 열 값이 맞는지 확인
                name_cols = [i for i, c in enumerate(header_row) if "이름" in c or "성명" in c]
                for nc in name_cols:
                     print(f"   👉 Index {nc}의 값: '{sample[nc]}'")

        else:
            print("❌ '번호'와 '이름'이 포함된 헤더 줄을 못 찾았습니다.")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    diagnose_header()