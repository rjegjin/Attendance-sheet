import pdfplumber
import pandas as pd
import os
import re
import sys
from datetime import date

class PDFScheduleManager:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.target_file = None
        self.year = 2026  # 기본값 2026년 고정
        self.raw_data = []

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_header(self):
        self.clear_screen()
        print("\n" + "="*60)
        print("       📄  학사일정 PDF 변환 매니저 (Visual Parser)")
        print("="*60)

    def find_pdf_file(self):
        """현재 폴더에서 '학사일정'이 포함된 PDF 파일을 찾습니다."""
        candidates = [f for f in os.listdir(self.base_dir) if f.endswith('.pdf') and '학사일정' in f]
        
        if not candidates:
            print("\n❌ 현재 폴더에서 '학사일정' PDF 파일을 찾을 수 없습니다.")
            return False
        
        # 최신 파일 선택
        candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        self.target_file = candidates[0]
        
        # 파일명에서 연도 추출 시도
        match = re.search(r'(\d{4})', self.target_file)
        if match:
            self.year = int(match.group(1))
            
        print(f"\n📂 감지된 파일: {self.target_file}")
        print(f"📅 목표 연도  : {self.year}학년도 (PDF 내용을 이 연도에 매핑합니다)")
        return True

    def clean_text(self, text):
        """줄바꿈이나 불필요한 공백 제거"""
        if text is None: return ""
        return str(text).replace('\n', ' ').strip()

    def extract_day_number(self, text):
        """
        PDF 셀에 있는 텍스트에서 '일(Day)' 숫자만 추출
        예: "3" -> 3, "3(화)" -> 3, "03" -> 3
        """
        if not text: return 0
        # 숫자만 찾기
        match = re.search(r'^(\d+)', str(text).strip())
        if match:
            return int(match.group(1))
        return 0

    def parse_pdf(self):
        print("\n⏳ PDF의 표(Table) 구조를 분석 중입니다...")
        
        try:
            pdf = pdfplumber.open(self.target_file)
        except Exception as e:
            print(f"❌ PDF 열기 실패: {e}")
            return False

        all_rows = []
        
        # 모든 페이지에서 표 추출
        for page in pdf.pages:
            # table_settings: 수직선과 수평선을 기준으로 셀을 나눔
            tables = page.extract_tables()
            for table in tables:
                all_rows.extend(table)
        
        print(f"   └─ 총 {len(all_rows)}개의 행(Row)을 발견했습니다.")
        
        self.raw_data = []
        current_month = None
        
        # PDF 표 구조 추정 (일반적인 학사일정 표 구조)
        # Index 0: 월
        # Index 1: 주
        # Index 2: 월-날짜 / Index 3: 월-행사
        # Index 4: 화-날짜 / Index 5: 화-행사
        # ...
        
        # 유효한 데이터 행인지 판단하기 위한 최소 컬럼 수
        MIN_COLS = 12 

        for row in all_rows:
            # None 값을 빈 문자열로 치환
            row = [self.clean_text(cell) for cell in row]
            
            # 컬럼 수가 너무 적으면(헤더나 기타 정보) 패스
            if len(row) < MIN_COLS: continue
            
            # 1. 월(Month) 추출 (Forward Fill 로직 적용)
            month_text = row[0]
            if month_text.isdigit():
                current_month = int(month_text)
            
            # 월 정보가 아직 없거나, 유효하지 않으면 패스
            if current_month is None: continue
            
            # 학사일정 연도 계산 (3월~12월: 2026, 1월~2월: 2027)
            target_year = self.year if current_month >= 3 else self.year + 1

            # 2. 요일별 데이터 추출 (월~금)
            # (날짜인덱스, 행사인덱스) 쌍
            # 주의: PDF 추출 시 컬럼 인덱스는 엑셀과 다를 수 있으나, 보통 순서대로 나열됨
            # 월(2,3), 화(4,5), 수(6,7), 목(8,9), 금(10,11) -> 표 구조에 따라 조정 가능성 있음
            # [진단] 3월 첫주 데이터를 통해 인덱스 확인 필요. 일단 표준 구조로 시도.
            day_pairs = [
                (2, 3), # 월
                (4, 5), # 화
                (6, 7), # 수
                (8, 9), # 목
                (10, 11) # 금
            ]

            for date_idx, event_idx in day_pairs:
                # 인덱스 범위 초과 방지
                if event_idx >= len(row): continue

                date_text = row[date_idx]
                event_text = row[event_idx]

                # 날짜가 없거나 행사가 없으면 패스
                if not date_text and not event_text: continue
                
                # 시수(숫자만 있는 행사) 필터링
                if event_text.isdigit(): continue

                # 날짜 숫자 추출
                day = self.extract_day_number(date_text)
                if day == 0: continue

                # 유효한 날짜 생성
                try:
                    final_date = date(target_year, current_month, day).strftime("%Y-%m-%d")
                    
                    # 데이터 저장
                    self.raw_data.append({
                        'date': final_date,
                        'subject': event_text,
                        'grade_year': self.year
                    })
                except ValueError:
                    continue # 2월 30일 등 존재하지 않는 날짜 무시

        print(f"✅ 분석 완료! 총 {len(self.raw_data)}개의 유효한 일정을 추출했습니다.")
        
        # [검증용] 3월 데이터 미리보기
        print("\n🔎 [검증] 3월 초기 데이터 미리보기:")
        count = 0
        for item in self.raw_data:
            if item['date'].startswith(f"{self.year}-03") and count < 3:
                print(f"   📅 {item['date']} : {item['subject']}")
                count += 1
                
        return True

    def filter_by_grade(self, content, target_grade):
        if target_grade == 0: return True
        
        keywords = {
            1: ['1학년', '신입', '①', '입학', '시업'],
            2: ['2학년', '②'],
            3: ['3학년', '졸업', '③', '진학']
        }
        
        found = set()
        for g, k_list in keywords.items():
            for k in k_list:
                if k in content:
                    found.add(g)
                    break
        
        if not found: return True # 공통 행사
        return target_grade in found

    def generate_csv(self, choice):
        grade_map = {'1': 1, '2': 2, '3': 3, '4': 0}
        target = grade_map.get(choice)
        if target is None: return

        filtered_data = []
        for item in self.raw_data:
            if self.filter_by_grade(item['subject'], target):
                filtered_data.append({
                    "Subject": item['subject'],
                    "Start Date": item['date'],
                    "All Day Event": "True",
                    "Description": f"{self.year}학년도 학사일정"
                })

        label = "전체학년" if target == 0 else f"{target}학년"
        filename = f"schedule_{self.year}_{label}.csv"
        
        df = pd.DataFrame(filtered_data)
        if df.empty:
            print(f"\n⚠️ {label} 일정이 없습니다.")
        else:
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 [저장 완료] {filename} ({len(df)}건)")

    def run(self):
        self.print_header()
        if self.find_pdf_file():
            if self.parse_pdf():
                while True:
                    print("\n" + "-"*40)
                    print(" [PDF 변환 메뉴]")
                    print(" 1. 1학년  2. 2학년  3. 3학년  4. 전체  Q. 종료")
                    print("-" * 40)
                    c = input(" >> ").upper()
                    if c == 'Q': break
                    if c in ['1','2','3','4']: self.generate_csv(c)

if __name__ == "__main__":
    PDFScheduleManager().run()