"""
Logging configuration for the application.
"""

import sys
from pathlib import Path
from loguru import logger

from app.core.config import LOG_LEVEL, LOG_FILE_PATH


def setup_logging():
    """
    Configure loguru logger with file and console output.
    """
    # Remove default logger
    logger.remove()

    # Add console handler
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True
    )

    # Ensure log directory exists
    log_path = Path(LOG_FILE_PATH)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Add file handler with rotation
    logger.add(
        LOG_FILE_PATH,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=LOG_LEVEL,
        rotation="00:00",  # Rotate daily at midnight
        retention="30 days",  # Keep logs for 30 days
        compression="zip"  # Compress rotated logs
    )

    return logger


# Initialize logger
app_logger = setup_logging()
