import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import datetime
import os
import time
import pickle
import json
import re
from pathlib import Path

# [나침반] 경로 설정
from src.paths import (
    SERVICE_KEY_PATH, 
    CACHE_DIR, 
    CONFIG_FILE_PATH,
    ROOT_DIR,
    ensure_directories
)

# 초기 폴더 생성
ensure_directories()

# =============================================================================
# 설정 및 인증
# =============================================================================
def load_config():
    if not CONFIG_FILE_PATH.exists():
        return {"target_year": 2025, "holidays": []}
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"target_year": 2025, "holidays": []}

_CONFIG = load_config()
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1Jlyok_qOggzj-KeC1O8xqa6OPyRm8KDw9P7ojNXc4UE/edit"
TARGET_YEAR = _CONFIG.get("target_year", 2025)
ACADEMIC_MONTHS = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2]

# [싱글톤] 구글 연결 객체 재사용
_SHEET_CLIENT = None
_DOC_INSTANCE = None

def get_holidays():
    config_holidays = _CONFIG.get("holidays", [])
    if config_holidays:
        lst = []
        for d in config_holidays:
            try: lst.append(datetime.datetime.strptime(d, "%Y-%m-%d").date())
            except: pass
        return lst
    
    holiday_file = ROOT_DIR / f"holidays_{TARGET_YEAR}.json"
    if holiday_file.exists():
        try:
            with open(holiday_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                lst = []
                for d_str in data.keys():
                    try: lst.append(datetime.datetime.strptime(d_str, "%Y-%m-%d").date())
                    except: pass
                return lst
        except: pass
    return []

HOLIDAYS_KR = get_holidays()

def get_google_client():
    global _SHEET_CLIENT
    if _SHEET_CLIENT: return _SHEET_CLIENT

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    key_path = str(SERVICE_KEY_PATH)
    
    if os.path.exists(key_path):
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
            client = gspread.authorize(creds)
            _SHEET_CLIENT = client
            return client
        except Exception as e:
            print(f"❌ 인증 실패: {e}")
            raise e
    else:
        print(f"❌ 인증 파일 없음: {key_path}")
        return None

def get_sheet_instance():
    global _DOC_INSTANCE
    if _DOC_INSTANCE: return _DOC_INSTANCE

    client = get_google_client()
    if client:
        try:
            _DOC_INSTANCE = client.open_by_url(GOOGLE_SHEET_URL)
            return _DOC_INSTANCE
        except Exception as e:
            print(f"❌ 시트 열기 실패: {e}")
            return None
    return None

# =============================================================================
# 캐시 관리
# =============================================================================
def get_cache_path(key):
    return os.path.join(str(CACHE_DIR), f"{key}.pkl")

def save_to_cache(key, data):
    try:
        if not CACHE_DIR.exists(): CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(get_cache_path(key), 'wb') as f:
            pickle.dump({'timestamp': time.time(), 'data': data}, f)
    except: pass

def load_from_cache(key, ttl=3600):
    path = get_cache_path(key)
    if os.path.exists(path):
        try:
            with open(path, 'rb') as f:
                cached = pickle.load(f)
            if time.time() - cached['timestamp'] < ttl:
                return cached['data']
        except: pass
    return None

# =============================================================================
# 1. 명단 확보 (A열=번호, B열=이름 고정)
# =============================================================================
def get_master_roster(force_update=False):
    if not force_update:
        cached = load_from_cache("master_roster", ttl=86400 * 7)
        if cached is not None: return cached

    print("☁️ [Google] 학생 명단 다운로드 중... (A열:번호/B열:이름)")
    try:
        doc = get_sheet_instance()
        if not doc: return {}

        sheet = None
        for title in ['명렬표', '명단', '기본정보', '학생명단']:
            try: sheet = doc.worksheet(title); break
            except: continue
            
        if not sheet: 
            # 없으면 기본정보 탭 시도
            try: sheet = doc.worksheet('기본정보'); 
            except: 
                print("❌ 명렬표 시트를 찾을 수 없습니다.")
                return {}

        rows = sheet.get_all_values()
        roster = {}
        
        for row in rows:
            if len(row) < 2: continue
            
            num_val = str(row[0]).strip()
            name_val = str(row[1]).strip()
            
            if not num_val.isdigit(): continue
            num = int(num_val)
            
            if num <= 0 or num >= 100: continue
            if not name_val or "이름" in name_val or "성명" in name_val: continue

            roster[num] = name_val

        roster = dict(sorted(roster.items()))
        save_to_cache("master_roster", roster)
        return roster
    except Exception as e:
        print(f"❌ 명렬표 로드 실패: {e}")
        return {}

# =============================================================================
# [핵심 엔진] 데이터 파싱 및 캐시 저장
# =============================================================================
def _parse_and_save(target_month, all_values, roster):
    cache_key = f"events_{target_month}"
    
    if not all_values or len(all_values) < 2:
        save_to_cache(cache_key, [])
        return []

    # 1. 헤더 분석
    header_row_idx = 0
    header = []
    col_idx_num = -1  
    col_idx_name = -1 

    for i, row in enumerate(all_values[:10]): 
        row_str = str(row)
        if "번호" in row_str and ("이름" in row_str or "성명" in row_str):
            header_row_idx = i
            header = row
            for c_idx, cell_val in enumerate(row):
                cell_clean = str(cell_val).replace(" ", "")
                if "번호" in cell_clean and "핸드폰" not in cell_clean: 
                    col_idx_num = c_idx
                elif "이름" in cell_clean or "성명" in cell_clean: 
                    col_idx_name = c_idx
            break
    
    if col_idx_num == -1 or col_idx_name == -1:
        print(f"   ⚠️ {target_month}월: 번호/이름 열을 찾을 수 없어 건너뜁니다.")
        save_to_cache(cache_key, [])
        return []

    # 2. 날짜 매핑
    date_map = {}
    year = TARGET_YEAR + 1 if target_month < 3 else TARGET_YEAR
    
    for idx, cell in enumerate(header):
        cell_str = str(cell).strip()
        if re.search(r'\d+[./-]\d+', cell_str):
            try:
                clean_date = re.sub(r'[./-]', '/', cell_str)
                parts = [int(p) for p in clean_date.split('/') if p.isdigit()]
                
                m, d = 0, 0
                if len(parts) >= 2:
                    if parts[0] == target_month: m, d = parts[0], parts[1]
                    elif len(parts) > 1 and parts[-2] == target_month: m, d = parts[-2], parts[-1]
                    if m == target_month:
                        date_map[idx] = datetime.date(year, m, d)
            except: pass
    
    events = []
    
    for row in all_values[header_row_idx + 1:]:
        if not row or len(row) < 2: continue
        
        try:
            if len(row) <= col_idx_num: continue
            num_str = str(row[col_idx_num]).strip()
            if not num_str.isdigit(): continue
            num = int(num_str)
            
            name = ""
            if len(row) > col_idx_name:
                name = str(row[col_idx_name]).strip()
            
            if not name and (roster and num in roster):
                name = roster[num]
            if not name: name = "Unknown"

        except: continue

        for col_idx, date_obj in date_map.items():
            if col_idx >= len(row): continue
            
            val_check = str(row[col_idx]).strip() 
            final_val = ""
            
            # [값 보정] 텍스트가 있으면 우선, 없으면 체크박스(TRUE/FALSE) 확인
            val_text = ""
            if col_idx + 1 < len(row):
                val_text = str(row[col_idx + 1]).strip() # 바로 옆 칸(사유) 확인
            
            if val_text:
                final_val = val_text
            elif val_check.upper() == "TRUE":
                final_val = "결석" 
            elif val_check and val_check.upper() != "FALSE":
                final_val = val_check

            if not final_val or final_val == "-" or final_val == "0" or final_val.upper() == "FALSE": 
                continue

            # [상세 정보 파싱] (시간, 사유)
            time_info = ""
            match_time = re.search(r'\((.*?)\)', final_val)
            if match_time: time_info = match_time.group(1)
            
            clean_type = re.sub(r'[\(].*?[\)]', '', final_val).replace('[]', '').strip()
            reason_match = re.search(r'\[(.*?)\]', final_val)
            reason = reason_match.group(1) if reason_match else ""
            if reason: clean_type = clean_type.replace(f"[{reason}]", "").strip()

            events.append({
                'num': num, 'name': name, 'date': date_obj,
                'type': final_val, 'raw_type': clean_type, 
                'time': time_info,
                'is_unexcused': ("미인정" in final_val or "무단" in final_val),
                'reason': reason
            })
            
    save_to_cache(cache_key, events)
    return events


# =============================================================================
# 2. 데이터 다운로드 인터페이스
# =============================================================================
def load_all_events(file_path_ignored, target_month, roster, force_update=False):
    if target_month is None: return []
    cache_key = f"events_{target_month}"
    
    if not force_update:
        cached = load_from_cache(cache_key, ttl=1800)
        if cached is not None: return cached
    
    print(f"☁️ [Google] {target_month}월 데이터 개별 다운로드 중...")
    try:
        doc = get_sheet_instance()
        if not doc: return []

        ws = None
        for cand in [f"{target_month}월", f"{target_month:02d}월"]:
            try: ws = doc.worksheet(cand); break
            except: pass
        
        if not ws:
            save_to_cache(cache_key, []) 
            return []
            
        return _parse_and_save(target_month, ws.get_all_values(), roster)

    except Exception as e:
        print(f"❌ {target_month}월 처리 중 오류: {e}")
        return []

def sync_all_data_batch(roster, target_months=None):
    if not target_months: target_months = ACADEMIC_MONTHS
    
    months_to_fetch = []
    for m in target_months:
        if load_from_cache(f"events_{m}", ttl=1800) is None:
            months_to_fetch.append(m)
            
    if not months_to_fetch:
        print("✨ 모든 데이터가 최신입니다 (캐시 사용).")
        return

    print(f"☁️ [Google] {len(months_to_fetch)}개 시트 일괄 다운로드 중... (Batch)")
    
    try:
        doc = get_sheet_instance()
        if not doc: return

        all_worksheets = doc.worksheets()
        sheet_map = {ws.title: ws for ws in all_worksheets}
        
        ranges = []
        valid_months = []
        
        for m in months_to_fetch:
            target_title = None
            for cand in [f"{m}월", f"{m:02d}월"]:
                if cand in sheet_map:
                    target_title = cand
                    break
            
            if target_title:
                # 🚨 [범위 확장] AZ(52열) -> ZZ(702열)로 변경하여 짤림 방지
                ranges.append(f"'{target_title}'!A1:ZZ2000")
                valid_months.append(m)
            else:
                save_to_cache(f"events_{m}", [])
        
        if not ranges: return

        results = doc.values_batch_get(ranges)
        
        if 'valueRanges' in results:
            for i, result in enumerate(results['valueRanges']):
                m = valid_months[i]
                raw_values = result.get('values', [])
                _parse_and_save(m, raw_values, roster)
                print(f"   -> {m}월 처리 완료")
                
    except Exception as e:
        print(f"❌ 일괄 다운로드 중 오류 발생: {e}")

# =============================================================================
# 유틸리티 함수
# =============================================================================
def check_gap_is_holiday(start, end):
    delta = (end - start).days
    gap_days = [start + datetime.timedelta(days=x) for x in range(1, delta)]
    return all((d.weekday() in [5, 6] or d in HOLIDAYS_KR) for d in gap_days)

def group_consecutive_events(events):
    if not events: return []
    events.sort(key=lambda x: (x['num'], x['date']))
    grouped = []
    
    curr = events[0]; curr_start = curr['date']; curr_end = curr['date']
    
    for i in range(1, len(events)):
        nxt = events[i]
        delta = (nxt['date'] - curr_end).days
        
        is_same = (nxt['num'] == curr['num'] and nxt['raw_type'] == curr['raw_type'])
        is_conn = (delta == 1) or (delta > 1 and is_same and check_gap_is_holiday(curr_end, nxt['date']))

        if is_same and is_conn:
            curr_end = nxt['date']
        else:
            grouped.append({**curr, 'start': curr_start, 'end': curr_end})
            curr = nxt; curr_start = nxt['date']; curr_end = nxt['date']
            
    grouped.append({**curr, 'start': curr_start, 'end': curr_end})
    return grouped