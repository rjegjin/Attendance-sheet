import streamlit as st
import os
from src.components import universal_long_term_absence as absence_gen
from src.paths import REPORTS_DIR
from src.ui.common import display_html_report

def render():
    st.subheader("📉 장기결석 경고")
    if st.button("📉 분석 실행") or st.session_state.get('absence_done'):
        if not st.session_state.get('absence_done'):
            absence_gen.run_long_term_absence()
            st.session_state['absence_done'] = True
            
        display_html_report(os.path.join(REPORTS_DIR, "stats", "장기결석_경고리포트.html"))
