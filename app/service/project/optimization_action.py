class OptimizationAction:
    def __init__(
        self,
        rule: str,
        filename: str,
        title: str = "",
        description: str = "",
    ):
        self.rule = rule
        self.filename = filename
        self.title = title
        self.description = description

    def to_json(self) -> dict:
        return {
            "rule": self.rule,
            "filename": self.filename,
            "title": self.title,
            "description": self.description,
        }
