from datetime import datetime
import logging
import os
import sys
import argparse
from enum import Enum, auto

# Configuration and Constants

LOG_CONFIG = {
    "LOGIN_URL": "/login",
    "LOGIN_JSON_HEADERS": {"Accept": "application/json", "Content-Type": "application/json"},
    "LOG_FORMAT": "%(asctime)s | %(levelname)s | %(message)s",
    "LOG_FILE": f"logs/testlog_{datetime.now().strftime('%Y%m%d')}.log",
}

# Setup logging


def setup_logging(level=logging.INFO):
    """
    Sets up and returns a configured logger with both stdout and file handlers.
    Args:
        level (int): Logging level.
    Returns:
        logging.Logger: Configured logger.
    """
    if not os.path.isdir("logs"):
        os.mkdir("logs")

    logger = logging.getLogger(__name__)
    logger.setLevel(level)

    formatter = logging.Formatter(LOG_CONFIG["LOG_FORMAT"])

    handlers = [logging.StreamHandler(sys.stdout), logging.FileHandler(LOG_CONFIG["LOG_FILE"])]
    for handler in handlers:
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


LOGGER = setup_logging()


# configure testing modes


class TestMode(Enum):
    ALL = auto()
    SPECIFIC = auto()
    COMPARE_ONLY = auto()


def test_mode_type(value):
    try:
        return TestMode[value]
    except KeyError as e:
        raise argparse.ArgumentTypeError(f"{value} is not a valid TestMode") from e
