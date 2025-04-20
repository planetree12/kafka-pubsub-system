"""Logging configuration for the Kafka Producer."""

import logging
import sys
import structlog
import json
from typing import Dict

def configure_logging(config: Dict) -> None:
    """
    Configure logging based on the provided configuration.

    Args:
        config: The logging configuration.
    """
    log_level = getattr(logging, config["logging"]["level"])

    # Configure structlog
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    # Format as JSON or console-friendly
    if config["logging"]["format"].lower() == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure the root logger
    handler = logging.StreamHandler(sys.stdout)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(handler)

    # Don't propagate Kafka logs unless in DEBUG mode
    if log_level != logging.DEBUG:
        for logger_name in ['kafka', 'kafka.conn']:
            logger = logging.getLogger(logger_name)
            logger.propagate = False
            logger.setLevel(logging.WARNING)

    # Return a logger for the producer module
    return structlog.get_logger("producer")

def get_logger(name: str):
    """
    Get a logger for the specified module.

    Args:
        name: The module name.

    Returns:
        A structlog logger.
    """
    return structlog.get_logger(name)
