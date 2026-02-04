import json
import os
from pathlib import Path
import datetime

# 프로젝트 루트 경로 (data_loader.py와 동일한 방식으로 계산)
# 이 파일 위치: src/services/config_manager.py
# 루트 위치: ../../
BASE_DIR = Path(__file__).parent.parent.parent
CONFIG_FILE_PATH = BASE_DIR / "config.json"

def load_config():
    """
    config.json을 읽고, target_year에 맞는 holidays_XXXX.json을 자동으로 로드하여 병합합니다.
    """
    # 1. 기본값 설정 (안전장치)
    config = {
        "target_year": datetime.datetime.now().year,
        "school_name": "학교",
        "holidays": [],
        "holiday_details": {}
    }

    # 2. config.json 로드
    if CONFIG_FILE_PATH.exists():
        try:
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                config.update(loaded_config)
        except Exception as e:
            print(f"⚠️ [Config] config.json 로드 실패: {e}")

    # [New] Streamlit Secrets 우선 적용 (Override)
    # config.json이 있어도 secrets.toml의 내용이 더 우선순위를 가짐
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "app_config" in st.secrets:
            secrets_config = dict(st.secrets["app_config"])
            # 딕셔너리는 재귀적으로 업데이트되지 않으므로 주의 (1단계만 병합)
            config.update(secrets_config)
            print("🔒 [Config] Streamlit Secrets 설정을 우선 적용했습니다.")
    except ImportError:
        pass  # Streamlit 환경이 아니면 무시
    except Exception as e:
        print(f"⚠️ [Config] Secrets 로드 중 오류: {e}")

    # 3. 휴일 파일 동적 로드 (holidays_2025.json 등)
    target_year = config.get("target_year")
    
    # [New] 연도별 스프레드시트 URL 자동 매핑
    # config.json에 "spreadsheets": {"2025": "url1", "2026": "url2"} 형태가 있다면,
    # target_year에 맞는 URL을 "spreadsheet_url" 키로 승격시킴.
    spreadsheets_map = config.get("spreadsheets", {})
    str_year = str(target_year)
    
    if spreadsheets_map and str_year in spreadsheets_map:
        config["spreadsheet_url"] = spreadsheets_map[str_year]
        print(f"✅ [Config] {target_year}년도 시트 URL이 설정되었습니다.")
    elif "spreadsheet_url" not in config:
        # 매핑도 없고 단일 URL도 없으면 경고
        print(f"⚠️ [Config] {target_year}년도 시트 URL을 찾을 수 없습니다.")

    holiday_file = BASE_DIR / f"holidays_{target_year}.json"

    if holiday_file.exists():
        try:
            with open(holiday_file, 'r', encoding='utf-8') as f:
                holiday_data = json.load(f)
                
                # 기존 로직과의 호환성을 위해 리스트와 딕셔너리 모두 제공
                # (1) 날짜 리스트 (기존 data_loader 호환)
                config['holidays'] = list(holiday_data.keys())
                
                # (2) 상세 정보 (날짜: 이름)
                config['holiday_details'] = holiday_data
                
            print(f"✅ [Config] {target_year}년도 휴일 데이터 로드 완료 ({len(config['holidays'])}일)")
        except Exception as e:
            print(f"⚠️ [Config] 휴일 파일 로드 실패: {e}")
    else:
        print(f"ℹ️ [Config] 휴일 파일이 없습니다: {holiday_file.name}")

    return config

# [싱글톤 패턴] 이 변수를 import해서 쓰면 매번 파일을 읽지 않고 메모리에서 가져다 씀
GLOBAL_CONFIG = load_config()