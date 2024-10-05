from .image import Image


class Stage:
    _index: int
    _line_num: int
    _baseimage: Image
    _name: str
    _layers: list

    def __init__(
        self, index: int, line: int, baseimage: Image, layers: list, name: str = ""
    ):
        self._index = index
        self._line_num = line
        self._baseimage = baseimage
        self._name = name
        self._layers = layers

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
        pass

    def name(self) -> str:
        """
        Returns the stage name.
        An unnamed stage (eg- final stage or the only stage in dockerfile) has
         its name set to empty string.
        """
        return self._name

    def line_num(self) -> int:
        """
        Returns the number of the line on which the stage is declared.
        """
        return self._line_num
