import streamlit as st
import os

def display_html_report(file_path, height=800):
    """HTML 리포트를 화면에 표시하고 다운로드 버튼을 제공합니다."""
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            html = f.read()
        fname = os.path.basename(file_path)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            st.download_button(f"📥 {fname} 다운로드", html, fname, "text/html")
        
        st.components.v1.html(html, height=height, scrolling=True)
    else:
        st.info(f"ℹ️ 생성된 리포트가 없습니다. 먼저 '생성/분석 실행' 버튼을 눌러주세요.
(경로: {os.path.basename(file_path)})")

def set_page(page_name):
    """페이지 이동 (메뉴 변경)"""
    st.session_state['menu'] = page_name
