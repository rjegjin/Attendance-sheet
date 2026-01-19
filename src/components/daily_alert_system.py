# src/components/daily_alert_system.py (통합 완성본)

import os
import datetime
import gspread

# [수리] 이사 간 모듈들의 주소를 정확히 명시
from src.services import data_loader 
from src.services import universal_notification as bot
# [수리] 체크리스트 DB 확인용 모듈 연결 (generate_checklist 대신 checklist_manager 권장)
from src.components import checklist_manager as checklist_db 

# [설정] 서류 미제출 독촉 기준일 (5일 경과)
DOCUMENT_DEADLINE_DAYS = 5

def get_today_date():
    return datetime.date.today()

# ==========================================
# 1. 📅 오늘의 출결 브리핑
# ==========================================
def send_morning_briefing(roster):
    today = get_today_date()
    month = today.month
    
    # 학기 중이 아니면 스킵
    if month not in data_loader.ACADEMIC_MONTHS: return

    print(f"   ☀️ [브리핑] {today.strftime('%m월 %d일')} 출결 데이터 집계 중...")
    
    # data_loader를 통해 오늘 데이터 로드
    events = data_loader.load_all_events(None, month, roster)
    today_events = [e for e in events if e['date'] == today]
    
    if not today_events:
        print("      -> 특이사항 없음")
        return

    absent, late, etc = [], [], []
    for e in today_events:
        display_type = e['raw_type'].replace('결석','')
        if e['time']:
            display_type += f" [{e['time']}]"
            
        desc = f"{e['name']}({display_type})"
        
        if "결석" in e['raw_type']:
            absent.append(desc)
        elif any(x in e['raw_type'] for x in ["지각", "조퇴", "결과"]):
            late.append(desc)
        else:
            etc.append(desc)

    msg = f"☀️ [{today.strftime('%m/%d')} 출결]\n"
    if absent: msg += f"- 결석({len(absent)}): {', '.join(absent)}\n"
    if late:   msg += f"- 지조결({len(late)}): {', '.join(late)}\n"
    if etc:    msg += f"- 기타: {', '.join(etc)}"
    
    if bot.send_alert(msg):
        print("      -> 🔔 텔레그램 전송 완료")
    else:
        print("      -> ❌ 전송 실패 (네트워크를 확인하세요)")

# ==========================================
# 2. 🎂 생일 알림 (주간 예보 기능 통합)
# ==========================================
def send_enhanced_birthday_alert(roster):
    print("   🎂 [생일] 생일자 확인 중...")
    today = get_today_date()
    
    # 구글 시트에서 생일 정보 가져오기
    try:
        client = data_loader.get_google_client()
        if not client: return
        doc = client.open_by_url(data_loader.GOOGLE_SHEET_URL)
        # [주의] 시트 이름이 '기본정보'가 맞는지 확인 필요 (유연하게 처리 가능)
        try:
            worksheet = doc.worksheet("기본정보")
        except:
            # 혹시 시트 이름이 다를 경우 대비
            worksheet = doc.get_worksheet(0)
            
        rows = worksheet.get_all_values()
    except Exception as e:
        print(f"      ⚠️ 생일 데이터 로드 실패: {e}")
        return

    if not rows: return
    
    # 열 인덱스 찾기
    header = rows[0]
    name_idx = next((i for i, c in enumerate(header) if "성명" in c or "이름" in c), -1)
    num_idx = next((i for i, c in enumerate(header) if "번호" in c), -1)
    birth_idx = 4  # E열 고정 (혹시 변동되면 수정 필요)
    
    if name_idx == -1: return

    # [기능 1] 오늘 생일자 찾기
    today_str_dot = today.strftime("%m.%d")
    today_str_slash = today.strftime("%m/%d")
    today_targets = [today_str_dot, today_str_slash]
    
    today_kids = []
    
    # [기능 2] 주간 생일자 찾기 (월요일인 경우만)
    is_monday = (today.weekday() == 0)
    week_kids = []
    
    # 이번 주 날짜 리스트 생성 (월~일)
    week_dates = []
    if is_monday:
        for i in range(7):
            d = today + datetime.timedelta(days=i)
            week_dates.append({
                'date_obj': d,
                'str_dot': d.strftime("%m.%d"), 
                'str_slash': d.strftime("%m/%d")
            })

    for row in rows[1:]:
        if len(row) <= birth_idx: continue
        
        birth_val = row[birth_idx].strip()
        if not birth_val: continue
        
        student_name = row[name_idx]
        if num_idx != -1 and len(row) > num_idx:
            student_name = f"{row[num_idx]}번 {student_name}"

        # 1. 오늘 생일 체크
        if any(t in birth_val for t in today_targets):
            today_kids.append(student_name)
            
        # 2. 주간 예보 체크 (월요일만)
        if is_monday:
            for w in week_dates:
                if (w['str_dot'] in birth_val) or (w['str_slash'] in birth_val):
                    day_name = ["월","화","수","목","금","토","일"][w['date_obj'].weekday()]
                    desc = f"{student_name} ({w['date_obj'].strftime('%m/%d')} {day_name})"
                    week_kids.append(desc)

    # 알림 발송
    msgs = []
    
    # 주간 예보 메시지
    if is_monday and week_kids:
        week_msg = "📅 [주간 생일 예보]\n이번 주 생일자를 미리 알려드립니다.\n" + "\n".join(week_kids)
        msgs.append(week_msg)
        print(f"      -> 주간 예보 {len(week_kids)}명 발견")

    # 오늘 생일 메시지
    if today_kids:
        today_msg = f"🎉 오늘({today.strftime('%m/%d')}) 생일 축하합니다!\n" + ", ".join(today_kids)
        msgs.append(today_msg)
        print(f"      -> 오늘 생일 {len(today_kids)}명 발견")
    
    if not msgs:
        print("      -> 생일 관련 특이사항 없음")
    
    for m in msgs:
        bot.send_alert(m)

# ==========================================
# 3. 📑 증빙서류 미제출 독촉 (제출여부 확인 기능 추가)
# ==========================================
def send_document_reminder(roster):
    print(f"   📑 [서류] 증빙서류 필요 건(결석/인정) {DOCUMENT_DEADLINE_DAYS}일 경과 확인...")
    today = get_today_date()
    
    # 지난달 말일 결석자도 체크하기 위해 이번달 + 지난달 스캔
    check_months = sorted(list(set([today.month, (today.replace(day=1) - datetime.timedelta(days=1)).month])))
    check_months = [m for m in check_months if m in data_loader.ACADEMIC_MONTHS]
    
    all_events = []
    for month in check_months:
        all_events.extend(data_loader.load_all_events(None, month, roster))
    
    grouped_events = data_loader.group_consecutive_events(all_events)
    
    alerts = []
    for group in grouped_events:
        raw_type = group['raw_type']
        
        # 결석, 인정결석 등 증빙이 필요한 건만 필터링 (미인정/무단 제외)
        if ("미인정" in raw_type) or group.get('is_unexcused', False):
            continue
            
        is_target = ("결석" in raw_type) or ("인정" in raw_type) or ("기타" in raw_type)
        
        if is_target:
            start_date = group['start']
            end_date = group['end']
            name = group['name']
            
            # 경과일수 계산
            delta = (today - start_date).days
            
            if delta >= DOCUMENT_DEADLINE_DAYS:
                # [핵심] checklist_manager 모듈을 통해 이미 제출했는지 확인
                # date 객체를 문자열(YYYY-MM-DD)로 변환하거나, DB 키 형식에 맞춰야 함
                # checklist_manager는 보통 '이름_M.D' 형식을 키로 씀.
                # 여기서는 checklist_db.is_submitted 인터페이스에 맞게 호출
                
                # 날짜 포맷 맞추기 (checklist_manager가 M.D 형식을 쓸 경우)
                date_key = start_date.strftime("%m.%d") # "03.05"
                # 만약 M.D에서 앞 0을 뺀다면(3.5) 로직 조정 필요하지만, 
                # 보통 checklist_manager는 파일명과 키를 맞춤.
                
                if checklist_db.is_submitted(name, date_key):
                    continue

                period_str = start_date.strftime("%m.%d")
                if start_date != end_date:
                    period_str += f"~{end_date.strftime('%m.%d')}"
                
                alerts.append(f"⚠️ {name}({period_str} {raw_type}): {delta}일째 미제출")

    if alerts:
        msg = f"📑 [증빙서류 미제출 명단]\n(발생 후 {DOCUMENT_DEADLINE_DAYS}일 경과)\n" + "\n".join(alerts)
        if bot.send_alert(msg):
            print(f"      -> 독촉 알림 전송 ({len(alerts)}건)")
    else:
        print("      -> 대상 없음 (모두 제출 완료)")

# ==========================================
# 실행
# ==========================================
def run_daily_checks():
    print("\n" + "="*40)
    print(" 🌅 [매일 아침/오후] 출결 종합 브리핑")
    print("="*40)
    
    try:
        roster = data_loader.get_master_roster()
        if not roster:
            print(" ❌ 명렬표를 불러오지 못해 중단합니다.")
            return

        # 1. 출결 브리핑
        send_morning_briefing(roster)
        
        # 2. 생일 알림 (월요일 주간예보 포함)
        send_enhanced_birthday_alert(roster)
        
        # 3. 서류 독촉 (제출완료 건 제외)
        send_document_reminder(roster)
        
        print("\n ✅ 점검 완료.")
    except Exception as e:
        print(f" ❌ 실행 중 오류 발생: {e}")

if __name__ == "__main__":
    run_daily_checks()