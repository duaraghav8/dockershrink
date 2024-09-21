# Temperature should be set to a low value, we want more deterministic, fact-based results for our tasks


class AIService:
    def __init__(self, api_key):
        self.openai_api_key = api_key
