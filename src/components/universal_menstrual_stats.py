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

LIMIT_ABSENCE = 1
LIMIT_SUB = 3

def analyze_menstrual_stats(roster):
    # [1] 명렬표 기준 초기화 (모든 학생 포함)
    raw_stats = {num: {m: {'abs': [], 'sub': []} for m in ACADEMIC_MONTHS} for num in roster}
    print("   🩸 [분석] 생리인정결석 데이터 스캔 중...")
    
    for month in ACADEMIC_MONTHS:
        events = load_all_events(None, month, roster)
        for e in events:
            # [2] 명렬표에 없는 번호 무시 (유령 학생 제거)
            if e['num'] not in raw_stats:
                continue

            if "생리" in e['raw_type'] or "생리" in e['reason']:
                date_str = e['date'].strftime("%m.%d")
                if "결석" in e['raw_type']:
                    raw_stats[e['num']][month]['abs'].append(date_str)
                elif any(x in e['raw_type'] for x in ["지각", "조퇴", "결과"]):
                    raw_stats[e['num']][month]['sub'].append(date_str)
    
    rows = []
    alerts = []
    
    # [3] 명렬표 순서대로 리포트 행 생성
    for num in sorted(roster.keys()):
        name = roster[num]
        cells = []
        
        for month in ACADEMIC_MONTHS:
            data = raw_stats[num][month]
            abs_cnt = len(data['abs'])
            sub_cnt = len(data['sub'])
            
            cell_class = ""
            content = ""
            tooltip = ""
            
            # 사용 내역이 있을 때만 내용 채움
            if abs_cnt > 0 or sub_cnt > 0:
                tips = []
                if abs_cnt: tips.append(f"결석: {', '.join(data['abs'])}")
                if sub_cnt: tips.append(f"기타: {', '.join(data['sub'])}")
                tooltip = " | ".join(tips)
                
                is_violation = (abs_cnt > 0 and sub_cnt > 0) or (abs_cnt > LIMIT_ABSENCE) or (sub_cnt > LIMIT_SUB)
                
                if is_violation:
                    cell_class = "violation"
                    content = f"⚠ 위반<br><span style='font-size:0.8em'>결{abs_cnt}/기{sub_cnt}</span>"
                    alerts.append(f"{name}({month}월): 결{abs_cnt}/기{sub_cnt} (위반)")
                elif abs_cnt > 0:
                    cell_class = "used-abs"
                    content = f"결석 {abs_cnt}"
                else:
                    cell_class = "used-sub"
                    content = f"기타 {sub_cnt}"
            
            cells.append({
                'class': cell_class,
                'content': content,
                'tooltip': tooltip
            })
            
        rows.append({'num': num, 'name': name, 'cells': cells})
        
    return rows, alerts

def run_menstrual_stats():
    roster = get_master_roster()
    rows, alerts = analyze_menstrual_stats(roster)
    
    template = env.get_template("stats_menstrual.html")
    html = template.render(
        months=ACADEMIC_MONTHS,
        rows=rows
    )
    
    out_file = os.path.join(OUTPUT_DIR, "생리인정결석_통계.html")
    with open(out_file, "w", encoding="utf-8") as f: f.write(html)
    print(f"   ✅ 리포트 생성 완료: {out_file}")

    if alerts:
        bot.send_alert(f"🩸 [생리인정 규정위반 경고]\n" + "\n".join(alerts))
        print(f"   🔔 알림 전송 완료 ({len(alerts)}건)")

if __name__ == "__main__":
    run_menstrual_stats()