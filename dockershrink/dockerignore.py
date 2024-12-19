import os
from typing import Set, Optional


class Dockerignore:
    _raw_data: Optional[str] = None

    def __init__(self, contents: Optional[str]):
        self._raw_data = contents

    def exists(self) -> bool:
        return self._raw_data is not None

    def create(self):
        self._raw_data = ""

    def add_if_not_present(self, entries: Set[str]) -> Set[str]:
        """
        Takes a set of entries and ensures that they are included in the .dockerignore file.
        If any of the entries are not already present, this method adds them.
        :param entries: a set of strings which represent the entries that must be present in .dockerignore
        :return: a set of strings that were actually added to .dockerignore
        """
        original_entries = self._raw_data.strip().splitlines()
        original_entries = set(map(str.strip, original_entries))

        to_be_added = entries - original_entries
        if to_be_added:
            to_be_added_str = os.linesep.join(to_be_added)
            new_entries = self._raw_data.rstrip() + os.linesep + to_be_added_str
            self._raw_data = new_entries.strip()

        return to_be_added

    def raw(self) -> str:
        return self._raw_data
