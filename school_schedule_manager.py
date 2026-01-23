import pandas as pd
import os
import re
import sys
from datetime import datetime, date

class ScheduleManager:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.target_file = None
        self.year = None
        self.raw_data = []
        
        # 엑셀의 요일별 컬럼 인덱스 (0부터 시작)
        # 구조: [날짜 열, 내용 열]
        self.WEEKDAY_COLUMNS = {
            '월': [3, 5],
            '화': [6, 8],
            '수': [9, 11],
            '목': [12, 14],
            '금': [15, 17]
        }

    def print_header(self):
        """CLI 헤더 출력"""
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\n" + "="*50)
        print("   🏫  학사일정 변환 매니저 (Excel ➔ Calendar)")
        print("="*50)

    def find_excel_file(self):
        """'학사일정'이 포함된 최신 엑셀 파일을 찾고 연도를 추출"""
        candidates = [f for f in os.listdir(self.base_dir) if f.endswith('.xlsx') and '학사일정' in f]
        
        if not candidates:
            print("\n❌ 현재 폴더에서 '학사일정' 엑셀 파일을 찾을 수 없습니다.")
            return False
        
        # 수정일 기준 최신 파일 선택
        candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        self.target_file = candidates[0]
        
        # 파일명에서 연도 추출 (예: 2026...)
        match = re.search(r'(\d{4})', self.target_file)
        if match:
            self.year = int(match.group(1))
        else:
            self.year = date.today().year
            print(f"⚠️ 연도 식별 불가. 올해({self.year})로 설정합니다.")
            
        print(f"\n📂 감지된 파일: [ {self.target_file} ]")
        print(f"📅 기준 연도  : [ {self.year}학년도 ]")
        return True

    def parse_excel(self):
        """엑셀 파싱 및 데이터 정제"""
        print("\n⏳ 엑셀 데이터를 정밀 분석 중입니다...", end='')
        
        try:
            # 헤더 없이 읽어서 인덱스로 접근
            df = pd.read_excel(self.target_file, header=None, engine='openpyxl')
        except Exception as e:
            print(f"\n❌ 파일 읽기 치명적 오류: {e}")
            return False

        # B열(Index 1) 월 정보 채우기 (Merge Cell 처리)
        df[1] = pd.to_numeric(df[1], errors='coerce')
        df[1] = df[1].ffill()

        self.raw_data = []
        count = 0

        # 행 단위 순회
        for idx, row in df.iterrows():
            if pd.isna(row[1]): continue # 월 정보 없으면 스킵
            
            month = int(row[1])
            # 1, 2월은 다음 해로 계산
            current_year = self.year if month >= 3 else self.year + 1
            
            # 요일별(월~금) 컬럼 순회
            for day_name, (date_col, event_col) in self.WEEKDAY_COLUMNS.items():
                val_date = row[date_col]
                val_event = row[event_col]
                
                # 데이터 유효성 1차 검사
                if pd.isna(val_date) or pd.isna(val_event): continue
                
                str_event = str(val_event).strip()
                # 시수(숫자만) 또는 nan 제외
                if not str_event or str_event.isdigit() or str_event.lower() == 'nan':
                    continue

                # --- [핵심] 날짜(일) 추출 로직 ---
                day_num = 0
                try:
                    # 1. 엑셀 날짜 객체인 경우
                    if isinstance(val_date, (datetime, date)):
                        day_num = val_date.day
                    # 2. 문자열/숫자인 경우
                    else:
                        str_date = str(val_date).strip()
                        if '-' in str_date: # 2026-03-02 형태
                            day_num = int(str_date.split('-')[-1].split(' ')[0])
                        else: # 그냥 '1', '2' 숫자 형태
                            day_num = int(float(str_date))
                except:
                    continue # 날짜 파싱 실패 시 건너뜀

                if day_num == 0: continue

                # 유효한 날짜인지 검증 (예: 2월 30일 방지)
                try:
                    final_date_str = date(current_year, month, day_num).strftime("%Y-%m-%d")
                except ValueError:
                    # 날짜 오류 발생 시 로그 남기고 건너뜀
                    # print(f"\n⚠️ 날짜 오류 무시됨: {current_year}년 {month}월 {day_num}일 ({str_event})")
                    continue

                # 이벤트 내용 정제 (줄바꿈 -> 공백)
                clean_event = str_event.replace('\n', ' ').strip()
                
                self.raw_data.append({
                    'date': final_date_str,
                    'subject': clean_event,
                    'grade_year': self.year
                })
                count += 1
        
        print(f" 완료!\n✅ 총 {count}개의 유효한 일정을 추출했습니다.")
        return True

    def filter_by_grade(self, content, target_grade):
        """학년별 필터링 로직"""
        if target_grade == 0: return True # 전체 학년
        
        # 학년별 키워드
        keywords = {
            1: ['1학년', '신입생', '①', '입학'],
            2: ['2학년', '②'],
            3: ['3학년', '졸업', '③', '진학']
        }
        
        # 텍스트에 포함된 학년 정보 수집
        found_grades = set()
        for g, k_list in keywords.items():
            for k in k_list:
                if k in content:
                    found_grades.add(g)
                    break
        
        # 학년 언급이 없으면 -> 공통 행사 (포함)
        if not found_grades:
            return True
        
        # 학년 언급이 있으면 -> 해당 학년이 포함되어야 함
        return target_grade in found_grades

    def generate_csv(self, choice):
        """CSV 파일 생성"""
        grade_map = {'1': 1, '2': 2, '3': 3, '4': 0}
        target = grade_map.get(choice)
        
        if target is None:
            print("⚠️ 잘못된 입력입니다.")
            return

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
            print(f"\n⚠️ {label} 대상 일정이 없습니다.")
        else:
            # utf-8-sig로 저장하여 엑셀/구글 호환성 확보
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"\n💾 [저장 완료] {filename}")
            print(f"   └─ 포함된 일정: {len(df)}건")

    def run(self):
        self.print_header()
        if not self.find_excel_file(): return
        if not self.parse_excel(): return
        
        while True:
            print("\n" + "-"*40)
            print(" 🎯 생성할 학사일정을 선택하세요")
            print("-"*40)
            print("  1. 1학년 일정 (공통 포함)")
            print("  2. 2학년 일정 (공통 포함)")
            print("  3. 3학년 일정 (공통 포함)")
            print("  4. 전체 학년 통합 일정")
            print("  Q. 종료 (Quit)")
            print("-"*40)
            
            choice = input(" 선택 >> ").strip().upper()
            
            if choice == 'Q':
                print("\n👋 프로그램을 종료합니다. 감사합니다!")
                break
            elif choice in ['1', '2', '3', '4']:
                self.generate_csv(choice)
            else:
                print("⚠️ 올바른 번호를 입력해주세요.")

if __name__ == "__main__":
    app = ScheduleManager()
    app.run()