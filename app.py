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
    from src.services import universal_notification # [New] 알림 서비스 추가
    from src.paths import REPORTS_DIR, CACHE_DIR
    
    from src.components import universal_monthly_report_batch as monthly_gen
    from src.components import universal_fieldtrip_stats as fieldtrip_gen
    from src.components import universal_menstrual_stats as menstrual_gen
    from src.components import universal_long_term_absence as absence_gen
    from src.components import generate_checklist as checklist_gen
    from src.components import universal_weekly_summary_batch as weekly_gen
    from src.components import universal_calendar_batch as calendar_gen
    from src.components import daily_alert_system as daily_bot
    
    # 인덱스 생성기 (선택 사항)
    try:
        from src.components import universal_monthly_index as index_gen
    except ImportError:
        index_gen = None
    
except ImportError as e:
    st.error(f"❌ 모듈 임포트 오류: {e}")
    st.stop()

# --------------------------------------------------------------------------
# 3. PAGE CONFIG & SESSION STATE
# --------------------------------------------------------------------------
CURRENT_YEAR = config_manager.GLOBAL_CONFIG.get("target_year", 2025)

st.set_page_config(
    page_title=f"{CURRENT_YEAR}학년도 출결 관리",
    page_icon="🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 네비게이션 상태 초기화
if 'menu' not in st.session_state:
    st.session_state['menu'] = "대시보드(Home)"

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
        st.info(f"ℹ️ 리포트가 없습니다.\n(경로: {os.path.basename(file_path)})")

# 버튼 클릭 콜백
def set_page(page_name):
    st.session_state['menu'] = page_name

# --------------------------------------------------------------------------
# 5. SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.title(f"🏫 {CURRENT_YEAR}학년도\n출결 관리 시스템")
    st.markdown("---")
    
    # Session State와 연동된 라디오 버튼
    def on_menu_change():
        st.session_state['menu'] = st.session_state._menu_selection

    # [New] '🔔 알림 센터' 메뉴 추가
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
    
    if st.session_state['menu'] not in menu_options:
        st.session_state['menu'] = menu_options[0]

    menu = st.radio("작업 선택", 
        menu_options,
        index=menu_options.index(st.session_state['menu']),
        key='_menu_selection',
        on_change=on_menu_change
    )
    
    st.markdown("---")
    
    # 연단위 일괄 선택
    st.write("📅 **분석 대상 월 선택**")
    all_months = getattr(data_loader, 'ACADEMIC_MONTHS', [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2])
    
    select_all = st.checkbox("✅ 1년 전체 선택 (일괄)", value=False)
    
    if select_all:
        default_selection = all_months
    else:
        now = datetime.datetime.now()
        default_selection = [now.month] if now.month in all_months else [3]
        
    selected_months = st.multiselect(
        "월을 선택하세요", 
        all_months, 
        default=default_selection
    )
    
    st.markdown("---")
    
    # 데이터 관리
    with st.expander("⚙️ 데이터 관리"):
        if st.button("🔄 데이터 새로고침 (캐시삭제)", use_container_width=True):
            clear_cache_data()
            time.sleep(0.5)
            st.rerun()

    # 관리자 메뉴
    st.divider()
    with st.expander("🔐 관리자 설정 (새 학기)"):
        st.caption(f"현재: {CURRENT_YEAR}학년도")
        admin_pw = st.text_input("관리자 암호", type="password")
        
        if admin_pw == "school1234":
            st.success("인증됨")
            new_year_input = st.number_input("새 학년도", value=CURRENT_YEAR + 1, step=1, format="%d")
            reset_holiday = st.checkbox("공휴일 초기화", value=True)
            confirm = st.checkbox("데이터 백업 및 초기화 확인")
            
            if st.button("🚀 시스템 진급 실행", type="primary", disabled=not confirm):
                with st.spinner(f"{new_year_input}학년도 준비 중..."):
                    logs = admin_manager.run_new_year_reset(new_year_input, reset_holiday)
                    for log in logs: st.text(log)
                    time.sleep(2)
                    st.success("재시작합니다.")
                    time.sleep(1)
                    st.rerun()

# --------------------------------------------------------------------------
# 6. MAIN CONTENT
# --------------------------------------------------------------------------

current_menu = st.session_state['menu']

if current_menu == "대시보드(Home)":
    st.header(f"👋 {CURRENT_YEAR}학년도 출결 관리 대시보드")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric(label="총 학생 수", value=f"{len(data_loader.get_master_roster())}명")
    with col_b:
        st.metric(label="설정된 휴일", value=f"{len(config_manager.GLOBAL_CONFIG.get('holidays', []))}일")
    
    st.markdown("### 🚀 바로가기 메뉴")
    
    row1_1, row1_2, row1_3 = st.columns(3)
    row2_1, row2_2, row2_3 = st.columns(3)
    
    row1_1.button("📑 월별/학급별 리포트", use_container_width=True, type="primary", 
                  on_click=set_page, args=("월별/학급별 리포트",))
    
    row1_2.button("🚌 교외체험학습 통계", use_container_width=True, 
                  on_click=set_page, args=("교외체험학습 통계",))
        
    row1_3.button("🩸 생리인정결석 체크", use_container_width=True, 
                  on_click=set_page, args=("생리인정결석 체크",))
        
    row2_1.button("📉 장기결석 경고", use_container_width=True, 
                  on_click=set_page, args=("장기결석 경고 관리",))
        
    row2_2.button("✅ 증빙서류 체크리스트", use_container_width=True, 
                  on_click=set_page, args=("증빙서류 체크리스트",))
        
    # [New] 알림 센터 버튼 추가 (기존 달력 버튼 옆)
    if row2_3.button("🔔 알림 발송 센터", use_container_width=True):
        set_page("🔔 알림 센터")
        st.rerun()

# --------------------------------------------------------------------------
# [New] 알림 발송 센터
# --------------------------------------------------------------------------
elif current_menu == "🔔 알림 센터":
    st.subheader("🔔 텔레그램 알림 발송 센터")
    st.info("텔레그램 봇을 통해 공지사항을 전송하거나, 매일 아침 브리핑을 수동으로 실행합니다.")
    
    # 1. 봇 상태 확인
    token, chat_id = universal_notification.get_telegram_config()
    if not token or not chat_id:
        st.error("⚠️ 텔레그램 봇 설정이 되어있지 않습니다. (.env 또는 Secrets 확인)")
    else:
        st.success(f"✅ 봇 연결됨 (Chat ID: {chat_id})")

        tab1, tab2 = st.tabs(["📨 직접 메시지 전송", "🤖 자동 알림 수동 실행"])

        # 탭 1: 직접 메시지 보내기
        with tab1:
            with st.container(border=True):
                st.write("**메시지 작성**")
                
                # 상용구 버튼
                col_tags = st.columns(5)
                if col_tags[0].button("[공지]"): st.session_state['msg_input'] = "[공지] " + st.session_state.get('msg_input', '')
                if col_tags[1].button("[긴급]"): st.session_state['msg_input'] = "[긴급] " + st.session_state.get('msg_input', '')
                
                message = st.text_area("내용을 입력하세요", height=150, key='msg_input')
                
                if st.button("🚀 전송하기", type="primary"):
                    if not message.strip():
                        st.warning("내용을 입력해주세요.")
                    else:
                        with st.spinner("전송 중..."):
                            success = universal_notification.send_alert(message)
                            if success:
                                st.toast("메시지가 전송되었습니다!", icon="✅")
                            else:
                                st.error("전송에 실패했습니다. 로그를 확인하세요.")

        # 탭 2: 데일리 브리핑 실행
        with tab2:
            st.write("### 🌅 오늘 아침 브리핑")
            st.write("매일 아침 8시 30분에 발송되는 **출결/생일/미제출 서류 요약**을 지금 즉시 발송합니다.")
            
            if st.button("▶️ 브리핑 즉시 실행"):
                with st.spinner("데이터 분석 및 브리핑 작성 중..."):
                    # daily_bot 내부 함수 호출
                    daily_bot.run_daily_checks() 
                st.success("브리핑 발송이 완료되었습니다.")

elif current_menu == "월별/학급별 리포트":
    st.subheader(f"📑 {CURRENT_YEAR}학년도 월별/학급별 리포트")
    st.info("나이스 업로드용 '월별 출결 상세'와 내부 결재용 '학급별 통계'를 생성합니다.")
    
    if st.button("🚀 리포트 생성 (선택된 월)", type="primary"):
        if not selected_months: st.warning("월을 선택해주세요.")
        else:
            with st.spinner("데이터 분석 및 HTML 생성 중..."):
                monthly_gen.run_monthly_reports(selected_months)
                if index_gen: index_gen.run_monthly_index(selected_months)
            st.success("생성 완료!")
            
            tabs = st.tabs([f"{m}월" for m in selected_months])
            for i, m in enumerate(selected_months):
                with tabs[i]:
                    sub_tab1, sub_tab2 = st.tabs(["📊 월별 출결 상세(나이스용)", "🏫 학급별 통계(내부결재용)"])
                    
                    with sub_tab1:
                        path_detail = os.path.join(REPORTS_DIR, "monthly", f"{m:02d}월_월별출결현황.html")
                        display_html_report(path_detail)
                        
                    with sub_tab2:
                        path_stats = os.path.join(REPORTS_DIR, "monthly", f"{m:02d}월_학급별현황.html")
                        display_html_report(path_stats)

elif current_menu == "교외체험학습 통계":
    st.subheader("🚌 교외체험학습 연간 통계")
    if st.button("📊 분석 실행"):
        fieldtrip_gen.run_fieldtrip_stats()
        display_html_report(os.path.join(REPORTS_DIR, "stats", "연간_체크_체험학습통계.html"))

elif current_menu == "생리인정결석 체크":
    st.subheader("🩸 생리인정결석 체크")
    if st.button("🩸 분석 실행"):
        menstrual_gen.run_menstrual_stats()
        display_html_report(os.path.join(REPORTS_DIR, "stats", "생리인정결석_통계.html"))

elif current_menu == "장기결석 경고 관리":
    st.subheader("📉 장기결석 경고")
    if st.button("📉 분석 실행"):
        absence_gen.run_long_term_absence()
        display_html_report(os.path.join(REPORTS_DIR, "stats", "장기결석_경고리포트.html"))

elif current_menu == "증빙서류 체크리스트":
    st.subheader("✅ 증빙서류 체크리스트")
    if st.button("📝 생성 실행"):
        checklist_gen.run_checklists(selected_months)
        tabs = st.tabs([f"{m}월" for m in selected_months])
        for i, m in enumerate(selected_months):
            with tabs[i]:
                display_html_report(os.path.join(REPORTS_DIR, "checklist", f"{m:02d}월_증빙서류_체크리스트.html"))

elif current_menu == "주간 요약 & 달력":
    st.subheader("📅 주간 요약 및 생활기록 달력")
    st.info("주 단위 출결 요약과 NEIS 입력용 생활기록 달력을 생성합니다.")
    
    if st.button("📆 생성 실행"):
        if not selected_months: st.warning("월을 선택해주세요.")
        else:
            with st.spinner("생성 중..."):
                try:
                    weekly_gen.run_weekly(selected_months)
                    calendar_gen.run_calendar(selected_months)
                    st.success("완료!")
                except Exception as e:
                    st.error(f"생성 중 오류 발생: {e}")
            
            tabs = st.tabs([f"{m}월" for m in selected_months])
            for i, m in enumerate(selected_months):
                with tabs[i]:
                    sub_tab1, sub_tab2 = st.tabs(["📑 주간 요약", "🗓️ 생활기록 달력"])
                    
                    with sub_tab1:
                        path_weekly = os.path.join(REPORTS_DIR, "weekly", f"{m:02d}월_주간요약.html")
                        display_html_report(path_weekly)
                    
                    with sub_tab2:
                        path_calendar = os.path.join(REPORTS_DIR, "calendar", f"{m:02d}월_생활기록_달력.html")
                        display_html_report(path_calendar)