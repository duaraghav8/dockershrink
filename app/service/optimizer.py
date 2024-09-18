class Optimizer:
    dockerfile: str
    dockerignore: str
    package_json: str
    openai_api_key: str

    def __init__(self, dockerfile: str, dockerignore: str, package_json: str, openai_api_key: str):
        self.dockerfile = dockerfile
        self.dockerignore = dockerignore
        self.package_json = package_json
        self.openai_api_key = openai_api_key

    def optimize(self):
        # run the rule engine
        # if key available, call ai to analyse further
        # curate results and return response
        return {"ok": "okayyy"}
