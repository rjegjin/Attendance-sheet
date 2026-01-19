import json
import os
import shutil
import datetime
from pathlib import Path

# [핵심] 나침반을 가져와서 절대 경로를 사용합니다.
from src.paths import ROOT_DIR, DATA_DIR

# 1. 마스터 데이터베이스 (영구 저장소)
# DATA_DIR은 이미 src.paths에서 "reports/data"로 정의되어 있습니다.
DATA_FILE = DATA_DIR / "checklist_status.json"

# 2. 업데이트 파일 탐색 대상 (HTML에서 받은 파일은 항상 루트에 위치)
UPDATE_FILE_NAME = "checklist_update.json"
UPDATE_FILE_PATH = ROOT_DIR / UPDATE_FILE_NAME

# 3. 처리 후 보관할 백업 폴더
BACKUP_DIR = DATA_DIR / "processed_updates"

def load_status():
    """마스터 DB 로드"""
    if not DATA_FILE.exists(): return {}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    except: return {}

def save_status(data):
    """마스터 DB 저장"""
    # 폴더가 없으면 생성 (DATA_DIR은 Path 객체이므로 mkdir 사용 가능)
    if not DATA_DIR.exists(): DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def mark_submitted(student_name, date_str):
    """개별 건 수동 처리"""
    data = load_status()
    key = f"{student_name}_{date_str}"
    data[key] = True
    save_status(data)
    print(f"   ✅ [수동저장] {student_name} ({date_str}) 처리 완료")

def is_submitted(student_name, date_str):
    """제출 여부 확인"""
    data = load_status()
    key = f"{student_name}_{date_str}"
    return data.get(key, False)

def auto_scan_and_merge():
    """
    [핵심 기능] 루트 폴더에 'checklist_update.json'이 있는지 확인하고,
    있다면 마스터 DB에 병합한 뒤 파일을 백업 폴더로 이동시킵니다.
    """
    print(f"   🔎 파일 탐색 중: {UPDATE_FILE_NAME} ...")
    
    if not UPDATE_FILE_PATH.exists():
        print("   ❌ 루트 폴더에 업데이트 파일이 없습니다.")
        print(f"      HTML에서 저장한 '{UPDATE_FILE_NAME}' 파일을 프로젝트 폴더로 옮겨주세요.")
        return

    try:
        # 1. 업데이트 파일 읽기
        with open(UPDATE_FILE_PATH, 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        
        # 2. 기존 마스터 DB 읽기
        current_data = load_status()
        count = 0
        
        # 3. 병합 (Merge)
        for key, value in new_data.items():
            if value: # True인 값만 반영
                if key not in current_data:
                    current_data[key] = True
                    count += 1
        
        # 4. 저장
        save_status(current_data)
        print(f"   💾 [병합 완료] 총 {count}건의 새로운 제출 기록이 반영되었습니다.")
        
        # 5. 파일 정리 (백업 폴더로 이동)
        if not BACKUP_DIR.exists(): BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"processed_{timestamp}.json"
        backup_path = BACKUP_DIR / backup_name
        
        shutil.move(str(UPDATE_FILE_PATH), str(backup_path))
        print(f"   🧹 [정리 완료] 사용한 파일은 백업 폴더로 이동되었습니다.")
        print(f"      (위치: {backup_path})")

    except Exception as e:
        print(f"   ⚠️ 처리 중 오류 발생: {e}")