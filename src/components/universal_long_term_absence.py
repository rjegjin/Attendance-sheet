import os
import datetime
from jinja2 import Environment, FileSystemLoader

# [Import] 데이터 로더 및 유틸리티
from src.services.data_loader import (
    load_all_events, 
    get_master_roster, 
    ACADEMIC_MONTHS, 
    check_gap_is_holiday  # [필수] 연속성 판단을 위해 가져옴
)
from src.paths import REPORTS_DIR, SRC_DIR

# [Import] 알림 모듈
import src.services.universal_notification as bot

OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "stats")
TEMPLATE_DIR = os.path.join(str(SRC_DIR), "templates")

# 안전장치: 폴더 생성
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.exists(TEMPLATE_DIR): os.makedirs(TEMPLATE_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# [설정] 장기결석 누적 임계값
THRESHOLD_L1 = 30
THRESHOLD_L2 = 40
THRESHOLD_L3 = 45
THRESHOLD_L4 = 50

# [설정] 연속 결석 위험 기준 (수업일수 기준)
# 예: 주말 포함 10일간 결석했어도, 수업일수가 7일이면 7일로 카운트됩니다.
# 교육청 지침에 따라 7일 또는 10일 등으로 조정하세요.
LIMIT_CONSECUTIVE = 7 

def get_status_info(count):
    """누적 일수에 따른 상태 메시지와 색상을 반환"""
    if count >= THRESHOLD_L4: return "🛑 3차 독촉 (정원외)", "bg-black", 100
    elif count >= THRESHOLD_L3: return "🚨 내교통지서", "bg-red", 90
    elif count >= THRESHOLD_L2: return "🟧 2차 독촉", "bg-orange", 80
    elif count >= THRESHOLD_L1: return "🟨 1차 독촉", "bg-yellow", 60
    else: return "정상", "bg-green", (count / THRESHOLD_L4) * 100

def calculate_max_consecutive(dates):
    """
    결석 날짜 리스트를 받아, 주말/공휴일을 건너뛰며 연결된 '실제 결석 일수'를 계산합니다.
    """
    if not dates: return 0, []
    
    dates = sorted(list(set(dates)))
    long_periods = []
    
    # 연속 구간 추적용 변수
    streak_start = dates[0]
    streak_end = dates[0]
    streak_count = 1  # 실제 결석 횟수 (1일부터 시작)
    
    max_streak = 1
    
    for i in range(1, len(dates)):
        curr = dates[i-1]
        nxt = dates[i]
        delta = (nxt - curr).days
        
        # [연속성 판단] 
        # 1. 바로 다음 날이거나 (delta=1)
        # 2. 날짜 차이가 나더라도 그 사이가 모두 휴일/주말인 경우
        is_connected = (delta == 1) or (delta > 1 and check_gap_is_holiday(curr, nxt))
        
        if is_connected:
            # 연속됨: 끝 날짜 갱신 & 카운트 1 증가 (날짜 차이가 아님!)
            streak_end = nxt
            streak_count += 1
        else:
            # 끊김: 현재까지의 구간 저장 (기준 넘으면)
            if streak_count >= LIMIT_CONSECUTIVE:
                long_periods.append((streak_start, streak_end, streak_count))
            
            max_streak = max(max_streak, streak_count)
            
            # 초기화 (새로운 구간 시작)
            streak_start = nxt
            streak_end = nxt
            streak_count = 1
            
    # 마지막 구간 체크
    if streak_count >= LIMIT_CONSECUTIVE:
        long_periods.append((streak_start, streak_end, streak_count))
    max_streak = max(max_streak, streak_count)
    
    return max_streak, long_periods

def analyze_long_term_absence(roster):
    # [1] 명렬표 기준 초기화
    stats = {num: {'name': name, 'count': 0, 'details': [], 'raw_dates': []} for num, name in roster.items()}
    
    print("   📉 [분석] 장기결석 위험군 스캔 중...")
    
    for month in ACADEMIC_MONTHS:
        events = load_all_events(None, month, roster)
        for e in events:
            if e['num'] not in stats: continue

            # 결석(질병, 미인정, 기타)만 카운트 (인정결석 제외)
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
        
        # [New] 연속 결석 분석 (수업일수 기준)
        max_cons, long_periods = calculate_max_consecutive(data['raw_dates'])
        is_long_streak = (max_cons >= LIMIT_CONSECUTIVE)
        
        # 결석 0일인 학생 처리 (연속결석도 없으면 제외)
        if count == 0 and not is_long_streak: continue 
        
        msg, color_class, pct = get_status_info(count)
        bar_color = color_map[color_class]

        # 알림 생성 (누적 or 연속)
        if count >= THRESHOLD_L1:
            alerts.append(f"{data['name']}(누적 {count}일): {msg}")
            
        if is_long_streak:
            # 기간 문자열 생성 (예: "08.27~09.05(8일)")
            period_str = ", ".join([f"{s.strftime('%m.%d')}~{e.strftime('%m.%d')}({d}일)" for s, e, d in long_periods])
            alerts.append(f"🚨 {data['name']}: 연속 {max_cons}일 결석! [{period_str}]")
            
            msg += f" / 🚨연속 {max_cons}일"
            
            # 연속 결석 발견 시 색상 격상
            if color_class == "bg-green": 
                color_class = "bg-orange"
                bar_color = color_map["bg-orange"]
        
        rows.append({
            'num': num,
            'name': data['name'],
            'count': count,
            'msg': msg,
            'color_class': color_class,
            'bar_color': bar_color,
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
