"""
Logging configuration for the scraping system.
"""
import logging
import sys
from pathlib import Path
from typing import Dict


def setup_logging(
    level: str = "INFO",
    log_file: str = None,
    format_string: str = None
) -> Dict[str, logging.Logger]:
    """
    Set up logging configuration for different components.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional log file path
        format_string: Custom format string
    
    Returns:
        Dictionary of configured loggers
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Create formatter
    formatter = logging.Formatter(format_string)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Create specific loggers
    loggers = {
        "scraper": logging.getLogger("scraper"),
        "data": logging.getLogger("data"),
        "pipeline": logging.getLogger("pipeline"),
        "monitoring": logging.getLogger("monitoring"),
        "quality": logging.getLogger("quality")
    }
    
    return loggers


# Default logger setup
loggers = setup_logging()