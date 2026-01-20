import json
import os

# ------------------------------------------------------------------
# [설정] 파일 이름
# ------------------------------------------------------------------
INPUT_FILE = 'service_key.json'       # 원본 파일 (절대 공유 금지)
OUTPUT_FILE = 'service_key_safe.json' # 생성될 안전한 파일 (공유 가능)

def sanitize_credentials():
    # 1. 원본 파일 존재 여부 확인
    if not os.path.exists(INPUT_FILE):
        print(f"❌ 오류: '{INPUT_FILE}' 파일을 찾을 수 없습니다.")
        return

    try:
        # 2. 원본 JSON 읽기
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 3. 민감 정보 치환 (Masking)
        # 구조는 유지하되, 값을 안전한 더미 데이터로 교체합니다.
        
        # (1) 프로젝트 ID 및 이메일 마스킹
        safe_project_id = "sanitized-project-id"
        data['project_id'] = safe_project_id
        data['private_key_id'] = "0000000000000000000000000000000000000000"
        data['client_id'] = "123456789012345678901"
        
        # (2) 이메일 주소 형식 유지하며 치환
        if 'client_email' in data:
            data['client_email'] = f"school-bot@{safe_project_id}.iam.gserviceaccount.com"
            
        if 'client_x509_cert_url' in data:
            data['client_x509_cert_url'] = f"https://www.googleapis.com/robot/v1/metadata/x509/school-bot%40{safe_project_id}.iam.gserviceaccount.com"

        # (3) Private Key (가장 중요!)
        # 실제 키 형식을 흉내 내지만 기능은 없는 가짜 키로 대체
        data['private_key'] = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQD... (SANITIZED_KEY) ...\n-----END PRIVATE KEY-----\n"

        # 4. 안전한 파일로 저장
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

        print("\n" + "="*60)
        print(f"✅ 보안 처리가 완료되었습니다!")
        print(f"📁 생성된 파일: {OUTPUT_FILE}")
        print("="*60)
        print("👉 이 파일(service_key_safe.json)은 GitHub에 올려도 안전합니다.")
        print("👉 다른 개발자가 구조를 파악하는 용도로 사용할 수 있습니다.")

    except Exception as e:
        print(f"❌ 변환 중 오류 발생: {e}")

if __name__ == "__main__":
    sanitize_credentials()