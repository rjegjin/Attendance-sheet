import os
from src.services.data_loader import (
    ACADEMIC_MONTHS, 
    TARGET_YEAR
)
from src.paths import REPORTS_DIR

REPORT_ROOT = str(REPORTS_DIR)
INDEX_DIR = os.path.join(REPORT_ROOT, "index")
if not os.path.exists(INDEX_DIR): os.makedirs(INDEX_DIR)

def generate_monthly_index(month):
    if not os.path.exists(INDEX_DIR): os.makedirs(INDEX_DIR)
    year = TARGET_YEAR + 1 if month < 3 else TARGET_YEAR
    month_str = f"{month:02d}월"
    
    # [설정] 링크 경로 확인: ../monthly/ 폴더를 바라보도록 설정됨
    links = [
        {"name": "📅 학급 생활기록 달력", "path": f"../calendar/{month_str}_생활기록_달력.html"},
        {"name": "📊 월별 출결 상세 현황", "path": f"../monthly/{month_str}_월별출결현황.html"},
        {"name": "🏫 학급별 출결 통계 (Hover)", "path": f"../monthly/{month_str}_학급별현황.html"},
        {"name": "📑 주간 출결 요약", "path": f"../weekly/{month_str}_주간요약.html"},
        {"name": "✅ 증빙서류 체크리스트", "path": f"../checklist/{month_str}_증빙서류_체크리스트.html"},
        {"name": "🚌 연간 체험학습 통계 (국내/외)", "path": "../stats/연간_체크_체험학습통계.html"},
        {"name": "🩸 생리인정결석 규정 체크", "path": "../stats/생리인정결석_통계.html"},
        {"name": "📉 장기결석 경고 리포트 (New)", "path": "../stats/장기결석_경고리포트.html"}
    ]

    html = f"""<!DOCTYPE html><html lang="ko"><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{month_str} 통합 리포트</title>
    <style>
        body {{ font-family: 'Malgun Gothic', sans-serif; padding: 20px; background: #f0f2f5; }}
        .container {{ background: white; padding: 20px; border-radius: 12px; max-width: 500px; margin: auto; }}
        h1 {{ text-align: center; color: #1a73e8; margin-bottom: 20px; }}
        .link-card {{ 
            display: block; padding: 15px; margin: 10px 0;
            background: #fff; border: 1px solid #ddd; border-radius: 8px;
            text-decoration: none; color: #333; font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .link-card:active, .link-card:hover {{ background: #e8f0fe; border-color: #1a73e8; color: #1a73e8; }}
    </style></head><body>
    <div class="container">
        <h1>📁 {year}년 {month}월 통합 허브</h1>
        <div class="link-grid">"""

    for link in links:
        html += f'<a href="{link["path"]}" class="link-card">{link["name"]}</a>'

    html += "</div></div></body></html>"

    with open(out:=os.path.join(INDEX_DIR, f"{month_str}_통합_인덱스.html"), "w", encoding="utf-8") as f: f.write(html)
    return out

def run_monthly_index(target_months=None):
    if target_months is None: target_months = ACADEMIC_MONTHS
    for m in target_months: generate_monthly_index(m)
    print(f"    ✅ 통합 인덱스 갱신 완료!")