import os
import requests
import sys

# [수리] 나침반 가져오기 (절대 경로로 .env 찾기 위함)
from src.paths import ROOT_DIR

# ✅ 설정 관리자 연동
try:
    from src.services.config_manager import GLOBAL_CONFIG
except ImportError:
    GLOBAL_CONFIG = {}

# [중요] 로컬 .env 로딩을 위한 라이브러리
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ROOT_DIR / ".env")
except ImportError:
    pass

def get_telegram_config():
    """
    환경에 따라 적절한 키 값을 찾아 반환하는 함수
    우선순위: 1. Streamlit Secrets -> 2. config.json -> 3. 로컬 .env
    """
    bot_token = None
    chat_id = None

    # 1. Streamlit Cloud Secrets 확인 시도
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            #Case A: 헤더 없이 바로 있는 경우 (TELEGRAM_TOKEN = "...")
            bot_token = st.secrets.get("TELEGRAM_TOKEN")
            chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
            
            #Case B: [telegram] 섹션 아래에 있는 경우 (선생님의 설정 상황)
            if not bot_token and "telegram" in st.secrets:
                bot_token = st.secrets["telegram"].get("TELEGRAM_TOKEN")
                chat_id = st.secrets["telegram"].get("TELEGRAM_CHAT_ID")
    except Exception:
        pass 

    # 2. config.json 확인
    if not bot_token:
        bot_token = GLOBAL_CONFIG.get("telegram_token")
    if not chat_id:
        chat_id = GLOBAL_CONFIG.get("telegram_chat_id")

    # 3. 로컬 환경 변수(.env) 확인
    if not bot_token:
        bot_token = os.getenv("TELEGRAM_TOKEN")
    if not chat_id:
        chat_id = os.getenv("TELEGRAM_CHAT_ID")

    return bot_token, chat_id

# ==========================================
# 전역 변수 설정 (최초 1회 실행)
# ==========================================
BOT_TOKEN, CHAT_ID = get_telegram_config()

def send_alert(msg):
    """
    텔레그램 메시지 전송 함수
    """
    global BOT_TOKEN, CHAT_ID
    
    if not BOT_TOKEN:
        BOT_TOKEN, CHAT_ID = get_telegram_config()

    if not BOT_TOKEN or not CHAT_ID:
        return False
    
    school_name = GLOBAL_CONFIG.get("school_name", "")
    if school_name:
        msg = f"<b>[{school_name}]</b>\n{msg}"

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ [Telegram] 연결 오류: {e}")
        return False

if __name__ == "__main__":
    token, cid = get_telegram_config()
    if token and cid:
        print(f"✅ 설정 확인 완료! (ChatID: {cid})")
        send_alert("🔔 시스템 설정 테스트 메시지입니다.")
    else:
        print("❌ 설정을 찾을 수 없습니다.")

# ==========================================
# ID 확인용 유틸리티 (직접 실행 시)
# ==========================================
if __name__ == "__main__":
    print("--- 텔레그램 설정 진단 ---")
    token, cid = get_telegram_config()
    
    if token and cid:
        print(f"✅ 설정 확인 완료!")
        print(f"   Token: {token[:5]}...")
        print(f"   ChatID: {cid}")
        
        print("\n📨 테스트 메시지 전송 시도...")
        res = send_alert("🔔 시스템 설정 테스트 메시지입니다.")
        if res: print("   --> 성공!")
        else: print("   --> 실패.")
    else:
        print("❌ 설정을 찾을 수 없습니다.")
        print("   1. 로컬: .env 파일에 TELEGRAM_TOKEN, TELEGRAM_CHAT_ID 확인")
        print("   2. 클라우드: Manage App > Settings > Secrets 확인")