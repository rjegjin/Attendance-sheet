import json
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Set, Optional, Any, Union
from pathlib import Path

from src.paths import ROOT_DIR

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DateCalculator:
    """
    날짜 계산 및 휴일 처리를 담당하는 유틸리티 클래스
    - Singleton 패턴이 적용되지 않았으므로 인스턴스 생성 시 주의
    - 휴일 데이터 캐싱 기능 포함
    """

    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        """
        Args:
            project_root: 프로젝트 루트 경로 (deprecated, src.paths.ROOT_DIR 사용 권장)
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = ROOT_DIR
            
        self.holidays_cache: Dict[int, Set[str]] = {}

    def _load_holidays(self, year: int) -> Set[str]:
        """
        연도별 휴일 데이터를 로드하고 캐싱합니다.

        Args:
            year: 로드할 연도

        Returns:
            Set[str]: 'YYYY-MM-DD' 형식의 휴일 문자열 집합
        """
        if year in self.holidays_cache:
            return self.holidays_cache[year]
        
        filename = f"holidays_{year}.json"
        
        # 탐색 경로 우선순위:
        # 1. src.paths.ROOT_DIR
        # 2. self.project_root (인스턴스 생성 시 전달된 경우)
        # 3. ROOT_DIR/config
        
        candidate_paths = [
            ROOT_DIR / filename,
            self.project_root / filename,
            ROOT_DIR / "config" / filename
        ]

        holidays = set()
        loaded = False
        
        for path in candidate_paths:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        holidays = set(data.keys())
                    logger.debug(f"Loaded holidays from {path}")
                    loaded = True
                    break
                except Exception as e:
                    logger.error(f"Failed to load holidays from {path}: {e}")
        
        if not loaded:
            logger.warning(f"Holiday file for {year} not found. Assuming no holidays.")

        self.holidays_cache[year] = holidays
        return holidays

    def is_school_day(self, date_obj: Union[date, datetime]) -> bool:
        """
        해당 날짜가 등교일(평일이면서 공휴일이 아닌 날)인지 확인합니다.

        Args:
            date_obj: 확인할 날짜 객체

        Returns:
            bool: 등교일이면 True, 아니면 False
        """
        if isinstance(date_obj, datetime):
            date_obj = date_obj.date()
            
        if date_obj.weekday() >= 5: # 5: 토요일, 6: 일요일
            return False 
        
        holidays = self._load_holidays(date_obj.year)
        if date_obj.strftime("%Y-%m-%d") in holidays:
            return False
            
        return True

    def count_real_school_days(self, start_date: Union[date, datetime], end_date: Union[date, datetime]) -> int:
        """
        두 날짜 사이(시작일, 종료일 포함)의 실제 등교일 수를 계산합니다.

        Args:
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            int: 등교일 수
        """
        if isinstance(start_date, datetime): start_date = start_date.date()
        if isinstance(end_date, datetime): end_date = end_date.date()

        count = 0
        current = start_date
        while current <= end_date:
            if self.is_school_day(current):
                count += 1
            current += timedelta(days=1)
        return count

    def group_consecutive_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        [핵심 로직] 연속된 결석/조퇴 등의 이벤트를 하나로 묶고 실제 등교일 수를 계산합니다.
        중간에 휴일이 끼어있어도 논리적으로 연속되면 하나로 묶습니다 (Bridge 적용).

        Args:
            events: 이벤트 딕셔너리 리스트 (필수 키: 'name', 'raw_type', 'date' 또는 'start'/'end')

        Returns:
            List[Dict[str, Any]]: 그룹화된 이벤트 리스트
        """
        if not events: return []

        # 1. 데이터 정규화 및 유효성 검사
        sanitized_events = []
        for e in events:
            item = e.copy()
            # 'date' 키만 있는 경우 'start', 'end'로 확장
            if 'date' in item and 'start' not in item:
                item['start'] = item['date']
                item['end'] = item['date']
            
            # 필수 필드 확인
            if 'start' in item and 'name' in item:
                # datetime 객체라면 date로 변환
                if isinstance(item['start'], datetime): item['start'] = item['start'].date()
                if isinstance(item.get('end'), datetime): item['end'] = item['end'].date()
                
                sanitized_events.append(item)

        if not sanitized_events: return []

        # 2. 정렬 (이름 -> 시작일 순)
        sanitized_events.sort(key=lambda x: (x['name'], x['start']))

        grouped = []
        current = sanitized_events[0].copy()
        
        for i in range(1, len(sanitized_events)):
            next_event = sanitized_events[i]
            
            # 3. 분리 조건: 학생이 다르거나 결석 사유가 다르면 분리
            if (current['name'] != next_event['name']) or \
               (current.get('raw_type') != next_event.get('raw_type')):
                current['real_days'] = self.count_real_school_days(current['start'], current['end'])
                grouped.append(current)
                current = next_event.copy()
                continue
            
            # 4. 연속성 판단 (Gap 검사)
            # current['end'] 다음 날부터 next_event['start'] 전날까지가 모두 휴일이어야 연속으로 인정
            gap_start = current['end'] + timedelta(days=1)
            gap_end = next_event['start']
            
            is_connected = True
            
            if gap_start < gap_end:
                # 갭이 존재하는 경우: 사이의 모든 날짜가 등교일이 아니어야 함 (휴일이어야 함)
                check_date = gap_start
                while check_date < gap_end:
                    if self.is_school_day(check_date): 
                        is_connected = False # 평일(등교일)이 끼어있으면 연속 아님
                        break
                    check_date += timedelta(days=1)
            elif gap_start > gap_end:
                 # 데이터 순서가 꼬인 경우 (방어적 처리: 분리)
                is_connected = False

            if is_connected:
                # 기간 연장 (병합)
                current['end'] = next_event['end']
                
                # 메타데이터 병합 (필요 시 로직 추가)
                # 예: 비고란 합치기 등
            else:
                # 연결되지 않음 -> 현재 그룹 종료 및 저장
                current['real_days'] = self.count_real_school_days(current['start'], current['end'])
                grouped.append(current)
                current = next_event.copy()
        
        # 마지막 항목 처리
        current['real_days'] = self.count_real_school_days(current['start'], current['end'])
        grouped.append(current)
        
        return grouped
