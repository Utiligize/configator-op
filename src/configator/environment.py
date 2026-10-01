"""Deployment environment and developer mode, as read from environment variables."""

###################################################################################################
# Copyright (c) 2025-2026 Utiligize ApS <contact@utiligize.com>                                   #
# This file is part of Configator: <https://github.com/Utiligize/configator>                      #
# SPDX-License-Identifier: MIT                                                                    #
# License-Filename: LICENSE.md                                                                    #
###################################################################################################

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from enum import StrEnum, unique
from os import getenv

from .log import get_logger

log = get_logger()

# Every ConfigatorSettings instance, one per section included, picks its sources, so the
# developer mode is logged by the first and skipped by the rest.
_dev_mode_logged: ContextVar[bool] = ContextVar("configator_dev_mode_logged", default=False)


@unique
class Environment(StrEnum):
    DEVELOPMENT = "develop"
    STAGING = "staging"
    PRODUCTION = "product"


def dev_mode_enabled() -> bool:
    """Return True when `CONFIGATOR_DEV_MODE` is set to a non-empty value."""
    return bool(getenv("CONFIGATOR_DEV_MODE"))


@contextmanager
def dev_mode_log_scope() -> Generator[None, None, None]:
    """Log the developer mode once for all settings built inside the block."""
    token = _dev_mode_logged.set(False)
    try:
        yield
    finally:
        _dev_mode_logged.reset(token)


def log_dev_mode_once() -> None:
    """Log the developer mode unless it has already been logged in this scope."""
    if _dev_mode_logged.get():
        return
    _dev_mode_logged.set(True)
    log_msg = "configator developer mode is %s"
    if dev_mode_enabled():
        log.warning(log_msg, "ENABLED")
    else:
        log.debug(log_msg, "disabled")


def refuse_dev_mode_in_production() -> None:
    """Raise if developer mode is enabled in a production environment."""
    if dev_mode_enabled() and _is_production():
        raise RuntimeError(
            "CONFIGATOR_DEV_MODE is set in a production environment; refusing to let "
            "a .env file override vetted secrets. Unset CONFIGATOR_DEV_MODE (and ensure "
            "no .env ships in production images)."
        )


def _is_production() -> bool:
    """Return True when the deployment environment resolves to production.

    Reads ``ENVIRONMENT`` first, falling back to ``APP_ENV``, and matches the
    value case-insensitively against the ``Environment.PRODUCTION`` prefix so
    both ``product`` and ``production`` are recognised.
    """
    env = getenv("ENVIRONMENT") or getenv("APP_ENV") or ""
    return env.lower().startswith(Environment.PRODUCTION)
