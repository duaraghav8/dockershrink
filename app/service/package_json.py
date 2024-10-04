from typing import Optional


class PackageJSON:
    _raw_data: dict

    def __init__(self, data: dict):
        self._raw_data = data

    def get_script(self, name: str) -> Optional[str]:
        """
        Returns the commands specified for the given script.
        This is extracted from the "scripts" object of the package json.
        If the commands for the script are not present, None is returned.
        eg-
          script = "npm run build"
          name = "build"
          package.json = {"scripts": {"build": "babel ."}}
          returns = "babel ."
        """
        scripts = self._raw_data.get("scripts", {})
        return scripts.get(name)

    def raw(self) -> dict:
        return self._raw_data
