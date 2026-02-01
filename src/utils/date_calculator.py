import os
import json
from datetime import timedelta

class DateCalculator:
    def __init__(self, project_root):
        self.project_root = project_root
        self.holidays_cache = {}

    def _load_holidays(self, year):
        """연도별 휴일 데이터 로드 (캐싱 적용)"""
        if year in self.holidays_cache:
            return self.holidays_cache[year]
        
        filename = f"holidays_{year}.json"
        # 프로젝트 루트 및 현재 경로 등에서 파일 탐색
        paths = [
            os.path.join(self.project_root, filename),
            os.path.join(self.project_root, "config", filename),
            filename
        ]

        holidays = set()
        for path in paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        holidays = set(data.keys())
                    break
                except Exception: pass
        
        self.holidays_cache[year] = holidays
        return holidays

    def is_school_day(self, date_obj):
        """학교 가는 날인가? (주말 X, 공휴일 X)"""
        if date_obj.weekday() >= 5: return False # 주말
        
        holidays = self._load_holidays(date_obj.year)
        if date_obj.strftime("%Y-%m-%d") in holidays: return False # 휴일
            
        return True

    def count_real_school_days(self, start_date, end_date):
        """기간 내 실제 수업일수 카운트"""
        count = 0
        current = start_date
        while current <= end_date:
            if self.is_school_day(current):
                count += 1
            current += timedelta(days=1)
        return count

    def group_consecutive_events(self, events):
        """
        [핵심] 연속된 기간 묶기 (휴일 Bridge 적용) + 실제 일수(real_days) 계산
        """
        if not events: return []

        # [Fix] 데이터 전처리: 'date'만 있는 Raw 데이터를 'start', 'end'로 정규화
        sanitized_events = []
        for e in events:
            item = e.copy()
            # 'date' 키가 있고 'start'가 없으면 start/end를 date로 설정
            if 'date' in item and 'start' not in item:
                item['start'] = item['date']
                item['end'] = item['date']
            
            # 최소한 start 정보는 있어야 처리 가능
            if 'start' in item:
                sanitized_events.append(item)

        if not sanitized_events: return []

        # 1. 정렬 (이름 -> 시작일)
        sanitized_events.sort(key=lambda x: (x['name'], x['start']))

        grouped = []
        current = sanitized_events[0].copy()
        
        for i in range(1, len(sanitized_events)):
            next_event = sanitized_events[i]
            
            # 2. 다른 학생이거나 사유가 다르면 분리
            if (current['name'] != next_event['name']) or \
               (current['raw_type'] != next_event['raw_type']):
                current['real_days'] = self.count_real_school_days(current['start'], current['end'])
                grouped.append(current)
                current = next_event.copy()
                continue
            
            # 3. 연속성 판단 (Gap 검사)
            gap_start = current['end'] + timedelta(days=1)
            gap_end = next_event['start']
            
            is_connected = True
            check_date = gap_start
            
            # 갭이 존재하는 경우에만 검사
            if gap_start < gap_end:
                while check_date < gap_end:
                    if self.is_school_day(check_date): # 평일이 끼어있으면 끊김
                        is_connected = False
                        break
                    check_date += timedelta(days=1)
            elif gap_start > gap_end:
                # 데이터가 꼬여서 순서가 뒤집힌 경우 (방어 코드)
                is_connected = False

            if is_connected:
                current['end'] = next_event['end'] # 기간 연장
                
                # (선택) 교시 정보 병합 (예: 1교시, 2교시 -> 1,2교시)
                # 여기서는 간단히 덮어쓰거나 유지
            else:
                current['real_days'] = self.count_real_school_days(current['start'], current['end'])
                grouped.append(current)
                current = next_event.copy()
        
        # 마지막 항목 처리
        current['real_days'] = self.count_real_school_days(current['start'], current['end'])
        grouped.append(current)
        
        return grouped