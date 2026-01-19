import os
import requests
import sys

# [수리] 나침반 가져오기 (절대 경로로 .env 찾기 위함)
from src.paths import ROOT_DIR

# [중요] 로컬 .env 로딩을 위한 라이브러리
try:
    from dotenv import load_dotenv
    # [수리] 루트 경로의 .env 파일을 명시적으로 지정하여 로드
    load_dotenv(dotenv_path=ROOT_DIR / ".env")
except ImportError:
    # Streamlit Cloud에는 python-dotenv가 없을 수도 있으니 패스
    pass

def get_telegram_config():
    """
    환경에 따라 적절한 키 값을 찾아 반환하는 함수
    우선순위: 1. Streamlit Secrets (클라우드) -> 2. os.getenv (로컬 .env)
    """
    bot_token = None
    chat_id = None

    # 1. Streamlit Cloud Secrets 확인 시도
    try:
        import streamlit as st
        # Cloud 환경인지 확인 (secrets 속성이 있는지)
        if hasattr(st, "secrets"):
            # secrets.toml에 정의된 키 이름으로 접근
            bot_token = st.secrets.get("TELEGRAM_TOKEN")
            chat_id = st.secrets.get("TELEGRAM_CHAT_ID")
    except Exception:
        pass # 로컬 환경이거나 streamlit 모듈 에러 시 무시

    # 2. 로컬 환경 변수(.env) 확인 (Secrets에서 못 찾았을 경우)
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
    
    # 실행 시점에 토큰이 없으면 다시 한 번 로드 시도 (안전장치)
    if not BOT_TOKEN:
        BOT_TOKEN, CHAT_ID = get_telegram_config()

    if not BOT_TOKEN or not CHAT_ID:
        # 키가 없으면 조용히 실패 (로그만 남김)
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": msg,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code == 200:
            return True
        else:
            print(f"❌ [Telegram] 전송 거부 ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ [Telegram] 연결 오류: {e}")
        return False

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