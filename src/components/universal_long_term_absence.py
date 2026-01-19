import os
import datetime
from jinja2 import Environment, FileSystemLoader
from src.services.data_loader import load_all_events, get_master_roster, ACADEMIC_MONTHS
from src.paths import REPORTS_DIR, SRC_DIR
import src.services.universal_notification as bot

OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "stats")
TEMPLATE_DIR = os.path.join(str(SRC_DIR), "templates")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# 장기결석 임계값
THRESHOLD_L1 = 30
THRESHOLD_L2 = 40
THRESHOLD_L3 = 45
THRESHOLD_L4 = 50

def get_status_info(count):
    if count >= THRESHOLD_L4: return "🛑 3차 독촉 (정원외)", "bg-black", 100
    elif count >= THRESHOLD_L3: return "🚨 내교통지서", "bg-red", 90
    elif count >= THRESHOLD_L2: return "🟧 2차 독촉", "bg-orange", 80
    elif count >= THRESHOLD_L1: return "🟨 1차 독촉", "bg-yellow", 60
    else: return "정상", "bg-green", (count / THRESHOLD_L4) * 100

def analyze_long_term_absence(roster):
    # [1] 명렬표 기준 초기화
    stats = {num: {'name': name, 'count': 0, 'details': []} for num, name in roster.items()}
    print("   📉 [분석] 장기결석 위험군 스캔 중...")
    
    for month in ACADEMIC_MONTHS:
        events = load_all_events(None, month, roster)
        for e in events:
            # [2] 명렬표에 없는 번호 무시 (KeyError 방지)
            if e['num'] not in stats:
                continue

            if "결석" in e['raw_type'] and "인정" not in e['raw_type']:
                stats[e['num']]['count'] += 1
                stats[e['num']]['details'].append(f"{e['date'].strftime('%m.%d')}({e['raw_type'][:2]})")

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
        
        # (선택) 결석 0일인 학생은 목록에서 제외 (너무 길어짐 방지)
        # 만약 0일인 학생도 보고 싶으면 아래 줄을 주석 처리하세요.
        if count == 0: continue 
        
        msg, color_class, pct = get_status_info(count)
        
        if count >= THRESHOLD_L1:
            alerts.append(f"{data['name']}({count}일): {msg}")
            
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
        bot.send_alert(f"📉 [장기결석 경고]\n" + "\n".join(alerts))
        print(f"   🔔 알림 전송 완료 ({len(alerts)}건)")

if __name__ == "__main__":
    run_long_term_absence()