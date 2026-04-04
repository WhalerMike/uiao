"""
UIAO-Core Adapters Package.

All adapter classes are exported here for convenient import.
Adapters are DNS-style alignment resolvers — they do NOT perform
heavy OSCAL/SBOM/SSP conversions. That work lives in generators/.
"""

from .database_base import DatabaseAdapterBase
from .servicenow_adapter import ServiceNowAdapter

__all__ = [
    "DatabaseAdapterBase",
    "ServiceNowAdapter",
]
