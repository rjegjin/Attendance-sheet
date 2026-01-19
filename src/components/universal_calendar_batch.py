import pandas as pd
import datetime
import os

# [수정] 필요한 함수와 변수를 '직접' 가져옵니다.
from src.services.data_loader import (
    load_all_events, 
    get_master_roster, 
    TARGET_YEAR, 
    ACADEMIC_MONTHS
)
from src.paths import REPORTS_DIR

# 경로 설정
OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "calendar")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

def create_calendar_html(year, month, daily_records, output_path):
    html = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8"><style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
            body {{ font-family: 'Noto Sans KR', sans-serif; padding: 20px; }}
            h2 {{ text-align: center; margin-bottom: 20px; }}
            table {{ width: 100%; height: 80vh; border-collapse: collapse; table-layout: fixed; }}
            th {{ background-color: #eee; height: 30px; border: 1px solid #333; }}
            td {{ border: 1px solid #333; vertical-align: top; padding: 5px; position: relative; }}
            .day-num {{ font-weight: bold; margin-bottom: 5px; display: block; }}
            .event {{ font-size: 0.85em; margin-bottom: 2px; line-height: 1.3; }}
            .sun {{ color: red; }} .sat {{ color: blue; }}
            @media print {{ @page {{ size: A4 landscape; margin: 5mm; }} body {{ padding: 0; }} table {{ height: 95vh; }} }}
        </style></head><body>
        <h2>{year}년 {month}월 학급 생활기록</h2>
        <table><thead><tr><th class="sun">일</th><th>월</th><th>화</th><th>수</th><th>목</th><th>금</th><th class="sat">토</th></tr></thead><tbody><tr>"""
    
    import calendar
    _, last_day = calendar.monthrange(year, month)
    first_weekday = datetime.date(year, month, 1).weekday() 
    start_col = (first_weekday + 1) % 7 
    current_col = 0
    
    for _ in range(start_col): html += "<td></td>"; current_col += 1
        
    for day in range(1, last_day + 1):
        if current_col == 7: html += "</tr><tr>"; current_col = 0
        cls = "sun" if current_col == 0 else "sat" if current_col == 6 else ""
        content = f"<span class='day-num {cls}'>{day}</span>"
        if day in daily_records:
            for rec in daily_records[day]: content += f"<div class='event'>{rec}</div>"
        html += f"<td>{content}</td>"; current_col += 1
        
    while current_col < 7: html += "<td></td>"; current_col += 1
    html += "</tr></tbody></table></body></html>"
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

def run_calendar(target_months=None):
              
    # 인자가 없으면 전체 월 실행
    if target_months is None: target_months = ACADEMIC_MONTHS
    
    print(f"=== 생활기록 달력 생성 (대상: {target_months}) ===")
    master_roster = get_master_roster() 
    
    for month in target_months:
        year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        
        raw_events = load_all_events(None, month, master_roster)
        daily = {}
        if raw_events:
            for e in raw_events:
                day = e['date'].day
                if day not in daily: daily[day] = []
                daily[day].append(f"{e['num']} {e['name']} : {e['type']}")
            for d in daily: daily[d].sort(key=lambda x: int(x.split()[0]))
        
        out = os.path.join(OUTPUT_DIR, f"{month:02d}월_생활기록_달력.html")
        create_calendar_html(year, month, daily, out)
        print(f"   -> {year}년 {month}월 완료")

if __name__ == "__main__":
    # 단독 실행 시 전체 생성
    run_calendar()