import dockerfile
import dockerfile as parser

from .image import Image


class Stage:
    _parent_dockerfile = None
    _index: int
    _statement: parser.Command
    _baseimage: Image
    _name: str
    _layers: list

    def __init__(
        self,
        parent_dockerfile,
        index: int,
        statement: parser.Command,
        layers: list,
    ):
        self._parent_dockerfile = parent_dockerfile
        self._index = index
        self._statement = statement
        self._layers = layers

        # The first item in "value" tuple is the full image name
        self._baseimage = Image(self._statement.value[0])

        # By default, a stage doesn't have a name
        self._name = ""
        for i in range(len(self._statement.value)):
            # If there is a 'AS' in value tuple, the string right after it is the stage's name.
            if self._statement.value[i].upper() == "AS":
                self._name = self._statement.value[i + 1]
                break

    def parent_dockerfile(self):
        """
        Returns the Dockerfile object this stage is part of.
        """
        return self._parent_dockerfile

    def index(self) -> int:
        """
        Returns the position of this stage in the Dockerfile.
        Stages are 0-indexed.
        eg-
          FROM ubuntu:latest    (index 0)
          FROM node:slim        (index 1)
          ...
        :return:
        """
        return self._index

    def layers(self) -> list:
        """
        Returns all layers part of this stage, as a List of instances
         of Layer or subclasses of Layer.
        """
        return self._layers

    def baseimage(self) -> Image:
        """
        Returns the base image used in the stage
         eg- "FROM ubuntu:latest" -> returns ubuntu:latest as Image object
        """
        return self._baseimage

    def name(self) -> str:
        """
        Returns the stage name.
        An unnamed stage (eg- final stage or the only stage in dockerfile) has
         its name set to empty string.
        eg-
         "FROM ubuntu:latest" => ""
         "FROM ubuntu:latest AS build" => "build"
        """
        return self._name

    def text(self) -> str:
        """
        Returns the dockerfile statement that declares this stage
        eg- "FROM ubuntu:latest AS build"
        """
        return self._statement.original

    def parsed_statement(self) -> dockerfile.Command:
        return self._statement
