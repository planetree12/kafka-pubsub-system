"""
Logging configuration for the consumer application.
"""
import json
import logging
import sys
from typing import Dict, Any


class JsonFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the log record.
    """
    def format(self, record):
        logobj = {}
        logobj['level'] = record.levelname
        logobj['time'] = self.formatTime(record, self.datefmt)
        logobj['message'] = record.getMessage()
        if record.exc_info:
            logobj['exception'] = self.formatException(record.exc_info)

        if hasattr(record, 'props'):
            logobj.update(record.props)

        return json.dumps(logobj)


def setup_logging(config: Dict[str, Any]) -> None:
    """
    Configure logging based on the provided configuration.

    Args:
        config: Configuration dictionary
    """
    log_level = getattr(logging, config.get('logging', {}).get('level', 'INFO'))
    log_format = config.get('logging', {}).get('format', 'json')

    root_logger = logging.getLogger()

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Only set level once
    root_logger.setLevel(log_level)

    handler = logging.StreamHandler(sys.stdout)

    if log_format.lower() == 'json':
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))

    root_logger.addHandler(handler)

    # Suppress Kafka logs
    logging.getLogger('kafka').setLevel(logging.WARNING)
