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

    def analyze(self) -> dict:
        """
        Analyze package.json and return the analysis results.
        project_info = f
            # Package name: {package_json_analysis['name']}
            # Entry point: {package_json_analysis['main']}
            # Has build script: {package_json_analysis['has_build_script']}
            # Has start script: {package_json_analysis['has_start_script']}
            # Scripts available: {list(package_json_analysis['scripts'].keys())}
            #
        """
        return {
            "name": self.raw().get("name", ""),
            "main": self.raw().get("main", ""),
            "has_build_script": "build" in self.raw().get("scripts", {}),
            "has_start_script": "start" in self.raw().get("scripts", {}),
            "scripts": self.raw().get("scripts", {}),
            "dependencies": self.raw().get("dependencies", {}),
        }
