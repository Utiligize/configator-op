"""Typed exceptions raised by Configator."""

###################################################################################################
# Copyright (c) 2025 Utiligize ApS <contact@utiligize.com>                                        #
# This file is part of Configator: <https://github.com/Utiligize/configator>                      #
# SPDX-License-Identifier: MIT                                                                    #
# License-Filename: LICENSE.md                                                                    #
###################################################################################################


class ConfigatorError(Exception):
    """Base class for the typed failures raised while loading configuration.

    The developer-mode production guard in ``models.py`` stays outside this
    hierarchy and still raises a plain ``RuntimeError``: it is a refusal to
    start, not a report about the config item.
    """


class ConfigInvalidError(ConfigatorError):
    """The config item was read, but does not fit the schema.

    Retrying or falling back to an older snapshot cannot help: someone has to
    fix the 1Password item or the schema. Callers should fail loudly.
    """


class ConfigUnavailableError(ConfigatorError):
    """1Password could not be reached, or would not answer.

    The config that is there may well be fine, so a caller that keeps a
    last-good snapshot may boot from it instead of failing.
    """
