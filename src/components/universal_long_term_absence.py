import requests
import json
import os

# 프로젝트 루트 경로 찾기 (src/components/ 에서 두 단계 위)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
CONFIG_PATH = os.path.join(ROOT_DIR, "config.json")

def load_config():
    """config.json에서 텔레그램 설정을 읽어옵니다."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def send_alert(message):
    """
    텔레그램으로 메시지를 전송합니다.
    설정이 없거나 전송 실패 시 콘솔에 출력합니다.
    """
    config = load_config()
    token = config.get("telegram_token")
    chat_id = config.get("telegram_chat_id")

    # 헤더 장식
    formatted_msg = f"🏫 [출결 관리 시스템 알림]\n{message}"

    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = {"chat_id": chat_id, "text": formatted_msg}
            response = requests.post(url, data=data, timeout=5)
            
            if response.status_code != 200:
                print(f"⚠️ [Telegram Error] 전송 실패: {response.text}")
                print(f"📢 (콘솔 출력) {message}")
        except Exception as e:
            print(f"⚠️ [Telegram Error] 연결 오류: {e}")
            print(f"📢 (콘솔 출력) {message}")
    else:
        # 설정이 없는 경우 콘솔에만 출력
        print("\n" + "="*40)
        print("📢 [알림 (설정 없음)]")
        print(message)
        print("="*40 + "\n")
