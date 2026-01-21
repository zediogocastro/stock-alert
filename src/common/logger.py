import os
import logging
import inspect

from colorlog import ColoredFormatter

# Log format string defining the structure of each log message
_LOG_FORMAT = "%(log_color)s%(asctime)-16s [%(levelname)-8s]%(reset)s %(name)s.%(funcName)s:%(lineno)d - %(message)s"
# Date format string for log timestamps
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S,%03d"
# Color mapping for different log severity levels
_LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "red,bg_white",
}

log_level = os.getenv("LOG_LEVEL", "INFO").upper()

def _get_caller_module_name() -> str:
    """Determine the name of the module that called the logger.

    Returns:
        str: The fully qualified module name of the caller. Returns the logger module name as fallback
             if no valid caller is found in the stack.
    """
    stack = inspect.stack()
    for frame_info in stack:
        module = inspect.getmodule(frame_info.frame)
        if module and module.__name__ != __name__:
            return module.__name__
    return __name__

def _setup_logger(name: str) -> logging.Logger:
    """Create and configure a logger instance with standard formatting.
    
    Args:
        logger_name (str): The name for the logger,i.e. the fully qualified module name
                          This name appears in log messages to identify the source.
    
    Returns:
        logging.Logger: A configured logger instance with:
            - Log level: INFO (shows INFO, WARNING, ERROR, CRITICAL messages)
            - Handler: StreamHandler (outputs to standard error stream)
            - Formatter: ColoredFormatter with standard log format
            - Color mapping: Severity-based colors for terminal output
    
    Side Effects:
        - Creates a new logger if one with the given name doesn't exist
        - Attaches a StreamHandler and ColoredFormatter if not already present
        - Logs are written to the standard error stream
    """
    log = logging.getLogger(name)
    if not log.handlers:
        log.setLevel(getattr(logging, log_level, logging.INFO))
        handler = logging.StreamHandler()
        formatter = ColoredFormatter(
            _LOG_FORMAT,
            datefmt=_DATE_FORMAT,
            log_colors=_LOG_COLORS,
        )
        handler.setFormatter(formatter)
        log.addHandler(handler)
    return log

class _LoggerProxy():

    def __getattr__(self, name: str):
        caller_module = _get_caller_module_name()
        actual_logger = _setup_logger(caller_module)
        return getattr(actual_logger, name)


logger = _LoggerProxy()