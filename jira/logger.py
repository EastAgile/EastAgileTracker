import logging
import os
from datetime import datetime


class CustomFormatter(logging.Formatter):
    """Custom formatter adding color to the log output"""

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = (
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    )

    FORMATS = {
        logging.DEBUG: grey + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logger(name, log_file=None, level=logging.INFO):
    """Function to set up as many loggers as you want"""

    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Create handlers
    c_handler = logging.StreamHandler()
    c_handler.setFormatter(CustomFormatter())
    logger.addHandler(c_handler)

    if log_file:
        if not os.path.exists("logs"):
            os.makedirs("logs")
        f_handler = logging.FileHandler(log_file)
        f_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(f_handler)

    return logger


# Create a logger for the Jira migration
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = f"logs/jira_migration_{timestamp}.log"
logger = setup_logger("jira_migration", log_file)
