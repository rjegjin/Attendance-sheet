import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from bs4 import BeautifulSoup
import os
import glob
import re
import time
import datetime
# [수리] import 수정
from src.services.data_loader import get_master_roster, TARGET_YEAR
from src.paths import SERVICE_KEY_PATH, REPORTS_DIR

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Jlyok_qOggzj-KeC1O8xqa6OPyRm8KDw9P7ojNXc4UE/edit"

# [수리] 경로 수정
INPUT_DIR = os.path.join(str(REPORTS_DIR), "month")

ACADEMIC_MONTHS = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2]

def get_client():
    # [수리] 절대 경로 사용
    key_path = str(SERVICE_KEY_PATH)
    if not os.path.exists(key_path):
        print(f"❌ [오류] 인증 키 파일 없음: {key_path}")
        return None
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
    return gspread.authorize(creds)

# ... (이후 코드는 그대로 둡니다)

# ==========================================
# 3. HTML 파싱
# ==========================================
def parse_html_to_df(html_path):
    if not os.path.exists(html_path): return None
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
    table = soup.find('table')
    if not table: return None
    
    data = []
    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        if not cols: continue 
        try:
            # HTML 구조: [1]일자, [2]번호, [4]구분, [5]시간, [6]사유
            date_str = cols[1].get_text(strip=True)
            if not re.match(r'\d{4}\.\d{2}\.\d{2}', date_str): continue
            
            num = int(cols[2].get_text(strip=True))
            att_type = cols[4].get_text(strip=True)
            time_info = cols[5].get_text(strip=True)
            reason = cols[6].get_text(strip=True)
            
            full_text = att_type
            if time_info: full_text += f"({time_info})"
            if reason: full_text += f"[{reason}]"
            
            data.append({
                'date': date_str, 'num': num,
                'content': full_text, 'type': att_type
            })
        except: continue
    return pd.DataFrame(data)

# ==========================================
# 4. 데이터 변환 (수식 생성 포함)
# ==========================================
def prepare_smart_data(df_long, year, month, master_roster):
    import calendar
    _, last_day = calendar.monthrange(year, month)
    all_days = [f"{month}/{d}" for d in range(1, last_day + 1)]

    # 1. Pivot
    if df_long is not None and not df_long.empty:
        df_long['dt'] = pd.to_datetime(df_long['date'], format='%Y.%m.%d')
        df_long['day_idx'] = df_long['dt'].dt.day
        df_wide = df_long.pivot_table(index='num', columns='day_idx', values='content', aggfunc=lambda x: '\n'.join(x))
    else:
        df_wide = pd.DataFrame()

    all_nums = sorted(master_roster.keys())
    
    # 2. 헤더 생성 (수식 적용)
    # [번호, 이름, (공백), SMS, 날짜수식1, 빈칸, 날짜수식2, 빈칸...]
    # 날짜 수식: =DATE($B$1, $A$1, 1), =DATE($B$1, $A$1, 2)...
    headers = ["번호", "이름", "", "SMS 0건"]
    for day_num in range(1, last_day + 1):
        # [핵심] 텍스트 대신 엑셀 수식을 넣습니다.
        date_formula = f'=DATE($B$1, $A$1, {day_num})'
        headers.append(date_formula) # E열, G열...
        headers.append("")           # F열, H열... (내용 들어갈 자리)

    # 3. 데이터 행 생성
    final_rows = []
    for num in all_nums:
        name = master_roster.get(num, "")
        row = [num, name, "", ""]
        
        for day_num in range(1, last_day + 1):
            content = ""
            if day_num in df_wide.columns and num in df_wide.index:
                val = df_wide.loc[num, day_num]
                content = str(val).strip() if pd.notna(val) else ""
            
            has_data = len(content) > 0
            row.append(has_data) # 체크박스 값 (TRUE/FALSE)
            row.append(content)  # 텍스트 값
            
        final_rows.append(row)

    return headers, final_rows

# ==========================================
# 5. 업로드 & 서식 적용 (Batch Update)
# ==========================================
def upload_and_format(ws, month, headers, data_rows):
    ws.clear()
    
    # 1. A1, B1 세팅 (값 & 수식)
    # A1: 월 (숫자)
    # B1: 연도 계산 수식 (선생님 요청)
    year_formula = "=IF(A1>2, '기본정보'!E1, '기본정보'!E1+1)"
    
    # 2. 데이터 업로드 (USER_ENTERED 모드로 해야 수식이 적용됨)
    # 1행: [월, 연도수식]
    # 2행: 헤더 (날짜 수식들)
    # 3행~: 데이터
    
    # A1, B1 먼저 업데이트
    ws.update(range_name='A1', values=[[month, year_formula]], value_input_option='USER_ENTERED')
    
    # 헤더와 데이터 한 번에 업데이트
    all_values = [headers] + data_rows
    ws.update(range_name='A2', values=all_values, value_input_option='USER_ENTERED')
    
    # 3. 서식 적용 (Batch Request)
    requests = []
    sheet_id = ws.id
    total_rows = len(data_rows)
    total_cols = len(headers)

    # (1) A1: 숫자 포맷, B1: 숫자 포맷 (연도)
    requests.append({
        "repeatCell": {
            "range": {"sheetId": sheet_id, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 2},
            "cell": {
                "userEnteredFormat": {
                    "horizontalAlignment": "CENTER",
                    "textFormat": {"fontSize": 14, "bold": True},
                    "numberFormat": {"type": "NUMBER", "pattern": "0"} # 숫자형 강제
                }
            },
            "fields": "userEnteredFormat"
        }
    })

    # (2) 날짜 헤더 (2행, E열부터) 포맷 설정: "3/1" 형태 ("M/d")
    # 2칸씩 건너뛰며 적용
    for col_idx in range(4, total_cols, 2):
        # 헤더 셀 (날짜 수식 있는 곳)
        requests.append({
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id, 
                    "startRowIndex": 1, "endRowIndex": 2,  # 2행
                    "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {"type": "DATE", "pattern": "M/d"}, # 날짜 서식
                        "horizontalAlignment": "CENTER",
                        "textFormat": {"bold": True},
                        "backgroundColor": {"red": 0.95, "green": 0.95, "blue": 0.95}
                    }
                },
                "fields": "userEnteredFormat"
            }
        })
        
        # (3) 체크박스 생성 (3행 ~ 끝)
        requests.append({
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 2, "endRowIndex": total_rows + 2,
                    "startColumnIndex": col_idx, "endColumnIndex": col_idx + 1
                },
                "rule": {"condition": {"type": "BOOLEAN"}, "showCustomUi": True}
            }
        })
        
        # (4) 열 너비 (체크박스=30, 텍스트=120)
        requests.append({
            "updateDimensionProperties": {
                "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": col_idx, "endIndex": col_idx + 1},
                "properties": {"pixelSize": 30}, "fields": "pixelSize"
            }
        })
        if col_idx + 1 < total_cols:
            requests.append({
                "updateDimensionProperties": {
                    "range": {"sheetId": sheet_id, "dimension": "COLUMNS", "startIndex": col_idx + 1, "endIndex": col_idx + 2},
                    "properties": {"pixelSize": 120}, "fields": "pixelSize"
                }
            })

    # (5) 틀 고정 (2행, 4열까지) - 스크롤 편의성
    requests.append({
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": 2, "frozenColumnCount": 4}
            },
            "fields": "gridProperties(frozenRowCount, frozenColumnCount)"
        }
    })

    if requests:
        ws.spreadsheet.batch_update({"requests": requests})

# ==========================================
# 6. 메인 실행
# ==========================================
# =========================================================
# [New] 외부 호출 가능한 실행 함수
# =========================================================
def run_restore(target_months=None):
    if target_months is None: target_months = ACADEMIC_MONTHS
    print(f"=== 구글 시트 복원 시작 (대상: {target_months}) ===")
    
    client = get_client()
    if not client: return
    try: doc = client.open_by_url(GOOGLE_SHEET_URL)
    except: print("❌ 접속 실패"); return

    roster = get_master_roster()
    if not roster: print("❌ 명단 실패"); return

    stats = {num: {'이름': name, '결석':0, '지각':0, '조퇴':0, '결과':0} for num, name in roster.items()}

    for month in target_months:
        current_year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        pattern = os.path.join(INPUT_DIR, f"{month:02d}월*월별출결현황.html")
        files = glob.glob(pattern)
        
        if not files:
            print(f"   [Skip] {month}월 HTML 파일 없음")
            continue
            
        print(f"   📂 [{month}월] 데이터 처리 및 업로드...")
        df_long = parse_html_to_df(files[0])
        
        if df_long is not None and not df_long.empty:
            for _, row in df_long.iterrows():
                if row['num'] in stats:
                    t = row['type']
                    if "결석" in t: stats[row['num']]['결석'] += 1
                    elif "지각" in t: stats[row['num']]['지각'] += 1
                    elif "조퇴" in t: stats[row['num']]['조퇴'] += 1
                    elif "결과" in t: stats[row['num']]['결과'] += 1

        headers, data_rows = prepare_smart_data(df_long, current_year, month, roster)
        sheet_name = f"{month}월"
        try:
            try: ws = doc.worksheet(sheet_name)
            except: ws = doc.add_worksheet(title=sheet_name, rows=100, cols=100)
            upload_and_format(ws, month, headers, data_rows)
            print(f"      ✅ 완료")
            time.sleep(2)
        except Exception as e:
            print(f"      ❌ 오류: {e}")

    # 합계는 항상 갱신 (복원 작업 시)
    try:
        print("   📊 [합계] 시트 갱신 중...")
        s_head = ['번호', '이름', '결석', '지각', '조퇴', '결과']
        s_rows = [[n, stats[n]['이름'], stats[n]['결석'], stats[n]['지각'], stats[n]['조퇴'], stats[n]['결과']] for n in sorted(stats)]
        try: ws_s = doc.worksheet("합계")
        except: ws_s = doc.add_worksheet("합계", 100, 20)
        ws_s.clear()
        ws_s.update(range_name='A1', values=[s_head] + s_rows)
        print("      ✅ 완료")
    except: pass

if __name__ == "__main__":
    run_restore()