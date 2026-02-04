import streamlit as st
import pandas as pd
from src.components.school_schedule_manager import SchoolScheduleManager

def render(current_year):
    st.subheader("📅 학사일정 관리 (Google Sheets)")
    
    # 1. 초기화
    if 'ssm' not in st.session_state:
        st.session_state['ssm'] = SchoolScheduleManager(year=current_year)
    ssm = st.session_state['ssm']
    
    # 2. API 연결
    st.markdown("### 1단계: API 연결")
    if st.button("🔌 Google API 연결"):
        # secrets에서 가져오기 시도
        creds = None
        if 'gcp_service_account' in st.secrets:
            creds = dict(st.secrets['gcp_service_account'])
            if 'private_key' in creds:
                creds['private_key'] = creds['private_key'].replace('\\n', '\n')
        
        success, msg = ssm.connect_google_api(credentials_dict=creds)
        if success:
            st.success(msg)
            # 연결 성공 시 시트 목록 가져오기 위해 즉시 시트 열기 시도
            success_open, msg_open = ssm.open_spreadsheet()
            if success_open:
                st.info(msg_open)
            else:
                st.error(msg_open)
        else:
            st.error(msg)

    # 3. 시트 선택
    if ssm.client and ssm.spreadsheet:
        st.markdown("---")
        st.markdown("### 2단계: 워크시트 선택")
        worksheets = ssm.get_worksheets()
        titles = [ws.title for ws in worksheets]
        
        # 추천 시트 찾기
        rec_idx = 0
        for i, t in enumerate(titles):
            if "전체" in t or "학사" in t:
                rec_idx = i
                break
        
        selected_title = st.selectbox("파싱할 시트를 선택하세요", titles, index=rec_idx)
        if st.button("📂 데이터 분석 시작"):
            ws = next(w for w in worksheets if w.title == selected_title)
            ssm.set_worksheet(ws)
            with st.spinner("데이터 분석 및 복원 중..."):
                success, msg = ssm.parse_all_data()
                if success:
                    st.success(msg)
                else:
                    st.error(msg)

    # 4. 내보내기
    if ssm.raw_data:
        st.markdown("---")
        st.markdown("### 3단계: 데이터 내보내기")
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("#### 🏮 휴일 데이터 (JSON)")
            st.caption("시스템의 휴일 설정 파일(holidays_XXXX.json)로 저장합니다.")
            if st.button("💾 JSON으로 저장", use_container_width=True):
                success, msg = ssm.save_holidays_json()
                if success: st.success(msg)
                else: st.error(msg)
                
        with col2:
            st.write("#### 📅 캘린더 데이터 (CSV)")
            st.caption("구글 캘린더 업로드용 CSV 파일을 생성합니다.")
            grade = st.radio("대상 선택", ["1", "2", "3", "4 (전체)"], horizontal=True)
            if st.button("📊 CSV로 저장", use_container_width=True):
                success, msg = ssm.save_calendar_csv(grade[0])
                if success: st.success(msg)
                else: st.error(msg)
        
        # 데이터 미리보기
        with st.expander("👀 추출된 데이터 미리보기 (상위 20건)"):
            st.table(pd.DataFrame(ssm.raw_data).head(20))
