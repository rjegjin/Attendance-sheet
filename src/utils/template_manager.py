import os
from jinja2 import Environment, FileSystemLoader

class TemplateManager:
    def __init__(self, project_root):
        # 템플릿 폴더 위치 고정 (src/templates)
        self.template_dir = os.path.join(project_root, "src", "templates")
        if not os.path.exists(self.template_dir):
            os.makedirs(self.template_dir, exist_ok=True)
            
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def render_and_save(self, template_name, context, output_path):
        """
        템플릿 파일명(html)과 데이터(context)를 받아 결과 파일로 저장
        """
        try:
            template = self.env.get_template(template_name)
            html_content = template.render(**context)
            
            # 출력 폴더가 없으면 생성
            out_dir = os.path.dirname(output_path)
            if not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)
                
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(html_content)
                
            return True
        except Exception as e:
            print(f"❌ [TemplateManager] HTML 생성 실패 ({template_name}): {e}")
            return False