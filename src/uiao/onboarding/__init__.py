"""UIAO onboarding package.

Provides guided wizard and pre-generation validator for canon YAML files.
"""

from .validator import validate_canon
from .wizard import run_wizard

__all__ = ["run_wizard", "validate_canon"]
