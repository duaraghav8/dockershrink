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

    def raw(self) -> str:
        return self._raw_data
