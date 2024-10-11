from enum import Enum
from typing import Dict, Optional, List

import dockerfile

from .shell_command import (
    ShellCommand,
    ShellCommandFlags,
    split_chained_commands,
    parse_flags,
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
        self._flags = parse_flags(self._statement.flags)

    def command(self) -> LayerCommand:
        return self._command

    def line_num(self) -> int:
        """
        Returns the line number in the Dockerfile on which this layer begins.
        :return: int
        """
        return self._statement.start_line

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


class CopyLayer(Layer):
    _src: List[str]
    _dest: str

    def __init__(
        self,
        index: int,
        statement: dockerfile.Command,
        parent_stage: Stage,
    ):
        # TODO(p0): derive the info
        self._src = src
        self._dest = dest

        super().__init__(index, statement, parent_stage)

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

    def src(self) -> List[str]:
        return self._src


class RunLayer(Layer):
    _shell_commands: List[ShellCommand]

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
                line_num=statement.start_line,
                parent_layer=self,
                cmd=statement.value,
            )
            self._shell_commands = [sc]
            return

        # RUN statement uses Shell form (eg- RUN npx depcheck && npm install --foo && echo done)
        # This means there may be 1 or more shell commands and value[0] needs to be
        #  split into individual shell commands and have their own ShellCommand object.
        # NOTE: We must also preserve the operator information ("echo hello; echo world && echo hehe")
        individual_cmds = split_chained_commands(statement.value[0])
        curr_cmd_index = 0

        # TODO: Fix the logic of setting line number for ShellCommand
        # Instead, we should derive line num based on how the user actually
        # distributed the commands over single/multiple lines.
        # But the dockerfile parser removes all extraneous whitespace after
        # parsing RUN commands, so we lose info about newline characters.
        curr_cmd_line = statement.start_line

        for i in range(len(individual_cmds)):
            # Every even-numbered index is a command and every odd-number index is an operator
            # eg- ["echo hello world", "&&", "apt-get install -y", "||", "echo done"]
            # In case of an operator, skip. In case of command, capture.
            if i % 2 == 1:
                # TODO: Capture operator information as well
                # ATM we only capture shell commands and expose to the user.
                # This is because there has been no need to expose the operators till now.
                # When there is, we need to start capturing operators here.
                continue

            curr_cmd: str = individual_cmds[i]
            sc = ShellCommand(
                index=curr_cmd_index,
                line_num=curr_cmd_line,
                parent_layer=self,
                cmd=(curr_cmd,),
            )
            self._shell_commands.append(sc)
            curr_cmd_index += 1

            # If we've reached the last line number for this RUN layer, we don't
            #  increase line number for the future ShellCommands created.
            # This guarantees that we only spread the ShellCommands between
            #  statement.start_line & statement.end_line.
            if curr_cmd_line < statement.end_line:
                curr_cmd_line += 1

        return

    def shell_commands(self) -> List[ShellCommand]:
        return self._shell_commands


# CopyLayer, RunLayer constructors will remain this way
# the user should only have to supply the user-controlled stuff (shell command, src, dest).
#  Rest should be filled out internally by dockerfile package.
#  Details like index, line_num should be determined internally by dockerfile, not by user
#  user doesn't have to create the docker objects, they can just provide data and we internally create those objects
# We don't want to provide any write methods for Docker objects other than Dockerfile
#  If we provide, those methods don't modify themselves, but rather return a new object with those changes
# we can revisit dockerfile.replace_layer() api
##############
# User will only provide data, they won't provide new objects.
# Dockerfile will internally create new objects and use the data given by user


# Some modifications APIs will result in a change in object metadata(line, index).
# Should these methods update this metadata?

# The contract with user is that any change made by a rule is immediately reflected in the AST and dockerfile string,
#  so the next rule operates on the updated AST.
# + If we don't update, then the AST is actually inconsistent with the newly flattened dockerfile string.
# + If we don't update line, index, the flattener MUST NOT rely on those values.
# However, a change in line number can cause incorrect reporting for future rules (if they create a suggestion, they could
#  end up giving the wrong line number. We want to give suggestions in the original Dockerfile lines).

# line_num() is used by user (project.py)
# index() is only used by dockerfile, but its still exposed as a public api

# -------------
# 1. dockerfile apis for user don't change (we must follow top-down and implement what the user needs to use not the other way)
# 2. dockerfile object will parse the raw string and get Commands. It will then assign all commands to respective docker objects.
#    This will determine the constructors of these objects.
# 3. User cannot create docker objects because they don't have appropriate info. User provides plain docker statements to add
#    eg- "COPY package*.json .", "RUN npm install --production"
#    Internally, dockerfile object uses the parser to parse these into Commands, changes their index, line num and inserts them into
#      its AST. It will then update the index and line info for all subsequent objects
# 4. When a change is made

# Problems:
# After modification, dockerfile must change the index & line info for all subsequent ast nodes where applicable
# objects must provide curr_line() and original_line() & curr_index() and original_index() apis; project must use original_line()
# any new objects added in dockerfile obviosuly don't have original_line number

# TODO
# 1. project must supply complete docker statements (as strings) to dockerfile write apis. They get back the new objects created and can use them.
# 2. dockerfile write apis must accept string statements, internally create new objects, modify the AST, update metadata and return the new objects as response.
# 3. dockerfile uses parser to parse str, then creates the internal AST. Each docker objects gets its corresponding Command to parse
# 4. This causes some change in docker objects' constructors' signatures
