import os
import re

# 프로젝트 루트 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 수정할 파일 목록 (자동으로 찾을 수도 있지만, 안전하게 지정합니다)
TARGET_FILES = [
    "main_controller.py",
    "daily_alert_system.py",
    "generate_checklist.py",
    "restore_from_html_to_gsheet.py",
    "universal_calendar_batch.py",
    "universal_fieldtrip_stats.py",
    "universal_long_term_absence.py",
    "universal_menstrual_stats.py",
    "universal_monthly_index.py",
    "universal_monthly_report_batch.py",
    "universal_weekly_summary_batch.py"
]

def fix_imports():
    print("🚀 [일괄 수정] data_loader Import 경로 업데이트 시작...")
    count = 0
    
    for filename in TARGET_FILES:
        # 파일이 루트에 있든 src/components에 있든 찾기 위해 전체 검색
        target_path = None
        
        # 1. 루트에서 찾기
        if os.path.exists(os.path.join(BASE_DIR, filename)):
            target_path = os.path.join(BASE_DIR, filename)
        # 2. src/components에서 찾기 (이미 옮겼을 수도 있으니)
        elif os.path.exists(os.path.join(BASE_DIR, "src", "components", filename)):
            target_path = os.path.join(BASE_DIR, "src", "components", filename)
        # 3. src/services에서 찾기
        elif os.path.exists(os.path.join(BASE_DIR, "src", "services", filename)):
            target_path = os.path.join(BASE_DIR, "src", "services", filename)
            
        if not target_path:
            print(f"   ⚠️ 파일 못 찾음 (패스): {filename}")
            continue

        # 파일 읽기
        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        original_content = content
        
        # ========================================================
        # [패턴 1] import data_loader -> from src.services import data_loader
        # (단, 이미 수정된 건 건드리지 않음)
        # ========================================================
        # "import data_loader"가 줄의 시작이거나 공백 뒤에 올 때
        content = re.sub(r"^(import data_loader)", r"from src.services import data_loader", content, flags=re.MULTILINE)
        
        # ========================================================
        # [패턴 2] from data_loader import ... -> from src.services.data_loader import ...
        # ========================================================
        content = re.sub(r"^(from data_loader import)", r"from src.services.data_loader import", content, flags=re.MULTILINE)

        # 변경사항 저장
        if content != original_content:
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"   ✅ 수정 완료: {filename}")
            count += 1
        else:
            print(f"   ℹ️ 변경 없음 (이미 최신): {filename}")

    print(f"\n🎉 총 {count}개 파일의 Import 구문이 'src.services'로 업데이트되었습니다.")

if __name__ == "__main__":
    fix_imports()