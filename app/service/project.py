class Project:
    dockerfile = None
    dockerignore = None
    package_json = None
    openai_api_key = None

    def __init__(
        self,
        dockerfile=None,
        dockerignore=None,
        package_json=None,
        openai_api_key: str = None,
    ):
        self.dockerfile = dockerfile
        self.dockerignore = dockerignore
        self.package_json = package_json
        self.openai_api_key = openai_api_key

        self.suggestions = []

    def _ensure_dockerignore_best_practices(self):
        pass

    def _ensure_dockerfile_finalstage_light_baseimage(self):
        pass

    def _ensure_dockerfile_no_dev_dependencies(self):
        pass

    def ensure_dockerfile_multistage(self):
        pass

    def _ensure_dockerfile_minimum_layercount(self):
        pass

    def _ensure_dockerfile_node_prune(self):
        pass

    def generate_docker_image(self):
        return "dockerfile", "dockerignore"

    def optimize_docker_image(self):
        """
        Given all assets of the current project, this method optimises
        the Docker image definition for it.
        :return:
        """

        self._ensure_dockerignore_best_practices()
        self._ensure_dockerfile_finalstage_light_baseimage()
        self._ensure_dockerfile_no_dev_dependencies()
        self.ensure_dockerfile_multistage()
        self._ensure_dockerfile_minimum_layercount()
        self._ensure_dockerfile_node_prune()

        self.dockerfile.finalize()
        self.dockerignore.finalize()
        self.package_json.finalize()

        return {
            "suggestions": self.suggestions,
            "modified_project": {
                "Dockerfile": self.dockerfile,
                "package.json": self.package_json,
                ".dockerignore": self.dockerignore,
            }
        }
