import streamlit as st
from src.services import universal_notification
from src.components import daily_alert_system as daily_bot
from src.ui.common import set_page

def render():
    st.subheader("🔔 텔레그램 알림 발송 센터")
    
    token, chat_id = universal_notification.get_telegram_config()
    if not token or not chat_id:
        st.error("⚠️ 텔레그램 봇 설정 확인 필요")
    else:
        st.success(f"✅ 봇 연결됨 (Chat ID: {chat_id})")
        tab1, tab2 = st.tabs(["📨 메시지 전송", "🤖 데일리 브리핑"])

        with tab1:
            st.write("**메시지 작성**")
            col_tags = st.columns(5)
            if col_tags[0].button("[공지]"): st.session_state['msg_input'] = "[공지] " + st.session_state.get('msg_input', '')
            if col_tags[1].button("[긴급]"): st.session_state['msg_input'] = "[긴급] " + st.session_state.get('msg_input', '')
            
            message = st.text_area("내용 입력", height=150, key='msg_input')
            if st.button("🚀 전송하기", type="primary"):
                if not message.strip(): st.warning("내용을 입력해주세요.")
                else:
                    if universal_notification.send_alert(message): st.toast("전송 성공!", icon="✅")
                    else: st.error("전송 실패")

        with tab2:
            st.write("### 🌅 오늘 아침 브리핑 (수동 실행)")
            if st.button("▶️ 브리핑 즉시 실행"):
                with st.spinner("실행 중..."):
                    daily_bot.run_daily_checks()
                st.success("완료")
