class ValidationError(Exception):
    pass


class Image:
    _name: str
    _tag: str

    def __init__(self, full_name: str):
        self._name, self._tag = full_name.split(":")

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


class Stage:
    def __init__(self):
        pass

    def baseimage(self) -> Image:
        pass


class Dockerfile:
    _raw_data: str

    def __init__(self, contents: str):
        self._raw_data = contents
        self._validate()

    def _validate(self):
        if not self._raw_data:
            raise ValidationError(
                f"Cannot pass None or empty string for Dockerfile: {self._raw_data}"
            )
        # TODO: Parse the dockerfile and raise error in case it is invalid / syntactically incorrect

    def get_stage_count(self) -> int:
        pass

    def extract_scripts_invoked(self) -> list:
        """
        Returns a list of scripts invoked in the Dockerfile and the contents (commands) inside these scripts.
        "npm start" and "npm run start" are treated as the same script.
        If start is invoked but not defined in package.json, it is treated as "node server.js".

        Example return value:
        [ {"command": "npm run build", "source": "package.json", "contents": "tsc -f ."} ]

        :return: List of scripts invoked in the dockerfile
        """
        pass

    def final_stage(self) -> Stage:
        pass

    def raw(self) -> str:
        return self._raw_data
