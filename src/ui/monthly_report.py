import streamlit as st
import os
from src.components import universal_monthly_report_batch as monthly_gen
from src.paths import REPORTS_DIR
from src.ui.common import display_html_report

try:
    from src.components import universal_monthly_index as index_gen
except ImportError:
    index_gen = None

def render(selected_months):
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
    if st.session_state.get('monthly_report_done') or selected_months:
        tabs = st.tabs([f"{m}월" for m in selected_months])
        for i, m in enumerate(selected_months):
            with tabs[i]:
                t1, t2 = st.tabs(["📊 월별 출결 상세", "🏫 학급별 통계"])
                with t1: display_html_report(os.path.join(REPORTS_DIR, "monthly", f"{m:02d}월_월별출결현황.html"))
                with t2: display_html_report(os.path.join(REPORTS_DIR, "monthly", f"{m:02d}월_학급별현황.html"))
