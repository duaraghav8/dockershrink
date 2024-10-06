from enum import Enum
from typing import Dict, Optional, List, Union

from .shell_command import ShellCommand
from .stage import Stage


class LayerCommand(Enum):
    COPY = 0
    RUN = 1
    ENV = 2


class Layer:
    _index: int
    _line_num: int
    _command: LayerCommand
    _flags: Dict[str, Union[str, bool]]
    _text: str
    _parent_stage: Stage

    def __init__(
        self,
        index: int,
        line: int,
        command: LayerCommand,
        flags: Dict[str, Union[str, bool]],
        text: str,
        parent_stage: Stage,
    ):
        self._index = index
        self._line_num = line
        self._command = command
        self._flags = flags
        self._text = text
        self._parent_stage = parent_stage

    def command(self) -> LayerCommand:
        return self._command

    def line_num(self) -> int:
        """
        Returns the line number in the Dockerfile on which this layer begins.
        :return: int
        """
        return self._line_num

    def text(self) -> str:
        """
        :return: The complete contents of the layer as text, ie, command + parameters
        """
        return self._text

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


class EnvLayer(Layer):
    _env_vars: Dict[str, str]

    def __init__(
        self,
        index: int,
        line: int,
        flags: Dict[str, Union[str, bool]],
        text: str,
        parent_stage: Stage,
        env_vars: Dict[str, str],
    ):
        self._env_vars = env_vars
        super().__init__(index, line, LayerCommand.ENV, flags, text, parent_stage)

    def env_vars(self) -> Dict[str, str]:
        return self._env_vars


class CopyLayer(Layer):
    _src: List[str]
    _dest: str

    def __init__(
        self,
        index: int,
        line: int,
        text: str,
        parent_stage: Stage,
        flags: Dict[str, Union[str, bool]],
        src: List[str],
        dest: str,
    ):
        self._src = src
        self._dest = dest
        super().__init__(index, line, LayerCommand.COPY, flags, text, parent_stage)

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
        line: int,
        flags: Dict[str, Union[str, bool]],
        text: str,
        parent_stage: Stage,
        shell_commands: List[ShellCommand],
    ):
        self._shell_commands = shell_commands
        super().__init__(index, line, LayerCommand.RUN, flags, text, parent_stage)

    def shell_commands(self) -> List[ShellCommand]:
        return self._shell_commands
