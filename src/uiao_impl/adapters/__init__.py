"""
UIAO-Core Adapters Package.

All adapter classes are exported here for convenient import.
Adapters are DNS-style alignment resolvers -- they do NOT perform
heavy OSCAL/SBOM/SSP conversions. That work lives in generators/.
"""

from .database_base import DatabaseAdapterBase
from .entra_adapter import EntraAdapter
from .servicenow_adapter import ServiceNowAdapter
from .terraform_adapter import TerraformAdapter

__all__ = [
    "DatabaseAdapterBase",
    "EntraAdapter",
    "ServiceNowAdapter",
    "TerraformAdapter",
]
