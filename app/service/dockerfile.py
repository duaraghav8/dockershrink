class Dockerfile:
    _raw_data: str = None

    def __init__(self, contents: str):
        self._raw_data = contents

    def get_stage_count(self) -> int:
        pass

    def raw(self) -> str:
        return self._raw_data
