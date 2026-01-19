import os
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_drive_service():
    """구글 드라이브 API 연결 서비스 생성"""
    creds = None
    try:
        # 1. Streamlit Secrets 확인
        if hasattr(st, "secrets") and "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(
                creds_dict, scopes=SCOPES
            )
        # 2. 로컬 파일 확인
        elif os.path.exists('service_key.json'):
            creds = service_account.Credentials.from_service_account_file(
                'service_key.json', scopes=SCOPES
            )
        
        if creds:
            service = build('drive', 'v3', credentials=creds)
            return service, creds.service_account_email
        else:
            return None, None
    except Exception as e:
        st.error(f"구글 드라이브 연결 오류: {e}")
        return None, None

def check_folder_access(folder_id):
    """폴더 접근 테스트"""
    service, email = get_drive_service()
    if not service: return False, "서비스 연결 실패"

    try:
        # 폴더 정보 가져오기 시도
        folder = service.files().get(fileId=folder_id, fields="name").execute()
        return True, f"✅ 접속 성공! (로봇: {email}) -> 폴더명: '{folder.get('name')}'"
    except Exception as e:
        return False, f"❌ 접속 실패 (로봇: {email})\n오류 내용: {e}"

def upload_file(file_path, folder_id):
    """파일 업로드"""
    service, _ = get_drive_service()
    if not service: return None

    file_name = os.path.basename(file_path)
    
    file_metadata = {
        'name': file_name,
        'parents': [folder_id] 
    }
    
    media = MediaFileUpload(file_path, mimetype='text/html', resumable=True)

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return file.get('id')
    except Exception as e:
        st.error(f"업로드 에러 상세: {e}")
        return None