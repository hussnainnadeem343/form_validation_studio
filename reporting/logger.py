"""Structured logging configuration for the framework."""
import logging
import sys
from datetime import datetime


def setup_logger(name: str = "generic_form_automation", level: int = logging.INFO) -> logging.Logger:
    """Configures and returns a structured logger with standard formatting."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-5s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = setup_logger()
