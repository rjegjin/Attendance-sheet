import pandas as pd
import os
import re
import json
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date

class SchoolScheduleMasterGSheet:
    def __init__(self):
        self.base_dir = os.getcwd()
        
        # [수정 1] 서비스 키 경로: 루트 폴더
        self.key_path = os.path.join(self.base_dir, "service_key.json")
        
        # [수정 2] 구글 시트 URL 하드코딩
        self.TARGET_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1-aStuqYl_xtdJLaQLQh6TLuWPAQSU_8-kENxME4a0y8/edit?gid=1585887942#gid=1585887942"
        
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self.year = None 
        self.raw_data = [] 
        
        # 📌 컬럼 좌표 (0부터 시작: A=0, B=1, C=2...)
        # B열(1)이 '월' 정보라고 가정하고, 이를 이용해 날짜를 복원합니다.
        self.WEEKDAY_COLUMNS = {
            '월': [3, 5],   # D열(날짜), F열(내용)
            '화': [6, 8],   # G열(날짜), I열(내용)
            '수': [9, 11],  # J열(날짜), L열(내용)
            '목': [12, 14], # M열(날짜), O열(내용)
            '금': [15, 17]  # P열(날짜), R열(내용)
        }

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

    def connect_google_api(self):
        print("📌 [2단계] Google Sheets API 연결 중...")
        if not os.path.exists(self.key_path):
            print(f"❌ 서비스 키 파일을 찾을 수 없습니다: {self.key_path}")
            return False
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(self.key_path, scope)
            self.client = gspread.authorize(creds)
            print("✅ Google API 인증 성공!")
            return True
        except Exception as e:
            print(f"❌ API 연결 실패: {e}")
            return False

    def open_spreadsheet(self):
        print("\n📌 [3단계] 구글 스프레드시트 접속")
        print(f"   URL: {self.TARGET_SPREADSHEET_URL}")
        try:
            print("⏳ 스프레드시트에 접속 중...")
            self.spreadsheet = self.client.open_by_url(self.TARGET_SPREADSHEET_URL)
            print(f"✅ 접속 성공: [{self.spreadsheet.title}]")
            return True
        except Exception as e:
            print(f"❌ 시트 열기 실패: {e}")
        return False

    def select_worksheet(self):
        worksheets = self.spreadsheet.worksheets()
        if not worksheets: return False

        print("\n" + "="*50)
        print(f" 📑 [4단계] 시트(탭) 선택 (총 {len(worksheets)}개)")
        print("="*50)
        
        recommended_idx = 0
        for i, ws in enumerate(worksheets):
            if "전체" in ws.title or "학사" in ws.title:
                recommended_idx = i
                break

        for idx, ws in enumerate(worksheets):
            mark = "👈 추천" if idx == recommended_idx else ""
            print(f"  {idx + 1}. {ws.title} {mark}")
        
        while True:
            choice = input("\n 번호 입력 (Enter = 추천 시트) >> ").strip()
            if not choice:
                self.worksheet = worksheets[recommended_idx]
                break
            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(worksheets):
                    self.worksheet = worksheets[idx]
                    break
        print(f"✅ 선택된 시트: '{self.worksheet.title}'")
        return True

    def extract_month(self, val):
        """B열(Index 1) 값에서 월(Month) 숫자 추출"""
        if not val: return None
        s = str(val).strip()
        # "3월", "3", "03" 등에서 숫자만 추출
        match = re.search(r'(\d+)', s)
        if match:
            m = int(match.group(1))
            return m if 1 <= m <= 12 else None
        return None

    def parse_date_smart(self, val, month):
        """
        [핵심] 값(val)과 월(month) 정보를 조합하여 'YYYY-MM-DD' 문자열 생성
        """
        if not val: return None
        s = str(val).strip()
        if not s: return None

        # 1. 이미 완전한 날짜 포맷인 경우 (2026-03-03)
        if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
            return s
        
        # 2. 날짜 파싱 시도 (2026.3.3 etc)
        clean_s = re.sub(r'[.\s/]+', '-', s).strip('-')
        if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', clean_s):
            try:
                dt = datetime.strptime(clean_s, "%Y-%m-%d")
                return dt.strftime("%Y-%m-%d")
            except: pass

        # 3. 숫자만 있는 경우 ("3" -> 3일) 복원 로직
        # month 정보가 있어야 복원 가능
        if s.isdigit() and month is not None:
            day = int(s)
            
            # [Fix] month가 float(3.0)으로 들어올 경우 int(3)으로 변환
            month = int(month)
            
            # 학년도 로직: 3월~12월은 self.year, 1월~2월은 self.year + 1
            target_year = self.year if month >= 3 else self.year + 1
            
            try:
                # 유효한 날짜인지 검증 (예: 2월 30일 방지)
                dt = date(target_year, month, day)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None
                
        return None

    def parse_all_data(self):
        print(f"\n⏳ '{self.worksheet.title}' 데이터 분석 및 복원 중...")
        try:
            raw_values = self.worksheet.get_all_values()
            df = pd.DataFrame(raw_values)
        except Exception as e:
            print(f"❌ 데이터 로드 실패: {e}")
            return False

        # [Logic] B열(Index 1)에서 월 정보 추출 및 채우기 (Forward Fill)
        # B열이 비어있으면 None으로 바꾸고 ffill로 채움 (엑셀 병합 셀 효과)
        if 1 < len(df.columns):
            df[1] = df[1].apply(lambda x: self.extract_month(x) if x else None)
            df[1] = df[1].ffill() 

        self.raw_data = []
        count = 0
        
        print("\n🔎 [파싱 로그] (날짜 복원 과정)")
        debug_limit = 5
        debug_count = 0

        for idx, row in df.iterrows():
            # 현재 행의 월 정보 가져오기
            # [Fix] Pandas가 NaN 때문에 float으로 변환했을 수 있으므로 int로 안전하게 변환
            raw_month = row[1] if 1 < len(row) else None
            current_month = int(raw_month) if pd.notna(raw_month) else None
            
            for day_name, cols in self.WEEKDAY_COLUMNS.items():
                date_idx = cols[0]
                event_idx = cols[1]

                if date_idx >= len(row) or event_idx >= len(row): continue
                
                val_date = row[date_idx]
                val_event = row[event_idx]

                if not val_event: continue
                event_name = str(val_event).strip()
                if not event_name: continue

                # 스마트 파싱 (숫자만 있어도 복원 가능)
                date_str = self.parse_date_smart(val_date, current_month)
                
                # 디버깅 출력
                if debug_count < debug_limit:
                    status = "✅" if date_str else "❌"
                    # print(f"   [{day_name}] 값:'{val_date}'(월:{current_month}) -> {date_str} | {event_name[:5]}... {status}")
                    if not date_str and val_date:
                        print(f"   ⚠️ 복원 실패: 월={current_month}, 값='{val_date}'")
                        debug_count += 1
                
                if date_str:
                    self.raw_data.append({
                        'date': date_str,
                        'subject': event_name.replace('\n', ' ').strip()
                    })
                    count += 1

        print("-" * 60)
        print(f"✅ 총 {count}개의 학사일정을 완벽하게 복원했습니다.")
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
        print("📅 [학교 학사일정 마스터 (Google Sheets 버전)]")
        print("-" * 50)
        
        self.ask_for_year()
        if self.connect_google_api():
            if self.open_spreadsheet():
                if self.select_worksheet():
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
    app = SchoolScheduleMasterGSheet()
    app.run()