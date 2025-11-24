"""Logging configuration and setup module.

This allows library users to inject their custom log config by calling log.configure_logging().
"""

###################################################################################################
# Copyright (c) 2025 Utiligize ApS <contact@utiligize.com>                                        #
# This file is part of Configator: <https://github.com/Utiligize/configator>                      #
# SPDX-License-Identifier: MIT                                                                    #
# License-Filename: LICENSE.md                                                                    #
###################################################################################################

from os import getenv
from typing import Any, Sequence

from structlog import configure, make_filtering_bound_logger
from structlog import get_logger as structlog_get_logger
from structlog.stdlib import LoggerFactory
from structlog.types import Processor


def configure_logging(
    *, level: str = "INFO", processors: Sequence[Processor] | None = None
) -> None:
    """Configure structlog logging according to given parameters and environment variables."""
    actual_log_level = getenv("LOG_LEVEL", level).upper()
    if processors is None:
        processors = []

    configure(
        processors=processors,
        wrapper_class=make_filtering_bound_logger(actual_log_level),
        logger_factory=LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger() -> Any:
    """Convenience function that returns a logger according to configuration."""
    return structlog_get_logger()
