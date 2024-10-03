class OptimizationAction:
    def __init__(
        self, rule: str, filename: str, title: str, description: str, line: int = -1
    ):
        self.rule = rule
        self.filename = filename
        self.title = title
        self.description = description
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
