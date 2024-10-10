import os
from typing import List, Optional, Tuple, TypeAlias

import dockerfile

from . import ast
from .image import Image
from .layer import Layer, RunLayer, LayerCommand, CopyLayer, EnvLayer
from .shell_command import ShellCommand, split_chained_commands
from .stage import Stage


class ValidationError(Exception):
    pass


ParsedDockerfile: TypeAlias = Tuple[dockerfile.Command]


# Contract:
# 1. Only the Dockerfile object allows writes on the Dockerfile.
# 2. All other objects such as Image, Layer, Stage, etc are read-only.
# 3. Any write method called on Dockerfile object will change the internal
#  objects as well as the raw dockerfile immediately.
class Dockerfile:
    _raw_data: str
    _parsed: ParsedDockerfile
    _stages: List[Stage]

    def __init__(self, contents: str):
        if not contents:
            raise ValidationError(
                f"Cannot pass None or empty string for Dockerfile: {self._raw_data}"
            )

        self._raw_data = contents

        try:
            self._parsed = dockerfile.parse_string(contents)
        except dockerfile.GoParseError as e:
            raise ValidationError(f"Failed to parse Dockerfile with error: {e}")

        try:
            self._stages = ast.create(self._parsed, self)
        except ast.ValidationError as e:
            raise ValidationError(
                f"Failed to create Abstract Syntax Tree from Dockerfile: {e}"
            )

    def _flatten(self):
        """
        Updates self._raw_data to reflect the current state of self._stages.
        This method converts stages into a Dockerfile string and assigns to raw_data
        """
        self._raw_data = ast.flatten(self._stages)

    def _align_layer_indices(self, stage: Stage):
        """
        Corrects the indices of all layers inside the given stage.
        eg-
          L1(i) = 0, L2(i) = 1, L3(i) = 1, L4(i) = 2
          => L1(i) = 0, L2(i) = 1, L3(i) = 2, L4(i) = 3
        """
        layers = stage.layers()

        for i in range(len(layers)):
            curr_layer = layers[i]
            if curr_layer.index() == i:
                continue

            # Index is inconsistent, recreate the layer object with the correct index
            if curr_layer.command() == LayerCommand.RUN:
                updated_layer = RunLayer(
                    index=i,
                    parent_stage=curr_layer.parent_stage(),
                    statement=curr_layer.parsed_statement(),
                )
            elif curr_layer.command() == LayerCommand.COPY:
                updated_layer = CopyLayer(
                    index=i,
                    parent_stage=curr_layer.parent_stage(),
                    statement=curr_layer.parsed_statement(),
                )
            elif curr_layer.command() == LayerCommand.ENV:
                updated_layer = EnvLayer(
                    index=i,
                    parent_stage=curr_layer.parent_stage(),
                    statement=curr_layer.parsed_statement(),
                )
            else:
                updated_layer = Layer(
                    index=i,
                    parent_stage=curr_layer.parent_stage(),
                    statement=curr_layer.parsed_statement(),
                )

            layers[i] = updated_layer

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

    def get_stage_by_name(self, name: str) -> Optional[Stage]:
        """
        Returns the Stage object whose name is passed.
        If a stage with the given name doesn't exist, None is returned.
        """
        for stage in self._stages:
            if stage.name() == name:
                return stage
        return None

    def set_stage_baseimage(self, stage: Stage, image: Image):
        i = stage.index()
        if i < 0 or i > (self.get_stage_count() - 1):
            raise ValidationError(f"Given stage has invalid index: {i}")

        orig_stage = self._stages[i]
        statement = orig_stage.parsed_statement()

        # In a FROM statement, the first item in "value" tuple is the full image name.
        # That's what we need to replace.
        new_values = [i for i in statement.value]
        new_values[0] = image.full_name()
        new_values = tuple(new_values)

        new_statement = dockerfile.Command(
            value=new_values,
            cmd=statement.cmd,
            sub_cmd=statement.sub_cmd,
            json=statement.json,
            original=statement.original,
            start_line=statement.start_line,
            end_line=statement.end_line,
            flags=statement.flags,
        )
        new_stage = Stage(
            statement=new_statement,
            index=orig_stage.index(),
            layers=orig_stage.layers(),
            parent_dockerfile=orig_stage.parent_dockerfile(),
        )

        self._stages[i] = new_stage
        self._flatten()

    def replace_shell_command(self, target: ShellCommand, new_cmd: str) -> ShellCommand:
        """
        Replaces a specific shell command inside a RUN layer with a new shell command.
        Note that new_cmd is treated as a single shell command. Don't supply multiple commands.
        eg- "echo hello" is a good input
         "echo hello && echo world" is a bad input because there are 2 separate shell commands
         in this statement.
        """
        # We cannot simply replace the ShellCommand in the parent layer's ShellCommands list.
        # The layer also stores the parsed statement, whose values also need to be updated.
        # So, we must recreate the whole layer object with new parsed statement, then
        # replace the layer.
        parent_layer: RunLayer = target.parent_layer()
        parent_layer_statement = parent_layer.parsed_statement()

        flags_str = " ".join(parent_layer_statement.flags)

        if parent_layer_statement.json:
            # Single shell command in Exec form
            # TODO: Preserve the Exec form.
            # For now, we're ignoring it and just creating the new command in shell form.
            new_value = (new_cmd,)
            new_original = " ".join([parent_layer_statement.cmd, flags_str, new_cmd])
        else:
            # One or more shell commands in Shell form
            existing_cmds = split_chained_commands(parent_layer_statement.value[0])

            curr_cmd = 0
            for i in range(len(existing_cmds)):
                if i % 2 == 1:
                    # Skip the operator
                    continue
                if curr_cmd == target.index():
                    existing_cmds[i] = new_cmd
                    break
                curr_cmd += 1

            new_cmds_string = " ".join(existing_cmds)
            new_value = (new_cmds_string,)
            new_original = " ".join(
                [parent_layer_statement.cmd, flags_str, new_cmds_string]
            )

        new_statement = dockerfile.Command(
            original=new_original,
            value=new_value,
            cmd=parent_layer_statement.cmd,
            sub_cmd=parent_layer_statement.sub_cmd,
            json=parent_layer_statement.json,
            start_line=parent_layer_statement.start_line,
            end_line=parent_layer_statement.end_line,
            flags=parent_layer_statement.flags,
        )
        new_layer = RunLayer(
            statement=new_statement,
            index=parent_layer.index(),
            parent_stage=parent_layer.parent_stage(),
        )

        parent_stage_layers = parent_layer.parent_stage().layers()
        parent_stage_layers[parent_layer.index()] = new_layer

        self._flatten()
        return new_layer.shell_commands()[target.index()]

    def replace_layer_with_statements(
        self, target: Layer, statements: List[str]
    ) -> List[Layer]:
        """
        Replaces the given layer with a new set of statements.
        If an empty list is passed for statements, this method exits without any changes.
        :param target: the layer that already exists in the dockerfile
        :param statements: list of dockerfile statements to add in place of the target layer
        """
        if len(statements) < 1:
            return []

        parent_stage = target.parent_stage()
        all_layers = parent_stage.layers()

        statements_str = os.linesep.join(statements)
        parsed_statements = dockerfile.parse_string(statements_str)
        new_layers = []

        curr_layer_index = target.index()
        curr_layer_line = target.line_num()

        parsed_statement: dockerfile.Command
        for parsed_statement in parsed_statements:
            # Update the line number because the parser assigns these new statements
            #  line numbers starting from 1.
            updated_parsed_statement = dockerfile.Command(
                start_line=curr_layer_line,
                end_line=curr_layer_line,
                original=parsed_statement.original,
                value=parsed_statement.value,
                cmd=parsed_statement.cmd,
                sub_cmd=parsed_statement.sub_cmd,
                json=parsed_statement.json,
                flags=parsed_statement.flags,
            )
            new_layers.append(
                ast.create_layer(
                    curr_layer_index, updated_parsed_statement, parent_stage
                )
            )
            curr_layer_index += 1
            curr_layer_line += 1

        all_layers[target.index()] = new_layers[0]
        for i in range(1, len(new_layers)):
            all_layers.insert(new_layers[i].index(), new_layers[i])

        # TODO(p0)
        # Update line numbers and indices of all subsequent layers
        # Indices mut be modified only within the parent stage
        # but line numbers must be revised for all subsequent statements
        self._align_layer_indices(parent_stage)

        self._flatten()
        return new_layers

    def insert_after_layer(self, layer: Layer, statement: str):
        """
        Inserts statement right after the given layer.
        :param layer: Layer that already exists in Dockerfile
        :statement str: statement to add
        """
        # TODO(p0): create new_layer using statement
        #  reimplement the write methods
        stage_index = layer.parent_stage().index()
        stage_layers = self._stages[stage_index].layers()
        stage_layers.insert(layer.index() + 1, new_layer)

        return new_layer

    def raw(self) -> str:
        return self._raw_data
