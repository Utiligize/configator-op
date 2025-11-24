###################################################################################################
# Copyright (c) 2025 Utiligize ApS <contact@utiligize.com>                                        #
# This file is part of Configator: <https://github.com/Utiligize/configator>                      #
# SPDX-License-Identifier: MIT                                                                    #
# License-Filename: LICENSE.md                                                                    #
###################################################################################################

from importlib.metadata import version

from configator.core import load_config
from configator.log import configure_logging
from configator.models import ConfigatorSettings, Environment, PostgresConfig, SentryConfig

__maintainer__ = "kthy"
__version__ = version("configator")

__all__ = [
    "ConfigatorSettings",
    "Environment",
    "PostgresConfig",
    "SentryConfig",
    "__maintainer__",
    "__version__",
    "configure_logging",
    "load_config",
]
