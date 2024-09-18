class ImageDefinitionGenerator:
    package_json: str
    openai_api_key: str

    def __init__(self, package_json: str, openai_api_key: str):
        self.package_json = package_json
        self.openai_api_key = openai_api_key

    def generate(self):
        return "dockerfile", "dockerignore"
