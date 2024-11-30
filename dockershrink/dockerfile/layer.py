import os
from enum import Enum
from typing import Dict, Optional, List, Tuple

import dockerfile

from .shell_command import (
    ShellCommand,
    ShellCommandFlags,
    DockerShellCommandForm,
    split_chained_commands,
    get_flags_kv,
)
from .stage import Stage


class LayerCommand(str, Enum):
    ADD = "ADD"
    ARG = "ARG"
    CMD = "CMD"
    COPY = "COPY"
    ENTRYPOINT = "ENTRYPOINT"
    ENV = "ENV"
    EXPOSE = "EXPOSE"
    FROM = "FROM"
    HEALTHCHECK = "HEALTHCHECK"
    LABEL = "LABEL"
    MAINTAINER = "MAINTAINER"
    ONBUILD = "ONBUILD"
    RUN = "RUN"
    SHELL = "SHELL"
    STOPSIGNAL = "STOPSIGNAL"
    USER = "USER"
    VOLUME = "VOLUME"
    WORKDIR = "WORKDIR"


class Layer:
    _index: int
    _statement: dockerfile.Command
    _parent_stage: Stage
    _command: LayerCommand
    _flags: ShellCommandFlags

    def __init__(
        self,
        index: int,
        statement: dockerfile.Command,
        parent_stage: Stage,
    ):
        self._index = index
        self._statement = statement
        self._parent_stage = parent_stage
        self._command = LayerCommand(self._statement.cmd.upper())
        self._flags = get_flags_kv(self._statement.flags)

    def command(self) -> LayerCommand:
        return self._command

    def text(self) -> str:
        """
        :return: The complete contents of the layer as text, ie, command + parameters
        """
        # TODO: Don't loose the whitespace in original text
        # The dockerfile parser looses the extra whitespace in commands.
        # So in case of a command that spans over multiple lines (eg- RUN command with
        #  shell commands over multiple lines), "original" produces the original
        #  statement but without the newline.
        # So while flatten()-ing the AST, we end up removing the newline chars.
        # This doesn't corrupt the dockerfile code but makes it less legible and might
        # annoy the user.
        # eg-
        #  "RUN foo &&\
        #      bar --opt"
        # results in
        #  "RUN foo && bar --opt"
        # This makes longer RUN statements very hard to read.
        # Fix to apply: if a RunLayer has multiple ShellCommands, put them all into their own line
        #  util we reach statement.end_line. After that, put all commands on that last line.
        return self._statement.original

    def text_pretty(self) -> str:
        """
        Returns current layer's text in human-readable form.
        Child Layer classes must override this method to customize their pretty text representation.
        """
        return self._statement.original

    def parent_stage(self) -> Stage:
        """
        Returns the Stage this layer is part of
        :return: Stage
        """
        return self._parent_stage

    def index(self) -> int:
        """
        Returns the position of this layer inside the Stage.
        Layers are 0-indexed but their indices are unique only within a stage.
        eg-
          FROM ubuntu:latest
          WORKDIR /app          (layer index 0)
          RUN npm run build     (layer index 1)

          FROM node:slim
          COPY . /app           (layer index 0)
          EXPOSE 5000           (layer index 1)
        """
        return self._index

    def parsed_statement(self) -> dockerfile.Command:
        return self._statement


class EnvLayer(Layer):
    _env_vars: Dict[str, str]

    def __init__(
        self,
        index: int,
        statement: dockerfile.Command,
        parent_stage: Stage,
    ):
        super().__init__(index, statement, parent_stage)

        self._env_vars = {}
        for i in range(0, len(statement.value), 2):
            key = statement.value[i]
            value = statement.value[i + 1]
            self._env_vars[key] = value

    def env_vars(self) -> Dict[str, str]:
        return self._env_vars

    def text_pretty(self) -> str:
        """
        If this layer contains more than one env var, they're all placed on their own line.
        eg- "ENV a=b c=d"
          => ENV a=b \
                 c=d
        """
        if len(self._env_vars) == 1:
            return os.linesep + self.text() + os.linesep

        spaces = " " * (len(self._statement.cmd) + 1)
        text = f"{os.linesep}{self._statement.cmd} "

        for i in range(0, len(self._statement.value), 2):
            key = self._statement.value[i]
            value = self._statement.value[i + 1]
            to_add = f"{key}={value} \\{os.linesep}{spaces}"
            text += to_add

        text = text.rstrip().rstrip("\\").rstrip() + os.linesep
        return text


class CopyLayer(Layer):
    _src: Tuple[str]
    _dest: str

    def __init__(
        self,
        index: int,
        statement: dockerfile.Command,
        parent_stage: Stage,
    ):
        super().__init__(index, statement, parent_stage)

        # Last item in value tuple is the destination. All previous items are part of source.
        self._src = statement.value[:-1]
        self._dest = statement.value[-1]

    def copies_from_build_context(self) -> bool:
        """
        Returns false if the copy statement specifies --from, true otherwise.
        Specifying --from means the statement is using external source for copying data (like a previous stage).
         eg-
         "COPY --from=build /app /app" -> False
         "COPY node_modules ." -> True
        """
        return "from" not in self._flags

    def copies_from_previous_stage(self) -> bool:
        """
        Returns true if data is copied from a previous stage of the current Dockerfile, false otherwise.
         eg-
         "COPY --from=build /app /app" -> True
         "COPY --from=nginx:latest /app /app" -> False
         "COPY node_modules ." -> False
        """
        # TODO: Improve this logic
        # Right now, if --from is specified, we determine whether its a docker image based on
        #  whether it contains ":". This is not fool-proof.
        # Furthermore, if the string doesn't contain ":", we treat it as the name of a
        #  previous stage, and we're totally ignoring a third type of thing we can
        #  supply to --from - additional build context.
        # This is based on the assumption that most dockerfiles out there only use --from to
        #  refer to a previous stage, so this shouldn't cause much problems.
        from_value = self._flags.get("from")
        if (from_value is None) or (":" in from_value):
            return False
        return True

    def source_stage(self) -> Optional[Stage]:
        """
        Returns the Stage the data is being copied from.
         eg- for "COPY --from=build node_modules .", this method returns the "build" Stage object
        If this COPY statement doesn't specify "--from" or doesn't specify a stage in --from,
         this method returns None.
        """
        stage_name = self._flags.get("from")
        if stage_name is None:
            return None
        df = self._parent_stage.parent_dockerfile()
        return df.get_stage_by_name(stage_name)

    def src(self) -> Tuple[str]:
        return self._src


class RunLayer(Layer):
    _shell_commands: List[ShellCommand]
    _split_commands_and_operators: Tuple[str]

    def __init__(
        self,
        index: int,
        statement: dockerfile.Command,
        parent_stage: Stage,
    ):
        # Examples of RUN statements in dockerfiles:
        #  RUN npm build
        #
        #  RUN --mount=type=cache --foo=bar echo "hello" && echo "world!"
        #
        #  RUN ["echo", "hello world"]
        #
        #  RUN echo hello && \
        #  apt-get install foobar && \
        #  echo done
        #
        #  RUN <<EOF
        #  echo hello
        #  apt-get install curl -y
        #  EOF
        super().__init__(index, statement, parent_stage)

        self._shell_commands = []
        if len(statement.value) < 1:
            return

        if statement.json:
            # RUN statement uses Exec form.
            # In Exec form, Docker treats all items in the array as part of a single shell command.
            # And statement.value is a Tuple with one or more words.
            # 'RUN ["echo", "hello", "&&", "foo"]' -> statement.value=("echo", "hello", "&&", "foo",)
            sc = ShellCommand(
                index=0,
                parent_layer=self,
                cmd=statement.value,
                cmd_form=DockerShellCommandForm.EXEC,
            )
            self._shell_commands = [sc]
            return

        # RUN statement uses Shell form (eg- RUN npx depcheck && npm install --foo && echo done)
        # This means there may be 1 or more shell commands and value[0] needs to be
        #  split into individual shell commands and have their own ShellCommand object.
        # NOTE: We must also preserve the operator information ("echo hello; echo world && echo hehe")
        self._split_commands_and_operators = tuple(
            split_chained_commands(statement.value[0])
        )
        curr_cmd_index = 0

        for i in range(len(self._split_commands_and_operators)):
            # Every even-numbered index is a command and every odd-number index is an operator
            # eg- ["echo hello world", "&&", "apt-get install -y", "||", "echo done"]
            # In case of an operator, skip. In case of command, capture.
            if i % 2 == 1:
                # TODO: Capture operator information as well
                # ATM we only capture shell commands and expose to the user.
                # This is because there has been no need to expose the operators till now.
                # When there is, we need to start capturing operators here.
                continue

            curr_cmd: str = self._split_commands_and_operators[i]
            sc = ShellCommand(
                index=curr_cmd_index,
                parent_layer=self,
                cmd=(curr_cmd,),
                cmd_form=DockerShellCommandForm.SHELL,
            )
            self._shell_commands.append(sc)
            curr_cmd_index += 1

        return

    def shell_commands(self) -> List[ShellCommand]:
        return self._shell_commands

    def text_pretty(self) -> str:
        # If the command is in Exec form, no need to prettify
        if self._statement.json:
            return self.text()

        # If there's at most 1 flag and 1 shell command, no need to prettify
        if len(self._statement.flags) < 2 and len(self.shell_commands()) < 2:
            return self.text()

        spaces = " " * (len(self._statement.cmd) + 1)
        text = f"{os.linesep}{self._statement.cmd} "

        for flag in self._statement.flags:
            to_add = f"{flag} \\{os.linesep}{spaces}"
            text += to_add

        for i in range(len(self._split_commands_and_operators)):
            if i % 2 == 0:
                to_add = self._split_commands_and_operators[i]
            else:
                op = self._split_commands_and_operators[i]
                if not op == ";":
                    op = " " + op
                to_add = f"{op} \\{os.linesep}{spaces}"

            text += to_add

        text += os.linesep
        return text


class LabelLayer(Layer):
    def text_pretty(self) -> str:
        """
        If this layer contains more than one label, they're all placed on their own line.
        eg- "LABEL a=b c=d"
          => LABEL a=b \
                   c=d
        """
        if len(self._statement.value) <= 2:
            return os.linesep + self.text() + os.linesep

        spaces = " " * (len(self._statement.cmd) + 1)
        text = f"{os.linesep}{self._statement.cmd} "

        for i in range(0, len(self._statement.value), 2):
            key = self._statement.value[i]
            value = self._statement.value[i + 1]
            to_add = f"{key}={value} \\{os.linesep}{spaces}"
            text += to_add

        text = text.rstrip().rstrip("\\").rstrip() + os.linesep
        return text


class WorkDirLayer(Layer):
    def text_pretty(self) -> str:
        return os.linesep + self.text() + os.linesep


class ExposeLayer(Layer):
    def text_pretty(self) -> str:
        return os.linesep + self.text()
