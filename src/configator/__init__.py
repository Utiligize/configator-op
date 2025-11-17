from importlib.metadata import version

from configator.core import load_config
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
    "load_config",
]
