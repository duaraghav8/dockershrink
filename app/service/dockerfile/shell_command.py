from enum import Enum
from typing import Union, List, Dict, TypeAlias, Tuple
import bashlex

ShellCommandFlagValue: TypeAlias = Union[str, bool]
ShellCommandFlags: TypeAlias = Dict[str, ShellCommandFlagValue]


def split_chained_commands(cmd_string: str) -> List[str]:
    """
    Takes a string containing one or more shell commands chained together and splits them into individual commands.
    Also returns the operator between 2 commands.
    eg-
      "echo hello world && npx depcheck || apt-get install foo -y; /scripts/myscript.sh"
      => ["echo hello world", "&&", "npx depcheck", "||", "apt-get install foo -y", ";", "/scripts/myscript.sh"]
    """
    parsed = bashlex.parsesingle(cmd_string)

    # Single command, no operators
    if parsed.kind == "command":
        return [cmd_string]

    if not parsed.kind == "list":
        # TODO: raise exception or Log this situation.
        # We're dealing with an unexpected type of ast node.
        return []

    # Multiple commands joined by operators
    commands = []

    for node in parsed.parts:
        # If current node is an operator, simply add it to the commands list
        if node.kind == "operator":
            commands.append(node.op)
            continue
        # Otherwise just capture the entire text of the node and add it to
        # list. This is the entire shell command.
        start, end = node.pos
        cmd = cmd_string[start:end]
        commands.append(cmd)

    return commands


def merge_chained_commands(commands: List[str]) -> str:
    """
    Merges the given list of split chained commands back into a single string of shell commands.
    The main caveat is that ; operator is added right after the word, without any whitespace,
     while && and || are added with whitespace on both sides.
    """
    resp = []

    for cmd_or_op in commands:
        # In case of the ';' operator, simply attach it to the previous word
        if cmd_or_op == ";":
            resp[-1] += cmd_or_op
        else:
            resp.append(cmd_or_op)

    return " ".join(resp)


def get_flags_kv(flags: Tuple[str]) -> ShellCommandFlags:
    """
    Converts the given set of flags parsed by dockerfile parser into a dict where
     flag name is the key and flag value is the dict value.
    If a flag doesn't have an explicit value, its value is set to True.
    eg-
      ("--foo", "--bar=true", "--bax=false") => {"foo": True, "bar": True, "bax": False}
      ("--mount=type=cache,type=local") => {"mount": "type=cache,type=local"}
    """
    response = {}

    for raw_flag in flags:
        separated = raw_flag.split("=", 1)
        if len(separated) == 1:
            # Flag has no value set (eg- "--production")
            key = separated[0]
            value = True
        else:
            # Flag has a value set (eg "--security=sandbox")
            key, value = separated

            # Special case: If the value is set to "true" or "false" (or equivalents),
            #  convert to bool object.
            if value.lower() == "true":
                value = True
            elif value.lower() == "false":
                value = False

        key = key.removeprefix("--")
        response[key] = value

    return response


# Dockerfile instructions accept shell commands in 2 different formats:
# SHELL form: "ENTRYPOINT npm run start", "ENTRYPOINT npm run build && npm start"
#  shell form may contain one or more shell commands
# EXEC form: ENTRYPOINT ["npm", "run", "start"]
#  exec form only contains a single shell command
class DockerShellCommandForm(str, Enum):
    SHELL = "SHELL"
    EXEC = "EXEC"


class ShellCommand:
    _parent_layer = None
    _index: int
    _command: Tuple[str]
    _command_form: DockerShellCommandForm
    _program: str
    _args: List[str]
    _flags: ShellCommandFlags

    def __init__(
        self,
        index: int,
        parent_layer,
        cmd: Tuple[str],
        cmd_form: DockerShellCommandForm,
    ):
        self._parent_layer = parent_layer
        self._index = index
        self._command = cmd
        self._command_form = cmd_form

        self._parse_command()

    def _parse_command(self):
        """
        Parses self._command and sets values for own args, program & flags
        """
        # TODO: There is ambiguity in a command containing flags.
        # eg- "foo --option bar"
        # In this example, we don't know for sure whether to treat "bar" as the value supplied to --option
        #  or --option is a standalone flag and "bar" is an arg.
        # A static analyser cannot differentiate without knowledge of a cli program's usage.
        #
        # Right now, we use the following Heuristics which work well for most cases:
        #  word starting with "-" or "--" is captured as a standalone flag
        #   eg "--production", "--production=true" are captured, but in "--omit dev", only "--omit" gets captured
        #  word without any "-" at start is captured as args
        # This technique works well for the following cases:
        #  "npm run script-name", "npm install --production", "yarn install"
        #  "npm ci --omit=dev", "npm prune --production", "npx depcheck", "npx npm-check"
        self._args = []
        flags: List[str] = []

        if self._command_form == DockerShellCommandForm.EXEC:
            # In case of exec form, the first item in the array is the program name
            self._program = self._command[0]

            # Capture the remaining items as either flags or arguments
            for i in range(1, len(self._command)):
                word = self._command[i]
                if word.startswith("-"):
                    # Capture all flags starting with hyphen ("-r" / "--recursive")
                    # NOTE: This also captures "--" in something like "npm run test -- --grep=pattern" as flag
                    flags.append(word)
                else:
                    self._args.append(word)

            self._flags = get_flags_kv(tuple(flags))
            return

        # In case of shell form, we need to parse the command to extract the parts
        cmd_node = bashlex.parsesingle(self._command[0])
        if not cmd_node.kind == "command":
            # TODO: raise exception or Log this situation.
            # We're dealing with an unexpected type of ast node.
            return

        self._program = cmd_node.parts[0].word

        for i in range(1, len(cmd_node.parts)):
            if not cmd_node.parts[i].kind == "word":
                # If the current part is not a WordNode, it can neither be a flag nor an arg.
                # So skip it.
                continue

            word = cmd_node.parts[i].word
            if word.startswith("-"):
                flags.append(word)
            else:
                self._args.append(word)

        self._flags = get_flags_kv(tuple(flags))

    def program(self) -> str:
        """
        Returns the main program invoked as part of this command, ie, the first word in the text.
        eg- In "npm install", the program is "npm".
        """
        return self._program

    def args(self) -> List[str]:
        """
        Returns a list of arguments passed to the program.
        eg-
          "npm --foo=bar run test --production" -> ["run", "test"]
          "npm" -> []
        """
        return self._args

    def subcommand(self) -> str:
        """
        Returns the subcommand invoked for the program.
        This method is a wrapper around args()[0]
        If the command doesn't have a subcommand, this method returns empty string "".
        eg-
          For "npm --hello=world install --production --foo=bar ./", the subcommand is "install".
          For "npm" or "npm --production", the subcommand is "".
        """
        return self._args[0] if len(self._args) > 0 else ""

    def options(self) -> ShellCommandFlags:
        """
        Returns a dict of all options specified in this command.
        eg- "npm install --production --foo=bar --lorem=false" -> {"production": True, "foo": "bar", "lorem": False}
        """
        return self._flags

    def text(self) -> str:
        """
        :return: the complete shell command as a string
        """
        if self._command_form == DockerShellCommandForm.SHELL:
            return self._command[0]
        # In case of exec form, join all items in the array by space and return as full command
        # ["npm", "run", "build", "--production"] -> "npm run build --production"
        return " ".join(self._command)

    def parent_layer(self):
        """
        Returns this shell command's parent Layer (specifically, RunLayer).
        :return: RunLayer
        """
        return self._parent_layer

    def index(self) -> int:
        """
        Returns the position of this command inside the RunLayer.
        ShellCommands are 0-indexed but their indices are unique only within their Layer.
        eg-
          FROM ubuntu:latest
          RUN npm run build \\               (command layer 0)
              apt-get install foobar \\      (command layer 1)
              npm start                      (command layer 2)

          RUN npm run build \\               (command layer 0)
              apt-get install foobar \\      (command layer 1)
              npm start                      (command layer 2)
        """
        return self._index

    def parsed_command(self) -> Tuple[str]:
        return self._command

    def form(self) -> DockerShellCommandForm:
        return self._command_form
