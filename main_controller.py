import sys
import os
import shutil  # 파일 삭제/이동용
import webbrowser
import glob
import time
import datetime

# =========================================================
# [설정] 프로젝트 경로 및 라이브러리 로딩
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

try:
    # 1. 핵심 서비스 (Services)
    from src.services import data_loader
    from src.services import config_manager  # [New] 설정 관리자
    from src.services import admin_manager   # [New] 시스템 관리자 (진급 로직)

    # 2. 리포트 생성기 (Components)
    from src.components import universal_monthly_report_batch as monthly_report
    from src.components import universal_calendar_batch as calendar_gen
    from src.components import universal_weekly_summary_batch as weekly_gen
    from src.components import universal_monthly_index as index_gen

    # 3. 통계 및 도구
    from src.components import generate_checklist as checklist_gen
    from src.components import universal_fieldtrip_stats as fieldtrip_gen
    from src.components import restore_from_html_to_gsheet as restore_tool
    from src.components import universal_menstrual_stats as menstrual_stats
    from src.components import universal_long_term_absence as absence_gen
    from src.components import daily_alert_system as daily_bot
    from src.components.school_schedule_manager import SchoolScheduleManager

    # 4. 경로 상수
    from src.paths import CACHE_DIR, REPORTS_DIR

except ImportError as e:
    print(f"❌ [Error] 필수 모듈을 찾을 수 없습니다: {e}")
    print("   프로젝트 루트 폴더에서 실행했는지 확인해주세요.")
    sys.exit(1)

# ==========================================
# 유틸리티 함수
# ==========================================
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def clear_all_cache():
    print("\n 🧹 캐시 데이터를 정리하는 중...")
    if not os.path.exists(CACHE_DIR):
        print("   ℹ️ 캐시 폴더가 이미 비어있거나 존재하지 않습니다.")
        return

    try:
        count = 0
        for filename in os.listdir(CACHE_DIR):
            # 중요 설정 파일은 삭제하지 않음
            if filename in ['service_key.json', 'config.json']:
                continue
                
            file_path = os.path.join(CACHE_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                    count += 1
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                    count += 1
            except Exception as e:
                print(f"   ❌ 삭제 실패 ({filename}): {e}")
        
        print(f"   ✅ {count}개의 캐시 파일이 삭제되었습니다.")
    except Exception as e:
        print(f"   ❌ 캐시 폴더 정리 실패: {e}")

# ==========================================
# 메뉴 UI 및 입력
# ==========================================
def get_user_target_months():
    print("-" * 50)
    print(" 🗓️  처리할 '월(Month)'을 선택하세요.")
    print("   [Enter] : 전체 학기 (설정된 월 목록)")
    print("   [숫자]  : 해당 월만 (예: 5)")
    print("   [쉼표]  : 여러 월 (예: 3, 5, 11)")
    print("-" * 50)
    
    val = input(" 선택 > ").strip()
    
    # 기본값: Config에 설정된 학기 전체
    all_months = getattr(data_loader, 'ACADEMIC_MONTHS', [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2])
    
    if not val: 
        return all_months
    
    try:
        return [int(x.strip()) for x in val.split(',') if x.strip().isdigit()]
    except ValueError:
        print(" ❌ 잘못된 입력입니다. 전체 월로 진행합니다.")
        return all_months

def get_menu_choice():
    # 현재 설정된 학년도 표시
    curr_year = config_manager.GLOBAL_CONFIG.get("target_year", 2025)
    
    print("\n" + "="*50)
    print(f" 🏫 학급 출결 관리 시스템 ({curr_year}학년도)")
    print("="*50)
    print(" [기본 업무]")
    print(" 1. 📄 리포트 세트 생성 (달력/월별/주간/체크리스트)")
    print(" 2. 🚌 교외체험학습 연간 통계 분석")
    print(" 3. 🩸 생리인정결석 규정 위반 체크")
    print(" 4. 📉 장기결석 관리 (독촉 기준 체크)")
    print(" 5. 📅 학사일정 업데이트 (Google Sheets)")
    print("-" * 50)
    print(" [유틸리티]")
    print(" 7. 🌅 아침 브리핑 & 알림 발송")
    print(" 8. ✅ 증빙서류 제출 수동 처리")
    print(" 9. 📥 체크리스트 업데이트 파일 반영")
    print(" 10. 🧹 캐시 데이터 일괄 삭제")
    print("-" * 50)
    print(" 99. 🔐 [관리자] 새 학년도 시스템 진급 (초기화)")
    print(" 0. ❌ 종료")
    print("-" * 50)
    return input(" 메뉴 선택 > ").strip()

# ==========================================
# 메인 로직
# ==========================================
def main():
    while True:
        try:
            mode = get_menu_choice()
        except KeyboardInterrupt:
            print("\n 👋 강제 종료되었습니다.")
            break

        if mode == '0':
            print(" 👋 프로그램을 종료합니다.")
            break

        # ----------------------------------------------------------------------
        # [99번] 관리자 모드 (시스템 진급)
        # ----------------------------------------------------------------------
        if mode == '99':
            print("\n" + "!"*50)
            print(" 🔐 [관리자 모드] 새 학년도 시스템 진급")
            print("!"*50)
            
            pw = input(" 🔑 관리자 암호를 입력하세요: ")
            if pw != "school1234":
                print(" ❌ 암호가 틀렸습니다.")
                continue
                
            curr_year = config_manager.GLOBAL_CONFIG.get("target_year", 2025)
            print(f"\n 📅 현재 학년도: {curr_year}")
            
            try:
                new_year_in = input(f" 🆕 새 학년도 입력 (Enter for {curr_year+1}): ").strip()
                new_year = int(new_year_in) if new_year_in else curr_year + 1
                
                reset_yn = input(" 🗓️  공휴일 날짜도 초기화할까요? (y/n): ").lower()
                
                print("\n ⚠️ [경고] reports 폴더가 백업 후 초기화됩니다.")
                confirm = input(" 🚀 정말 진행하시겠습니까? (yes 입력): ")
                
                if confirm.lower() == "yes":
                    logs = admin_manager.run_new_year_reset(new_year, reset_yn=='y')
                    for log in logs: print(log)
                    print("\n ✅ 시스템 진급이 완료되었습니다. 재시작해주세요.")
                    break # 설정이 바뀌었으므로 프로그램 종료 후 재시작 유도
                else:
                    print(" ⛔ 취소되었습니다.")
            except Exception as e:
                print(f" ❌ 오류 발생: {e}")
            continue

        # ----------------------------------------------------------------------
        # [10번] 캐시 삭제
        # ----------------------------------------------------------------------
        if mode == '10':
            clear_all_cache()
            continue

        # ----------------------------------------------------------------------
        # [7번] 아침 알림
        # ----------------------------------------------------------------------
        if mode == '7':
            daily_bot.run_daily_checks()
            continue 

        # ----------------------------------------------------------------------
        # [8번] 서류 수동 처리
        # ----------------------------------------------------------------------
        if mode == '8':
            print("\n 📝 서류 제출 수동 처리")
            name = input("   학생 이름 > ").strip()
            date = input("   결석 날짜 (예: 11.05) > ").strip()
            if name and date:
                success, msg = checklist_gen.mark_submitted_manually(name, date)
                print(f"   {'✅' if success else '❌'} {msg}")
            else:
                print("   ❌ 입력이 올바르지 않습니다.")
            continue 

        # ----------------------------------------------------------------------
        # [9번] 체크리스트 DB 반영
        # ----------------------------------------------------------------------
        if mode == '9':
            # (기존 로직 유지 - 코드 길이상 핵심만 요약)
            print("\n 📥 업데이트 파일 스캔 중...")
            data_dir = os.path.join(REPORTS_DIR, "data")
            files = glob.glob(os.path.join(data_dir, "checklist_update_*.json"))
            
            if not files:
                print("   ℹ️ 반영할 파일이 없습니다.")
            else:
                count = 0
                import json, re
                for fpath in files:
                    try:
                        fname = os.path.basename(fpath)
                        match = re.search(r"_(\d{4})_(\d{2})", fname)
                        if match:
                            y, m = int(match.group(1)), int(match.group(2))
                            with open(fpath, "r", encoding="utf-8") as f: new_d = json.load(f)
                            cur_d = checklist_gen.load_status(m, y)
                            cur_d.update(new_d)
                            checklist_gen.save_status(m, cur_d, y)
                            
                            # 처리된 파일 이동
                            proc_dir = os.path.join(data_dir, "processed")
                            os.makedirs(proc_dir, exist_ok=True)
                            try: shutil.move(fpath, os.path.join(proc_dir, fname))
                            except: pass
                            
                            print(f"   ✅ {fname} 반영 완료")
                            count += 1
                    except Exception as e:
                        print(f"   ❌ {fname} 실패: {e}")
                print(f"   🎉 총 {count}개 파일 처리 완료")
            continue

        # ----------------------------------------------------------------------
        # [5번] 학사일정 업데이트
        # ----------------------------------------------------------------------
        if mode == '5':
            print("\n 📅 학사일정 업데이트를 시작합니다...")
            try:
                ssm = SchoolScheduleManager(year=curr_year)
                success, msg = ssm.connect_google_api()
                if success:
                    print(f" ✅ {msg}")
                    success, msg = ssm.open_spreadsheet()
                    if success:
                        print(f" ✅ {msg}")
                        worksheets = ssm.get_worksheets()
                        print("\n 📑 시트 목록:")
                        for i, ws in enumerate(worksheets):
                            print(f"   {i+1}. {ws.title}")
                        
                        choice = input("\n 파싱할 시트 번호 선택 (Enter=1) > ").strip()
                        idx = int(choice) - 1 if choice.isdigit() else 0
                        
                        if 0 <= idx < len(worksheets):
                            ssm.set_worksheet(worksheets[idx])
                            print(f"   👉 선택된 시트: {worksheets[idx].title}")
                            
                            success, msg = ssm.parse_all_data()
                            if success:
                                print(f" ✅ {msg}")
                                ssm.save_holidays_json()
                                ssm.save_calendar_csv('4') # 전체
                            else:
                                print(f" ❌ {msg}")
                        else:
                            print(" ❌ 잘못된 시트 번호입니다.")
                    else:
                        print(f" ❌ {msg}")
                else:
                    print(f" ❌ {msg}")
            except Exception as e:
                print(f" ❌ 실행 중 오류 발생: {e}")
            
            input("\n [Enter]를 누르면 메뉴로 돌아갑니다.")
            continue

        # ----------------------------------------------------------------------
        # [1~4번] 리포트 생성 그룹
        # ----------------------------------------------------------------------
        if mode in ['1', '2', '3', '4', '6']:
            targets = get_user_target_months()
            
            # 데이터 동기화 여부
            sync = input("\n ☁️  구글 시트 최신 데이터를 다운로드 할까요? (y/n) > ").lower()
            if sync == 'y':
                roster = data_loader.get_master_roster()
                data_loader.sync_all_data_batch(roster, target_months=targets)
            
            print("\n" + "="*30)
            print(" ▶ 작업 시작...")
            print("="*30)

            # [1] 기본 세트
            if mode == '1' or mode == '6':
                print("\n [1/4] 달력/월별/주간 리포트 생성...")
                calendar_gen.run_calendar(target_months=targets)
                monthly_report.run_monthly_reports(target_months=targets)
                weekly_gen.run_weekly(target_months=targets)
                checklist_gen.run_checklists(target_months=targets)

            # [2] 체험학습
            if mode == '2' or mode == '6':
                print("\n [2/4] 체험학습 통계...")
                fieldtrip_gen.run_fieldtrip_stats()

            # [3] 생리인정
            if mode == '3' or mode == '6':
                print("\n [3/4] 생리인정결석 체크...")
                menstrual_stats.run_menstrual_stats()

            # [4] 장기결석
            if mode == '4' or mode == '6':
                print("\n [4/4] 장기결석 관리...")
                absence_gen.run_long_term_absence()

            # [공통] 인덱스 갱신
            last_index = None
            if mode == '1' or mode == '6':
                print("\n 🔗 인덱스 페이지 갱신 중...")
                last_index = index_gen.run_monthly_index(target_months=targets)

            print("\n" + "="*50)
            print(" 🎉 모든 작업 완료!")
            print(f" 📂 저장 위치: {REPORTS_DIR}")
            
            if last_index and os.path.exists(last_index):
                webbrowser.open(f'file://{os.path.abspath(last_index)}')
            
            input("\n [Enter]를 누르면 메뉴로 돌아갑니다.")

if __name__ == "__main__":
    main()