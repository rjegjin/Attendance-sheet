import os
from pathlib import Path

# ==========================================
# [설정] 무시할 폴더 및 파일 패턴 목록
# ==========================================
IGNORE_DIRS = {
    '__pycache__', 
    'venv', 
    'env', 
    '.git', 
    '.idea', 
    '.vscode', 
    'node_modules', 
    'cache', 
    '.pytest_cache',
    'site-packages',
    'Lib',       # venv 내부 라이브러리 폴더 등
    'Scripts',   # venv 내부 스크립트 폴더 등
    'Include'
}

IGNORE_FILES = {
    '.DS_Store', 
    'Thumbs.db', 
    'tree.txt',          # 자기 자신 제외
    'generate_tree.py',  # 이 스크립트 제외
    'pip.exe',           # 특정 실행 파일 제외 예시
    'python.exe'
}

EXT_FILTER = [] # 예: ['.py', '.js']  <- 비워두면 모든 확장자 포함

OUTPUT_FILE = 'tree.txt'

def generate_tree(dir_path: Path, prefix: str = ""):
    """
    재귀적으로 디렉토리 트리를 문자열 리스트로 생성합니다.
    
    Args:
        dir_path (Path): 현재 탐색 중인 경로
        prefix (str): 트리 구조를 그리기 위한 접두어
    
    Returns:
        list: 트리 구조가 담긴 문자열 리스트
    """
    tree_lines = []
    
    try:
        # 1. 현재 디렉토리의 모든 아이템 가져오기
        # os.scandir이 os.listdir보다 대량 파일 처리에 효율적입니다.
        entries = list(os.scandir(dir_path))
        
        # 2. 정렬 (폴더와 파일을 섞어서 이름순으로 정렬 or 폴더 우선 정렬 가능)
        # 여기서는 윈도우 tree와 비슷하게 이름순 정렬을 수행합니다.
        entries.sort(key=lambda e: e.name.lower())

        # 3. 필터링 (설정된 무시 목록 적용)
        filtered_entries = []
        for entry in entries:
            if entry.is_dir():
                if entry.name not in IGNORE_DIRS:
                    filtered_entries.append(entry)
            else:
                if entry.name not in IGNORE_FILES:
                    # 확장자 필터가 설정되어 있다면 체크
                    if EXT_FILTER and Path(entry.name).suffix not in EXT_FILTER:
                        continue
                    filtered_entries.append(entry)

        entry_count = len(filtered_entries)

        for index, entry in enumerate(filtered_entries):
            # 마지막 아이템인지 확인 (트리 가지 모양 결정)
            is_last = (index == entry_count - 1)
            connector = "└─ " if is_last else "├─ "
            
            tree_lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                # 디렉토리인 경우 재귀 호출
                # 다음 레벨의 prefix 설정: 현재가 마지막이면 공백, 아니면 수직선 유지
                extension = "    " if is_last else "│   "
                tree_lines.extend(generate_tree(Path(entry.path), prefix + extension))

    except PermissionError:
        tree_lines.append(f"{prefix}[Access Denied]")
    except Exception as e:
        tree_lines.append(f"{prefix}[Error: {str(e)}]")

    return tree_lines

def main():
    root_dir = Path.cwd() # 현재 작업 디렉토리
    print(f"Generating tree for: {root_dir}")
    print("Filtering out useless folders...")

    lines = [f"{root_dir.name}/"]
    lines.extend(generate_tree(root_dir))
    
    # 파일 쓰기
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    
    print(f"Done! Tree structure saved to '{OUTPUT_FILE}'")

if __name__ == "__main__":
    main()