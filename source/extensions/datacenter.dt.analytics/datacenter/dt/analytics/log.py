"""Module-level logger for the Boreas Operator extension.

Use this instead of print() so log level can be controlled via Kit's
log settings. Kit bridges the stdlib logging module into the carb log
sink at runtime.
"""

import logging

logger = logging.getLogger("boreas.operator")
