"""
UIAO-Core Adapters Package.

All adapter classes are exported here for convenient import.
Adapters are DNS-style alignment resolvers -- they do NOT perform
heavy OSCAL/SBOM/SSP conversions. That work lives in generators/.
"""

from .database_base import DatabaseAdapterBase
from .entra_adapter import EntraAdapter
from .m365_adapter import M365Adapter
from .paloalto_adapter import PaloAltoAdapter
from .patchstate_adapter import PatchStateAdapter
from .servicenow_adapter import ServiceNowAdapter
from .stigcompliance_adapter import StigComplianceAdapter
from .terraform_adapter import TerraformAdapter
from .vulnscan_adapter import VulnScanAdapter

__all__ = [
    "DatabaseAdapterBase",
    "EntraAdapter",
    "M365Adapter",
    "PaloAltoAdapter",
    "PatchStateAdapter",
    "ServiceNowAdapter",
    "StigComplianceAdapter",
    "TerraformAdapter",
    "VulnScanAdapter",
]
