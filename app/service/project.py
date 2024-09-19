class Project:
    dockerfile: Dockerfile
    dockerignore: Dockerignore
    package_json: PackageJSON

    def __init__(
        self,
        dockerfile: Dockerfile,
        dockerignore: Dockerignore,
        package_json: PackageJSON,
    ):
        self.dockerfile = dockerfile
        self.dockerignore = dockerignore
        self.package_json = package_json

        self.suggestions = []

    def _ensure_dockerfile_finalstage_light_baseimage(self):
        pass

    def _dockerfile_use_multistage_builds(self):
        # Light base image, preferably NODE_ENV=production
        pass

    def generate_docker_image(self, ai=None):
        return "dockerfile", "dockerignore"

    def optimize_docker_image(self, ai=None):
        """
        Given all assets of the current project, this method optimises
        the Docker image definition for it.

        TODO: Should each rule get the original dockerfile+assets?
         Or should each rule receive the assets that have been
         optimised by the previous rules till now?

         original:
         -

         No 2 fixes can conflict with each other. If this happens,
         We must report it as an ERROR log and investigate the cause.
         + The rule engine should apply the first fix and ignore the
         second one.

        :return:
        """
        # Ensure that .dockerignore exists and contains the recommended
        # files & directories
        if not self.dockerignore.exists():
            self.dockerignore.create()
        self.dockerignore.add_if_not_present(
            ["node_modules", "npm_debug.log", ".git"]
        )

        # First, we try to include multistage build. Using Multistage builds is always recommended.
        # Because in the final stage, you can just use a light base image, leave out everything and only cherry-pick
        # what you need.
        # Only the things that you consciously include are present, there is no data or apps which were a side effect of
        # some process.
        # Another benefit of ensuring multistage first is that all other rules execute on the final (optimised) stage.
        # It doesn't matter if the final stage was already user-provided or generated by dockershrink.
        if self.dockerfile.get_stage_count() == 1:
            self._dockerfile_use_multistage_builds()

        self._dockerfile_finalstage_use_light_baseimage()
        self._dockerfile_exclude_dev_dependencies()
        self._dockerfile_minimize_layercount()
        self._dockerfile_use_node_prune()
        self._exclude_frontend_assets()

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
