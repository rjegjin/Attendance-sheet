import os
import datetime
from jinja2 import Environment, FileSystemLoader
from src.services.data_loader import (
    load_all_events, 
    get_master_roster, 
    ACADEMIC_MONTHS, 
    check_gap_is_holiday  # [필수] 연속성 판단을 위해 가져옴
)
from src.paths import REPORTS_DIR, SRC_DIR
import src.components.universal_notification as bot

OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "stats")
TEMPLATE_DIR = os.path.join(str(SRC_DIR), "templates")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.exists(TEMPLATE_DIR): os.makedirs(TEMPLATE_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# [설정] 장기결석 누적 임계값
THRESHOLD_L1 = 30
THRESHOLD_L2 = 40
THRESHOLD_L3 = 45
THRESHOLD_L4 = 50

# [설정] 연속 결석 위험 기준 (주말/휴일 포함)
LIMIT_CONSECUTIVE = 10 

def get_status_info(count):
    if count >= THRESHOLD_L4: return "🛑 3차 독촉 (정원외)", "bg-black", 100
    elif count >= THRESHOLD_L3: return "🚨 내교통지서", "bg-red", 90
    elif count >= THRESHOLD_L2: return "🟧 2차 독촉", "bg-orange", 80
    elif count >= THRESHOLD_L1: return "🟨 1차 독촉", "bg-yellow", 60
    else: return "정상", "bg-green", (count / THRESHOLD_L4) * 100

def calculate_max_consecutive(dates):
    """
    결석 날짜 리스트를 받아, 주말/공휴일을 포함한 최대 연속 결석 일수를 계산합니다.
    """
    if not dates: return 0, []
    
    dates = sorted(list(set(dates)))
    max_streak_days = 1
    current_streak_days = 1
    start_date = dates[0]
    curr_end = dates[0]
    long_periods = [] 
    
    for i in range(1, len(dates)):
        nxt = dates[i]
        delta = (nxt - curr_end).days
        
        # 1. 바로 다음 날이거나 2. 사이가 모두 휴일이면 연속으로 간주
        is_connected = (delta == 1) or (delta > 1 and check_gap_is_holiday(curr_end, nxt))
        
        if is_connected:
            curr_end = nxt
            current_streak_days = (curr_end - start_date).days + 1
        else:
            if current_streak_days >= LIMIT_CONSECUTIVE:
                long_periods.append((start_date, curr_end, current_streak_days))
            max_streak_days = max(max_streak_days, current_streak_days)
            start_date = nxt
            curr_end = nxt
            current_streak_days = 1
            
    if current_streak_days >= LIMIT_CONSECUTIVE:
        long_periods.append((start_date, curr_end, current_streak_days))
    max_streak_days = max(max_streak_days, current_streak_days)
    
    return max_streak_days, long_periods

def analyze_long_term_absence(roster):
    # [1] 명렬표 기준 초기화 (날짜 객체를 담을 raw_dates 추가)
    stats = {num: {'name': name, 'count': 0, 'details': [], 'raw_dates': []} for num, name in roster.items()}
    
    print("   📉 [분석] 장기결석 위험군 스캔 중...")
    
    for month in ACADEMIC_MONTHS:
        events = load_all_events(None, month, roster)
        for e in events:
            # 명렬표에 없는 번호 무시
            if e['num'] not in stats: continue

            # 결석(질병, 미인정, 기타)만 카운트
            if "결석" in e['raw_type'] and "인정" not in e['raw_type']:
                stats[e['num']]['count'] += 1
                stats[e['num']]['details'].append(f"{e['date'].strftime('%m.%d')}({e['raw_type'][:2]})")
                stats[e['num']]['raw_dates'].append(e['date'])

    rows = []
    alerts = []
    
    # [3] 결석 일수 많은 순 정렬
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)
    
    color_map = {
        "bg-green":"#28a745", "bg-yellow":"#ffc107", 
        "bg-orange":"#fd7e14", "bg-red":"#dc3545", "bg-black":"#212529"
    }

    for num, data in sorted_stats:
        count = data['count']
        if count == 0: continue 
        
        # 기본 상태 메시지
        msg, color_class, pct = get_status_info(count)
        
        # [New] 연속 결석 분석
        max_cons, long_periods = calculate_max_consecutive(data['raw_dates'])
        is_long_streak = (max_cons >= LIMIT_CONSECUTIVE)
        
        # 알림 생성 (누적 or 연속)
        if count >= THRESHOLD_L1:
            alerts.append(f"{data['name']}(누적 {count}일): {msg}")
            
        if is_long_streak:
            period_str = ", ".join([f"{s.strftime('%m.%d')}~{e.strftime('%m.%d')}" for s, e, d in long_periods])
            alerts.append(f"🚨 {data['name']}: 연속 {max_cons}일 결석! ({period_str})")
            
            # 리포트 표시용 메시지 수정
            msg += f" / 🚨연속 {max_cons}일"
            # 연속 결석이 있으면 색상을 경고색(오렌지 이상)으로 강제 상향
            if color_class == "bg-green": 
                color_class = "bg-orange"
        
        rows.append({
            'num': num,
            'name': data['name'],
            'count': count,
            'msg': msg,
            'color_class': color_class,
            'bar_color': color_map[color_class],
            'pct': min(pct, 100),
            'details': ", ".join(data['details'])
        })
        
    return rows, alerts

def run_long_term_absence():
    roster = get_master_roster()
    rows, alerts = analyze_long_term_absence(roster)
    
    template = env.get_template("stats_longterm.html")
    html = template.render(
        limits={'l1': THRESHOLD_L1, 'l2': THRESHOLD_L2, 'l3': THRESHOLD_L3, 'l4': THRESHOLD_L4},
        rows=rows
    )
    
    out_file = os.path.join(OUTPUT_DIR, "장기결석_경고리포트.html")
    with open(out_file, "w", encoding="utf-8") as f: f.write(html)
    print(f"   ✅ 리포트 생성 완료: {out_file}")

    if alerts:
        bot.send_alert(f"📉 [장기결석/연속결석 경고]\n" + "\n".join(alerts))
        print(f"   🔔 알림 전송 완료 ({len(alerts)}건)")

if __name__ == "__main__":
    run_long_term_absence()
