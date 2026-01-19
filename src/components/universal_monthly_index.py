import os
import sys
from jinja2 import Environment, FileSystemLoader

# 프로젝트 경로 설정
from src.services.data_loader import (
    ACADEMIC_MONTHS, 
    TARGET_YEAR
)
from src.paths import REPORTS_DIR, SRC_DIR

# 템플릿 환경 설정
TEMPLATE_DIR = os.path.join(SRC_DIR, "templates")
env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))

REPORT_ROOT = str(REPORTS_DIR)
INDEX_DIR = os.path.join(REPORT_ROOT, "index")
if not os.path.exists(INDEX_DIR): os.makedirs(INDEX_DIR)

def generate_monthly_index(month):
    """
    특정 월의 index.html을 생성합니다.
    Jinja2 템플릿을 사용하여 드롭다운 네비게이션이 포함된 HTML을 만듭니다.
    """
    current_year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
    month_str = f"{month:02d}월"
    
    # 1. 네비게이션 옵션 데이터 생성 (모든 월에 대한 링크 정보)
    nav_options = []
    for m in ACADEMIC_MONTHS:
        y = TARGET_YEAR + 1 if m < 3 else TARGET_YEAR
        # 같은 폴더(index/) 안에 있으므로 파일명만 적으면 됨
        nav_path = f"{m:02d}월_통합_인덱스.html"
        nav_options.append({
            "label": f"{y}년 {m}월",
            "path": nav_path,
            "current": (m == month)  # 현재 페이지인지 표시
        })

    # 2. 본문 링크 데이터 생성
    # (경로 주의: index.html은 reports/index/ 폴더에 있으므로, reports/monthly/ 로 가려면 ../monthly/ 가 필요함)
    links = [
        {"name": "📅 학급 생활기록 달력", "path": f"../calendar/{month_str}_생활기록_달력.html"},
        {"name": "📊 월별 출결 상세 현황", "path": f"../monthly/{month_str}_월별출결현황.html"},
        {"name": "🏫 학급별 출결 통계", "path": f"../monthly/{month_str}_학급별현황.html"},
        {"name": "📑 주간 출결 요약", "path": f"../weekly/{month_str}_주간요약.html"},
        {"name": "✅ 증빙서류 체크리스트", "path": f"../checklist/{month_str}_증빙서류_체크리스트.html"},
        {"name": "🚌 연간 체험학습 통계", "path": "../stats/연간_체크_체험학습통계.html"},
        {"name": "🩸 생리인정결석 통계", "path": "../stats/생리인정결석_통계.html"},
        {"name": "📉 장기결석 경고 리포트", "path": "../stats/장기결석_경고리포트.html"}
    ]

    # 3. 템플릿 렌더링
    try:
        template = env.get_template("monthly_index_template.html")
        html_content = template.render(
            year=current_year,
            month=month,
            month_str=month_str,
            nav_options=nav_options,
            links=links
        )
        
        # 4. 파일 저장
        output_path = os.path.join(INDEX_DIR, f"{month_str}_통합_인덱스.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        return output_path
        
    except Exception as e:
        print(f"❌ [Index] {month}월 인덱스 생성 실패: {e}")
        return None

def run_monthly_index(target_months=None):
    """
    지정된 월(또는 전체 학기)에 대해 인덱스 페이지를 일괄 갱신합니다.
    """
    if target_months is None: 
        target_months = ACADEMIC_MONTHS
        
    print(f"📂 [Index] 통합 인덱스 페이지 갱신 중... ({len(target_months)}개)")
    
    count = 0
    for m in target_months:
        if generate_monthly_index(m):
            count += 1
            
    print(f"    ✅ 총 {count}개 월별 인덱스 페이지 생성 완료!")

# 단독 실행 테스트
if __name__ == "__main__":
    run_monthly_index()