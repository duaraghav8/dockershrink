class Image:
    _name: str
    _tag: str

    def __init__(self, full_name: str):
        components = full_name.split(":")
        self._name = components[0]
        self._tag = components[1] if len(components) > 1 else "latest"

    def name(self) -> str:
        return self._name

    def full_name(self) -> str:
        return f"{self._name}:{self._tag}"

    def is_alpine_or_slim(self) -> bool:
        """
        Returns true if the image is a light one, ie, either alpine or slim
        :return:
        """
        pass

    def alpine_equivalent_tag(self) -> str:
        """
        Returns the alpine equivalent tag of the currently set tag.
        This tag has the same version is the current tag, but is also alpine.
        eg- current="latest", returns "alpine" | "22.9.0" => "22.9.0-alpine"
        If the current tag is already alpine, then the current tag is returned.
        :return: str Image tag
        """
        pass
