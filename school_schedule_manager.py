import pandas as pd
import os
import re
import json
import sys
from datetime import datetime, date

class SchoolScheduleMaster:
    def __init__(self):
        self.base_dir = os.getcwd()
        self.target_file = None
        self.selected_sheet_name = None
        self.year = None 
        self.raw_data = [] 
        
        # 📌 [수정됨] 엑셀 컬럼 인덱스 재설정 (0부터 시작: A=0, B=1, C=2, D=3...)
        # 데이터 구조: [A:?, B:월, C:주, D:월날짜, E:월시수, F:월행사, G:화날짜...]
        self.WEEKDAY_COLUMNS = {
            '월': [3, 5],   # D열(날짜), F열(내용)
            '화': [6, 8],   # G열(날짜), I열(내용)
            '수': [9, 11],  # J열(날짜), L열(내용)
            '목': [12, 14], # M열(날짜), O열(내용)
            '금': [15, 17]  # P열(날짜), R열(내용)
        }

        # 📌 [휴일] 필터링 키워드
        self.HOLIDAY_INCLUDE = [
            "대체공휴일", "재량휴업", "개교기념일", 
            "어린이날", "석가탄신일", "부처님", "성탄절", 
            "현충일", "광복절", "추석", "개천절", "한글날", "신정", "구정", "설날",
            "선거", "수능", "공휴일", "방학"
        ]
        self.HOLIDAY_EXCLUDE = ["자치", "동아리", "방과후", "시업", "입학", "진단", "고사", "수업", "식", "회의"]

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def ask_for_year(self):
        today = date.today()
        default_year = today.year + 1 if today.month >= 10 else today.year
        print("📌 [1단계] 작업 기준 연도 설정")
        while True:
            user_input = input(f"👉 학년도 입력 (엔터 누르면 {default_year}년): ").strip()
            if not user_input:
                self.year = default_year
                break
            if user_input.isdigit() and len(user_input) == 4:
                self.year = int(user_input)
                break
            print("⚠️ 4자리 숫자로 입력해주세요 (예: 2026)")
        print(f"✅ 작업 연도 설정 완료: {self.year}학년도\n")

    def find_excel_file(self):
        print("📌 [2단계] 학사일정 엑셀 파일 찾기")
        candidates = [f for f in os.listdir(self.base_dir) if f.endswith('.xlsx') and '학사일정' in f and not f.startswith('~$')]
        if not candidates:
            print("❌ '학사일정' 엑셀 파일을 찾을 수 없습니다.")
            return False
        
        year_str = str(self.year)
        matched = [f for f in candidates if year_str in f]
        
        if matched:
            matched.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            self.target_file = matched[0]
            print(f"✅ '{year_str}'년도가 포함된 파일 발견: {self.target_file}")
        else:
            candidates.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            self.target_file = candidates[0]
            print(f"⚠️ 연도 일치 파일 없음. 최신 파일 선택: {self.target_file}")
        return True

    def select_sheet(self):
        try:
            xl = pd.ExcelFile(self.target_file, engine='openpyxl')
            sheets = xl.sheet_names
        except Exception as e:
            print(f"❌ 엑셀 파일 열기 실패: {e}")
            return False

        if len(sheets) == 1:
            self.selected_sheet_name = sheets[0]
            print(f"✅ 시트 자동 선택: '{self.selected_sheet_name}'")
            return True

        recommended_idx = 0
        for i, sheet in enumerate(sheets):
            if "전체" in sheet or "학사" in sheet:
                recommended_idx = i
                break

        print("\n" + "="*50)
        print(f" 📑 [3단계] 시트 선택 (추천: {recommended_idx+1}번)")
        print("="*50)
        for idx, sheet in enumerate(sheets):
            mark = "👈 추천" if idx == recommended_idx else ""
            print(f"  {idx + 1}. {sheet} {mark}")
        
        while True:
            choice = input("\n 번호 입력 (Enter = 추천 시트) >> ").strip()
            if not choice:
                self.selected_sheet_name = sheets[recommended_idx]
                return True
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(sheets):
                    self.selected_sheet_name = sheets[idx]
                    return True
            print(" ⚠️ 올바른 번호를 입력하세요.")

    def parse_real_date(self, val):
        """엑셀 날짜 값(datetime or String) 파싱"""
        if pd.isna(val): return None
        try:
            if isinstance(val, (datetime, date)):
                return val.strftime("%Y-%m-%d")
            s = str(val).strip()
            # 2026-03-02 형식
            if re.match(r'\d{4}-\d{2}-\d{2}', s):
                return s
            # 2026.03.02 형식
            if re.match(r'\d{4}\.\d{2}\.\d{2}', s):
                return s.replace('.', '-')
        except: pass
        return None

    def parse_all_data(self):
        print(f"\n⏳ '{self.selected_sheet_name}' 시트 데이터 분석 중 (디버그 모드)...")
        try:
            df = pd.read_excel(self.target_file, sheet_name=self.selected_sheet_name, header=None, engine='openpyxl')
        except Exception as e:
            print(f"❌ 데이터 읽기 실패: {e}")
            return False

        self.raw_data = []
        count = 0
        
        # [디버깅] 처음 10개 행의 핵심 컬럼 출력
        print("\n🔎 [데이터 미리보기 - 처음 10행]")
        print("   (D열=월요일날짜, F열=월요일행사)")
        print("-" * 60)
        
        debug_limit = 10
        debug_cnt = 0

        for idx, row in df.iterrows():
            # 컬럼 수 부족하면 패스
            if len(row) < 18: 
                continue

            # [디버깅 출력] 3월달 데이터가 시작될 즈음부터 출력
            # B열(Index 1)이 '3'이거나, D열(Index 3)이 날짜 형식이면 출력
            val_sample = row[3] # 월요일 날짜 추정 위치
            is_date = self.parse_real_date(val_sample) is not None
            
            if is_date and debug_cnt < debug_limit:
                # 월요일 데이터만 샘플로 출력
                val_mon_date = row[3]
                val_mon_event = row[5]
                print(f"   [Row {idx}] 월요일: {val_mon_date} | 행사: {val_mon_event}")
                debug_cnt += 1

            # 실제 파싱 로직
            for day_name, cols in self.WEEKDAY_COLUMNS.items():
                date_idx = cols[0]
                event_idx = cols[1]

                val_date = row[date_idx]
                val_event = row[event_idx]

                if pd.isna(val_event): continue
                event_name = str(val_event).strip()
                if not event_name or event_name == 'nan': continue

                date_str = self.parse_real_date(val_date)
                
                if date_str:
                    self.raw_data.append({
                        'date': date_str,
                        'subject': event_name.replace('\n', ' ').strip()
                    })
                    count += 1

        print("-" * 60)
        print(f"✅ 총 {count}개의 학사일정을 로드했습니다.")
        return True

    # =========================================================
    # 1. 휴일 추출 (JSON)
    # =========================================================
    def export_holidays_json(self):
        print("\n=== [1] 휴일 데이터 추출 (JSON) ===")
        holidays = {}
        
        for item in self.raw_data:
            name = item['subject']
            has_include = any(k in name for k in self.HOLIDAY_INCLUDE)
            has_exclude = any(k in name for k in self.HOLIDAY_EXCLUDE)
            
            if "방학" in name and "식" not in name:
                holidays[item['date']] = name
                continue

            if has_include and not has_exclude:
                holidays[item['date']] = name

        fixed = self.get_fixed_holidays()
        for k, v in fixed.items():
            if k not in holidays: holidays[k] = v
        
        if holidays:
            sorted_h = dict(sorted(holidays.items()))
            filename = f"holidays_{self.year}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(sorted_h, f, ensure_ascii=False, indent=4)
            print(f"💾 [저장 완료] {filename} ({len(holidays)}건)")
        else:
            print("⚠️ 추출된 휴일이 없습니다.")

    def get_fixed_holidays(self):
        y = self.year; ny = y + 1
        return {
            f"{y}-03-01": "3.1절", f"{y}-05-05": "어린이날", f"{y}-06-06": "현충일",
            f"{y}-08-15": "광복절", f"{y}-10-03": "개천절", f"{y}-10-09": "한글날",
            f"{y}-12-25": "성탄절", f"{ny}-01-01": "신정"
        }

    # =========================================================
    # 2. 캘린더 CSV 추출
    # =========================================================
    def export_calendar_csv(self):
        print("\n=== [2] 구글 캘린더용 CSV 추출 ===")
        print("대상 학년을 선택하세요:")
        print("1. 1학년  2. 2학년  3. 3학년  4. 전체학사일정")
        
        choice = input(">> ").strip()
        grade_map = {'1': 1, '2': 2, '3': 3, '4': 0}
        target = grade_map.get(choice)
        
        if target is None:
            print("⚠️ 잘못된 입력입니다.")
            return

        filtered_list = []
        for item in self.raw_data:
            is_target = True
            if target != 0:
                keywords = {
                    1: ['1학년','신입','①','입학','시업'], 
                    2: ['2학년','②'], 
                    3: ['3학년','졸업','③','진학']
                }
                found_grades = set()
                for g, k_list in keywords.items():
                    for k in k_list:
                        if k in item['subject']: found_grades.add(g)
                
                if found_grades and target not in found_grades:
                    is_target = False
            
            if is_target:
                filtered_list.append({
                    "Subject": item['subject'],
                    "Start Date": item['date'],
                    "All Day Event": "True",
                    "Description": f"{self.year}학년도 학사일정"
                })

        label = "전체학년" if target == 0 else f"{target}학년"
        filename = f"schedule_{self.year}_{label}.csv"
        
        if filtered_list:
            df = pd.DataFrame(filtered_list)
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            print(f"💾 [저장 완료] {filename} ({len(filtered_list)}건)")
        else:
            print("⚠️ 해당 조건의 데이터가 없습니다.")

    def run(self):
        self.clear_screen()
        print("📅 [학교 학사일정 마스터 도구 v4.0 (Debug)]")
        self.ask_for_year()
        if self.find_excel_file():
            if self.select_sheet():
                if self.parse_all_data():
                    while True:
                        print("\n[메인 메뉴]")
                        print("1. 휴일 데이터 추출 (.json)")
                        print("2. 캘린더 일정 추출 (.csv)")
                        print("Q. 종료")
                        cmd = input("\n메뉴 선택 >> ").strip().upper()
                        if cmd == '1': self.export_holidays_json()
                        elif cmd == '2': self.export_calendar_csv()
                        elif cmd == 'Q': break
                        else: print("잘못된 입력")

if __name__ == "__main__":
    app = SchoolScheduleMaster()
    app.run()