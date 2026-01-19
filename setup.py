import os
import sys
import subprocess
import platform

def create_junction(link_path, target_path):
    """
    폴더 바로가기(Junction) 생성 함수
    """
    # 1. 타겟(OneDrive 폴더)이 실제로 존재하는지 확인
    if not os.path.exists(target_path):
        print(f"   ❌ [오류] 원본 경로를 찾을 수 없습니다: {target_path}")
        return False

    # 2. 링크를 만들 자리에 이미 무언가 있는지 확인
    if os.path.exists(link_path):
        # 그것이 심볼릭 링크(또는 정션)라면 -> 삭제하고 재생성
        if os.path.islink(link_path): 
            print(f"   ⚠️  기존 링크를 감지했습니다. 업데이트합니다.")
            os.remove(link_path)
        # 진짜 폴더가 있다면 -> 경고 후 중단 (데이터 보호)
        elif os.path.isdir(link_path):
            print(f"   ⛔ [경고] '{os.path.basename(link_path)}'라는 이름의 '실제 폴더'가 이미 존재합니다.")
            print(f"      이 폴더 안에 중요한 파일이 있을 수 있어 자동으로 삭제하지 않았습니다.")
            print(f"      직접 폴더를 삭제하거나 이름을 변경한 후 다시 실행해주세요.")
            return False

    # 3. 윈도우 mklink 명령어 실행 (/J 옵션은 폴더용 Junction 생성)
    # Junction은 관리자 권한이 없어도 생성이 잘 되는 편입니다.
    try:
        if platform.system() == "Windows":
            # 명령어 구성: mklink /J "링크위치" "원본위치"
            cmd = f'mklink /J "{link_path}" "{target_path}"'
            # shell=True로 실행해야 윈도우 내부 명령어 인식
            subprocess.run(cmd, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"   ✅ [성공] 연결 완료!")
            return True
        else:
            print("   ❌ 이 스크립트는 Windows 환경 전용입니다.")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"   ❌ [실패] 시스템 권한 오류가 발생했습니다.")
        print(f"      관리자 권한으로 터미널을 다시 실행해보세요.")
        return False

def main():
    print("="*60)
    print(" 🔗 OneDrive - Git 프로젝트 연결 설정 (Setup)")
    print("="*60)
    
    # 현재 프로젝트 경로 (Git Repo)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 사용자 홈 디렉토리 찾기 (예: C:\Users\rjegj)
    user_home = os.path.expanduser("~")
    
    # 예상되는 OneDrive 경로 제안 (사용자 편의)
    default_onedrive = os.path.join(user_home, "OneDrive", "문서", "학교근무", "목일중", "Attendance")
    
    print(f"\n[1단계] OneDrive 내의 실제 데이터 폴더 경로를 입력하세요.")
    print(f"   (엔터를 치면 아래 기본 경로로 설정됩니다)")
    print(f"   기본값: {default_onedrive}")
    
    user_input = input("\n>> 경로 입력: ").strip().strip('"') # 따옴표 제거 처리
    
    # 입력이 없으면 기본값 사용
    target_base_path = user_input if user_input else default_onedrive
    
    if not os.path.exists(target_base_path):
        print(f"\n❌ 입력하신 경로에 폴더가 없습니다: {target_base_path}")
        print("   탐색기에서 경로를 복사해서 다시 시도해주세요.")
        return

    print("-" * 60)

    # 1. input 폴더 연결
    print(f"\n[2단계] 'input' 폴더 연결 중...")
    target_input = os.path.join(target_base_path, "input")
    link_input = os.path.join(current_dir, "input")
    create_junction(link_input, target_input)

    # 2. reports 폴더 연결
    print(f"\n[3단계] 'reports' 폴더 연결 중...")
    target_reports = os.path.join(target_base_path, "reports")
    link_reports = os.path.join(current_dir, "reports")
    
    # reports 폴더는 없을 수도 있으니 체크
    if not os.path.exists(target_reports):
        print(f"   ⚠️  OneDrive에 'reports' 폴더가 없어 새로 생성합니다.")
        os.makedirs(target_reports, exist_ok=True)
        
    create_junction(link_reports, target_reports)

    print("\n" + "="*60)
    print(" 🎉 모든 설정이 완료되었습니다!")
    print("    이제 'run_all.py'를 실행하면 OneDrive 데이터를 불러옵니다.")
    print("="*60)
    
    # 창이 바로 꺼지는 것 방지
    input("\n종료하려면 엔터키를 누르세요...")

if __name__ == "__main__":
    main()