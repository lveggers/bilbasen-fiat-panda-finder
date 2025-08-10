"""Logging configuration for the Bilbasen Fiat Panda Finder."""

import logging
import logging.config
import sys
from typing import Any, Dict
from datetime import datetime
import json

from .config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from the record
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key
            not in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "getMessage",
            }
        }
        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, ensure_ascii=False)


def get_logging_config() -> Dict[str, Any]:
    """Get logging configuration dictionary."""
    if settings.log_format.lower() == "json":
        formatter_class = f"{__name__}.JSONFormatter"
        format_string = ""  # Not used for JSON formatter
    else:
        formatter_class = "logging.Formatter"
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "()": formatter_class,
                "format": format_string,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "default",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "default",
                "filename": "app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "app": {
                "level": settings.log_level,
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "playwright": {
                "level": "WARNING",  # Reduce playwright verbosity
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "httpx": {
                "level": "WARNING",  # Reduce httpx verbosity
                "handlers": ["console", "file"],
                "propagate": False,
            },
        },
        "root": {
            "level": settings.log_level,
            "handlers": ["console", "file"],
        },
    }


def setup_logging() -> None:
    """Set up application logging."""
    config = get_logging_config()
    logging.config.dictConfig(config)

    # Get the main application logger
    logger = logging.getLogger("app")
    logger.info(
        "Logging configured",
        extra={
            "log_level": settings.log_level,
            "log_format": settings.log_format,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the specified name."""
    # Ensure logging is set up
    if not logging.getLogger("app").handlers:
        setup_logging()

    return logging.getLogger(f"app.{name}")


# Convenience function for getting module-specific loggers
def get_module_logger(module_name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return get_logger(module_name)
