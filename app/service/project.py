from typing import List

import dockerfile as df

from app.service.ai import AIService
from app.service.dockerfile import Dockerfile
from app.service.dockerignore import Dockerignore
from app.service.package_json import PackageJSON
from app.utils.log import LOG


class OptimizationAction:
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
    _recommendations: List[OptimizationAction]
    _actions_taken: List[OptimizationAction]

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
        self._actions_taken = []

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
        rule = "use-multistage-builds"
        filename = "Dockerfile"

        rec = OptimizationAction(
            rule=rule,
            filename=filename,
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

        action = OptimizationAction(
            rule=rule,
            filename=filename,
            title="Implemented Multistage Builds",
            description="""Multistage Builds have been applied to the Dockerfile.
A new stage has been created with a lighter base Image.
This stage only includes the application code, dependencies and any other assets necessary for running the app.""",
        )
        self._add_action_taken(action)

        self.dockerfile = new_dockerfile

    def _remove_unnecessary_files_from_node_modules(self):
        # TODO
        # maybe node-prune or yarn clean or similar OSS tools to achieve this

        # if single stage, download node-prune after the last "npm/yarn install" and invoke it to trim down node_modules, then delete it.
        # if multistage, download node-prune as last step of second last stage. Copy node-prune into the last stage. In final stage, invoke node-prune.
        #  if there's any "npm/yarn install" in final stage, invoke the binary AFTER the install command. After this, delete node-prune.
        pass

    def _dockerfile_finalstage_use_light_baseimage(self):
        rule = "final-stage-slim-baseimage"
        filename = "Dockerfile"

        final_stage_baseimage: df.Image = self.dockerfile.final_stage_baseimage()
        if final_stage_baseimage.is_alpine_or_slim():
            # a light image is already being used, nothing to do, exit
            return

        preferred_image = df.Image("node:alpine")
        if final_stage_baseimage.name() == "node":
            preferred_image = df.Image(
                f"node:{final_stage_baseimage.alpine_equivalent_tag()}"
            )

        if self.dockerfile.get_stage_count() == 1:
            # In case of a single stage, we'll only give a recommendation.
            # This is because this stage is probably building & testing, and we don't want to cause limitations in that.
            rec = OptimizationAction(
                rule=rule,
                filename=filename,
                title="Use a smaller base image for the final image produced",
                description=f"""Use {preferred_image.full_name()} instead of {final_stage_baseimage.full_name()} as the base image.
This will significantly decrease the final image's size.
This practice is best combined with Multistage builds. The final stage of your Dockerfile must use a slim base image.
Since all testing and build processes take place in a previous stage, dev dependencies and a heavy distro isn't really needed in the final image.
Enable AI to generate code for multistage build.""",
            )
            self._add_recommendation(rec)
            return

        # Multistage builds are already being used. Modify the base image in final stage.
        LOG.debug(
            "Setting new (smaller) base image for the final stage of multistage Dockerfile",
            data={
                "dockerfile": self.dockerfile.raw(),
                "new_baseimage": preferred_image.full_name(),
            },
        )
        action = OptimizationAction(
            rule=rule,
            filename=filename,
            title="Used a new and smaller base image for the final stage in Multistage Dockerfile",
            description=f"""Used {preferred_image.full_name()} instead of {final_stage_baseimage.full_name()} as the base image of the final stage.
This becomes the base image of the final image produced, reducing the size significantly.""",
        )
        self._add_action_taken(action)

        self.dockerfile.set_final_stage_baseimage(preferred_image)

    def _remove_unused_node_modules(self):
        # According to user feedback, devs often forget to remove unused packages, resulting in bloated node_modules.
        #  Removing this has shed as much as 700MB in size!
        # user feedback - https://www.linkedin.com/feed/update/urn:li:activity:7244193836338397185?commentUrn=urn%3Ali%3Acomment%3A%28activity%3A7244193836338397185%2C7244202247755030529%29&dashCommentUrn=urn%3Ali%3Afsd_comment%3A%287244202247755030529%2Curn%3Ali%3Aactivity%3A7244193836338397185%29
        # We can probably already do this using some npm/yarn built-in functionality.

        # most popular suggestions seem to be:
        # https://github.com/depcheck/depcheck
        # https://github.com/dylang/npm-check
        pass

    def _dockerfile_exclude_dev_dependencies(self):
        # A developer writing Dockerfile must make sure to never install the devDependencies in node_modules in the final docker image - this just adds unnecessary weight to the image.
        # This method checks if the final image produced by the Dockerfile will contain the devDependencies (as specified in package.json). If yes, it applies a fix to only install production dependencies.
        # Otherwise, no action is required.

        # ALGORITHM TO CHECK FOR devDependencies:
        # The final stage must only contain prod deps
        # 1. deps are being installed in final stage
        #  1.1 look for NODE_ENV = production BEFORE any installation commands are run
        #  1.2 look for "npm install --production"
        #  1.3 look for "npm prune --omit=dev" or "npm prune --production"
        #  1.4 look for "yarn install --production"
        #  1.5 look for "npm ci --omit=dev"
        # 2. deps were installed in a previous stage and copied into the final stage
        #  2.1 Get the name of the stage from which node_modules has been copied
        #  2.2 Run step 1 for this stage
        # 3. No deps were installed in the final stage at all
        #  3.1 nothing to do, exit

        # HOW THE FIX WILL BE APPLIED:
        # For Step 1, the fix is easy. Get the last command that is installing deps.
        #  Add the appropriate flag to this command.
        # For step 2
        #  remove the COPY node_modules statement
        #  COPY package*.json from the same stage
        #  RUN npm install --production

        pass

    def _dockerfile_exclude_frontend_assets(self):
        """
        Determines whether any frontend assets are being packaged inside the image.
        If yes, this rule adds a recommendation to avoid including FE assets in the image.
        FE assets are better served via a CDN or dedicated frontend server (like nginx).
        At the moment, this rule cannot "fix" this in the Dockerfile.
        """
        pass

    def _add_recommendation(self, r: OptimizationAction):
        self._recommendations.append(r)

    def _add_action_taken(self, a: OptimizationAction):
        self._actions_taken.append(a)

    def _get_recommendations(self) -> List[dict]:
        recommendations = [r.to_json() for r in self._recommendations]
        return recommendations

    def _get_actions_taken(self) -> List[dict]:
        actions = [a.to_json() for a in self._actions_taken]
        return actions

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
        # TODO: Add actions for creating and modifying .dockerignore in self._actions_taken
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
        self._dockerfile_exclude_dev_dependencies()
        self._remove_unused_node_modules()
        self._remove_unnecessary_files_from_node_modules()

        # TODO
        # self._use_bundler()
        # self._dockerfile_exclude_frontend_assets()
        # self._dockerfile_minimize_layers()

        return {
            "actions_taken": self._get_actions_taken(),
            "recommendations": self._get_recommendations(),
            "modified_project": {
                "Dockerfile": self.dockerfile.raw(),
                ".dockerignore": self.dockerignore.raw(),
                "package.json": self.package_json.raw(),
            },
        }
