import os
from typing import List, Optional

from app.service import dockerfile as df
from app.service.ai import AIService
from app.service.dockerignore import Dockerignore
from app.service.package_json import PackageJSON
from app.utils.log import LOG

from . import helpers
from .optimization_action import OptimizationAction


class Project:
    _recommendations: List[OptimizationAction]
    _actions_taken: List[OptimizationAction]

    dockerfile: df.Dockerfile
    dockerignore: Dockerignore
    package_json: PackageJSON

    def __init__(
        self,
        dockerfile: df.Dockerfile = None,
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

        scripts = []
        if self.package_json is not None:
            scripts = helpers.extract_npm_scripts_invoked(
                self.dockerfile, self.package_json
            )

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
            new_dockerfile = df.Dockerfile(updated_dockerfile_code)
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

        action = OptimizationAction(
            rule=rule,
            filename=filename,
            title="Implemented Multistage Builds",
            description="""Multistage Builds have been applied to the Dockerfile.
A new stage has been created with a lighter base Image.
This stage only includes the application code, dependencies and any other assets necessary for running the app.""",
        )
        self._add_action_taken(action)

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

        final_stage = self.dockerfile.get_final_stage()

        final_stage_baseimage: df.Image = final_stage.baseimage()
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
        self.dockerfile.set_stage_baseimage(final_stage, preferred_image)

        action = OptimizationAction(
            rule=rule,
            filename=filename,
            title="Used a new and smaller base image for the final stage in Multistage Dockerfile",
            description=f"""Used {preferred_image.full_name()} instead of {final_stage_baseimage.full_name()} as the base image of the final stage.
This becomes the base image of the final image produced, reducing the size significantly.""",
        )
        self._add_action_taken(action)

    def _remove_unused_node_modules(self):
        # task: remove packages from package.json "dependencies" which are not actually being used in the project.
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
        #    2.1.1 NOTE: node_modules could be directly named in the COPY statement or it could be copying a directory containing the node_modules.
        #  2.2 Run step 1 for this stage
        # 3. Deps are copied from local system
        #  3.1 Replace this statement with a fresh install instruction (copy package*.json + npm install)
        # 3. No deps were installed in the final stage at all
        #  3.1 nothing to do, exit

        # HOW THE FIX WILL BE APPLIED:
        # For Step 1, the fix is easy. Get the last command that is installing deps.
        #  Add the appropriate flag to this command.
        # For step 2
        #  remove the COPY node_modules statement
        #  COPY package*.json from the same stage
        #  RUN npm install --production

        ###########################################################################
        optimization_action = OptimizationAction(
            rule="exclude-devDependencies",
            filename="Dockerfile",
        )

        # First, check the final stage for any dependency installation commands
        offending_cmd: df.ShellCommand
        offends, offending_cmd = helpers.check_stage_installs_dev_dependencies(
            self.dockerfile.get_final_stage()
        )
        if offends:
            # In case of multistage Dockerfile, if any command is found to be installing devDependencies
            #  in the final stage, fix it to only install prod deps instead.
            if self.dockerfile.get_stage_count() > 1:
                new_install_command: df.ShellCommand = (
                    helpers.apply_prod_option_to_installation_command(offending_cmd)
                )
                self.dockerfile.replace_shell_command(
                    offending_cmd, new_install_command
                )

                optimization_action.line = offending_cmd.line_num()
                optimization_action.title = (
                    "Modified installation command to exclude devDependencies"
                )
                optimization_action.description = f"""The dependency installation command in the last stage '{offending_cmd.text()}' has been modified to '{new_install_command.text()}'.
This ensures that the final image excludes all modules listed in "devDependencies" in package.json and only includes production modules needed by the app at runtime."""
                self._add_action_taken(optimization_action)

                return

            # In case of single stage dockerfile, we cannot change the command since
            #  it might break build/test processes. So add a recommendation.
            optimization_action.line = offending_cmd.line_num()
            optimization_action.title = (
                "Do not install devDependencies in the final image"
            )
            optimization_action.description = """You seem to be installing modules listed in "devDependencies" in your package.json.
These modules are suitable in the build/test phase but are not required by your app during runtime.
The final image of your app should not contain these unnecessary dependencies.
Instead, use a command like "npm install --production", "yarn install --production" or "npm ci --omit=dev" to exclude devDependencies.
This is best done using multistage builds.
Create a new (final) stage in the Dockerfile and install node_modules excluding the devDependencies."""
            self._add_recommendation(optimization_action)

            return

        # The final stage doesn't install any devDependencies.
        # Now, we need to check if it is copying node_modules from localhost or a previous stage.
        final_stage_layers = self.dockerfile.get_final_stage().layers()

        for layer in final_stage_layers:
            if layer.command() == df.LayerCommand.COPY:
                # skip if this COPY statement doesn't deal with node_modules
                if not helpers.check_layer_copies_node_modules(layer):
                    continue

                stage_count = self.dockerfile.get_stage_count()

                # TODO: Make sure this copying is correct. Will package.json be in curr dir only?
                layers_install_prod_deps_only = [
                    df.CopyLayer(src=["package*.json"], dest="./"),
                    df.RunLayer(
                        shell_commands=[
                            df.ShellCommand("npm install --production"),
                        ],
                    ),
                ]
                layers_install_prod_deps_only_text = os.linesep.join(
                    [lyr.text() for lyr in layers_install_prod_deps_only]
                )

                # If layer is copying multiple files and directories (and not just node_modules), we cannot simply
                #  delete the layer.
                # We need to only remove node_modules from it and keep the layer as-is.
                # Then add new layers to perform fresh install os node_modules.
                if len(layer.src()) > 1:
                    # TODO: Add a new COPY layer on index 0 to layers_install_prod_deps_only.
                    #  This layer is same as original, except its src list doesn't contain node_modules.
                    #  Then we don't need to add recommendation and return from this conditional,
                    #  we can let the algo continue.
                    #  This involves some effort so for now, we just add a recommendation and exit.
                    optimization_action.line = layer.line_num()
                    optimization_action.title = (
                        "Avoid copying node_modules into the final image"
                    )
                    optimization_action.description = """You seem to be copying node_modules into your final image.
Avoid this. Instead, perform a fresh dependency installation which excludes devDependencies (defined in your package.json).
Instead of "COPY", use something like "RUN npm install --production" / "RUN yarn install --production"."""
                    self._add_recommendation(optimization_action)
                    return

                # If no '--from' is specified in the COPY statement, then the node_modules are being copied
                #  from build context (local system). This should be prevented.
                if layer.copies_from_build_context():
                    # In case of single-stage dockerfile, don't try to fix this because it might break build/test.
                    # Add a recommendation instead.
                    if stage_count < 2:
                        optimization_action.line = layer.line_num()
                        optimization_action.title = (
                            "Do not copy node_modules from your local system"
                        )
                        optimization_action.description = """You seem to be copying node_modules from your local system into the final image.
Avoid this. For your final image, always perform a fresh dependency installation which excludes devDependencies (defined in your package.json).
Create a new (final) stage in your Dockerfile, copy the built code into this stage and perform a fresh install of node_modules using "npm install --production" / "yarn install --production"."""
                        self._add_recommendation(optimization_action)
                        return

                    self.dockerfile.replace_layer(layer, layers_install_prod_deps_only)

                    optimization_action.line = layer.line_num()
                    optimization_action.title = (
                        "Perform fresh install of node_modules in the final stage"
                    )
                    optimization_action.description = f"""In the last stage, the layer: {os.linesep}{layer.text()}{os.linesep} has been replaced by: {os.linesep}{layers_install_prod_deps_only_text}{os.linesep}
Copying node_modules from the local machine is not recommended.
A fresh install of production dependencies here ensures that the final image only contains modules needed for runtime, leaving out all devDependencies."""
                    self._add_action_taken(optimization_action)

                    return

                # Data is copied from external context.
                # Right now, we only support checking a previous stage in the current Dockerfile.
                # Other external contexts are ignored and no action is taken on them.
                if not layer.copies_from_previous_stage():
                    return

                source_stage = layer.source_stage()
                offends, _ = helpers.check_stage_installs_dev_dependencies(source_stage)
                if offends:
                    # If this Dockefile is single-stage, then you cannot COPY from a previous stage.
                    # So this is an illegal state.
                    if stage_count < 2:
                        # For now, we just exit because this dockerfile is semantically incorrect.
                        # TODO: Add recommendation that you cannot COPY from a previous stage.
                        return

                    # user is copying node_modules from previous stage, but the previous stage
                    #  installs devDependencies as well.
                    # So replace this COPY layer with prod dep installation
                    self.dockerfile.replace_layer(layer, layers_install_prod_deps_only)

                    optimization_action.line = layer.line_num()
                    optimization_action.title = (
                        "Perform fresh install of node_modules in the final stage"
                    )
                    optimization_action.description = f"""In the last stage, the layer: {os.linesep}{layer.text()}{os.linesep} has been replaced by: {os.linesep}{layers_install_prod_deps_only_text}{os.linesep}
It seems that you're copying node_modules from a previous stage '{source_stage.name()}' which installs devDependencies as well.
So your final image will contain unnecessary packages. 
Instead, a fresh installation of only production dependencies here ensures that the final image only contains modules needed for runtime, leaving out all devDependencies."""
                    self._add_action_taken(optimization_action)

                    return

        # The final stage also doesn't copy any node_modules into it.
        # Since it neither installs nor copies, there are no node_modules in the image.
        # Nothing to do.

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
        pass

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

        # TODO: Project should return structured python object.
        #  It is upto the user of this module, ie, the api, to convert it into json format to return api response.
        return {
            "actions_taken": self._get_actions_taken(),
            "recommendations": self._get_recommendations(),
            "modified_project": {
                "Dockerfile": self.dockerfile.raw(),
                ".dockerignore": self.dockerignore.raw(),
                "package.json": self.package_json.raw(),
            },
        }
