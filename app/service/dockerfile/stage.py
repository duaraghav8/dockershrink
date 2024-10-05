from .image import Image


class Stage:
    _index: int
    _name: str

    def __init__(self, index: int, name: str):
        self._index = index
        self._name = name

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
        Returns all layers part of this stage.
        Returns a List of instances of Layer or subclasses of Layer
        """
        pass

    def baseimage(self) -> Image:
        """
        Returns the base image used in the stage
         eg- "FROM ubuntu:latest" -> returns ubuntu:latest as Image object
        """
        pass

    def set_baseimage(self, image: Image):
        pass
