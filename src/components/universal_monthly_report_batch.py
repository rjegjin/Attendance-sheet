import os
import datetime
import calendar
from jinja2 import Environment, FileSystemLoader

# [설정] 필요한 상수 및 로더 import
from src.services.data_loader import (
    load_all_events, 
    get_master_roster, 
    ACADEMIC_MONTHS, 
    HOLIDAYS_KR,
    TARGET_YEAR
)
from src.paths import REPORTS_DIR, SRC_DIR

# [경로] monthly 폴더 사용
OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "monthly")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)

# 템플릿 환경 설정
TEMPLATE_DIR = os.path.join(str(SRC_DIR), "templates")
if not os.path.exists(TEMPLATE_DIR): os.makedirs(TEMPLATE_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

def calculate_school_days(year, month):
    s = datetime.date(year, month, 1)
    if month == 12: e = datetime.date(year + 1, 1, 1) - datetime.timedelta(days=1)
    else: e = datetime.date(year, month + 1, 1) - datetime.timedelta(days=1)
    
    days = []
    curr = s
    while curr <= e:
        if curr.weekday() < 5 and curr not in HOLIDAYS_KR:
            days.append(curr)
        curr += datetime.timedelta(days=1)
    return days  # ✅ 들여쓰기 수정 완료

# =========================================================
# 1. 월별 세부 리포트 (monthly_detail.html)
# =========================================================
def create_monthly_html(events, master_roster, school_days, month, year, output_path):
    if events: events.sort(key=lambda x: (x['date'], x['num']))
    
    processed_events = []
    for e in events:
        # 명렬표에 없는 번호 제외
        if e['num'] not in master_roster:
            continue
            
        is_req = ("결석" in e['raw_type'] or "인정" in e['raw_type']) and not e['is_unexcused']
        processed_events.append({
            'is_req': is_req,
            'date_str': e['date'].strftime("%Y.%m.%d"),
            'num': e['num'],
            'name': e['name'],
            'raw_type': e['raw_type'],
            'time': e['time'],
            'reason': e['reason']
        })

    template = env.get_template("monthly_detail.html")
    html = template.render(year=year, month=f"{month:02d}", events=processed_events)
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

# =========================================================
# 2. 학급별 통계 리포트 (monthly_class.html)
# =========================================================
def create_class_html(events, master_roster, school_days, month, year, output_path):
    # 명렬표 기준 (학번 제외)
    all_nums = sorted(master_roster.keys())
    all_nums = [n for n in all_nums if n < 100]

    # 데이터 초기화
    stats = {}
    for n in all_nums:
        name = master_roster.get(n, "")
        stats[n] = {'name': name, 'abs':[[],[],[],[]], 'lat':[[],[],[],[]], 'ear':[[],[],[],[]], 'res':[[],[],[],[]]}

    # 이벤트 데이터 채우기
    if events:
        for e in events:
            if e['num'] not in stats: 
                continue
            
            t = e['raw_type']
            
            # 카테고리 분류
            cat = 0 
            if e['is_unexcused']: cat = 1 
            elif "인정" in t: cat = 3     
            elif "기타" in t: cat = 2     
            else: cat = 0                 
            
            k = None
            if "결석" in t: k = 'abs'
            elif "지각" in t: k = 'lat'
            elif "조퇴" in t: k = 'ear'
            elif "결과" in t: k = 'res'
            
            if k:
                stats[e['num']][k][cat].append(e['date'].strftime("%m.%d"))

    # 템플릿용 데이터(rows) 생성
    rows = []
    for n in all_nums:
        s = stats[n]
        row_data = {
            'num': n,
            'disp_num': str(n),
            'name': s['name'],
            'school_days': len(school_days),
            'cells': [],
            'totals': []
        }
        
        totals = {'abs':[], 'lat':[], 'ear':[], 'res':[]}
        categories = ['abs', 'lat', 'ear', 'res']
        
        # 상세 셀
        for k in categories:
            val_lists = s[k]
            for i in range(4): 
                dates = val_lists[i]
                count = len(dates)
                
                classes = []
                if i == 3: classes.append("thick-right")
                if count > 0: classes.append("highlight")
                if i == 1 and count > 0: classes.append("unexcused")

                tooltip = "\n".join(dates) if count > 0 else ""
                
                row_data['cells'].append({
                    'count': count,
                    'classes': " ".join(classes),
                    'tooltip': tooltip
                })
                
                # 🚨 [수정] 인정(cat=3)은 총계에서 제외
                if i != 3: 
                    totals[k].extend(dates)
        
        # 총계 셀
        for k in categories:
            all_dates = sorted(totals[k])
            t_count = len(all_dates)
            tooltip = "\n".join(all_dates) if t_count > 0 else ""
            row_data['totals'].append({
                'count': t_count,
                'classes': "highlight-total" if t_count > 0 else "",
                'tooltip': tooltip
            })
            
        rows.append(row_data)

    last_day = calendar.monthrange(year, month)[1]
    period_str = f"{year}.{month:02d}.01. - {year}.{month:02d}.{last_day}."

    template = env.get_template("monthly_class.html")
    html = template.render(period_str=period_str, rows=rows, month=month)
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

def run_monthly_reports(target_months=None):
    if not target_months: target_months = ACADEMIC_MONTHS
    print(f"=== [1-2] 월별/학급별 리포트 생성 (Jinja2) ===")
    
    roster = get_master_roster()
    
    for month in target_months:
        year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        
        events = load_all_events(None, month, roster)
        days = calculate_school_days(year, month)
        
        out_detail = os.path.join(OUTPUT_DIR, f"{month:02d}월_월별출결현황.html")
        out_class = os.path.join(OUTPUT_DIR, f"{month:02d}월_학급별현황.html")
        
        create_monthly_html(events, roster, days, month, year, out_detail)
        create_class_html(events, roster, days, month, year, out_class)
        print(f"   -> {year}년 {month}월 생성 완료")

if __name__ == "__main__":
    run_monthly_reports()


    return days

# =========================================================
# 1. 월별 세부 리포트 (monthly_detail.html)
# =========================================================
def create_monthly_html(events, master_roster, school_days, month, year, output_path):
    if events: events.sort(key=lambda x: (x['date'], x['num']))
    
    processed_events = []
    for e in events:
        # 명렬표에 없는 번호 제외
        if e['num'] not in master_roster:
            continue
            
        # 인정 결석 등은 세부 리포트에는 표시하되, 필수 확인 대상(is_req)에서는 제외할 수도 있음
        # 여기서는 기존 로직 유지 (인정도 표시)
        is_req = ("결석" in e['raw_type'] or "인정" in e['raw_type']) and not e['is_unexcused']
        processed_events.append({
            'is_req': is_req,
            'date_str': e['date'].strftime("%Y.%m.%d"),
            'num': e['num'],
            'name': e['name'],
            'raw_type': e['raw_type'],
            'time': e['time'],
            'reason': e['reason']
        })

    template = env.get_template("monthly_detail.html")
    html = template.render(year=year, month=f"{month:02d}", events=processed_events)
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

# =========================================================
# 2. 학급별 통계 리포트 (monthly_class.html)
# =========================================================
def create_class_html(events, master_roster, school_days, month, year, output_path):
    # 명렬표 기준 (학번 제외)
    all_nums = sorted(master_roster.keys())
    all_nums = [n for n in all_nums if n < 100]

    # 데이터 초기화
    # abs(결석), lat(지각), ear(조퇴), res(결과)
    # 각 리스트는 [질병, 미인정, 기타, 인정] 순서로 저장됨 (인덱스 0~3)
    stats = {}
    for n in all_nums:
        name = master_roster.get(n, "")
        stats[n] = {'name': name, 'abs':[[],[],[],[]], 'lat':[[],[],[],[]], 'ear':[[],[],[],[]], 'res':[[],[],[],[]]}

    # 이벤트 데이터 채우기
    if events:
        for e in events:
            if e['num'] not in stats: 
                continue
            
            t = e['raw_type']
            
            # 카테고리 분류 (질병=0, 미인정=1, 기타=2, 인정=3)
            cat = 0 
            if e['is_unexcused']: cat = 1     # 미인정
            elif "인정" in t: cat = 3         # 인정
            elif "기타" in t: cat = 2         # 기타
            else: cat = 0                     # 질병 (기본값)
            
            k = None
            if "결석" in t: k = 'abs'
            elif "지각" in t: k = 'lat'
            elif "조퇴" in t: k = 'ear'
            elif "결과" in t: k = 'res'
            
            if k:
                stats[e['num']][k][cat].append(e['date'].strftime("%m.%d"))

    # 템플릿용 데이터(rows) 생성
    rows = []
    for n in all_nums:
        s = stats[n]
        row_data = {
            'num': n,
            'disp_num': str(n),
            'name': s['name'],
            'school_days': len(school_days),
            'cells': [],
            'totals': []
        }
        
        totals = {'abs':[], 'lat':[], 'ear':[], 'res':[]}
        categories = ['abs', 'lat', 'ear', 'res']
        
        # 상세 셀 (질병, 미인정, 기타, 인정 순서)
        for k in categories:
            val_lists = s[k]
            for i in range(4): # 0:질병, 1:미인정, 2:기타, 3:인정
                dates = val_lists[i]
                count = len(dates)
                
                classes = []
                if i == 3: classes.append("thick-right") # 인정 칸 오른쪽 굵은 선
                if count > 0: classes.append("highlight")
                if i == 1 and count > 0: classes.append("unexcused") # 미인정 빨간색

                tooltip = "\n".join(dates) if count > 0 else ""
                
                row_data['cells'].append({
                    'count': count,
                    'classes': " ".join(classes),
                    'tooltip': tooltip
                })
                
                # 🚨 [수정된 핵심 로직]
                # 총계(totals)에는 '인정(cat=3)'을 제외하고 '질병(0), 미인정(1), 기타(2)'만 합산합니다.
                if i != 3: 
                    totals[k].extend(dates)
        
        # 총계 셀 (합계 계산)
        for k in categories:
            all_dates = sorted(totals[k])
            t_count = len(all_dates)
            tooltip = "\n".join(all_dates) if t_count > 0 else ""
            
            row_data['totals'].append({
                'count': t_count, 
                'classes': "highlight-total" if t_count > 0 else "",
                'tooltip': tooltip
            })
            
        rows.append(row_data)

    last_day = calendar.monthrange(year, month)[1]
    period_str = f"{year}.{month:02d}.01. - {year}.{month:02d}.{last_day}."

    template = env.get_template("monthly_class.html")
    html = template.render(period_str=period_str, rows=rows, month=month)
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

def run_monthly_reports(target_months=None):
    if not target_months: target_months = ACADEMIC_MONTHS
    print(f"=== [1-2] 월별/학급별 리포트 생성 (Jinja2) ===")
    
    roster = get_master_roster()
    
    for month in target_months:
        year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        
        events = load_all_events(None, month, roster)
        days = calculate_school_days(year, month)
        
        out_detail = os.path.join(OUTPUT_DIR, f"{month:02d}월_월별출결현황.html")
        out_class = os.path.join(OUTPUT_DIR, f"{month:02d}월_학급별현황.html")
        
        create_monthly_html(events, roster, days, month, year, out_detail)
        create_class_html(events, roster, days, month, year, out_class)
        print(f"   -> {year}년 {month}월 생성 완료")

if __name__ == "__main__":
    run_monthly_reports()

    return days

# =========================================================
# 1. 월별 세부 리포트 (monthly_detail.html)
# =========================================================
def create_monthly_html(events, master_roster, school_days, month, year, output_path):
    if events: events.sort(key=lambda x: (x['date'], x['num']))
    
    processed_events = []
    for e in events:
        # 명렬표에 없는 번호 제외
        if e['num'] not in master_roster:
            continue
            
        is_req = ("결석" in e['raw_type'] or "인정" in e['raw_type']) and not e['is_unexcused']
        processed_events.append({
            'is_req': is_req,
            'date_str': e['date'].strftime("%Y.%m.%d"),
            'num': e['num'],
            'name': e['name'],
            'raw_type': e['raw_type'],
            'time': e['time'],
            'reason': e['reason']
        })

    template = env.get_template("monthly_detail.html")
    html = template.render(year=year, month=f"{month:02d}", events=processed_events)
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

# =========================================================
# 2. 학급별 통계 리포트 (monthly_class.html)
# =========================================================
def create_class_html(events, master_roster, school_days, month, year, output_path):
    # 명렬표 기준 (학번 제외)
    all_nums = sorted(master_roster.keys())
    all_nums = [n for n in all_nums if n < 100]

    # 데이터 초기화
    stats = {}
    for n in all_nums:
        name = master_roster.get(n, "")
        stats[n] = {'name': name, 'abs':[[],[],[],[]], 'lat':[[],[],[],[]], 'ear':[[],[],[],[]], 'res':[[],[],[],[]]}

    # 이벤트 데이터 채우기
    if events:
        for e in events:
            if e['num'] not in stats: 
                continue
            
            t = e['raw_type']
            if e['is_unexcused']: cat = 1 
            elif "인정" in t: cat = 3     
            elif "기타" in t: cat = 2     
            else: cat = 0                 
            
            k = None
            if "결석" in t: k = 'abs'
            elif "지각" in t: k = 'lat'
            elif "조퇴" in t: k = 'ear'
            elif "결과" in t: k = 'res'
            
            if k:
                stats[e['num']][k][cat].append(e['date'].strftime("%m.%d"))

    # 템플릿용 데이터(rows) 생성
    rows = []
    for n in all_nums:
        s = stats[n]
        row_data = {
            'num': n,
            'disp_num': str(n),
            'name': s['name'],
            'school_days': len(school_days),
            'cells': [],
            'totals': []
        }
        
        totals = {'abs':[], 'lat':[], 'ear':[], 'res':[]}
        categories = ['abs', 'lat', 'ear', 'res']
        
        # 상세 셀
        for k in categories:
            val_lists = s[k]
            for i in range(4): 
                dates = val_lists[i]
                count = len(dates)
                
                classes = []
                if i == 3: classes.append("thick-right")
                if count > 0: classes.append("highlight")
                if i == 1 and count > 0: classes.append("unexcused")

                tooltip = "\n".join(dates) if count > 0 else ""
                
                row_data['cells'].append({
                    'count': count,  # 🚨 [수정] 여기서 "."로 바꾸지 않고 정수 그대로 보냅니다!
                    'classes': " ".join(classes),
                    'tooltip': tooltip
                })
                totals[k].extend(dates)
        
        # 총계 셀
        for k in categories:
            all_dates = sorted(totals[k])
            t_count = len(all_dates)
            tooltip = "\n".join(all_dates) if t_count > 0 else ""
            row_data['totals'].append({
                'count': t_count, # 🚨 [수정] 정수 그대로
                'classes': "highlight-total" if t_count > 0 else "",
                'tooltip': tooltip
            })
            
        rows.append(row_data)

    last_day = calendar.monthrange(year, month)[1]
    period_str = f"{year}.{month:02d}.01. - {year}.{month:02d}.{last_day}."

    template = env.get_template("monthly_class.html")
    html = template.render(period_str=period_str, rows=rows, month=month)
    
    with open(output_path, "w", encoding="utf-8") as f: f.write(html)

def run_monthly_reports(target_months=None):
    if not target_months: target_months = ACADEMIC_MONTHS
    print(f"=== [1-2] 월별/학급별 리포트 생성 (Jinja2) ===")
    
    roster = get_master_roster()
    
    for month in target_months:
        year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        
        events = load_all_events(None, month, roster)
        days = calculate_school_days(year, month)
        
        out_detail = os.path.join(OUTPUT_DIR, f"{month:02d}월_월별출결현황.html")
        out_class = os.path.join(OUTPUT_DIR, f"{month:02d}월_학급별현황.html")
        
        create_monthly_html(events, roster, days, month, year, out_detail)
        create_class_html(events, roster, days, month, year, out_class)
        print(f"   -> {year}년 {month}월 생성 완료")

if __name__ == "__main__":
    run_monthly_reports()
