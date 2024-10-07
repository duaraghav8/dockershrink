class OptimizationAction:
    def __init__(
        self,
        rule: str,
        filename: str,
        title: str = "",
        description: str = "",
        line: int = -1,
    ):
        self.rule = rule
        self.filename = filename
        self.title = title
        self.description = description

        # NOTE: The line number provided in both actions taken and suggestions refers to
        #  the line in the new files, ie, the updated files returned by dockershrink.
        # This must also be clarified in the client(s) so the user doesn't think that
        #  line numbers are for the original files.
        self.line = line

    def to_json(self) -> dict:
        resp = {
            "rule": self.rule,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
        }
        if self.line > 0:
            resp["line"] = self.line
        return resp
