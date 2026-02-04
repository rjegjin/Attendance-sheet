import streamlit as st
import sys
import os
import shutil
import datetime
import json
import time

# --------------------------------------------------------------------------
# 1. PATH CONFIGURATION & SECRETS SETUP
# --------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

def create_file_from_secrets(filename, secret_key):
    """파일이 없을 때만 Secrets에서 생성"""
    file_path = os.path.join(BASE_DIR, filename)
    if os.path.exists(file_path): return

    if secret_key in st.secrets:
        try:
            data = dict(st.secrets[secret_key])
            if 'private_key' in data:
                data['private_key'] = data['private_key'].replace('\\n', '\n')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            print(f"✅ [System] {filename} 생성됨.")
        except Exception as e:
            print(f"❌ [Error] {filename} 생성 실패: {e}")

create_file_from_secrets('service_key.json', 'gcp_service_account')
create_file_from_secrets('config.json', 'app_config')

# --------------------------------------------------------------------------
# 2. IMPORT MODULES
# --------------------------------------------------------------------------
try:
    from src.services import data_loader
    from src.services import config_manager
    from src.paths import CACHE_DIR
    
    # UI Modules
    from src.ui import (
        dashboard,
        notification,
        monthly_report,
        fieldtrip,
        menstrual,
        absence,
        checklist,
        weekly_calendar,
        schedule_manager
    )
    
except ImportError as e:
    st.error(f"❌ 모듈 임포트 오류: {e}")
    st.stop()

# --------------------------------------------------------------------------
# 3. PAGE CONFIG & SESSION STATE INIT
# --------------------------------------------------------------------------
CURRENT_YEAR = config_manager.GLOBAL_CONFIG.get("target_year", 2025)

st.set_page_config(
    page_title=f"{CURRENT_YEAR}학년도 출결 관리",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# [State Persistence] 상태 보존을 위한 초기화 함수
def init_session_state():
    defaults = {
        'menu': "대시보드(Home)",
        'selected_months': [],
        # 각 기능별 실행 여부 상태 저장
        'monthly_report_done': False,
        'fieldtrip_done': False,
        'menstrual_done': False,
        'absence_done': False,
        'checklist_done': False,
        'weekly_calendar_done': False,
        'msg_input': ""
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session_state()

# --------------------------------------------------------------------------
# 4. HELPER FUNCTIONS
# --------------------------------------------------------------------------
def clear_cache_data():
    if os.path.exists(CACHE_DIR):
        try:
            for filename in os.listdir(CACHE_DIR):
                if filename in ['service_key.json', 'config.json']: continue
                file_path = os.path.join(CACHE_DIR, filename)
                if os.path.isfile(file_path): os.unlink(file_path)
                elif os.path.isdir(file_path): shutil.rmtree(file_path)
            st.toast("🧹 데이터 캐시 삭제 완료!", icon="✅")
            # 캐시 삭제 시 상태도 초기화
            keys_to_reset = ['monthly_report_done', 'fieldtrip_done', 'menstrual_done', 'absence_done', 'checklist_done', 'weekly_calendar_done']
            for k in keys_to_reset: st.session_state[k] = False
        except: pass

# --------------------------------------------------------------------------
# 5. SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.title(f"🏫 {CURRENT_YEAR}학년도\n출결 관리 시스템")
    st.markdown("---")
    
    def on_menu_change():
        st.session_state['menu'] = st.session_state._menu_selection

    menu_options = [
        "대시보드(Home)", 
        "🔔 알림 센터",
        "월별/학급별 리포트", 
        "교외체험학습 통계", 
        "생리인정결석 체크", 
        "장기결석 경고 관리", 
        "증빙서류 체크리스트", 
        "주간 요약 & 달력",
        "📅 학사일정 관리"
    ]
    
    # 메뉴 선택 (현재 상태 반영)
    if st.session_state['menu'] not in menu_options:
        st.session_state['menu'] = menu_options[0]

    st.radio("작업 선택", 
        menu_options,
        index=menu_options.index(st.session_state['menu']),
        key='_menu_selection',
        on_change=on_menu_change
    )
    
    st.markdown("---")
    
    # 연단위 일괄 선택 (Session State 연동)
    st.write("📅 **분석 대상 월 선택**")
    all_months = getattr(data_loader, 'ACADEMIC_MONTHS', [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2])
    
    # 현재 월 자동 선택 (기본값)
    now = datetime.datetime.now()
    default_month = [now.month] if now.month in all_months else [3]
    if not st.session_state['selected_months']:
        st.session_state['selected_months'] = default_month

    selected_months = st.multiselect(
        "월을 선택하세요", 
        all_months, 
        key='selected_months'
    )
    
    st.markdown("---")
    
    with st.expander("⚙️ 데이터 관리"):
        if st.button("🔄 데이터 새로고침 (캐시삭제)", use_container_width=True):
            clear_cache_data()
            time.sleep(0.5)
            st.rerun()

    st.divider()
    with st.expander("🔐 관리자 설정"):
        admin_pw = st.text_input("관리자 암호", type="password")
        if admin_pw == "school1234":
            st.success("인증됨")
            if st.button("🚀 시스템 진급 실행", type="primary"):
                # (관리자 로직 생략 - 필요시 추가)
                st.info("관리자 기능 실행")

# --------------------------------------------------------------------------
# 6. MAIN CONTENT ROUTER
# --------------------------------------------------------------------------
current_menu = st.session_state['menu']

if current_menu == "대시보드(Home)":
    dashboard.render(CURRENT_YEAR, all_months)

elif current_menu == "🔔 알림 센터":
    notification.render()

elif current_menu == "월별/학급별 리포트":
    monthly_report.render(selected_months)

elif current_menu == "교외체험학습 통계":
    fieldtrip.render()

elif current_menu == "생리인정결석 체크":
    menstrual.render()

elif current_menu == "장기결석 경고 관리":
    absence.render()

elif current_menu == "증빙서류 체크리스트":
    checklist.render(selected_months)

elif current_menu == "주간 요약 & 달력":
    weekly_calendar.render(selected_months)

elif current_menu == "📅 학사일정 관리":
    schedule_manager.render(CURRENT_YEAR)
