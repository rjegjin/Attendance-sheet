import streamlit as st
import os
from src.components import generate_checklist as checklist_gen
from src.paths import REPORTS_DIR
from src.ui.common import display_html_report

def render(selected_months):
    st.subheader("✅ 증빙서류 체크리스트")
    if st.button("📝 생성 실행") or st.session_state.get('checklist_done'):
        if not st.session_state.get('checklist_done'):
            checklist_gen.run_checklists(selected_months)
            st.session_state['checklist_done'] = True
            
        tabs = st.tabs([f"{m}월" for m in selected_months])
        for i, m in enumerate(selected_months):
            with tabs[i]:
                display_html_report(os.path.join(REPORTS_DIR, "checklist", f"{m:02d}월_증빙서류_체크리스트.html"))
