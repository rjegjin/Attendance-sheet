import os
import json
import glob
from jinja2 import Environment, FileSystemLoader
import src.services.data_loader as data_loader

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_PATH)) 
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports", "checklist")
STATUS_DIR = os.path.join(OUTPUT_DIR, "status")

# 템플릿 폴더 경로 설정
TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "src", "templates")
if not os.path.exists(TEMPLATE_DIR): os.makedirs(TEMPLATE_DIR, exist_ok=True)

# Jinja2 환경 설정
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# =========================================================
# [Master-Detail] 데이터 관리 로직
# =========================================================
def get_status_file_path(month, year):
    if not os.path.exists(STATUS_DIR): os.makedirs(STATUS_DIR, exist_ok=True)
    return os.path.join(STATUS_DIR, f"checklist_{year}_{month:02d}.json")

def get_total_file_path(year):
    if not os.path.exists(STATUS_DIR): os.makedirs(STATUS_DIR, exist_ok=True)
    return os.path.join(STATUS_DIR, f"checklist_{year}_TOTAL.json")

def load_status(month, year):
    path = get_status_file_path(month, year)
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_status(month, status_data, year):
    month_path = get_status_file_path(month, year)
    with open(month_path, "w", encoding="utf-8") as f:
        json.dump(status_data, f, ensure_ascii=False, indent=4)
    update_total_status()

def update_total_status():
    target_year = data_loader.TARGET_YEAR 
    total_data = {}
    
    pattern_sem1 = os.path.join(STATUS_DIR, f"checklist_{target_year}_??.json")
    files_sem1 = glob.glob(pattern_sem1)
    
    pattern_sem2 = os.path.join(STATUS_DIR, f"checklist_{target_year + 1}_0[1-2].json")
    files_sem2 = glob.glob(pattern_sem2)
    
    all_files = [f for f in files_sem1 + files_sem2 if "TOTAL" not in f]
    
    for file_path in all_files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                month_data = json.load(f)
                if isinstance(month_data, dict):
                    total_data.update(month_data)
        except Exception as e:
            print(f"⚠️ 통합 중 파일 읽기 오류: {e}")
            
    total_path = get_total_file_path(target_year)
    with open(total_path, "w", encoding="utf-8") as f:
        json.dump(total_data, f, ensure_ascii=False, indent=4)
    
    print(f"   📊 [DB 통합] {target_year}학년도 전체 데이터 갱신 완료 ({len(all_files)}개 파일)")

# =========================================================
# HTML 생성 로직 (Jinja2 적용)
# =========================================================
def generate_html(grouped_events, month, year, output_path):
    storage_key = f"chk_state_{year}_{month:02d}"
    
    # DB 상태 로드
    current_db_status = load_status(month, year)

    # 템플릿에 넘길 데이터 리스트 가공 (ViewModel 생성)
    rows = []
    for i, e in enumerate(grouped_events):
        # 1. 기간 문자열 생성
        p_str = e['start'].strftime("%m.%d")
        if e['start'] != e['end']: 
            p_str += f" ~ {e['end'].strftime('%m.%d')}"
        
        # 2. 데이터 키 생성 (이름_날짜)
        key_date_str = e['start'].strftime("%m.%d")
        data_key = f"{e['name']}_{key_date_str}"
        
        # 3. 완료 여부 확인
        is_done = current_db_status.get(data_key, False)
        
        rows.append({
            'idx': i + 1,
            'rid': f"r{i}",             # HTML ID용
            'data_key': data_key,       # JS 저장용 키
            'is_done': is_done,         # 완료 상태
            'period_str': p_str,
            'num': e['num'],
            'name': e['name'],
            'type': e['raw_type'],
            'time': e['time'],          # 교시 정보
            'reason': e['reason']
        })

    # Jinja2 템플릿 로드 및 렌더링
    template = env.get_template("checklist_template.html")
    html = template.render(
        year=year,
        month=month,
        month_pad=f"{month:02d}", # 파일명 생성용
        storage_key=storage_key,
        rows=rows
    )
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

def run_checklists(target_months=None):
    if not os.path.exists(STATUS_DIR): os.makedirs(STATUS_DIR, exist_ok=True)
    if target_months is None: target_months = data_loader.ACADEMIC_MONTHS
    
    print(f"=== 증빙서류 체크리스트 생성 (대상: {target_months}) ===")
    roster = data_loader.get_master_roster()
    
    for month in target_months:
        year = data_loader.TARGET_YEAR + 1 if month < 3 else data_loader.TARGET_YEAR
        
        events = data_loader.load_all_events(None, month, roster)
        grouped = data_loader.group_consecutive_events(events)
        
        # [정렬 규칙] 날짜(start) 오름차순 -> 번호(num) 오름차순
        grouped.sort(key=lambda x: (x['start'], x['num']))
        
        out_file = os.path.join(OUTPUT_DIR, f"{month:02d}월_증빙서류_체크리스트.html")
        generate_html(grouped, month, year, out_file)
        print(f"   -> {year}년 {month}월 완료 ({len(grouped)}건)")

# =========================================================
# 외부 호출용 도우미 함수
# =========================================================
def mark_submitted_manually(name, date_str):
    try:
        m, d = map(int, date_str.split('.'))
        year = data_loader.TARGET_YEAR + 1 if m < 3 else data_loader.TARGET_YEAR
        
        key = f"{name}_{m:02d}.{d:02d}"
        current = load_status(m, year)
        current[key] = True
        save_status(m, current, year)
        return True, f"{year}년 {m}월 데이터에 반영되었습니다."
    except Exception as e:
        return False, str(e)

if __name__ == "__main__":
    run_checklists()