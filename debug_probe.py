import sys
import os
import shutil
from pathlib import Path
import time

# 1. 환경 진단
print("="*50)
print("🕵️‍♂️ [1] 환경 정밀 진단")
print("="*50)
print(f"📍 현재 실행 위치: {os.getcwd()}")
print(f"📍 실행 파일 경로: {os.path.abspath(__file__)}")

# 경로 강제 주입 (테스트용)
sys.path.append(os.getcwd())

try:
    from src.paths import ROOT_DIR, CACHE_DIR, SERVICE_KEY_PATH
    print(f"✅ src.paths 로드 성공")
    print(f"   -> ROOT_DIR: {ROOT_DIR}")
    print(f"   -> CACHE_DIR: {CACHE_DIR}")
except ImportError as e:
    print(f"❌ src.paths 로드 실패: {e}")
    sys.exit(1)

# 2. 캐시 오염도 측정
print("\n" + "="*50)
print("🕵️‍♂️ [2] 캐시(Cache) 상태 확인")
print("="*50)
if CACHE_DIR.exists():
    cache_files = list(CACHE_DIR.glob("*.pkl"))
    print(f"📁 캐시 폴더 발견: {CACHE_DIR}")
    print(f"📦 저장된 캐시 파일 수: {len(cache_files)}개")
    for f in cache_files[:3]:
        print(f"   - {f.name} (수정시간: {time.ctime(os.path.getmtime(f))})")
    
    print("\n⚠️ [중요 진단] 코드를 고쳐도 옛날 캐시가 남아있으면 소용이 없습니다.")
    print("👉 이 진단이 끝난 후 캐시를 강제로 비우시겠습니까? (권장)")
else:
    print("✨ 캐시 폴더가 비어있거나 없습니다. (Good)")

# 3. 데이터 실체 해부 (Live Probe)
print("\n" + "="*50)
print("🕵️‍♂️ [3] 구글 시트 데이터 실시간 해부")
print("="*50)

try:
    from src.services import data_loader
    print(f"✅ data_loader 모듈 위치: {data_loader.__file__}")
    
    # 강제로 캐시를 무시하고 라이브 데이터를 긁어옵니다.
    print("☁️ 3월 데이터 1개를 강제로 뜯어봅니다 (Force Update)...")
    
    # [핵심] 로우 데이터 검사
    client = data_loader.get_google_client()
    doc = client.open_by_url(data_loader.GOOGLE_SHEET_URL)
    
    # 3월 시트 찾기
    ws = None
    for cand in ["3월", "03월"]:
        try: ws = doc.worksheet(cand); break
        except: pass
        
    if ws:
        # 데이터 일부만 가져와서 타입 검사
        print(f"✅ 시트 접속 성공: {ws.title}")
        raw_values = ws.get_all_values()
        
        # 헤더 찾기
        header_row = None
        for row in raw_values[:5]:
            if "이름" in str(row) or "성명" in str(row):
                header_row = row
                break
        
        if header_row:
            print(f"   -> 헤더 발견: {header_row[:5]} ...")
            
            # 실제 데이터 행 분석 (FALSE가 있을만한 곳)
            sample_row = None
            for row in raw_values[5:15]: # 5~15번째 줄 사이 탐색
                if "FALSE" in str(row).upper():
                    sample_row = row
                    break
            
            if sample_row:
                print("\n🔬 [현미경 분석] 'FALSE'가 포함된 행 발견!")
                print(f"   -> 원본 데이터: {sample_row}")
                
                # 각 셀의 타입을 정밀 분석
                print("\n   -> 각 셀의 파이썬 인식 타입:")
                for idx, cell in enumerate(sample_row):
                    # 날짜 컬럼 근처만 분석 (너무 많으니까)
                    if idx < 10: 
                        print(f"      Col {idx}: 값='{cell}' | 타입={type(cell)} | 길이={len(str(cell))}")
            else:
                print("\n❓ 이 범위(5~15행)에는 'FALSE'가 안 보입니다. 데이터가 깨끗한가요?")
        else:
            print("❌ 헤더를 못 찾겠습니다.")
            
    else:
        print("❌ 3월 시트를 못 찾았습니다.")

except Exception as e:
    print(f"❌ 데이터 진단 중 오류 발생: {e}")

print("\n" + "="*50)
print("🏁 진단 종료. 이 결과를 복사해서 알려주세요.")
print("="*50)