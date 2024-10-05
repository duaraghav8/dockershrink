from typing import List

from .image import Image
from .layer import Layer
from .shell_command import ShellCommand
from .stage import Stage


class ValidationError(Exception):
    pass


# Contract:
# 1. Only the Dockerfile object allows writes on the Dockerfile.
# 2. All other objects such as Image, Layer, Stage, etc are read-only.
# 3. Any write method called on Dockerfile object will change the internal
#  objects as well as the raw dockerfile immediately.
class Dockerfile:
    _raw_data: str
    _stages: List[Stage]

    def __init__(self, contents: str):
        if not contents:
            raise ValidationError(
                f"Cannot pass None or empty string for Dockerfile: {self._raw_data}"
            )
        self._raw_data = contents

        # TODO
        # validate dockerfile
        # parse and create structure, store it
        self._stages = []

    def _flatten(self):
        """
        Updates self._raw_data to reflect the current state of self._stages.
        This method converts stages into a Dockerfile string and assigns to raw_data
        """
        # TODO
        pass

    def get_stage_count(self) -> int:
        """
        Returns the number of stages in this dockerfile.
        This will always be an unsigned integer, ie, >= 0.
        """
        return len(self._stages)

    def get_all_stages(self) -> List[Stage]:
        return self._stages

    def get_final_stage(self) -> Stage:
        """
        Returns the last stage in the dockerfile
        :return: Stage
        """
        return self._stages[-1]

    def set_stage_baseimage(self, stage: Stage, image: Image):
        i = stage.index()
        if i < 0 or i > (self.get_stage_count() - 1):
            raise ValidationError(f"Given stage has invalid index: {i}")

        orig_stage = self._stages[i]
        new_stage = Stage(
            index=orig_stage.index(),
            line=orig_stage.line_num(),
            baseimage=image,
            name=orig_stage.name(),
            layers=orig_stage.layers(),
        )
        self._stages[i] = new_stage
        self._flatten()

    def replace_shell_command(self, original: ShellCommand, new: ShellCommand):
        """
        Replaces a specific shell command inside a RUN layer with a new shell command.
        """
        layer = original.parent_layer()
        stage_index = layer.parent_stage().index()

        target_stage_layers = self._stages[stage_index].layers()
        target_layer = target_stage_layers[layer.index()]
        target_layer[original.index()] = new

        self._flatten()

    def replace_layer(self, layer: Layer, new_layers: List[Layer]):
        """
        Replaces the given layer with a new set of layers.
        :param layer: the layer that already exists in the dockerfile
        :param new_layers: list of Layer objects to put in pace of the original layer
        """
        stage_index = layer.parent_stage().index()
        stage_layers = self._stages[stage_index].layers()

        i = layer.index()
        # Insert the elements of new_layers inside stage layers, right after the to-be-removed layer.
        stage_layers[i + 1 : i + 1] = new_layers
        # Remove the layer.
        stage_layers.pop(i)

    def insert_layer_after(self, layer: Layer, new_layer: Layer):
        """
        Inserts new_layer right after the given layer.
        :param layer: Layer that already exists in Dockerfile
        :param new_layer: New Layer to be added
        """
        stage_index = layer.parent_stage().index()
        stage_layers = self._stages[stage_index].layers()
        stage_layers.insert(layer.index() + 1, new_layer)

    def raw(self) -> str:
        return self._raw_data
