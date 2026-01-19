import os
from pathlib import Path

# [절대 좌표 설정]
# 이 파일은 src 폴더 안에 있으므로, 부모의 부모가 루트입니다.
ROOT_DIR = Path(__file__).resolve().parent.parent

# 1. 핵심 설정 파일 경로 (절대 경로)
SERVICE_KEY_PATH = ROOT_DIR / "service_key.json"
CONFIG_FILE_PATH = ROOT_DIR / "config.json"   # <--- 에러의 원인! 여기를 추가합니다.
HOLIDAYS_2025_PATH = ROOT_DIR / "holidays_2025.json"
HOLIDAYS_2026_PATH = ROOT_DIR / "holidays_2026.json"

# 2. 저장소 및 데이터베이스 경로
REPORTS_DIR = ROOT_DIR / "reports"
DATA_DIR = REPORTS_DIR / "data"               # 체크리스트 DB 위치
CACHE_DIR = ROOT_DIR / "cache"
SRC_DIR = ROOT_DIR / "src"

# 3. 안전장치: 필수 폴더 자동 생성
def ensure_directories():
    REPORTS_DIR.mkdir(exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)

# 테스트용 출력
if __name__ == "__main__":
    print(f"📍 프로젝트 루트: {ROOT_DIR}")
    print(f"🔑 키 파일 위치: {SERVICE_KEY_PATH}")
    print(f"⚙️ 설정 파일 위치: {CONFIG_FILE_PATH}")
    print(f"📊 리포트 디렉토리: {REPORTS_DIR}")
    print(f"💾 데이터 디렉토리: {DATA_DIR}")
    print(f"🗃️ 캐시 디렉토리: {CACHE_DIR}")
    