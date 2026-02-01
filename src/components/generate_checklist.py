import os
import sys

# 프로젝트 루트 경로 설정 (src/components/ 위치 기준)
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_PATH)) # components -> src -> root
sys.path.append(PROJECT_ROOT) 

# [Refactor] Utils 및 서비스 모듈 임포트
from src.utils.date_calculator import DateCalculator
from src.utils.template_manager import TemplateManager
from src.utils.state_manager import StateManager
import src.services.data_loader as data_loader

# 경로 설정
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "reports", "checklist")
STATUS_DIR = os.path.join(OUTPUT_DIR, "status")

# [Refactor] 3대장 도구 초기화
date_calc = DateCalculator(PROJECT_ROOT)
tmpl_mgr = TemplateManager(PROJECT_ROOT)
state_mgr = StateManager(STATUS_DIR)

def generate_html(grouped_events, month, year, output_path):
    # 1. 체크 상태 로드 (StateManager 활용)
    status_filename = f"checklist_{year}_{month:02d}.json"
    current_db_status = state_mgr.load_json(status_filename, default={})

    rows = []
    for i, e in enumerate(grouped_events):
        # 2. 기간 문자열 생성
        p_str = e['start'].strftime("%m.%d")
        if e['start'] != e['end']: 
            p_str += f" ~ {e['end'].strftime('%m.%d')}"
        
        # 3. [New] 실제 수업일수 표시 (DateCalculator가 계산해준 real_days 활용)
        real_days = e.get('real_days', 1)
        if real_days > 1:
            p_str += f" <span style='color:#2563eb; font-size:0.9em; font-weight:bold;'>({real_days}일)</span>"
        
        # 4. 데이터 키 생성 (저장용)
        key_date_str = e['start'].strftime("%m.%d")
        data_key = f"{e['name']}_{key_date_str}"
        
        rows.append({
            'idx': i + 1,
            'rid': f"r{i}",
            'data_key': data_key,
            'is_done': current_db_status.get(data_key, False),
            'period_str': p_str,
            'num': e['num'],
            'name': e['name'],
            'type': e['raw_type'],
            'time': e['time'],
            'reason': e['reason']
        })

    # 5. HTML 생성 및 저장 (TemplateManager 활용)
    context = {
        'year': year,
        'month': month,
        'month_pad': f"{month:02d}",
        'storage_key': f"chk_state_{year}_{month:02d}",
        'rows': rows
    }
    
    if tmpl_mgr.render_and_save("checklist_template.html", context, output_path):
        pass 
    else:
        print(f"❌ HTML 생성 실패: {output_path}")

def filter_checklist_events(events):
    """
    체크리스트 표시 대상 필터링
    1. 미인정(무단) 제외
    2. 질병지각/조퇴/결과 제외 (질병결석은 포함)
    """
    targets = []
    exclude_keywords = ["질병지각", "질병조퇴", "질병결과"]

    for e in events:
        if e.get('is_unexcused', False):
            continue
            
        raw_type = e.get('raw_type', '')
        if any(keyword in raw_type for keyword in exclude_keywords):
            continue
            
        targets.append(e)
    return targets

def run_checklists(target_months=None):
    if target_months is None: target_months = data_loader.ACADEMIC_MONTHS
    
    print(f"=== 증빙서류 체크리스트 생성 (Phase 2 Refactored) ===")
    roster = data_loader.get_master_roster()
    
    for month in target_months:
        year = data_loader.TARGET_YEAR + 1 if month < 3 else data_loader.TARGET_YEAR
        
        # 1. 데이터 로드 (Raw Data: 'date' 키 가짐)
        all_events = data_loader.load_all_events(None, month, roster)
        
        # 2. 필터링
        filtered_events = filter_checklist_events(all_events)
        
        # 3. [핵심] 스마트 그룹화 (DateCalculator 활용)
        # Raw Data가 들어와도 내부에서 'start/end'로 변환 후 처리함
        grouped = date_calc.group_consecutive_events(filtered_events)
        
        # 정렬: 날짜순 -> 번호순
        grouped.sort(key=lambda x: (x['start'], x['num']))
        
        # 파일 생성
        out_file = os.path.join(OUTPUT_DIR, f"{month:02d}월_증빙서류_체크리스트.html")
        generate_html(grouped, month, year, out_file)
        
        print(f"   -> {year}년 {month}월 완료 ({len(grouped)}건)")

if __name__ == "__main__":
    run_checklists()