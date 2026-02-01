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
    # CONFIG_FILE_PATH,  <-- 제거됨 (Config Manager가 처리)
    ROOT_DIR,
    ensure_directories
)

# ✅ [Refactor] Utils 모듈 임포트 (추가됨)
try:
    from src.utils.date_calculator import DateCalculator
except ImportError:
    print("⚠️ [DataLoader] DateCalculator를 임포트할 수 없습니다. 경로를 확인하세요.")

# ✅ [New] 설정 관리자 연동 (여기서 모든 설정을 가져옴)
try:
    from src.services.config_manager import GLOBAL_CONFIG
except ImportError:
    # config_manager가 없을 때를 대비한 폴백(Fallback) - 개발 중 에러 방지
    GLOBAL_CONFIG = {"target_year": 2025, "holidays": []}
    print("⚠️ [DataLoader] config_manager를 찾을 수 없어 기본값을 사용합니다.")

# 초기 폴더 생성
ensure_directories()

# =============================================================================
# 설정 및 인증 (Config Manager 사용으로 대폭 간소화)
# =============================================================================

# 기존 load_config 함수 제거됨

GOOGLE_SHEET_URL = GLOBAL_CONFIG.get("spreadsheet_url", "https://docs.google.com/spreadsheets/d/1Jlyok_qOggzj-KeC1O8xqa6OPyRm8KDw9P7ojNXc4UE/edit")
TARGET_YEAR = GLOBAL_CONFIG.get("target_year", 2025)
ACADEMIC_MONTHS = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2]

# [싱글톤] 구글 연결 객체 재사용
_SHEET_CLIENT = None
_DOC_INSTANCE = None

def get_holidays():
    """
    Config Manager가 이미 휴일 데이터를 파싱해서 리스트로 만들어 두었음.
    날짜 문자열을 date 객체로 변환만 하면 됨.
    """
    raw_holidays = GLOBAL_CONFIG.get("holidays", [])
    date_objs = []
    
    for d_str in raw_holidays:
        try:
            date_objs.append(datetime.datetime.strptime(d_str, "%Y-%m-%d").date())
        except ValueError:
            pass
            
    return date_objs

# 전역 변수에 할당
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
            
            if col_idx + 1 < len(row):
                val_text = str(row[col_idx + 1]).strip() 
            else: val_text = ""
            
            if val_text:
                final_val = val_text
            elif val_check.upper() == "TRUE":
                final_val = "결석" 
            elif val_check and val_check.upper() != "FALSE":
                final_val = val_check

            if not final_val or final_val == "-" or final_val == "0" or final_val.upper() == "FALSE": 
                continue

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

# [Refactor] Phase 3: 레거시 로직 제거 및 Utils 위임
# 기존 check_gap_is_holiday 함수는 DateCalculator 내부 로직으로 대체되었으므로 삭제했습니다.

def group_consecutive_events(events):
    """
    [Wrapper] 기존 로직을 제거하고, 모든 권한을 src.utils.DateCalculator에게 위임합니다.
    이제 이 함수를 호출하면 자동으로 휴일 건너뛰기 및 실제 수업일수(real_days)가 계산됩니다.
    """
    if not events: return []

    # 1. 계산기 인스턴스 생성 (ROOT_DIR 전달)
    # src.paths의 ROOT_DIR은 Path 객체일 수 있으므로 str()로 변환하여 안전하게 전달
    date_calc = DateCalculator(str(ROOT_DIR))
    
    # 2. 작업 위임 (Toss)
    # DateCalculator가 정렬, 휴일 체크, 그룹화, real_days 계산까지 모두 수행함
    return date_calc.group_consecutive_events(events)