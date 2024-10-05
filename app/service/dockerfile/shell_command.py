from typing import Union, List

from .layer import RunLayer


class ShellCommand:
    _text: str

    def __init__(self, cmd: str):
        self._text = cmd

    def line_num(self) -> int:
        """
        Returns the line number in the Dockerfile on which is resides.
        :return: int
        """
        pass

    def program(self) -> str:
        """
        Returns the main program invoked as part of this command, ie, the first word in the text.
        eg- In "npm install", the program is "npm".
        """
        pass

    def args(self) -> List[str]:
        """
        Returns a list of arguments passed to the program.
        eg-
          "npm --foo=bar run test --production" -> ["run", "test"]
          "npm" -> []
        """
        pass

    def subcommand(self) -> str:
        """
        Returns the subcommand invoked for the program.
        This method is a wrapper around args()[0]
        eg-
          For "npm --hello=world install --production --foo=bar ./", the subcommand is "install".
          For "npm", the subcommand is "".
        """
        args = self.args()
        return args[0] if len(args) > 0 else ""

    def options(self) -> dict:
        """
        Returns a dict of all options specified in this command.
        eg- "npm install --production --foo=bar --lorem=false" -> {"production": True, "foo": "bar", "lorem": False}
        """
        pass

    def text(self) -> str:
        """
        :return: the complete shell command as a string
        """
        return self._text

    def add_option(self, name: str, value: Union[str, bool]):
        """
        Adds the specified option to the command.
          eg- add_option("omit", "dev") -> "npm ci --omit=dev"
        If the value is bool and set to True, the option is added as a flag.
          If False, this method exits without making any changes to the command.
          eg- add_option("production", True) -> "npm install --production"
        """
        pass

    def parent_layer(self) -> RunLayer:
        """
        Returns this shell command's parent Layer (specifically, RunLayer).
        :return: RunLayer
        """
        pass

    def index(self) -> int:
        """
        Returns the position of this command inside the RunLayer.
        ShellCommands are 0-indexed but their indices are unique only within their Layer.
        eg-
          FROM ubuntu:latest
          RUN npm run build \\               (command layer 0)
              apt-get install foobar \\      (command layer 1)
              npm start                      (command layer 2)

          RUN npm run build \\               (command layer 0)
              apt-get install foobar \\      (command layer 1)
              npm start                      (command layer 2)
        """
        pass
