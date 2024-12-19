import os
from typing import List

import openai

from dockershrink import dockerfile as df
from dockershrink.ai import AIService
from dockershrink.dockerignore import Dockerignore
from dockershrink.package_json import PackageJSON
from dockershrink.utils.log import LOG

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
        except openai.APIError as e:
            raise e
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
            tag = helpers.get_node_alpine_equivalent_tag_for_image(
                final_stage_baseimage
            )
            preferred_image = df.Image(f"node:{tag}")

        if self.dockerfile.get_stage_count() == 1:
            # In case of a single stage, we'll only give a recommendation.
            # This is because this stage is probably building & testing, and we don't want to cause limitations in that.
            rec = OptimizationAction(
                rule=rule,
                filename=filename,
                title="Use a smaller base image for the final image produced",
                description=f"""Use \'{preferred_image.full_name()}\' instead of \'{final_stage_baseimage.full_name()}\' as the base image.
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
            description=f"""Used \'{preferred_image.full_name()}\' instead of \'{final_stage_baseimage.full_name()}\' as the base image of the final stage.
This becomes the base image of the final image produced, reducing the size significantly.""",
        )
        self._add_action_taken(action)

    def _dockerfile_use_depcheck(self):
        """
        Ensures that depcheck or npm-check is being used in the Dockerfile.
        If not, this method adds a layer to run "npx depcheck".
        In case of any unused dependencies, depcheck will fail the image build process
         and the user must delete the packages from package.json.
        """
        # TODO: Evaluate using AI for this whole method rather than rule engine.
        # Because adding the depcheck command layer at the right place in the dockerfile
        #  requires a analysing the file at every step.

        # TODO: Add functionality to remove the packages flagged by depcheck from package.json.
        # For now, we simply integrate depcheck in the Dockerfile.
        # This fails the image build if any unused dependencies are detected.
        # This is already helpful. But ideally, we want to remove these deps ourselves.
        # But currently there are 2 challenges with that:
        #  1. Depcheck might be giving false positives sometimes. In such cases, we can't decide on the user's behalf
        #     (Maybe they just want depcheck to --ignore those packages).
        #  2. Depcheck itself doesn't provide an option to remove these packages.
        #     So to remove, we need to implement a mechanism on top of depcheck to remove them, which is more effort.

        # Add depcheck command as early as possible in the dockerfile, but only
        #  after package.json and source code have been copied into the docker image.
        # Since its difficult and fuzzy to determine this with static analysis, we add
        #  depcheck command after the last COPY statement that copies data from the
        #  build context.
        #
        #  eg-
        #  1. COPY ./part1 .
        #  2. COPY ./part2 .
        #  3. COPY --from=foo ...
        #
        # In the above example, we insert the depcheck command layer after line 2
        # This trick is still not fool-proof but will yield good results for most sane dockerfiles.

        last_copy_layer: df.CopyLayer = None

        stage: df.Stage
        for stage in self.dockerfile.get_all_stages():
            for layer in stage.layers():
                # Keep track of the last COPY layer encountered in the dockerfile that copies data
                #  from the build context, ie, that doesn't use the --from option.
                if (
                    layer.command() == df.LayerCommand.COPY
                    and layer.copies_from_build_context()
                ):
                    last_copy_layer = layer
                    continue

                if layer.command() == df.LayerCommand.RUN:
                    for shell_cmd in layer.shell_commands():
                        # If depcheck or npm-check is already being used anywhere in the Dockerfile,
                        #  then the user is already aware of those tools and we don't need to optimize anything.
                        if helpers.check_command_runs_depcheck_or_npm_check(shell_cmd):
                            return

        if last_copy_layer is None:
            # If there are no COPY layers that copy from build context OR
            #  there are simply no COPY layers at all, then we don't need
            #  to add depcheck because we assume that the user hasn't included
            #  any package*json files and doesn't intend to download any deps.
            return

        depcheck_layer: df.RunLayer = self.dockerfile.insert_after_layer(
            last_copy_layer, "RUN npx depcheck"
        )

        action = OptimizationAction(
            rule="use-depcheck",
            filename="Dockerfile",
            title="Added depcheck to detect unused dependencies",
            description=f"""Added{os.linesep}```{os.linesep}{depcheck_layer.text()}{os.linesep}```{os.linesep}right after{os.linesep}```{os.linesep}{last_copy_layer.text()}{os.linesep}```{os.linesep}
Depcheck flags all dependencies listed in package.json but not actually used in the project.
If any unused dependencies are found, depcheck exits with a non-zero code, causing "docker build" to fail.
You need to either remove these dependencies from package.json or ignore them in depcheck using the --ignores option.
NOTE: You may need to change where exactly you want to run depcheck within your Dockerfile.""",
        )
        self._add_action_taken(action)

    def _dockerfile_exclude_dev_dependencies(self):
        """
        Checks if the final image produced by the Dockerfile will contain devDependencies (as defined in package.json).
        If yes, it applies a fix to only install production dependencies.
        Otherwise, no action is taken.
        """
        # SCENARIOS
        # 1. Deps are being installed in the final stage.
        #    The installation command should contain an option to exclude dev deps (eg: --production, --omit=dev, etc)
        #    or NODE_ENV env var must be set to production.
        #    If these are not present, apply a fix/recommendation.
        #    If the first stage is also the final stage, ie, no multistage, then only give a recommendation.
        #
        # 2. Deps are installed in a previous stage and copied into the final stage
        #    Get the name of the stage in which deps are being installed.
        #    Perform scenario 1 checks on this stage.
        #    If the previous stage excludes dev deps, no further action is needed.
        #    Else, apply a fix.
        #
        # 3. Deps are copied from build context (local system)
        #    Replace this COPY statement with a fresh installation instruction (copy package*.json + npm install)
        #
        # 4. No deps are included in the final stage at all.
        #    In this case, no further action is needed.
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
                key, value = helpers.get_prod_option_for_installation_command(
                    offending_cmd
                )
                new_install_command = self.dockerfile.add_option_to_shell_command(
                    command=offending_cmd, key=key, value=value
                )

                optimization_action.title = (
                    "Modified installation command to exclude devDependencies"
                )
                optimization_action.description = f"""The dependency installation command in the last stage '{offending_cmd.text()}' has been modified to '{new_install_command.text()}'.
This ensures that the final image excludes all modules listed in "devDependencies" in package.json and only includes production modules needed by the app at runtime."""
                self._add_action_taken(optimization_action)

                return

            # In case of single stage dockerfile, we cannot change the command since
            #  it might break build/test processes. So add a recommendation.
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

                # TODO: Specify the path of package*.json relative to project root directory
                # Currently, we simply copy package*.json from build context (local) and paste into the image.
                # This will work in most cases because "docker build" is run from the root directory, which
                #  also contains the package*.json files.
                # But this isn't guaranteed.
                #  eg- package.json is supposed to be copied from src/package.json but we just wrote COPY package.json.
                # 2 good strategies to achieve this:
                #  - Check previous statements. If any of them copies package*.json, use that same path.
                #  - Get info about directory structure of the project. Then specify the precise path.
                layers_install_prod_deps_only = [
                    "COPY package*.json .",
                    "RUN npm install --production",
                ]
                layers_install_prod_deps_only_text = os.linesep.join(
                    layers_install_prod_deps_only
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
                        optimization_action.title = (
                            "Do not copy node_modules from your local system"
                        )
                        optimization_action.description = """You seem to be copying node_modules from your local system into the final image.
Avoid this. For your final image, always perform a fresh dependency installation which excludes devDependencies (defined in your package.json).
Create a new (final) stage in your Dockerfile, copy the built code into this stage and perform a fresh install of node_modules using "npm install --production" / "yarn install --production"."""
                        self._add_recommendation(optimization_action)
                        return

                    self.dockerfile.replace_layer_with_statements(
                        layer, layers_install_prod_deps_only
                    )

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
                    self.dockerfile.replace_layer_with_statements(
                        layer, layers_install_prod_deps_only
                    )

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

    def optimize_docker_image(self, ai: AIService = None):
        """
        Given all assets of the current project, this method optimises
        the Docker image definition for it.

        :return:
        """
        # Ensure that .dockerignore exists and contains the recommended entries
        if not self.dockerignore.exists():
            self.dockerignore.create()
            action = OptimizationAction(
                rule="create-dockerignore",
                filename=".dockerignore",
                title="Created .dockerignore file",
                description="Created a new .dockerignore file to exclude unnecessary files from the Docker build context.",
            )
            self._add_action_taken(action)

        entries = {"node_modules", "npm_debug.log", ".git"}
        added = self.dockerignore.add_if_not_present(entries)
        if added:
            action = OptimizationAction(
                rule="update-dockerignore",
                filename=".dockerignore",
                title="Updated .dockerignore file",
                description=f"Added the following entries to .dockerignore to exclude them from the Docker build context:\n{os.linesep.join(sorted(added))}",
            )
            self._add_action_taken(action)

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
        self._dockerfile_use_depcheck()

        # TODO(p1)
        # self._use_node_prune()
        #  OR
        # self._remove_unnecessary_files_from_node_modules()

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
            },
        }
