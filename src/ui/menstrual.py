import streamlit as st
import os
from src.components import universal_menstrual_stats as menstrual_gen
from src.paths import REPORTS_DIR
from src.ui.common import display_html_report

def render():
    st.subheader("🩸 생리인정결석 체크")
    if st.button("🩸 분석 실행") or st.session_state.get('menstrual_done'):
        if not st.session_state.get('menstrual_done'):
            menstrual_gen.run_menstrual_stats()
            st.session_state['menstrual_done'] = True
            
        display_html_report(os.path.join(REPORTS_DIR, "stats", "생리인정결석_통계.html"))
