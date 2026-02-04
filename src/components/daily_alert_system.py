import os
import sys
import datetime
import gspread
from pathlib import Path

# [Import] 경로 상수
from src.paths import ROOT_DIR

# [Import] 서비스 및 데이터 로더
from src.services import data_loader 
from src.services import universal_notification as bot
# [Import] 체크리스트 매니저 (제출 여부 확인용)
from src.components import checklist_manager as checklist_db 

# [Import] Utils (DateCalculator)
try:
    from src.utils.date_calculator import DateCalculator
    has_utils = True
except ImportError:
    has_utils = False
    print("⚠️ [Warning] DateCalculator 모듈을 찾을 수 없습니다.")

# [설정] 서류 미제출 독촉 기준일 (5일 경과)
DOCUMENT_DEADLINE_DAYS = 5

# Utils 인스턴스 초기화 (Default to ROOT_DIR via src.paths)
date_calc = DateCalculator() if has_utils else None

def get_today_date():
    return datetime.date.today()

# =========================================================
# 1. 📅 오늘의 출결 브리핑
# =========================================================
def send_morning_briefing(roster):
    today = get_today_date()
    month = today.month
    
    # 학기 중이 아니면 스킵 (단, 데이터 로더 설정에 따름)
    if month not in data_loader.ACADEMIC_MONTHS: return

    print(f"   ☀️ [브리핑] {today.strftime('%m월 %d일')} 출결 데이터 집계 중...")
    
    # data_loader를 통해 오늘 데이터 로드
    try:
        events = data_loader.load_all_events(None, month, roster)
    except Exception:
        print("      ❌ 데이터 로드 실패")
        return

    today_events = [e for e in events if e['date'] == today]
    
    if not today_events:
        print("      -> 특이사항 없음")
        return

    # 정렬 (번호순)
    today_events.sort(key=lambda x: x['num'])

    lines = []
    for e in today_events:
        # [강화된 로직] 미인정/무단 결석은 불꽃 아이콘으로 강조
        is_unexcused = e.get('is_unexcused', False) or "미인정" in e['raw_type'] or "무단" in e['raw_type']
        icon = "🔥" if is_unexcused else "📝"
        
        # 표시할 타입 (결석 글자 제외 등 가공)
        display_type = e['raw_type'].replace('결석', '').strip()
        if not display_type: display_type = "결석" # 그냥 '결석'인 경우
        
        if e['time']:
            display_type += f" ({e['time']})"
            
        lines.append(f"{icon} {e['name']}({display_type})")

    msg = f"☀️ [{today.strftime('%m/%d')} 출결 현황]\n" + "\n".join(lines)
    
    if bot.send_alert(msg):
        print("      -> 🔔 텔레그램 전송 완료")
    else:
        print("      -> ❌ 전송 실패 (네트워크를 확인하세요)")

# =========================================================
# 2. 🎂 생일 알림 (주간 예보 기능 통합)
# =========================================================
def send_enhanced_birthday_alert(roster):
    print("   🎂 [생일] 생일자 확인 중...")
    today = get_today_date()
    
    # 구글 시트에서 생일 정보 가져오기
    try:
        client = data_loader.get_google_client()
        if not client: return
        doc = data_loader.get_sheet_instance() # 기존 인스턴스 재사용 권장
        if not doc:
             # data_loader에 인스턴스가 없으면 새로 연결 시도 (fallback)
             doc = client.open_by_url(data_loader.GOOGLE_SHEET_URL)

        # 시트 이름 찾기 ('기본정보' 등)
        worksheet = None
        for title in ["기본정보", "명렬표", "학생명단"]:
            try: worksheet = doc.worksheet(title); break
            except: pass
        if not worksheet: worksheet = doc.get_worksheet(0)
            
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

# =========================================================
# 3. 📑 증빙서류 미제출 독촉 (제출여부 확인 기능 추가)
# =========================================================
def send_document_reminder(roster):
    print(f"   📑 [서류] 증빙서류 필요 건(결석/인정) {DOCUMENT_DEADLINE_DAYS}일 경과 확인...")
    today = get_today_date()
    
    # 지난달 말일 결석자도 체크하기 위해 이번달 + 지난달 스캔
    check_months = sorted(list(set([today.month, (today.replace(day=1) - datetime.timedelta(days=1)).month])))
    check_months = [m for m in check_months if m in data_loader.ACADEMIC_MONTHS]
    
    all_events = []
    for month in check_months:
        try:
            events = data_loader.load_all_events(None, month, roster)
            all_events.extend(events)
        except: continue
    
    # [핵심] Phase 3에서 리팩토링된 data_loader.group_consecutive_events 호출
    # (내부적으로 DateCalculator를 사용하여 휴일은 건너뛰고 묶어줌)
    grouped_events = data_loader.group_consecutive_events(all_events)
    
    alerts = []
    for group in grouped_events:
        raw_type = group['raw_type']
        
        # [정책] 미인정/무단은 증빙서류 제출 대상이 아닐 수 있음 -> 제외
        if ("미인정" in raw_type) or group.get('is_unexcused', False):
            continue
            
        # 결석, 인정결석, 기타결석 등 증빙이 필요한 건만 타겟팅
        is_target = ("결석" in raw_type) or ("인정" in raw_type) or ("기타" in raw_type)
        
        if is_target:
            start_date = group['start']
            end_date = group['end']
            name = group['name']
            
            # 경과일수 계산
            delta = (today - start_date).days
            
            if delta >= DOCUMENT_DEADLINE_DAYS:
                # [체크] checklist_manager 모듈을 통해 이미 제출했는지 확인
                date_key = start_date.strftime("%m.%d") # "03.05"
                
                # is_submitted 함수가 있다고 가정 (인터페이스 준수)
                if hasattr(checklist_db, 'is_submitted'):
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

# =========================================================
# 실행 진입점
# =========================================================
def run_daily_checks():
    print("\n" + "="*40)
    print(" 🌅 [매일 아침/오후] 출결 종합 브리핑")
    print("="*40)
    
    # 1. 휴일/주말 실행 방지
    # DateCalculator가 있으면 스마트하게 체크, 없으면 주말만 체크
    if date_calc:
        if not date_calc.is_school_day(datetime.datetime.now()):
            print(" 📅 오늘은 휴일(주말/공휴일)입니다. 알림 시스템을 가동하지 않습니다.")
            return
    else:
        if datetime.date.today().weekday() >= 5:
            print(" 📅 주말입니다. 알림을 건너뜁니다.")
            return

    try:
        roster = data_loader.get_master_roster()
        if not roster:
            print(" ❌ 명렬표를 불러오지 못해 중단합니다.")
            return

        # 2. 출결 브리핑
        send_morning_briefing(roster)
        
        # 3. 생일 알림 (월요일 주간예보 포함)
        send_enhanced_birthday_alert(roster)
        
        # 4. 서류 독촉 (제출완료 건 제외)
        send_document_reminder(roster)
        
        print("\n ✅ 점검 완료.")
    except Exception as e:
        print(f" ❌ 실행 중 오류 발생: {e}")
        # import traceback; traceback.print_exc() # 디버깅 시 주석 해제

if __name__ == "__main__":
    run_daily_checks()
