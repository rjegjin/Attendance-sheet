import json
import os

# ------------------------------------------------------------------
# 설정: 변환할 JSON 파일명
# ------------------------------------------------------------------
INPUT_FILE = 'service_key.json'

def convert_json_to_toml():
    # 1. 파일 존재 여부 확인
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 오류: '{INPUT_FILE}' 파일을 찾을 수 없습니다.")
        print("이 스크립트와 같은 폴더에 json 파일을 넣어주세요.")
        return

    # 2. JSON 파일 읽기
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("❌ 오류: JSON 파일 형식이 올바르지 않습니다.")
        return

    # 3. TOML 형식으로 출력 (터미널에 표시)
    print("\n" + "="*50)
    print("👇 아래 내용을 복사해서 Streamlit Secrets에 붙여넣으세요 👇")
    print("="*50 + "\n")

    # 헤더 출력 (필수)
    print("[gcp_service_account]")

    # 키-값 쌍 출력
    for key, value in data.items():
        # json.dumps를 사용하면 문자열의 따옴표나 이스케이프 문자(\n)를 
        # TOML에서도 안전하게 사용할 수 있는 형태로 자동 변환해줍니다.
        formatted_value = json.dumps(value, ensure_ascii=False)
        print(f'{key} = {formatted_value}')

    print("\n" + "="*50)
    print("✅ 변환 완료!")

if __name__ == "__main__":
    convert_json_to_toml()