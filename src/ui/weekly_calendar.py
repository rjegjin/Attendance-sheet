import streamlit as st
import os
from src.components import universal_weekly_summary_batch as weekly_gen
from src.components import universal_calendar_batch as calendar_gen
from src.paths import REPORTS_DIR
from src.ui.common import display_html_report

def render(selected_months):
    st.subheader("📅 주간 요약 및 생활기록 달력")
    
    if st.button("📆 생성 실행") or st.session_state.get('weekly_calendar_done'):
        if not selected_months:
            st.warning("월을 선택해주세요.")
        else:
            if not st.session_state.get('weekly_calendar_done'):
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
                    t1, t2 = st.tabs(["📊 주간 요약", "🗓️ 생활기록 달력"])
                    with t1: display_html_report(os.path.join(REPORTS_DIR, "weekly", f"{m:02d}월_주간요약.html"))
                    with t2: display_html_report(os.path.join(REPORTS_DIR, "calendar", f"{m:02d}월_생활기록_달력.html"))
