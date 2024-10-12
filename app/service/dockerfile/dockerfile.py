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
        Ensures that indices and line numbers of all docker objects are set properly.
        Then updates self._raw_data to reflect the current state of self._stages.
        This method must be called at the end of every write method in Dockerfile.
        """
        self._align_indices()
        self._align_line_numbers()
        self._raw_data = ast.flatten(self._stages)

    def _align_indices(self):
        # Stages
        for i in range(len(self._stages)):
            curr_stage = self._stages[i]
            if not curr_stage.index() == i:
                updated_stage = Stage(
                    self, i, curr_stage.parsed_statement(), curr_stage.layers()
                )
                self._stages[i] = updated_stage

            self._align_stage_layer_indices(self._stages[i])

    def _align_stage_layer_indices(self, stage: Stage):
        """
        Corrects the indices of all layers inside the given stage.
        eg-
          L1(i) = 0, L2(i) = 1, L3(i) = 1, L4(i) = 2
          => L1(i) = 0, L2(i) = 1, L3(i) = 2, L4(i) = 3
        """
        layers = stage.layers()

        for i in range(len(layers)):
            curr_layer = layers[i]
            if not curr_layer.index() == i:
                # Index is inconsistent, recreate the layer object with the correct index
                new_layer = ast.create_layer(
                    i, curr_layer.parsed_statement(), curr_layer.parent_stage
                )
                layers[i] = new_layer

            if layers[i].command() == LayerCommand.RUN:
                self._align_shellcmd_indices(layers[i])

    def _align_shellcmd_indices(self, layer: RunLayer):
        cmds = layer.shell_commands()

        for i in range(len(cmds)):
            curr_cmd = cmds[i]
            if curr_cmd.index() == i:
                continue

            new_cmd = ShellCommand(
                i,
                curr_cmd.line_num(),
                curr_cmd.parent_layer(),
                curr_cmd.parsed_command(),
                curr_cmd.form(),
            )
            cmds[i] = new_cmd

    def _align_line_numbers(self):
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
            # Every odd-numbered index contains the operator, we can skip it.
            # So we only access indices 0,2,4,6...
            for i in range(0, len(existing_cmds), 2):
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

        # Convert the given statements into AST nodes.
        # Then add these nodes inside the stage's list of layers, replacing target.

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

        self._flatten()
        return new_layers

    def insert_after_layer(self, layer: Layer, statement: str):
        """
        Inserts Dockerfile statement right after the given layer.
        :param layer: Layer that already exists in Dockerfile
        :param statement: statement to add
        """
        stage = layer.parent_stage()
        parsed = dockerfile.parse_string(statement)

        new_layer = ast.create_layer(layer.index() + 1, parsed, stage)
        stage.layers().insert(new_layer.index(), new_layer)

        self._flatten()
        return new_layer

    def raw(self) -> str:
        return self._raw_data
