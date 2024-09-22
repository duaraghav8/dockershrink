from typing import List

import dockerfile as df

from app.service.ai import AIService
from app.service.dockerfile import Dockerfile
from app.service.dockerignore import Dockerignore
from app.service.package_json import PackageJSON
from app.utils.log import LOG


class Recommendation:
    def __init__(self, rule: str, filename: str, title: str, description: str):
        self.rule = rule
        self.filename = filename
        self.title = title
        self.description = description

    def to_json(self) -> dict:
        return {
            "rule": self.rule,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
        }


class Project:
    _recommendations: List[Recommendation]

    dockerfile: Dockerfile
    dockerignore: Dockerignore
    package_json: PackageJSON

    def __init__(
        self,
        dockerfile: Dockerfile = None,
        dockerignore: Dockerignore = None,
        package_json: PackageJSON = None,
    ):
        self.dockerfile = dockerfile
        self.dockerignore = dockerignore
        self.package_json = package_json

        self._recommendations = []

    def _dockerfile_use_multistage_builds(self, ai: AIService):
        """
        Given a single-stage Dockerfile, this method uses AI to modify it to use Multistage builds.
        The final stage in the Dockerfile uses a slim base image and only contains the application code,
          dependencies (excluding dev deps) and any other assets needed to run the app.
        If it fails to add a new stage, this method simply returns the original Dockerfile without any
          modifications.

        :param ai: AIService
        :return: Dockerfile
        """
        rec = Recommendation(
            rule="use-multistage-builds",
            filename="Dockerfile",
            title="Use Multistage Builds",
            description="""Create a final stage in Dockerfile using a slim base image such as node alpine.
Use the first stage to test and build the application.
Copy the built application code & assets into the final stage.
Set the \"NODE_ENV\" environment variable to \"production\" and install the dependencies, excluding devDependencies.""",
        )

        scripts = self.dockerfile.extract_scripts_invoked()
        try:
            updated_dockerfile_code = ai.add_multistage_builds(
                dockerfile=self.dockerfile.raw(), scripts=scripts
            )
        except Exception as e:
            LOG.error(
                f"AI service failed to add multistage builds to dockerfile: {e}",
                data={
                    "dockerfile": self.dockerfile.raw(),
                    "scripts": scripts,
                },
            )

            self._add_recommendation(rec)
            return

        try:
            new_dockerfile = Dockerfile(updated_dockerfile_code)
        except df.ValidationError as ve:
            LOG.error(
                f"dockerfile received from ai/multistage is invalid: {ve}",
                data={
                    "dockerfile": self.dockerfile.raw(),
                    "scripts": scripts,
                    "new_dockerfile": updated_dockerfile_code,
                },
            )

            self._add_recommendation(rec)
            return

        if new_dockerfile.get_stage_count() < 2:
            LOG.warning(
                "ai service could not add multistage builds to dockerfile",
                data={
                    "dockerfile": self.dockerfile.raw(),
                    "scripts": scripts,
                    "new_dockerfile": updated_dockerfile_code,
                },
            )

            self._add_recommendation(rec)
            return

        # TODO: Verify that the commands written by LLM in RUN statements are correct.
        #  Claude wrote "npm ci --only=production", which is incorrect because ci command doesn't have any such option.
        #  The "install" command actually has the --only option.

        self.dockerfile = new_dockerfile

    def _dockerfile_minimize_layers(self):
        """
        Minimizes the number of layers by combining consecutive RUN statements into a since RUN statement.
        """
        pass

    def _dockerfile_use_node_prune(self):
        """ """
        # if single stage, download node-prune after the last "npm/yarn install" and invoke it to trim down node_modules, then delete it.
        # if multistage, download node-prune as last step of second last stage. Copy node-prune into the last stage. In final stage, invoke node-prune.
        #  if there's any "npm/yarn install" in final stage, invoke the binary AFTER the install command. After this, delete node-prune.
        pass

    def _dockerfile_finalstage_use_light_baseimage(self):
        pass

    def _dockerfile_exclude_dev_dependencies(self):
        # ensure npm install --production or yarn install --production
        # alternatively, check if npm prune command is being used
        pass

    def _dockerfile_exclude_frontend_assets(self):
        """
        Determines whether any frontend assets are being packaged inside the image.
        If yes, this rule adds a recommendation to avoid including FE assets in the image.
        FE assets are better served via a CDN or dedicated frontend server (like nginx).
        At the moment, this rule cannot "fix" this in the Dockerfile.
        """
        pass

    def _add_recommendation(self, r: Recommendation = None):
        self._recommendations.append(r)

    def _get_recommendations_json(self) -> List[dict]:
        recommendations = [r.to_json() for r in self._recommendations]
        return recommendations

    def generate_docker_image_definition(self, ai=None):
        return "dockerfile", "dockerignore"

    def optimize_docker_image(self, ai: AIService = None):
        """
        Given all assets of the current project, this method optimises
        the Docker image definition for it.

        :return:
        """
        # Ensure that .dockerignore exists and contains the recommended
        # files & directories
        if not self.dockerignore.exists():
            self.dockerignore.create()
        self.dockerignore.add_if_not_present({"node_modules", "npm_debug.log", ".git"})

        # We prefer to run the AI-powered rules first, then the rule engine.
        # Always run the deterministic checks AFTER the non-deterministic ones to get better results.
        if ai:
            # First, we try to include multistage build. Using Multistage is always recommended.
            # Because in the final stage, you can just use a light base image, leave out everything and only cherry-pick
            # what you need. Nothing unknown/unexpected is present.
            # Another benefit of implementing multistage first is that all other rules execute on the final stage,
            # which is more useful than optimizing previous stage(s).
            if self.dockerfile.get_stage_count() == 1:
                self._dockerfile_use_multistage_builds(ai)

            # Rest of the rules must operate regardless of the number of stages in the Dockerfile (1 or more).
            # In case of multistage, the final stage could be either user-generated or AI-generated. Shouldn't matter.
            # TODO: All rules using AI must be moved here

        self._dockerfile_finalstage_use_light_baseimage()
        self._dockerfile_use_node_prune()
        self._dockerfile_minimize_layers()
        self._dockerfile_exclude_dev_dependencies()
        self._dockerfile_exclude_frontend_assets()

        return {
            "recommendations": self._get_recommendations_json(),
            "modified_project": {
                "Dockerfile": self.dockerfile.raw(),
                ".dockerignore": self.dockerignore.raw(),
                "package.json": self.package_json.raw(),
            },
        }
