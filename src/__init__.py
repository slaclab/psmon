import logging as pslogging
from psmon import config


def log_level_parse(log_level):
    """
    Parse log level as a string (non-case sensitive) into a log level enum
    """
    return getattr(pslogging, log_level.upper(), config.LOG_LEVEL_ROOT)


# initialize logging for the package
pslogging.basicConfig(format=config.LOG_FORMAT, level=config.LOG_LEVEL_ROOT)
