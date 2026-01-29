import os
import datetime
import traceback # 에러 추적용
from jinja2 import Environment, FileSystemLoader

# [Import] 데이터 로더 (함수 직접 import 대신 모듈 전체 참조가 안전할 수 있음)
from src.services.data_loader import (
    load_all_events, 
    get_master_roster, 
    ACADEMIC_MONTHS, 
    HOLIDAYS_KR # 휴일 데이터는 가져옴
)
from src.paths import REPORTS_DIR, SRC_DIR

# [Import] 알림 모듈 (경로: src.services)
import src.services.universal_notification as bot

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

# [설정] 연속 결석 위험 기준 (수업일수 기준)
LIMIT_CONSECUTIVE = 7 

# =========================================================
# 유틸리티 함수 (Local Definition)
# =========================================================
def check_gap_is_holiday_local(start, end):
    """
    두 날짜 사이(start < date < end)가 모두 휴일/주말인지 확인
    (data_loader 로딩 문제 방지를 위해 로컬 정의)
    """
    delta = (end - start).days
    if delta <= 1: return False # 사이 날짜 없음
    
    gap_days = [start + datetime.timedelta(days=x) for x in range(1, delta)]
    # HOLIDAYS_KR은 data_loader에서 가져온 리스트 사용
    return all((d.weekday() in [5, 6] or d in HOLIDAYS_KR) for d in gap_days)

def get_status_info(count):
    if count >= THRESHOLD_L4: return "🛑 3차 독촉 (정원외)", "bg-black", 100
    elif count >= THRESHOLD_L3: return "🚨 내교통지서", "bg-red", 90
    elif count >= THRESHOLD_L2: return "🟧 2차 독촉", "bg-orange", 80
    elif count >= THRESHOLD_L1: return "🟨 1차 독촉", "bg-yellow", 60
    else: return "정상", "bg-green", (count / THRESHOLD_L4) * 100

def calculate_max_consecutive(dates):
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
        delta = (nxt - curr).days
        
        # 로컬 함수 사용
        is_connected = (delta == 1) or (delta > 1 and check_gap_is_holiday_local(curr, nxt))
        
        if is_connected:
            streak_end = nxt
            streak_count += 1
        else:
            if streak_count >= LIMIT_CONSECUTIVE:
                long_periods.append((streak_start, streak_end, streak_count))
            max_streak = max(max_streak, streak_count)
            streak_start = nxt
            streak_end = nxt
            streak_count = 1
            
    if streak_count >= LIMIT_CONSECUTIVE:
        long_periods.append((streak_start, streak_end, streak_count))
    max_streak = max(max_streak, streak_count)
    
    return max_streak, long_periods

def analyze_long_term_absence(roster):
    stats = {num: {'name': name, 'count': 0, 'details': [], 'raw_dates': []} for num, name in roster.items()}
    print("   📉 [분석] 장기결석 위험군 스캔 중...")
    
    for month in ACADEMIC_MONTHS:
        events = load_all_events(None, month, roster)
        for e in events:
            if e['num'] not in stats: continue
            if "결석" in e['raw_type'] and "인정" not in e['raw_type']:
                stats[e['num']]['count'] += 1
                stats[e['num']]['details'].append(f"{e['date'].strftime('%m.%d')}({e['raw_type'][:2]})")
                stats[e['num']]['raw_dates'].append(e['date'])
    return stats

def generate_report(stats):
    WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]

    html = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
    <title>장기결석 경고 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; background: #f0f2f5; }}
        h2 {{ text-align: center; color: #333; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #666; font-size: 0.9em; margin-bottom: 30px; }}
        
        .card {{ background: #fff; padding: 15px; margin-bottom: 15px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); border-left: 6px solid #ccc; }}
        .bg-green {{ border-left-color: #28a745; }}
        .bg-yellow {{ border-left-color: #ffc107; background-color: #fffbf2; }}
        .bg-orange {{ border-left-color: #fd7e14; background-color: #fff5eb; }}
        .bg-red {{ border-left-color: #dc3545; background-color: #ffeef0; }}
        .bg-black {{ border-left-color: #212529; background-color: #e2e3e5; }}
        
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }}
        .name-tag {{ font-size: 1.2em; font-weight: bold; }}
        
        .status-badge {{ padding: 4px 8px; border-radius: 4px; font-size: 0.85em; font-weight: bold; color: #fff; background: #666; }}
        .status-bg-green {{ background: #28a745; }}
        .status-bg-yellow {{ background: #ffc107; color: #000; }}
        .status-bg-orange {{ background: #fd7e14; }}
        .status-bg-red {{ background: #dc3545; }}
        .status-bg-black {{ background: #212529; }}

        .consecutive-box {{
            margin-top: 12px;
            background-color: #fff5f5;
            border: 1px solid #feb2b2;
            border-radius: 6px;
            padding: 10px;
        }}
        .consecutive-title {{
            color: #c53030;
            font-weight: bold;
            font-size: 0.9em;
            margin-bottom: 6px;
        }}
        .consecutive-item {{ padding: 3px 0; border-bottom: 1px dashed #eee; font-size: 0.9em; }}
        .day-badge {{
            background-color: #fc8181; color: white;
            padding: 1px 6px; border-radius: 10px;
            font-size: 0.8em; font-weight: bold; margin-left: 6px;
        }}

        .progress-bg {{ width: 100%; background: #e9ecef; height: 10px; border-radius: 5px; margin: 10px 0; overflow: hidden; }}
        .progress-bar {{ height: 100%; transition: width 0.5s; }}
        .details {{ font-size: 0.85em; color: #555; margin-top: 8px; line-height: 1.4; }}
    </style></head><body>
    
    <h2>📉 장기결석(질병/미인정/기타) 관리 리포트</h2>
    <div class="subtitle">기준: {THRESHOLD_L1}일(1차) → {THRESHOLD_L2}일(2차) → {THRESHOLD_L3}일(내교) → {THRESHOLD_L4}일(정원외)</div>
    <div style="text-align:center; font-size:0.85em; color:#666; margin-bottom:20px;">※ 연속 {LIMIT_CONSECUTIVE}일 이상(수업일 기준) 결석 시 상세 구간이 표시됩니다.</div>
    
    <div style="max-width: 800px; margin: 0 auto;">"""

    alerts = []
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['count'], reverse=True)
    color_map = {
        "bg-green":"#28a745", "bg-yellow":"#ffc107", 
        "bg-orange":"#fd7e14", "bg-red":"#dc3545", "bg-black":"#212529"
    }

    has_data = False
    for num, data in sorted_stats:
        count = data['count']
        max_cons, long_periods = calculate_max_consecutive(data['raw_dates'])
        is_long_streak = (max_cons >= LIMIT_CONSECUTIVE)
        
        if count == 0 and not is_long_streak: continue
        has_data = True
        
        msg, color_class, pct = get_status_info(count)
        
        if count >= THRESHOLD_L1:
            alerts.append(f"{data['name']}(누적 {count}일): {msg}")
            
        if is_long_streak:
            period_simple = ", ".join([f"{s.strftime('%m.%d')}~{e.strftime('%m.%d')}" for s, e, d in long_periods])
            alerts.append(f"🚨 {data['name']}: 연속 {max_cons}일 결석! [{period_simple}]")
            msg += f" / 🚨연속 {max_cons}일"
            if color_class == "bg-green": color_class = "bg-orange"

        bar_color = color_map.get(color_class, "#28a745")
        detail_txt = ", ".join(data['details'])
        
        html += f"""
        <div class="card {color_class}">
            <div class="header">
                <span class="name-tag">{num}번 {data['name']} 
                    <span style="font-size:0.8em; color:#666">({count}일 누적)</span>
                </span>
                <span class="status-badge status-{color_class}">{msg}</span>
            </div>
            <div class="progress-bg">
                <div class="progress-bar" style="width: {min(pct, 100)}%; background-color: {bar_color};"></div>
            </div>
            <div class="details">📝 전체 상세: {detail_txt}</div>"""
            
        if is_long_streak:
            html += """<div class="consecutive-box">
                <div class="consecutive-title">🚨 연속 결석 주의 구간 (수업일수 기준)</div>"""
            for start, end, days in long_periods:
                s_str = f"{start.strftime('%m.%d')}({WEEKDAYS[start.weekday()]})"
                e_str = f"{end.strftime('%m.%d')}({WEEKDAYS[end.weekday()]})"
                html += f"""<div class="consecutive-item">• {s_str} ~ {e_str} <span class="day-badge">{days}일간</span></div>"""
            html += "</div>"
            
        html += "</div>"

    if not has_data:
        html += "<div style='text-align:center; padding:30px; color:#999;'>결석 데이터가 없습니다.</div>"

    html += "</div></body></html>"
    
    out_file = os.path.join(OUTPUT_DIR, "장기결석_경고리포트.html")
    with open(out_file, "w", encoding="utf-8") as f: f.write(html)
    print(f"   ✅ 리포트 생성 완료: {out_file}")

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
        # 상세 에러 로그 출력 (디버깅용)
        traceback.print_exc()

if __name__ == "__main__":
    run_long_term_absence()
