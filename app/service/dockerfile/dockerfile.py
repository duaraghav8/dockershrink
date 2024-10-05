from typing import List

from .image import Image
from .layer import Layer
from .shell_command import ShellCommand
from .stage import Stage


# CONTRACT
# Internally, we operate on the AST structure, not class instances.
# Only the dockerfile object allows write methods.
#  All other objects like Layer, ShellCommand, etc only provide read methods
# Read requests - serve the structure in its current state
# write request - change the structure and immediately flatten it into new dockerfile, assign to _raw_data.
#  any writes to dockerfile should reflect immediately in the structure as well as raw dockerfile
# ideal AST structure:
# stages = [
#   {
#     "name": "",
#     "layers": [
#       {
#         "command": "RUN",
#         "text": "...",
#         "shell_commands": [
#           {
#             "text": "npm run build --production --foo=bar",
#             "program": "npm",
#             "subcommand": "run",
#             "args": ["build"]
#             "options": {"production": True, "foo": "bar"}
#           }
#         ]
#       },
#       {"command": "COPY", "text": "...", "src": "...", "dest": "..."}
#     ],
#   },
# ]


class ValidationError(Exception):
    pass


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
        pass

    def get_stage_count(self) -> int:
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
            raise ValidationError(f"Given stage has invalid index value: {i}")

        target = self._stages[i]
        target.set_baseimage(image)
        self._flatten()

    def replace_shell_command(self, original: ShellCommand, new: ShellCommand):
        """
        Replaces a specific shell command inside a RUN layer with a new shell command.
        """
        layer = original.layer()
        stage_index = layer.stage().index()

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
        stage_index = layer.stage().index()
        self._stages[stage_index].layers()

    def insert_layer_after(self, layer: Layer, new_layer: Layer):
        """
        Inserts new_layer right after the given layer.
        :param layer: Layer that already exists in Dockerfile
        :param new_layer: New Layer to be added
        """
        pass

    def raw(self) -> str:
        return self._raw_data
