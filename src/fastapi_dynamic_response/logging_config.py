# logging_config.py


import logging

from fastapi_dynamic_response.settings import settings
import structlog

logger = structlog.get_logger()


def configure_logging():
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

    logger.info("Logging configured")
    logger.info(f"Environment: {settings.ENV}")
