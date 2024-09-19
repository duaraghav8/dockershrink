class Dockerignore:
    _raw_data: str = None

    def __init__(self, contents: str):
        self._raw_data = contents

    def exists(self) -> bool:
        pass

    def create(self):
        pass

    def add_if_not_present(self, entries):
        pass

    def raw(self) -> str:
        return self._raw_data
