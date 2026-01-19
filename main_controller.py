import sys
import os
import shutil  # [New] 파일 삭제를 위한 모듈
import webbrowser 
import glob

# =========================================================
# [주소록 갱신] 이사 간 모듈들을 새로운 경로로 부릅니다.
# =========================================================

# 1. 심장 (Services)
from src.services import data_loader

# 2. 리포트 4대장 (Components)
from src.components import universal_monthly_report_batch as monthly_report
from src.components import universal_calendar_batch as calendar_gen
from src.components import universal_weekly_summary_batch as weekly_gen
from src.components import universal_monthly_index as index_gen

# 3. [NEW] 통계 및 도구 (새로 이사 온 친구들)
from src.components import generate_checklist as checklist_gen
from src.components import universal_fieldtrip_stats as fieldtrip_gen
from src.components import restore_from_html_to_gsheet as restore_tool
from src.components import universal_menstrual_stats as menstrual_stats
from src.components import universal_long_term_absence as absence_gen
from src.components import daily_alert_system as daily_bot

# 4. 경로 참조
from src.paths import CACHE_DIR

# ==========================================
# 유틸리티 함수: 캐시 삭제
# ==========================================
def clear_all_cache():
    print("\n 🧹 캐시 데이터를 정리하는 중...")
    if not os.path.exists(CACHE_DIR):
        print("   ℹ️ 캐시 폴더가 이미 비어있거나 존재하지 않습니다.")
        return

    try:
        # 폴더 내의 모든 파일 및 하위 폴더 삭제
        for filename in os.listdir(CACHE_DIR):
            file_path = os.path.join(CACHE_DIR, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"   ❌ 삭제 실패 ({filename}): {e}")
        
        print("   ✅ 모든 캐시 파일이 삭제되었습니다. (다음 실행 시 최신 데이터를 받아옵니다)")
    except Exception as e:
        print(f"   ❌ 캐시 폴더 정리 실패: {e}")

# ==========================================
# 사용자 입력 처리
# ==========================================
def get_user_target_months():
    print("-" * 50)
    print(" 🗓️  처리할 '월(Month)'을 선택하세요.")
    print("   [Enter] : 전체 (3월 ~ 2월)")
    print("   [숫자]  : 해당 월만 (예: 5)")
    print("   [쉼표]  : 여러 월 (예: 3, 5, 11)")
    print("-" * 50)
    
    val = input(" 선택 > ").strip()
    if not val: return None
    
    try:
        return [int(x.strip()) for x in val.split(',')]
    except ValueError:
        print(" ❌ 잘못된 입력입니다. 전체 월로 진행합니다.")
        return None

def get_menu_choice():
    print("\n" + "="*50)
    print(" 🏫 출결 관리 통합 시스템 (Main Controller)")
    print("="*50)
    print(" 1. 📄 [기본] 리포트 세트 생성 (달력, 월별, 주간, 체크리스트)")
    print(" 2. 🚌 [통계] 교외체험학습 연간 통계 분석")
    print(" 3. 🩸 [통계] 생리인정결석 규정 위반 체크")
    print(" 4. 📉 [통계] 장기결석 관리 (독촉 기준 체크)")
    print(" 5. ♻️ [복원] HTML 리포트 -> 구글 시트 원상 복구")
    print(" 6. 🚀 [전체] 모든 작업 일괄 수행 (1~4번)")
    print("-" * 50)
    print(" 7. 🌅 [매일] 아침 브리핑 & 알림 발송 (출결/생일/서류)")
    print(" 8. ✅ [서류] 증빙서류 제출 처리 (건별 수동)")
    print(" 9. 📥 [서류] 체크리스트 업데이트 파일 자동 반영")
    print(" 10. 🧹 [관리] 캐시 데이터 일괄 삭제 (초기화)")
    print(" 0. ❌ 프로그램 종료")
    print("-" * 50)
    return input(" 메뉴 선택 (0~10) > ").strip()

# ==========================================
# 메인 실행
# ==========================================
def main():
    while True:
        mode = get_menu_choice()

        if mode == '0':
            print(" 👋 프로그램을 종료합니다. 감사합니다.")
            break

        # [즉시 실행 그룹]
        if mode == '10':
            clear_all_cache()
            print("\n ↩️  메인 메뉴로 돌아갑니다.")
            continue

        if mode == '7':
            daily_bot.run_daily_checks()
            print("\n ↩️  메인 메뉴로 돌아갑니다.")
            continue 

        if mode == '8':
            print("\n 📝 서류 제출 처리할 학생 이름과 날짜를 입력하세요.")
            name = input("   학생 이름 > ").strip()
            date = input("   결석 날짜 (예: 11.05) > ").strip()
            
            if name and date:
                success, msg = checklist_gen.mark_submitted_manually(name, date)
                if success: print(f"   ✅ 처리 완료: {msg}")
                else: print(f"   ❌ 처리 실패: {msg}")
            else:
                print("   ❌ 이름과 날짜를 모두 입력해야 합니다.")
                
            print("\n ↩️  메인 메뉴로 돌아갑니다.")
            continue 
            
        # [메뉴 9번] 체크리스트 업데이트 파일 자동 반영
        if mode == '9':
            print("\n 📥 'reports/data' 폴더에서 업데이트 파일(JSON)을 스캔합니다...")
            
            base_dir = os.path.dirname(os.path.abspath(__file__))
            data_dir = os.path.join(base_dir, "reports", "data")
            processed_dir = os.path.join(data_dir, "processed_updates")
            
            if not os.path.exists(data_dir):
                print(f" ⚠️ 데이터 폴더가 없습니다: {data_dir}")
                continue

            pattern = os.path.join(data_dir, "checklist_update_*.json")
            files = glob.glob(pattern)
            
            if not files:
                print(" ℹ️  반영할 새로운 JSON 파일이 없습니다.")
            else:
                success_count = 0
                import time 
                import shutil 
                import re
                import json

                for file_path in files:
                    file_name = os.path.basename(file_path)
                    print(f"   📄 발견: {file_name}")
                    
                    try:
                        match = re.search(r"checklist_update_(\d{4})_(\d{2})", file_name)
                        if not match:
                            print(f"     ⚠️ 파일명 형식 불일치 (YYYY_MM 포함 필요)")
                            continue

                        year = int(match.group(1))
                        month = int(match.group(2))

                        with open(file_path, "r", encoding="utf-8") as f:
                            new_data = json.load(f)
                        
                        current = checklist_gen.load_status(month, year)
                        current.update(new_data)
                        checklist_gen.save_status(month, current, year)
                        
                        print(f"     ✅ 병합 완료 ({len(new_data)}건) -> {year}년 {month}월 DB")
                        success_count += 1
                        
                        os.makedirs(processed_dir, exist_ok=True)
                        dest_path = os.path.join(processed_dir, file_name)
                        
                        if os.path.exists(dest_path):
                            try: os.remove(dest_path)
                            except: pass
                        
                        move_success = False
                        for retry in range(3):
                            try:
                                time.sleep(0.5) 
                                shutil.move(file_path, dest_path)
                                move_success = True
                                print(f"     📦 파일 이동됨 -> processed_updates/")
                                break 
                            except PermissionError:
                                print(f"     ⏳ 파일 이동 대기 중... ({retry+1}/3)")
                        
                        if not move_success:
                            print("     ❌ [경고] 데이터는 반영되었으나, 원본 파일 이동에 실패했습니다.")

                    except Exception as e:
                        print(f"     ❌ 처리 실패: {e}")
                
                print(f"\n 🎉 총 {success_count}개의 파일이 데이터베이스에 반영되었습니다.")

            print("\n ↩️  메인 메뉴로 돌아갑니다.")
            continue

        if mode not in ['1', '2', '3', '4', '5', '6']:
             print(" ❌ 올바른 메뉴를 선택해주세요.")
             continue

        # [리포트 그룹]
        targets = get_user_target_months()

        if mode != '5':
            print("\n [질문] 구글 시트 최신 데이터를 다운로드 할까요?")
            sync = input("   (y/n) > ").strip().lower()
            roster = data_loader.get_master_roster()
            if sync == 'y':
                data_loader.sync_all_data_batch(roster, target_months=targets)
            else:
                print("   ⚡ 기존 캐시 데이터를 사용합니다.")
        else:
            print("\n ⚠️ [주의] 복원 모드는 'reports/month' 폴더의 HTML 파일을 사용합니다.")

        print("\n" + "="*30)
        print(" ▶ 작업 시작...")
        print("="*30)

        # [1] 기본 리포트 생성
        if mode in ['1', '6']:
            print("\n 📑 [1-1] 생활기록 달력 생성")
            calendar_gen.run_calendar(target_months=targets)
            print("\n 📑 [1-2] 월별/학급별 리포트 생성")
            monthly_report.run_monthly_reports(target_months=targets)
            print("\n 📑 [1-3] 주간 요약 리포트 생성")
            weekly_gen.run_weekly(target_months=targets)
            print("\n 📑 [1-4] 증빙서류 체크리스트 생성")
            checklist_gen.run_checklists(target_months=targets)

        # [2] 통계
        if mode in ['2', '6']:
            print("\n 📊 [2] 교외체험학습 통계 분석")
            fieldtrip_gen.run_fieldtrip_stats()

        if mode in ['3', '6']:
            print("\n 🩸 [3] 생리인정결석 규정 위반 체크")
            menstrual_stats.run_menstrual_stats()

        if mode in ['4', '6']:
            print("\n 📉 [4] 장기결석 관리 (독촉 기준 체크)")
            absence_gen.run_long_term_absence()

        if mode == '5':
            print("\n ♻️ [5] 구글 시트 복원 (HTML -> GSheet)")
            restore_tool.run_restore(target_months=targets)

        # [공통] 통합 인덱스 생성 및 자동 실행
        last_index_path = None
        if mode in ['1', '6']:
            print("\n 🔗 [Index] 월별 통합 인덱스 파일 갱신 중...")
            last_index_path = index_gen.run_monthly_index(target_months=targets)

        print("\n" + "="*50)
        print(" 🎉 모든 작업이 성공적으로 완료되었습니다!")
        print(f" 📂 결과 폴더: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')}")
        
        if last_index_path and os.path.exists(last_index_path):
            print(f" 🚀 결과 화면을 띄웁니다: {last_index_path}")
            webbrowser.open(f'file://{os.path.abspath(last_index_path)}')
            
        print("="*50)
        print("\n 메인 메뉴로 돌아갑니다.")

if __name__ == "__main__":
    main()