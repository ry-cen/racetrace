import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    def format(self, record):
        data = {"event": record.getMessage(), **getattr(record, "fields", {})}
        if record.exc_info:
            data["error"] = self.formatException(record.exc_info)
        return json.dumps(data)


def configure():
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
