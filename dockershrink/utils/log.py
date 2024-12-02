import logging
import json
import datetime
import os


class CustomLogger:
    def __init__(self, name: str, level: str):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)

        # Create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(level)

        # Create formatter
        formatter = logging.Formatter("%(message)s")

        # Add formatter to ch
        ch.setFormatter(formatter)

        # Add ch to logger
        self.logger.addHandler(ch)

    def _log(self, level, msg, data: dict = None):
        log_entry = {
            "timestamp": datetime.datetime.now(datetime.UTC).isoformat(),
            "level": logging.getLevelName(level),
            "message": msg,
        }
        if data:
            log_entry["data"] = data

        self.logger.log(level, json.dumps(log_entry))

    def info(self, msg, data=None):
        self._log(logging.INFO, msg, data)

    def error(self, msg, data=None):
        self._log(logging.ERROR, msg, data)

    def warning(self, msg, data=None):
        self._log(logging.WARNING, msg, data)

    def debug(self, msg, data=None):
        self._log(logging.DEBUG, msg, data)


LOG = CustomLogger(
    name="app", level=os.environ.get("DOCKERSHRINK_CLI_LOGLEVEL", "WARNING")
)
