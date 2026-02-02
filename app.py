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
    from src.services import admin_manager
    from src.services import universal_notification
    from src.paths import REPORTS_DIR, CACHE_DIR
    
    from src.components import universal_monthly_report_batch as monthly_gen
    from src.components import universal_fieldtrip_stats as fieldtrip_gen
    from src.components import universal_menstrual_stats as menstrual_gen
    from src.components import universal_long_term_absence as absence_gen
    from src.components import generate_checklist as checklist_gen
    from src.components import universal_weekly_summary_batch as weekly_gen
    from src.components import universal_calendar_batch as calendar_gen
    from src.components import daily_alert_system as daily_bot
    
    try:
        from src.components import universal_monthly_index as index_gen
    except ImportError:
        index_gen = None
    
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

def display_html_report(file_path, height=800):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        fname = os.path.basename(file_path)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button(f"📥 {fname} 다운로드", html, fname, "text/html")
        
        st.components.v1.html(html, height=height, scrolling=True)
    else:
        st.info(f"ℹ️ 생성된 리포트가 없습니다. 먼저 '생성/분석 실행' 버튼을 눌러주세요.\n(경로: {os.path.basename(file_path)})")

def set_page(page_name):
    st.session_state['menu'] = page_name

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
        "주간 요약 & 달력"
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
# 6. MAIN CONTENT
# --------------------------------------------------------------------------
current_menu = st.session_state['menu']

# ==========================================
# 🏠 대시보드 (Home)
# ==========================================
if current_menu == "대시보드(Home)":
    st.header(f"👋 {CURRENT_YEAR}학년도 출결 관리 대시보드")
    
    # 상단 요약 지표
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric(label="총 학생 수", value=f"{len(data_loader.get_master_roster())}명")
    with col_b:
        st.metric(label="오늘 날짜", value=datetime.date.today().strftime("%Y-%m-%d"))
    with col_c:
        st.metric(label="설정된 휴일", value=f"{len(config_manager.GLOBAL_CONFIG.get('holidays', []))}일")
    
    st.divider()

    # [New] 대시보드 탭 구성
    tab_links, tab_weekly, tab_calendar = st.tabs(["🚀 바로가기 메뉴", "📅 이번 주 요약 (미리보기)", "🗓️ 이번 달 달력 (미리보기)"])

    # 1. 바로가기 메뉴 탭
    with tab_links:
        st.markdown("#### ⚡ 자주 쓰는 기능")
        row1_1, row1_2, row1_3 = st.columns(3)
        row2_1, row2_2, row2_3 = st.columns(3)
        
        row1_1.button("📑 월별/학급별 리포트", use_container_width=True, type="primary", on_click=set_page, args=("월별/학급별 리포트",))
        row1_2.button("🚌 교외체험학습 통계", use_container_width=True, on_click=set_page, args=("교외체험학습 통계",))
        row1_3.button("🩸 생리인정결석 체크", use_container_width=True, on_click=set_page, args=("생리인정결석 체크",))
        row2_1.button("📉 장기결석 경고", use_container_width=True, on_click=set_page, args=("장기결석 경고 관리",))
        row2_2.button("✅ 증빙서류 체크리스트", use_container_width=True, on_click=set_page, args=("증빙서류 체크리스트",))
        if row2_3.button("🔔 알림 발송 센터", use_container_width=True):
            set_page("🔔 알림 센터")
            st.rerun()

    # 2. 이번 주 요약 미리보기 탭
    with tab_weekly:
        st.caption("※ 현재 월 기준으로 자동 생성된 요약입니다.")
        this_month = datetime.date.today().month
        target_months = [this_month] if this_month in all_months else [3]
        
        # 파일이 없거나 오래되었으면 자동 생성 시도
        weekly_path = os.path.join(REPORTS_DIR, "weekly", f"{target_months[0]:02d}월_주간요약.html")
        if not os.path.exists(weekly_path):
            with st.spinner(f"{target_months[0]}월 주간 요약 생성 중..."):
                try:
                    weekly_gen.run_weekly(target_months)
                except: st.error("데이터 로드 실패")
        
        display_html_report(weekly_path, height=600)

    # 3. 이번 달 달력 미리보기 탭
    with tab_calendar:
        st.caption("※ 현재 월 기준으로 자동 생성된 생활기록 달력입니다.")
        calendar_path = os.path.join(REPORTS_DIR, "calendar", f"{target_months[0]:02d}월_생활기록_달력.html")
        
        if not os.path.exists(calendar_path):
            with st.spinner(f"{target_months[0]}월 달력 생성 중..."):
                try:
                    calendar_gen.run_calendar(target_months)
                except: st.error("데이터 로드 실패")
        
        display_html_report(calendar_path, height=800)

# ==========================================
# 🔔 알림 센터
# ==========================================
elif current_menu == "🔔 알림 센터":
    st.subheader("🔔 텔레그램 알림 발송 센터")
    
    token, chat_id = universal_notification.get_telegram_config()
    if not token or not chat_id:
        st.error("⚠️ 텔레그램 봇 설정 확인 필요")
    else:
        st.success(f"✅ 봇 연결됨 (Chat ID: {chat_id})")
        tab1, tab2 = st.tabs(["📨 메시지 전송", "🤖 데일리 브리핑"])

        with tab1:
            st.write("**메시지 작성**")
            col_tags = st.columns(5)
            if col_tags[0].button("[공지]"): st.session_state['msg_input'] = "[공지] " + st.session_state.get('msg_input', '')
            if col_tags[1].button("[긴급]"): st.session_state['msg_input'] = "[긴급] " + st.session_state.get('msg_input', '')
            
            message = st.text_area("내용 입력", height=150, key='msg_input')
            if st.button("🚀 전송하기", type="primary"):
                if not message.strip(): st.warning("내용을 입력해주세요.")
                else:
                    if universal_notification.send_alert(message): st.toast("전송 성공!", icon="✅")
                    else: st.error("전송 실패")

        with tab2:
            st.write("### 🌅 오늘 아침 브리핑 (수동 실행)")
            if st.button("▶️ 브리핑 즉시 실행"):
                with st.spinner("실행 중..."):
                    daily_bot.run_daily_checks()
                st.success("완료")

# ==========================================
# 📑 월별/학급별 리포트
# ==========================================
elif current_menu == "월별/학급별 리포트":
    st.subheader("📑 월별/학급별 리포트")
    
    # 실행 버튼 (상태 저장)
    if st.button("🚀 리포트 생성 (선택된 월)", type="primary"):
        if not selected_months: st.warning("월을 선택해주세요.")
        else:
            with st.spinner("생성 중..."):
                monthly_gen.run_monthly_reports(selected_months)
                if index_gen: index_gen.run_monthly_index(selected_months)
            st.session_state['monthly_report_done'] = True # 상태 저장
            st.success("생성 완료!")

    # 결과 표시 (상태가 True이거나 파일이 있으면 표시)
    if st.session_state['monthly_report_done'] or selected_months:
        tabs = st.tabs([f"{m}월" for m in selected_months])
        for i, m in enumerate(selected_months):
            with tabs[i]:
                t1, t2 = st.tabs(["📊 월별 출결 상세", "🏫 학급별 통계"])
                with t1: display_html_report(os.path.join(REPORTS_DIR, "monthly", f"{m:02d}월_월별출결현황.html"))
                with t2: display_html_report(os.path.join(REPORTS_DIR, "monthly", f"{m:02d}월_학급별현황.html"))

# ==========================================
# 🚌 교외체험학습 통계
# ==========================================
elif current_menu == "교외체험학습 통계":
    st.subheader("🚌 교외체험학습 연간 통계")
    if st.button("📊 분석 실행") or st.session_state['fieldtrip_done']:
        if not st.session_state['fieldtrip_done']:
            fieldtrip_gen.run_fieldtrip_stats()
            st.session_state['fieldtrip_done'] = True
        
        display_html_report(os.path.join(REPORTS_DIR, "stats", "연간_체크_체험학습통계.html"))

# ==========================================
# 🩸 생리인정결석 체크
# ==========================================
elif current_menu == "생리인정결석 체크":
    st.subheader("🩸 생리인정결석 체크")
    if st.button("🩸 분석 실행") or st.session_state['menstrual_done']:
        if not st.session_state['menstrual_done']:
            menstrual_gen.run_menstrual_stats()
            st.session_state['menstrual_done'] = True
            
        display_html_report(os.path.join(REPORTS_DIR, "stats", "생리인정결석_통계.html"))

# ==========================================
# 📉 장기결석 경고 관리
# ==========================================
elif current_menu == "장기결석 경고 관리":
    st.subheader("📉 장기결석 경고")
    if st.button("📉 분석 실행") or st.session_state['absence_done']:
        if not st.session_state['absence_done']:
            absence_gen.run_long_term_absence()
            st.session_state['absence_done'] = True
            
        display_html_report(os.path.join(REPORTS_DIR, "stats", "장기결석_경고리포트.html"))

# ==========================================
# ✅ 증빙서류 체크리스트
# ==========================================
elif current_menu == "증빙서류 체크리스트":
    st.subheader("✅ 증빙서류 체크리스트")
    if st.button("📝 생성 실행") or st.session_state['checklist_done']:
        if not st.session_state['checklist_done']:
            checklist_gen.run_checklists(selected_months)
            st.session_state['checklist_done'] = True
            
        tabs = st.tabs([f"{m}월" for m in selected_months])
        for i, m in enumerate(selected_months):
            with tabs[i]:
                display_html_report(os.path.join(REPORTS_DIR, "checklist", f"{m:02d}월_증빙서류_체크리스트.html"))

# ==========================================
# 📅 주간 요약 & 달력
# ==========================================
elif current_menu == "주간 요약 & 달력":
    st.subheader("📅 주간 요약 및 생활기록 달력")
    
    if st.button("📆 생성 실행") or st.session_state['weekly_calendar_done']:
        if not selected_months:
            st.warning("월을 선택해주세요.")
        else:
            if not st.session_state['weekly_calendar_done']:
                with st.spinner("생성 중..."):
                    try:
                        weekly_gen.run_weekly(selected_months)
                        calendar_gen.run_calendar(selected_months)
                        st.session_state['weekly_calendar_done'] = True
                        st.success("완료!")
                    except Exception as e:
                        st.error(f"오류: {e}")

            tabs = st.tabs([f"{m}월" for m in selected_months])
            for i, m in enumerate(selected_months):
                with tabs[i]:
                    t1, t2 = st.tabs(["📑 주간 요약", "🗓️ 생활기록 달력"])
                    with t1: display_html_report(os.path.join(REPORTS_DIR, "weekly", f"{m:02d}월_주간요약.html"))
                    with t2: display_html_report(os.path.join(REPORTS_DIR, "calendar", f"{m:02d}월_생활기록_달력.html"))