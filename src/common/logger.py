import logging
import os
from colorlog import ColoredFormatter

def get_logger(name: str | None = None) -> logging.Logger:
    """Get a configured logger for a module
    
    This function returns a logger with colored console output.

    Args:
        name: The name of the calling module (str).
        If None, uses this module's name (common.logger) as a fallback.

    Returns:
        A configured logger.
    """
    # Get or create a logger instance
    logger = logging.getLogger(name or __name__)

    # Set the logging level
    # Read from environement variable, default to INFO
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    # Create a handler, StreamHandler sends to the console
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    # Create a formatter, ColoredFormatter adds color based on log level
    formatter = ColoredFormatter(
        fmt=(
        "%(log_color)s%(asctime)s.%(msecs)03d [%(levelname)-8s]%(reset)s "
        "%(cyan)s%(name)s%(reset)s.%(funcName)s:%(lineno)d - "
        "%(message_log_color)s%(message)s"
        ),
        # Date format
        datefmt="%Y-%m-%d %H:%M:%S",
        # Colors for different log levels
        log_colors={
            "DEBUG": "purple",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        # Colors for the actual message text
        secondary_log_colors={
                "message": {
                "DEBUG": "white",
                "INFO": "white",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red",
            }
        },
        # Reset colors after each log line
        reset=True
    )
    # Attach the formatter to the handler
    handler.setFormatter(formatter)

    return logger
