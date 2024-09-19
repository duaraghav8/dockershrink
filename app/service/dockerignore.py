class Dockerignore:
    _raw_data: str = None

    def __init__(self, contents: str):
        self._raw_data = contents

    def exists(self) -> bool:
        return self._raw_data is not None

    def create(self):
        self._raw_data = ""

    def add_if_not_present(self, entries):
        pass

    def raw(self) -> str:
        return self._raw_data
