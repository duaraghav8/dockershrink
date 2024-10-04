from typing import List

from .image import Image
from .layer import Layer
from .shell_command import ShellCommand
from .stage import Stage


class ValidationError(Exception):
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

    def get_all_stages(self) -> List[Stage]:
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
        Replaces the given layer with a new set of layers.
        :param layer: the layer that already exists in the dockerfile
        :param new_layers: list of Layer objects to put in pace of the original layer
        """
        pass

    def insert_layer_before(self, layer: Layer, new_layer: Layer):
        """
        Inserts new_layer right before the given layer.
        :param layer: Layer that already exists in Dockerfile
        :param new_layer: New Layer to be added
        """
        pass

    def raw(self) -> str:
        return self._raw_data
