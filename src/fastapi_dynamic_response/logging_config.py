# logging_config.py
import logging
import structlog
import sys

from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer

from rich.traceback import install

logger = structlog.get_logger()


install(show_locals=True)


def configure_logging_one(dev_mode: bool = True):
    """Configure structlog based on the mode (dev or prod)."""
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.DEBUG if dev_mode else logging.INFO,
    )

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),  # Add timestamps
            structlog.stdlib.add_log_level,  # Add log levels
            structlog.processors.StackInfoRenderer(),  # Render stack info
            structlog.processors.format_exc_info,  # Format exceptions
            # structlog.dev.RichTracebackFormatter(),
            ConsoleRenderer(
                # exception_formatter=structlog.dev.rich_traceback
            )
            if dev_mode
            else JSONRenderer(),  # Render logs nicely for dev
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


import logging

from fastapi_dynamic_response.settings import Settings
import structlog


def configure_logging_two():
    settings = Settings()

    # Clear existing loggers
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
        }
    )

    if settings.ENV == "local":
        # Local development logging configuration
        processors = [
            # structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=False),
        ]
        logging_level = logging.DEBUG

        # Enable rich tracebacks
        from rich.traceback import install

        install(show_locals=True)

        # Use RichHandler for pretty console logs
        from rich.logging import RichHandler

        logging.basicConfig(
            level=logging_level,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler()],
        )
    else:
        # Production logging configuration
        processors = [
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
        logging_level = logging.INFO

        # Standard logging configuration
        logging.basicConfig(
            format="%(message)s",
            level=logging_level,
            handlers=[logging.StreamHandler()],
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(logging_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Redirect uvicorn loggers to structlog
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(logger_name)
        logger.handlers = []
        logger.propagate = True


configure_logging = configure_logging_two
