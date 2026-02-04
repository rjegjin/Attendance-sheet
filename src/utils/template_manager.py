import os
from pathlib import Path
from typing import Optional, Union, Any, Dict
from jinja2 import Environment, FileSystemLoader

from src.paths import ROOT_DIR

class TemplateManager:
    """
    Jinja2 템플릿 로딩 및 렌더링을 담당하는 매니저 클래스
    """
    def __init__(self, project_root: Optional[Union[str, Path]] = None):
        """
        Args:
            project_root: 프로젝트 루트 경로 (deprecated, src.paths.ROOT_DIR 사용 권장)
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            self.project_root = ROOT_DIR
            
        # 템플릿 폴더 위치 고정 (src/templates)
        self.template_dir = self.project_root / "src" / "templates"
        
        if not self.template_dir.exists():
            # 혹시 모를 경로 호환성을 위해 문자열 기반으로도 시도 (방어 코드)
            alt_path = os.path.join(str(self.project_root), "src", "templates")
            if os.path.exists(alt_path):
                 self.template_dir = Path(alt_path)
            else:
                 # 폴더가 없으면 생성 시도
                 self.template_dir.mkdir(parents=True, exist_ok=True)
            
        self.env = Environment(loader=FileSystemLoader(str(self.template_dir)))

    def render_and_save(self, template_name: str, context: Dict[str, Any], output_path: Union[str, Path]) -> bool:
        """
        템플릿 파일명(html)과 데이터(context)를 받아 결과 파일로 저장

        Args:
            template_name: 템플릿 파일 이름 (예: 'calendar_template.html')
            context: 템플릿에 주입할 변수 딕셔너리
            output_path: 저장할 파일 경로

        Returns:
            bool: 성공 여부
        """
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(**context)
            
            output_path = Path(output_path)
            
            # 출력 폴더가 없으면 생성
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            return True
        except Exception as e:
            print(f"❌ [TemplateManager] HTML 생성 실패 ({template_name}): {e}")
            return False
