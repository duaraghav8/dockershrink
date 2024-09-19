class PackageJSON:
    _raw_data = None

    def __init__(self, data):
        self._raw_data = data

    def raw(self) -> str:
        return self._raw_data
