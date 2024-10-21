import os
from typing import List, Optional, Tuple, TypeAlias

import dockerfile

from . import ast
from .image import Image
from .layer import Layer, RunLayer, LayerCommand
from .shell_command import (
    ShellCommand,
    ShellCommandFlagValue,
    DockerShellCommandForm,
    split_chained_commands,
    merge_chained_commands,
)
from .stage import Stage


class ValidationError(Exception):
    pass


ParsedDockerfile: TypeAlias = Tuple[dockerfile.Command]


# Contract:
# 1. Only the Dockerfile object allows writes on the Dockerfile.
# 2. All other objects such as Image, Layer, Stage, ShellCommand, etc are read-only.
# 3. Any write method called on Dockerfile object will change the internal
#    objects as well as the raw dockerfile immediately.
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
        Ensures that all docker objects are orderly indexed.
        Then updates self._raw_data to reflect dockerfile's current state.
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
                    i, curr_layer.parsed_statement(), curr_layer.parent_stage()
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
                index=i,
                parent_layer=curr_cmd.parent_layer(),
                cmd=curr_cmd.parsed_command(),
                cmd_form=curr_cmd.form(),
            )
            cmds[i] = new_cmd

    def _align_line_numbers(self):
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

        # In the original text, replace the original image full name with the new image's full name
        new_original = statement.original.replace(
            stage.baseimage().full_name(), image.full_name(), 1
        )

        new_statement = dockerfile.Command(
            value=new_values,
            original=new_original,
            cmd=statement.cmd,
            sub_cmd=statement.sub_cmd,
            json=statement.json,
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

    def add_option_to_shell_command(
        self, command: ShellCommand, key: str, value: ShellCommandFlagValue = True
    ) -> ShellCommand:
        """
        Appends the specified option to the given command.
          eg- fn(cmd("npm ci"), "omit", "dev") -> "npm ci --omit=dev"
        If the value is bool and set to True, the option is added as a flag.
          eg- fn(cmd("npm install"), "production", True) -> "npm install --production"
        If value is bool and set to False, the option is not added to the command at all.
          So nothing is modified in the Dockerfile.
        If you want true/false included, supply them as a string (eg- key="foo", value="false").

        This method returns the new ShellCommand containing the specified option.
        """
        # We need to recreate the Layer, insert new original + value fields into it.
        # Layer will create the ShellCommand itself.

        to_add = f"--{key}"
        if type(value) == str:
            to_add = f"--{key}={value}"
        elif not value:
            # value is boolean and set to False, so there's nothing to do
            return command

        parent_layer: RunLayer = command.parent_layer()
        parent_layer_statement = parent_layer.parsed_statement()
        layer_flags = " ".join(parent_layer_statement.flags)

        if command.form() == DockerShellCommandForm.EXEC:
            # Single shell command
            new_value = list(parent_layer_statement.value)
            new_value.append(to_add)

            values_json_array = [f'"{v}"' for v in new_value]
            values_json_array = ", ".join(values_json_array)

            new_original = parent_layer_statement.cmd
            if layer_flags:
                new_original += " " + layer_flags
            new_original += f" [{values_json_array}]"
        else:
            # One or more shell commands
            orig_command = parent_layer_statement.value[0]
            split_commands = split_chained_commands(orig_command)

            # multiply by 2 because split_commands list contains operators, so it has double the
            #  items of the actual command list
            cmd_to_modify = command.index() * 2
            split_commands[cmd_to_modify] += " " + to_add
            new_cmds = merge_chained_commands(split_commands)

            new_value = [new_cmds]

            new_original = parent_layer_statement.cmd
            if layer_flags:
                new_original += " " + layer_flags
            new_original += " " + new_cmds

        new_statement = dockerfile.Command(
            original=new_original,
            value=tuple(new_value),
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

        all_layers = parent_layer.parent_stage().layers()
        all_layers[parent_layer.index()] = new_layer

        self._flatten()
        return new_layer.shell_commands()[command.index()]

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

        # Layer's line number is not exposed as a formal API, so we need to get it from the parsed object.
        curr_layer_line = target.parsed_statement().start_line
        curr_layer_index = target.index()

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

        new_layer = ast.create_layer(layer.index() + 1, parsed[0], stage)
        stage.layers().insert(new_layer.index(), new_layer)

        self._flatten()
        return new_layer

    def raw(self) -> str:
        return self._raw_data
