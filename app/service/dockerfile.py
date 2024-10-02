import sys
from enum import Enum
from typing import Dict, List, Union


class ValidationError(Exception):
    pass


class StagePosition(int, Enum):
    FIRST = 0
    LAST = sys.maxsize


class Command(Enum):
    COPY = 0
    RUN = 1
    ENV = 2


class Layer:
    _command: Command
    _data: dict

    def __init__(self, command: Command, **kwargs):
        self._command = command
        self._data = kwargs

    def command(self) -> Command:
        return self._command

    def env_vars(self) -> Dict[str, str]:
        pass

    def get_run_shell_commands(self) -> list:
        """
        If the current layer is a RUN command, this method returns a list of shell commands
        that exist in this RUN layer.
        :return: list
        """
        pass

    def get_copy_statement(self):
        pass

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

    def extract_scripts_invoked(self) -> list:
        """
        Returns a list of scripts invoked in the Dockerfile and the contents (commands) inside these scripts.
        "npm start" and "npm run start" are treated as the same script.
        If start is invoked but not defined in package.json, it is treated as "node server.js".

        Example return value:
        [ {"command": "npm run build", "source": "package.json", "contents": "tsc -f ."} ]

        :return: List of scripts invoked in the dockerfile
        """
        pass

    def stage_baseimage(self, stage: int) -> Image:
        if stage < StagePosition.FIRST or stage > StagePosition.LAST:
            # TODO: Raise invalid value exception
            pass
        # TODO: return stage based on specified index

    def final_stage_baseimage(self) -> Image:
        """
        A wrapper around stage_baseimage(StagePosition.LAST)
        :return: base image of the specified stage
        """
        return self.stage_baseimage(StagePosition.LAST)

    def set_stage_baseimage(self, stage: int, image: Image):
        if stage < StagePosition.FIRST or stage > StagePosition.LAST:
            # TODO: Raise invalid value exception
            pass

    def stage_layers(self, stage: int) -> List[Layer]:
        pass

    def set_final_stage_baseimage(self, image: Image):
        """
        wrapper around set_stage_baseimage(StagePosition.LAST, image)
        :param image: the baseimage to set
        """
        self.set_stage_baseimage(StagePosition.LAST, image)

    def replace_shell_command(self, original: ShellCommand, new: ShellCommand):
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
