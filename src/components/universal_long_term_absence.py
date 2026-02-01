import os
import sys
import datetime
import traceback

# 프로젝트 루트 경로 설정
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_PATH))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# [Import] 데이터 로더 및 서비스
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

# 경로 설정
OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "stats")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)

# [설정] 장기결석 기준값
LIMITS = {
    'l1': 30, 'l2': 40, 'l3': 45, 'l4': 50, # 누적일수 단계
    'consecutive': 7                        # 연속결석 기준
}

# Utils 인스턴스
date_calc = DateCalculator(PROJECT_ROOT) if has_utils else None
tmpl_mgr = TemplateManager(PROJECT_ROOT) if has_utils else None

# =========================================================
# 로직 함수 (Utils 활용)
# =========================================================

def check_is_connected(start, end):
    """두 날짜 사이가 모두 휴일/주말이라서 연속된 것으로 볼 수 있는지 확인"""
    delta = (end - start).days
    if delta == 1: return True
    if delta <= 0: return False

    if date_calc:
        current = start + datetime.timedelta(days=1)
        while current < end:
            if date_calc.is_school_day(current): return False
            current += datetime.timedelta(days=1)
        return True
    else:
        gap_days = [start + datetime.timedelta(days=x) for x in range(1, delta)]
        return all(d.weekday() in [5, 6] for d in gap_days)

def calculate_max_consecutive(dates):
    """최대 연속 결석일수(Streak)와 구간 정보 계산"""
    if not dates: return 0, []
    dates = sorted(list(set(dates)))
    long_periods = []
    
    streak_start = dates[0]
    streak_end = dates[0]
    streak_count = 1
    max_streak = 1
    
    for i in range(1, len(dates)):
        curr = dates[i-1]
        nxt = dates[i]
        
        if check_is_connected(curr, nxt):
            streak_end = nxt
            streak_count += 1
        else:
            if streak_count >= LIMITS['consecutive']:
                long_periods.append((streak_start, streak_end, streak_count))
            max_streak = max(max_streak, streak_count)
            streak_start = nxt
            streak_end = nxt
            streak_count = 1
            
    if streak_count >= LIMITS['consecutive']:
        long_periods.append((streak_start, streak_end, streak_count))
    max_streak = max(max_streak, streak_count)
    
    return max_streak, long_periods

def get_status_info(count):
    """상태 메시지 및 CSS 클래스 반환"""
    if count >= LIMITS['l4']: return "🛑 3차 독촉 (정원외)", "bg-black", 100
    elif count >= LIMITS['l3']: return "🚨 내교통지서", "bg-red", 90
    elif count >= LIMITS['l2']: return "🟧 2차 독촉", "bg-orange", 80
    elif count >= LIMITS['l1']: return "🟨 1차 독촉", "bg-yellow", 60
    else: return "정상", "bg-green", (count / LIMITS['l4']) * 100

def analyze_long_term_absence(roster):
    """데이터 분석 및 통계 생성"""
    stats = {num: {'name': name, 'count': 0, 'details': [], 'raw_dates': []} for num, name in roster.items()}
    print("   📉 [분석] 장기결석 위험군 스캔 중...")
    
    for month in ACADEMIC_MONTHS:
        try:
            events = load_all_events(None, month, roster)
        except Exception: continue
            
        for e in events:
            if e['num'] not in stats: continue
            raw_type = e.get('raw_type', '')
            
            # [미인정 포함 로직] 결석 키워드 포함 & (인정결석이 아니거나, 미인정이면 포함)
            if "결석" in raw_type:
                is_pure_authorized = ("인정" in raw_type) and ("미인정" not in raw_type)
                if not is_pure_authorized:
                    stats[e['num']]['count'] += 1
                    stats[e['num']]['details'].append(f"{e['date'].strftime('%m.%d')}({raw_type[:2]})")
                    stats[e['num']]['raw_dates'].append(e['date'])
    return stats

def generate_report(stats):
    """데이터 가공 및 템플릿 렌더링"""
    WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
    color_map = {"bg-green":"#28a745", "bg-yellow":"#ffc107", "bg-orange":"#fd7e14", "bg-red":"#dc3545", "bg-black":"#212529"}
    
    rows = []
    alerts = []
    
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    for num, data in sorted_stats:
        count = data['count']
        max_cons, raw_periods = calculate_max_consecutive(data['raw_dates'])
        is_long_streak = (max_cons >= LIMITS['consecutive'])
        
        if count == 0 and not is_long_streak: continue
        
        msg, color_class, pct = get_status_info(count)
        
        # 알림 수집
        if count >= LIMITS['l1']:
            alerts.append(f"{data['name']}(누적 {count}일): {msg}")
            
        # 연속 결석 구간 포맷팅
        formatted_periods = []
        if is_long_streak:
            period_strs = []
            for s, e, d in raw_periods:
                s_str = f"{s.strftime('%m.%d')}({WEEKDAYS[s.weekday()]})"
                e_str = f"{e.strftime('%m.%d')}({WEEKDAYS[e.weekday()]})"
                formatted_periods.append({'start_str': s_str, 'end_str': e_str, 'days': d})
                period_strs.append(f"{s.strftime('%m.%d')}~{e.strftime('%m.%d')}")
            
            alerts.append(f"🚨 {data['name']}: 연속 {max_cons}일 결석! [{', '.join(period_strs)}]")
            msg += f" / 🚨연속 {max_cons}일"
            if color_class == "bg-green": color_class = "bg-orange"

        rows.append({
            'num': num,
            'name': data['name'],
            'count': count,
            'msg': msg,
            'color_class': color_class,
            'bar_color': color_map.get(color_class, "#28a745"),
            'pct': min(pct, 100),
            'details': ", ".join(data['details']),
            'long_periods': formatted_periods
        })

    # 템플릿 렌더링 (TemplateManager 활용)
    context = {'limits': LIMITS, 'rows': rows}
    out_file = os.path.join(OUTPUT_DIR, "장기결석_경고리포트.html")
    
    if tmpl_mgr and tmpl_mgr.render_and_save("stats_longterm.html", context, out_file):
        print(f"   ✅ 리포트 생성 완료: {out_file}")
    else:
        print("❌ 템플릿 렌더링 실패")

    if alerts:
        bot.send_alert(f"📉 [장기결석/연속결석 경고]\n" + "\n".join(alerts))
        print(f"   🔔 알림 전송 완료 ({len(alerts)}건)")

def run_long_term_absence():
    try:
        roster = get_master_roster()
        stats = analyze_long_term_absence(roster)
        generate_report(stats)
    except Exception as e:
        print(f"❌ 장기결석 리포트 생성 중 오류 발생: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    run_long_term_absence()