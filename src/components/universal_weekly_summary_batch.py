import pandas as pd
import datetime
import os

# [수정] 필요한 것들을 직접 import
from src.services.data_loader import (
    load_all_events, 
    get_master_roster, 
    TARGET_YEAR, 
    ACADEMIC_MONTHS
)
from src.paths import REPORTS_DIR

OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "weekly")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

# ... (이후 코드 그대로)

def create_weekly_html(month, year, student_data, output_path):
    import calendar
    _, last = calendar.monthrange(year, month)
    start = datetime.date(year, month, 1)
    end = datetime.date(year, month, last)
    
    weeks = []
    curr = start
    while curr.weekday() != 6: curr -= datetime.timedelta(days=1)
    while curr <= end:
        weeks.append((curr, curr + datetime.timedelta(days=6))); curr += datetime.timedelta(days=7)
        
    html = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
        body {{ font-family: 'Malgun Gothic'; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 10pt; table-layout: fixed; }}
        th, td {{ border: 1px solid #999; padding: 5px; vertical-align: top; word-wrap: break-word; }}
        th {{ background: #eee; height: 30px; }}
        .col-num {{ width: 40px; background: #f0f0f0; text-align: center; }}
        .col-name {{ width: 60px; background: #f0f0f0; text-align: center; font-weight: bold; }}
    </style></head><body><h2>{year}년 {month}월 주간 요약</h2><table><thead><tr><th class="col-num">번호</th><th class="col-name">이름</th>"""
    
    for s, e in weeks: html += f"<th>{s.month}/{s.day}~{e.month}/{e.day}</th>"
    html += "</tr></thead><tbody>"
    
    for num in sorted(student_data.keys()):
        s = student_data[num]
        html += f"<tr><td class='col-num'>{num}</td><td class='col-name'>{s['name']}</td>"
        for w_s, w_e in weeks:
            cell = ""
            matched = [e for e in s['events'] if w_s <= e['date'] <= w_e]
            matched.sort(key=lambda x: x['date'])
            for e in matched:
                cell += f"[{e['date'].day}일] {e['type']}<br>"
            html += f"<td>{cell}</td>"
        html += "</tr>"
    html += "</table></body></html>"
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

# [수정] 외부 호출 가능 함수
def run_weekly(target_months=None):
        
    if target_months is None: target_months = ACADEMIC_MONTHS

    print(f"=== 주간 요약 생성 (대상: {target_months}) ===")
    roster = get_master_roster()
    
    for month in target_months:
        year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        
        events = load_all_events(None, month, roster)
        data = {n: {'name': name, 'events': []} for n, name in roster.items()}
        if events:
            for e in events:
                if e['num'] in data: data[e['num']]['events'].append(e)
        
        out = os.path.join(OUTPUT_DIR, f"{month:02d}월_주간요약.html")
        create_weekly_html(month, year, data, out)
        print(f"   -> {year}년 {month}월 완료")

if __name__ == "__main__":
    run_weekly()