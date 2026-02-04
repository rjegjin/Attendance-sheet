import streamlit as st
import os
import datetime
from src.services import data_loader, config_manager
from src.components import universal_weekly_summary_batch as weekly_gen
from src.components import universal_calendar_batch as calendar_gen
from src.paths import REPORTS_DIR
from src.ui.common import display_html_report, set_page

def render(current_year, all_months):
    st.header(f"👋 {current_year}학년도 출결 관리 대시보드")
    
    # 상단 요약 지표
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        st.metric(label="총 학생 수", value=f"{len(data_loader.get_master_roster())}명")
    with col_b:
        st.metric(label="오늘 날짜", value=datetime.date.today().strftime("%Y-%m-%d"))
    with col_c:
        st.metric(label="설정된 휴일", value=f"{len(config_manager.GLOBAL_CONFIG.get('holidays', []))}일")
    
    st.divider()

    # 대시보드 탭 구성
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
