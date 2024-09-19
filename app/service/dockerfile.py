class Dockerfile:
    _raw_data: str = None

    def __init__(self, contents: str):
        self._raw_data = contents
