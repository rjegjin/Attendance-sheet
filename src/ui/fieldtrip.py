import streamlit as st
import os
from src.components import universal_fieldtrip_stats as fieldtrip_gen
from src.paths import REPORTS_DIR
from src.ui.common import display_html_report

def render():
    st.subheader("🚌 교외체험학습 연간 통계")
    if st.button("📊 분석 실행") or st.session_state.get('fieldtrip_done'):
        if not st.session_state.get('fieldtrip_done'):
            fieldtrip_gen.run_fieldtrip_stats()
            st.session_state['fieldtrip_done'] = True
        
        display_html_report(os.path.join(REPORTS_DIR, "stats", "연간_체크_체험학습통계.html"))
