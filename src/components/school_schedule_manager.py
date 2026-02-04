import pandas as pd
import os
import re
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, date
from pathlib import Path
from src.paths import SERVICE_KEY_PATH, ROOT_DIR

class SchoolScheduleManager:
    def __init__(self, year=None):
        self.year = year or date.today().year
        self.key_path = SERVICE_KEY_PATH
        self.TARGET_SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1-aStuqYl_xtdJLaQLQh6TLuWPAQSU_8-kENxME4a0y8/edit?gid=1585887942#gid=1585887942"
        
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        self.raw_data = [] 
        
        # 📌 컬럼 좌표 (0부터 시작: A=0, B=1, C=2...)
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

    def connect_google_api(self, credentials_dict=None):
        """
        API 연결. Streamlit에서는 credentials_dict를 전달받아 사용할 수 있음.
        """
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            if credentials_dict:
                creds = ServiceAccountCredentials.from_json_keyfile_dict(credentials_dict, scope)
            else:
                if not os.path.exists(self.key_path):
                    return False, f"서비스 키 파일을 찾을 수 없습니다: {self.key_path}"
                creds = ServiceAccountCredentials.from_json_keyfile_name(self.key_path, scope)
            
            self.client = gspread.authorize(creds)
            return True, "Google API 인증 성공!"
        except Exception as e:
            return False, f"API 연결 실패: {e}"

    def open_spreadsheet(self, url=None):
        url = url or self.TARGET_SPREADSHEET_URL
        try:
            self.spreadsheet = self.client.open_by_url(url)
            return True, f"접속 성공: [{self.spreadsheet.title}]"
        except Exception as e:
            return False, f"시트 열기 실패: {e}"

    def get_worksheets(self):
        if not self.spreadsheet:
            return []
        return self.spreadsheet.worksheets()

    def set_worksheet(self, worksheet):
        self.worksheet = worksheet

    def extract_month(self, val):
        if not val: return None
        s = str(val).strip()
        match = re.search(r'(\d+)', s)
        if match:
            m = int(match.group(1))
            return m if 1 <= m <= 12 else None
        return None

    def parse_date_smart(self, val, month):
        if not val: return None
        s = str(val).strip()
        if not s: return None

        if re.match(r'^\d{4}-\d{2}-\d{2}$', s):
            return s
        
        clean_s = re.sub(r'[.\s/]+', '-', s).strip('-')
        if re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', clean_s):
            try:
                dt = datetime.strptime(clean_s, "%Y-%m-%d")
                return dt.strftime("%Y-%m-%d")
            except: pass

        if s.isdigit() and month is not None:
            day = int(s)
            month = int(month)
            target_year = self.year if month >= 3 else self.year + 1
            try:
                dt = date(target_year, month, day)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                return None
        return None

    def parse_all_data(self):
        if not self.worksheet:
            return False, "워크시트가 선택되지 않았습니다."
        try:
            raw_values = self.worksheet.get_all_values()
            df = pd.DataFrame(raw_values)
        except Exception as e:
            return False, f"데이터 로드 실패: {e}"

        if 1 < len(df.columns):
            df[1] = df[1].apply(lambda x: self.extract_month(x) if x else None)
            df[1] = df[1].ffill() 

        self.raw_data = []
        count = 0
        
        # 요일 순서 정의 (롤오버 감지용)
        weekday_order = ['월', '화', '수', '목', '금']

        for idx, row in df.iterrows():
            raw_month = row[1] if 1 < len(row) else None
            base_month = int(raw_month) if pd.notna(raw_month) else None
            
            if base_month is None: continue

            last_day_num = -1
            current_month_offset = 0

            for day_name in weekday_order:
                cols = self.WEEKDAY_COLUMNS[day_name]
                date_idx = cols[0]
                event_idx = cols[1]

                if date_idx >= len(row) or event_idx >= len(row): continue
                
                val_date = row[date_idx]
                val_event = row[event_idx]

                # 날짜 숫자가 있는지 확인
                day_match = re.search(r'(\d+)', str(val_date))
                if not day_match: continue
                
                current_day_num = int(day_match.group(1))

                # 롤오버 감지: 이전 요일의 날짜보다 현재 날짜가 작으면 다음 달로 간주
                if last_day_num != -1 and current_day_num < last_day_num:
                    current_month_offset += 1
                
                last_day_num = current_day_num

                if not val_event: continue
                event_name = str(val_event).strip()
                if not event_name: continue

                # 실제 계산될 월 계산 (12월에서 1월로 넘어가는 경우 등 처리)
                calc_month = base_month + current_month_offset
                while calc_month > 12:
                    calc_month -= 12

                date_str = self.parse_date_smart(val_date, calc_month)
                
                if date_str:
                    self.raw_data.append({
                        'date': date_str,
                        'subject': event_name.replace('\n', ' ').strip()
                    })
                    count += 1

        return True, f"총 {count}개의 학사일정을 복원했습니다."

    def get_fixed_holidays(self):
        y = self.year; ny = y + 1
        return {
            f"{y}-03-01": "3.1절", f"{y}-05-05": "어린이날", f"{y}-06-06": "현충일",
            f"{y}-08-15": "광복절", f"{y}-10-03": "개천절", f"{y}-10-09": "한글날",
            f"{y}-12-25": "성탄절", f"{ny}-01-01": "신정"
        }

    def save_holidays_json(self):
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
            file_path = ROOT_DIR / filename
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(sorted_h, f, ensure_ascii=False, indent=4)
            return True, f"💾 [저장 완료] {filename} ({len(holidays)}건)"
        else:
            return False, "⚠️ 추출된 휴일이 없습니다."

    def save_calendar_csv(self, grade_choice='4'):
        """
        grade_choice: '1', '2', '3', '4'(전체)
        """
        grade_map = {'1': 1, '2': 2, '3': 3, '4': 0}
        target = grade_map.get(grade_choice, 0)
        
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
        file_path = ROOT_DIR / filename
        
        if filtered_list:
            df = pd.DataFrame(filtered_list)
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            return True, f"💾 [저장 완료] {filename} ({len(filtered_list)}건)"
        else:
            return False, "⚠️ 해당 조건의 데이터가 없습니다."
