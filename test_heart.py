# test_heart.py
try:
    from src.services import data_loader
    print("✅ data_loader 모듈 import 성공!")
    
    roster = data_loader.get_master_roster(force_update=False)
    if roster:
        print(f"✅ 명단 로드 성공: {len(roster)}명 확인됨.")
        print("🎉 심장 이식 수술 성공! 2단계 완료.")
    else:
        print("❌ 명단 로드 실패 (로그 확인 필요)")
        
except ImportError as e:
    print(f"❌ Import 에러: {e}")
except Exception as e:
    print(f"❌ 실행 에러: {e}")