import sys
from enum import Enum
from typing import Dict, List, Union, Optional


class ValidationError(Exception):
    pass


class Image:
    _name: str
    _tag: str

    def __init__(self, full_name: str):
        components = full_name.split(":")
        self._name = components[0]
        self._tag = components[1] if len(components) > 1 else "latest"

    def name(self) -> str:
        return self._name

    def full_name(self) -> str:
        return f"{self._name}:{self._tag}"

    def is_alpine_or_slim(self) -> bool:
        """
        Returns true if the image is a light one, ie, either alpine or slim
        :return:
        """
        pass

    def alpine_equivalent_tag(self) -> str:
        """
        Returns the alpine equivalent tag of the currently set tag.
        This tag has the same version is the current tag, but is also alpine.
        eg- current="latest", returns "alpine" | "22.9.0" => "22.9.0-alpine"
        If the current tag is already alpine, then the current tag is returned.
        :return: str Image tag
        """
        pass


class Stage:
    _index: int
    _name: str

    def __init__(self, index: int, name: str):
        self._index = index
        self._name = name

    def layers(self) -> list:
        """
        Returns all layers part of this stage.
        Returns a List of instances of Layer or subclasses of Layer
        """
        pass

    def baseimage(self) -> Image:
        """
        Returns the base image used in the stage
         eg- "FROM ubuntu:latest" -> returns ubuntu:latest as Image object
        """
        pass


class LayerCommand(Enum):
    COPY = 0
    RUN = 1
    ENV = 2


class ShellCommand:
    _text: str

    def __init__(self, cmd: str):
        self._text = cmd

    def line_num(self) -> int:
        """
        Returns the line number in the Dockerfile on which is resides.
        :return: int
        """
        pass

    def program(self) -> str:
        """
        Returns the main program invoked as part of this command, ie, the first word in the text.
        eg- In "npm install", the program is "npm".
        """
        pass

    def subcommand(self) -> str:
        """
        Returns the subcommand invoked for the program.
        eg- For "npm --hello=world install --production --foo=bar ./", the subcommand is "install".
        """
        pass

    def options(self) -> dict:
        """
        Returns a dict of all options specified in this command.
        eg- "npm install --production --foo=bar --lorem=false" -> {"production": True, "foo": "bar", "lorem": False}
        """
        pass

    def text(self) -> str:
        """
        :return: the complete shell command as a string
        """
        return self._text

    def add_option(self, name: str, value: Union[str, bool]):
        """
        Adds the specified option to the command.
          eg- add_option("omit", "dev") -> "npm ci --omit=dev"
        If the value is bool and set to True, the option is added as a flag.
          If False, this method exits without making any changes to the command.
          eg- add_option("production", True) -> "npm install --production"
        """
        pass


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


class EnvLayer(Layer):
    def env_vars(self) -> Dict[str, str]:
        pass


class CopyLayer(Layer):
    _src: str
    _dest: str

    def __init__(self, src: str, dest: str):
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


class RunLayer(Layer):
    _shell_commands: List[ShellCommand]

    def __init__(self, shell_commands: List[ShellCommand]):
        self._shell_commands = shell_commands
        super().__init__(LayerCommand.RUN)

    def shell_commands(self) -> List[ShellCommand]:
        return self._shell_commands


class Dockerfile:
    _raw_data: str

    def __init__(self, contents: str):
        self._raw_data = contents
        self._validate()

        # TODO: initialize self._final_stage

    def _validate(self):
        if not self._raw_data:
            raise ValidationError(
                f"Cannot pass None or empty string for Dockerfile: {self._raw_data}"
            )
        # TODO: Parse the dockerfile and raise error in case it is invalid / syntactically incorrect

    def get_stage_count(self) -> int:
        pass

    def get_final_stage(self) -> Stage:
        """
        Returns the last stage in the dockerfile
        :return: Stage
        """
        pass

    def set_stage_baseimage(self, stage: Stage, image: Image):
        pass

    def replace_shell_command(self, original: ShellCommand, new: ShellCommand):
        """
        Replaces a specific shell command inside a RUN layer with a new shell command.
        """
        pass

    def replace_layer(self, layer: Layer, new_layers: List[Layer]):
        """
        replaces the given layer with a new set of layers.
        :param layer: the layer that already exists in the dockerfile
        :param new_layers: list of Layer objects to put in pace of the original layer
        """
        pass

    def raw(self) -> str:
        return self._raw_data
