from typing import Dict, Optional
from dockershrink.ai import AIService
from dockershrink.package_json import PackageJSON


class Generator:
    def __init__(self, ai_service: AIService):
        self.ai = ai_service

    def generate_docker_files(self, analysis: Dict) -> Dict[str, str]:
        """Generate new optimized Docker files"""

        dockerfile = self.ai.generate_dockerfile(analysis)
        dockerignore = self.ai.generate_dockerignore(analysis)

        return {"Dockerfile": dockerfile, ".dockerignore": dockerignore}
