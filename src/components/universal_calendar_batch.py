import os
import sys
import datetime
import calendar

# 프로젝트 루트 경로 설정
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_PATH))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# [Import] 데이터 로더 및 경로
from src.services.data_loader import load_all_events, get_master_roster, TARGET_YEAR, ACADEMIC_MONTHS
from src.paths import REPORTS_DIR

# [Import] Utils (DateCalculator & TemplateManager)
try:
    from src.utils.date_calculator import DateCalculator
    from src.utils.template_manager import TemplateManager
    has_utils = True
except ImportError:
    has_utils = False
    print("⚠️ [Warning] Utils 모듈을 찾을 수 없습니다.")

# 경로 설정
OUTPUT_DIR = os.path.join(str(REPORTS_DIR), "calendar")
if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR, exist_ok=True)

# Utils 인스턴스
date_calc = DateCalculator(PROJECT_ROOT) if has_utils else None
tmpl_mgr = TemplateManager(PROJECT_ROOT) if has_utils else None

def build_calendar_data(year, month, daily_records):
    """
    달력 템플릿에 넘길 2차원 리스트(Weeks -> Days) 생성
    """
    # [핵심 수정 1] 달력 시작 요일을 '일요일(6)'로 설정 (기본값은 월요일(0))
    calendar.setfirstweekday(6) 
    cal = calendar.monthcalendar(year, month)
    
    calendar_weeks = []
    
    for week in cal:
        week_data = []
        # col_idx: 0(일), 1(월), 2(화), 3(수), 4(목), 5(금), 6(토)
        for day_num, col_idx in zip(week, range(7)):
            
            # 빈 날짜 처리
            if day_num == 0:
                week_data.append({'day_num': 0, 'css_class': 'empty'})
                continue
            
            current_date = datetime.date(year, month, day_num)
            events = daily_records.get(day_num, [])
            
            # 스타일 및 속성 초기화
            num_class = ""
            css_class = ""
            is_holiday_name = "" 
            
            # [핵심 수정 2] 요일별 색상 로직 변경 (일요일 시작 기준)
            if col_idx == 0: 
                num_class = "sun" # 0번 인덱스 = 일요일 (빨강)
            elif col_idx == 6: 
                num_class = "sat" # 6번 인덱스 = 토요일 (파랑)
            
            # 2. 공휴일 체크 (평일인데 쉬는 날이면 빨간색)
            # DateCalculator 활용
            if date_calc and not date_calc.is_school_day(current_date):
                # current_date.weekday()는 설정과 무관하게 항상 월=0 ~ 일=6임
                # 주말(5,6)이 아닌데 학교를 안 간다면 -> 평일 공휴일/재량휴업일
                weekday_std = current_date.weekday()
                if weekday_std < 5: 
                    num_class = "holiday"
                    css_class = "holiday-bg"
                    # 공휴일 이름 표시는 선택사항

            week_data.append({
                'day_num': day_num,
                'num_class': num_class,
                'css_class': css_class,
                'is_holiday_name': is_holiday_name,
                'events': events
            })
        calendar_weeks.append(week_data)
        
    return calendar_weeks

def run_calendar(target_months=None):
    if target_months is None: target_months = ACADEMIC_MONTHS
    
    print(f"=== 생활기록 달력 생성 (대상: {target_months}) ===")
    
    try:
        master_roster = get_master_roster()
    except Exception as e:
        print(f"❌ 명렬표 로드 실패: {e}")
        return
    
    for month in target_months:
        year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        
        # 데이터 로드
        try:
            raw_events = load_all_events(None, month, master_roster)
        except:
            print(f"⚠️ {month}월 데이터 로드 실패, 빈 달력 생성")
            raw_events = []

        # 일별 데이터 정리
        daily = {}
        if raw_events:
            for e in raw_events:
                day = e['date'].day
                if day not in daily: daily[day] = []
                
                # 표시 형식: "1 홍길동 : 질병결석"
                daily[day].append(f"{e['num']} {e['name']} : {e['type']}")
            
            # 번호순 정렬
            for d in daily:
                daily[d].sort(key=lambda x: int(x.split()[0]) if x.split()[0].isdigit() else 0)
        
        # 템플릿 데이터 생성
        calendar_weeks = build_calendar_data(year, month, daily)
        
        # HTML 렌더링
        out_file = os.path.join(OUTPUT_DIR, f"{month:02d}월_생활기록_달력.html")
        context = {
            'year': year,
            'month': month,
            'calendar_weeks': calendar_weeks
        }
        
        if tmpl_mgr and tmpl_mgr.render_and_save("calendar_template.html", context, out_file):
            print(f"   -> {year}년 {month}월 완료")
        else:
            print(f"   ❌ {month}월 달력 생성 실패 (TemplateManager 오류)")

if __name__ == "__main__":
    run_calendar()


    """
    if not date_calc: return None
    
    # DateCalculator._load_holidays는 내부 메서드지만, 
    # 편의상 여기서 휴일 목록(Set)을 가져와서 이름(Dict)으로 매핑하는 로직이 필요함.
    # 하지만 DateCalculator는 현재 Set(날짜)만 반환하므로, 
    # 정확한 '공휴일 이름'을 표시하려면 DateCalculator를 조금 수정하거나
    # 여기서 holidays.json을 직접 읽어야 함.
    # -> 간편하게: is_school_day가 False이고 평일이면 '휴일'로 표시하거나,
    # -> 정석대로: DateCalculator에 get_holiday_name 메서드를 추가하는 것이 좋음.
    
    # 여기서는 DateCalculator의 휴일 Set에 날짜가 있는지만 체크 (이름 표시는 추후 고도화)
    date_str = date_obj.strftime("%Y-%m-%d")
    holidays = date_calc._load_holidays(date_obj.year)
    
    if date_str in holidays:
        # 휴일 이름 매핑 로직이 없다면 그냥 True 반환 (CSS로 빨갛게만 표시)
        return "공휴일/재량휴업" 
    return None

def build_calendar_data(year, month, daily_records):
    """
    달력 템플릿에 넘길 2차원 리스트(Weeks -> Days) 생성
    """
    cal = calendar.monthcalendar(year, month)
    calendar_weeks = []
    
    for week in cal:
        week_data = []
        for day_num, weekday in zip(week, range(7)):
            if day_num == 0:
                week_data.append({'day_num': 0, 'css_class': 'empty'})
                continue
            
            current_date = datetime.date(year, month, day_num)
            events = daily_records.get(day_num, [])
            
            # 스타일 결정
            num_class = ""
            css_class = ""
            holiday_name = None
            
            # 1. 요일별 색상 (일=sun, 토=sat)
            if weekday == 6: num_class = "sun" # 일요일
            elif weekday == 5: num_class = "sat" # 토요일
            
            # 2. 공휴일 체크 (빨간색 덮어쓰기)
            # DateCalculator 활용
            if date_calc and not date_calc.is_school_day(current_date) and weekday < 5:
                # 평일인데 쉬는 날이면 공휴일/재량휴업일
                num_class = "holiday"
                css_class = "holiday-bg"
                
                # 공휴일 이름 가져오기 (json 직접 조회 - 임시)
                # 실제로는 DateCalculator에 get_holiday_name 기능 추가 권장
                # 여기선 간단히 '휴일' 표시
                # holiday_name = "휴일" 

            week_data.append({
                'day_num': day_num,
                'num_class': num_class,
                'css_class': css_class,
                'holiday_name': holiday_name,
                'events': events
            })
        calendar_weeks.append(week_data)
        
    return calendar_weeks

def run_calendar(target_months=None):
    if target_months is None: target_months = ACADEMIC_MONTHS
    
    print(f"=== 생활기록 달력 생성 (대상: {target_months}) ===")
    
    try:
        master_roster = get_master_roster()
    except:
        print("❌ 명렬표 로드 실패")
        return
    
    for month in target_months:
        year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
        
        # 데이터 로드
        try:
            raw_events = load_all_events(None, month, master_roster)
        except:
            print(f"⚠️ {month}월 데이터 로드 실패, 빈 달력 생성")
            raw_events = []

        # 일별 데이터 정리
        daily = {}
        if raw_events:
            for e in raw_events:
                day = e['date'].day
                if day not in daily: daily[day] = []
                
                # 표시 형식: "1 홍길동 : 질병결석"
                daily[day].append(f"{e['num']} {e['name']} : {e['type']}")
            
            # 번호순 정렬
            for d in daily:
                daily[d].sort(key=lambda x: int(x.split()[0]))
        
        # 템플릿 데이터 생성
        calendar_weeks = build_calendar_data(year, month, daily)
        
        # HTML 렌더링
        out_file = os.path.join(OUTPUT_DIR, f"{month:02d}월_생활기록_달력.html")
        context = {
            'year': year,
            'month': month,
            'calendar_weeks': calendar_weeks
        }
        
        if tmpl_mgr and tmpl_mgr.render_and_save("calendar_template.html", context, out_file):
            print(f"   -> {year}년 {month}월 완료")
        else:
            print(f"   ❌ {month}월 달력 생성 실패")

if __name__ == "__main__":
    run_calendar()
