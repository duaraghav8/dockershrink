from typing import Optional, Dict, List

from app.service.dockerfile import (
    Dockerfile,
    ShellCommand,
    CopyLayer,
    Stage,
    LayerCommand,
)
from app.service.package_json import PackageJSON

NODE_ENV_PRODUCTION = "production"

node_dependency_installation_commands = {
    "npm": {
        "install": {"production": True, "omit": "dev"},
        "i": {"production": True, "omit": "dev"},
        "add": {"production": True, "omit": "dev"},
        "ci": {"omit": "dev"},
        "clean-install": {"omit": "dev"},
        "install-clean": {"omit": "dev"},
    },
    "yarn": {
        "install": {"production": True},
    },
}
node_dev_dependency_removal_commands = {
    "npm": {
        "prune": {
            "omit": "dev",
            "production": True,  # Older versions of npm allowed --production with prune
        },
    },
}


def extract_npm_scripts_invoked(
    dockerfile: Dockerfile, package_json: PackageJSON
) -> List[Dict[str, str]]:
    """
    Returns a list of scripts invoked in the Dockerfile and the contents (commands) inside these scripts.
    "npm start" and "npm run start" are treated as the same script.
    If start is invoked but not defined in package.json, it is treated as "node server.js".

    Example return value:
    [ {"command": "npm run build", "source": "package.json", "contents": "tsc -f ."} ]

    :return: List of scripts invoked in the dockerfile
    """
    scripts = []

    stage: Stage
    for stage in dockerfile.get_all_stages():
        for layer in stage.layers():
            if not layer.command() == LayerCommand.RUN:
                continue

            cmd: ShellCommand
            for cmd in layer.shell_commands():
                if not cmd.program() == "npm":
                    continue

                subcmd = cmd.subcommand()
                text = cmd.text()

                if subcmd == "start":
                    # This is equivalent to "npm run start"
                    contents = package_json.get_script("start")
                    if contents is None:
                        contents = "node server.js"

                    scripts.append(
                        {
                            "command": text,
                            "script_contents": contents,
                        },
                    )

                elif subcmd in ["run", "run-script"]:
                    # command structure is: "npm run <script name>"
                    # args[0] is the subcommand, so args[1] is always the script to invoke
                    script_name = cmd.args()[1]

                    contents = package_json.get_script(script_name)
                    if contents is None:
                        if script_name == "start":
                            contents = "node server.js"
                        else:
                            # NOTE: This is symantecally incorrect.
                            # An npm script is invoked, but it doesn't contain a corresponding definition
                            #  in package.json.
                            contents = "(No Definition found in package.json)"

                        scripts.append(
                            {
                                "command": text,
                                "script_contents": contents,
                            },
                        )

    return scripts


def check_command_installs_node_modules(shell_command: ShellCommand) -> bool:
    """
    Returns true if the given command installs node dependencies, false otherwise.
    There can be multiple commands for installing deps, like "npm install", "yarn install",
     "npm ci", etc.
    :param shell_command: the command to analyse
    """
    program = shell_command.program()
    if program not in node_dependency_installation_commands:
        return False

    subcommand = shell_command.subcommand()
    if subcommand not in node_dependency_installation_commands[program]:
        return False

    return True


def check_install_command_uses_prod_option(shell_command: ShellCommand) -> bool:
    """
    Returns true if the given node dependency installation command uses production option, ie, the command
      only installs prod dependencies.
    Returns false otherwise, ie, the command installs devDependencies as well.
    """
    program = shell_command.program()
    subcommand = shell_command.subcommand()
    prod_options = node_dependency_installation_commands[program][subcommand]
    specified_options = shell_command.options()

    for opt, val in specified_options.items():
        if opt in prod_options and prod_options[opt] == val:
            return True

    # We iterated through all the options, none of them were prod options
    return False


def check_command_removes_dev_dependencies(
    shell_command: ShellCommand, node_env: str
) -> bool:
    """
    Returns true if the given command deletes devDependencies, false otherwise.
    eg- "npm prune --omit=dev" does this.
    :param shell_command: the command to analyse
    :param node_env: current value of NODE_ENV environment variable
    """
    program = shell_command.program()
    if program not in node_dev_dependency_removal_commands:
        return False

    subcommand = shell_command.subcommand()
    if subcommand not in node_dev_dependency_removal_commands[program]:
        return False

    if node_env == NODE_ENV_PRODUCTION:
        return True

    dev_dep_options = node_dev_dependency_removal_commands[program][subcommand]
    specified_options = shell_command.options()

    for opt, val in specified_options.items():
        if opt in dev_dep_options and dev_dep_options[opt] == val:
            return True

    # A deletion command is being used, but it is not deleting the devDependencies.
    return False


def apply_prod_option_to_installation_command(
    shell_command: ShellCommand,
) -> ShellCommand:
    program = shell_command.program()
    subcommand = shell_command.subcommand()
    prod_opts = node_dependency_installation_commands[program][subcommand]

    prod_opt_name = list(prod_opts)[0]
    prod_opt_value = prod_opts[prod_opt_name]

    from copy import deepcopy

    new_cmd = deepcopy(shell_command)

    new_cmd.add_option(name=prod_opt_name, value=prod_opt_value)
    return new_cmd


def check_layer_copies_node_modules(layer: CopyLayer) -> bool:
    """
    Returns true if the given COPY layer copies node_modules into the image stage, false otherwise.
    It only checks for node_modules as the base directory.
    If the layer copies a different directory which may contain node_modules, this method cannot detect that.
    eg-
     "COPY --from=build /app/node_modules ." -> True
     "COPY /app /app" -> False (even if app directory contains node_modules inside it)
    """
    import os.path

    for src in layer.src():
        if os.path.basename(src) == "node_modules":
            return True

    return False


def check_stage_installs_dev_dependencies(
    stage: Stage,
) -> (bool, Optional[ShellCommand]):
    """
    Determines if the given stage installs devDependencies.
    If the stage doesn't install node_modules at all, this function returns False, None.
    If the stage installs node_modules but without devDependencies, it returns False, None.
    But if devDependencies are also installed, it returns True, SC
      where SC is the offending shell command inside a particular RUN Layer
      (since a RUN layer can have multiple shell commands)
    """
    installs_dev_deps = False
    offending_command: Optional[ShellCommand] = None

    stage_layers = stage.layers()
    node_env_value = ""

    # Visit each layer from top to bottom.
    # When a RUN layer is encountered, check its shell commands.
    # If cmd is a dep install command:
    #  if it installs only prod deps, then unmark any violations flagged
    #  if it installs devDeps too, then mark it for violation
    # If cmd removes dev deps:
    #  unmark any violations flagged
    # By the time all layers have been scanned, we know exactly whether devDeps are installed or not.
    # The last install/prune command in the stage determines this result and that's what we return.
    for layer in stage_layers:
        cmd = layer.command()

        if cmd == LayerCommand.ENV:
            node_env_value: str = layer.env_vars().get("NODE_ENV", "")

        elif cmd == LayerCommand.RUN:
            shell_command: ShellCommand
            for shell_command in layer.shell_commands():
                if check_command_installs_node_modules(shell_command):
                    # If installation command was run with NODE_ENV=production, rule is satisfied
                    # Or if the command uses a prod option, rule is satisfied
                    # Otherwise, devDeps are being installed as well and rule is violated
                    if (
                        node_env_value == NODE_ENV_PRODUCTION
                        or check_install_command_uses_prod_option(shell_command)
                    ):
                        installs_dev_deps, offending_command = False, None
                    else:
                        installs_dev_deps, offending_command = (
                            True,
                            shell_command,
                        )

                elif check_command_removes_dev_dependencies(
                    shell_command, node_env_value
                ):
                    installs_dev_deps, offending_command = False, None

    return installs_dev_deps, offending_command


def check_command_runs_depcheck_or_npm_check(shell_command: ShellCommand) -> bool:
    """
    Returns true if the given shell command runs depcheck or npm-check, false otherwise.
    """
    # TODO: Add support for depcheck invoked via npm script
    # eg- (dockerfile) "npm run dependency_check" | (package.json) "script": {"dependency_checker": "npx depcheck"}

    # Possible ways to invoke depcheck or npm-check:
    #  npx depcheck
    #  npx npm-check
    #  depcheck
    #  npm-check
    dep_checker_programs = {"depcheck", "npm-check"}

    program = shell_command.program()
    if program in dep_checker_programs:
        return True
    if program == "npx" and shell_command.subcommand() in dep_checker_programs:
        return True

    return False
