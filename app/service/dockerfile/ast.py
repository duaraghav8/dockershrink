import os
from typing import Tuple, List, TypeAlias

import dockerfile

from .stage import Stage
from .layer import LayerCommand, RunLayer, Layer, EnvLayer, CopyLayer, LabelLayer


class ValidationError(Exception):
    pass


ParsedDockerfile: TypeAlias = Tuple[dockerfile.Command]


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
        # TODO(p0): Add a hack to parse heredoc
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

    return "".join(dockerfile_contents).strip()
