import os
import json

class StateManager:
    def __init__(self, base_dir):
        """
        base_dir: 상태 파일들이 저장될 폴더 (예: reports/checklist/status)
        """
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)

    def get_file_path(self, filename):
        return os.path.join(self.base_dir, filename)

    def load_json(self, filename, default=None):
        if default is None: default = {}
        
        path = self.get_file_path(filename)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ [StateManager] 파일 읽기 실패 ({filename}): {e}")
                return default
        return default

    def save_json(self, filename, data):
        path = self.get_file_path(filename)
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            print(f"❌ [StateManager] 파일 저장 실패 ({filename}): {e}")
            return False