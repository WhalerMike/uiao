from __future__ import annotations

"""
Entra ID (Azure AD) evidence collector package.

Provides real-time collection of identity and access management evidence
from Microsoft Entra ID via the Microsoft Graph API.
"""

from .entra_collector import EntraCollector

__all__ = ["EntraCollector"]
