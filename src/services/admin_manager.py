import os
import json
import shutil
from pathlib import Path

# 프로젝트 루트 경로 (상위 폴더로 2번 이동: src/services -> src -> root)
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_PATH = BASE_DIR / "config.json"
REPORTS_DIR = BASE_DIR / "reports"

def run_new_year_reset(new_year, reset_holidays=False):
    """
    새 학년도 준비를 위한 시스템 리셋 함수
    - reports 폴더 백업 및 초기화
    - config.json 연도 업데이트
    Returns: 실행 로그 리스트 (List[str])
    """
    logs = []
    logs.append(f"🚀 [시스템] {new_year}학년도 준비 작업을 시작합니다.")

    # 1. 기존 설정 확인
    old_year = 2025
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
                old_year = config.get("target_year", 2025)
        except:
            pass
    
    logs.append(f"📅 학년도 변경: {old_year} -> {new_year}")

    # 2. 리포트 폴더 백업 (Archiving)
    if REPORTS_DIR.exists():
        archive_name = f"reports_{old_year}_archive"
        archive_path = BASE_DIR / archive_name
        try:
            # shutil.make_archive는 확장자(.zip)를 자동으로 붙임
            shutil.make_archive(str(archive_path), 'zip', str(REPORTS_DIR))
            logs.append(f"📦 데이터 백업 완료: {archive_name}.zip")
            
            # 3. 리포트 폴더 내부 청소
            deleted_count = 0
            for root, dirs, files in os.walk(REPORTS_DIR):
                for file in files:
                    # .gitignore 등 숨김 파일이나 필수 파일은 제외할 수도 있음
                    if file == ".gitkeep": continue
                    try:
                        os.remove(os.path.join(root, file))
                        deleted_count += 1
                    except: pass
            logs.append(f"🧹 기존 리포트 파일 {deleted_count}개 삭제 완료")
            
        except Exception as e:
            logs.append(f"⚠️ 백업/삭제 중 오류 발생: {e}")
    else:
        logs.append("⚠️ reports 폴더가 없어 백업을 건너뜁니다.")

    # 4. Config 업데이트
    try:
        data = {}
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        
        data["target_year"] = int(new_year)
        
        # 공휴일 초기화 옵션
        if reset_holidays:
            # 기본적인 국경일 세팅 (음력 설날/추석 제외)
            data["holidays"] = [
                f"{new_year}-03-01", f"{new_year}-05-05", f"{new_year}-06-06",
                f"{new_year}-08-15", f"{new_year}-10-03", f"{new_year}-10-09",
                f"{new_year}-12-25"
            ]
            # 상세 정보 딕셔너리도 초기화
            data["holiday_details"] = {
                f"{new_year}-03-01": "3.1절", f"{new_year}-05-05": "어린이날",
                f"{new_year}-06-06": "현충일", f"{new_year}-08-15": "광복절",
                f"{new_year}-10-03": "개천절", f"{new_year}-10-09": "한글날",
                f"{new_year}-12-25": "성탄절"
            }
            logs.append("🗓️ 공휴일 목록이 기본값(국경일)으로 초기화되었습니다.")
            logs.append("   (설날, 추석, 재량휴업일은 config.json 또는 별도 파일에 추가해주세요)")

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
            
        logs.append("✅ config.json 설정 업데이트 완료")
        
    except Exception as e:
        logs.append(f"❌ 설정 저장 실패: {e}")
        return logs

    logs.append("\n🎉 모든 준비가 완료되었습니다! 잠시 후 시스템이 재시작됩니다.")
    return logs