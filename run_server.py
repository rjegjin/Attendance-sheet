import os
import sys
from pyngrok import ngrok
from time import sleep

# ==========================================
# [수정할 부분]
# 방금 복사한 '2'로 시작하는 긴 코드를 아래 따옴표 안에 붙여넣으세요.
# ==========================================
NGROK_AUTH_TOKEN = "37gEa3MNCUprpoi1g1Zu69SbVUD_5itBptSkVRg8Cr3AddXxm" 

# [설정] Streamlit 포트
PORT = 8501

def start_server():
    # 토큰 설정
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    print(f"✅ 인증 토큰 설정 완료!")

    # 터널 생성
    try:
        # 이전에 열려있는 터널이 있다면 닫기 (충돌 방지)
        tunnels = ngrok.get_tunnels()
        for t in tunnels:
            ngrok.disconnect(t.public_url)

        public_url = ngrok.connect(PORT).public_url
        print("=" * 50)
        print(f" 📲 핸드폰으로 접속하세요! (아래 링크 클릭)")
        print(f" 🔗 {public_url}")
        print("=" * 50)
    except Exception as e:
        print(f"❌ 터널 생성 실패: {e}")
        return

    # Streamlit 앱 실행
    os.system(f"streamlit run app.py --server.port {PORT}")

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n🛑 서버를 종료합니다.")
        ngrok.kill()
        sys.exit(0)