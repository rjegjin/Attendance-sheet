import pandas as pd
import os
import re
import sys
from datetime import datetime, date

class ScheduleManager:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.target_file = None
        self.selected_sheet_name = None
        self.year = None
        self.raw_data = []
        
        # 📌 컬럼 좌표 (월, 화, 수, 목, 금)
        self.WEEKDAY_COLUMNS = {
            '월': [3, 5],
            '화': [6, 8],
            '수': [9, 11],
            '목': [12, 14],
            '금': [15, 17]
        }

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def find_excel_file(self):
        candidates = [f for f in os.listdir(self.base_dir) if f.endswith('.xlsx') and '학사일정' in f]
        if not candidates:
            print("\n❌ '학사일정' 엑셀 파일을 찾을 수 없습니다.")
            return False
        
        candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        self.target_file = candidates[0]
        
        match = re.search(r'(\d{4})', self.target_file)
        self.year = int(match.group(1)) if match else date.today().year
        
        print(f"\n📂 감지된 파일: {self.target_file}")
        print(f"📅 목표 연도: {self.year}학년도 (이 연도로 강제 변환합니다)")
        return True

    def select_sheet(self):
        try:
            xl = pd.ExcelFile(self.target_file, engine='openpyxl')
            sheets = xl.sheet_names
        except Exception as e:
            print(f"❌ 시트 목록 로드 실패: {e}")
            return False

        print("\n" + "="*50)
        print(" 📑 [시트 선택] 데이터가 있는 시트를 선택하세요.")
        print("="*50)
        for idx, sheet in enumerate(sheets):
            print(f"  {idx + 1}. {sheet}")
        
        while True:
            try:
                choice = input("\n 번호 입력 >> ").strip()
                if not choice: continue
                idx = int(choice) - 1
                if 0 <= idx < len(sheets):
                    self.selected_sheet_name = sheets[idx]
                    print(f" ✅ 선택: '{self.selected_sheet_name}'")
                    return True
                else: print(" ⚠️ 올바른 번호를 입력하세요.")
            except ValueError: print(" ⚠️ 숫자를 입력하세요.")

    def extract_month(self, val):
        """월(Month) 추출: 텍스트든 숫자든 숫자만 반환"""
        if pd.isna(val): return None
        s = str(val).strip()
        match = re.search(r'(\d+)', s)
        return int(match.group(1)) if match else None

    def extract_visual_day(self, val):
        """
        [핵심 로직] PDF를 보듯이 '일(Day)' 숫자만 강제 추출
        - 2024-03-04 -> 4 리턴
        - 1900-01-05 -> 5 리턴
        - "5" -> 5 리턴
        """
        if pd.isna(val): return 0
        
        try:
            # 1. 엑셀 날짜 객체인 경우 (2024년이든 1900년이든 상관없이 Day만 가져옴)
            if isinstance(val, (datetime, date)):
                return val.day
            
            # 2. 텍스트나 숫자인 경우
            s = str(val).strip()
            if not s: return 0
            
            if '-' in s: # '2026-03-05' or '1900-01-05'
                # 구분자로 쪼개서 가장 마지막 숫자(일) 또는 그 앞(월)을 확인
                parts = re.split(r'[ -]', s)
                # 마지막 부분이 숫자면 Day로 간주
                if parts[-1].isdigit(): return int(parts[-1])
                # '05' 처럼 된 경우
                return int(parts[-1].split(' ')[0])
            else:
                # 그냥 숫자 '5', '5.0'
                return int(float(s))
        except:
            return 0

    def parse_excel(self):
        print("\n⏳ '시각적 데이터' 파싱 모드로 분석 중...")
        try:
            df = pd.read_excel(self.target_file, sheet_name=self.selected_sheet_name, header=None, engine='openpyxl')
        except Exception as e:
            print(f"❌ 오류: {e}")
            return False

        # 1. 월 정보 정제
        df[1] = df[1].apply(self.extract_month)
        df[1] = df[1].ffill()

        self.raw_data = []
        
        for idx, row in df.iterrows():
            if pd.isna(row[1]): continue
            
            month = int(row[1])
            # 1, 2월은 내년(2027)으로, 3~12월은 올해(2026)로 강제 고정
            target_year = self.year if month >= 3 else self.year + 1
            
            for day_name, cols in self.WEEKDAY_COLUMNS.items():
                val_date = row[cols[0]]
                val_event = row[cols[1]]

                # 행사 내용 없으면 패스
                if pd.isna(val_event): continue
                str_event = str(val_event).strip()
                if not str_event or str_event.isdigit() or str_event.lower() == 'nan': continue

                # [핵심] 엑셀에 적힌 연도 무시하고 '일(Day)'만 가져오기
                day_num = self.extract_visual_day(val_date)
                
                if day_num == 0: continue

                # [재조립] 우리가 원하는 연도(2026)와 결합
                try:
                    # 유효한 날짜인지 검증 (2월 30일 같은 오류 방지)
                    final_date = date(target_year, month, day_num).strftime("%Y-%m-%d")
                    
                    clean_subject = str_event.replace('\n', ' ').strip()
                    self.raw_data.append({
                        'date': final_date,
                        'subject': clean_subject,
                        'grade_year': self.year
                    })
                except ValueError:
                    # 날짜 생성 실패 (달력에 없는 날짜) -> 건너뜀
                    continue
        
        print(f"✅ 총 {len(self.raw_data)}개의 일정을 {self.year}년 달력에 맞춰 변환했습니다.")
        
        # [검증] 3월 첫째주 데이터 2개만 출력해서 확인
        print("\n🔎 [변환 결과 미리보기 - 3월]")
        preview_count = 0
        for item in self.raw_data:
            if item['date'].startswith(f"{self.year}-03") and preview_count < 2:
                print(f"   📅 {item['date']} : {item['subject']}")
                preview_count += 1
                
        return True

    def generate_csv(self, choice):
        grade_map = {'1': 1, '2': 2, '3': 3, '4': 0}
        target = grade_map.get(choice)
        if target is None: return

        filtered_data = []
        for item in self.raw_data:
            is_target = True
            if target != 0:
                keywords = {1: ['1학년','신입','①','입학','시업'], 2: ['2학년','②'], 3: ['3학년','졸업','③','진학']}
                found = set()
                for g, k_list in keywords.items():
                    for k in k_list:
                        if k in item['subject']: found.add(g)
                if found and target not in found: is_target = False
            
            if is_target:
                filtered_data.append({
                    "Subject": item['subject'],
                    "Start Date": item['date'],
                    "All Day Event": "True",
                    "Description": f"{self.year}학년도 학사일정"
                })

        label = "전체학년" if target == 0 else f"{target}학년"
        filename = f"schedule_{self.year}_{label}.csv"
        pd.DataFrame(filtered_data).to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"💾 저장 완료: {filename} ({len(filtered_data)}건)")

    def run(self):
        self.clear_screen()
        print("📅 학사일정 변환기 (시각적 파싱 모드)")
        
        if self.find_excel_file():
            if self.select_sheet():
                if self.parse_excel():
                    while True:
                        print("\n[메뉴] 1:1학년 2:2학년 3:3학년 4:전체 Q:종료")
                        c = input(">> ").upper()
                        if c == 'Q': break
                        if c in ['1','2','3','4']: self.generate_csv(c)

if __name__ == "__main__":
    ScheduleManager().run()