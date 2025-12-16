import logging
import os
from colorlog import ColoredFormatter

def __get_logger() -> logging.Logger:
    logger = logging.getLogger(__name__)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Creates a stream handler
    handler = logging.StreamHandler()
    formatter = ColoredFormatter(
        fmt=(
        "%(log_color)s%(asctime)s.%(msecs)03d [%(levelname)-8s]%(reset)s "
        "%(cyan)s%(name)s%(reset)s.%(funcName)s:%(lineno)d - "
        "%(message_log_color)s%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={
                "message": {
                "DEBUG": "white",
                "INFO": "white",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            }
        },
        reset=True
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

logger = __get_logger()
