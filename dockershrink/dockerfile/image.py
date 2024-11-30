class Image:
    _name: str
    _tag: str

    def __init__(self, full_name: str):
        # TODO: Support image digest as well
        # image can also be specified with @ followed by digest hash
        # eg- "FROM node@abhst2783dhu"
        # https://docs.docker.com/reference/dockerfile/#from
        # Add a _digest property and digest() method
        components = full_name.split(":")
        self._name = components[0]
        self._tag = components[1] if len(components) > 1 else "latest"

    def name(self) -> str:
        return self._name

    def tag(self) -> str:
        return self._tag

    def full_name(self) -> str:
        return f"{self._name}:{self._tag}"

    def is_alpine_or_slim(self) -> bool:
        """
        Returns true if the image is a light one, ie, either alpine or slim
        """
        return "alpine" in self._tag or "slim" in self._tag
