from enum import Enum
from typing import Dict, Optional, List

from .shell_command import ShellCommand
from .stage import Stage


class LayerCommand(Enum):
    COPY = 0
    RUN = 1
    ENV = 2


class Layer:
    _command: LayerCommand

    def __init__(self, command: LayerCommand):
        self._command = command

    def command(self) -> LayerCommand:
        return self._command

    def line_num(self) -> int:
        """
        Returns the line number in the Dockerfile on which this layer begins.
        :return: int
        """
        pass

    def text(self) -> str:
        """
        :return: The complete contents of the layer as text, ie, command + parameters
        """
        pass

    def parent_stage(self) -> Stage:
        """
        Returns the Stage this layer is part of
        :return: Stage
        """
        pass

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
        pass


class EnvLayer(Layer):
    def env_vars(self) -> Dict[str, str]:
        pass


class CopyLayer(Layer):
    _src: List[str]
    _dest: str

    def __init__(self, src: List[str], dest: str):
        self._src = src
        self._dest = dest

        super().__init__(LayerCommand.COPY)

    def copies_from_build_context(self) -> bool:
        """
        Returns false if the copy statement specifies --from, true otherwise.
        Specifying --from means the statement is using external source for copying data (like a previous stage).
         eg-
         "COPY --from=build /app /app" -> False
         "COPY node_modules ." -> True
        """
        pass

    def copies_from_previous_stage(self) -> bool:
        """
        Returns true if data is copied from a previous stage of the current Dockerfile, false otherwise.
         eg-
         "COPY --from=build /app /app" -> True
         "COPY --from=nginx:latest /app /app" -> False
         "COPY node_modules ." -> False
        """
        pass

    def source_stage(self) -> Optional[Stage]:
        """
        Returns the Stage the data is being copied from.
         eg- for "COPY --from=build node_modules .", this method returns the "build" Stage object
        If this COPY statement doesn't specify "--from" or doesn't specify a stage in --from,
         this method returns None.
        """
        pass

    def src(self) -> List[str]:
        return self._src


class RunLayer(Layer):
    _shell_commands: List[ShellCommand]

    def __init__(self, shell_commands: List[ShellCommand]):
        self._shell_commands = shell_commands
        super().__init__(LayerCommand.RUN)

    def shell_commands(self) -> List[ShellCommand]:
        return self._shell_commands
