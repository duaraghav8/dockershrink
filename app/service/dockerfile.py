class ValidationError(Exception):
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

    def raw(self) -> str:
        return self._raw_data
