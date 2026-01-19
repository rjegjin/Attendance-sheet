import os
import datetime
from jinja2 import Environment, FileSystemLoader
from src.services.data_loader import load_all_events, get_master_roster, ACADEMIC_MONTHS
from src.paths import REPORTS_DIR, SRC_DIR
import src.services.universal_notification as bot

# [설정] 경로 및 템플릿 환경
OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "stats")
TEMPLATE_DIR = os.path.join(str(SRC_DIR), "templates")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)
if not os.path.exists(TEMPLATE_DIR): os.makedirs(TEMPLATE_DIR, exist_ok=True)

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

# [설정] 체험학습 규정
LIMIT_DOMESTIC_TOTAL = 10      
LIMIT_DOMESTIC_CONSECUTIVE = 5 
LIMIT_INTL_TOTAL = 10          

def calculate_periods(dates):
    """날짜 리스트를 받아 기간과 최대 연속일수를 계산"""
    if not dates: return [], 0
    dates = sorted(list(set(dates)))
    periods = []
    
    current_streak = 1
    start_date = dates[0]
    prev_date = dates[0]
    max_consecutive = 1
    
    for i in range(1, len(dates)):
        curr_date = dates[i]
        delta = (curr_date - prev_date).days
        if delta <= 4: # 주말/공휴일 포함 4일 이내 간격은 연속으로 간주
            current_streak += 1
        else:
            periods.append((start_date, prev_date, current_streak))
            max_consecutive = max(max_consecutive, current_streak)
            current_streak = 1
            start_date = curr_date
        prev_date = curr_date
        
    periods.append((start_date, prev_date, current_streak))
    max_consecutive = max(max_consecutive, current_streak)
    return periods, max_consecutive

def analyze_field_trips(roster):
    # [1] 데이터 수집 (안전하게 모든 학생 대상)
    # 구조: { 번호: { 'name': 이름, 'dom': [], 'int': [] } }
    raw_data = {num: {'name': name, 'dom': [], 'int': []} for num, name in roster.items()}
    
    print("   📊 [분석] 국내/국외 체험학습 데이터 분석 중...")
    
    for month in ACADEMIC_MONTHS:
        events = load_all_events(None, month, roster)
        for e in events:
            full_text = (e['raw_type'] + e['reason']).replace(" ", "")
            if ("체험" in full_text or "교외" in full_text) and not e['is_unexcused']:
                
                num = e['num']
                # 명렬표에 없는 학생(전학/누락)이라도 기록이 있으면 추가 (에러 방지)
                if num not in raw_data:
                    raw_data[num] = {'name': e['name'], 'dom': [], 'int': []}

                is_intl = any(k in full_text for k in ["국외", "해외", "유학", "출국", "비자"])
                if is_intl: 
                    raw_data[num]['int'].append(e['date'])
                else: 
                    raw_data[num]['dom'].append(e['date'])

    # [2] 리포트 데이터 생성 (여기서 필터링 적용!)
    students_data = []
    alerts = []
    
    for num in sorted(raw_data.keys()):
        student_info = raw_data[num]
        name = student_info['name']
        d_dates = student_info['dom']
        i_dates = student_info['int']
        
        # 🚨 [핵심 수정] 국내/국외 모두 사용 내역이 없으면 리포트에서 제외
        if not d_dates and not i_dates: 
            continue
        
        d_periods, d_max = calculate_periods(d_dates)
        i_periods, i_max = calculate_periods(i_dates)
        
        # 위반 여부 체크
        is_d_over = len(d_dates) > LIMIT_DOMESTIC_TOTAL
        is_i_over = len(i_dates) > LIMIT_INTL_TOTAL
        is_d_cons_over = d_max > LIMIT_DOMESTIC_CONSECUTIVE
        
        # 알림 메시지 생성
        if is_d_over: alerts.append(f"{name}: 국내 {len(d_dates)}일 (초과)")
        if is_i_over: alerts.append(f"{name}: 국외 {len(i_dates)}일 (초과)")
        if is_d_cons_over: alerts.append(f"{name}: 국내연속 {d_max}일 (주의)")

        # 뱃지(Badges) 생성
        badges = []
        if is_d_over: badges.append({'text': f'국내초과({len(d_dates)})', 'color_class': 'bg-red'})
        if is_d_cons_over: badges.append({'text': f'연속주의({d_max}일)', 'color_class': 'bg-orange'})
        if is_i_over: badges.append({'text': f'국외초과({len(i_dates)})', 'color_class': 'bg-red'})
        
        # 카드 테두리 색상 결정
        card_class = ""
        if d_dates or i_dates: card_class = "has-data"
        if is_d_cons_over: card_class = "warning"
        if is_d_over or is_i_over: card_class = "violation"

        # 상세 내역 텍스트 가공
        d_details_list = []
        for s, e, days in d_periods:
            txt = f"{s.strftime('%m.%d')}~{e.strftime('%m.%d')}({days}일)"
            if days > LIMIT_DOMESTIC_CONSECUTIVE: txt = f"<b style='color:#fd7e14'>{txt}</b>"
            d_details_list.append(txt)
            
        i_details_list = []
        for s, e, days in i_periods:
            i_details_list.append(f"{s.strftime('%m.%d')}~{e.strftime('%m.%d')}({days}일)")

        students_data.append({
            'num': num,
            'name': name,
            'card_class': card_class,
            'badges': badges,
            'dom': {
                'total': len(d_dates),
                'pct': min((len(d_dates)/LIMIT_DOMESTIC_TOTAL)*100, 100),
                'color': "#28a745" if not is_d_over else "#dc3545",
                'details': " / ".join(d_details_list)
            },
            'intl': {
                'total': len(i_dates),
                'pct': min((len(i_dates)/LIMIT_INTL_TOTAL)*100, 100) if LIMIT_INTL_TOTAL > 0 else 0,
                'color': "#17a2b8" if not is_i_over else "#dc3545",
                'details': " / ".join(i_details_list)
            }
        })

    return students_data, alerts

def run_fieldtrip_stats():
    print(f"=== 교외체험학습 연간 통계 (Jinja2) ===")
    roster = get_master_roster()
    students_data, alerts = analyze_field_trips(roster)
    
    # Jinja2 템플릿 렌더링
    template = env.get_template("stats_fieldtrip.html")
    html = template.render(
        limits={
            'dom_total': LIMIT_DOMESTIC_TOTAL,
            'dom_cons': LIMIT_DOMESTIC_CONSECUTIVE,
            'intl_total': LIMIT_INTL_TOTAL
        },
        students=students_data
    )
    
    out_file = os.path.join(OUTPUT_DIR, "연간_체크_체험학습통계.html")
    with open(out_file, "w", encoding="utf-8") as f: f.write(html)
    print(f"   ✅ 리포트 생성 완료: {out_file}")

    if alerts:
        bot.send_alert(f"🚌 [체험학습 주의/초과 알림]\n" + "\n".join(alerts))
        print(f"   🔔 알림 전송 완료 ({len(alerts)}건)")

if __name__ == "__main__":
    run_fieldtrip_stats()