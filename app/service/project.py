from app.service.ai import AIService
from app.service.dockerfile import Dockerfile
from app.service.dockerignore import Dockerignore
from app.service.package_json import PackageJSON


class Project:
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

        self.recommendations = []

    def _dockerfile_use_multistage_builds(self, ai):
        """
        Given a single-stage Dockerfile, this method uses AI to modify it to use Multistage builds.
        The final stage in the Dockerfile uses a slim base image and only contains the application code,
          dependencies (excluding dev deps) and any other assets needed to run the app.
        If it fails to add a new stage, this method simply returns the original Dockerfile without any
          modifications.

        :param ai:
        :return: Dockerfile
        """

        # prep the base prompt
        # check for "npm run" commands in dockerfile, extract them from package.json and add them to prompt
        # call llm, supply prompt & dockerfile
        # questions: how do i integrate, how do i prompt, what are roles (system, user), can I re-use a prompt

        # TODO: Use different dockerfile examples to run on LLM to build and optimise the prompt
        #  If needed, check how different apps/people are doing their prompts, especially for coding tasks

        # If the dockerfile contains "npm run build" command, then extract the build command
        # from package.json and include it in the prompt.
        # In general, if there's any "npm run X" command, supply the code for X from package.json.
        # "npm start" is an alias to "npm run start". If "start" is not defined in package.json,
        # default command is "node server.js".

        # Call LLM with prompt and Dockerfile, get back the optimised file.
        # Create a new Dockerfile object with this new file to run further tests on it.
        # Check that the returned file is a valid (syntactically correct) dockerfile.
        # Check stage count. If LLM didn't add another stage, report this event for further investigation but don't throw any error, just exit

        # Verify that the commands written by llm in RUN statements are correct.
        # Claude wrote "npm ci --only=production", which is incorrect because ci command doesn't have any such option.

        # Make sure that the final stage base image uses the same nodejs version as previous stage.
        #  If it uses something like "latest", we should be consistent with that too.

        # Write rules to ensure that the multistage was done correctly
        # If any of the rules are violated, we do not apply the changes.
        # Only stick to rules you think are important

        # If all good, apply the changes to self.dockerfile. return

        pass

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
            "recommendations": self.recommendations,
            "modified_project": {
                "Dockerfile": self.dockerfile.raw(),
                ".dockerignore": self.dockerignore.raw(),
                "package.json": self.package_json.raw(),
            },
        }
