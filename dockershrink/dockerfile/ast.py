import os
from typing import Tuple, List, TypeAlias

import dockerfile

from .stage import Stage
from .layer import (
    LayerCommand,
    RunLayer,
    Layer,
    EnvLayer,
    CopyLayer,
    LabelLayer,
    WorkDirLayer,
    ExposeLayer,
)


class ValidationError(Exception):
    pass


ParsedDockerfile: TypeAlias = Tuple[dockerfile.Command]


def _remove_extra_empty_lines(dockerfile_content: str) -> str:
    """
    Removes extra empty lines from the given dockerfile string.
    If there is more than 1 empty line between any 2 lines of text,
    they are extra and must be removed.
    """
    max_empty_lines = 1

    result = []
    empty_line_count = 0

    for line in dockerfile_content.splitlines():
        if line.strip() == "":  # If the line is empty (just a linebreak)
            empty_line_count += 1
        else:
            if empty_line_count > max_empty_lines:
                # If more than 1 consecutive empty lines were encountered, reduce to 1
                result.extend([""] * max_empty_lines)
            else:
                # Retain up to 1 empty line
                result.extend([""] * empty_line_count)

            result.append(line)
            empty_line_count = 0

    # Handle any trailing empty lines at the end of the file
    if empty_line_count > max_empty_lines:
        result.extend([""] * max_empty_lines)
    else:
        result.extend([""] * empty_line_count)

    # Join the result with new line breaks to form the final cleaned-up string
    return os.linesep.join(result)


def create_layer(
    curr_layer_index: int, statement: dockerfile.Command, parent_stage: Stage
) -> Layer:
    """
    Creates a Layer object from the given Dockerfile statement.
    Some layers are explicitly used by the rules, so we create special subclass Layers out of them.
    eg- "RUN .." -> RunLayer(), etc
    Otherwise, we simply create a base Layer() object and return
    :return: An Instance of Layer or a child class of Layer
    """
    cmd = statement.cmd.upper()

    if cmd == LayerCommand.RUN:
        # TODO(p1): Upgrade parser so it can support parsing heredoc
        # eg-
        # """
        # RUN <<EOF
        # foo --bar && npm build
        # EOF
        # """
        # Above is a single Docker statement and should be parsed into a single dockerfile.Command(cmd="RUN",...)
        # But the dockerfile parser doesn't parse heredoc right now, so this ends up producing a RUN command
        #  with just "<<EOF" as the contents and subsequent lines are separate Command objects.
        # The parser needs to update its buildkit to support heredoc.
        # https://github.com/asottile/dockerfile/issues/174
        return RunLayer(
            index=curr_layer_index,
            statement=statement,
            parent_stage=parent_stage,
        )
    if cmd == LayerCommand.COPY:
        return CopyLayer(
            index=curr_layer_index,
            statement=statement,
            parent_stage=parent_stage,
        )
    if cmd == LayerCommand.ENV:
        return EnvLayer(
            index=curr_layer_index,
            statement=statement,
            parent_stage=parent_stage,
        )
    if cmd == LayerCommand.LABEL:
        return LabelLayer(
            index=curr_layer_index,
            statement=statement,
            parent_stage=parent_stage,
        )
    if cmd == LayerCommand.WORKDIR:
        return WorkDirLayer(
            index=curr_layer_index,
            statement=statement,
            parent_stage=parent_stage,
        )
    if cmd == LayerCommand.EXPOSE:
        return ExposeLayer(
            index=curr_layer_index,
            statement=statement,
            parent_stage=parent_stage,
        )

    return Layer(
        index=curr_layer_index,
        statement=statement,
        parent_stage=parent_stage,
    )


def create_stage(
    statements: ParsedDockerfile, start_pos: int, index: int, parent_dockerfile
) -> Stage:
    layers = []
    curr_layer_index = 0

    stage = Stage(
        parent_dockerfile=parent_dockerfile,
        index=index,
        statement=statements[start_pos],
        layers=layers,
    )

    # Populate the layers in the current stage
    for i in range(start_pos + 1, len(statements)):
        cmd = statements[i].cmd.upper()
        try:
            LayerCommand(cmd)
        except ValueError:
            raise ValidationError(
                f"Invalid Dockerfile: {statements[i].cmd} is not a valid dockerfile command"
            )

        if cmd == LayerCommand.FROM:
            # We've reached the start of the next stage, so stop constructing
            #  layers for the current one.
            break

        layer = create_layer(curr_layer_index, statements[i], stage)
        layers.append(layer)

        curr_layer_index += 1

    return stage


def create(statements: ParsedDockerfile, parent_dockerfile) -> List[Stage]:
    """
    Creates and returns the Abstract Syntax Tree from the given Commands

        The AST is based on the following idea:
         - At the top level Dockerfile is composed of multiple Stages
         - Each Stage has 0 or more Layers
         - Each Layer has a Command (eg- RUN, ENV, COPY, LABEL, etc) and more parameters based on the Command
         - A RUN Layer has 1 or more ShellCommands.

        *** AST structure (self._stages) ***
        [
          Stage(
            layers=[
              Layer(...),
              RunLayer(
                shell_commands=[
                  ShellCommand(...),
                  ...
                ]
              ),
              ...
            ]
          ),
          ...
        ]
    """
    stages = []

    # Skip to the first FROM statement
    # A Dockerfile must begin with a FROM statement to declare the first stage.
    # FROM statement can only be preceded by a comment, parser directive or an ARG statement.
    # https://docs.docker.com/reference/dockerfile/#format
    first_stage_i = 0

    for i in range(len(statements)):
        cmd = statements[i].cmd
        if cmd.upper() == LayerCommand.FROM:
            first_stage_i = i
            break
        if cmd.upper() == LayerCommand.ARG:
            # TODO: Don't ignore global ARGs. Find a way to include them in the AST.
            # Maybe the AST returned can be {"stages": [...], "global_args": [...]}
            continue

        raise ValidationError(
            f"Invalid Dockerfile: a dockerfile must begin with a FROM or ARG statement, {cmd} found"
        )

    # Construct Stages
    curr_stage_index = 0

    for i in range(first_stage_i, len(statements)):
        cmd = statements[i].cmd.upper()

        # Create a new stage when a new FROM statement is encountered.
        if cmd == LayerCommand.FROM:
            new_stage = create_stage(statements, i, curr_stage_index, parent_dockerfile)
            stages.append(new_stage)
            curr_stage_index += 1

    return stages


def flatten(stages: List[Stage]) -> str:
    """
    Converts the AST into a Dockerfile string.
    """
    dockerfile_contents: List[str] = []

    for stage in stages:
        dockerfile_contents.append(stage.text())
        dockerfile_contents.append(os.linesep * 2)

        layer: Layer
        for layer in stage.layers():
            dockerfile_contents.append(layer.text_pretty())
            dockerfile_contents.append(os.linesep)

        # Extra linebreak at the end of a Stage
        dockerfile_contents.append(os.linesep)

    flattened = "".join(dockerfile_contents).strip()
    return _remove_extra_empty_lines(flattened)
