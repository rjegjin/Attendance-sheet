import os
import sys

# 프로젝트 루트 경로 설정
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_PATH))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# [Import] 데이터 로더 & 서비스
from src.services.data_loader import load_all_events, get_master_roster, ACADEMIC_MONTHS
from src.paths import REPORTS_DIR
import src.services.universal_notification as bot

# [Import] Utils (DateCalculator & TemplateManager)
try:
    from src.utils.date_calculator import DateCalculator
    from src.utils.template_manager import TemplateManager
    has_utils = True
except ImportError:
    has_utils = False
    print("⚠️ [Warning] Utils 모듈을 찾을 수 없습니다.")

# 경로 및 설정
OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "stats")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)

# [설정] 체험학습 규정 (일수)
LIMITS = {
    'dom_total': 10,       # 국내 연간 총량
    'dom_cons': 5,         # 국내 연속 허용
    'intl_total': 10       # 국외 연간 총량
}

# Utils 인스턴스
date_calc = DateCalculator(PROJECT_ROOT) if has_utils else None
tmpl_mgr = TemplateManager(PROJECT_ROOT) if has_utils else None

# =========================================================
# 분석 로직
# =========================================================

def calculate_max_consecutive(grouped_events):
    """그룹화된 이벤트 리스트에서 최대 연속 일수(수업일수 기준) 계산"""
    max_days = 0
    for g in grouped_events:
        # DateCalculator가 계산해준 'real_days' 사용 (없으면 기간 사용)
        days = g.get('real_days', (g['end'] - g['start']).days + 1)
        if days > max_days:
            max_days = days
    return max_days

def analyze_field_trips(roster):
    """
    학생별 체험학습 데이터 분석
    - 국내/국외 분리
    - 휴일 제외 실제 수업일수 계산 (DateCalculator 활용)
    """
    print("   📊 [분석] 국내/국외 체험학습 데이터 분석 중...")
    
    # 데이터 수집용 구조체 초기화
    raw_data = {num: {'name': name, 'dom': [], 'int': []} for num, name in roster.items()}
    
    # 1. 전체 데이터 로드 및 분류
    for month in ACADEMIC_MONTHS:
        try:
            events = load_all_events(None, month, roster)
        except: continue
            
        for e in events:
            full_text = (e['raw_type'] + str(e.get('reason',''))).replace(" ", "")
            
            # '체험' 또는 '교외' 키워드가 있고, 미인정이 아닌 경우
            if ("체험" in full_text or "교외" in full_text) and not e.get('is_unexcused'):
                num = e['num']
                if num not in raw_data:
                    raw_data[num] = {'name': e['name'], 'dom': [], 'int': []}

                is_intl = any(k in full_text for k in ["국외", "해외", "유학", "출국", "비자"])
                target_list = raw_data[num]['int'] if is_intl else raw_data[num]['dom']
                target_list.append(e)

    # 2. 학생별 통계 산출 (DateCalculator로 그룹화)
    students_data = []
    alerts = []
    
    for num in sorted(raw_data.keys()):
        s_info = raw_data[num]
        name = s_info['name']
        
        # 국내/국외 각각 스마트 그룹화 (휴일 건너뛰기 & 일수 계산)
        # Utils가 없으면 data_loader의 구형 함수 사용 (Fallback)
        if has_utils:
            dom_groups = date_calc.group_consecutive_events(s_info['dom'])
            int_groups = date_calc.group_consecutive_events(s_info['int'])
        else:
            # 여기서는 편의상 빈 리스트 처리 (실제로는 data_loader 사용 가능)
            dom_groups, int_groups = [], []

        # 사용 내역이 없으면 스킵
        if not dom_groups and not int_groups: continue
        
        # 총 사용일수 및 최대 연속일수 계산
        dom_total = sum(g.get('real_days', 1) for g in dom_groups)
        dom_max_cons = calculate_max_consecutive(dom_groups)
        
        int_total = sum(g.get('real_days', 1) for g in int_groups)
        # 국외는 연속 제한이 없다면 계산 생략 가능
        
        # 규정 위반 체크
        is_d_over = dom_total > LIMITS['dom_total']
        is_i_over = int_total > LIMITS['intl_total']
        is_d_cons_over = dom_max_cons > LIMITS['dom_cons']
        
        # 알림 메시지
        if is_d_over: alerts.append(f"{name}: 국내 {dom_total}일 (초과)")
        if is_i_over: alerts.append(f"{name}: 국외 {int_total}일 (초과)")
        if is_d_cons_over: alerts.append(f"{name}: 국내연속 {dom_max_cons}일 (주의)")

        # 뱃지 생성
        badges = []
        if is_d_over: badges.append({'text': f'국내초과({dom_total})', 'color_class': 'bg-red'})
        if is_d_cons_over: badges.append({'text': f'연속주의({dom_max_cons}일)', 'color_class': 'bg-orange'})
        if is_i_over: badges.append({'text': f'국외초과({int_total})', 'color_class': 'bg-red'})
        
        # 스타일 클래스
        card_class = ""
        if dom_groups or int_groups: card_class = "has-data"
        if is_d_cons_over: card_class = "warning"
        if is_d_over or is_i_over: card_class = "violation"

        # 상세 내역 텍스트 생성 (HTML 태그 포함 가능)
        def format_details(groups, limit_cons=None):
            details = []
            for g in groups:
                days = g.get('real_days', 1)
                txt = f"{g['start'].strftime('%m.%d')}~{g['end'].strftime('%m.%d')}({days}일)"
                # 연속일수 초과 시 강조
                if limit_cons and days > limit_cons:
                    txt = f"<b style='color:#fd7e14'>{txt}</b>"
                details.append(txt)
            return " / ".join(details)

        students_data.append({
            'num': num,
            'name': name,
            'card_class': card_class,
            'badges': badges,
            'dom': {
                'total': dom_total,
                'pct': min((dom_total / LIMITS['dom_total']) * 100, 100),
                'color': "#28a745" if not is_d_over else "#dc3545",
                'details': format_details(dom_groups, LIMITS['dom_cons'])
            },
            'intl': {
                'total': int_total,
                'pct': min((int_total / LIMITS['intl_total']) * 100, 100) if LIMITS['intl_total'] > 0 else 0,
                'color': "#17a2b8" if not is_i_over else "#dc3545",
                'details': format_details(int_groups)
            }
        })
        
    return students_data, alerts

def run_fieldtrip_stats():
    print(f"=== 교외체험학습 연간 통계 (Jinja2 & DateCalculator) ===")
    
    roster = get_master_roster()
    students_data, alerts = analyze_field_trips(roster)
    
    # 템플릿 렌더링
    out_file = os.path.join(OUTPUT_DIR, "연간_체크_체험학습통계.html")
    context = {
        'limits': LIMITS,
        'students': students_data
    }
    
    if tmpl_mgr and tmpl_mgr.render_and_save("stats_fieldtrip.html", context, out_file):
        print(f"   ✅ 리포트 생성 완료: {out_file}")
    else:
        print("❌ 템플릿 렌더링 실패")

    # 알림 발송
    if alerts:
        bot.send_alert(f"🚌 [체험학습 주의/초과 알림]\n" + "\n".join(alerts))
        print(f"   🔔 알림 전송 완료 ({len(alerts)}건)")

if __name__ == "__main__":
    run_fieldtrip_stats()